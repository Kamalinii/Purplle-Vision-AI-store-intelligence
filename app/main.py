import time
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import asyncio
from contextlib import asynccontextmanager
from typing import List
import uuid
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("api")

from .models import (
    DetectionEvent, IngestResponse, MetricsResponse, FunnelResponse, 
    HeatmapResponse, AnomaliesResponse, HealthResponse, ReIdRequest, ReIdUpdateRequest
)
import cv2
import numpy as np
from .database import init_db, get_db
from .ingestion import process_events
from .metrics import get_metrics
from .funnel import get_funnel
from .anomalies import get_anomalies
from .health import get_health
from .health_score import get_health_score
from .alerts import get_alerts
from .journey import get_recent_visitors, get_visitor_journey
from .recommendations import get_recommendations
import aiosqlite
from fastapi import Query, Request

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.global_past_visitors = {}
    app.state.latest_frames = {}
    
    import os
    import re
    footage_dir = os.path.join(os.path.dirname(__file__), "..", "data", "CCTV Footage")
    if os.path.exists(footage_dir):
        for file in os.listdir(footage_dir):
            if file.endswith(".mp4"):
                match = re.search(r'\d+', file)
                if match:
                    app.state.latest_frames[f"CAM_{match.group()}"] = None
                    
    app.state.last_reset_time = time.time()
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Failed to init DB: {e}")
    yield

