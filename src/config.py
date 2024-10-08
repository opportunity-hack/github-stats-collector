import os
import json
from dotenv import load_dotenv
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class Config:
    github_token: str
    github_orgs: str
    google_credentials: dict
    collection_interval: str
    collection_time: str

def load_config() -> Config:
    """Load configuration from environment variables."""
    load_dotenv()  # This loads the variables from .env file

    github_token = os.getenv('GITHUB_TOKEN')
    github_orgs = os.getenv('GITHUB_ORGS')
    google_credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')

    if not github_token:
        raise ValueError("GITHUB_TOKEN environment variable is not set")
    if not github_orgs:
        raise ValueError("GITHUB_ORGS environment variable is not set")
    if not google_credentials_json:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable is not set")

    try:
        google_credentials = json.loads(google_credentials_json)
    except json.JSONDecodeError:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS_JSON is not valid JSON")

    return Config(
        github_token=github_token,
        github_orgs=github_orgs,
        google_credentials=google_credentials,
        collection_interval=os.getenv('COLLECTION_INTERVAL', 'daily'),
        collection_time=os.getenv('COLLECTION_TIME', '00:00')
    )

# Usage example
if __name__ == "__main__":
    try:
        config = load_config()
        print("Configuration loaded successfully:")
        print(f"GitHub Organizations: {config.github_orgs}")
        print(f"Collection Interval: {config.collection_interval}")
        print(f"Collection Time: {config.collection_time}")
    except Exception as e:
        print(f"Error loading configuration: {str(e)}")