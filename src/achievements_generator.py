import logging
from typing import Dict, Any, List
from datetime import datetime
import pytz
from dateutil import parser
from collections import defaultdict

logger = logging.getLogger(__name__)

class AchievementsGenerator:
    MIN_FILES_FOR_PRODUCTIVE_TEAM = 10

    def __init__(self):
        logger.info("AchievementsGenerator initialized")

    def generate_achievements(self, org_name: str, repositories: List[Dict[str, Any]], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate achievements based on GitHub data collected from an organization's repositories."""
        logger.info(f"Generating achievements for organization: {org_name}")
        
        achievements = []
        try:
            # First, organize data by repository and contributor for easier processing
            repos_data = {repo['name']: repo for repo in repositories}
            contributors_by_repo = {}
            
            for contributor in contributors_data:
                repo_name = contributor.get('repo_name')
                if repo_name not in contributors_by_repo:
                    contributors_by_repo[repo_name] = []
                contributors_by_repo[repo_name].append(contributor)
            
            # Generate individual achievements
            achievements.extend(self._find_first_commit(org_name, repos_data, contributors_data))
            achievements.extend(self._find_epic_pr(org_name, repos_data, contributors_data))
            achievements.extend(self._find_night_owl(org_name, repos_data, contributors_data))
            achievements.extend(self._find_code_surgeon(org_name, repos_data, contributors_data))
            achievements.extend(self._find_pr_master(org_name, repos_data, contributors_data))
            achievements.extend(self._find_issue_resolver(org_name, repos_data, contributors_data))
            achievements.extend(self._find_review_champion(org_name, repos_data, contributors_data))
            achievements.extend(self._find_weekend_warrior(org_name, repos_data, contributors_data))
            achievements.extend(self._find_jack_of_all_trades(org_name, repos_data, contributors_data))
            
            # Generate team achievements
            achievements.extend(self._find_most_productive_team(org_name, repos_data, contributors_data))
            achievements.extend(self._find_most_collaborative_team(org_name, repos_data, contributors_data))

            # Generate mentor opportunity entries for teams that could use support
            achievements.extend(self._find_teams_ready_for_boost(org_name, repos_data, contributors_data))
            
            logger.info(f"Generated {len(achievements)} achievements for {org_name}")
            return achievements
            
        except Exception as e:
            logger.error(f"Error generating achievements for {org_name}: {str(e)}")
            return []
            
    def _find_first_commit(self, org_name: str, repos_data: Dict[str, Any], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the contributor with the first commit after project kickoff."""
        try:
            earliest_commit = None
            earliest_contributor = None
            earliest_repo = None
            earliest_time = None
            
            for contributor in contributors_data:
                if contributor.get('first_commit_time'):
                    commit_time = parser.parse(contributor['first_commit_time'])
                    if earliest_time is None or commit_time < earliest_time:
                        earliest_time = commit_time
                        earliest_contributor = contributor
                        earliest_repo = contributor.get('repo_name')
                        earliest_commit = contributor.get('first_commit_id')
                        logger.debug(f"Found earlier commit: {earliest_contributor['login']} at {earliest_time} in repo {earliest_repo}")
            
            if earliest_contributor and earliest_time:
                formatted_time = earliest_time.strftime("%H:%M:%S")
                logger.info(f"First commit achievement found: {earliest_contributor['login']} at {formatted_time} in {earliest_repo}")
                return [{
                    "title": "First to Commit",
                    "person": {
                        "name": earliest_contributor.get('name', earliest_contributor['login']),
                        "avatar": earliest_contributor.get('avatar_url', f"https://github.com/{earliest_contributor['login']}.png"),
                        "team": earliest_contributor.get('team', ""),
                        "githubUsername": earliest_contributor['login']
                    },
                    "value": formatted_time,
                    "icon": "accessTime",
                    "description": "First to make a code contribution after kickoff",
                    "repo": earliest_repo,
                    "commitId": earliest_commit
                }]
            logger.info("No first commit achievement found - no valid commit data available")
            return []
        except Exception as e:
            logger.error(f"Error finding first commit achievement: {str(e)}", exc_info=True)
            return []
            
    def _find_epic_pr(self, org_name: str, repos_data: Dict[str, Any], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the contributor with the largest pull request by lines changed."""
        try:
            logger.info(f"Finding contributor with largest PR for {org_name}")
            
            largest_pr_size = 0
            largest_pr_contributor = None
            largest_pr_repo = None
            largest_pr_number = None
            processed_count = 0
            
            for contributor in contributors_data:
                processed_count += 1
                if contributor.get('largest_pr'):
                    pr_size = contributor['largest_pr'].get('additions', 0) + contributor['largest_pr'].get('deletions', 0)
                    logger.debug(f"Found PR for {contributor['login']} with {pr_size} lines changed")
                    if pr_size > largest_pr_size:
                        largest_pr_size = pr_size
                        largest_pr_contributor = contributor
                        largest_pr_repo = contributor.get('repo_name')
                        largest_pr_number = contributor['largest_pr'].get('number')
                        logger.debug(f"New largest PR: {pr_size} lines by {contributor['login']} in PR #{largest_pr_number}")
            
            logger.info(f"Processed {processed_count} contributors when searching for epic PR")
            
            if largest_pr_contributor and largest_pr_size > 0:
                formatted_size = f"{largest_pr_size:,} lines"
                logger.info(f"Epic PR achievement found: {largest_pr_contributor['login']} with {formatted_size} in PR #{largest_pr_number}")
                return [{
                    "title": "Epic PR",
                    "person": {
                        "name": largest_pr_contributor.get('name', largest_pr_contributor['login']),
                        "avatar": largest_pr_contributor.get('avatar_url', f"https://github.com/{largest_pr_contributor['login']}.png"),
                        "team": largest_pr_contributor.get('team', ""),
                        "githubUsername": largest_pr_contributor['login']
                    },
                    "value": formatted_size,
                    "icon": "merge",
                    "description": "Largest merged PR by lines added + deleted",
                    "repo": largest_pr_repo,
                    "prNumber": str(largest_pr_number) if largest_pr_number else ""
                }]
            logger.info("No epic PR achievement found - no valid PR data available")
            return []
        except Exception as e:
            logger.error(f"Error finding epic PR achievement: {str(e)}", exc_info=True)
            return []
            
    def _find_night_owl(self, org_name: str, repos_data: Dict[str, Any], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the contributor who committed code at the latest hour."""
        try:            
            latest_contributor = None
            latest_repo = None            
            latest_early_morning_commit_count = None
            latest_late_night_commit_count = None
            latest_total_commits = 0
            
            # For each contributor, find the largest sum of "early_morning_commits" and "late_night_commits"
            for contributor in contributors_data:
                if contributor.get('late_night_commits') and contributor.get('early_morning_commits'): # late_night_commits is a count of commits during the night
                    late_night_commit_count = contributor['late_night_commits']
                    early_morning_commit_count = contributor['early_morning_commits']
                    total_commits = late_night_commit_count + early_morning_commit_count
                    if total_commits > 0:
                        if total_commits > latest_total_commits:
                            latest_total_commits = total_commits
                            latest_contributor = contributor
                            latest_repo = contributor.get('repo_name')
                            latest_early_morning_commit_count = early_morning_commit_count
                            latest_late_night_commit_count = late_night_commit_count                            



            if latest_contributor and latest_total_commits>0:
                
                return [{
                    "title": "Night Owl",
                    "person": {
                        "name": latest_contributor.get('name', latest_contributor['login']),
                        "avatar": latest_contributor.get('avatar_url', f"https://github.com/{latest_contributor['login']}.png"),
                        "team": latest_contributor.get('team', ""),
                        "githubUsername": latest_contributor['login']
                    },
                    "value": f"{latest_total_commits} commits",
                    "icon": "accessTime",
                    "description": "Commits between 10pm–4am MST",
                    "repo": latest_repo                    
                }]
            return []
        except Exception as e:
            logger.error(f"Error finding night owl achievement: {str(e)}", exc_info=True)
            return []
    
    def _find_code_surgeon(self, org_name: str, repos_data: Dict[str, Any], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the contributor with the most code deletions."""
        try:
            max_deletions = 0
            max_deletion_contributor = None
            max_deletion_repo = None
            
            for contributor in contributors_data:
                deletions = contributor.get('deletions', 0)
                if deletions > max_deletions:
                    max_deletions = deletions
                    max_deletion_contributor = contributor
                    max_deletion_repo = contributor.get('repo_name')
            
            if max_deletion_contributor and max_deletions > 0:
                formatted_deletions = f"{max_deletions:,} lines"
                return [{
                    "title": "Code Surgeon",
                    "person": {
                        "name": max_deletion_contributor.get('name', max_deletion_contributor['login']),
                        "avatar": max_deletion_contributor.get('avatar_url', f"https://github.com/{max_deletion_contributor['login']}.png"),
                        "team": max_deletion_contributor.get('team', ""),
                        "githubUsername": max_deletion_contributor['login']
                    },
                    "value": formatted_deletions,
                    "icon": "delete",
                    "description": "Most lines of code removed across commits",
                    "repo": max_deletion_repo
                }]
            return []
        except Exception as e:
            logger.error(f"Error finding code surgeon achievement: {str(e)}")
            return []
    
    def _find_pr_master(self, org_name: str, repos_data: Dict[str, Any], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the contributor who opened the most PRs."""
        try:
            max_prs = 0
            max_pr_contributor = None
            max_pr_repo = None
            
            for contributor in contributors_data:
                if contributor.get('pull_requests') and contributor['pull_requests'].get('total', 0) > max_prs:
                    max_prs = contributor['pull_requests'].get('total', 0)
                    max_pr_contributor = contributor
                    max_pr_repo = contributor.get('repo_name')
            
            if max_pr_contributor and max_prs > 0:
                return [{
                    "title": "PR Master",
                    "person": {
                        "name": max_pr_contributor.get('name', max_pr_contributor['login']),
                        "avatar": max_pr_contributor.get('avatar_url', f"https://github.com/{max_pr_contributor['login']}.png"),
                        "team": max_pr_contributor.get('team', ""),
                        "githubUsername": max_pr_contributor['login']
                    },
                    "value": f"{max_prs} PRs",
                    "icon": "pull_request",
                    "description": "Most pull requests created",
                    "repo": max_pr_repo
                }]
            return []
        except Exception as e:
            logger.error(f"Error finding PR master achievement: {str(e)}")
            return []
    
    def _find_issue_resolver(self, org_name: str, repos_data: Dict[str, Any], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the contributor who closed the most issues."""
        try:
            max_issues_closed = 0
            max_issue_contributor = None
            max_issue_repo = None
            
            for contributor in contributors_data:
                if contributor.get('issues') and contributor['issues'].get('closed', 0) > max_issues_closed:
                    max_issues_closed = contributor['issues'].get('closed', 0)
                    max_issue_contributor = contributor
                    max_issue_repo = contributor.get('repo_name')
            
            if max_issue_contributor and max_issues_closed > 0:
                return [{
                    "title": "Issue Resolver",
                    "person": {
                        "name": max_issue_contributor.get('name', max_issue_contributor['login']),
                        "avatar": max_issue_contributor.get('avatar_url', f"https://github.com/{max_issue_contributor['login']}.png"),
                        "team": max_issue_contributor.get('team', ""),
                        "githubUsername": max_issue_contributor['login']
                    },
                    "value": f"{max_issues_closed} issues",
                    "icon": "task_alt",
                    "description": "Most GitHub issues closed",
                    "repo": max_issue_repo
                }]
            return []
        except Exception as e:
            logger.error(f"Error finding issue resolver achievement: {str(e)}")
            return []
    
    def _find_review_champion(self, org_name: str, repos_data: Dict[str, Any], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the contributor who reviewed the most PRs."""
        try:
            max_reviews = 0
            max_review_contributor = None
            max_review_repo = None
            
            for contributor in contributors_data:
                reviews = contributor.get('reviews', 0)
                if reviews > max_reviews:
                    max_reviews = reviews
                    max_review_contributor = contributor
                    max_review_repo = contributor.get('repo_name')
            
            if max_review_contributor and max_reviews > 0:
                return [{
                    "title": "Review Champion",
                    "person": {
                        "name": max_review_contributor.get('name', max_review_contributor['login']),
                        "avatar": max_review_contributor.get('avatar_url', f"https://github.com/{max_review_contributor['login']}.png"),
                        "team": max_review_contributor.get('team', ""),
                        "githubUsername": max_review_contributor['login']
                    },
                    "value": f"{max_reviews} reviews",
                    "icon": "rate_review",
                    "description": "Most pull request reviews submitted",
                    "repo": max_review_repo
                }]
            return []
        except Exception as e:
            logger.error(f"Error finding review champion achievement: {str(e)}")
            return []
    
    def _find_weekend_warrior(self, org_name: str, repos_data: Dict[str, Any], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the contributor with the most weekend commits."""
        try:
            max_weekend_commits = 0
            max_weekend_contributor = None
            max_weekend_repo = None
            
            for contributor in contributors_data:
                if contributor.get('weekend_commits', 0) > max_weekend_commits:
                    max_weekend_commits = contributor.get('weekend_commits', 0)
                    max_weekend_contributor = contributor
                    max_weekend_repo = contributor.get('repo_name')
            
            if max_weekend_contributor and max_weekend_commits > 0:
                return [{
                    "title": "Weekend Warrior",
                    "person": {
                        "name": max_weekend_contributor.get('name', max_weekend_contributor['login']),
                        "avatar": max_weekend_contributor.get('avatar_url', f"https://github.com/{max_weekend_contributor['login']}.png"),
                        "team": max_weekend_contributor.get('team', ""),
                        "githubUsername": max_weekend_contributor['login']
                    },
                    "value": f"{max_weekend_commits} commits",
                    "icon": "weekend",
                    "description": "Most commits on Saturday & Sunday",
                    "repo": max_weekend_repo
                }]
            return []
        except Exception as e:
            logger.error(f"Error finding weekend warrior achievement: {str(e)}")
            return []
    
    def _find_jack_of_all_trades(self, org_name: str, repos_data: Dict[str, Any], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the contributor who contributed to the most repositories."""
        try:
            # Build a map of contributors and which repos they contributed to
            contributor_repos = {}
            for contributor in contributors_data:
                login = contributor.get('login')
                repo = contributor.get('repo_name')
                if login and repo:
                    if login not in contributor_repos:
                        contributor_repos[login] = set()
                    contributor_repos[login].add(repo)
            
            # Find the contributor with the most repos
            max_repos = 0
            jack_contributor = None
            
            for login, repos in contributor_repos.items():
                if len(repos) > max_repos:
                    max_repos = len(repos)
                    jack_contributor = next((c for c in contributors_data if c.get('login') == login), None)
            
            if jack_contributor and max_repos > 1:
                return [{
                    "title": "Jack of All Trades",
                    "person": {
                        "name": jack_contributor.get('name', jack_contributor['login']),
                        "avatar": jack_contributor.get('avatar_url', f"https://github.com/{jack_contributor['login']}.png"),
                        "team": jack_contributor.get('team', ""),
                        "githubUsername": jack_contributor['login']
                    },
                    "value": f"{max_repos} repos",
                    "icon": "explore",
                    "description": "Contributed to the most repositories",
                    "repo": org_name  # Using org name as a placeholder
                }]
            return []
        except Exception as e:
            logger.error(f"Error finding jack of all trades achievement: {str(e)}")
            return []
            
    def _find_most_productive_team(self, org_name: str, repos_data: Dict[str, Any], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the team that completed the most tasks."""
        try:
            # Group contributors by team
            teams = defaultdict(list)
            for contributor in contributors_data:
                team = contributor.get('team')
                if team:
                    teams[team].append(contributor)
            
            if not teams:
                logger.warning(f"No team information found in contributors data for {org_name}")
                return []
            
            # Calculate team productivity (commits + PRs merged + issues closed)
            team_productivity = {}
            for team_name, team_members in teams.items():
                tasks_completed = 0
                members_count = len(team_members)
                
                files_changed = 0
                for member in team_members:
                    # Count completed tasks (commits + PRs merged + issues closed)
                    tasks_completed += member.get('commits', 0)
                    tasks_completed += member.get('pull_requests', {}).get('merged', 0)
                    tasks_completed += member.get('issues', {}).get('closed', 0)
                    files_changed += member.get('unique_files_changed', 0)

                if tasks_completed > 0 and members_count > 0 and files_changed >= self.MIN_FILES_FOR_PRODUCTIVE_TEAM:
                    team_productivity[team_name] = {
                        "tasks": tasks_completed,
                        "members": members_count,
                        "files_changed": files_changed,
                        "members_data": team_members
                    }
            
            # Find the most productive team
            if not team_productivity:
                return []
                
            most_productive_team = max(team_productivity.items(), key=lambda x: x[1]["tasks"])
            team_name, team_data = most_productive_team
            
            # Create team slug/page name from team name
            team_page = team_name.lower().replace(' ', '-')
            
            return [{
                "title": "Most Productive Team",
                "team": team_name,
                "value": f"{team_data['tasks']} tasks",
                "icon": "group",
                "members": team_data["members"],
                "filesChanged": team_data["files_changed"],
                "description": "Most commits + merged PRs + issues closed",
                "teamPage": team_page
            }]
        except Exception as e:
            logger.error(f"Error finding most productive team achievement: {str(e)}")
            return []
            
    def _find_most_collaborative_team(self, org_name: str, repos_data: Dict[str, Any], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the team with the highest number of PR reviews and comments."""
        try:
            # Group contributors by team
            teams = defaultdict(list)
            for contributor in contributors_data:
                team = contributor.get('team')
                if team:
                    teams[team].append(contributor)
            
            if not teams:
                logger.warning(f"No team information found in contributors data for {org_name}")
                return []
            
            # Calculate team collaboration (reviews + comments)
            team_collaboration = {}
            for team_name, team_members in teams.items():
                collaboration_count = 0
                members_count = len(team_members)
                
                for member in team_members:
                    # Count reviews
                    collaboration_count += member.get('reviews', 0)
                    
                    # The structure doesn't explicitly track comments, but 
                    # we can assume reviews are a good proxy for collaboration
                
                if collaboration_count > 0 and members_count > 0:
                    team_collaboration[team_name] = {
                        "collaboration": collaboration_count,
                        "members": members_count,
                        "members_data": team_members
                    }
            
            # Find the most collaborative team
            if not team_collaboration:
                return []
                
            most_collaborative_team = max(team_collaboration.items(), key=lambda x: x[1]["collaboration"])
            team_name, team_data = most_collaborative_team
            
            # Create team slug/page name from team name
            team_page = team_name.lower().replace(' ', '-')
            
            return [{
                "title": "Most Collaborative",
                "team": team_name,
                "value": f"{team_data['collaboration']} PRs reviewed",
                "icon": "merge",
                "members": team_data["members"],
                "description": "Highest number of pull request reviews",
                "teamPage": team_page
            }]
        except Exception as e:
            logger.error(f"Error finding most collaborative team achievement: {str(e)}")
            return []

    def _find_teams_ready_for_boost(self, org_name: str, repos_data: Dict[str, Any], contributors_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find teams with low GitHub activity so mentors can offer support."""
        try:
            teams = defaultdict(list)
            for contributor in contributors_data:
                team = contributor.get('team')
                if team:
                    teams[team].append(contributor)

            if not teams:
                return []

            boost_teams = []
            for team_name, team_members in teams.items():
                total_commits = sum(member.get('commits', 0) for member in team_members)
                files_changed = sum(member.get('unique_files_changed', 0) for member in team_members)
                members_count = len(team_members)

                if files_changed < self.MIN_FILES_FOR_PRODUCTIVE_TEAM or total_commits < 5:
                    team_page = team_name.lower().replace(' ', '-')
                    boost_teams.append({
                        "title": "Ready for a Boost",
                        "team": team_name,
                        "value": f"{files_changed} files, {total_commits} commits",
                        "icon": "rocket_launch",
                        "members": members_count,
                        "filesChanged": files_changed,
                        "description": "This team might benefit from some mentor guidance to get rolling!",
                        "teamPage": team_page,
                        "type": "mentor_opportunity"
                    })

            logger.info(f"Found {len(boost_teams)} teams ready for a boost in {org_name}")
            return boost_teams
        except Exception as e:
            logger.error(f"Error finding teams ready for boost: {str(e)}")
            return []