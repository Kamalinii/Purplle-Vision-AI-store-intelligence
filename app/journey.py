import aiosqlite

from .database import DB_PATH


async def get_visitor_journey(store_id: str, visitor_id: str) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT event_type, timestamp, zone_id, dwell_ms, camera_id
            FROM events
            WHERE store_id = ? AND visitor_id = ?
            ORDER BY timestamp, session_seq
            """,
            (store_id, visitor_id),
        )
        rows = await cursor.fetchall()

    events = []
    for row in rows:
        events.append({
            "event_type": row["event_type"],
            "timestamp": row["timestamp"],
            "zone_id": row["zone_id"],
            "dwell_ms": int(row["dwell_ms"] or 0),
            "camera_id": row["camera_id"],
        })

    return {
        "visitor_id": visitor_id,
        "events": events,
    }


async def get_recent_visitors(store_id: str, limit: int = 20) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT visitor_id, MAX(timestamp) as last_seen
            FROM events
            WHERE store_id = ? AND is_staff = 0
            GROUP BY visitor_id
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (store_id, limit),
        )
        rows = await cursor.fetchall()

    return [row[0] for row in rows]
