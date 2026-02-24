# RevScore IQ™ Module 2

Professional website assessment and P0-P3 scoring system.

## Structure
```
modules/revscore-iq/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models/              # Database models
│   ├── routes/              # API endpoints
│   ├── services/            # Business logic
│   └── utils/               # Utilities
├── frontend/                # React UI
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   └── public/
│       └── schemas/         # JSON schemas for screens
└── public/
    └── schemas/             # Public JSON schemas
```

## Quick Start

```bash
# Start backend
cd modules/revscore-iq/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8100

# Start frontend (in another terminal)
cd modules/revscore-iq/frontend
npm install
npm run dev
```

## Features

- ✅ 16 Screens (Dashboard, Assessment Flow, Reports, Settings)
- ✅ 8 Assessment Modules (A, B, C, D, E, E1, E2, F)
- ✅ 41 Scoring Components
- ✅ 5-Stage AI Pipeline
- ✅ 4 Report Types (Executive, Comprehensive, Regional, JSON)
- ✅ 32 Appendices Library
- ✅ P0-P3 Classification System

## Ports

- Backend: 8100
- Frontend: 3001 (dev) / 8101 (production)

