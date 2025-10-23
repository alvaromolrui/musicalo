"""
Embeddings generation module.
Handles creating and updating vector embeddings for music content.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from loguru import logger

from config import settings
from database.models import Artist, Album, Song, Embedding
from database.vector_store import get_vector_store


class EmbeddingGenerator:
    """Handles generation and management of vector embeddings."""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.vector_store = None
        
    async def initialize(self):
        """Initialize the embedding generator."""
        try:
            # Create database engine
            self.engine = create_async_engine(
                settings.database_url,
                echo=False,
                pool_size=5,
                max_overflow=10
            )
            
            # Create session factory
            self.session_factory = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Initialize vector store
            self.vector_store = await get_vector_store()
            
            logger.info("Embedding generator initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize embedding generator: {e}")
            raise
    
    async def generate_all_embeddings(self) -> Dict[str, Any]:
        """Generate embeddings for all music content."""
        result = {
            "artists": {"processed": 0, "created": 0, "updated": 0, "failed": 0},
            "albums": {"processed": 0, "created": 0, "updated": 0, "failed": 0},
            "songs": {"processed": 0, "created": 0, "updated": 0, "failed": 0}
        }
        
        try:
            logger.info("Starting embedding generation for all content")
            
            # Generate embeddings for artists
            result["artists"] = await self._generate_artist_embeddings()
            
            # Generate embeddings for albums
            result["albums"] = await self._generate_album_embeddings()
            
            # Generate embeddings for songs
            result["songs"] = await self._generate_song_embeddings()
            
            total_processed = (
                result["artists"]["processed"] + 
                result["albums"]["processed"] + 
                result["songs"]["processed"]
            )
            
            total_created = (
                result["artists"]["created"] + 
                result["albums"]["created"] + 
                result["songs"]["created"]
            )
            
            logger.info(f"Embedding generation completed: {total_processed} processed, {total_created} created")
            return result
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return result
    
    async def _generate_artist_embeddings(self) -> Dict[str, int]:
        """Generate embeddings for all artists."""
        result = {"processed": 0, "created": 0, "updated": 0, "failed": 0}
        
        try:
            async with self.session_factory() as session:
                # Get all artists
                stmt = select(Artist)
                artists_result = await session.execute(stmt)
                artists = artists_result.scalars().all()
                
                logger.info(f"Generating embeddings for {len(artists)} artists")
                
                for artist in artists:
                    try:
                        result["processed"] += 1
                        
                        # Check if embedding already exists
                        existing_embedding = await session.execute(
                            select(Embedding).filter(
                                Embedding.entity_type == "artist",
                                Embedding.entity_id == artist.id,
                                Embedding.model_name == settings.embedding_model
                            )
                        )
                        existing_embedding = existing_embedding.scalar_one_or_none()
                        
                        # Prepare artist data for embedding
                        artist_data = {
                            "name": artist.name,
                            "genres": artist.genres or [],
                            "country": artist.country or "",
                            "type": artist.type or ""
                        }
                        
                        # Generate and store embedding
                        success = await self.vector_store.add_artist(str(artist.id), artist_data)
                        
                        if success:
                            if existing_embedding:
                                # Update existing embedding record
                                existing_embedding.text_content = self._prepare_artist_text(artist_data)
                                existing_embedding.created_at = datetime.utcnow()
                                result["updated"] += 1
                            else:
                                # Create new embedding record
                                new_embedding = Embedding(
                                    entity_type="artist",
                                    entity_id=artist.id,
                                    model_name=settings.embedding_model,
                                    embedding_dimension=self.vector_store.embedding_dimension,
                                    text_content=self._prepare_artist_text(artist_data),
                                    created_at=datetime.utcnow()
                                )
                                session.add(new_embedding)
                                result["created"] += 1
                        
                        # Commit every 50 artists
                        if result["processed"] % 50 == 0:
                            await session.commit()
                            logger.info(f"Processed {result['processed']} artist embeddings")
                    
                    except Exception as e:
                        logger.error(f"Failed to generate embedding for artist {artist.id}: {e}")
                        result["failed"] += 1
                
                # Final commit
                await session.commit()
            
            logger.info(f"Artist embedding generation completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Artist embedding generation failed: {e}")
            result["failed"] += result["processed"]
            return result
    
    async def _generate_album_embeddings(self) -> Dict[str, int]:
        """Generate embeddings for all albums."""
        result = {"processed": 0, "created": 0, "updated": 0, "failed": 0}
        
        try:
            async with self.session_factory() as session:
                # Get all albums with their artists
                stmt = select(Album).join(Artist)
                albums_result = await session.execute(stmt)
                albums = albums_result.scalars().all()
                
                logger.info(f"Generating embeddings for {len(albums)} albums")
                
                for album in albums:
                    try:
                        result["processed"] += 1
                        
                        # Check if embedding already exists
                        existing_embedding = await session.execute(
                            select(Embedding).filter(
                                Embedding.entity_type == "album",
                                Embedding.entity_id == album.id,
                                Embedding.model_name == settings.embedding_model
                            )
                        )
                        existing_embedding = existing_embedding.scalar_one_or_none()
                        
                        # Prepare album data for embedding
                        album_data = {
                            "title": album.title,
                            "artist_name": album.artist.name,
                            "genres": album.genres or [],
                            "release_type": album.release_type or "",
                            "year": album.release_date.year if album.release_date else 0
                        }
                        
                        # Generate and store embedding
                        success = await self.vector_store.add_album(str(album.id), album_data)
                        
                        if success:
                            if existing_embedding:
                                # Update existing embedding record
                                existing_embedding.text_content = self._prepare_album_text(album_data)
                                existing_embedding.created_at = datetime.utcnow()
                                result["updated"] += 1
                            else:
                                # Create new embedding record
                                new_embedding = Embedding(
                                    entity_type="album",
                                    entity_id=album.id,
                                    model_name=settings.embedding_model,
                                    embedding_dimension=self.vector_store.embedding_dimension,
                                    text_content=self._prepare_album_text(album_data),
                                    created_at=datetime.utcnow()
                                )
                                session.add(new_embedding)
                                result["created"] += 1
                        
                        # Commit every 50 albums
                        if result["processed"] % 50 == 0:
                            await session.commit()
                            logger.info(f"Processed {result['processed']} album embeddings")
                    
                    except Exception as e:
                        logger.error(f"Failed to generate embedding for album {album.id}: {e}")
                        result["failed"] += 1
                
                # Final commit
                await session.commit()
            
            logger.info(f"Album embedding generation completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Album embedding generation failed: {e}")
            result["failed"] += result["processed"]
            return result
    
    async def _generate_song_embeddings(self) -> Dict[str, int]:
        """Generate embeddings for all songs."""
        result = {"processed": 0, "created": 0, "updated": 0, "failed": 0}
        
        try:
            async with self.session_factory() as session:
                # Get all songs with their artists and albums
                stmt = select(Song).join(Artist).join(Album)
                songs_result = await session.execute(stmt)
                songs = songs_result.scalars().all()
                
                logger.info(f"Generating embeddings for {len(songs)} songs")
                
                for song in songs:
                    try:
                        result["processed"] += 1
                        
                        # Check if embedding already exists
                        existing_embedding = await session.execute(
                            select(Embedding).filter(
                                Embedding.entity_type == "song",
                                Embedding.entity_id == song.id,
                                Embedding.model_name == settings.embedding_model
                            )
                        )
                        existing_embedding = existing_embedding.scalar_one_or_none()
                        
                        # Prepare song data for embedding
                        song_data = {
                            "title": song.title,
                            "artist_name": song.artist.name,
                            "album_title": song.album.title,
                            "genres": song.genres or [],
                            "duration": song.duration or 0,
                            "year": song.album.release_date.year if song.album.release_date else 0
                        }
                        
                        # Generate and store embedding
                        success = await self.vector_store.add_song(str(song.id), song_data)
                        
                        if success:
                            if existing_embedding:
                                # Update existing embedding record
                                existing_embedding.text_content = self._prepare_song_text(song_data)
                                existing_embedding.created_at = datetime.utcnow()
                                result["updated"] += 1
                            else:
                                # Create new embedding record
                                new_embedding = Embedding(
                                    entity_type="song",
                                    entity_id=song.id,
                                    model_name=settings.embedding_model,
                                    embedding_dimension=self.vector_store.embedding_dimension,
                                    text_content=self._prepare_song_text(song_data),
                                    created_at=datetime.utcnow()
                                )
                                session.add(new_embedding)
                                result["created"] += 1
                        
                        # Commit every 100 songs
                        if result["processed"] % 100 == 0:
                            await session.commit()
                            logger.info(f"Processed {result['processed']} song embeddings")
                    
                    except Exception as e:
                        logger.error(f"Failed to generate embedding for song {song.id}: {e}")
                        result["failed"] += 1
                
                # Final commit
                await session.commit()
            
            logger.info(f"Song embedding generation completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Song embedding generation failed: {e}")
            result["failed"] += result["processed"]
            return result
    
    def _prepare_artist_text(self, artist_data: Dict[str, Any]) -> str:
        """Prepare text representation of an artist for embedding."""
        name = artist_data.get("name", "")
        genres = artist_data.get("genres", [])
        country = artist_data.get("country", "")
        artist_type = artist_data.get("type", "")
        
        text_parts = [name, artist_type, country]
        
        if genres:
            text_parts.append(" ".join(genres))
        
        return " ".join(filter(None, text_parts))
    
    def _prepare_album_text(self, album_data: Dict[str, Any]) -> str:
        """Prepare text representation of an album for embedding."""
        title = album_data.get("title", "")
        artist_name = album_data.get("artist_name", "")
        genres = album_data.get("genres", [])
        release_type = album_data.get("release_type", "")
        year = album_data.get("year", 0)
        
        text_parts = [title, artist_name, release_type]
        
        if year > 0:
            text_parts.append(str(year))
        
        if genres:
            text_parts.append(" ".join(genres))
        
        return " ".join(filter(None, text_parts))
    
    def _prepare_song_text(self, song_data: Dict[str, Any]) -> str:
        """Prepare text representation of a song for embedding."""
        title = song_data.get("title", "")
        artist_name = song_data.get("artist_name", "")
        album_title = song_data.get("album_title", "")
        genres = song_data.get("genres", [])
        year = song_data.get("year", 0)
        
        text_parts = [title, artist_name, album_title]
        
        if year > 0:
            text_parts.append(str(year))
        
        if genres:
            text_parts.append(" ".join(genres))
        
        return " ".join(filter(None, text_parts))
    
    async def generate_embedding_for_entity(self, entity_type: str, entity_id: str) -> bool:
        """Generate embedding for a specific entity."""
        try:
            async with self.session_factory() as session:
                if entity_type == "artist":
                    artist = await session.get(Artist, entity_id)
                    if not artist:
                        return False
                    
                    artist_data = {
                        "name": artist.name,
                        "genres": artist.genres or [],
                        "country": artist.country or "",
                        "type": artist.type or ""
                    }
                    
                    success = await self.vector_store.add_artist(entity_id, artist_data)
                
                elif entity_type == "album":
                    album = await session.get(Album, entity_id)
                    if not album:
                        return False
                    
                    album_data = {
                        "title": album.title,
                        "artist_name": album.artist.name,
                        "genres": album.genres or [],
                        "release_type": album.release_type or "",
                        "year": album.release_date.year if album.release_date else 0
                    }
                    
                    success = await self.vector_store.add_album(entity_id, album_data)
                
                elif entity_type == "song":
                    song = await session.get(Song, entity_id)
                    if not song:
                        return False
                    
                    song_data = {
                        "title": song.title,
                        "artist_name": song.artist.name,
                        "album_title": song.album.title,
                        "genres": song.genres or [],
                        "duration": song.duration or 0,
                        "year": song.album.release_date.year if song.album.release_date else 0
                    }
                    
                    success = await self.vector_store.add_song(entity_id, song_data)
                
                else:
                    logger.error(f"Unknown entity type: {entity_type}")
                    return False
                
                if success:
                    # Update or create embedding record
                    existing_embedding = await session.execute(
                        select(Embedding).filter(
                            Embedding.entity_type == entity_type,
                            Embedding.entity_id == entity_id,
                            Embedding.model_name == settings.embedding_model
                        )
                    )
                    existing_embedding = existing_embedding.scalar_one_or_none()
                    
                    if existing_embedding:
                        existing_embedding.created_at = datetime.utcnow()
                    else:
                        new_embedding = Embedding(
                            entity_type=entity_type,
                            entity_id=entity_id,
                            model_name=settings.embedding_model,
                            embedding_dimension=self.vector_store.embedding_dimension,
                            text_content="",  # Will be filled by the vector store
                            created_at=datetime.utcnow()
                        )
                        session.add(new_embedding)
                    
                    await session.commit()
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to generate embedding for {entity_type} {entity_id}: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.engine:
                await self.engine.dispose()
            logger.info("Embedding generator cleanup completed")
        except Exception as e:
            logger.error(f"Embedding generator cleanup failed: {e}")


# Global embedding generator instance
_embedding_generator: Optional[EmbeddingGenerator] = None


async def get_embedding_generator() -> EmbeddingGenerator:
    """Get or create embedding generator instance."""
    global _embedding_generator
    if _embedding_generator is None:
        _embedding_generator = EmbeddingGenerator()
        await _embedding_generator.initialize()
    return _embedding_generator


async def close_embedding_generator():
    """Close the global embedding generator instance."""
    global _embedding_generator
    if _embedding_generator:
        await _embedding_generator.cleanup()
        _embedding_generator = None
