"""
Crea el esquema SQLite para el data layer de Chainlit antes de arrancar la app.
Usa aiosqlite directamente (no depende de los internos de Chainlit).
Es idempotente: CREATE TABLE IF NOT EXISTS no toca tablas existentes.
También migra threads existentes sin userIdentifier.
"""
import asyncio
import os

DB_PATH = os.getenv("CHAINLIT_DB_PATH", "/app/data/chainlit.db")
DEFAULT_USER = os.getenv("CHAINLIT_DEFAULT_USER", "musicalo")

# Esquema derivado de los SQL que emite SQLAlchemyDataLayer de Chainlit 2.x
_SCHEMA = """
CREATE TABLE IF NOT EXISTS "users" (
    "id"         TEXT PRIMARY KEY,
    "identifier" TEXT NOT NULL UNIQUE,
    "createdAt"  TEXT,
    "metadata"   TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS "threads" (
    "id"             TEXT PRIMARY KEY,
    "createdAt"      TEXT,
    "name"           TEXT,
    "userId"         TEXT REFERENCES "users"("id"),
    "userIdentifier" TEXT,
    "tags"           TEXT,
    "metadata"       TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS "steps" (
    "id"           TEXT PRIMARY KEY,
    "name"         TEXT NOT NULL,
    "type"         TEXT NOT NULL,
    "threadId"     TEXT NOT NULL,
    "parentId"     TEXT,
    "streaming"    INTEGER NOT NULL DEFAULT 0,
    "waitForAnswer" INTEGER,
    "isError"      INTEGER,
    "metadata"     TEXT,
    "tags"         TEXT,
    "input"        TEXT,
    "output"       TEXT,
    "createdAt"    TEXT,
    "start"        TEXT,
    "end"          TEXT,
    "generation"   TEXT,
    "showInput"    TEXT,
    "language"     TEXT,
    "defaultOpen"  INTEGER,
    "autoCollapse" INTEGER
);

CREATE TABLE IF NOT EXISTS "elements" (
    "id"          TEXT PRIMARY KEY,
    "threadId"    TEXT,
    "type"        TEXT,
    "url"         TEXT,
    "chainlitKey" TEXT,
    "name"        TEXT NOT NULL,
    "display"     TEXT,
    "objectKey"   TEXT,
    "size"        TEXT,
    "page"        INTEGER,
    "language"    TEXT,
    "forId"       TEXT,
    "mime"        TEXT,
    "props"       TEXT
);

CREATE TABLE IF NOT EXISTS "feedbacks" (
    "id"       TEXT PRIMARY KEY,
    "forId"    TEXT NOT NULL,
    "threadId" TEXT NOT NULL,
    "value"    INTEGER NOT NULL,
    "comment"  TEXT
);
"""


async def main() -> None:
    import aiosqlite

    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(_SCHEMA)

        # Migraciones de columnas: ALTER TABLE falla si la columna ya existe;
        # lo ignoramos para que init_db.py sea idempotente.
        # Chainlit 2.11.1 consulta steps.language y elements.props, que no
        # estaban en el esquema original → get_thread fallaba en toda carga.
        for table, column, col_type in [
            ("steps",    "language", "TEXT"),
            ("elements", "props",    "TEXT"),
        ]:
            try:
                await db.execute(
                    f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_type}'
                )
            except Exception:
                pass  # columna ya existe

        # Migración: threads sin userIdentifier no aparecen en list_threads.
        # Chainlit 2.11.1 no persiste userIdentifier en el INSERT, así que
        # asignamos el usuario por defecto a todos los threads que tengan pasos
        # (conversaciones reales) pero no tengan autor asignado.
        cur = await db.execute(
            """UPDATE "threads"
               SET "userIdentifier" = ?,
                   "userId" = (SELECT "id" FROM "users" WHERE "identifier" = ? LIMIT 1)
               WHERE "userIdentifier" IS NULL
                 AND "id" IN (SELECT DISTINCT "threadId" FROM "steps")""",
            (DEFAULT_USER, DEFAULT_USER),
        )
        migrated = cur.rowcount
        await db.commit()

    print(f"✅ DB schema inicializado: {DB_PATH}")
    if migrated:
        print(f"   Migrados {migrated} thread(s) sin userIdentifier → '{DEFAULT_USER}'")


asyncio.run(main())
