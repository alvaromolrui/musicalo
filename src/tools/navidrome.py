"""
Navidrome API client for music library access.
Implements Subsonic API protocol for Navidrome integration.
"""

import asyncio
import hashlib
import random
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

import httpx
from loguru import logger

from src.config import settings


class NavidromeClient:
    """Client for interacting with Navidrome via Subsonic API."""
    
    def __init__(self):
        self.base_url = settings.navidrome_url.rstrip('/')
        self.username = settings.navidrome_username
        self.password = settings.navidrome_password
        self.client = httpx.AsyncClient(timeout=30.0)
        
    def _generate_auth_params(self) -> Dict[str, str]:
        """Generate authentication parameters for Subsonic API."""
        salt = str(random.randint(100000, 999999))
        token = hashlib.md5(f"{self.password}{salt}".encode()).hexdigest()
        
        return {
            "u": self.username,
            "t": token,
            "s": salt,
            "v": "1.16.1",
            "c": "MusicAssistant",
            "f": "json"
        }
    
    async def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make authenticated request to Navidrome API."""
        auth_params = self._generate_auth_params()
        
        if params:
            auth_params.update(params)
        
        url = f"{self.base_url}/rest/{endpoint}"
        
        try:
            response = await self.client.get(url, params=auth_params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("subsonic-response", {}).get("status") != "ok":
                error_msg = data.get("subsonic-response", {}).get("error", {}).get("message", "Unknown error")
                raise Exception(f"Navidrome API error: {error_msg}")
            
            return data.get("subsonic-response", {})
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling Navidrome API: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calling Navidrome API: {e}")
            raise
    
    async def get_artists(self, limit: int = 500, offset: int = 0) -> List[Dict[str, Any]]:
        """Get list of artists from the library."""
        try:
            response = await self._make_request("getArtists")
            artists = response.get("artists", {}).get("artist", [])
            
            # Handle single artist case
            if isinstance(artists, dict):
                artists = [artists]
            
            # Apply pagination
            return artists[offset:offset + limit]
            
        except Exception as e:
            logger.error(f"Failed to get artists: {e}")
            return []
    
    async def get_albums(self, limit: int = 500, offset: int = 0, 
                        artist_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of albums from the library."""
        try:
            params = {"type": "alphabeticalByArtist", "size": limit, "offset": offset}
            
            if artist_id:
                params["artistId"] = artist_id
            
            response = await self._make_request("getAlbumList2", params)
            albums = response.get("albumList2", {}).get("album", [])
            
            # Handle single album case
            if isinstance(albums, dict):
                albums = [albums]
            
            return albums
            
        except Exception as e:
            logger.error(f"Failed to get albums: {e}")
            return []
    
    async def get_songs(self, limit: int = 500, offset: int = 0,
                       album_id: Optional[str] = None, artist_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of songs from the library."""
        try:
            params = {"type": "alphabeticalByArtist", "size": limit, "offset": offset}
            
            if album_id:
                params["albumId"] = album_id
            elif artist_id:
                params["artistId"] = artist_id
            
            response = await self._make_request("getAlbumList2", params)
            albums = response.get("albumList2", {}).get("album", [])
            
            # Handle single album case
            if isinstance(albums, dict):
                albums = [albums]
            
            # Extract songs from albums
            songs = []
            for album in albums:
                album_songs = await self.get_album_songs(album["id"])
                songs.extend(album_songs)
            
            return songs[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get songs: {e}")
            return []
    
    async def get_album_songs(self, album_id: str) -> List[Dict[str, Any]]:
        """Get songs from a specific album."""
        try:
            response = await self._make_request("getAlbum", {"id": album_id})
            album = response.get("album", {})
            songs = album.get("song", [])
            
            # Handle single song case
            if isinstance(songs, dict):
                songs = [songs]
            
            return songs
            
        except Exception as e:
            logger.error(f"Failed to get album songs for {album_id}: {e}")
            return []
    
    async def search(self, query: str, limit: int = 20) -> Dict[str, List[Dict[str, Any]]]:
        """Search for artists, albums, and songs."""
        try:
            params = {"query": query}
            response = await self._make_request("search3", params)
            
            results = {
                "artists": response.get("searchResult3", {}).get("artist", []),
                "albums": response.get("searchResult3", {}).get("album", []),
                "songs": response.get("searchResult3", {}).get("song", [])
            }
            
            # Handle single item cases
            for key in results:
                if isinstance(results[key], dict):
                    results[key] = [results[key]]
                # Limit results
                results[key] = results[key][:limit]
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search for '{query}': {e}")
            return {"artists": [], "albums": [], "songs": []}
    
    async def get_playlists(self) -> List[Dict[str, Any]]:
        """Get all playlists."""
        try:
            response = await self._make_request("getPlaylists")
            playlists = response.get("playlists", {}).get("playlist", [])
            
            # Handle single playlist case
            if isinstance(playlists, dict):
                playlists = [playlists]
            
            return playlists
            
        except Exception as e:
            logger.error(f"Failed to get playlists: {e}")
            return []
    
    async def get_playlist_songs(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get songs from a specific playlist."""
        try:
            response = await self._make_request("getPlaylist", {"id": playlist_id})
            playlist = response.get("playlist", {})
            songs = playlist.get("entry", [])
            
            # Handle single song case
            if isinstance(songs, dict):
                songs = [songs]
            
            return songs
            
        except Exception as e:
            logger.error(f"Failed to get playlist songs for {playlist_id}: {e}")
            return []
    
    async def get_library_stats(self) -> Dict[str, Any]:
        """Get library statistics."""
        try:
            # Get counts
            artists = await self.get_artists()
            albums = await self.get_albums()
            
            # Count songs by getting a sample and estimating
            sample_songs = await self.get_songs(limit=1000)
            total_songs = len(sample_songs)
            
            # If we got the full limit, there might be more
            if len(sample_songs) == 1000:
                # Rough estimation based on albums
                avg_songs_per_album = 10  # Conservative estimate
                total_songs = len(albums) * avg_songs_per_album
            
            return {
                "artists": len(artists),
                "albums": len(albums),
                "songs": total_songs,
                "last_updated": time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to get library stats: {e}")
            return {"artists": 0, "albums": 0, "songs": 0, "last_updated": 0}
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Global client instance
_navidrome_client: Optional[NavidromeClient] = None


async def get_navidrome_client() -> NavidromeClient:
    """Get or create Navidrome client instance."""
    global _navidrome_client
    if _navidrome_client is None:
        _navidrome_client = NavidromeClient()
    return _navidrome_client


async def close_navidrome_client():
    """Close the global Navidrome client."""
    global _navidrome_client
    if _navidrome_client:
        await _navidrome_client.close()
        _navidrome_client = None
