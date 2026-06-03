import aiosqlite
from .models import FunnelResponse, FunnelStage
from .database import DB_PATH

async def get_funnel(store_id: str) -> FunnelResponse:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Determine logical 'today' based on the newest event
        cursor = await db.execute("SELECT date(MAX(timestamp)) as today FROM events WHERE store_id = ?", (store_id,))
        row = await cursor.fetchone()
        today = row['today']
        
        # 1. Entry
        cursor = await db.execute("""
            SELECT COUNT(DISTINCT visitor_id) as c
            FROM events
            WHERE store_id = ? AND date(timestamp) = ?
            AND visitor_id NOT IN (SELECT visitor_id FROM events WHERE is_staff = 1)
        """, (store_id, today))
        row = await cursor.fetchone()
        entry_count = row['c'] if row else 0
        
        # 2. Zone Visit
        cursor = await db.execute("""
            SELECT COUNT(DISTINCT visitor_id) as c
            FROM events
            WHERE store_id = ? AND zone_id IS NOT NULL AND date(timestamp) = ?
            AND visitor_id NOT IN (SELECT visitor_id FROM events WHERE is_staff = 1)
        """, (store_id, today))
        row = await cursor.fetchone()
        zone_count = row['c'] if row else 0
        
        # 3. Billing Queue
        cursor = await db.execute("""
            SELECT COUNT(DISTINCT visitor_id) as c
            FROM events
            WHERE store_id = ? AND (event_type = 'BILLING_QUEUE_JOIN' OR zone_id = 'CASH_COUNTER') AND date(timestamp) = ?
            AND visitor_id NOT IN (SELECT visitor_id FROM events WHERE is_staff = 1)
        """, (store_id, today))
        row = await cursor.fetchone()
        queue_count = row['c'] if row else 0
        
        # 4. Purchase
        cursor = await db.execute("""
            SELECT COUNT(DISTINCT e.visitor_id) as c
            FROM events e
            JOIN pos_transactions p ON e.store_id = p.store_id
            WHERE e.store_id = ? 
              AND e.visitor_id NOT IN (SELECT visitor_id FROM events WHERE is_staff = 1)
              AND date(e.timestamp) = ?
              AND (e.zone_id = 'CASH_COUNTER' OR e.event_type LIKE 'BILLING%')
              AND datetime(e.timestamp) <= datetime(p.timestamp) 
              AND datetime(e.timestamp) >= datetime(p.timestamp, '-5 minutes')
        """, (store_id, today))
        row = await cursor.fetchone()
        purchase_count = row['c'] if row else 0
        
    stages = [
        {"stage": "Entry", "count": entry_count},
        {"stage": "Zone Visit", "count": zone_count},
        {"stage": "Billing Queue", "count": queue_count},
        {"stage": "Purchase", "count": purchase_count}
    ]
    
    funnel_stages = []
    prev_count = entry_count
    for stage in stages:
        c = stage["count"]
        # Can't have more in a downstream stage than previous stage due to mock data randomness,
        # so cap it for realism if needed, but we'll just leave it pure.
        dropoff = 0.0
        if prev_count > 0 and c <= prev_count:
            dropoff = (prev_count - c) / prev_count
        elif prev_count > 0 and c > prev_count:
            dropoff = 0.0 # Prevent negative dropoff in weird mock data
        
        funnel_stages.append(
            FunnelStage(
                stage=stage["stage"],
                count=c,
                dropoff_percentage=round(dropoff * 100, 2)
            )
        )
        prev_count = c
        
    return FunnelResponse(funnel=funnel_stages)
