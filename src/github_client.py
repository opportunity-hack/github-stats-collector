import asyncio
from typing import List, Dict, Any
from github import Github
from github.Repository import Repository
from github.NamedUser import NamedUser
import aiohttp
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self, token: str, recent_activity_count: int = 5):
        self.github = Github(token)
        self.session = aiohttp.ClientSession(headers={"Authorization": f"token {token}"})
        self.recent_activity_count = recent_activity_count

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def close(self):
        await self.session.close()

    async def get_organization_repos(self, org_name: str) -> List[Repository]:
        """Fetch all repositories for a given organization."""
        org = self.github.get_organization(org_name)
        repos = org.get_repos()
        return [repo async for repo in self._aiter_paginated(repos)]

    async def get_repo_contributors(self, repo: Repository) -> List[NamedUser]:
        """Fetch all contributors for a given repository."""
        contributors = repo.get_contributors()
        return [contributor async for contributor in self._aiter_paginated(contributors)]

    async def get_contributor_stats(self, repo: Repository, contributor: NamedUser) -> Dict[str, Any]:
        """Fetch statistics and recent activity for a given contributor in a repository."""
        stats = {
            "login": contributor.login,
            "name": contributor.name,
            "repo_name": repo.name,
            "repo_full_name": repo.full_name,
        }

        # Fetch counts and recent activity asynchronously
        tasks = [
            self._fetch_commit_data(repo, contributor),
            self._fetch_pr_data(repo, contributor),
            self._fetch_issue_data(repo, contributor),
            self._fetch_review_data(repo, contributor),
        ]
        commit_data, pr_data, issue_data, review_data = await asyncio.gather(*tasks)

        stats.update({
            "commit_count": commit_data["count"],
            "pr_count": pr_data["count"],
            "issue_count": issue_data["count"],
            "review_count": review_data["count"],
            "recent_commits": commit_data["recent"],
            "recent_prs": pr_data["recent"],
            "recent_issues": issue_data["recent"],
            "recent_reviews": review_data["recent"],
        })

        logger.debug(f"Fetched stats for {contributor.login} in {repo.full_name}: {stats}")
        return stats

    async def _aiter_paginated(self, paginated):
        """Asynchronous iterator for PaginatedList."""
        for item in paginated:
            yield item
            await asyncio.sleep(0)  # Allow other coroutines to run

    def _parse_link_header(self, link_header: str) -> int:
        """Parse the Link header to get the total count."""
        if not link_header:
            return 0
        match = re.search(r'page=(\d+)>; rel="last"', link_header)
        if match:
            return int(match.group(1))
        return 0

    async def _fetch_data(self, url: str, params: Dict[str, Any], entity_type: str, repo: Repository, contributor: NamedUser) -> Dict[str, Any]:
        """Generic method to fetch count and recent activity for different entities."""
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                total_count = response.headers.get("X-Total-Count")
                if total_count:
                    count = int(total_count)
                else:
                    count = self._parse_link_header(response.headers.get("Link", ""))
                
                data = await response.json()
                recent = [self._format_activity(item, entity_type) for item in data[:self.recent_activity_count]]
                
                logger.debug(f"{entity_type.capitalize()} data for {contributor.login} in {repo.full_name}: count={count}, recent={len(recent)}")
                return {"count": count, "recent": recent}
            else:
                logger.error(f"Failed to fetch {entity_type} data for {contributor.login} in {repo.full_name}: {response.status}")
                return {"count": 0, "recent": []}

    def _format_activity(self, item: Dict[str, Any], entity_type: str) -> Dict[str, Any]:
        """Format the activity data based on the entity type."""
        if entity_type == "commit":
            return {
                "sha": item["sha"],
                "message": item["commit"]["message"],
                "url": item["html_url"],
                "date": item["commit"]["author"]["date"],
            }
        elif entity_type in ["pr", "issue"]:
            return {
                "number": item["number"],
                "title": item["title"],
                "url": item["html_url"],
                "state": item["state"],
                "created_at": item["created_at"],
            }
        elif entity_type == "review":
            return {
                "id": item["id"],
                "state": item["state"],
                "body": item.get("body", ""),
                "url": item["html_url"],
                "submitted_at": item["submitted_at"],
                "pr_number": item["pull_request_url"].split("/")[-1],
            }
        return item

    async def _fetch_commit_data(self, repo: Repository, contributor: NamedUser) -> Dict[str, Any]:
        """Fetch the total number of commits and recent commits for a contributor in a repository."""
        url = f"https://api.github.com/repos/{repo.full_name}/commits"
        params = {"author": contributor.login, "per_page": self.recent_activity_count}
        return await self._fetch_data(url, params, "commit", repo, contributor)

    async def _fetch_pr_data(self, repo: Repository, contributor: NamedUser) -> Dict[str, Any]:
        """Fetch the total number of pull requests and recent PRs for a contributor in a repository."""
        url = f"https://api.github.com/repos/{repo.full_name}/pulls"
        params = {"state": "all", "creator": contributor.login, "per_page": self.recent_activity_count}
        return await self._fetch_data(url, params, "pr", repo, contributor)

    async def _fetch_issue_data(self, repo: Repository, contributor: NamedUser) -> Dict[str, Any]:
        """Fetch the total number of issues and recent issues for a contributor in a repository."""
        url = f"https://api.github.com/repos/{repo.full_name}/issues"
        params = {"state": "all", "creator": contributor.login, "per_page": self.recent_activity_count}
        return await self._fetch_data(url, params, "issue", repo, contributor)

    async def _fetch_review_data(self, repo: Repository, contributor: NamedUser) -> Dict[str, Any]:
        """Fetch the total number of reviews and recent reviews for a contributor in a repository."""
        url = f"https://api.github.com/repos/{repo.full_name}/pulls"
        params = {"state": "all", "per_page": 100}  # Fetch more PRs to increase chances of finding reviews
        
        all_reviews = []
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                prs = await response.json()
                for pr in prs:
                    review_url = f"https://api.github.com/repos/{repo.full_name}/pulls/{pr['number']}/reviews"
                    async with self.session.get(review_url) as review_response:
                        if review_response.status == 200:
                            reviews = await review_response.json()
                            contributor_reviews = [r for r in reviews if r['user']['login'] == contributor.login]
                            all_reviews.extend(contributor_reviews)
                            if len(all_reviews) >= self.recent_activity_count:
                                break
                
                count = len(all_reviews)
                recent = [self._format_activity(review, "review") for review in all_reviews[:self.recent_activity_count]]
                
                logger.debug(f"Review data for {contributor.login} in {repo.full_name}: count={count}, recent={len(recent)}")
                return {"count": count, "recent": recent}
            else:
                logger.error(f"Failed to fetch review data for {contributor.login} in {repo.full_name}: {response.status}")
                return {"count": 0, "recent": []}