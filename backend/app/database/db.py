"""
MetricMind SQLite Database Access Layer
Maintains the application database, table creation, indexing, and parameterized query execution.
"""
import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from ..config import settings

def get_db_path() -> Path:
    db_file = Path(settings.DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return db_file

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()))
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(sql: str, params: tuple | dict | None = None) -> List[Dict[str, Any]]:
    """Executes a parameterized SQL query safely and returns a list of dictionaries."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def execute_script(script: str):
    conn = get_connection()
    try:
        conn.executescript(script)
        conn.commit()
    finally:
        conn.close()
