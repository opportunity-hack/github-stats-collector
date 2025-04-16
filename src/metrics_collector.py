import logging
from typing import Dict, Any, List
from github_client import GitHubClient
from firestore_client import FirestoreClient
from achievements_generator import AchievementsGenerator

logger = logging.getLogger(__name__)

class MetricsCollector:
    def __init__(self, github_client: GitHubClient, firestore_client: FirestoreClient):
        self.github_client = github_client
        self.firestore_client = firestore_client
        self.achievements_generator = AchievementsGenerator()
        logger.info("MetricsCollector initialized")

    async def process_organization(self, org_name: str) -> None:
        logger.info(f"Starting to process organization: '{org_name}'")
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
                            # Print stack trace
                            import traceback
                            logger.error(traceback.format_exc())
                            logger.error(f"Error processing contributor {contributor_login} for {org_name}/{repo_name}: {str(e)}")                            
                except Exception as e:
                    logger.error(f"Error processing repository {org_name}/{repo_name}: {str(e)}")
            
            # Generate and save achievements after processing all repositories
            await self.generate_achievements(org_name)
                
            logger.info(f"Finished processing organization: {org_name}")
        except Exception as e:
            logger.error(f"Error processing organization {org_name}: {str(e)}")
            raise  # Re-raise the exception to be caught by the caller

    async def get_top_contributors(self, org_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            contributors = await self.firestore_client.get_org_contributors(org_name)
            sorted_contributors = sorted(contributors, key=lambda x: x.get('commits', 0) + x.get('pull_requests', {}).get('total', 0), reverse=True)
            return sorted_contributors[:limit]
        except Exception as e:
            logger.error(f"Error getting top contributors for {org_name}: {str(e)}")
            return []
            
    async def generate_achievements(self, org_name: str) -> List[Dict[str, Any]]:
        """Generate achievements for an organization and save them to Firestore."""
        logger.info(f"Generating achievements for organization: {org_name}")
        try:
            # Get all contributors data
            contributors = await self.firestore_client.get_org_contributors(org_name)
            logger.info(f"Found {len(contributors)} contributors for {org_name}")
            
            # Get all repositories data
            repositories = await self.firestore_client.get_org_repositories(org_name)
            logger.info(f"Found {len(repositories)} repositories for {org_name}")
            
            # Generate achievements
            achievements = self.achievements_generator.generate_achievements(org_name, repositories, contributors)
            logger.info(f"Generated {len(achievements)} achievements for {org_name}")
            
            # Save achievements to Firestore
            if achievements:
                await self.firestore_client.save_achievements(org_name, achievements)
                logger.info(f"Saved {len(achievements)} achievements for {org_name}")
            
            return achievements
        except Exception as e:
            logger.error(f"Error generating achievements for {org_name}: {str(e)}")
            return []
            
    async def get_achievements(self, org_name: str) -> List[Dict[str, Any]]:
        """Get all achievements for an organization."""
        try:
            achievements = await self.firestore_client.get_achievements(org_name)
            return achievements
        except Exception as e:
            logger.error(f"Error retrieving achievements for {org_name}: {str(e)}")
            return []