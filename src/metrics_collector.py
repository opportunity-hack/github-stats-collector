import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime

from github_client import GitHubClient
from firestore_client import FirestoreClient

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self, github_client: GitHubClient, firestore_client: FirestoreClient):
        self.github_client = github_client
        self.firestore_client = firestore_client

    async def collect_contributor_metrics(self, org_name: str, repo, contributor) -> Dict[str, Any]:
        """Collect metrics for a given contributor in a repository."""
        try:
            logger.info(f"Collecting metrics for {contributor.login} in {repo.full_name}")
            stats = await self.github_client.get_contributor_stats(repo, contributor)
            
            # Add additional metrics
            stats['collected_at'] = datetime.utcnow().isoformat()
            stats['org_name'] = org_name
            
            # Calculate derived metrics
            stats['contribution_score'] = self._calculate_contribution_score(stats)
            
            logger.info(f" Collected stats: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error collecting metrics for {contributor.login} in {repo.full_name}: {str(e)}")
            return {}

    async def save_contributor_metrics(self, metrics: Dict[str, Any]) -> None:
        """Save collected contributor metrics to Firestore."""
        if not metrics:
            logger.warning("No metrics to save")
            return
        
        org_name = metrics['org_name']
        repo_name = metrics['repo_name']
        contributor_login = metrics['login']
        await self.firestore_client.save_contributor_stats(org_name, repo_name, contributor_login, metrics)

    def _calculate_contribution_score(self, stats: Dict[str, Any]) -> float:
        """Calculate a contribution score based on various activities."""
        commit_weight = 0.4
        pr_weight = 0.3
        issue_weight = 0.15
        review_weight = 0.15
        
        commit_score = min(stats['commit_count'] / 100, 1) * commit_weight
        pr_score = min(stats['pr_count'] / 50, 1) * pr_weight
        issue_score = min(stats['issue_count'] / 20, 1) * issue_weight
        review_score = min(stats['review_count'] / 30, 1) * review_weight
        
        return round(commit_score + pr_score + issue_score + review_score, 2)

    async def process_organization(self, org_name: str) -> None:
        """Process all repositories and contributors for a given organization."""
        try:
            repos = await self.github_client.get_organization_repos(org_name)
            logger.info(f"Found {len(repos)} repositories for {org_name}")
            
            for repo in repos:
                contributors = await self.github_client.get_repo_contributors(repo)
                logger.info(f"Found {len(contributors)} contributors for {repo.full_name}")
                
                for contributor in contributors:
                    metrics = await self.collect_contributor_metrics(org_name, repo, contributor)
                    await self.save_contributor_metrics(metrics)
                
            logger.info(f"Finished processing organization: {org_name}")
        except Exception as e:
            logger.error(f"Error processing organization {org_name}: {str(e)}")

    async def get_top_contributors(self, org_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top contributors across all repositories in an organization."""
        contributors = await self.firestore_client.get_org_contributors(org_name)
        sorted_contributors = sorted(contributors, key=lambda x: x['contribution_score'], reverse=True)
        return sorted_contributors[:limit]