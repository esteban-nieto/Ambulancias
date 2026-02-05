import sqlite3
from datetime import datetime
from typing import Any


def init_db():
    conn = sqlite3.connect("historias.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            contrasena TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS historias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consecutivo TEXT,
            usuario TEXT,
            paciente TEXT,
            edad TEXT,
            motivo TEXT,
            diagnostico TEXT,
            tratamiento TEXT,
            fecha_creacion TEXT,
            estado TEXT
        )
    """)
    conn.commit()
    conn.close()

def crear_usuario(usuario: str, contrasena: str):
    conn = sqlite3.connect("historias.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO usuarios (usuario, contrasena) VALUES (?, ?)", (usuario, contrasena))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

def validar_usuario(usuario: str, contrasena: str) -> bool:
    conn = sqlite3.connect("historias.db")
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE usuario=? AND contrasena=?", (usuario, contrasena))
    valido = c.fetchone() is not None
    conn.close()
    return valido

def obtener_consecutivo():
    conn = sqlite3.connect("historias.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM historias")
    total = c.fetchone()[0] + 1
    conn.close()
    return f"HC-2026-{total:04d}"

def guardar_historia(
    consecutivo: str,
    usuario: str,
    paciente: str,
    edad: str,
    motivo: str,
    diagnostico: str,
    tratamiento: str,
    estado: str = "incompleta"
) -> None:
    conn = sqlite3.connect("historias.db")
    c = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO historias (consecutivo, usuario, paciente, edad, motivo, diagnostico, tratamiento, fecha_creacion, estado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (consecutivo, usuario, paciente, edad, motivo, diagnostico, tratamiento, fecha, estado))
    conn.commit()
    conn.close()

def obtener_historias_por_estado(usuario: str, estado: str) -> list[Any]:
    conn = sqlite3.connect("historias.db")
    c = conn.cursor()
    # Devolver las columnas en el orden que usa la interfaz para mostrar (consecutivo, usuario, paciente, edad, motivo, diagnóstico, tratamiento)
    c.execute("""
        SELECT consecutivo, usuario, paciente, edad, motivo, diagnostico, tratamiento
        FROM historias
        WHERE usuario=? AND estado=?
        ORDER BY fecha_creacion DESC
    """, (usuario, estado))
    data = c.fetchall()
    conn.close()
    return data
