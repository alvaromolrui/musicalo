#!/usr/bin/env python3
"""
Script de prueba para verificar la creación de playlists en Navidrome
"""

import asyncio
import os
from dotenv import load_dotenv
from backend.services.music_agent_service import MusicAgentService

async def test_playlist_creation():
    """Probar la creación de playlists"""
    
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar que las variables necesarias estén configuradas
    required_vars = [
        "NAVIDROME_URL",
        "NAVIDROME_USERNAME", 
        "NAVIDROME_PASSWORD",
        "GEMINI_API_KEY"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Variables de entorno faltantes: {missing_vars}")
        return
    
    print("✅ Variables de entorno configuradas")
    
    # Crear instancia del agente
    agent = MusicAgentService()
    
    try:
        # Probar conexión con Navidrome
        print("🔍 Probando conexión con Navidrome...")
        navidrome_ok = await agent.navidrome.test_connection()
        
        if not navidrome_ok:
            print("❌ No se pudo conectar con Navidrome")
            return
        
        print("✅ Conexión con Navidrome exitosa")
        
        # Probar creación de playlist
        test_queries = [
            "crea una playlist de rock",
            "playlist de jazz suave",
            "haz una playlist con música de Queen"
        ]
        
        for query in test_queries:
            print(f"\n🎵 Probando: '{query}'")
            
            try:
                result = await agent.query(query, user_id=12345)
                
                if result.get('success'):
                    print(f"✅ Respuesta generada: {len(result['answer'])} caracteres")
                    
                    if result.get('playlist_created'):
                        playlist = result['playlist_created']
                        print(f"🎵 Playlist creada:")
                        print(f"   - Nombre: {playlist['name']}")
                        print(f"   - ID: {playlist['id']}")
                        print(f"   - Canciones: {playlist['track_count']}")
                    else:
                        print("⚠️ No se creó playlist (posiblemente no se encontraron canciones)")
                else:
                    print(f"❌ Error: {result.get('answer', 'Error desconocido')}")
                    
            except Exception as e:
                print(f"❌ Error procesando consulta: {e}")
    
    finally:
        # Cerrar conexiones
        await agent.close()
        print("\n✅ Conexiones cerradas")

if __name__ == "__main__":
    asyncio.run(test_playlist_creation())
