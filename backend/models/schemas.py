from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class Track(BaseModel):
    id: str
    title: str
    artist: str
    album: str
    duration: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    play_count: Optional[int] = None
    last_played: Optional[datetime] = None
    path: Optional[str] = None
    cover_url: Optional[str] = None

class Album(BaseModel):
    id: str
    name: str
    artist: str
    year: Optional[int] = None
    genre: Optional[str] = None
    track_count: Optional[int] = None
    duration: Optional[int] = None
    cover_url: Optional[str] = None
    play_count: Optional[int] = None

class Artist(BaseModel):
    id: str
    name: str
    album_count: Optional[int] = None
    track_count: Optional[int] = None
    play_count: Optional[int] = None
    genre: Optional[str] = None
    bio: Optional[str] = None
    image_url: Optional[str] = None

class LastFMTrack(BaseModel):
    name: str
    artist: str
    album: Optional[str] = None
    playcount: Optional[int] = None
    date: Optional[datetime] = None
    url: Optional[str] = None
    image_url: Optional[str] = None

class LastFMArtist(BaseModel):
    name: str
    playcount: Optional[int] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    rank: Optional[int] = None

class Recommendation(BaseModel):
    track: Track
    reason: str
    confidence: float
    source: str  # "navidrome", "lastfm", "ai"
    tags: List[str] = []

class UserProfile(BaseModel):
    recent_tracks: List[LastFMTrack] = []
    top_artists: List[LastFMArtist] = []
    favorite_genres: List[str] = []
    mood_preference: str = ""
    activity_context: str = ""
    listening_history: List[Track] = []
    skip_patterns: Dict[str, Any] = {}

class MusicAnalysis(BaseModel):
    genre_distribution: Dict[str, float]
    tempo_preferences: Dict[str, float]
    mood_analysis: Dict[str, float]
    time_patterns: Dict[str, int]
    artist_diversity: float
    discovery_rate: float

class RecommendationRequest(BaseModel):
    user_profile: UserProfile
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None
    exclude_known: bool = True
