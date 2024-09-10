from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import logging
from typing import Dict, Any, List, Optional
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

class FirestoreClient:
    def __init__(self, credentials_dict):
        self.db = firestore.AsyncClient.from_service_account_info(credentials_dict)
        self.contributor_collection = self.db.collection('github_contributors')
        self.repo_collection = self.db.collection('github_repositories')

    async def save_contributor_stats(self, org_name: str, repo_name: str, contributor_login: str, stats: Dict[str, Any]) -> None:
        """Save contributor statistics to Firestore."""
        doc_ref = self.contributor_collection.document(f"{org_name}_{repo_name}_{contributor_login}")
        stats['timestamp'] = firestore.SERVER_TIMESTAMP
        stats['org_name'] = org_name
        stats['repo_name'] = repo_name
        try:
            await doc_ref.set(stats, merge=True)
            logger.info(f"Saved stats for {contributor_login} in {org_name}/{repo_name}")
        except Exception as e:
            logger.error(f"Error saving stats for {contributor_login} in {org_name}/{repo_name}: {str(e)}")

    async def get_org_contributors(self, org_name: str) -> List[Dict[str, Any]]:
        """Retrieve statistics for all contributors in an organization."""
        query = self.contributor_collection.where(filter=FieldFilter("org_name", "==", org_name))
        try:
            docs = await query.get()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error retrieving contributors for organization {org_name}: {str(e)}")
            return []

    async def get_repo_contributors(self, org_name: str, repo_name: str) -> List[Dict[str, Any]]:
        """Retrieve statistics for all contributors in a specific repository."""
        query = self.contributor_collection.where(filter=FieldFilter("org_name", "==", org_name)).where(filter=FieldFilter("repo_name", "==", repo_name))
        try:
            docs = await query.get()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error retrieving contributors for repository {org_name}/{repo_name}: {str(e)}")
            return []

    async def get_contributor_stats(self, org_name: str, repo_name: str, contributor_login: str) -> Dict[str, Any]:
        """Retrieve statistics for a specific contributor in a specific repository."""
        doc_ref = self.contributor_collection.document(f"{org_name}_{repo_name}_{contributor_login}")
        try:
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            else:
                logger.warning(f"No stats found for {contributor_login} in {org_name}/{repo_name}")
                return {}
        except Exception as e:
            logger.error(f"Error retrieving stats for {contributor_login} in {org_name}/{repo_name}: {str(e)}")
            return {}

    async def save_repo_stats(self, org_name: str, repo_name: str, stats: Dict[str, Any]) -> None:
        """Save repository statistics to Firestore."""
        doc_ref = self.repo_collection.document(f"{org_name}_{repo_name}")
        stats['timestamp'] = firestore.SERVER_TIMESTAMP
        stats['org_name'] = org_name
        stats['repo_name'] = repo_name
        try:
            await doc_ref.set(stats, merge=True)
            logger.info(f"Saved stats for {org_name}/{repo_name}")
        except Exception as e:
            logger.error(f"Error saving stats for {org_name}/{repo_name}: {str(e)}")

    async def get_repo_stats(self, org_name: str, repo_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve the latest statistics for a specific repository."""
        doc_ref = self.repo_collection.document(f"{org_name}_{repo_name}")
        try:
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            else:
                logger.warning(f"No stats found for {org_name}/{repo_name}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving stats for {org_name}/{repo_name}: {str(e)}")
            return None

    async def get_org_repos(self, org_name: str) -> List[Dict[str, Any]]:
        """Retrieve statistics for all repositories in an organization."""
        query = self.repo_collection.where(filter=FieldFilter("org_name", "==", org_name))
        try:
            docs = await query.get()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error retrieving stats for organization {org_name}: {str(e)}")
            return []

    async def get_all_stats(self) -> List[Dict[str, Any]]:
        """Retrieve statistics for all repositories and contributors."""
        try:
            repo_docs = await self.repo_collection.get()
            contributor_docs = await self.contributor_collection.get()
            return [doc.to_dict() for doc in repo_docs] + [doc.to_dict() for doc in contributor_docs]
        except Exception as e:
            logger.error(f"Error retrieving all stats: {str(e)}")
            return []

    async def delete_repo_stats(self, org_name: str, repo_name: str) -> None:
        """Delete statistics for a specific repository."""
        doc_ref = self.repo_collection.document(f"{org_name}_{repo_name}")
        try:
            await doc_ref.delete()
            logger.info(f"Deleted stats for {org_name}/{repo_name}")
        except Exception as e:
            logger.error(f"Error deleting stats for {org_name}/{repo_name}: {str(e)}")

    async def delete_contributor_stats(self, org_name: str, repo_name: str, contributor_login: str) -> None:
        """Delete statistics for a specific contributor in a repository."""
        doc_ref = self.contributor_collection.document(f"{org_name}_{repo_name}_{contributor_login}")
        try:
            await doc_ref.delete()
            logger.info(f"Deleted stats for {contributor_login} in {org_name}/{repo_name}")
        except Exception as e:
            logger.error(f"Error deleting stats for {contributor_login} in {org_name}/{repo_name}: {str(e)}")