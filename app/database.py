import aiosqlite
import csv
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "store.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Reset unique visitors and events on restart
        await db.execute("DROP TABLE IF EXISTS events")
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                store_id TEXT,
                camera_id TEXT,
                visitor_id TEXT,
                event_type TEXT,
                timestamp DATETIME,
                zone_id TEXT,
                dwell_ms INTEGER,
                is_staff BOOLEAN,
                confidence REAL,
                queue_depth INTEGER,
                sku_zone TEXT,
                session_seq INTEGER
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pos_transactions (
                store_id TEXT,
                transaction_id TEXT PRIMARY KEY,
                timestamp DATETIME,
                basket_value_inr REAL
            )
        """)
        
        # Load pos_transactions from csv if empty
        async with db.execute("SELECT COUNT(*) FROM pos_transactions") as cursor:
            row = await cursor.fetchone()
            if row[0] == 0:
                pos_file = "data/pos_transactions.csv"
                if os.path.exists(pos_file):
                    offset = 5
                    simulated_start = datetime.strptime("2026-04-10T12:10:00", "%Y-%m-%dT%H:%M:%S")
                    with open(pos_file, "r") as f:
                        reader = csv.DictReader(f)
                        for r in reader:
                            cleaned_row = {k.strip(): v.strip() for k, v in r.items() if k is not None}
                            # The CCTV videos are processed with a simulated clock starting at 2026-04-10T12:10:00.
                            # We stagger mock POS transactions every 5 seconds from this exact start time 
                            # so they perfectly overlap with the short video clips!
                            dyn_time = simulated_start + __import__("datetime").timedelta(seconds=offset)
                            new_ts = dyn_time.strftime("%Y-%m-%dT%H:%M:%S")
                            offset += 5
                            
                            await db.execute(
                                "INSERT INTO pos_transactions (store_id, transaction_id, timestamp, basket_value_inr) VALUES (?, ?, ?, ?)",
                                (cleaned_row["store_id"], cleaned_row["transaction_id"], new_ts, float(cleaned_row["basket_value_inr"]))
                            )
        await db.commit()

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()
