"""
MusicBrainz API client for music metadata and artist information.
Provides access to comprehensive music database for enrichment.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any

import httpx
from loguru import logger

from src.config import settings


class MusicBrainzClient:
    """Client for interacting with MusicBrainz API."""
    
    def __init__(self):
        self.base_url = "https://musicbrainz.org/ws/2"
        self.app_name = "MusicAssistant"
        self.contact_email = "music@assistant.local"  # Default, should be configured
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": f"{self.app_name}/2.0.0 ({self.contact_email})",
                "Accept": "application/json"
            }
        )
        self.rate_limit_delay = 1.0  # 1 second between requests
        self.last_request_time = 0
    
    async def _rate_limit(self):
        """Implement rate limiting for MusicBrainz API."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make rate-limited request to MusicBrainz API."""
        await self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling MusicBrainz API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling MusicBrainz API: {e}")
            raise
    
    async def search_artists(self, query: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Search for artists by name."""
        try:
            params = {
                "query": query,
                "fmt": "json",
                "limit": limit
            }
            
            response = await self._make_request("/artist", params)
            artists = response.get("artists", [])
            
            return artists
            
        except Exception as e:
            logger.error(f"Failed to search artists for '{query}': {e}")
            return []
    
    async def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed artist information by MBID."""
        try:
            params = {
                "inc": "releases+tags+ratings+url-rels",
                "fmt": "json"
            }
            
            response = await self._make_request(f"/artist/{artist_id}", params)
            return response
            
        except Exception as e:
            logger.error(f"Failed to get artist {artist_id}: {e}")
            return None
    
    async def search_releases(self, query: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Search for releases by title or artist."""
        try:
            params = {
                "query": query,
                "fmt": "json",
                "limit": limit
            }
            
            response = await self._make_request("/release", params)
            releases = response.get("releases", [])
            
            return releases
            
        except Exception as e:
            logger.error(f"Failed to search releases for '{query}': {e}")
            return []
    
    async def get_release(self, release_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed release information by MBID."""
        try:
            params = {
                "inc": "artists+recordings+release-groups+tags+ratings+url-rels",
                "fmt": "json"
            }
            
            response = await self._make_request(f"/release/{release_id}", params)
            return response
            
        except Exception as e:
            logger.error(f"Failed to get release {release_id}: {e}")
            return None
    
    async def search_recordings(self, query: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Search for recordings (tracks) by title or artist."""
        try:
            params = {
                "query": query,
                "fmt": "json",
                "limit": limit
            }
            
            response = await self._make_request("/recording", params)
            recordings = response.get("recordings", [])
            
            return recordings
            
        except Exception as e:
            logger.error(f"Failed to search recordings for '{query}': {e}")
            return []
    
    async def get_recording(self, recording_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed recording information by MBID."""
        try:
            params = {
                "inc": "artists+releases+tags+ratings+url-rels",
                "fmt": "json"
            }
            
            response = await self._make_request(f"/recording/{recording_id}", params)
            return response
            
        except Exception as e:
            logger.error(f"Failed to get recording {recording_id}: {e}")
            return None
    
    async def get_artist_releases(self, artist_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get releases by a specific artist."""
        try:
            params = {
                "artist": artist_id,
                "fmt": "json",
                "limit": limit
            }
            
            response = await self._make_request("/release", params)
            releases = response.get("releases", [])
            
            return releases
            
        except Exception as e:
            logger.error(f"Failed to get releases for artist {artist_id}: {e}")
            return []
    
    async def get_similar_artists(self, artist_id: str) -> List[Dict[str, Any]]:
        """Get artists similar to the given artist."""
        try:
            # MusicBrainz doesn't have direct similar artists, but we can use tags
            artist = await self.get_artist(artist_id)
            if not artist:
                return []
            
            # Get tags from the artist
            tags = artist.get("tags", [])
            if not tags:
                return []
            
            # Search for other artists with similar tags
            similar_artists = []
            for tag in tags[:3]:  # Use top 3 tags
                tag_name = tag.get("name", "")
                if tag_name:
                    artists = await self.search_artists(f"tag:{tag_name}", limit=10)
                    similar_artists.extend(artists)
            
            # Remove duplicates and the original artist
            seen = set()
            unique_artists = []
            for artist in similar_artists:
                artist_id = artist.get("id")
                if artist_id and artist_id not in seen and artist_id != artist_id:
                    seen.add(artist_id)
                    unique_artists.append(artist)
            
            return unique_artists[:10]  # Limit to 10 similar artists
            
        except Exception as e:
            logger.error(f"Failed to get similar artists for {artist_id}: {e}")
            return []
    
    async def get_artist_genres(self, artist_id: str) -> List[str]:
        """Get genres/tags for an artist."""
        try:
            artist = await self.get_artist(artist_id)
            if not artist:
                return []
            
            tags = artist.get("tags", [])
            genres = [tag.get("name", "") for tag in tags if tag.get("name")]
            
            return genres
            
        except Exception as e:
            logger.error(f"Failed to get genres for artist {artist_id}: {e}")
            return []
    
    async def enrich_artist_info(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Enrich artist information with MusicBrainz data."""
        try:
            # Search for the artist
            artists = await self.search_artists(artist_name, limit=5)
            if not artists:
                return None
            
            # Get the best match (first result)
            artist = artists[0]
            artist_id = artist.get("id")
            
            if not artist_id:
                return artist
            
            # Get detailed information
            detailed_artist = await self.get_artist(artist_id)
            if detailed_artist:
                # Merge basic and detailed info
                artist.update(detailed_artist)
            
            return artist
            
        except Exception as e:
            logger.error(f"Failed to enrich artist info for '{artist_name}': {e}")
            return None
    
    async def enrich_release_info(self, release_title: str, artist_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Enrich release information with MusicBrainz data."""
        try:
            # Build search query
            query = release_title
            if artist_name:
                query = f"{artist_name} {release_title}"
            
            # Search for the release
            releases = await self.search_releases(query, limit=5)
            if not releases:
                return None
            
            # Get the best match (first result)
            release = releases[0]
            release_id = release.get("id")
            
            if not release_id:
                return release
            
            # Get detailed information
            detailed_release = await self.get_release(release_id)
            if detailed_release:
                # Merge basic and detailed info
                release.update(detailed_release)
            
            return release
            
        except Exception as e:
            logger.error(f"Failed to enrich release info for '{release_title}': {e}")
            return None
    
    async def get_artist_biography(self, artist_id: str) -> Optional[str]:
        """Get artist biography from MusicBrainz (if available)."""
        try:
            artist = await self.get_artist(artist_id)
            if not artist:
                return None
            
            # MusicBrainz doesn't store biographies directly,
            # but we can get related URLs that might contain biographies
            relations = artist.get("relations", [])
            for relation in relations:
                if relation.get("type") == "wikipedia":
                    # Could fetch Wikipedia content here if needed
                    return f"Wikipedia: {relation.get('url', {}).get('resource', '')}"
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get biography for artist {artist_id}: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global client instance
_musicbrainz_client: Optional[MusicBrainzClient] = None


async def get_musicbrainz_client() -> MusicBrainzClient:
    """Get or create MusicBrainz client instance."""
    global _musicbrainz_client
    if _musicbrainz_client is None:
        _musicbrainz_client = MusicBrainzClient()
    return _musicbrainz_client


async def close_musicbrainz_client():
    """Close the global MusicBrainz client."""
    global _musicbrainz_client
    if _musicbrainz_client:
        await _musicbrainz_client.close()
        _musicbrainz_client = None
