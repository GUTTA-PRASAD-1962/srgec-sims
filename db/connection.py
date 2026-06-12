"""db/connection.py"""
import sqlite3
from pathlib import Path

try:
    from config import DB_PATH
except Exception:
    DB_PATH = "db/sims_data.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def fetchall(sql, params=()):
    conn = get_conn()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def fetchone(sql, params=()):
    conn = get_conn()
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def execute(sql, params=()):
    conn = get_conn()
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()
