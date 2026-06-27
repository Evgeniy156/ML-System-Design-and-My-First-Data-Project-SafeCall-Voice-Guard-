"""Home routes — public pages and health check."""
import os
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates

home_route = APIRouter()
templates = Jinja2Templates(directory="view")


@home_route.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@home_route.get("/health")
async def health():
    return {"status": "ok", "service": "safecall-api"}
