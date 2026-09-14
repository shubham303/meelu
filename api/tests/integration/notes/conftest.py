from src.app import app
from src.notes.endpoints import router as notes_router

if not any(getattr(route, "path", None) == "/api/v1/notes" for route in app.routes):
    app.include_router(notes_router, prefix="/api/v1")
