import sqlite3
from pathlib import Path
from datetime import datetime

APP_DIR = Path.home() / ".local/share/kde-epson-fax"
DB_PATH = APP_DIR / "fax.db"


def init_db():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS fax_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datetime TEXT,
        printer TEXT,
        recipient TEXT,
        file TEXT,
        job_id TEXT,
        status TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        fax_number TEXT
    )
    """)

    conn.commit()
    conn.close()


# ===== HISTORY =====

def add_history(printer, recipient, file, job_id, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    INSERT INTO fax_history (datetime, printer, recipient, file, job_id, status)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        printer,
        recipient,
        file,
        job_id,
        status
    ))
    conn.commit()
    conn.close()


def update_status(job_id, new_status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE fax_history SET status=? WHERE job_id=?", (new_status, job_id))
    conn.commit()
    conn.close()


def get_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, datetime, printer, recipient, file, job_id, status
        FROM fax_history ORDER BY id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows


# ===== CONTACTS =====

def get_contacts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, fax_number FROM contacts ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return rows


def add_contact(name, fax_number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO contacts (name, fax_number) VALUES (?, ?)", (name, fax_number))
    conn.commit()
    conn.close()


def delete_contact(contact_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
    conn.commit()
    conn.close()
