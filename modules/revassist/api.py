# /root/revhome_assessment_engine_v2/api.py

from fastapi import FastAPI

# Create the FastAPI app instance
app = FastAPI()

# Define a simple route to test the API
@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

# --- Added simple root route to satisfy reverse proxy GET on "/" ---
try:
    from fastapi import FastAPI
    app  # type: ignore  # noqa: F821
except Exception:
    pass

if 'app' in globals():
    @app.get("/", include_in_schema=False)
    async def root():
        return {"status": "ok", "msg": "revhome_api root"}
