import json
import logging
import httpx

from app.agents.base import Publisher
from app.config import Settings


log = logging.getLogger("linkedin_agent")


class LinkedInPublisher:
    """Publishes posts to LinkedIn using the UGC or Posts API."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.access_token = settings.linkedin_access_token
        # The member id is usually fetched via /v2/me, but we assume it's in the DB or settings for this example.
        # If not provided, we could fetch it dynamically.
        self.api_version = settings.linkedin_api_version or "202401"
        self.base_url = "https://api.linkedin.com"

    def publish(self, text: str, run_id: str) -> str:
        """Publishes a text post to LinkedIn."""
        if not self.access_token:
            raise ValueError("LINKEDIN_ACCESS_TOKEN is missing from settings.")
            
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": self.api_version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json"
        }
        
        # 1. Fetch author URN
        with httpx.Client() as client:
            me_resp = client.get(f"{self.base_url}/v2/userinfo", headers=headers)
            if not me_resp.is_success:
                raise RuntimeError(f"Failed to fetch LinkedIn profile: {me_resp.text}")
            
            # Using userinfo endpoint, the sub is the member ID
            author_urn = f"urn:li:person:{me_resp.json().get('sub')}"
            
            # 2. Publish post using the Posts API
            post_payload = {
                "author": author_urn,
                "commentary": text,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": []
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False
            }
            
            resp = client.post(
                f"{self.base_url}/rest/posts",
                headers=headers,
                json=post_payload
            )
            
            if not resp.is_success:
                raise RuntimeError(f"Failed to publish post: {resp.text}")
                
            post_id = resp.headers.get("x-restli-id")
            if not post_id:
                raise RuntimeError("Post published but no ID returned.")
                
            log.info(f"Successfully published LinkedIn post: {post_id}")
            return post_id
