# Music Assistant 🎵

An AI-powered music library assistant that helps you discover, organize, and explore your music collection through natural language conversations via Telegram.

## Features

- **Smart Music Discovery**: Ask questions about your music library in natural language
- **Library Integration**: Connects to your Navidrome music server
- **Listening Analytics**: Analyzes your listening patterns via ListenBrainz
- **Music Metadata**: Enriches your library with MusicBrainz data
- **Vector Search**: Semantic search through your music collection
- **Local AI**: Runs entirely on your hardware using Ollama

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │   Music Agent   │    │   Data Layer    │
│                 │◄──►│   (LangChain)   │◄──►│                 │
│ - User Interface│    │                 │    │ - PostgreSQL    │
│ - Commands      │    │ - RAG System    │    │ - ChromaDB      │
│ - Auth          │    │ - Tools         │    │ - Vector Store  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   External APIs │
                       │                 │
                       │ - Navidrome     │
                       │ - ListenBrainz  │
                       │ - MusicBrainz   │
                       └─────────────────┘
```

## System Requirements

- **RAM**: Minimum 8GB (recommended 16GB)
- **Storage**: 10GB free space
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd music-assistant
cp env.template .env
```

### 2. Configure Environment

Edit `.env` file with your credentials:

```env
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ALLOWED_USERS=123456789
NAVIDROME_URL=http://your-navidrome:4533
NAVIDROME_USERNAME=admin
NAVIDROME_PASSWORD=your_password
LISTENBRAINZ_TOKEN=your_token
LISTENBRAINZ_USERNAME=your_username
POSTGRES_PASSWORD=secure_password
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Initialize Ollama Model

The first startup will automatically download the `qwen2.5:3b` model (~2GB). This may take a few minutes.

### 5. Start Using

1. Find your bot on Telegram
2. Send `/start` to begin
3. Try asking: "What are my most played artists this month?"

## Commands

- `/start` - Initialize the bot
- `/help` - Show available commands
- `/sync` - Manually sync your music library
- `/stats` - Show library statistics

## Example Queries

- "What indie rock albums do I have?"
- "Show me my most played songs this week"
- "Find songs similar to Radiohead"
- "What new music did I add recently?"
- "Recommend something based on my listening history"

## Configuration

### Resource Limits

The system is optimized for limited resources:

- **PostgreSQL**: 512MB RAM limit
- **Ollama**: 3GB RAM limit  
- **Music Assistant**: 2GB RAM limit

### Customization

- **AI Model**: Change `OLLAMA_MODEL` in `.env`
- **Sync Interval**: Adjust `SYNC_INTERVAL` (default: 1 hour)
- **Log Level**: Set `LOG_LEVEL` (DEBUG, INFO, WARNING, ERROR)

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check `TELEGRAM_BOT_TOKEN` and user permissions
2. **Library sync fails**: Verify Navidrome credentials and URL
3. **High memory usage**: Reduce `OLLAMA_MODEL` size or adjust resource limits
4. **Slow responses**: Check if Ollama model is fully loaded

### Logs

```bash
# View application logs
docker-compose logs -f music_assistant

# View all services
docker-compose logs -f
```

### Health Check

```bash
# Check service status
docker-compose ps

# Test database connection
docker-compose exec music_assistant python -c "from src.database.models import engine; print('DB OK')"
```

## Development

### Project Structure

```
src/
├── main.py              # Telegram bot entry point
├── agent.py             # AI agent with LangChain
├── config.py            # Configuration management
├── tools/               # API clients and utilities
│   ├── navidrome.py     # Navidrome API client
│   ├── listenbrainz.py  # ListenBrainz API client
│   ├── musicbrainz.py   # MusicBrainz API client
│   └── vector_search.py # Vector search utilities
├── ingestion/           # Data synchronization
│   ├── sync_library.py  # Library sync process
│   ├── embeddings.py    # Embedding generation
│   └── enrichment.py    # Metadata enrichment
└── database/            # Data layer
    ├── models.py        # SQLAlchemy models
    ├── vector_store.py  # ChromaDB wrapper
    └── repository.py    # Data repository
```

### Adding New Features

1. Create tool in `src/tools/`
2. Register with agent in `src/agent.py`
3. Add database models if needed
4. Update documentation

## Security

- **User Whitelist**: Only authorized Telegram users can access
- **Environment Variables**: All secrets stored in environment
- **Non-root Container**: Application runs as non-privileged user
- **Network Isolation**: Services communicate through internal network

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error messages
3. Open an issue with detailed information

---

**Note**: This assistant runs entirely on your hardware. No data is sent to external AI services except for the configured APIs (Navidrome, ListenBrainz, MusicBrainz).