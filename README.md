# Abyssal Lens

Abyssal Lens is an AI-powered marine intelligence platform for real-time detection, classification, and analysis of marine plastic pollution. The project combines computer vision, deep learning, and geospatial analysis to detect floating debris, identify plastic materials, and support environmental monitoring and cleanup planning.

This repository contains the working project files for a research-oriented platform that includes:

- a landing page and analytics dashboard
- image and video analysis workflows
- geospatial and monitoring views
- backend Flask APIs for model-driven processing
- machine learning model loading and configuration

The project is based on the repository structure and implementation currently present in the codebase and includes the project documentation files:

- `Chapter 1.docx`
- `Chapter 2 FYP.docx`

## Repository overview

The repository is organized into these main areas:

- `index.html` — landing page redirect to the main application page
- `pages/` — front-end web pages for the platform UI
- `assets/` — shared frontend styling assets
- `backend/` — Python backend, database, routes, models, and utilities

## Project structure

```text
AI-Powered-Real-Time-Detection-and-Analysis-of-Marine-Plastic-Pollution/
├── README.md
├── Chapter 1.docx
├── Chapter 2 FYP.docx
├── index.html
├── assets/
│   └── css/
│       └── shared.css
├── pages/
│   ├── admin.html
│   ├── alerts.html
│   ├── authentication.html
│   ├── create
│   ├── dashboard.html
│   ├── geospatial.html
│   ├── image-analysis.html
│   ├── index.html
│   ├── live-monitoring.html
│   └── reports.html
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── requirements.txt
│   ├── __pycache__/
│   ├── database/
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── static/
│   ├── uploads/
│   └── utils/
└── .gitignore (if present in repo)
```

## What this project does

The system is designed to support marine plastic pollution monitoring through the following stages:

1. Data acquisition from images, video streams, and satellite-like sources
2. AI-powered object detection to locate plastic debris
3. Classification of detected material types
4. Visualization through dashboards and reports
5. Environmental monitoring and decision support

The frontend pages indicate an application called "Abyssal Lens" with sections for:

- Dashboard
- Analysis
- Satellite / geospatial monitoring
- Reports
- Alerts
- Admin / authentication views

## Frontend summary

The main front-end is a dark themed web application built with HTML, CSS, and JavaScript with Tailwind styling. The `pages/index.html` file contains the main product landing page and multi-section interface for:

- hero section and platform introduction
- intelligence stack overview
- detection and analysis workflows
- SDG 14 / ocean protection messaging
- call-to-action sections

The project uses a modern visual design with a marine-tech style and a “Abyssal Lens” brand identity.

## Backend summary

The Python backend is a Flask application with these main building blocks:

- `backend/app.py` — application factory and route registration
- `backend/config.py` — app configuration, upload paths, database location, and ML model paths
- `backend/requirements.txt` — project dependencies

The backend is configured to load and use:

- YOLO detection model
- CNN classifier
- LSTM-based trend prediction model

It also sets up:

- upload directory
- static report and annotated output directories
- SQLite database path
- CORS and app health routes

## Main backend dependencies

The actual project dependency file includes:

- Flask
- Flask-CORS
- Werkzeug
- Pillow
- OpenCV
- NumPy
- PyTorch
- TorchVision
- Ultralytics
- TensorFlow
- ReportLab
- python-dotenv

This reflects a research-oriented AI application stack designed for image processing and model inference.

## How to run the project

### 1. Clone the repository

```bash
git clone https://github.com/Chaudhary6559/AI-Powered-Real-Time-Detection-and-Analysis-of-Marine-Plastic-Pollution.git
cd AI-Powered-Real-Time-Detection-and-Analysis-of-Marine-Plastic-Pollution
```

### 2. Set up the backend environment

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run the Flask app

```bash
python app.py
```

The backend will run on the default Flask port, typically:

```text
http://localhost:5000
```

### 4. Open the frontend

The root `index.html` redirects to `pages/index.html`, so opening the app through the repository root or the landing page route will load the main interface.

## API and app behavior

From the backend application structure, the app is designed to expose several route groups for:

- authentication
- image analysis
- streaming and monitoring
- dashboard data
- geospatial intelligence
- report generation
- alert notifications

The project includes a health endpoint:

```text
GET /health
```

and the app returns JSON status responses for health and common errors.

## Project purpose and research context

The repository aligns with a marine-environmental AI use case focused on the detection and quantification of plastic pollution in coastal and oceanic areas. It reflects a practical system that could support:

- environmental monitoring agencies
- research institutions
- marine conservation efforts
- cleanup and response coordination
