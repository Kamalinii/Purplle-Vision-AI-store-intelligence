import aiosqlite
from .models import HealthResponse
from .database import DB_PATH
from datetime import datetime
from dateutil.parser import parse

async def get_health() -> HealthResponse:
    stores_status = {}
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Determine logical 'now' based on the absolute newest event across all stores
        cursor = await db.execute("SELECT MAX(timestamp) as global_max FROM events")
        global_row = await cursor.fetchone()
        
        now = datetime.utcnow()
        if global_row and global_row['global_max']:
            try:
                now = parse(global_row['global_max']).replace(tzinfo=None)
            except:
                pass
        
        cursor = await db.execute("""
            SELECT store_id, MAX(timestamp) as last_event
            FROM events
            GROUP BY store_id
        """)
        rows = await cursor.fetchall()
        
        for row in rows:
            store_id = row['store_id']
            last_event = row['last_event']
            
            is_stale = False
            if last_event:
                try:
                    last_event_dt = parse(last_event).replace(tzinfo=None)
                    # If this store is more than 10 mins (600s) behind the global max, it is stale
                    if (now - last_event_dt).total_seconds() > 600:
                        is_stale = True
                except:
                    pass
            else:
                is_stale = True
            
            stores_status[store_id] = {
                "last_event": last_event,
                "status": "STALE_FEED" if is_stale else "OK"
            }
            
    return HealthResponse(
        status="OK" if stores_status else "INITIALIZING",
        stores=stores_status
    )
