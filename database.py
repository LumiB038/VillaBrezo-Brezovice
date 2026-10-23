import sqlite3

def lidhu():
    conn = sqlite3.connect("database.db")
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
    """)
    conn.commit()
    conn.close()