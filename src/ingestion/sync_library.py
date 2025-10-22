"""
Library synchronization module.
Handles syncing music library data from Navidrome to the local database.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from loguru import logger

from src.config import settings
from src.database.models import Base, Artist, Album, Song, SyncLog
from src.tools.navidrome import get_navidrome_client
from src.tools.musicbrainz import get_musicbrainz_client


class LibrarySync:
    """Handles synchronization of music library from Navidrome."""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
        self.navidrome = None
        self.musicbrainz = None
        
    async def initialize(self):
        """Initialize the sync service."""
        try:
            # Create database engine
            self.engine = create_async_engine(
                settings.database_url,
                echo=False,
                pool_size=10,
                max_overflow=20
            )
            
            # Create session factory
            self.session_factory = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Initialize API clients
            self.navidrome = await get_navidrome_client()
            self.musicbrainz = await get_musicbrainz_client()
            
            logger.info("Library sync service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize library sync: {e}")
            raise
    
    async def sync_full_library(self) -> Dict[str, Any]:
        """Perform a full library synchronization."""
        sync_id = None
        
        try:
            # Start sync log
            async with self.session_factory() as session:
                sync_log = SyncLog(
                    sync_type="navidrome",
                    status="started",
                    message="Starting full library sync",
                    started_at=datetime.utcnow()
                )
                session.add(sync_log)
                await session.commit()
                await session.refresh(sync_log)
                sync_id = sync_log.id
                
                logger.info(f"Started full library sync (ID: {sync_id})")
            
            # Get library statistics
            library_stats = await self.navidrome.get_library_stats()
            
            # Sync artists
            artists_result = await self._sync_artists()
            
            # Sync albums
            albums_result = await self._sync_albums()
            
            # Sync songs
            songs_result = await self._sync_songs()
            
            # Update sync log
            async with self.session_factory() as session:
                sync_log = await session.get(SyncLog, sync_id)
                if sync_log:
                    sync_log.status = "completed"
                    sync_log.message = "Full library sync completed successfully"
                    sync_log.completed_at = datetime.utcnow()
                    sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()
                    sync_log.items_processed = artists_result["processed"] + albums_result["processed"] + songs_result["processed"]
                    sync_log.items_created = artists_result["created"] + albums_result["created"] + songs_result["created"]
                    sync_log.items_updated = artists_result["updated"] + albums_result["updated"] + songs_result["updated"]
                    sync_log.items_skipped = artists_result["skipped"] + albums_result["skipped"] + songs_result["skipped"]
                    sync_log.items_failed = artists_result["failed"] + albums_result["failed"] + songs_result["failed"]
                    
                    await session.commit()
            
            result = {
                "success": True,
                "sync_id": str(sync_id),
                "artists": artists_result,
                "albums": albums_result,
                "songs": songs_result,
                "total_processed": artists_result["processed"] + albums_result["processed"] + songs_result["processed"],
                "total_created": artists_result["created"] + albums_result["created"] + songs_result["created"],
                "total_updated": artists_result["updated"] + albums_result["updated"] + songs_result["updated"]
            }
            
            logger.info(f"Full library sync completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Full library sync failed: {e}")
            
            # Update sync log with error
            if sync_id:
                try:
                    async with self.session_factory() as session:
                        sync_log = await session.get(SyncLog, sync_id)
                        if sync_log:
                            sync_log.status = "failed"
                            sync_log.message = f"Full library sync failed: {str(e)}"
                            sync_log.completed_at = datetime.utcnow()
                            sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()
                            await session.commit()
                except Exception as log_error:
                    logger.error(f"Failed to update sync log: {log_error}")
            
            return {
                "success": False,
                "error": str(e),
                "sync_id": str(sync_id) if sync_id else None
            }
    
    async def _sync_artists(self) -> Dict[str, int]:
        """Sync artists from Navidrome."""
        result = {"processed": 0, "created": 0, "updated": 0, "skipped": 0, "failed": 0}
        
        try:
            logger.info("Starting artist sync")
            
            # Get all artists from Navidrome
            navidrome_artists = await self.navidrome.get_artists(limit=1000)
            
            async with self.session_factory() as session:
                for navidrome_artist in navidrome_artists:
                    try:
                        result["processed"] += 1
                        
                        navidrome_id = navidrome_artist.get("id")
                        name = navidrome_artist.get("name", "")
                        
                        if not navidrome_id or not name:
                            result["skipped"] += 1
                            continue
                        
                        # Check if artist already exists
                        existing_artist = await session.execute(
                            session.query(Artist).filter(Artist.navidrome_id == navidrome_id)
                        )
                        existing_artist = existing_artist.scalar_one_or_none()
                        
                        if existing_artist:
                            # Update existing artist
                            existing_artist.name = name
                            existing_artist.updated_at = datetime.utcnow()
                            existing_artist.last_synced = datetime.utcnow()
                            result["updated"] += 1
                        else:
                            # Create new artist
                            new_artist = Artist(
                                name=name,
                                navidrome_id=navidrome_id,
                                created_at=datetime.utcnow(),
                                updated_at=datetime.utcnow(),
                                last_synced=datetime.utcnow()
                            )
                            session.add(new_artist)
                            result["created"] += 1
                        
                        # Commit every 50 artists to avoid memory issues
                        if result["processed"] % 50 == 0:
                            await session.commit()
                            logger.info(f"Processed {result['processed']} artists")
                    
                    except Exception as e:
                        logger.error(f"Failed to sync artist {navidrome_artist}: {e}")
                        result["failed"] += 1
                
                # Final commit
                await session.commit()
            
            logger.info(f"Artist sync completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Artist sync failed: {e}")
            result["failed"] += result["processed"]
            return result
    
    async def _sync_albums(self) -> Dict[str, int]:
        """Sync albums from Navidrome."""
        result = {"processed": 0, "created": 0, "updated": 0, "skipped": 0, "failed": 0}
        
        try:
            logger.info("Starting album sync")
            
            # Get all albums from Navidrome
            navidrome_albums = await self.navidrome.get_albums(limit=1000)
            
            async with self.session_factory() as session:
                for navidrome_album in navidrome_albums:
                    try:
                        result["processed"] += 1
                        
                        navidrome_id = navidrome_album.get("id")
                        title = navidrome_album.get("title", "")
                        artist_id = navidrome_album.get("artistId", "")
                        
                        if not navidrome_id or not title or not artist_id:
                            result["skipped"] += 1
                            continue
                        
                        # Find the artist in our database
                        artist = await session.execute(
                            session.query(Artist).filter(Artist.navidrome_id == artist_id)
                        )
                        artist = artist.scalar_one_or_none()
                        
                        if not artist:
                            logger.warning(f"Artist not found for album {title} (artist_id: {artist_id})")
                            result["skipped"] += 1
                            continue
                        
                        # Check if album already exists
                        existing_album = await session.execute(
                            session.query(Album).filter(Album.navidrome_id == navidrome_id)
                        )
                        existing_album = existing_album.scalar_one_or_none()
                        
                        if existing_album:
                            # Update existing album
                            existing_album.title = title
                            existing_album.updated_at = datetime.utcnow()
                            existing_album.last_synced = datetime.utcnow()
                            result["updated"] += 1
                        else:
                            # Create new album
                            new_album = Album(
                                title=title,
                                navidrome_id=navidrome_id,
                                artist_id=artist.id,
                                created_at=datetime.utcnow(),
                                updated_at=datetime.utcnow(),
                                last_synced=datetime.utcnow()
                            )
                            session.add(new_album)
                            result["created"] += 1
                        
                        # Commit every 50 albums
                        if result["processed"] % 50 == 0:
                            await session.commit()
                            logger.info(f"Processed {result['processed']} albums")
                    
                    except Exception as e:
                        logger.error(f"Failed to sync album {navidrome_album}: {e}")
                        result["failed"] += 1
                
                # Final commit
                await session.commit()
            
            logger.info(f"Album sync completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Album sync failed: {e}")
            result["failed"] += result["processed"]
            return result
    
    async def _sync_songs(self) -> Dict[str, int]:
        """Sync songs from Navidrome."""
        result = {"processed": 0, "created": 0, "updated": 0, "skipped": 0, "failed": 0}
        
        try:
            logger.info("Starting song sync")
            
            # Get all songs from Navidrome
            navidrome_songs = await self.navidrome.get_songs(limit=2000)
            
            async with self.session_factory() as session:
                for navidrome_song in navidrome_songs:
                    try:
                        result["processed"] += 1
                        
                        navidrome_id = navidrome_song.get("id")
                        title = navidrome_song.get("title", "")
                        artist_id = navidrome_song.get("artistId", "")
                        album_id = navidrome_song.get("albumId", "")
                        duration = navidrome_song.get("duration", 0)
                        track_number = navidrome_song.get("track", 0)
                        
                        if not navidrome_id or not title or not artist_id or not album_id:
                            result["skipped"] += 1
                            continue
                        
                        # Find the artist and album in our database
                        artist = await session.execute(
                            session.query(Artist).filter(Artist.navidrome_id == artist_id)
                        )
                        artist = artist.scalar_one_or_none()
                        
                        album = await session.execute(
                            session.query(Album).filter(Album.navidrome_id == album_id)
                        )
                        album = album.scalar_one_or_none()
                        
                        if not artist or not album:
                            logger.warning(f"Artist or album not found for song {title}")
                            result["skipped"] += 1
                            continue
                        
                        # Check if song already exists
                        existing_song = await session.execute(
                            session.query(Song).filter(Song.navidrome_id == navidrome_id)
                        )
                        existing_song = existing_song.scalar_one_or_none()
                        
                        if existing_song:
                            # Update existing song
                            existing_song.title = title
                            existing_song.duration = duration
                            existing_song.track_number = track_number
                            existing_song.updated_at = datetime.utcnow()
                            existing_song.last_synced = datetime.utcnow()
                            result["updated"] += 1
                        else:
                            # Create new song
                            new_song = Song(
                                title=title,
                                navidrome_id=navidrome_id,
                                artist_id=artist.id,
                                album_id=album.id,
                                duration=duration,
                                track_number=track_number,
                                created_at=datetime.utcnow(),
                                updated_at=datetime.utcnow(),
                                last_synced=datetime.utcnow()
                            )
                            session.add(new_song)
                            result["created"] += 1
                        
                        # Commit every 100 songs
                        if result["processed"] % 100 == 0:
                            await session.commit()
                            logger.info(f"Processed {result['processed']} songs")
                    
                    except Exception as e:
                        logger.error(f"Failed to sync song {navidrome_song}: {e}")
                        result["failed"] += 1
                
                # Final commit
                await session.commit()
            
            logger.info(f"Song sync completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Song sync failed: {e}")
            result["failed"] += result["processed"]
            return result
    
    async def sync_incremental(self) -> Dict[str, Any]:
        """Perform incremental sync (only new/changed items)."""
        # TODO: Implement incremental sync logic
        # This would check timestamps and only sync items that have changed
        # For now, we'll do a full sync
        return await self.sync_full_library()
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.engine:
                await self.engine.dispose()
            logger.info("Library sync cleanup completed")
        except Exception as e:
            logger.error(f"Library sync cleanup failed: {e}")


# Global sync instance
_library_sync: Optional[LibrarySync] = None


async def get_library_sync() -> LibrarySync:
    """Get or create library sync instance."""
    global _library_sync
    if _library_sync is None:
        _library_sync = LibrarySync()
        await _library_sync.initialize()
    return _library_sync


async def close_library_sync():
    """Close the global library sync instance."""
    global _library_sync
    if _library_sync:
        await _library_sync.cleanup()
        _library_sync = None
