from google.cloud import firestore
from google.oauth2 import service_account
from google.api_core import retry
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class FirestoreClient:
    def __init__(self, credentials_json: str):
        try:
            credentials_dict = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(credentials_dict)
            self.db = firestore.AsyncClient(credentials=credentials)
            self.orgs_collection = self.db.collection('github_organizations')
            logger.info("Firestore client initialized successfully")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding credentials JSON: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error initializing Firestore client: {str(e)}")
            raise

    @retry.Retry()
    async def save_contributor_stats(self, org_name: str, repo_name: str, contributor_login: str, stats: Dict[str, Any]) -> None:
        if not self.db:
            raise ValueError("Firestore client is not initialized")
        
        org_doc_ref = self.orgs_collection.document(org_name)
        repo_collection_ref = org_doc_ref.collection('github_repositories')
        repo_doc_ref = repo_collection_ref.document(repo_name)
        contributor_collection_ref = repo_doc_ref.collection('github_contributors')
        contributor_doc_ref = contributor_collection_ref.document(contributor_login)

        logger.info(f"Saving stats for {contributor_login} in {org_name}/{repo_name}")
        stats['timestamp'] = firestore.SERVER_TIMESTAMP
        stats['login'] = contributor_login
        
        try:
            # Ensure the organization document exists
            await org_doc_ref.set({'name': org_name}, merge=True)
            
            # Ensure the repository document exists
            await repo_doc_ref.set({'name': repo_name}, merge=True)
            
            # Save the contributor stats
            await contributor_doc_ref.set(stats, merge=True)
            
            logger.info(f"Saved stats for {contributor_login} in {org_name}/{repo_name}: {stats}")
        except Exception as e:
            logger.error(f"Error saving stats for {contributor_login} in {org_name}/{repo_name}: {str(e)}")
            raise

    @retry.Retry()
    async def get_org_contributors(self, org_name: str) -> List[Dict[str, Any]]:
        if not self.db:
            raise ValueError("Firestore client is not initialized")
        
        org_doc_ref = self.orgs_collection.document(org_name)
        repo_collection_ref = org_doc_ref.collection('github_repositories')
        
        try:
            repos = await repo_collection_ref.get()
            all_contributors = []
            
            for repo in repos:
                contributor_collection_ref = repo.reference.collection('github_contributors')
                contributors = await contributor_collection_ref.get()
                all_contributors.extend([doc.to_dict() for doc in contributors])
            
            return all_contributors
        except Exception as e:
            logger.error(f"Error retrieving contributors for organization {org_name}: {str(e)}")
            raise
            
    @retry.Retry()
    async def get_org_repositories(self, org_name: str) -> List[Dict[str, Any]]:
        """Get all repositories for an organization."""
        if not self.db:
            raise ValueError("Firestore client is not initialized")
        
        org_doc_ref = self.orgs_collection.document(org_name)
        repo_collection_ref = org_doc_ref.collection('github_repositories')
        
        try:
            repos = await repo_collection_ref.get()
            return [repo.to_dict() for repo in repos]
        except Exception as e:
            logger.error(f"Error retrieving repositories for organization {org_name}: {str(e)}")
            raise
            
    @retry.Retry()
    async def save_achievements(self, org_name: str, achievements: List[Dict[str, Any]]) -> None:
        """Save achievements for an organization."""
        if not self.db:
            raise ValueError("Firestore client is not initialized")
        
        org_doc_ref = self.orgs_collection.document(org_name)
        achievements_collection_ref = org_doc_ref.collection('achievements')
        
        logger.info(f"Saving {len(achievements)} achievements for {org_name}")
        
        try:
            # First delete existing achievements
            existing_achievements = await achievements_collection_ref.get()
            for achievement in existing_achievements:
                await achievement.reference.delete()
                
            # Then save the new achievements
            for i, achievement in enumerate(achievements):
                achievement_id = f"{achievement['title']}_{i}".replace(" ", "_").lower()
                achievement_doc_ref = achievements_collection_ref.document(achievement_id)
                achievement['timestamp'] = firestore.SERVER_TIMESTAMP
                achievement['org_name'] = org_name
                await achievement_doc_ref.set(achievement)
                
            logger.info(f"Successfully saved {len(achievements)} achievements for {org_name}")
        except Exception as e:
            logger.error(f"Error saving achievements for {org_name}: {str(e)}")
            raise
            
    @retry.Retry()
    async def get_achievements(self, org_name: str) -> List[Dict[str, Any]]:
        """Get all achievements for an organization."""
        if not self.db:
            raise ValueError("Firestore client is not initialized")
        
        org_doc_ref = self.orgs_collection.document(org_name)
        achievements_collection_ref = org_doc_ref.collection('achievements')
        
        try:
            achievements = await achievements_collection_ref.get()
            return [achievement.to_dict() for achievement in achievements]
        except Exception as e:
            logger.error(f"Error retrieving achievements for organization {org_name}: {str(e)}")
            raise

    async def close(self):
        if self.db:
            try:
                self.db.close()
                logger.info("Firestore client closed successfully")
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(f"Error closing Firestore client: {str(e)}")
        else:
            logger.warning("Attempted to close Firestore client, but it was not initialized")
                