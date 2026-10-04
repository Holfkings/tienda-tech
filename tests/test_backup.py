"""Tests del script de backup (scripts/backup_db.py).

Cubre el fallo silencioso del modo WAL: con `journal_mode=WAL` y el WAL sin
checkpoint, el archivo .db por si solo esta desactualizado. Copiarlo con `cp`
pierde filas y `PRAGMA integrity_check` igual dice "ok". El script oficial usa
la API de backup en linea de sqlite3, que si incluye el WAL.
"""
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "backup_db.py"


def _crear_db_con_wal_sin_checkpoint(db: Path, filas: int):
    """Crea la DB con datos que viven SOLO en el -wal.

    `wal_autocheckpoint=0` desactiva el volcado automatico al .db, y mientras la
    conexion siga abierta nadie hace checkpoint: el .db queda desactualizado a
    proposito, que es exactamente el estado del volumen en produccion.
    """
    con = sqlite3.connect(db)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA wal_autocheckpoint=0")
    con.execute(
        "CREATE TABLE productos (id INTEGER PRIMARY KEY, sku TEXT, nombre TEXT, precio REAL, "
        "stock INTEGER, categoria TEXT, activo INTEGER DEFAULT 1)"
    )
    con.executemany(
        "INSERT INTO productos (sku, nombre, precio, stock, categoria) VALUES (?,?,?,?,?)",
        [(f"SKU-{i}", f"Producto {i}", 1000, 5, "Test") for i in range(filas)],
    )
    con.commit()
    return con  # se mantiene abierta: si se cierra, SQLite puede hacer checkpoint


def _contar(ruta: Path):
    """Filas en `productos`, o None si la copia no tiene ni la tabla."""
    con = sqlite3.connect(ruta)
    try:
        return con.execute("SELECT count(*) FROM productos").fetchone()[0]
    except sqlite3.OperationalError:
        return None
    finally:
        con.close()


def test_copia_simple_del_db_pierde_datos_del_wal(tmp_path):
    """Documenta el bug: `cp tienda.db` NO es un backup valido en modo WAL."""
    db = tmp_path / "tienda.db"
    con = _crear_db_con_wal_sin_checkpoint(db, 300)
    try:
        copia = tmp_path / "copia_simple.db"
        shutil.copyfile(db, copia)

        # La copia es "integra" para SQLite, pero le falta informacion: si el WAL
        # no se volco, puede faltar la tabla entera o solo las filas recientes.
        assert sqlite3.connect(copia).execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        filas_copia = _contar(copia)
        assert filas_copia is None or filas_copia < 300, (
            "si el WAL ya se volco, el escenario no se reprodujo"
        )
        assert _contar(db) == 300
    finally:
        con.close()


def test_backup_db_incluye_el_wal_y_verifica_el_conteo(tmp_path):
    """El script oficial si trae las filas que viven en el WAL, y lo comprueba."""
    db = tmp_path / "tienda.db"
    backups = tmp_path / "backups"
    con = _crear_db_con_wal_sin_checkpoint(db, 300)
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPT), str(db), str(backups)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert "ADVERTENCIA" not in r.stderr

        copias = sorted(backups.glob("tienda-*.db"))
        assert len(copias) == 1, r.stdout
        assert _contar(copias[0]) == 300, "el backup debe incluir los datos del WAL"
        assert sqlite3.connect(copias[0]).execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        con.close()


def test_backup_db_falla_si_no_existe_la_db(tmp_path):
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "no-existe.db"), str(tmp_path / "b")],
        capture_output=True, text=True,
    )
    assert r.returncode == 1
    assert "no existe la DB" in r.stderr


def test_backup_no_deja_archivos_tmp(tmp_path):
    db = tmp_path / "tienda.db"
    backups = tmp_path / "backups"
    con = _crear_db_con_wal_sin_checkpoint(db, 20)
    try:
        subprocess.run([sys.executable, str(SCRIPT), str(db), str(backups)], capture_output=True, text=True)
        assert list(backups.glob("*.tmp")) == []
    finally:
        con.close()
