"""
Music Assistant AI Agent.
LangChain-based agent for processing music-related queries.
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from loguru import logger
from langchain_community.llms import Ollama
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage, HumanMessage, AIMessage

from config import settings
from tools.navidrome import get_navidrome_client
from tools.listenbrainz import get_listenbrainz_client
from tools.musicbrainz import get_musicbrainz_client
from database.vector_store import get_vector_store


class MusicAgent:
    """AI agent for processing music-related queries."""
    
    def __init__(self):
        self.llm = None
        self.agent_executor = None
        self.tools = []
        self.vector_store = None
        
    async def initialize(self):
        """Initialize the agent and its components."""
        try:
            # Initialize LLM
            self.llm = Ollama(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                temperature=0.7
            )
            
            # Initialize vector store
            self.vector_store = await get_vector_store()
            
            # Initialize tools
            await self._initialize_tools()
            
            # Create agent
            await self._create_agent()
            
            logger.info("Music Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Music Agent: {e}")
            raise
    
    async def _initialize_tools(self):
        """Initialize tools for the agent."""
        self.tools = [
            Tool(
                name="search_library",
                description="Search the user's music library for songs, albums, or artists. Use this for finding specific music.",
                func=self._search_library_sync
            ),
            Tool(
                name="get_listening_stats",
                description="Get listening statistics and top artists/songs from ListenBrainz. Use this for analytics queries.",
                func=self._get_listening_stats_sync
            ),
            Tool(
                name="get_library_stats",
                description="Get basic library statistics (total artists, albums, songs). Use this for general library info.",
                func=self._get_library_stats_sync
            ),
            Tool(
                name="search_similar_music",
                description="Find similar artists or music based on a given artist or song. Use this for recommendations.",
                func=self._search_similar_music_sync
            ),
            Tool(
                name="get_recent_listens",
                description="Get recently played songs from ListenBrainz. Use this for recent activity queries.",
                func=self._get_recent_listens_sync
            )
        ]
    
    async def _create_agent(self):
        """Create the LangChain agent."""
        try:
            # Create prompt template
            prompt = PromptTemplate.from_template("""
