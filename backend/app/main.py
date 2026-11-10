from fastapi import FastAPI

from backend.app.exceptions.exception_handlers import register_exception_handlers
from backend.app.routers import auth

app = FastAPI(title="OGE")

register_exception_handlers(app)


@app.get("/health")
def check_health():
    return {"status": "ok"}


app.include_router(auth.router)
