import asyncio
import logging
import schedule
from typing import List

from config import load_config
from github_client import GitHubClient
from firestore_client import FirestoreClient
from metrics_collector import MetricsCollector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, github_token: str, google_credentials: dict, organizations: List[str], 
                 recent_activity_count: int = 5, collection_interval: str = 'daily', collection_time: str = '00:00'):
        self.github_token = github_token
        self.google_credentials = google_credentials
        self.organizations = organizations
        self.recent_activity_count = recent_activity_count
        self.collection_interval = collection_interval.lower()
        self.collection_time = collection_time
        self.github_client = None
        self.firestore_client = None
        self.metrics_collector = None
        self.loop = asyncio.get_event_loop()

    async def setup(self):
        """Set up the clients and collector."""
        self.github_client = GitHubClient(self.github_token, self.recent_activity_count)
        self.firestore_client = FirestoreClient(self.google_credentials)
        self.metrics_collector = MetricsCollector(self.github_client, self.firestore_client)

    async def cleanup(self):
        """Clean up resources."""
        if self.github_client:
            await self.github_client.close()

    async def collect_metrics(self):
        """Collect metrics for all organizations."""
        logger.info("Starting metrics collection...")
        for org in self.organizations:
            try:
                await self.metrics_collector.process_organization(org)
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
        self.loop.run_until_complete(self.run_collection())

    def run(self):
        """Run the scheduler."""
        logger.info("Starting scheduler...")
        self.schedule_job()
        while True:
            schedule.run_pending()
            self.loop.run_until_complete(asyncio.sleep(1))

def main():
    config = load_config()
    organizations = config.github_orgs.split(',')
    scheduler = Scheduler(
        github_token=config.github_token,
        google_credentials=config.google_credentials,
        organizations=organizations,
        recent_activity_count=config.recent_activity_count,
        collection_interval=config.collection_interval,
        collection_time=config.collection_time
    )
    
    # Run the scheduler
    scheduler.run()

if __name__ == "__main__":
    main()