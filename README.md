# Purplle-Vision-AI-store-intelligence
AI-powered retail store intelligence platform that transforms CCTV feeds into real-time customer analytics, conversion funnels, queue monitoring, dwell-time insights, and heatmap visualizations using YOLOv8, FastAPI, and OpenCV.
Built for the Purplle Tech Challenge 2026.
#  Purplle Vision AI – Real-Time Store Intelligence Platform

End-to-end retail analytics system that converts CCTV footage into actionable business intelligence using Computer Vision, Event Analytics, and Real-Time Dashboards.

Built for the Purplle Engineering Hiring Challenge 2026.

---

##  Overview

Purplle Vision AI helps retail stores understand customer behavior without requiring additional hardware.

Using existing CCTV infrastructure, the system automatically tracks visitors, measures engagement across product zones, monitors billing queues, generates conversion funnels, and visualizes customer movement through live heatmaps.
The platform transforms raw video streams into business insights that store managers can use to improve customer experience, optimize layouts, and increase conversions.

System Screenshots
<img width="1837" height="907" alt="Screenshot (403)" src="https://github.com/user-attachments/assets/05b0bfb1-7344-4e5f-83c6-09ece7fe685f" />
<img width="1885" height="907" alt="Screenshot (402)" src="https://github.com/user-attachments/assets/0c100a41-b690-42f6-bae5-86b53e311337" />
<img width="2830" height="1546" alt="image" src="https://github.com/user-attachments/assets/d13e7c99-9aca-43b9-ae6e-4a8846859635" />
<img width="1835" height="874" alt="Screenshot (400)" src="https://github.com/user-attachments/assets/7f0cc42d-47c5-4ca0-bd47-45a8bcd84713" />

---
System Architecture

                    ┌────────────────────┐
                    │ CCTV Camera Feeds  │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ YOLOv8 Detection   │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ ByteTrack Tracking │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ Re-Identification  │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ Event Generation   │
                    └─────────┬──────────┘
                              │
                              ▼
                    ┌────────────────────┐
                    │ FastAPI Backend    │
                    └─────────┬──────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼                               ▼
    ┌──────────────────┐          ┌──────────────────┐
    │ SQLite Database  │          │ POS Correlation  │
    └────────┬─────────┘          └────────┬─────────┘
             │                             │
             └──────────────┬──────────────┘
                            ▼
                  ┌──────────────────┐
                  │ Analytics Engine │
                  └────────┬─────────┘
                           ▼
                  ┌──────────────────┐
                  │ Live Dashboard   │
                  └──────────────────┘
##  Core Features

### Multi-Camera Monitoring

* Simultaneous processing of 5 CCTV feeds
* Live video streaming dashboard
* Real-time visitor tracking

### Visitor Analytics

* Unique visitor counting
* Staff exclusion
* Cross-camera re-identification
* Re-entry detection

### Dwell Time Analytics

Measures customer engagement in:

* Skincare Zone
* Makeup Zone
* Storage Zone
* Billing Zone

###  Conversion Funnel

Tracks customer journey:

Entry

↓

Zone Visit

↓

Billing Queue

↓

Purchase

Provides conversion and drop-off visibility.

###  AI Heatmaps

Visualizes:

* High traffic zones
* Customer engagement hotspots
* Average dwell density

###  POS Correlation

Links in-store activity with transaction records to estimate conversion rates.

###  Queue Intelligence

Monitors:

* Billing queue depth
* Queue abandonment
* Checkout bottlenecks

### Live Dashboard

Displays:

* Visitor Count
* Conversion Rate
* Queue Depth
* Abandonment Rate
* Funnel Analytics
* Heatmaps
* Live Camera Streams

---

##  Technology Stack

### Computer Vision

* YOLOv8
* OpenCV
* NumPy

### Backend

* FastAPI
* AsyncIO
* AioSQLite

### Database

* SQLite

### Frontend

