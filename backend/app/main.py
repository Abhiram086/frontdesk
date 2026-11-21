import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import auth, routes_public, routes_staff, service


async def sweeper():
    while True:
        try:
            # Runs immediately on startup to catch up after any downtime, then every 60s
            await asyncio.to_thread(service.run_sweep)
        except Exception:
            logging.exception("sweep failed")
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(sweeper())
    yield
    task.cancel()


app = FastAPI(title="Frontdesk", lifespan=lifespan)


class Login(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
def login(data: Login):
    u = auth.check_login(data.email, data.password)
    return {
        "token": auth.make_token(u),
        "user": {"id": u["id"], "name": u["name"], "role": u["role"]},
    }


@app.get("/api/health")
def health():
    return {"ok": True}


app.include_router(routes_staff.router)
app.include_router(routes_public.router)

# Serve the compiled React app in production (copied to backend/static by Docker)
if os.path.isdir("static"):
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404)
        return FileResponse("static/index.html")