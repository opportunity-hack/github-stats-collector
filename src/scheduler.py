import asyncio
import logging
import argparse
import os
import schedule
import time
from typing import List
from dotenv import load_dotenv

from github_client import GitHubClient
from firestore_client import FirestoreClient
from metrics_collector import MetricsCollector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

load_dotenv()

class Scheduler:
    def __init__(self, github_token: str, firestore_credentials: str, organizations: List[str],
                 collection_interval: str = 'daily', collection_time: str = '00:00'):
        self.github_token = github_token
        self.firestore_credentials = firestore_credentials
        self.organizations = organizations
        self.collection_interval = collection_interval.lower()
        self.collection_time = collection_time
        self.github_client = None
        self.firestore_client = None
        self.metrics_collector = None

    async def setup(self):
        """Set up the clients and collector."""
        self.github_client = GitHubClient(self.github_token)
        self.firestore_client = FirestoreClient(self.firestore_credentials)
        self.metrics_collector = MetricsCollector(self.github_client, self.firestore_client)

    async def cleanup(self):
        """Clean up resources."""
        if self.github_client:
            await self.github_client.close()
        if self.firestore_client:
            await self.firestore_client.close()

    async def collect_metrics(self):
        """Collect metrics for all organizations."""
        logger.info("Starting metrics collection...")
        for org in self.organizations:
            try:
                await self.metrics_collector.process_organization(org)
                top_contributors = await self.metrics_collector.get_top_contributors(org)
                logger.info(f"Top contributors for {org}:")
                for contributor in top_contributors:
                    logger.info(f"{contributor['login']}: {contributor.get('total_commits', 0)} commits, {contributor.get('total_prs', 0)} PRs")
            except Exception as e:
                logger.error(f"Error processing organization {org}: {str(e)}")
        logger.info("Metrics collection completed.")

    async def run_collection(self):
        """Run the collection process."""
        await self.setup()
        try:
            await self.collect_metrics()
        finally:
            await self.cleanup()

    def schedule_job(self):
        """Schedule the metrics collection job based on the collection interval."""
        if self.collection_interval == 'hourly':
            schedule.every().hour.at(self.collection_time[-2:]).do(self.run_collection_wrapper)
            logger.info(f"Scheduled metrics collection to run every hour at {self.collection_time[-2:]} minutes past the hour")
        elif self.collection_interval == 'daily':
            schedule.every().day.at(self.collection_time).do(self.run_collection_wrapper)
            logger.info(f"Scheduled metrics collection to run daily at {self.collection_time}")
        elif self.collection_interval == 'weekly':
            schedule.every().monday.at(self.collection_time).do(self.run_collection_wrapper)
            logger.info(f"Scheduled metrics collection to run every Monday at {self.collection_time}")
        else:
            raise ValueError(f"Unsupported collection interval: {self.collection_interval}")

    def run_collection_wrapper(self):
        """Wrapper to run the collection process in the event loop."""
        asyncio.run(self.run_collection())

    def run(self):
        """Run the scheduler."""
        logger.info("Starting scheduler...")
        self.schedule_job()
        while True:
            schedule.run_pending()
            time.sleep(1)

def main():
    parser = argparse.ArgumentParser(description="GitHub Organization Stats Collector")
    parser.add_argument("org_names", nargs="+", help="Names of the GitHub organizations to process")
    args = parser.parse_args()

    github_token = os.getenv("GITHUB_TOKEN")
    firestore_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    collection_interval = os.getenv("COLLECTION_INTERVAL", "daily")
    collection_time = os.getenv("COLLECTION_TIME", "00:00")

    if not github_token:
        logger.error("GITHUB_TOKEN environment variable is not set")
        return

    if not firestore_credentials:
        logger.error("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set")
        return

    scheduler = Scheduler(
        github_token=github_token,
        firestore_credentials=firestore_credentials,
        organizations=args.org_names,
        collection_interval=collection_interval,
        collection_time=collection_time
    )

    scheduler.run()

if __name__ == "__main__":
    main()