"""Database connection and query helpers.

Connection settings come from environment variables (loaded from a .env
file if one exists), so no password is ever hard-coded in the repo.
See .env.example for the variable names.
"""

import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "job_tracker"),
}


def get_db():
    """Open a new connection to the job_tracker database."""
    return mysql.connector.connect(**DB_CONFIG)


def query_all(sql, params=None):
    """Run a SELECT and return every row as a dict."""
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        return cursor.fetchall()
    finally:
        conn.close()


def query_one(sql, params=None):
    """Run a SELECT and return the first row as a dict (or None)."""
    rows = query_all(sql, params)
    return rows[0] if rows else None


def run_transaction(statements):
    """Run several write statements as ONE transaction (Assignment 4).

    `statements` is a list of (sql, params) pairs. Either every statement
    is committed, or - if any of them fails - all of them are rolled back,
    so the database is never left half-changed.
    """
    conn = get_db()
    try:
        conn.start_transaction()
        cursor = conn.cursor()
        for sql, params in statements:
            cursor.execute(sql, params or ())
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute(sql, params=None):
    """Run an INSERT/UPDATE/DELETE, commit it, and return the new row id
    (for inserts) or the number of affected rows (for updates/deletes)."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        conn.commit()
        return cursor.lastrowid or cursor.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
