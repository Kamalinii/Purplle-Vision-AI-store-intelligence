# Purplle-Vision-AI-store-intelligence
AI-powered retail store intelligence platform that transforms CCTV feeds into real-time customer analytics, conversion funnels, queue monitoring, dwell-time insights, and heatmap visualizations using YOLOv8, FastAPI, and OpenCV.
# 🟣 Purplle Vision AI – Real-Time Store Intelligence Platform

End-to-end retail analytics system that converts CCTV footage into actionable business intelligence using Computer Vision, Event Analytics, and Real-Time Dashboards.

Built for the Purplle Engineering Hiring Challenge 2026.

---

## 🚀 Overview

Purplle Vision AI helps retail stores understand customer behavior without requiring additional hardware.

Using existing CCTV infrastructure, the system automatically tracks visitors, measures engagement across product zones, monitors billing queues, generates conversion funnels, and visualizes customer movement through live heatmaps.

The platform transforms raw video streams into business insights that store managers can use to improve customer experience, optimize layouts, and increase conversions.

---

## 🔄 System Pipeline

CCTV Cameras

↓

YOLOv8 Person Detection

↓

Multi-Object Tracking

↓

Visitor Re-Identification

↓

Event Generation

↓

FastAPI Analytics Engine

↓

SQLite Event Store

↓

Live Intelligence Dashboard

---

## ✨ Core Features

### 🎥 Multi-Camera Monitoring

* Simultaneous processing of 5 CCTV feeds
* Live video streaming dashboard
* Real-time visitor tracking

### 👥 Visitor Analytics

* Unique visitor counting
* Staff exclusion
* Cross-camera re-identification
* Re-entry detection

### ⏱️ Dwell Time Analytics

Measures customer engagement in:

* Skincare Zone
* Makeup Zone
* Storage Zone
* Billing Zone

### 📊 Conversion Funnel

Tracks customer journey:

Entry

↓

Zone Visit

↓

Billing Queue

↓

Purchase

Provides conversion and drop-off visibility.

### 🔥 AI Heatmaps

Visualizes:

* High traffic zones
* Customer engagement hotspots
* Average dwell density

### 🛒 POS Correlation

Links in-store activity with transaction records to estimate conversion rates.

### 🚦 Queue Intelligence

Monitors:

* Billing queue depth
* Queue abandonment
* Checkout bottlenecks

### 📈 Live Dashboard

Displays:

* Visitor Count
* Conversion Rate
* Queue Depth
* Abandonment Rate
* Funnel Analytics
* Heatmaps
* Live Camera Streams

---

## 🏗️ Architecture

Camera Feeds
↓
YOLOv8 + OpenCV
↓
Tracking + Re-ID
↓
Event Engine
↓
FastAPI Backend
↓
SQLite Database
↓
Analytics Layer
↓
Dashboard UI

---

## 🛠️ Technology Stack

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

## 📂 Project Structure

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

│ ├── reid.py

│ ├── detection.py

│ └── ingestion.py

├── data/

│ ├── CCTV Footage/

│ ├── layout.png

│ └── transactions.csv

├── docs/

│ ├── DESIGN.md

│ └── CHOICES.md

└── requirements.txt

---

## ⚡ Quick Start

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

### 5. Start API

uvicorn app.main:app --reload

### 6. Start Camera Pipelines

Open separate terminals:

python pipeline/cam1.py

python pipeline/cam2.py

python pipeline/cam3.py

python pipeline/cam4.py

python pipeline/cam5.py

### 7. Open Dashboard

http://localhost:8000/dashboard

---

## 📊 Analytics Generated

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

## 🎯 Business Impact

Retail teams can use the platform to:

* Optimize store layouts
* Identify high-performing zones
* Detect customer drop-off points
* Reduce checkout bottlenecks
* Improve staffing decisions
* Increase conversions

without deploying additional sensors or hardware.

---

## 📖 Documentation

* DESIGN.md – System Architecture & AI-Assisted Decisions
* CHOICES.md – Engineering Trade-offs & Key Design Decisions

---

## 👥 Team

Purplle Engineering Challenge 2026

AI-Powered Store Intelligence using Computer Vision and Real-Time Analytics.
