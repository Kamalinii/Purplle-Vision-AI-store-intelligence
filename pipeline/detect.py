import cv2
import uuid
import datetime
import argparse
import time
import requests
import json
import os
import numpy as np
from ultralytics import YOLO
import logging
import threading
import queue

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("detect")

API_URL = "http://127.0.0.1:8000"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

latest_metrics = {
    "visitors": "--",
    "conversion": "--",
    "queue": "--",
    "abandon": "--"
}

def poll_metrics(store_id):
    while True:
        try:
            resp = requests.get(f"{API_URL}/stores/{store_id}/metrics", timeout=2)
            if resp.ok:
                data = resp.json()
                latest_metrics["visitors"] = str(data.get("unique_visitors", "--"))
                latest_metrics["conversion"] = f"{data.get('conversion_rate', 0.0)*100:.1f}%"
                latest_metrics["queue"] = str(data.get("queue_depth", "--"))
                latest_metrics["abandon"] = f"{data.get('abandonment_rate', 0.0)*100:.1f}%"
        except Exception:
            pass
        time.sleep(2)



def get_zone_for_camera(camera_id, store_id):
    try:
        with open("data/store_layout.json", "r") as f:
            layout = json.load(f)
            
        zones = layout.get(store_id, {}).get("zones", [])
        for z in zones:
            if camera_id in z.get("cameras", []):
                return z["zone_id"]
    except Exception:
        pass
    return None

def emit_structured_event(store_id, camera_id, visitor_id, event_type, timestamp, conf, is_staff, track, zone_id=None, dwell_ms=0, queue_depth=None, sku_zone=None):
    if event_type in ["ENTRY", "EXIT"]:
        zone_id = None
        
    # Increment sequence number for this visitor's session
    seq = track.get("session_seq", 1)
    track["session_seq"] = seq + 1
        
    payload = {
        "event_id": str(uuid.uuid4()),
        "store_id": store_id,
        "camera_id": camera_id,
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "zone_id": zone_id,
        "dwell_ms": int(dwell_ms),
        "is_staff": bool(is_staff),
        "confidence": float(conf),
        "metadata": {
            "queue_depth": queue_depth,
            "sku_zone": sku_zone,
            "session_seq": seq
        }
    }
    
    try:
        requests.post(f"{API_URL}/events/ingest", json=[payload])
    except Exception as e:
        logger.error(f"Failed to emit event: {e}")

def get_color_histogram(frame, box):
    x1, y1, x2, y2 = map(int, box)
    # Ensure coordinates are within frame
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
    cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    return hist

def is_staff_heuristic(frame, box):
    # Heuristic: check if the torso region of the person is "complete black"
    x1, y1, x2, y2 = map(int, box)
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
    
    # Focus on the torso (middle 50% vertically, middle 50% horizontally)
    height = y2 - y1
    width = x2 - x1
    if height == 0 or width == 0:
        return False
        
    torso_y1 = int(y1 + height * 0.2)
    torso_y2 = int(y1 + height * 0.8)
    torso_x1 = int(x1 + width * 0.2)
    torso_x2 = int(x1 + width * 0.8)
    
    crop = frame[torso_y1:torso_y2, torso_x1:torso_x2]
    if crop.size == 0:
        return False
        
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    v_channel = hsv[:, :, 2]
    s_channel = hsv[:, :, 1]
    
    # Black is low value (brightness) and low saturation
    # We use a very strict threshold (V < 90) to prevent gray shirts or shadows from triggering it
    dark_pixels = np.sum((v_channel < 90) & (s_channel < 50))
    total_pixels = v_channel.size
    
    # Require 60% of the torso to be solid black to avoid triggering on black bags
    if total_pixels > 0 and (dark_pixels / total_pixels) > 0.60:
        return True
        
    return False

frame_queue = queue.Queue(maxsize=1)
def web_sender(camera_id):
    while True:
        try:
            buffer = frame_queue.get(timeout=1.0)
            requests.post(f"{API_URL}/video/{camera_id}", data=buffer, timeout=2)
        except Exception:
            pass

def normalize_video_name(path: str) -> str:
    name = os.path.splitext(os.path.basename(path))[0]
    return "".join(ch for ch in name.lower() if ch.isalnum())

def resolve_video_path(video_path: str):
    candidates = [
        video_path,
        os.path.join(REPO_ROOT, video_path),
        os.path.join(os.getcwd(), video_path),
    ]

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    for candidate in candidates:
        directory = os.path.dirname(candidate) or "."
        if not os.path.isdir(directory):
            continue

        requested_name = normalize_video_name(candidate)
        for filename in os.listdir(directory):
            full_path = os.path.join(directory, filename)
            if os.path.isfile(full_path) and normalize_video_name(filename) == requested_name:
                return full_path

    return None

