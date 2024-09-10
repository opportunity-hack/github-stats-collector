import asyncio
import logging
from config import load_config
from github_client import GitHubClient
from firestore_client import FirestoreClient
from metrics_collector import MetricsCollector

# Set up logging
#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


async def main():
    try:
        # Load configuration
        config = load_config()
        logger.info("Configuration loaded successfully")

        # Initialize clients
        async with GitHubClient(config.github_token, recent_activity_count=5) as github_client:
            firestore_client = FirestoreClient(config.google_credentials)
            collector = MetricsCollector(github_client, firestore_client)

            # Process each organization
            for org_name in config.github_orgs.split(','):
                logger.info(f"Starting to process organization: {org_name}")
                await collector.process_organization(org_name)

                # Get and print top contributors
                top_contributors = await collector.get_top_contributors(org_name)
                logger.info(f"Top contributors for {org_name}:")
                for contributor in top_contributors:
                    logger.info(f"{contributor['login']}: {contributor['contribution_score']}")

    except Exception as e:
        logger.error(f"An error occurred in the main process: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())