#!/usr/bin/env python3
"""
Musicalo - Script de inicio

Ejecuta el bot de Telegram con la configuración apropiada.
"""

import sys
import os
from pathlib import Path

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Cambiar al directorio backend
os.chdir(backend_dir)

# Importar y ejecutar el bot
from bot import main

if __name__ == "__main__":
    print("🎵 Iniciando Musicalo...")
    print("📱 Busca tu bot en Telegram y escribe /start para comenzar")
    print("🛑 Presiona Ctrl+C para detener el bot")
    print("-" * 50)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido por el usuario")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