You are a helpful music assistant that helps users explore their music library and listening habits.

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}
""")
            
            # Create agent
            agent = create_react_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prompt
            )
            
            # Create agent executor
            self.agent_executor = AgentExecutor(
                agent=agent,
                tools=self.tools,
                verbose=True,
                max_iterations=5,
                early_stopping_method="generate",
                handle_parsing_errors=True
            )
            
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise
    
    async def process_query(self, query: str) -> str:
        """Process a user query and return a response."""
        try:
            logger.info(f"Processing query: {query}")
            
            # Use the agent to process the query
            result = await self.agent_executor.ainvoke({"input": query})
            
            response = result.get("output", "I'm sorry, I couldn't process your request.")
            
            logger.info(f"Query processed successfully")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process query: {e}")
            return f"I'm sorry, I encountered an error while processing your request: {str(e)}"
    
    async def sync_library(self) -> Dict[str, Any]:
        """Sync the music library from Navidrome."""
        try:
            logger.info("Starting library sync")
            start_time = datetime.now()
            
            # Import sync modules
            from ingestion.sync_library import get_library_sync
            from ingestion.embeddings import get_embedding_generator
            
            # Perform library sync
            library_sync = await get_library_sync()
            sync_result = await library_sync.sync_full_library()
            
            if not sync_result.get("success"):
                return sync_result
            
            # Generate embeddings for new content
            embedding_generator = await get_embedding_generator()
            embedding_result = await embedding_generator.generate_all_embeddings()
            
            duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                "success": True,
                "artists": sync_result.get("artists", {}).get("created", 0),
                "albums": sync_result.get("albums", {}).get("created", 0),
                "songs": sync_result.get("songs", {}).get("created", 0),
                "embeddings_created": (
                    embedding_result.get("artists", {}).get("created", 0) +
                    embedding_result.get("albums", {}).get("created", 0) +
                    embedding_result.get("songs", {}).get("created", 0)
                ),
                "duration": f"{duration:.1f}s"
            }
            
            logger.info(f"Library sync completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Library sync failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_library_stats(self) -> Dict[str, Any]:
        """Get comprehensive library and listening statistics."""
        try:
            # Get library stats from Navidrome
            navidrome = await get_navidrome_client()
            library_stats = await navidrome.get_library_stats()
            
            # Get listening stats from ListenBrainz
            listenbrainz = await get_listenbrainz_client()
            weekly_stats = await listenbrainz.get_weekly_stats()
            
            # Get vector store stats
            vector_stats = await self.vector_store.get_collection_stats()
            
            return {
                "library": library_stats,
                "listening": {
                    "total_plays": len(weekly_stats.get("top_recordings", [])),
                    "week_plays": len(weekly_stats.get("top_recordings", [])),
                    "month_plays": len(weekly_stats.get("top_recordings", [])),
                    "top_artists": weekly_stats.get("top_artists", [])[:5]
                },
                "vector_store": vector_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get library stats: {e}")
            return {
                "library": {"artists": 0, "albums": 0, "songs": 0},
                "listening": {"total_plays": 0, "week_plays": 0, "month_plays": 0, "top_artists": []},
                "vector_store": {"songs": 0, "albums": 0, "artists": 0, "total": 0}
            }
    
    # Tool functions
    async def _search_library(self, query: str) -> str:
        """Search the music library."""
        try:
            # Use vector search
            results = await self.vector_store.search_all(query, limit=5)
            
            response = "🔍 **Search Results:**\n\n"
            
            if results["songs"]:
                response += "🎵 **Songs:**\n"
                for song in results["songs"][:3]:
                    response += f"• {song['title']} by {song['artist_name']}\n"
                response += "\n"
            
            if results["albums"]:
                response += "💿 **Albums:**\n"
                for album in results["albums"][:3]:
                    response += f"• {album['title']} by {album['artist_name']}\n"
                response += "\n"
            
            if results["artists"]:
                response += "🎤 **Artists:**\n"
                for artist in results["artists"][:3]:
                    response += f"• {artist['name']}\n"
                response += "\n"
            
            if not any(results.values()):
                response = "No results found for your search."
            
            return response
            
        except Exception as e:
            logger.error(f"Library search failed: {e}")
            return f"Search failed: {str(e)}"
    
    async def _get_listening_stats(self, query: str) -> str:
        """Get listening statistics."""
        try:
            listenbrainz = await get_listenbrainz_client()
            weekly_stats = await listenbrainz.get_weekly_stats()
            
            response = "📊 **Your Listening Statistics:**\n\n"
            
            if weekly_stats.get("top_artists"):
                response += "🏆 **Top Artists This Week:**\n"
                for i, artist in enumerate(weekly_stats["top_artists"][:5], 1):
                    name = artist.get("artist_name", "Unknown")
                    plays = artist.get("play_count", 0)
                    response += f"{i}. {name} ({plays} plays)\n"
                response += "\n"
            
            if weekly_stats.get("top_recordings"):
                response += "🎵 **Top Songs This Week:**\n"
                for i, song in enumerate(weekly_stats["top_recordings"][:5], 1):
                    title = song.get("track_name", "Unknown")
                    artist = song.get("artist_name", "Unknown")
                    plays = song.get("play_count", 0)
                    response += f"{i}. {title} by {artist} ({plays} plays)\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Listening stats failed: {e}")
            return f"Failed to get listening statistics: {str(e)}"
    
    async def _get_library_stats(self, query: str) -> str:
        """Get basic library statistics."""
        try:
            navidrome = await get_navidrome_client()
            stats = await navidrome.get_library_stats()
            
            response = (
                f"📚 **Your Music Library:**\n\n"
                f"🎤 Artists: {stats.get('artists', 0)}\n"
                f"💿 Albums: {stats.get('albums', 0)}\n"
                f"🎵 Songs: {stats.get('songs', 0)}\n"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Library stats failed: {e}")
            return f"Failed to get library statistics: {str(e)}"
    
    async def _search_similar_music(self, query: str) -> str:
        """Search for similar music."""
        try:
            # Use vector search to find similar content
            results = await self.vector_store.search_all(query, limit=10)
            
            response = f"🎧 **Music similar to '{query}':**\n\n"
            
            if results["songs"]:
                response += "🎵 **Similar Songs:**\n"
                for song in results["songs"][:5]:
                    similarity = int(song.get("similarity", 0) * 100)
                    response += f"• {song['title']} by {song['artist_name']} ({similarity}% match)\n"
                response += "\n"
            
            if results["artists"]:
                response += "🎤 **Similar Artists:**\n"
                for artist in results["artists"][:5]:
                    similarity = int(artist.get("similarity", 0) * 100)
                    response += f"• {artist['name']} ({similarity}% match)\n"
            
            if not any(results.values()):
                response = f"No similar music found for '{query}'."
            
            return response
            
        except Exception as e:
            logger.error(f"Similar music search failed: {e}")
            return f"Failed to find similar music: {str(e)}"
    
    async def _get_recent_listens(self, query: str) -> str:
        """Get recent listening activity."""
        try:
            listenbrainz = await get_listenbrainz_client()
            recent_listens = await listenbrainz.get_recent_listens(hours=24)
            
            response = "🕐 **Recent Listening Activity (Last 24 hours):**\n\n"
            
            if recent_listens:
                for i, listen in enumerate(recent_listens[:10], 1):
                    track = listen.get("track_metadata", {})
                    title = track.get("track_name", "Unknown")
                    artist = track.get("artist_name", "Unknown")
                    listened_at = listen.get("listened_at", "")
                    
                    # Format timestamp
                    if listened_at:
                        try:
                            dt = datetime.fromisoformat(listened_at.replace('Z', '+00:00'))
                            time_str = dt.strftime("%H:%M")
                        except:
                            time_str = "Unknown time"
                    else:
                        time_str = "Unknown time"
                    
                    response += f"{i}. {title} by {artist} ({time_str})\n"
            else:
                response += "No recent listening activity found."
            
            return response
            
        except Exception as e:
            logger.error(f"Recent listens failed: {e}")
            return f"Failed to get recent listening activity: {str(e)}"
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            # Close API clients
            from tools.navidrome import close_navidrome_client
            from tools.listenbrainz import close_listenbrainz_client
            from tools.musicbrainz import close_musicbrainz_client
            from database.vector_store import close_vector_store
            
            await close_navidrome_client()
            await close_listenbrainz_client()
            await close_musicbrainz_client()
            await close_vector_store()
            
            logger.info("Music Agent cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    # Synchronous wrapper functions for LangChain tools
    def _search_library_sync(self, query: str) -> str:
        """Synchronous wrapper for search_library."""
        import asyncio
        try:
            # Try to get existing loop, create new one if none exists
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, we need to run in a new thread
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self._search_library(query))
                        return future.result()
                else:
                    return loop.run_until_complete(self._search_library(query))
            except RuntimeError:
                # No event loop, create new one
                return asyncio.run(self._search_library(query))
        except Exception as e:
            return f"Error searching library: {str(e)}"
    
    def _get_library_stats_sync(self, query: str = "") -> str:
        """Synchronous wrapper for get_library_stats."""
        import asyncio
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self._get_library_stats(query))
                        return future.result()
                else:
                    return loop.run_until_complete(self._get_library_stats(query))
            except RuntimeError:
                return asyncio.run(self._get_library_stats(query))
        except Exception as e:
            return f"Error getting library stats: {str(e)}"
    
    def _get_listening_stats_sync(self, query: str) -> str:
        """Synchronous wrapper for get_listening_stats."""
        import asyncio
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self._get_listening_stats(query))
                        return future.result()
                else:
                    return loop.run_until_complete(self._get_listening_stats(query))
            except RuntimeError:
                return asyncio.run(self._get_listening_stats(query))
        except Exception as e:
            return f"Error getting listening stats: {str(e)}"
    
    def _get_recent_listens_sync(self, query: str = "") -> str:
        """Synchronous wrapper for get_recent_listens."""
        import asyncio
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self._get_recent_listens(query))
                        return future.result()
                else:
                    return loop.run_until_complete(self._get_recent_listens(query))
            except RuntimeError:
                return asyncio.run(self._get_recent_listens(query))
        except Exception as e:
            return f"Error getting recent listens: {str(e)}"
    
    def _search_similar_music_sync(self, query: str) -> str:
        """Synchronous wrapper for search_similar_music."""
        import asyncio
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self._search_similar_music(query))
                        return future.result()
                else:
                    return loop.run_until_complete(self._search_similar_music(query))
            except RuntimeError:
                return asyncio.run(self._search_similar_music(query))
        except Exception as e:
            return f"Error searching similar music: {str(e)}"
