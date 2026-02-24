import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging

# -----------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------
LOG_FILE = "/var/log/revhome_api_app.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="RevHome Assessment Engine (Privacy-Protected)")
from app.health import router as health_router
app.include_router(health_router)

# Allow CORS for flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict later to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>RevHome Report Generator</title>
    <style>
      body {font-family: Arial, sans-serif; background: #f6f7f9; display: flex; flex-direction: column; align-items: center; margin-top: 100px;}
      h1 {color: #0d6efd;}
      input {padding: 10px; font-size: 16px; width: 300px; border-radius: 8px; border: 1px solid #ccc; margin-top: 10px;}
      button {background: #0d6efd; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; margin-top: 10px;}
      button:hover {background: #0b5ed7;}
      #msg {margin-top: 15px; font-size: 14px; color: #333;}
    </style>
    </head>
    <body>
      <h1>RevHome Report Generator</h1>
      <p>Enter client name and click Generate:</p>
      <input type="text" id="client" placeholder="e.g. MR.LAW" />
      <button onclick="generateReport()">Generate Report</button>
      <div id="msg"></div>
      <script>
        async function generateReport() {
          const client = document.getElementById('client').value.trim();
          if (!client) return alert('Please enter a client name.');
          document.getElementById('msg').innerText = '⏳ Generating report... please wait...';
          try {
            const res = await fetch('/generate_report', {
              method: 'POST',
              headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer SUPERSECRETKEY123'},
              body: JSON.stringify({ client })
            });
            if (!res.ok) {
              const err = await res.json();
              document.getElementById('msg').innerText = '❌ ' + (err.error || 'Failed to generate report.');
              return;
            }
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = client.replace(/\s+/g, '_') + '_report.docx';
            a.click();
            window.URL.revokeObjectURL(url);
            document.getElementById('msg').innerText = '✅ Download started!';
          } catch (e) {
            document.getElementById('msg').innerText = '❌ Error: ' + e.message;
          }
        }
      </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

@app.post("/generate_report")
async def generate_report(req: Request):
    data = await req.json()
    client = data.get("client", "").strip()

    if not client:
        return JSONResponse({"error": "Client name required."}, status_code=400)

    # Dummy doc generation logic for now
    report_path = f"/tmp/{client.replace(' ', '_')}_report.docx"
    with open(report_path, "w") as f:
        f.write(f"RevHome report for {client} - generated at {datetime.utcnow()}")

    logging.info(f"Report generated for {client}")
    return FileResponse(report_path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", filename=os.path.basename(report_path))

# -----------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8081))
    logging.info(f"Starting RevHome API on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level=os.getenv("LOG_LEVEL", "info"))
