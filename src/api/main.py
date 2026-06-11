"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from src.api.routes import router

app = FastAPI(title="World Cup Prediction Baseline", version="0.1.0")
app.include_router(router)
