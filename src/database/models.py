"""
Database models for Music Assistant.
SQLAlchemy models for storing music library data and metadata.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, 
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

Base = declarative_base()


class Artist(Base):
    """Artist model for storing artist information."""
    
    __tablename__ = "artists"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    mbid = Column(String(36), unique=True, index=True)  # MusicBrainz ID
    navidrome_id = Column(String(50), unique=True, index=True)
    
    # Metadata
    country = Column(String(2))  # ISO country code
    type = Column(String(50))    # Person, Group, Orchestra, etc.
    gender = Column(String(10))  # Male, Female, Other
    disambiguation = Column(Text)
    
    # Enrichment data
    genres = Column(JSONB)  # List of genres/tags
    biography = Column(Text)
    external_urls = Column(JSONB)  # URLs to external services
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced = Column(DateTime)
    
    # Relationships
    albums = relationship("Album", back_populates="artist")
    songs = relationship("Song", back_populates="artist")
    
    # Indexes
    __table_args__ = (
        Index('idx_artist_name_lower', 'name'),
        Index('idx_artist_mbid', 'mbid'),
        Index('idx_artist_navidrome_id', 'navidrome_id'),
    )


class Album(Base):
    """Album model for storing album information."""
    
    __tablename__ = "albums"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, index=True)
    mbid = Column(String(36), unique=True, index=True)  # MusicBrainz ID
    navidrome_id = Column(String(50), unique=True, index=True)
    
    # Foreign keys
    artist_id = Column(UUID(as_uuid=True), ForeignKey("artists.id"), nullable=False)
    
    # Metadata
    release_date = Column(DateTime)
    release_type = Column(String(50))  # Album, EP, Single, etc.
    country = Column(String(2))  # ISO country code
    label = Column(String(255))
    catalog_number = Column(String(100))
    barcode = Column(String(50))
    disambiguation = Column(Text)
    
    # Enrichment data
    genres = Column(JSONB)  # List of genres
    external_urls = Column(JSONB)  # URLs to external services
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced = Column(DateTime)
    
    # Relationships
    artist = relationship("Artist", back_populates="albums")
    songs = relationship("Song", back_populates="album")
    
    # Indexes
    __table_args__ = (
        Index('idx_album_title_lower', 'title'),
        Index('idx_album_artist_id', 'artist_id'),
        Index('idx_album_mbid', 'mbid'),
        Index('idx_album_navidrome_id', 'navidrome_id'),
        Index('idx_album_release_date', 'release_date'),
    )


class Song(Base):
    """Song model for storing song/track information."""
    
    __tablename__ = "songs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, index=True)
    mbid = Column(String(36), unique=True, index=True)  # MusicBrainz ID
    navidrome_id = Column(String(50), unique=True, index=True)
    
    # Foreign keys
    artist_id = Column(UUID(as_uuid=True), ForeignKey("artists.id"), nullable=False)
    album_id = Column(UUID(as_uuid=True), ForeignKey("albums.id"), nullable=False)
    
    # Metadata
    track_number = Column(Integer)
    disc_number = Column(Integer, default=1)
    duration = Column(Integer)  # Duration in seconds
    bitrate = Column(Integer)
    format = Column(String(10))  # mp3, flac, etc.
    size = Column(Integer)  # File size in bytes
    
    # Enrichment data
    genres = Column(JSONB)  # List of genres
    external_urls = Column(JSONB)  # URLs to external services
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced = Column(DateTime)
    
    # Relationships
    artist = relationship("Artist", back_populates="songs")
    album = relationship("Album", back_populates="songs")
    plays = relationship("Play", back_populates="song")
    
    # Indexes
    __table_args__ = (
        Index('idx_song_title_lower', 'title'),
        Index('idx_song_artist_id', 'artist_id'),
        Index('idx_song_album_id', 'album_id'),
        Index('idx_song_mbid', 'mbid'),
        Index('idx_song_navidrome_id', 'navidrome_id'),
        Index('idx_song_duration', 'duration'),
    )


class Play(Base):
    """Play model for storing listening history from ListenBrainz."""
    
    __tablename__ = "plays"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    song_id = Column(UUID(as_uuid=True), ForeignKey("songs.id"), nullable=False)
    
    # ListenBrainz data
    listenbrainz_id = Column(String(50), unique=True, index=True)
    listened_at = Column(DateTime, nullable=False, index=True)
    
    # Metadata
    source = Column(String(50))  # ListenBrainz, Navidrome, etc.
    additional_info = Column(JSONB)  # Additional metadata
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    song = relationship("Song", back_populates="plays")
    
    # Indexes
    __table_args__ = (
        Index('idx_play_song_id', 'song_id'),
        Index('idx_play_listened_at', 'listened_at'),
        Index('idx_play_listenbrainz_id', 'listenbrainz_id'),
        Index('idx_play_source', 'source'),
    )


class Playlist(Base):
    """Playlist model for storing playlist information."""
    
    __tablename__ = "playlists"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    navidrome_id = Column(String(50), unique=True, index=True)
    
    # Metadata
    description = Column(Text)
    is_public = Column(Boolean, default=False)
    owner = Column(String(100))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced = Column(DateTime)
    
    # Relationships
    playlist_songs = relationship("PlaylistSong", back_populates="playlist")
    
    # Indexes
    __table_args__ = (
        Index('idx_playlist_name_lower', 'name'),
        Index('idx_playlist_navidrome_id', 'navidrome_id'),
        Index('idx_playlist_owner', 'owner'),
    )


class PlaylistSong(Base):
    """Junction table for playlist-song relationships."""
    
    __tablename__ = "playlist_songs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    playlist_id = Column(UUID(as_uuid=True), ForeignKey("playlists.id"), nullable=False)
    song_id = Column(UUID(as_uuid=True), ForeignKey("songs.id"), nullable=False)
    
    # Ordering
    position = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    playlist = relationship("Playlist", back_populates="playlist_songs")
    song = relationship("Song")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('playlist_id', 'song_id', name='uq_playlist_song'),
        Index('idx_playlist_song_playlist_id', 'playlist_id'),
        Index('idx_playlist_song_song_id', 'song_id'),
        Index('idx_playlist_song_position', 'position'),
    )


class SyncLog(Base):
    """Sync log model for tracking synchronization operations."""
    
    __tablename__ = "sync_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Sync information
    sync_type = Column(String(50), nullable=False)  # navidrome, listenbrainz, musicbrainz
    status = Column(String(20), nullable=False)  # started, completed, failed
    message = Column(Text)
    
    # Statistics
    items_processed = Column(Integer, default=0)
    items_created = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    items_skipped = Column(Integer, default=0)
    items_failed = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    
    # Additional data
    sync_metadata = Column(JSONB)
    
    # Indexes
    __table_args__ = (
        Index('idx_sync_log_type', 'sync_type'),
        Index('idx_sync_log_status', 'status'),
        Index('idx_sync_log_started_at', 'started_at'),
    )


class Embedding(Base):
    """Embedding model for storing vector embeddings."""
    
    __tablename__ = "embeddings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Entity information
    entity_type = Column(String(50), nullable=False)  # song, album, artist
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Embedding information
    model_name = Column(String(100), nullable=False)
    embedding_dimension = Column(Integer, nullable=False)
    
    # Text that was embedded
    text_content = Column(Text, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_embedding_entity_type', 'entity_type'),
        Index('idx_embedding_entity_id', 'entity_id'),
        Index('idx_embedding_model_name', 'model_name'),
        UniqueConstraint('entity_type', 'entity_id', 'model_name', name='uq_embedding_entity_model'),
    )
