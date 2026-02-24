# RevPublish Module 9

Content Publishing with Parallel Processing via RevCore Gateway

## Structure
```
/opt/revpublish/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── core/
│   │   └── gateway_client.py  # Gateway integration
│   ├── api/                 # API endpoints (NEW)
│   ├── services/            # External services (NEW)
│   ├── routes/              # Existing routes
│   ├── models/              # Data models
│   ├── utils/               # Utilities
│   ├── deployers/           # WordPress deployment
│   ├── extractors/          # Content extraction
│   └── integrations/        # External integrations
├── frontend/                # React UI
├── data/                    # Data storage
├── config/                  # Configuration
└── logs/                    # Application logs
```

## Quick Start
```bash
# Start RevPublish
/opt/revpublish/start.sh

# Or manually
cd /opt/revpublish/backend
python3 main.py
```

## Gateway Integration

RevPublish now uses RevCore Gateway (port 8004) for 3x faster parallel content generation:
```python
from core.gateway_client import GatewayClient

gateway = GatewayClient()
results = await gateway.generate_content_parallel(sites, batch_size=3)
```

## Features

- ✅ Parallel content generation (3 RevRank pipelines)
- ✅ WordPress deployment automation
- ✅ Content extraction and conversion
- ✅ Site scanning and analysis
- ✅ Template management

## Configuration

Environment: `/opt/revpublish/.env.local`
Shared config: `/opt/shared-api-engine/.env`

## Ports

- Backend: As configured in main.py
- RevCore Gateway: 8004 (upstream)
