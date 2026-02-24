# RevFlow Enrichment Service - Deployment Guide

## 📋 Prerequisites

- Python 3.11+
- Docker & Docker Compose (optional)
- API keys for providers (see Setup section)
- Access to RevFlow backend (Port 5000)

---

## 🚀 Deployment Options

### Option 1: Docker (Recommended for Production)

```bash
# 1. Navigate to service directory
cd /opt/revflow-enrichment

# 2. Copy environment file
cp .env.example .env

# 3. Edit with your API keys
nano .env

# 4. Build and start service
docker-compose up -d

# 5. Verify health
curl http://localhost:8500/health
```

### Option 2: Python Virtual Environment

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment file
cp .env.example .env
nano .env

# 4. Run service
uvicorn main:app --host 0.0.0.0 --port 8500 --workers 4

# 5. Verify health
curl http://localhost:8500/health
```

### Option 3: Systemd Service (Production Linux)

```bash
# 1. Create service file
sudo nano /etc/systemd/system/revflow-enrichment.service
```

Paste this content:
```ini
[Unit]
Description=RevFlow Enrichment Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/revflow-enrichment
Environment="PATH=/opt/revflow-enrichment/venv/bin"
ExecStart=/opt/revflow-enrichment/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8500 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 2. Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable revflow-enrichment
sudo systemctl start revflow-enrichment

# 3. Check status
sudo systemctl status revflow-enrichment

# 4. View logs
sudo journalctl -u revflow-enrichment -f
```

---

## 🔑 API Key Setup

### Phase 1: Minimum Viable (Week 1) - $65/month

**Required for basic functionality:**

1. **Hunter.io** - Email Finding
   - Sign up: https://hunter.io/users/sign_up
   - Get API key: https://hunter.io/api-keys
   - Plan: Starter ($49/mo for 1,000 searches)
   - Add to .env: `HUNTER_API_KEY="your_key_here"`

2. **ZeroBounce** - Email Validation
   - Sign up: https://www.zerobounce.net/members/signup/
   - Get API key: https://www.zerobounce.net/members/apikey/
   - Plan: Pay-as-you-go ($16 for 2,000 validations)
   - Add to .env: `ZEROBOUNCE_API_KEY="your_key_here"`

3. **DataForSEO** - Tech Stack (Already have)
   - You already have this configured
   - Verify in .env: `DATAFORSEO_LOGIN` and `DATAFORSEO_PASSWORD`

### Phase 2: Enhanced (Week 2-3) - $364/month

**Add for full enrichment:**

4. **People Data Labs** - Core Enrichment
   - Sign up: https://www.peopledatalabs.com/signup
   - Get API key: https://dashboard.peopledatalabs.com/main/api-keys
   - Plan: Growth ($299/mo for 10,000 enrichments)
   - Add to .env: `PEOPLE_DATA_LABS_API_KEY="your_key_here"`

### Phase 3: Complete (Week 4) - $650/month

**Add for waterfall optimization:**

5. **Prospeo** - Secondary Email Finder
   - Sign up: https://prospeo.io/pricing
   - Plan: Scale ($99/mo)
   - Add to .env: `PROSPEO_API_KEY="your_key_here"`

6. **Datagma** - Email + Phone Finder
   - Sign up: https://www.datagma.com/
   - Plan: Premium ($99/mo)
   - Add to .env: `DATAGMA_API_KEY="your_key_here"`

7. **Twilio** - Phone Validation
   - Sign up: https://www.twilio.com/try-twilio
   - Get credentials: https://www.twilio.com/console
   - Pay-as-you-go: $0.005 per lookup
   - Add to .env: `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`

8. **AudienceLab** - Visitor Intelligence (Already have?)
   - Contact: https://audiencelab.io/
   - Add to .env: `AUDIENCELAB_API_KEY="your_key_here"`

---

## 🔗 Backend Integration

### Add Enrichment Proxy to Backend Gateway

Edit your backend Flask app to add enrichment proxy:

**File:** `/opt/smarketsherpa-platform/backend/app.py`

```python
# Add this near top of file
from flask import Blueprint, request
import httpx

# Create enrichment blueprint
enrich_bp = Blueprint('enrich', __name__, url_prefix='/api/v1/enrich')

@enrich_bp.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def proxy_to_enrichment(path):
    """Proxy all /api/v1/enrich/* requests to enrichment service"""
    
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE')
        return response
    
    try:
        url = f"http://localhost:8500/api/v1/enrich/{path}"
        
        # Make request to enrichment service
        with httpx.Client(timeout=30.0) as client:
            if request.method == 'GET':
                response = client.get(url, params=request.args)
            else:
                response = client.request(
                    method=request.method,
                    url=url,
                    json=request.get_json() if request.is_json else None,
                    params=request.args
                )
        
        # Return response
        return response.json(), response.status_code
        
    except Exception as e:
        return {"error": str(e), "service": "enrichment"}, 500

