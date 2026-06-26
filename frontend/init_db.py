"""
Inicializa el esquema SQLite del data layer de Chainlit.
Se ejecuta una vez al arrancar el contenedor, antes de `chainlit run`.
create_all() es idempotente: no toca tablas que ya existan.
"""
import asyncio
import os
import sys


async def main() -> None:
    db_path = os.getenv("CHAINLIT_DB_PATH", "/app/data/chainlit.db")
    db_url = f"sqlite+aiosqlite:///{db_path}"

    try:
        from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

        layer = SQLAlchemyDataLayer(conninfo=db_url)
        async with layer.engine.begin() as conn:
            await conn.run_sync(layer.metadata.create_all)
        await layer.engine.dispose()
        print(f"✅ DB inicializada: {db_path}")
    except Exception as exc:
        # Si falla, Chainlit arranca igual pero sin historial persistente
        print(f"⚠️  No se pudo inicializar la BD: {exc}", file=sys.stderr)


asyncio.run(main())
