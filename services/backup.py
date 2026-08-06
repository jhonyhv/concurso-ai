from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from database.database import DB_PATH

REQUIRED_TABLES = {"questions", "attempts", "settings"}


def backup_bytes() -> bytes:
    if not DB_PATH.exists():
        return b""
    return DB_PATH.read_bytes()


def backup_filename() -> str:
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    return f"concursoai-backup-{stamp}.db"


def validate_database(path: Path) -> None:
    try:
        with sqlite3.connect(path) as connection:
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    except sqlite3.DatabaseError as exc:
        raise ValueError("O arquivo enviado não é um banco SQLite válido.") from exc
    if integrity != "ok":
        raise ValueError("O banco enviado falhou na verificação de integridade.")
    missing = REQUIRED_TABLES - tables
    if missing:
        raise ValueError("O banco não possui a estrutura do ConcursoAI.")


def restore_database(uploaded_bytes: bytes) -> None:
    if not uploaded_bytes:
        raise ValueError("O arquivo está vazio.")
    temporary = DB_PATH.with_suffix(".restore.tmp")
    temporary.write_bytes(uploaded_bytes)
    try:
        validate_database(temporary)
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        for suffix in ("-wal", "-shm"):
            DB_PATH.with_name(DB_PATH.name + suffix).unlink(missing_ok=True)
        temporary.replace(DB_PATH)
    finally:
        temporary.unlink(missing_ok=True)
