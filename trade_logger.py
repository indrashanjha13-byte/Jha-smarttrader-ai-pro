import sqlite3
import os
import logging

# Ensure database directory exists
DB_DIR = "database"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DB_PATH = os.path.join(DB_DIR, "trades.db")

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Example table creation for trades if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            symbol TEXT,
            action TEXT,
            entry REAL,
            exit_price REAL,
            stop_loss REAL,
            target REAL,
            quantity INTEGER,
            pnl REAL,
            status TEXT
        )
    """)
    conn.commit()
    logging.info("✅ Database connected and table initialized successfully.")

except Exception as e:
    logging.error(f"❌ Database connection error: {e}")