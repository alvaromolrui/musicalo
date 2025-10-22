"""
ListenBrainz API client for listening statistics and scrobbling data.
Provides access to user listening history and statistics.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import httpx
from loguru import logger

from src.config import settings


class ListenBrainzClient:
    """Client for interacting with ListenBrainz API."""
    
    def __init__(self):
        self.base_url = "https://api.listenbrainz.org"
        self.username = settings.listenbrainz_username
        self.token = settings.listenbrainz_token
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for authenticated requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MusicAssistant/2.0.0"
        }
        
        if self.token:
            headers["Authorization"] = f"Token {self.token}"
        
        return headers
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make authenticated request to ListenBrainz API."""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data.get("status") == "ok":
                error_msg = data.get("error", "Unknown error")
                raise Exception(f"ListenBrainz API error: {error_msg}")
            
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling ListenBrainz API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling ListenBrainz API: {e}")
            raise
    
    async def get_user_listens(self, username: Optional[str] = None, 
                             count: int = 25, max_ts: Optional[int] = None,
                             min_ts: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent listens for a user."""
        try:
            user = username or self.username
            if not user:
                raise ValueError("No username provided")
            
            params = {"count": count}
            if max_ts:
                params["max_ts"] = max_ts
            if min_ts:
                params["min_ts"] = min_ts
            
            response = await self._make_request(f"/1/user/{user}/listens", params)
            listens = response.get("payload", {}).get("listens", [])
            
            return listens
            
        except Exception as e:
            logger.error(f"Failed to get listens for {username or self.username}: {e}")
            return []
    
    async def get_user_stats(self, username: Optional[str] = None) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            user = username or self.username
            if not user:
                raise ValueError("No username provided")
            
            response = await self._make_request(f"/1/stats/user/{user}/listening-activity")
            stats = response.get("payload", {})
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats for {username or self.username}: {e}")
            return {}
    
    async def get_user_artists(self, username: Optional[str] = None, 
                              range: str = "week", count: int = 25) -> List[Dict[str, Any]]:
        """Get top artists for a user."""
        try:
            user = username or self.username
            if not user:
                raise ValueError("No username provided")
            
            params = {"range": range, "count": count}
            response = await self._make_request(f"/1/stats/user/{user}/artists", params)
            artists = response.get("payload", {}).get("artists", [])
            
            return artists
            
        except Exception as e:
            logger.error(f"Failed to get artists for {username or self.username}: {e}")
            return []
    
    async def get_user_releases(self, username: Optional[str] = None,
                               range: str = "week", count: int = 25) -> List[Dict[str, Any]]:
        """Get top releases for a user."""
        try:
            user = username or self.username
            if not user:
                raise ValueError("No username provided")
            
            params = {"range": range, "count": count}
            response = await self._make_request(f"/1/stats/user/{user}/releases", params)
            releases = response.get("payload", {}).get("releases", [])
            
            return releases
            
        except Exception as e:
            logger.error(f"Failed to get releases for {username or self.username}: {e}")
            return []
    
    async def get_user_recordings(self, username: Optional[str] = None,
                                 range: str = "week", count: int = 25) -> List[Dict[str, Any]]:
        """Get top recordings for a user."""
        try:
            user = username or self.username
            if not user:
                raise ValueError("No username provided")
            
            params = {"range": range, "count": count}
            response = await self._make_request(f"/1/stats/user/{user}/recordings", params)
            recordings = response.get("payload", {}).get("recordings", [])
            
            return recordings
            
        except Exception as e:
            logger.error(f"Failed to get recordings for {username or self.username}: {e}")
            return []
    
    async def get_recent_listens(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent listens from the last N hours."""
        try:
            # Calculate timestamp for N hours ago
            min_ts = int((datetime.now() - timedelta(hours=hours)).timestamp())
            
            listens = await self.get_user_listens(min_ts=min_ts, count=1000)
            return listens
            
        except Exception as e:
            logger.error(f"Failed to get recent listens: {e}")
            return []
    
    async def get_weekly_stats(self) -> Dict[str, Any]:
        """Get weekly listening statistics."""
        try:
            stats = await self.get_user_stats()
            artists = await self.get_user_artists(range="week", count=50)
            releases = await self.get_user_releases(range="week", count=50)
            recordings = await self.get_user_recordings(range="week", count=50)
            
            return {
                "stats": stats,
                "top_artists": artists,
                "top_releases": releases,
                "top_recordings": recordings,
                "period": "week"
            }
            
        except Exception as e:
            logger.error(f"Failed to get weekly stats: {e}")
            return {}
    
    async def get_monthly_stats(self) -> Dict[str, Any]:
        """Get monthly listening statistics."""
        try:
            stats = await self.get_user_stats()
            artists = await self.get_user_artists(range="month", count=50)
            releases = await self.get_user_releases(range="month", count=50)
            recordings = await self.get_user_recordings(range="month", count=50)
            
            return {
                "stats": stats,
                "top_artists": artists,
                "top_releases": releases,
                "top_recordings": recordings,
                "period": "month"
            }
            
        except Exception as e:
            logger.error(f"Failed to get monthly stats: {e}")
            return {}
    
    async def search_listens(self, query: str, count: int = 25) -> List[Dict[str, Any]]:
        """Search through user's listening history."""
        try:
            # Get recent listens and filter by query
            listens = await self.get_user_listens(count=count * 2)  # Get more to filter
            
            # Simple text search in track and artist names
            filtered_listens = []
            query_lower = query.lower()
            
            for listen in listens:
                track_name = listen.get("track_metadata", {}).get("track_name", "").lower()
                artist_name = listen.get("track_metadata", {}).get("artist_name", "").lower()
                release_name = listen.get("track_metadata", {}).get("release_name", "").lower()
                
                if (query_lower in track_name or 
                    query_lower in artist_name or 
                    query_lower in release_name):
                    filtered_listens.append(listen)
                    
                    if len(filtered_listens) >= count:
                        break
            
            return filtered_listens
            
        except Exception as e:
            logger.error(f"Failed to search listens for '{query}': {e}")
            return []
    
    async def get_listening_activity(self, days: int = 30) -> Dict[str, Any]:
        """Get listening activity over the last N days."""
        try:
            response = await self._make_request(f"/1/stats/user/{self.username}/listening-activity")
            activity = response.get("payload", {})
            
            return activity
            
        except Exception as e:
            logger.error(f"Failed to get listening activity: {e}")
            return {}
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global client instance
_listenbrainz_client: Optional[ListenBrainzClient] = None


async def get_listenbrainz_client() -> ListenBrainzClient:
    """Get or create ListenBrainz client instance."""
    global _listenbrainz_client
    if _listenbrainz_client is None:
        _listenbrainz_client = ListenBrainzClient()
    return _listenbrainz_client


async def close_listenbrainz_client():
    """Close the global ListenBrainz client."""
    global _listenbrainz_client
    if _listenbrainz_client:
        await _listenbrainz_client.close()
        _listenbrainz_client = None
