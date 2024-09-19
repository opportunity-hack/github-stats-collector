import logging
from typing import Dict, Any, List
from github_client import GitHubClient
from firestore_client import FirestoreClient

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self, github_client: GitHubClient, firestore_client: FirestoreClient):
        self.github_client = github_client
        self.firestore_client = firestore_client
        logger.info("MetricsCollector initialized")

    async def process_organization(self, org_name: str) -> None:
        logger.info(f"Starting to process organization: {org_name}")
        try:
            repos = await self.github_client.get_organization_repos(org_name)
            logger.info(f"Found {len(repos)} repositories for {org_name}")
            
            for repo in repos:
                repo_name = repo['name']
                logger.info(f"Processing repository: {org_name}/{repo_name}")
                try:
                    contributors = await self.github_client.get_repo_contributors(repo['full_name'])
                    logger.info(f"Found {len(contributors)} contributors for {org_name}/{repo_name}")
                    
                    for contributor in contributors:
                        contributor_login = contributor['login']
                        try:
                            logger.info(f"Processing contributor: {contributor_login} for {org_name}/{repo_name}")
                            metrics = await self.github_client.get_contributor_stats(org_name, repo_name, contributor_login)
                            if metrics:
                                await self.firestore_client.save_contributor_stats(org_name, repo_name, contributor_login, metrics)
                                logger.info(f"Saved metrics for {contributor_login} in {org_name}/{repo_name}")
                            else:
                                logger.warning(f"No metrics found for {contributor_login} in {org_name}/{repo_name}")
                        except Exception as e:
                            logger.error(f"Error processing contributor {contributor_login} for {org_name}/{repo_name}: {str(e)}")
                except Exception as e:
                    logger.error(f"Error processing repository {org_name}/{repo_name}: {str(e)}")
                
            logger.info(f"Finished processing organization: {org_name}")
        except Exception as e:
            logger.error(f"Error processing organization {org_name}: {str(e)}")
            raise  # Re-raise the exception to be caught by the caller

    async def get_top_contributors(self, org_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            contributors = await self.firestore_client.get_org_contributors(org_name)
            sorted_contributors = sorted(contributors, key=lambda x: x.get('total_commits', 0) + x.get('total_prs', 0), reverse=True)
            return sorted_contributors[:limit]
        except Exception as e:
            logger.error(f"Error getting top contributors for {org_name}: {str(e)}")
            return []