"""
Vector store implementation using ChromaDB.
Handles embedding storage and similarity search for music content.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from loguru import logger

from config import settings


class VectorStore:
    """ChromaDB wrapper for music content vector storage and search."""
    
    def __init__(self):
        self.persist_directory = Path(settings.chroma_persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
        
        # Collection names
        self.songs_collection_name = "songs"
        self.albums_collection_name = "albums"
        self.artists_collection_name = "artists"
        
        # Initialize collections
        self._initialize_collections()
    
    def _initialize_collections(self):
        """Initialize ChromaDB collections."""
        try:
            # Songs collection
            self.songs_collection = self.client.get_or_create_collection(
                name=self.songs_collection_name,
                metadata={"description": "Song embeddings for semantic search"}
            )
            
            # Albums collection
            self.albums_collection = self.client.get_or_create_collection(
                name=self.albums_collection_name,
                metadata={"description": "Album embeddings for semantic search"}
            )
            
            # Artists collection
            self.artists_collection = self.client.get_or_create_collection(
                name=self.artists_collection_name,
                metadata={"description": "Artist embeddings for semantic search"}
            )
            
            logger.info("ChromaDB collections initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB collections: {e}")
            raise
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using the configured model."""
        try:
            embedding = self.embedding_model.encode(text, convert_to_tensor=False)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def _prepare_song_text(self, song_data: Dict[str, Any]) -> str:
        """Prepare text representation of a song for embedding."""
        title = song_data.get("title", "")
        artist = song_data.get("artist_name", "")
        album = song_data.get("album_title", "")
        genres = song_data.get("genres", [])
        
        # Create comprehensive text representation
        text_parts = [title, artist, album]
        
        if genres:
            text_parts.append(" ".join(genres))
        
        return " ".join(filter(None, text_parts))
    
    def _prepare_album_text(self, album_data: Dict[str, Any]) -> str:
        """Prepare text representation of an album for embedding."""
        title = album_data.get("title", "")
        artist = album_data.get("artist_name", "")
        genres = album_data.get("genres", [])
        release_type = album_data.get("release_type", "")
        
        # Create comprehensive text representation
        text_parts = [title, artist, release_type]
        
        if genres:
            text_parts.append(" ".join(genres))
        
        return " ".join(filter(None, text_parts))
    
    def _prepare_artist_text(self, artist_data: Dict[str, Any]) -> str:
        """Prepare text representation of an artist for embedding."""
        name = artist_data.get("name", "")
        genres = artist_data.get("genres", [])
        country = artist_data.get("country", "")
        artist_type = artist_data.get("type", "")
        
        # Create comprehensive text representation
        text_parts = [name, artist_type, country]
        
        if genres:
            text_parts.append(" ".join(genres))
        
        return " ".join(filter(None, text_parts))
    
    async def add_song(self, song_id: str, song_data: Dict[str, Any]) -> bool:
        """Add a song to the vector store."""
        try:
            text = self._prepare_song_text(song_data)
            embedding = self._generate_embedding(text)
            
            # Prepare metadata
            metadata = {
                "song_id": song_id,
                "title": song_data.get("title", ""),
                "artist_name": song_data.get("artist_name", ""),
                "album_title": song_data.get("album_title", ""),
                "genres": song_data.get("genres", []),
                "duration": song_data.get("duration", 0),
                "year": song_data.get("year", 0)
            }
            
            # Add to collection
            self.songs_collection.add(
                ids=[song_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[text]
            )
            
            logger.debug(f"Added song {song_id} to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add song {song_id} to vector store: {e}")
            return False
    
    async def add_album(self, album_id: str, album_data: Dict[str, Any]) -> bool:
        """Add an album to the vector store."""
        try:
            text = self._prepare_album_text(album_data)
            embedding = self._generate_embedding(text)
            
            # Prepare metadata
            metadata = {
                "album_id": album_id,
                "title": album_data.get("title", ""),
                "artist_name": album_data.get("artist_name", ""),
                "genres": album_data.get("genres", []),
                "release_type": album_data.get("release_type", ""),
                "year": album_data.get("year", 0)
            }
            
            # Add to collection
            self.albums_collection.add(
                ids=[album_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[text]
            )
            
            logger.debug(f"Added album {album_id} to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add album {album_id} to vector store: {e}")
            return False
    
    async def add_artist(self, artist_id: str, artist_data: Dict[str, Any]) -> bool:
        """Add an artist to the vector store."""
        try:
            text = self._prepare_artist_text(artist_data)
            embedding = self._generate_embedding(text)
            
            # Prepare metadata
            metadata = {
                "artist_id": artist_id,
                "name": artist_data.get("name", ""),
                "genres": artist_data.get("genres", []),
                "country": artist_data.get("country", ""),
                "type": artist_data.get("type", "")
            }
            
            # Add to collection
            self.artists_collection.add(
                ids=[artist_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[text]
            )
            
            logger.debug(f"Added artist {artist_id} to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add artist {artist_id} to vector store: {e}")
            return False
    
    async def search_songs(self, query: str, limit: int = 10, 
                          filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for songs using semantic similarity."""
        try:
            query_embedding = self._generate_embedding(query)
            
            # Perform search
            results = self.songs_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=filters,
                include=["metadatas", "distances", "documents"]
            )
            
            # Format results
            formatted_results = []
            if results["metadatas"] and results["metadatas"][0]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    result = {
                        "song_id": metadata["song_id"],
                        "title": metadata["title"],
                        "artist_name": metadata["artist_name"],
                        "album_title": metadata["album_title"],
                        "genres": metadata["genres"],
                        "duration": metadata["duration"],
                        "year": metadata["year"],
                        "similarity": 1 - results["distances"][0][i],  # Convert distance to similarity
                        "text": results["documents"][0][i] if results["documents"] else ""
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search songs: {e}")
            return []
    
    async def search_albums(self, query: str, limit: int = 10,
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for albums using semantic similarity."""
        try:
            query_embedding = self._generate_embedding(query)
            
            # Perform search
            results = self.albums_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=filters,
                include=["metadatas", "distances", "documents"]
            )
            
            # Format results
            formatted_results = []
            if results["metadatas"] and results["metadatas"][0]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    result = {
                        "album_id": metadata["album_id"],
                        "title": metadata["title"],
                        "artist_name": metadata["artist_name"],
                        "genres": metadata["genres"],
                        "release_type": metadata["release_type"],
                        "year": metadata["year"],
                        "similarity": 1 - results["distances"][0][i],
                        "text": results["documents"][0][i] if results["documents"] else ""
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search albums: {e}")
            return []
    
    async def search_artists(self, query: str, limit: int = 10,
                            filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search for artists using semantic similarity."""
        try:
            query_embedding = self._generate_embedding(query)
            
            # Perform search
            results = self.artists_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=filters,
                include=["metadatas", "distances", "documents"]
            )
            
            # Format results
            formatted_results = []
            if results["metadatas"] and results["metadatas"][0]:
                for i, metadata in enumerate(results["metadatas"][0]):
                    result = {
                        "artist_id": metadata["artist_id"],
                        "name": metadata["name"],
                        "genres": metadata["genres"],
                        "country": metadata["country"],
                        "type": metadata["type"],
                        "similarity": 1 - results["distances"][0][i],
                        "text": results["documents"][0][i] if results["documents"] else ""
                    }
                    formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search artists: {e}")
            return []
    
    async def search_all(self, query: str, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Search across all collections."""
        try:
            # Search all collections in parallel
            songs_task = self.search_songs(query, limit)
            albums_task = self.search_albums(query, limit)
            artists_task = self.search_artists(query, limit)
            
            songs, albums, artists = await asyncio.gather(
                songs_task, albums_task, artists_task
            )
            
            return {
                "songs": songs,
                "albums": albums,
                "artists": artists
            }
            
        except Exception as e:
            logger.error(f"Failed to search all collections: {e}")
            return {"songs": [], "albums": [], "artists": []}
    
    async def delete_song(self, song_id: str) -> bool:
        """Delete a song from the vector store."""
        try:
            self.songs_collection.delete(ids=[song_id])
            logger.debug(f"Deleted song {song_id} from vector store")
            return True
        except Exception as e:
            logger.error(f"Failed to delete song {song_id}: {e}")
            return False
    
    async def delete_album(self, album_id: str) -> bool:
        """Delete an album from the vector store."""
        try:
            self.albums_collection.delete(ids=[album_id])
            logger.debug(f"Deleted album {album_id} from vector store")
            return True
        except Exception as e:
            logger.error(f"Failed to delete album {album_id}: {e}")
            return False
    
    async def delete_artist(self, artist_id: str) -> bool:
        """Delete an artist from the vector store."""
        try:
            self.artists_collection.delete(ids=[artist_id])
            logger.debug(f"Deleted artist {artist_id} from vector store")
            return True
        except Exception as e:
            logger.error(f"Failed to delete artist {artist_id}: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about the vector store collections."""
        try:
            songs_count = self.songs_collection.count()
            albums_count = self.albums_collection.count()
            artists_count = self.artists_collection.count()
            
            return {
                "songs": songs_count,
                "albums": albums_count,
                "artists": artists_count,
                "total": songs_count + albums_count + artists_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"songs": 0, "albums": 0, "artists": 0, "total": 0}
    
    async def reset_collections(self) -> bool:
        """Reset all collections (use with caution)."""
        try:
            self.client.delete_collection(self.songs_collection_name)
            self.client.delete_collection(self.albums_collection_name)
            self.client.delete_collection(self.artists_collection_name)
            
            # Reinitialize collections
            self._initialize_collections()
            
            logger.info("All vector store collections reset successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset collections: {e}")
            return False


# Global vector store instance
_vector_store: Optional[VectorStore] = None


async def get_vector_store() -> VectorStore:
    """Get or create vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


async def close_vector_store():
    """Close the global vector store."""
    global _vector_store
    if _vector_store:
        # ChromaDB doesn't need explicit closing
        _vector_store = None
