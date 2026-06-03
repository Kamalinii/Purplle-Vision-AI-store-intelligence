import aiosqlite
from .models import AnomaliesResponse, Anomaly
from .database import DB_PATH

async def get_anomalies(store_id: str) -> AnomaliesResponse:
    anomalies = []
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # 1. Queue Spike
        cursor = await db.execute("""
            SELECT queue_depth, timestamp
            FROM events
            WHERE store_id = ? AND event_type = 'BILLING_QUEUE_JOIN'
            ORDER BY timestamp DESC
            LIMIT 1
        """, (store_id,))
        row = await cursor.fetchone()
        if row and row['queue_depth'] is not None and row['queue_depth'] > 3:
            anomalies.append(Anomaly(
                anomaly_type="BILLING_QUEUE_SPIKE",
                severity="CRITICAL",
                description=f"Billing queue depth reached {row['queue_depth']}.",
                suggested_action="Deploy additional staff to billing."
            ))
            
        # 2. Dead Zone (No visits in last 30 minutes)
        # Find specific zones that have NO events in the last 30 mins from the latest store event
        cursor = await db.execute("""
            SELECT MAX(timestamp) as last_event
            FROM events
            WHERE store_id = ?
        """, (store_id,))
        row = await cursor.fetchone()
        if row and row['last_event']:
            last_event_time = row['last_event']
            
            import json
            import os
            layout_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'store_layout.json')
            try:
                with open(layout_path, 'r') as f:
                    layout = json.load(f)
                all_zones = [z['zone_id'] for z in layout.get(store_id, {}).get('zones', [])]
            except Exception:
                all_zones = ["CASH_COUNTER", "MAKEUP_UNIT", "SKINCARE", "STORAGE", "ENTRY_EXIT"]

            cursor = await db.execute("""
                SELECT zone_id, MAX(timestamp) as last_zone_visit
                FROM events
                WHERE store_id = ? AND zone_id IS NOT NULL
                GROUP BY zone_id
            """, (store_id,))
            
            zone_visits = {r['zone_id']: r['last_zone_visit'] for r in await cursor.fetchall()}
            
            from dateutil.parser import parse
            global_last_dt = parse(last_event_time).replace(tzinfo=None)
            
            for zone in all_zones:
                last_visit_str = zone_visits.get(zone)
                is_dead = False
                if not last_visit_str:
                    is_dead = True
                else:
                    last_dt = parse(last_visit_str).replace(tzinfo=None)
                    if (global_last_dt - last_dt).total_seconds() > 1800:
                        is_dead = True
                        
                if is_dead:
                    anomalies.append(Anomaly(
                        anomaly_type="DEAD_ZONE",
                        severity="WARN",
                        description=f"No events recorded in {zone} in the last 30 minutes.",
                        suggested_action=f"Check camera feed or store layout for {zone}."
                    ))
                
        # 3. Conversion Drop (vs historical avg)
        # Calculate today's conversion rate
        # Determine logical 'today' based on the newest event
        cursor = await db.execute("SELECT date(MAX(timestamp)) as today FROM events WHERE store_id = ?", (store_id,))
        row = await cursor.fetchone()
        today = row['today'] if row and row['today'] else '2026-04-10'

        cursor = await db.execute("""
            SELECT COUNT(DISTINCT visitor_id) as visitors
            FROM events
            WHERE store_id = ? AND is_staff = 0 AND date(timestamp) = ?
        """, (store_id, today))
        row = await cursor.fetchone()
        today_visitors = row['visitors'] if row and row['visitors'] else 0
        
        cursor = await db.execute("""
            SELECT COUNT(DISTINCT e.visitor_id) as buyers
            FROM events e
            JOIN pos_transactions p ON e.store_id = p.store_id
            WHERE e.store_id = ? AND e.is_staff = 0 AND date(e.timestamp) = ?
              AND (e.zone_id = 'CASH_COUNTER' OR e.event_type LIKE 'BILLING%')
              AND datetime(e.timestamp) <= datetime(p.timestamp) AND datetime(e.timestamp) >= datetime(p.timestamp, '-5 minutes')
        """, (store_id, today))
        row = await cursor.fetchone()
        today_buyers = row['buyers'] if row and row['buyers'] else 0
        
        today_conversion = (today_buyers / today_visitors) if today_visitors > 0 else 0.0
        
        # Calculate historical 7-day conversion rate
        cursor = await db.execute("""
            SELECT COUNT(DISTINCT visitor_id) as visitors
            FROM events
            WHERE store_id = ? AND is_staff = 0 
              AND date(timestamp) >= date(?, '-7 days')
              AND date(timestamp) < ?
        """, (store_id, today, today))
        row = await cursor.fetchone()
        hist_visitors = row['visitors'] if row and row['visitors'] else 0
        
        cursor = await db.execute("""
            SELECT COUNT(DISTINCT e.visitor_id) as buyers
            FROM events e
            JOIN pos_transactions p ON e.store_id = p.store_id
            WHERE e.store_id = ? AND e.is_staff = 0 
              AND date(e.timestamp) >= date(?, '-7 days')
              AND date(e.timestamp) < ?
              AND (e.zone_id = 'CASH_COUNTER' OR e.event_type LIKE 'BILLING%')
              AND datetime(e.timestamp) <= datetime(p.timestamp) AND datetime(e.timestamp) >= datetime(p.timestamp, '-5 minutes')
        """, (store_id, today, today))
        row = await cursor.fetchone()
        hist_buyers = row['buyers'] if row and row['buyers'] else 0
        
        historical_conversion = (hist_buyers / hist_visitors) if hist_visitors > 0 else 0.05  # Fallback to 5% if no historical data exists
        
        # If today's conversion is strictly less than historical conversion
        if today_conversion < historical_conversion:
            anomalies.append(Anomaly(
                anomaly_type="CONVERSION_DROP",
                severity="WARN",
                description=f"Conversion rate is {today_conversion*100:.1f}%, down from 7-day avg of {historical_conversion*100:.1f}%.",
                suggested_action="Review store layouts and staff availability."
            ))

    return AnomaliesResponse(active_anomalies=anomalies)
