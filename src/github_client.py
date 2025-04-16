import aiohttp
import asyncio
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.session = None

    async def ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def get_organization_repos(self, org_name: str) -> List[Dict[str, Any]]:
        await self.ensure_session()
        url = f"{self.base_url}/orgs/{org_name}/repos"
        return await self.get_paginated_data(url)

    async def get_repo_contributors(self, repo_full_name: str) -> List[Dict[str, Any]]:
        await self.ensure_session()
        url = f"{self.base_url}/repos/{repo_full_name}/contributors"
        return await self.get_paginated_data(url)

    async def get_contributor_stats(self, org_name: str, repo_name: str, contributor_login: str) -> Dict[str, Any]:
        await self.ensure_session()
        repo_full_name = f"{org_name}/{repo_name}"
        
        stats = {
            "login": contributor_login,
            "org_name": org_name,
            "repo_name": repo_name,
            "commits": 0,
            "additions": 0,
            "deletions": 0,
            "pull_requests": {
                "total": 0,
                "open": 0,
                "closed": 0,
                "merged": 0
            },
            "issues": {
                "total": 0,
                "open": 0,
                "closed": 0
            },
            "reviews": 0,
            "weekend_commits": 0,
            "saturday_commits": 0,
            "sunday_commits": 0,
            "late_night_commits": 0,
            "early_morning_commits": 0,
            "first_commit_time": None,
            "first_commit_id": None,
            "latest_commit_time": None,
            "latest_commit_id": None,
            "largest_pr": None,
            "avatar_url": None,
            "name": None
        }

        # Try to fetch user profile info
        try:
            user_url = f"{self.base_url}/users/{contributor_login}"
            print(f"Fetching user profile from {user_url}")
            async with self.session.get(user_url) as response:
                if response.status == 200:
                    user_data = await response.json()
                    stats["avatar_url"] = user_data.get("avatar_url")
                    stats["name"] = user_data.get("name", contributor_login)
        except Exception as e:
            logger.warning(f"Error fetching user profile for {contributor_login}: {str(e)}")

        # Fetch commit stats
        commits_url = f"{self.base_url}/repos/{repo_full_name}/commits"
        commits = await self.get_paginated_data(commits_url, params={"author": contributor_login, "per_page": 100})
        stats["commits"] = len(commits)

        # Process commits for achievements
        if commits:
            # Sort commits by date
            sorted_commits = sorted(
                [c for c in commits if c.get("commit", {}).get("committer", {}).get("date")], 
                key=lambda x: x["commit"]["committer"]["date"]
            )

            # Add date_mst to each commit
            for commit in sorted_commits:
                commit["date_mst"] = commit["commit"]["committer"]["date"]
                # Convert from UTC to Mountain Standard Time
                from datetime import datetime, timedelta                
                commit["date_mst"] = commit["date_mst"].replace("Z", "+00:00")
                commit["date_mst"] = datetime.fromisoformat(commit["date_mst"]) - timedelta(hours=7)
                commit["date_mst"] = commit["date_mst"].isoformat()
                commit["date_mst"] = commit["date_mst"].replace("+00:00", "")
                

            # late_night_count = Commits between 10pm at 12am using date_mst
            late_night_count = 0
                
            # early_morning_count = Commits between 12am and 4am using date_mst
            early_morning_count = 0
            for commit in commits:
                if commit.get("date_mst"):
                    commit_time = commit["date_mst"]
                    # Extract the time part
                    commit_time = commit_time.split("T")[1]
                    is_early_morning = commit_time >= "00:00" and commit_time < "04:00"
                    is_late_night = commit_time >= "22:00" and commit_time < "24:00"
                    if is_late_night:
                        late_night_count += 1
                        logger.info(f"Late night commit detected: {commit_time} - {commit.get('sha', 'unknown')}")
                    if is_early_morning:
                        early_morning_count += 1
                        logger.info(f"Early morning commit detected: {commit_time} - {commit.get('sha', 'unknown')}")
            
            stats["early_morning_commits"] = early_morning_count
            stats["late_night_commits"] = late_night_count
            logger.info(f"Total early morning commits for {contributor_login}: {early_morning_count}")
            logger.info(f"Total late night commits for {contributor_login}: {late_night_count}")
            
                            
            # Weekend commits
            stats["weekend_commits"] = sum(
                1 for commit in commits 
                if commit.get("commit", {}).get("committer", {}).get("date") and 
                self._is_weekend(commit["commit"]["committer"]["date"])
            )

            # Saturday commits
            stats["saturday_commits"] = sum(
                1 for commit in commits 
                if commit.get("commit", {}).get("committer", {}).get("date") and 
                self._is_saturday(commit["commit"]["committer"]["date"])
            )
            
            # Sunday commits
            stats["sunday_commits"] = sum(
                1 for commit in commits 
                if commit.get("commit", {}).get("committer", {}).get("date") and 
                self._is_sunday(commit["commit"]["committer"]["date"])
            )                
            
            if sorted_commits:
                # First commit
                first_commit = sorted_commits[0]
                stats["first_commit_time"] = first_commit["commit"]["committer"]["date"]
                stats["first_commit_id"] = first_commit["sha"]
                
                # Latest commit
                last_commit = sorted_commits[-1]
                stats["latest_commit_time"] = last_commit["commit"]["committer"]["date"]
                stats["latest_commit_id"] = last_commit["sha"]
                

        for commit in commits:
            if "stats" in commit:
                stats["additions"] += commit["stats"].get("additions", 0)
                stats["deletions"] += commit["stats"].get("deletions", 0)

        # Fetch PR stats
        prs_url = f"{self.base_url}/repos/{repo_full_name}/pulls"
        prs = await self.get_paginated_data(prs_url, params={"state": "all", "author": contributor_login, "per_page": 100})
        # Since the API doesn't support filtering by author, we need to filter manually
        prs = [pr for pr in prs if pr.get("user", {}).get("login") == contributor_login]
        stats["pull_requests"]["total"] = len(prs)
        stats["pull_requests"]["open"] = sum(1 for pr in prs if pr["state"] == "open")
        stats["pull_requests"]["closed"] = sum(1 for pr in prs if pr["state"] == "closed" and not pr["merged_at"])
        stats["pull_requests"]["merged"] = sum(1 for pr in prs if pr["merged_at"])
        
        # Find largest PR
        largest_pr_size = 0
        largest_pr = None
        
        for pr in prs:
            if pr.get("merged_at"):  # Only count merged PRs
                # Get PR details including additions/deletions
                pr_url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr['number']}"
                async with self.session.get(pr_url) as response:
                    if response.status == 200:
                        pr_data = await response.json()
                        pr_size = pr_data.get("additions", 0) + pr_data.get("deletions", 0)
                        if pr_size > largest_pr_size:
                            largest_pr_size = pr_size
                            largest_pr = {
                                "number": pr_data.get("number"),
                                "title": pr_data.get("title"),
                                "additions": pr_data.get("additions", 0),
                                "deletions": pr_data.get("deletions", 0),
                                "merged_at": pr_data.get("merged_at")
                            }
        
        if largest_pr:
            stats["largest_pr"] = largest_pr

        # Fetch issue stats
        issues_url = f"{self.base_url}/repos/{repo_full_name}/issues"
        issues = await self.get_paginated_data(issues_url, params={"state": "all", "creator": contributor_login, "per_page": 100})
        stats["issues"]["total"] = len(issues)
        stats["issues"]["open"] = sum(1 for issue in issues if issue["state"] == "open")
        stats["issues"]["closed"] = sum(1 for issue in issues if issue["state"] == "closed")

        # Fetch review stats
        reviews = await self.get_pr_reviews(repo_full_name, contributor_login)
        stats["reviews"] = len(reviews)

        return stats
        
    def _is_weekend(self, date_str: str) -> bool:
        """Check if a date string is a weekend (Saturday=5 or Sunday=6)."""
        from datetime import datetime
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date.weekday() >= 5  # 5=Saturday, 6=Sunday
    
    def _is_saturday(self, date_str: str) -> bool:
        """Check if a date string is a Saturday."""
        from datetime import datetime
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date.weekday() == 5
    
    def _is_sunday(self, date_str: str) -> bool:
        """Check if a date string is a Sunday."""
        from datetime import datetime
        date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date.weekday() == 6

    async def get_pr_reviews(self, repo_full_name: str, contributor_login: str) -> List[Dict[str, Any]]:
        await self.ensure_session()
        prs_url = f"{self.base_url}/repos/{repo_full_name}/pulls"
        prs = await self.get_paginated_data(prs_url, params={"state": "all", "per_page": 100})
        
        reviews = []
        for pr in prs:
            reviews_url = f"{self.base_url}/repos/{repo_full_name}/pulls/{pr['number']}/reviews"
            pr_reviews = await self.get_paginated_data(reviews_url, params={"per_page": 100})
            reviews.extend([review for review in pr_reviews if review['user']['login'] == contributor_login])
        
        return reviews

    async def get_paginated_data(self, url: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        await self.ensure_session()
        if params is None:
            params = {}
        
        all_data = []
        page = 1
        while True:
            params['page'] = page
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if not data:
                        break
                    all_data.extend(data)
                    if len(data) < params.get('per_page', 30):
                        break
                    page += 1
                else:
                    logger.error(f"Error fetching data from {url}: {response.status}")
                    break
        return all_data