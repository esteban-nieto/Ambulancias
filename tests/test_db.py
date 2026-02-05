import sqlite3
import db

import pytest

@pytest.fixture
def conn(monkeypatch, tmp_path):
    # Usar un archivo de base de datos temporal para que múltiples conexiones funcionen correctamente
    db_path = tmp_path / "test_historias.db"

    # Guardar la función original para evitar recursión cuando reemplacemos connect
    original_connect = sqlite3.connect

    def connect(*args, **kwargs):
        return original_connect(str(db_path))

    monkeypatch.setattr(db.sqlite3, "connect", connect)
    return db_path


def test_init_and_user_ops(conn):
    db.init_db()
    # Crear usuario y validar
    db.crear_usuario("usuario1", "pass1")
    assert db.validar_usuario("usuario1", "pass1") is True
    assert db.validar_usuario("usuario1", "wrong") is False


def test_guardar_y_obtener(conn):
    db.init_db()
    consec = db.obtener_consecutivo()
    db.crear_usuario("u2", "p2")
    db.guardar_historia(consec, "u2", "Paciente X", "40", "Dolor", "Dx probable", "Tx")

    rows = db.obtener_historias_por_estado("u2", "incompleta")
    assert len(rows) == 1
    row = rows[0]
    # Orden de columnas: consecutivo, usuario, paciente, edad, motivo, diagnostico, tratamiento
    assert row[0] == consec
    assert row[1] == "u2"
    assert row[2] == "Paciente X"
    assert row[3] == "40"
    assert row[4] == "Dolor"
