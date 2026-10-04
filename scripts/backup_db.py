#!/usr/bin/env python3
"""
Backup diario de la base SQLite. Solo LEE la DB original.

Usa la API de backup en linea de la stdlib (sqlite3.Connection.backup), asi que
NO necesita el binario `sqlite3` del sistema: funciona igual en Windows local y
en el contenedor de Railway. La copia es consistente aunque la app este escribiendo.

Uso:
    python scripts/backup_db.py                          # usa DATABASE_URL / defaults
    python scripts/backup_db.py /data/tienda.db /data/backups

Variables:
    DATABASE_URL      si no se pasan argumentos (ej: sqlite:////data/tienda.db)
    BACKUP_DIR        carpeta destino (default: <dir_db>/backups)
    RETENTION_DAYS    dias a conservar (default: 7)

IMPORTANTE: la retencion SI ELIMINA archivos de backup mas viejos que RETENTION_DAYS.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def db_path_from_env() -> Path:
    url = os.getenv("DATABASE_URL", "sqlite:///./tienda_dev.db")
    if not url.startswith("sqlite"):
        raise SystemExit(
            f"ERROR: DATABASE_URL no es sqlite ({url}). Este script es solo para SQLite."
        )
    # sqlite:///./x.db -> ./x.db   |   sqlite:////data/x.db -> /data/x.db
    raw = url.split("///", 1)[1] if "///" in url else url
    return Path(raw).expanduser()


def main() -> int:
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else db_path_from_env()
    backup_dir = Path(
        sys.argv[2] if len(sys.argv) > 2 else os.getenv("BACKUP_DIR", str(db.parent / "backups"))
    )
    retention_days = int(os.getenv("RETENTION_DAYS", "7"))

    if not db.is_file():
        print(f"ERROR: no existe la DB en {db}", file=sys.stderr)
        return 1

    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    target = backup_dir / f"tienda-{stamp}.db"

    # Copia consistente y atomica-ish: se escribe en .tmp y luego se renombra.
    tmp = target.with_suffix(".db.tmp")
    src = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(tmp))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    tmp.replace(target)

    # Verificar que el backup sea legible y tenga datos reales.
    chk = sqlite3.connect(str(target))
    try:
        tables = chk.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        try:
            filas = chk.execute("SELECT count(*) FROM productos").fetchone()[0]
        except sqlite3.Error:
            filas = None
        integrity = chk.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        chk.close()

    size = target.stat().st_size
    if tables < 1 or integrity != "ok":
        print(f"ERROR: backup invalido ({tables} tablas, integrity={integrity}), se descarta", file=sys.stderr)
        target.unlink(missing_ok=True)
        return 1

    print(f"OK backup: {target} ({size} bytes, {tables} tablas, productos={filas}, integrity={integrity})")

    # Retencion (ELIMINA archivos)
    limite = time.time() - retention_days * 86400
    borrados = 0
    for viejo in sorted(backup_dir.glob("tienda-*.db")):
        if viejo != target and viejo.stat().st_mtime < limite:
            print(f"  borrando backup viejo: {viejo.name}")
            viejo.unlink()
            borrados += 1
    print(f"Retencion: {retention_days} dias, {borrados} backup(s) eliminado(s)")
    print("Backups actuales:")
    for f in sorted(backup_dir.glob("tienda-*.db")):
        print(f"  {f.name}  {f.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
