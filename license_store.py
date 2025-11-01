# license_store.py
import sqlite3
import datetime
import os

DB_FILE = "licenses.db"

def init_db():
    """
    Create the licenses table if missing and ensure the columns exist.
    This uses explicit column names so SELECT ... returns fields in a consistent order.
    """
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()

    # Create table if missing (with correct column order)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT,
            product TEXT,
            license_key TEXT,
            expiry_date TEXT,
            max_users INTEGER,
            hwid TEXT,
            date_generated TEXT
        )
    """)
    con.commit()

    # Defensive migration: if older table missing column(s), add them.
    cur.execute("PRAGMA table_info(licenses)")
    cols = [r[1] for r in cur.fetchall()]

    # Add any missing columns (safe - ALTER only if column missing)
    expected = {
        "client_name": "TEXT",
        "product": "TEXT",
        "license_key": "TEXT",
        "expiry_date": "TEXT",
        "max_users": "INTEGER",
        "hwid": "TEXT",
        "date_generated": "TEXT",
    }
    for col, col_type in expected.items():
        if col not in cols:
            cur.execute(f"ALTER TABLE licenses ADD COLUMN {col} {col_type}")
    con.commit()
    con.close()

def save_license(client, product, license_key, expiry, users, hwid):
    """
    Insert a license row using explicit column list and set date_generated.
    """
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    today = datetime.date.today().isoformat()
    cur.execute("""
        INSERT INTO licenses (client_name, product, license_key, expiry_date, max_users, hwid, date_generated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (client, product, license_key, expiry, users, hwid, today))
    con.commit()
    con.close()

def fetch_all(order_desc=True):
    """Return rows in the exact column order we expect."""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    order = "DESC" if order_desc else "ASC"
    cur.execute(f"""
        SELECT id, client_name, product, license_key, expiry_date, max_users, hwid, date_generated
        FROM licenses
        ORDER BY id {order}
    """)
    rows = cur.fetchall()
    con.close()
    return rows

def search(term):
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    pattern = f"%{term}%"
    cur.execute("""
        SELECT id, client_name, product, license_key, expiry_date, max_users, hwid, date_generated
        FROM licenses
        WHERE client_name LIKE ? OR product LIKE ? OR hwid LIKE ? OR license_key LIKE ?
        ORDER BY id DESC
    """, (pattern, pattern, pattern, pattern))
    rows = cur.fetchall()
    con.close()
    return rows

if __name__ == "__main__":
    init_db()
    print("DB ready:", os.path.abspath(DB_FILE))
