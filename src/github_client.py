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
            "reviews": 0
        }

        # Fetch commit stats
        commits_url = f"{self.base_url}/repos/{repo_full_name}/commits"
        commits = await self.get_paginated_data(commits_url, params={"author": contributor_login, "per_page": 100})
        stats["commits"] = len(commits)

        for commit in commits:
            if "stats" in commit:
                stats["additions"] += commit["stats"].get("additions", 0)
                stats["deletions"] += commit["stats"].get("deletions", 0)

        # Fetch PR stats
        prs_url = f"{self.base_url}/repos/{repo_full_name}/pulls"
        prs = await self.get_paginated_data(prs_url, params={"state": "all", "creator": contributor_login, "per_page": 100})
        stats["pull_requests"]["total"] = len(prs)
        stats["pull_requests"]["open"] = sum(1 for pr in prs if pr["state"] == "open")
        stats["pull_requests"]["closed"] = sum(1 for pr in prs if pr["state"] == "closed" and not pr["merged_at"])
        stats["pull_requests"]["merged"] = sum(1 for pr in prs if pr["merged_at"])

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