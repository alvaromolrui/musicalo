#!/bin/bash

# Music Assistant - Docker Entrypoint
# This script handles initialization and startup of the music assistant

set -e

echo "🎵 Starting Music Assistant..."

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "✅ PostgreSQL is ready"

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama..."
while ! nc -z ollama 11434; do
  sleep 1
done
echo "✅ Ollama is ready"

# Download Ollama model if not present
echo "⏳ Ensuring Ollama model is available..."
python -c "
import requests
import time
import os
import sys

model = os.getenv('OLLAMA_MODEL', 'qwen2.5:3b')
ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')

def wait_for_ollama():
    '''Wait for Ollama to be ready'''
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(f'{ollama_url}/api/tags', timeout=5)
            if response.status_code == 200:
                return True
        except:
            pass
        print(f'Waiting for Ollama... (attempt {attempt + 1}/{max_attempts})')
        time.sleep(2)
    return False

try:
    if not wait_for_ollama():
        print('❌ Ollama is not responding after 60 seconds')
        sys.exit(1)
    
    # Check if model exists
    response = requests.get(f'{ollama_url}/api/tags', timeout=10)
    if response.status_code == 200:
        models = response.json().get('models', [])
        model_names = [m['name'] for m in models]
        
        if model not in model_names:
            print(f'📥 Downloading model {model}...')
            print('This may take several minutes for the first time...')
            
            # Pull the model with streaming
            pull_response = requests.post(f'{ollama_url}/api/pull', 
                                        json={'name': model, 'stream': True},
                                        stream=True, timeout=300)
            
            if pull_response.status_code == 200:
                for line in pull_response.iter_lines():
                    if line:
                        try:
                            data = line.decode('utf-8')
                            if 'status' in data:
                                print(f'Download progress: {data}')
                        except:
                            pass
                print(f'✅ Model {model} downloaded successfully')
            else:
                print(f'❌ Failed to download model {model}')
                sys.exit(1)
        else:
            print(f'✅ Model {model} already available')
    else:
        print('❌ Could not connect to Ollama API')
        sys.exit(1)
except Exception as e:
    print(f'❌ Error checking Ollama model: {e}')
    sys.exit(1)
"

# Run database migrations
echo "⏳ Running database migrations..."
python -c "
from src.database.models import Base
from src.config import get_database_url
from sqlalchemy import create_engine

try:
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    print('✅ Database migrations completed')
except Exception as e:
    print(f'❌ Database migration failed: {e}')
    exit(1)
"

# Start the application
echo "🚀 Starting Music Assistant application..."
exec python src/startup.py