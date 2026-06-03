import aiosqlite
from .models import MetricsResponse
from .database import DB_PATH
from .dwell import get_average_dwell_per_zone
from datetime import datetime

async def get_metrics(store_id: str) -> MetricsResponse:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Determine logical 'today' based on the newest event
        cursor = await db.execute("SELECT date(MAX(timestamp)) as today FROM events WHERE store_id = ?", (store_id,))
        row = await cursor.fetchone()
        today = row['today']
        
        # Unique Visitors (excluding staff)
        cursor = await db.execute("""
            SELECT COUNT(DISTINCT visitor_id) as c
            FROM events
            WHERE store_id = ? AND date(timestamp) = ?
            AND visitor_id NOT IN (SELECT visitor_id FROM events WHERE is_staff = 1)
        """, (store_id, today))
        row = await cursor.fetchone()
        unique_visitors = row['c'] if row else 0
        
        # Queue Depth (latest queue_depth reported)
        cursor = await db.execute("""
            SELECT queue_depth
            FROM events
            WHERE store_id = ? AND queue_depth IS NOT NULL AND date(timestamp) = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (store_id, today))
        row = await cursor.fetchone()
        queue_depth = row['queue_depth'] if row and row['queue_depth'] is not None else 0
        
        # Abandonment Rate
        # Visitors who abandoned / Visitors who joined queue
        cursor = await db.execute("""
            SELECT COUNT(DISTINCT visitor_id) as c
            FROM events
            WHERE store_id = ? AND event_type = 'BILLING_QUEUE_ABANDON' AND date(timestamp) = ?
            AND visitor_id NOT IN (SELECT visitor_id FROM events WHERE is_staff = 1)
        """, (store_id, today))
        row = await cursor.fetchone()
        abandoned = row['c'] if row else 0
        
        cursor = await db.execute("""
            SELECT COUNT(DISTINCT visitor_id) as c
            FROM events
            WHERE store_id = ? AND (event_type = 'BILLING_QUEUE_JOIN' OR zone_id = 'CASH_COUNTER') AND date(timestamp) = ?
            AND visitor_id NOT IN (SELECT visitor_id FROM events WHERE is_staff = 1)
        """, (store_id, today))
        row = await cursor.fetchone()
        joined = row['c'] if row and row['c'] > 0 else 1 # avoid division by zero
        
        abandonment_rate = abandoned / joined
        
        # Conversion Rate
        # Using a simplified subquery for time-window correlation.
        # "A visitor who was in the billing zone in the 5-minute window before a transaction timestamp counts as a converted visitor."
        # Because SQLite date functions can be tricky, we will find distinct visitors who have a BILLING event 
        # that occurred within 5 minutes before any POS transaction.
        cursor = await db.execute("""
            SELECT COUNT(DISTINCT e.visitor_id) as converted
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
        converted_visitors = row['converted'] if row else 0
        
        conversion_rate = converted_visitors / unique_visitors if unique_visitors > 0 else 0.0

    avg_dwell = await get_average_dwell_per_zone(store_id)

    return MetricsResponse(
        unique_visitors=unique_visitors,
        conversion_rate=conversion_rate,
        avg_dwell_per_zone=avg_dwell,
        queue_depth=queue_depth,
        abandonment_rate=abandonment_rate
    )
