from fastapi import FastAPI

app = FastAPI(title="OGE")

@app.get("/health")
def check_health():
    return {"status":"ok"}