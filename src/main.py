import asyncio
import logging
import argparse
import json
from github_client import GitHubClient
from firestore_client import FirestoreClient
from metrics_collector import MetricsCollector
import os
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

async def process_organization(org_name: str, github_token: str, firestore_credentials: str):
    github_client = None
    firestore_client = None
    try:
        # Parse ignored users from environment variable
        ignored_users_str = os.getenv("GITHUB_IGNORED_USERS", "gregv")
        ignored_users = set(user.strip() for user in ignored_users_str.split(",") if user.strip())
        
        github_client = GitHubClient(github_token, ignored_users)
        firestore_client = FirestoreClient(firestore_credentials)
        metrics_collector = MetricsCollector(github_client, firestore_client)

        await metrics_collector.process_organization(org_name)
        
        # Get and print top contributors
        top_contributors = await metrics_collector.get_top_contributors(org_name)
        logger.info(f"Top contributors for {org_name}:")
        for contributor in top_contributors:
            logger.info(f"{contributor['login']}: {contributor.get('commits', 0)} commits, {contributor.get('pull_requests', {}).get('total', 0)} PRs")
        
        # Get and print achievements
        achievements = await metrics_collector.get_achievements(org_name)
        logger.info(f"Achievements for {org_name}:")
        for achievement in achievements:
            person = achievement.get('person', {})
            logger.info(f"{achievement['title']}: {person.get('name')} ({person.get('githubUsername')}) - {achievement['value']}")
    
    except Exception as e:
        logger.error(f"Error processing organization {org_name}: {str(e)}")
    finally:
        if github_client:
            await github_client.close()
        if firestore_client:
            await firestore_client.close()

async def get_achievements(org_name: str, github_token: str, firestore_credentials: str, output_file: str = None):
    github_client = None
    firestore_client = None
    try:
        # Parse ignored users from environment variable
        ignored_users_str = os.getenv("GITHUB_IGNORED_USERS", "gregv")
        ignored_users = set(user.strip() for user in ignored_users_str.split(",") if user.strip())
        
        github_client = GitHubClient(github_token, ignored_users)
        firestore_client = FirestoreClient(firestore_credentials)
        metrics_collector = MetricsCollector(github_client, firestore_client)
        
        # Get achievements
        achievements = await metrics_collector.get_achievements(org_name)
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(achievements, f, indent=2)
            logger.info(f"Achievements saved to {output_file}")
        else:
            # Print achievements
            logger.info(f"Achievements for {org_name}:")
            for achievement in achievements:
                person = achievement.get('person', {})
                logger.info(f"{achievement['title']}: {person.get('name')} ({person.get('githubUsername')}) - {achievement['value']}")
        
        return achievements
    
    except Exception as e:
        logger.error(f"Error getting achievements for {org_name}: {str(e)}")
        return []
    finally:
        if github_client:
            await github_client.close()
        if firestore_client:
            await firestore_client.close()

async def main():
    parser = argparse.ArgumentParser(description="GitHub Organization Stats Collector")
    parser.add_argument("org_names", nargs="+", help="Names of the GitHub organizations to process")
    parser.add_argument("--achievements-only", action="store_true", help="Only retrieve achievements without processing organization")
    parser.add_argument("--output", help="Output file for achievements (JSON format)")
    args = parser.parse_args()

    github_token = os.getenv("GITHUB_TOKEN")
    firestore_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

    if not github_token:
        logger.error("GITHUB_TOKEN environment variable is not set")
        return
    
    if not firestore_credentials:
        logger.error("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set")
        return

    if args.achievements_only:
        tasks = [get_achievements(org_name, github_token, firestore_credentials, args.output) for org_name in args.org_names]
    else:
        tasks = [process_organization(org_name, github_token, firestore_credentials) for org_name in args.org_names]
    
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())