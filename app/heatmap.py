import aiosqlite
from .models import HeatmapResponse, HeatmapZone
from .database import DB_PATH

async def get_heatmap(store_id: str) -> HeatmapResponse:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # Count total unique visitor sessions
        cursor = await db.execute("""
            SELECT COUNT(DISTINCT visitor_id) as sessions
            FROM events
            WHERE store_id = ? AND is_staff = 0
        """, (store_id,))
        row = await cursor.fetchone()
        sessions = row['sessions'] if row else 0
        data_confidence = sessions >= 20
        
        # Get raw stats per zone
        # We use ZONE_ENTER for frequency, and ZONE_DWELL for avg_dwell to get accurate counts
        cursor = await db.execute("""
            SELECT 
                zone_id,
                SUM(CASE WHEN event_type = 'ZONE_ENTER' THEN 1 ELSE 0 END) as freq,
                AVG(CASE WHEN event_type = 'ZONE_DWELL' THEN dwell_ms ELSE NULL END) as avg_dwell
            FROM events
            WHERE store_id = ? AND is_staff = 0 AND zone_id IS NOT NULL
            GROUP BY zone_id
        """, (store_id,))
        rows = await cursor.fetchall()
        
        if not rows:
            return HeatmapResponse(zones=[], data_confidence=data_confidence)
            
        # Extract and compute max for normalization
        stats = []
        for r in rows:
            freq = r['freq'] if r['freq'] else 0
            dwell = r['avg_dwell'] if r['avg_dwell'] else 0
            if freq > 0 or dwell > 0:
                stats.append({"zone_id": r['zone_id'], "freq": freq, "dwell": dwell})
                
        if not stats:
            return HeatmapResponse(zones=[], data_confidence=data_confidence)
            
        max_freq = max((s['freq'] for s in stats))
        max_dwell = max((s['dwell'] for s in stats))
        
        max_freq = max(max_freq, 1)
        max_dwell = max(max_dwell, 1)
        
        zones = []
        for s in stats:
            freq_score = int((s['freq'] / max_freq) * 100)
            dwell_score = int((s['dwell'] / max_dwell) * 100)
            zones.append(HeatmapZone(
                zone_id=s['zone_id'],
                frequency_score=freq_score,
                avg_dwell_score=dwell_score
            ))
            
    return HeatmapResponse(zones=zones, data_confidence=data_confidence)
