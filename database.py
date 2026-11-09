import os
import sqlite3

DB_PATH = (
    os.path.join("/tmp", "villa-brezo.db")
    if os.environ.get("VERCEL")
    else os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")
)

def lidhu():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def krijo_tabelat():
    conn = lidhu()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS dhomat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emri TEXT NOT NULL,
        cmimi REAL NOT NULL,
        kapaciteti INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS ofertat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulli TEXT NOT NULL,
        pershkrimi TEXT,
        cmimi REAL
    );

    CREATE TABLE IF NOT EXISTS packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        price_per_night REAL NOT NULL,
        max_guests INTEGER NOT NULL,
        is_family INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        valid_from TEXT,
        valid_to TEXT,
        room_id INTEGER,
        FOREIGN KEY (room_id) REFERENCES dhomat(id)
    );

    CREATE TABLE IF NOT EXISTS rezervimet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dhoma_id INTEGER NOT NULL,
        emri TEXT NOT NULL,
        mbiemri TEXT NOT NULL,
        email TEXT NOT NULL,
        telefoni TEXT NOT NULL,
        data_hyrjes TEXT NOT NULL,
        data_daljes TEXT NOT NULL,
        persona INTEGER NOT NULL,
        kerkesat TEXT,
        cmimi_total REAL,
        statusi TEXT DEFAULT 'në pritje',
        krijuar TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (dhoma_id) REFERENCES dhomat(id)
    );

    CREATE TABLE IF NOT EXISTS mesazhet (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emri TEXT,
        email TEXT,
        mesazhi TEXT,
        krijuar TEXT DEFAULT CURRENT_TIMESTAMP
    );

    INSERT OR IGNORE INTO dhomat (id, emri, cmimi, kapaciteti) VALUES
        (1, 'Kati i 1-re', 150, 5),
        (2, 'Loft Alpin', 200, 10);

    INSERT OR IGNORE INTO packages
        (id, title, description, price_per_night, max_guests, is_family, is_active, room_id) VALUES
        (1, 'Paketa Familjare', 'Qendrim komod per familjen, afer pistave te skijimit.', 130, 5, 1, 1, 1),
        (2, 'Paketa Dimerore', 'Atmosfere e ngrohte dimerore, me oxhak dhe kuzhine.', 150, 5, 0, 1, 1),
        (3, 'Fundjave ne Brezovice', 'Arratisuni per nje fundjave ne mal.', 170, 5, 0, 1, 1);
    """)
    conn.commit()
    conn.close()