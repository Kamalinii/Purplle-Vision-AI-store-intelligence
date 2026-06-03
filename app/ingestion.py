import aiosqlite
from typing import List, Dict, Any
from .models import DetectionEvent, IngestResponse
from .database import DB_PATH
import logging
from pydantic import ValidationError

logger = logging.getLogger(__name__)

async def process_events(raw_events: List[Dict[str, Any]]) -> IngestResponse:
    processed = 0
    errors = 0
    error_details = []
    
    events_to_insert = []
    
    for raw in raw_events:
        try:
            event = DetectionEvent(**raw)
            events_to_insert.append(event)
        except ValidationError as e:
            errors += 1
            error_details.append(f"Validation failed for event: {str(e)}")
    
    async with aiosqlite.connect(DB_PATH) as db:
        for event in events_to_insert:
            try:
                # Use INSERT OR IGNORE to ensure idempotency by event_id
                cursor = await db.execute("""
                    INSERT OR IGNORE INTO events (
                        event_id, store_id, camera_id, visitor_id, event_type, 
                        timestamp, zone_id, dwell_ms, is_staff, confidence,
                        queue_depth, sku_zone, session_seq
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id, event.store_id, event.camera_id, event.visitor_id,
                    event.event_type, event.timestamp.isoformat(), event.zone_id,
                    event.dwell_ms, event.is_staff, event.confidence,
                    event.metadata.queue_depth,
                    event.metadata.sku_zone,
                    event.metadata.session_seq
                ))
                if cursor.rowcount > 0:
                    processed += 1
                else:
                    # If ignored because of conflict, we don't count it as error, but it's idempotent
                    pass
            except Exception as e:
                errors += 1
                error_details.append(f"Event {event.event_id} failed: {str(e)}")
        
        await db.commit()
    
    status = "partial_success" if errors > 0 and processed > 0 else "success" if errors == 0 else "failed"
    return IngestResponse(
        status=status,
        processed=processed,
        errors=errors,
        error_details=error_details
    )
