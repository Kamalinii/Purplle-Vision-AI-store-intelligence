from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class EventMetadata(BaseModel):
    queue_depth: Optional[int] = None
    sku_zone: Optional[str] = None
    session_seq: Optional[int] = None

class DetectionEvent(BaseModel):
    event_id: str
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: datetime
    zone_id: Optional[str] = None
    dwell_ms: int = 0
    is_staff: bool = False
    confidence: float
    metadata: Optional[EventMetadata] = Field(default_factory=EventMetadata)

class IngestResponse(BaseModel):
    status: str
    processed: int
    errors: int
    error_details: List[str] = []

class MetricsResponse(BaseModel):
    unique_visitors: int
    conversion_rate: float
    avg_dwell_per_zone: Dict[str, float]
    queue_depth: int
    abandonment_rate: float

class FunnelStage(BaseModel):
    stage: str
    count: int
    dropoff_percentage: float

class FunnelResponse(BaseModel):
    funnel: List[FunnelStage]

class HeatmapZone(BaseModel):
    zone_id: str
    frequency_score: int
    avg_dwell_score: int

class HeatmapResponse(BaseModel):
    zones: List[HeatmapZone]
    data_confidence: bool

class Anomaly(BaseModel):
    anomaly_type: str
    severity: str
    description: str
    suggested_action: str

class AnomaliesResponse(BaseModel):
    active_anomalies: List[Anomaly]

class HealthResponse(BaseModel):
    status: str
    stores: Dict[str, dict]

class ReIdRequest(BaseModel):
    camera_id: str
    raw_id: str
    hist: List[float]

class ReIdUpdateRequest(BaseModel):
    visitor_id: str
    hist: List[float]
    is_staff: bool = False
