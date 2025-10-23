"""
Vector search utilities for the Music Assistant.
Provides semantic search capabilities for music content.
"""

from typing import Dict, List, Any, Optional
from loguru import logger

from database.vector_store import get_vector_store


class VectorSearchTool:
    """Tool for performing vector-based semantic search."""
    
    def __init__(self):
        self.vector_store = None
    
    async def initialize(self):
        """Initialize the vector search tool."""
        try:
            self.vector_store = await get_vector_store()
            logger.info("Vector search tool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize vector search tool: {e}")
            raise
    
    async def search_music(self, query: str, limit: int = 10, 
                          entity_types: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Search for music content using semantic similarity."""
        try:
            if not self.vector_store:
                await self.initialize()
            
            if entity_types is None:
                entity_types = ["songs", "albums", "artists"]
            
            results = {}
            
            if "songs" in entity_types:
                results["songs"] = await self.vector_store.search_songs(query, limit)
            
            if "albums" in entity_types:
                results["albums"] = await self.vector_store.search_albums(query, limit)
            
            if "artists" in entity_types:
                results["artists"] = await self.vector_store.search_artists(query, limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return {"songs": [], "albums": [], "artists": []}
    
    async def find_similar_artists(self, artist_name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find artists similar to the given artist."""
        try:
            if not self.vector_store:
                await self.initialize()
            
            results = await self.vector_store.search_artists(artist_name, limit)
            
            # Filter out the exact match if present
            similar_artists = []
            for artist in results:
                if artist["name"].lower() != artist_name.lower():
                    similar_artists.append(artist)
            
            return similar_artists[:limit]
            
        except Exception as e:
            logger.error(f"Similar artists search failed: {e}")
            return []
    
    async def find_similar_songs(self, song_title: str, artist_name: Optional[str] = None, 
                                limit: int = 5) -> List[Dict[str, Any]]:
        """Find songs similar to the given song."""
        try:
            if not self.vector_store:
                await self.initialize()
            
            # Build search query
            query = song_title
            if artist_name:
                query = f"{artist_name} {song_title}"
            
            results = await self.vector_store.search_songs(query, limit * 2)  # Get more to filter
            
            # Filter out exact matches
            similar_songs = []
            for song in results:
                if (song["title"].lower() != song_title.lower() or 
                    (artist_name and song["artist_name"].lower() != artist_name.lower())):
                    similar_songs.append(song)
            
            return similar_songs[:limit]
            
        except Exception as e:
            logger.error(f"Similar songs search failed: {e}")
            return []
    
    async def find_similar_albums(self, album_title: str, artist_name: Optional[str] = None,
                                 limit: int = 5) -> List[Dict[str, Any]]:
        """Find albums similar to the given album."""
        try:
            if not self.vector_store:
                await self.initialize()
            
            # Build search query
            query = album_title
            if artist_name:
                query = f"{artist_name} {album_title}"
            
            results = await self.vector_store.search_albums(query, limit * 2)  # Get more to filter
            
            # Filter out exact matches
            similar_albums = []
            for album in results:
                if (album["title"].lower() != album_title.lower() or 
                    (artist_name and album["artist_name"].lower() != artist_name.lower())):
                    similar_albums.append(album)
            
            return similar_albums[:limit]
            
        except Exception as e:
            logger.error(f"Similar albums search failed: {e}")
            return []
    
    async def search_by_genre(self, genre: str, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Search for music by genre."""
        try:
            if not self.vector_store:
                await self.initialize()
            
            # Use genre as search query
            results = await self.vector_store.search_all(genre, limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Genre search failed: {e}")
            return {"songs": [], "albums": [], "artists": []}
    
    async def search_by_year(self, year: int, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Search for music from a specific year."""
        try:
            if not self.vector_store:
                await self.initialize()
            
            # Search for the year
            results = await self.vector_store.search_all(str(year), limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Year search failed: {e}")
            return {"songs": [], "albums": [], "artists": []}
    
    async def search_by_mood(self, mood: str, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Search for music by mood or style."""
        try:
            if not self.vector_store:
                await self.initialize()
            
            # Use mood as search query
            results = await self.vector_store.search_all(mood, limit)
            
            return results
            
        except Exception as e:
            logger.error(f"Mood search failed: {e}")
            return {"songs": [], "albums": [], "artists": []}
    
    async def get_search_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on partial query."""
        try:
            if not self.vector_store:
                await self.initialize()
            
            # Search for partial matches
            results = await self.vector_store.search_all(partial_query, limit)
            
            suggestions = []
            
            # Add artist names
            for artist in results.get("artists", []):
                if artist["name"] not in suggestions:
                    suggestions.append(artist["name"])
            
            # Add album titles
            for album in results.get("albums", []):
                if album["title"] not in suggestions:
                    suggestions.append(album["title"])
            
            # Add song titles
            for song in results.get("songs", []):
                if song["title"] not in suggestions:
                    suggestions.append(song["title"])
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Search suggestions failed: {e}")
            return []


# Global vector search tool instance
_vector_search_tool: Optional[VectorSearchTool] = None


async def get_vector_search_tool() -> VectorSearchTool:
    """Get or create vector search tool instance."""
    global _vector_search_tool
    if _vector_search_tool is None:
        _vector_search_tool = VectorSearchTool()
        await _vector_search_tool.initialize()
    return _vector_search_tool


async def close_vector_search_tool():
    """Close the global vector search tool."""
    global _vector_search_tool
    if _vector_search_tool:
        _vector_search_tool = None