# Register blueprint (add near other blueprint registrations)
app.register_blueprint(enrich_bp)
```

**Restart backend:**
```bash
sudo systemctl restart smarketsherpa-backend
# or
docker-compose restart backend
```

**Test integration:**
```bash
curl -X POST http://217.15.168.106:5000/api/v1/enrich/email \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Smith",
    "company_domain": "example.com"
  }'
```

---

## 🧪 Testing

### 1. Health Check

```bash
curl http://localhost:8500/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-30T10:00:00Z",
  "services": {
    "hunter": true,
    "zerobounce": true,
    "dataforseo": true,
    "audiencelab": true
  }
}
```

### 2. Run Test Suite

```bash
python test_endpoints.py
```

Expected: 18 endpoints tested, should pass all with configured API keys.

### 3. Test Individual Endpoint

```bash
curl -X POST http://localhost:8500/api/v1/enrich/email \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Smith",
    "company_domain": "example.com"
  }'
```

---

## 📊 Monitoring

### View Logs

**Docker:**
```bash
docker-compose logs -f enrichment-service
```

**Systemd:**
```bash
sudo journalctl -u revflow-enrichment -f
```

### Check Cost Tracking

```bash
curl http://217.15.168.106:5000/api/v1/costs/summary?days=7
```

### API Documentation

Open in browser:
- Swagger: http://localhost:8500/docs
- ReDoc: http://localhost:8500/redoc

---

## 🔒 Security Considerations

### 1. Add API Authentication (Recommended for Production)

**Add JWT authentication:**

```python
# In main.py, add this import
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    # Implement your JWT verification logic here
    pass

# Add to endpoints
@app.post("/api/v1/enrich/email", dependencies=[Depends(verify_token)])
async def find_email(...):
    ...
```

### 2. Rate Limiting

Already implemented via `RateLimiter` class. Configure in .env:
```
RATE_LIMIT_PER_MINUTE=60
```

### 3. HTTPS

Use Nginx reverse proxy:
```nginx
server {
    listen 443 ssl;
    server_name enrichment.revflow.io;
    
    ssl_certificate /etc/ssl/certs/revflow.crt;
    ssl_certificate_key /etc/ssl/private/revflow.key;
    
    location / {
        proxy_pass http://localhost:8500;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🚨 Troubleshooting

### Service Won't Start

```bash
# Check if port 8500 is available
lsof -i :8500

# Check logs
docker-compose logs enrichment-service
# or
sudo journalctl -u revflow-enrichment -n 100
```

### API Key Errors

```bash
# Verify .env file exists
ls -la .env

# Check if keys are loaded
curl http://localhost:8500/health
```

### High Costs

```bash
# Check daily costs
curl http://217.15.168.106:5000/api/v1/costs/summary?days=1

# Review provider costs in config.py
cat config.py | grep PROVIDER_COSTS
```

### Slow Responses

- Increase workers: `--workers 8`
- Add Redis caching
- Enable connection pooling

---

## 📈 Scaling

### Horizontal Scaling (Multiple Instances)

```yaml
# docker-compose.yml
services:
  enrichment-service-1:
    build: .
    ports:
      - "8501:8500"
  
  enrichment-service-2:
    build: .
    ports:
      - "8502:8500"
  
  enrichment-lb:
    image: nginx:alpine
    ports:
      - "8500:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Add Load Balancer (Nginx)

```nginx
upstream enrichment_backend {
    least_conn;
    server localhost:8501;
    server localhost:8502;
}

server {
    listen 8500;
    
    location / {
        proxy_pass http://enrichment_backend;
    }
}
```

---

## ✅ Deployment Checklist

- [ ] Python 3.11+ installed
- [ ] All API keys configured in .env
- [ ] Service running on port 8500
- [ ] Health check returns 200
- [ ] Backend proxy configured (Port 5000)
- [ ] Test suite passes
- [ ] Cost tracking working
- [ ] Monitoring/logging configured
- [ ] SSL/HTTPS enabled (production)
- [ ] Rate limiting configured
- [ ] Backups configured

---

## 🎉 Success!

Your enrichment service is now:
- ✅ Deployed and running
- ✅ Integrated with backend
- ✅ Tracking costs
- ✅ Ready for production

**Next Steps:**
1. Test with real data
2. Monitor costs for 1 week
3. Add more providers as needed
4. Scale horizontally if needed

**Support:**
- API Docs: http://localhost:8500/docs
- Health: http://localhost:8500/health
- Costs: http://217.15.168.106:5000/api/v1/costs/summary