* HTML
* Tailwind CSS
* JavaScript

### Streaming

* MJPEG Streaming

---

##  Project Structure

store-intelligence/

├── app/

│ ├── main.py

│ ├── metrics.py

│ ├── heatmap.py

│ ├── funnel.py

│ ├── anomalies.py

│ ├── health.py

│ └── static/

│ └── dashboard.html

├── pipeline/

│ ├── track.py

│ ├── detect.py

│ └── run_all.py

├── data/

│ ├── CCTV Footage/ //all camera screens

│ ├── layout.png

│ └── transactions.csv

├── docs/

│ ├── DESIGN.md

│ └── CHOICES.md

└── requirements.txt

---

##  Quick Start

### 1. Clone Repository

git clone <repository-url>

cd store-intelligence

### 2. Create Environment

python -m venv venv

### 3. Activate Environment

Windows:

venv\Scripts\activate

### 4. Install Dependencies

pip install -r requirements.txt

NOTE : Add the Video Datasets in the Data folder
To comply with repository size limits, the raw `.mp4` video files are excluded. 
1. Create the data directory: `mkdir -p "data/CCTV Footage"`
2. Place your raw video clips into the folder (e.g., `CAM 1.mp4`, `CAM 2.mp4`).

### 5. Start API

uvicorn app.main:app --reload

### 6. Start Camera Pipelines

Open separate terminals:

python pipeline\detect.py --video "data\CCTV Footage\cam1.mp4" --web

python pipeline\detect.py --video "data\CCTV Footage\cam2.mp4" --web

python pipeline\detect.py --video "data\CCTV Footage\cam3.mp4" --web

python pipeline\detect.py --video "data\CCTV Footage\cam4.mp4" --web

python pipeline\detect.py --video "data\CCTV Footage\cam5.mp4" --web


### 7. Open Dashboard

http://localhost:8000/dashboard


To visualize the footage detection and tracking  run :
  python pipeline\detect.py --video "data\CCTV Footage\CAM 1.mp4" --visualize  
  python pipeline\detect.py --video "data\CCTV Footage\CAM 2.mp4" --visualize  
  python pipeline\detect.py --video "data\CCTV Footage\CAM 3.mp4" --visualize  
  python pipeline\detect.py --video "data\CCTV Footage\CAM 4.mp4" --visualize  
  python pipeline\detect.py --video "data\CCTV Footage\CAM 5.mp4" --visualize  

---

##  Analytics Generated

### Footfall Metrics

* Unique Visitors
* Visitor Sessions

### Engagement Metrics

* Average Dwell Time
* Zone Popularity

### Funnel Metrics

* Entry Count
* Zone Visits
* Billing Queue
* Purchases

### Queue Metrics

* Queue Depth
* Abandonment Rate

### Heatmap Metrics

* Frequency Score
* Dwell Score

---

##  Business Impact

Retail teams can use the platform to:

* Optimize store layouts
* Identify high-performing zones
* Detect customer drop-off points
* Reduce checkout bottlenecks
* Improve staffing decisions
* Increase conversions

without deploying additional sensors or hardware.

---

## Documentation & Hackathon Criteria

Every major architectural decision, trade-off, and AI usage has been meticulously documented to meet the Hackathon grading rubric:

- **[docs/DESIGN.md](./docs/DESIGN.md)**: Contains the comprehensive system architecture, Mermaid diagrams, event schemas, and the mandatory **AI-Assisted Decisions** documentation.
- **[docs/CHOICES.md](./docs/CHOICES.md)**: Deep-dive rationale behind three major architectural trade-offs: *Decoupled Vision Layers*, *Stateless Ledgers*, and *SQLite WAL*.



* DESIGN.md – System Architecture & AI-Assisted Decisions
* CHOICES.md – Engineering Trade-offs & Key Design Decisions


                                                                         Built with and  for the Purplle Tech Challenge 2026
