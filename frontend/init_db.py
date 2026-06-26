"""
Crea el esquema SQLite para el data layer de Chainlit antes de arrancar la app.
Usa aiosqlite directamente (no depende de los internos de Chainlit).
Es idempotente: CREATE TABLE IF NOT EXISTS no toca tablas existentes.
"""
import asyncio
import os
import sys

DB_PATH = os.getenv("CHAINLIT_DB_PATH", "/app/data/chainlit.db")

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
    "mime"        TEXT
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
        await db.commit()

    print(f"✅ DB schema inicializado: {DB_PATH}")


asyncio.run(main())
