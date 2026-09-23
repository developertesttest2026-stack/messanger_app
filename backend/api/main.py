from fastapi import FastAPI
from contextlib import asynccontextmanager
from api.database import init_db
from api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(title="Auth System for Messanger", lifespan=lifespan)
app.include_router(router)