def process_video(video_path: str, store_id: str, visualize: bool, web: bool = False):
    filename = os.path.basename(video_path)
    camera_id = filename.split('.')[0].replace(" ", "_")
    zone_id = get_zone_for_camera(camera_id, store_id)
    
    logger.info(f"Processing {video_path} for Camera: {camera_id}, Zone: {zone_id}")

    logger.info("Loading YOLO model...")
    try:
        model = YOLO('yolov8n.pt') 
    except Exception as e:
        logger.error(f"Failed to load YOLO model: {e}")
        return
        
    logger.info(f"YOLO loaded successfully for {camera_id}! Starting video loop...")

    if visualize or web:
        threading.Thread(target=poll_metrics, args=(store_id,), daemon=True).start()
    
    if web:
        threading.Thread(target=web_sender, args=(camera_id,), daemon=True).start()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Failed to open video: {video_path}")
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0 or fps is None or fps != fps:
        fps = 30.0 
        
    frame_count = 0
    active_tracks = {}
    id_mapping = {} # maps raw track_id to re-identified visitor_id
    queue_depth = 0

    start_time_real = time.time()
    last_web_frame_sent = 0.0
    
    try:
        resp = requests.get(f"{API_URL}/reset-status", timeout=2).json()
        initial_reset_time = resp.get("last_reset", 0)
    except Exception:
        initial_reset_time = 0
    
    while cap.isOpened():
        # Dynamic frame drop to keep video playing at exactly 1x normal speed
        expected_frames = (time.time() - start_time_real) * fps
        if frame_count < expected_frames - 1:
            cap.grab() # Super fast frame skip without decoding
            frame_count += 1
            continue
            
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
            
        if frame_count % 100 == 0:
            logger.info(f"[{camera_id}] Processed {frame_count} frames...")
            
        # Poll the API to see if the user clicked "Reset" on the dashboard
        if frame_count % 30 == 0:
            try:
                resp = requests.get(f"{API_URL}/reset-status", timeout=1).json()
                if float(resp.get("last_reset", 0)) > float(initial_reset_time):
                    logger.info(f"[{camera_id}] Reset signal received from dashboard! Restarting ALL video streams...")
                    # Forcefully kill all python detect scripts so YOLO threads don't deadlock and the bash `wait` unblocks instantly
                    os.system("pkill -9 -f pipeline/detect.py")
                    import sys
                    sys.exit(0)
            except Exception as e:
                logger.error(f"Reset poll error in {camera_id}: {e}")
            
        # Process every frame for perfect tracker persistence
        # Use imgsz=320 to drastically increase YOLO inference speed by ~4x
        results = model.track(frame, persist=True, tracker="bytetrack.yaml", classes=[0], verbose=False, conf=0.45, imgsz=320)
        current_frame_ids = set()
        
        if results and len(results) > 0 and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()
            
            for box, track_id, conf in zip(boxes, track_ids, confidences):
                x1, y1, x2, y2 = box
                
                # Filter out passersby for CAM 3 (Entrance)
                # The mall corridor is on the right side of the frame.
                # If the center of the person is on the right side, they are outside.
                if camera_id == "CAM_3":
                    x_center = (x1 + x2) / 2
                    if x_center > frame.shape[1] * 0.65:
                        continue
                        
                raw_t_id = f"{camera_id}_VIS_{int(track_id)}"
                
                # Re-ID Check via API
                if raw_t_id not in id_mapping:
                    hist = get_color_histogram(frame, box)
                    hist_list = hist.flatten().tolist() if hist is not None else []
                    
                    try:
                        resp = requests.post(f"{API_URL}/reid", json={
                            "camera_id": camera_id,
                            "raw_id": raw_t_id,
                            "hist": hist_list
                        }, timeout=2).json()
                        t_id = resp.get("visitor_id", raw_t_id)
                        is_reentry = resp.get("is_reentry", False)
                        is_staff_past = resp.get("is_staff", False)
                    except Exception as e:
                        logger.error(f"Re-ID API failed: {e}")
                        t_id = raw_t_id
                        is_reentry = False
                        is_staff_past = False
                        
                    id_mapping[raw_t_id] = {
                        "t_id": t_id,
                        "is_reentry": is_reentry,
                        "is_staff_past": is_staff_past
                    }
                else:
                    t_id = id_mapping[raw_t_id]["t_id"]
                    is_reentry = id_mapping[raw_t_id]["is_reentry"]
                    is_staff_past = id_mapping[raw_t_id]["is_staff_past"]

                current_frame_ids.add(t_id)
                # Use simulated timestamp starting from 2026-04-10T12:10:00Z to match POS data
                simulated_base_time = datetime.datetime.strptime("2026-04-10T12:10:00Z", "%Y-%m-%dT%H:%M:%SZ")
                # Advance 1 second for every 30 frames
                simulated_now = simulated_base_time + datetime.timedelta(seconds=frame_count / fps)
                
                now = simulated_now
                is_staff_frame = is_staff_heuristic(frame, box)
                
                if t_id not in active_tracks:
                    # Sticky override: if past was staff, they are staff forever.
                    final_is_staff = is_staff_past or is_staff_frame
                    
                    active_tracks[t_id] = {
                        "first_seen": now,
                        "last_seen": now,
                        "last_dwell_emit": now,
                        "entered_zone": False,
                        "is_staff": final_is_staff,
                        "raw_id": raw_t_id,
                        "hist": get_color_histogram(frame, box),
                        "session_seq": 1
                    }
                    
                    event_type = "REENTRY" if is_reentry else ("ENTRY" if "ENTRY" in (zone_id or "") else "DETECTION")
                    if event_type in ["ENTRY", "REENTRY"]:
                        emit_structured_event(
                            store_id, camera_id, t_id, event_type, now, conf, final_is_staff, active_tracks[t_id], zone_id=zone_id
                        )
                        
                    # Fix: Immediately sync this new identity to the global Re-ID database
                    # so if they walk into another camera's view right now, they aren't double-counted!
                    if active_tracks[t_id]["hist"] is not None:
                        try:
                            requests.post(f"{API_URL}/reid/update", json={
                                "visitor_id": t_id,
                                "hist": active_tracks[t_id]["hist"].flatten().tolist(),
                                "is_staff": final_is_staff
                            }, timeout=1)
                        except: pass
                else:
                    active_tracks[t_id]["last_seen"] = now
                    # Update histogram periodically
                    active_tracks[t_id]["hist"] = get_color_histogram(frame, box)
                    
                    # Sticky promotion: if OpenCV confidently flags them later, lock it in!
                    if is_staff_frame and not active_tracks[t_id]["is_staff"]:
                        active_tracks[t_id]["is_staff"] = True
                        # Instantly emit an event so the backend DB registers is_staff=1 for this ID
                        emit_structured_event(
                            store_id, camera_id, t_id, "STAFF_PROMOTION", now, conf, True, active_tracks[t_id], zone_id=zone_id
                        )
                        # Also instantly broadcast this promotion to the global Re-ID database!
                        if active_tracks[t_id]["hist"] is not None:
                            try:
                                requests.post(f"{API_URL}/reid/update", json={
                                    "visitor_id": t_id,
                                    "hist": active_tracks[t_id]["hist"].flatten().tolist(),
                                    "is_staff": True
                                }, timeout=1)
                            except: pass
                    
                track = active_tracks[t_id]
                
                if visualize or web:
                    color = (0, 0, 255) if track["is_staff"] else (0, 255, 0)
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                    label = f"ID:{t_id[-4:]} {'(STAFF)' if track['is_staff'] else ''}"
                    cv2.putText(frame, label, (int(x1), int(y1)-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # Emit zone enter if not yet entered
                if not track["entered_zone"] and zone_id:
                    track["entered_zone"] = True
                    
                    if zone_id == "CASH_COUNTER" and not track["is_staff"]:
                        if queue_depth > 0:
                            queue_depth += 1
                            emit_structured_event(
                                store_id, camera_id, t_id, "BILLING_QUEUE_JOIN", now, conf, track["is_staff"], track,
                                zone_id=zone_id, queue_depth=queue_depth, sku_zone=zone_id
                            )
                        else:
                            queue_depth += 1
                            emit_structured_event(
                                store_id, camera_id, t_id, "ZONE_ENTER", now, conf, track["is_staff"], track,
                                zone_id=zone_id, queue_depth=queue_depth, sku_zone=zone_id
                            )
                    else:
                        emit_structured_event(
                            store_id, camera_id, t_id, "ZONE_ENTER", now, conf, track["is_staff"], track,
                            zone_id=zone_id, sku_zone=zone_id
                        )
                
                # Emit ZONE_DWELL every 30 seconds
                if track["entered_zone"] and (now - track["last_dwell_emit"]).total_seconds() >= 30.0:
                    track["last_dwell_emit"] = now
                    dwell = int((now - track["first_seen"]).total_seconds() * 1000)
                    emit_structured_event(
                        store_id, camera_id, t_id, "ZONE_DWELL", now, conf, track["is_staff"], track,
                        zone_id=zone_id, dwell_ms=dwell, sku_zone=zone_id
                    )
                    
        # Check for lost tracks (exited zone)
        lost_tracks = []
        simulated_base_time = datetime.datetime.strptime("2026-04-10T12:10:00Z", "%Y-%m-%dT%H:%M:%SZ")
        now = simulated_base_time + datetime.timedelta(seconds=frame_count / fps)
        
        for t_id, track in active_tracks.items():
            if t_id not in current_frame_ids:
                if (now - track["last_seen"]).total_seconds() > 2.0:
                    lost_tracks.append(t_id)
                    
        for t_id in lost_tracks:
            track = active_tracks.pop(t_id)
            
            # Send final histogram to API for global Re-ID
            if track["hist"] is not None:
                hist_list = track["hist"].flatten().tolist()
                try:
                    requests.post(f"{API_URL}/reid/update", json={
                        "visitor_id": t_id,
                        "hist": hist_list,
                        "is_staff": track["is_staff"]
                    }, timeout=2)
                except Exception as e:
                    logger.error(f"Re-ID update API failed: {e}")
            
            if track["entered_zone"] and zone_id:
                dwell = int((track["last_seen"] - track["first_seen"]).total_seconds() * 1000)
                
                if zone_id == "CASH_COUNTER" and not track["is_staff"]:
                    queue_depth = max(0, queue_depth - 1)
                    
                    try:
                        start_time = track["first_seen"].strftime("%Y-%m-%dT%H:%M:%SZ")
                        end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
                        pos_resp = requests.get(f"{API_URL}/stores/{store_id}/pos/match?start_time={start_time}&end_time={end_time}", timeout=2).json()
                        matched = pos_resp.get("matched", False)
                    except Exception as e:
                        logger.error(f"POS match API failed: {e}")
                        matched = False
                        
                    if not matched:
                        emit_structured_event(
                            store_id, camera_id, t_id, "BILLING_QUEUE_ABANDON", now, 0.9, track["is_staff"], track,
                            zone_id=zone_id, dwell_ms=dwell, queue_depth=queue_depth, sku_zone=zone_id
                        )
                
                emit_structured_event(
                    store_id, camera_id, t_id, "ZONE_EXIT", now, 0.9, track["is_staff"], track,
                    zone_id=zone_id, dwell_ms=dwell, sku_zone=zone_id
                )
                
                if "ENTRY" in (zone_id or ""):
                    emit_structured_event(
                        store_id, camera_id, t_id, "EXIT", now, 0.9, track["is_staff"], track,
                        zone_id=zone_id, dwell_ms=dwell, sku_zone=zone_id
                    )

        if visualize or web:
            cv2.rectangle(frame, (10, 10), (320, 150), (0, 0, 0), -1)
            cv2.putText(frame, f"Apex Retail - {camera_id}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(frame, f"Visitors: {latest_metrics['visitors']}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, f"Conversion: {latest_metrics['conversion']}", (20, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, f"Queue Depth: {latest_metrics['queue']}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            cv2.putText(frame, f"Zone: {zone_id or 'None'}", (20, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
            
            if web and (time.time() - last_web_frame_sent) >= 0.1:
                last_web_frame_sent = time.time()
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
                if frame_queue.full():
                    try: frame_queue.get_nowait()
                    except: pass
                frame_queue.put(buffer.tobytes())
            
            if visualize:
                cv2.imshow("Apex Retail Intelligence", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    if web:
        # Generate and push a final "Stream Ended" frame so the dashboard doesn't freeze on the last active frame
        end_frame = np.zeros((360, 640, 3), dtype=np.uint8)
        cv2.putText(end_frame, f"Apex Retail - {camera_id}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        text_size = cv2.getTextSize("STREAM ENDED", cv2.FONT_HERSHEY_SIMPLEX, 1.5, 3)[0]
        text_x = (640 - text_size[0]) // 2
        text_y = (360 + text_size[1]) // 2
        cv2.putText(end_frame, "STREAM ENDED", (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        
        _, buffer = cv2.imencode('.jpg', end_frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
        if frame_queue.full():
            try: frame_queue.get_nowait()
            except: pass
        frame_queue.put(buffer.tobytes())
        
        # Give the background web_sender thread 1.5 seconds to successfully POST the final frame to the API
        time.sleep(1.5)

    cap.release()
    logger.info("Finished processing.")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=str, default="ST1008")
    parser.add_argument("--video", type=str, required=True, help="Path to video file")
    parser.add_argument("--visualize", action="store_true", help="Enable UI visualization overlay")
    parser.add_argument("--web", action="store_true", help="Enable MJPEG streaming to web dashboard")
    args = parser.parse_args()
    
    resolved_video = resolve_video_path(args.video)
    if resolved_video:
        if os.path.abspath(resolved_video) != os.path.abspath(args.video):
            logger.info(f"Resolved video path: {resolved_video}")
        process_video(resolved_video, args.store, args.visualize, args.web)
    else:
        logger.error(f"Video {args.video} not found.")
