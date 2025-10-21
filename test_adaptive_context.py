#!/usr/bin/env python3
"""
Script de prueba para el Sistema de Contexto Adaptativo en 3 Niveles

Este script simula diferentes tipos de consultas para mostrar cómo se activa
cada nivel de contexto.

Uso:
    python test_adaptive_context.py
"""

import asyncio
import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.music_agent_service import MusicAgentService


async def test_context_levels():
    """Prueba los 3 niveles de contexto con diferentes queries"""
    
    print("=" * 80)
    print("🧠 TEST: Sistema de Contexto Adaptativo en 3 Niveles")
    print("=" * 80)
    print()
    
    # Inicializar el agente
    print("📊 Inicializando MusicAgentService...")
    agent = MusicAgentService()
    print()
    
    # ID de usuario de prueba
    test_user_id = 12345
    
    # TEST 1: Consulta simple (NIVEL 1)
    print("\n" + "=" * 80)
    print("TEST 1: Consulta Simple → NIVEL 1 (Contexto Mínimo)")
    print("=" * 80)
    print("Query: 'Hola'")
    print("Esperado: Solo contexto mínimo (top 3 artistas)")
    print("-" * 80)
    
    try:
        result = await agent.query("Hola", test_user_id)
        print("✅ Query ejecutada correctamente")
        print(f"Respuesta: {result['answer'][:200]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Esperar un poco para ver los logs
    await asyncio.sleep(2)
    
    # TEST 2: Consulta de recomendación (NIVEL 2)
    print("\n" + "=" * 80)
    print("TEST 2: Recomendación → NIVEL 2 (Contexto Enriquecido)")
    print("=" * 80)
    print("Query: 'Recomiéndame algo de rock'")
    print("Esperado: Contexto mínimo (caché) + contexto enriquecido (nueva consulta)")
    print("-" * 80)
    
    try:
        result = await agent.query("Recomiéndame algo de rock", test_user_id)
        print("✅ Query ejecutada correctamente")
        print(f"Respuesta: {result['answer'][:200]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Esperar un poco para ver los logs
    await asyncio.sleep(2)
    
    # TEST 3: Segunda recomendación (debe usar caché)
    print("\n" + "=" * 80)
    print("TEST 3: Segunda Recomendación → NIVEL 2 (Todo desde caché)")
    print("=" * 80)
    print("Query: 'Recomiéndame algo más tranquilo'")
    print("Esperado: Todo desde caché (debe ser MUY rápido)")
    print("-" * 80)
    
    try:
        result = await agent.query("Recomiéndame algo más tranquilo", test_user_id)
        print("✅ Query ejecutada correctamente")
        print(f"Respuesta: {result['answer'][:200]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Esperar un poco para ver los logs
    await asyncio.sleep(2)
    
    # TEST 4: Consulta de perfil (NIVEL 3)
    print("\n" + "=" * 80)
    print("TEST 4: Consulta de Perfil → NIVEL 3 (Contexto Completo)")
    print("=" * 80)
    print("Query: '¿Cuál es mi artista más escuchado?'")
    print("Esperado: Niveles 1+2 desde caché + nivel 3 nueva consulta")
    print("-" * 80)
    
    try:
        result = await agent.query("¿Cuál es mi artista más escuchado?", test_user_id)
        print("✅ Query ejecutada correctamente")
        print(f"Respuesta: {result['answer'][:200]}...")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Cerrar conexiones
    print("\n" + "=" * 80)
    print("🔒 Cerrando conexiones...")
    await agent.close()
    print("✅ Test completado")
    print("=" * 80)


def main():
    """Función principal"""
    print("""
    ╔═══════════════════════════════════════════════════════════════════════════╗
    ║                                                                           ║
    ║  🧠 TEST DEL SISTEMA DE CONTEXTO ADAPTATIVO EN 3 NIVELES                 ║
    ║                                                                           ║
    ║  Este script prueba los 3 niveles de contexto:                           ║
    ║  • Nivel 1: Contexto mínimo (SIEMPRE) - Top 3 artistas                   ║
    ║  • Nivel 2: Contexto enriquecido - Top 10 + últimas 5 escuchas          ║
    ║  • Nivel 3: Contexto completo - Top 15 + últimas 20 + estadísticas      ║
    ║                                                                           ║
    ║  Observa los logs para ver cómo se activan los cachés y niveles         ║
    ║                                                                           ║
    ╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Verificar variables de entorno
    required_vars = ["GEMINI_API_KEY", "NAVIDROME_URL"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ Error: Faltan variables de entorno: {', '.join(missing)}")
        print("   Asegúrate de tener un archivo .env configurado")
        sys.exit(1)
    
    # Ejecutar tests
    try:
        asyncio.run(test_context_levels())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