app = FastAPI(title="Store Intelligence API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    import time, json, uuid
    start_time = time.time()
    trace_id = str(uuid.uuid4())
    
    # Extract store_id from path if present
    path = request.url.path
    store_id = None
    if path.startswith("/stores/"):
        parts = path.split("/")
        if len(parts) >= 3:
            store_id = parts[2]
            
    response = await call_next(request)
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    # Avoid logging static asset requests to keep logs clean
    if not path.startswith("/static/") and not path.startswith("/video/"):
        log_entry = {
            "trace_id": trace_id,
            "store_id": store_id,
            "endpoint": path,
            "method": request.method,
            "latency_ms": latency_ms,
            "status_code": response.status_code
        }
        logger.info(json.dumps(log_entry))
        
    response.headers["X-Trace-Id"] = trace_id
    return response

@app.exception_handler(aiosqlite.OperationalError)
async def aiosqlite_exception_handler(request: Request, exc: aiosqlite.OperationalError):
    return JSONResponse(
        status_code=503,
        content={"error": "Database Service Unavailable", "details": "The database is currently inaccessible or experiencing issues."}
    )

@app.exception_handler(aiosqlite.DatabaseError)
async def aiosqlite_db_exception_handler(request: Request, exc: aiosqlite.DatabaseError):
    return JSONResponse(
        status_code=503,
        content={"error": "Database Service Unavailable", "details": "The database is currently inaccessible or experiencing issues."}
    )
@app.get("/stores/{store_id}/pos/match")
async def match_pos(
    store_id: str, 
    start_time: str = Query(...), 
    end_time: str = Query(...),
    db: aiosqlite.Connection = Depends(get_db)
):
    st = start_time.replace("Z", "")
    et = end_time.replace("Z", "")
    query = """
        SELECT COUNT(*) FROM pos_transactions 
        WHERE store_id = ? AND timestamp >= ? AND timestamp <= datetime(?, '+60 seconds')
    """
    async with db.execute(query, (store_id, st, et)) as cursor:
        row = await cursor.fetchone()
        matched = row[0] > 0
    return {"matched": matched}



import json

@app.middleware("http")
async def log_requests(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    start_time = time.time()
    
    store_id = None
    path_parts = request.url.path.split("/")
    if len(path_parts) > 2 and path_parts[1] == "stores":
        store_id = path_parts[2]
        
    event_count = None
    if request.url.path == "/events/ingest" and request.method == "POST":
        body_bytes = await request.body()
        try:
            body = json.loads(body_bytes)
            if isinstance(body, list):
                event_count = len(body)
        except Exception:
            pass
        # Re-inject body for the route handler
        async def receive():
            return {"type": "http.request", "body": body_bytes}
        request._receive = receive
        
    response = None
    try:
        response = await call_next(request)
    finally:
        latency_ms = (time.time() - start_time) * 1000
        status_code = response.status_code if response else 500
        
        log_data = {
            "trace_id": trace_id,
            "endpoint": request.url.path,
            "latency_ms": round(latency_ms, 2),
            "status_code": status_code
        }
        if store_id:
            log_data["store_id"] = store_id
        if event_count is not None:
            log_data["event_count"] = event_count
            
        logger.info(json.dumps(log_data))
        
    return response

@app.post("/events/ingest", response_model=IngestResponse)
async def ingest_events(events: List[dict]):
    if len(events) > 500:
        raise HTTPException(status_code=400, detail="Batch size exceeds 500")
    return await process_events(events)

@app.post("/reid")
async def handle_reid(request: Request, payload: ReIdRequest):
    global_past_visitors = request.app.state.global_past_visitors
    
    best_match = None
    best_score = 0.0
    
    if payload.hist:
        np_hist = np.array(payload.hist, dtype=np.float32).reshape(-1, 1)
        for past_id, data in global_past_visitors.items():
            past_hist_np = np.array(data["hist"], dtype=np.float32).reshape(-1, 1)
            score = cv2.compareHist(np_hist, past_hist_np, cv2.HISTCMP_CORREL)
            if score > 0.78 and score > best_score:
                best_score = score
                best_match = past_id
                
    if best_match:
        past_is_staff = global_past_visitors[best_match].get("is_staff", False)
        return {"visitor_id": best_match, "is_reentry": True, "is_staff": past_is_staff}
    else:
        return {"visitor_id": f"{payload.camera_id}_{payload.raw_id}", "is_reentry": False, "is_staff": False}

@app.post("/reid/update")
async def update_reid(request: Request, payload: ReIdUpdateRequest):
    global_past_visitors = request.app.state.global_past_visitors
    global_past_visitors[payload.visitor_id] = {
        "hist": payload.hist,
        "is_staff": payload.is_staff
    }
    return {"status": "ok"}

@app.post("/reset")
async def reset_system(request: Request):
    # Completely reset the database (wipes events, re-seeds POS mock transactions)
    await init_db()
    # Clear the global Re-ID color histogram cache
    request.app.state.global_past_visitors.clear()
    request.app.state.last_reset_time = time.time()
    return {"status": "ok", "message": "System reset completely!"}

@app.get("/reset-status")
async def reset_status(request: Request):
    return {"last_reset": request.app.state.last_reset_time}

@app.get("/stores/{store_id}/metrics", response_model=MetricsResponse)
async def metrics(store_id: str):
    return await get_metrics(store_id)

@app.get("/stores/{store_id}/funnel", response_model=FunnelResponse)
async def funnel(store_id: str):
    return await get_funnel(store_id)

@app.get("/stores/{store_id}/heatmap", response_model=HeatmapResponse)
async def heatmap(store_id: str):
    from .heatmap import get_heatmap
    return await get_heatmap(store_id)

@app.get("/stores/{store_id}/health-score")
async def health_score(store_id: str):
    return await get_health_score(store_id)

@app.get("/stores/{store_id}/alerts")
async def alerts(store_id: str):
    return await get_alerts(store_id)

@app.get("/stores/{store_id}/visitors")
async def visitors(store_id: str, limit: int = 20):
    limit = max(1, min(limit, 100))
    return {"visitors": await get_recent_visitors(store_id, limit)}

@app.get("/stores/{store_id}/journey/{visitor_id}")
async def journey(store_id: str, visitor_id: str):
    return await get_visitor_journey(store_id, visitor_id)

@app.get("/stores/{store_id}/recommendations")
async def recommendations(store_id:str):
    return await get_recommendations(store_id)

@app.get("/stores/{store_id}/anomalies", response_model=AnomaliesResponse)
async def anomalies(store_id: str):
    return await get_anomalies(store_id)

@app.get("/health", response_model=HealthResponse)
async def health():
    return await get_health()

from fastapi.responses import HTMLResponse, FileResponse
import os

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    file_path = os.path.join(os.path.dirname(__file__), "static", "dashboard.html")
    return FileResponse(file_path)

@app.get("/cameras")
async def get_active_cameras(request: Request):
    cams = list(request.app.state.latest_frames.keys())
    return {"cameras": sorted(cams)}

@app.post("/video/{camera_id}")
async def receive_video(request: Request, camera_id: str):
    body = await request.body()
    request.app.state.latest_frames[camera_id] = body
    return {"status": "ok"}

async def video_generator(request: Request, camera_id: str):
    # Create a loading frame using OpenCV
    img = np.zeros((360, 640, 3), dtype=np.uint8)
    cv2.putText(img, f"BOOTING YOLOv8: {camera_id}...", (50, 180), cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2)
    _, buffer = cv2.imencode('.jpg', img)
    loading_frame = buffer.tobytes()

    while True:
        frame = request.app.state.latest_frames.get(camera_id)
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            await asyncio.sleep(0.05) # 20fps playback
        else:
            # Yield the loading frame while YOLO is booting up
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + loading_frame + b'\r\n')
            await asyncio.sleep(0.5)

@app.get("/video/{camera_id}/stream")
async def stream_video(request: Request, camera_id: str):
    return StreamingResponse(video_generator(request, camera_id),
                             media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/stores/{store_id}/alerts")
async def alerts(store_id: str):
    return await get_alerts(store_id)