# RevScore IQ Quick Start Guide

## Prerequisites

- Python 3.9+
- Node.js 18+
- PostgreSQL database
- npm or yarn

## Setup Steps

### 1. Database Setup

Ensure PostgreSQL is running and create the database:

```sql
CREATE DATABASE revflow;
```

Or use existing database from RevFlow OS.

### 2. Backend Setup

```bash
cd modules/revscore-iq/backend

# Install dependencies
pip install -r requirements.txt

# Setup database tables
python setup_db.py

# Start backend server
python -m uvicorn main:app --host 0.0.0.0 --port 8100 --reload
```

Backend will be available at: http://localhost:8100
API docs at: http://localhost:8100/docs

### 3. Frontend Setup

```bash
cd modules/revscore-iq/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:3001

## Environment Variables

Create `.env` file in `backend/` directory:

```env
DATABASE_URL=postgresql://revflow:revflow2026@localhost:5432/revflow
```

## Testing the API

### Health Check
```bash
curl http://localhost:8100/health
```

### Create Assessment
```bash
curl -X POST http://localhost:8100/api/assessments \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_name": "Test Business",
    "prospect_url": "https://example.com",
    "industry": "home_services"
  }'
```

### Get Dashboard Stats
```bash
curl http://localhost:8100/api/assessments/stats
```

## Current Implementation Status

✅ **Completed:**
- Database models (all tables)
- Core backend API endpoints
- Frontend structure
- Database setup script

🚧 **In Progress:**
- Frontend App component
- JSON schemas for screens
- 5-stage AI pipeline implementation

📋 **Pending:**
- Full scoring logic implementation
- Report generation
- All 16 screen schemas
- Settings implementation

## Next Steps

1. Complete frontend App.jsx and JSONRender component
2. Create JSON schemas for all 16 screens
3. Implement actual scoring logic (replace placeholders)
4. Implement report generation
5. Test full assessment flow

## File Structure

```
modules/revscore-iq/
├── backend/
│   ├── main.py              # FastAPI app ✅
│   ├── models.py            # Database models ✅
│   ├── setup_db.py          # Database setup ✅
│   ├── routes/              # API routes (to be created)
│   ├── services/            # Business logic (to be created)
│   └── utils/               # Utilities (to be created)
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main app (to be created)
│   │   ├── main.jsx         # Entry point ✅
│   │   └── components/      # React components (to be created)
│   └── public/
│       └── schemas/         # JSON schemas (to be created)
└── public/
    └── schemas/             # Public schemas (to be created)
```

## Troubleshooting

### Database Connection Error
- Check PostgreSQL is running
- Verify DATABASE_URL in .env
- Ensure database exists

### Port Already in Use
- Backend: Change port in `main.py` or use `--port` flag
- Frontend: Change port in `vite.config.js`

### Module Import Errors
- Ensure all dependencies are installed
- Check Python path includes project root

