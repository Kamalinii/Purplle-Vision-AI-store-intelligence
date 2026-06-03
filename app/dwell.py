from datetime import datetime
from typing import Dict, List

import aiosqlite

from .database import DB_PATH


def parse_event_time(value: str) -> datetime:
    cleaned = value.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned)


async def get_average_dwell_per_zone(store_id: str) -> Dict[str, float]:
    """Compute average dwell in milliseconds from real zone events.

    The detector emits a ZONE_ENTER when a visitor first appears in a zone,
    periodic ZONE_DWELL samples while they remain there, and ZONE_EXIT when the
    track is lost. Prefer explicit dwell_ms values, and fall back to the
    timestamp gap between enter and exit when needed.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT visitor_id, zone_id, event_type, timestamp, dwell_ms
            FROM events
            WHERE store_id = ?
              AND zone_id IS NOT NULL
              AND is_staff = 0
              AND event_type IN ('ZONE_ENTER', 'ZONE_DWELL', 'ZONE_EXIT')
            ORDER BY visitor_id, zone_id, timestamp, session_seq
            """,
            (store_id,),
        )
        rows = await cursor.fetchall()

    active_sessions = {}
    samples_by_zone: Dict[str, List[float]] = {}

    for row in rows:
        visitor_id = row["visitor_id"]
        zone_id = row["zone_id"]
        event_type = row["event_type"]
        timestamp = parse_event_time(row["timestamp"])
        dwell_ms = float(row["dwell_ms"] or 0)
        key = (visitor_id, zone_id)

        if event_type == "ZONE_ENTER":
            active_sessions[key] = {
                "started_at": timestamp,
                "last_dwell_ms": 0.0,
            }
            continue

        if event_type == "ZONE_DWELL":
            session = active_sessions.setdefault(
                key,
                {"started_at": timestamp, "last_dwell_ms": 0.0},
            )
            if dwell_ms > 0:
                session["last_dwell_ms"] = max(session["last_dwell_ms"], dwell_ms)
            continue

        if event_type == "ZONE_EXIT":
            session = active_sessions.pop(key, None)
            final_dwell = dwell_ms

            if final_dwell <= 0 and session:
                final_dwell = session["last_dwell_ms"]

            if final_dwell <= 0 and session:
                final_dwell = max(
                    (timestamp - session["started_at"]).total_seconds() * 1000,
                    0,
                )

            if final_dwell > 0:
                samples_by_zone.setdefault(zone_id, []).append(final_dwell)

    for (_, zone_id), session in active_sessions.items():
        if session["last_dwell_ms"] > 0:
            samples_by_zone.setdefault(zone_id, []).append(session["last_dwell_ms"])

    return {
        zone_id: sum(samples) / len(samples)
        for zone_id, samples in samples_by_zone.items()
        if samples
    }
