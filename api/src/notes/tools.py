from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.notes.service import note_service
from src.notes.schemas import (
    NoteCreateRequest,
    NoteDeleteResponse,
    NoteResponse,
    NoteUpdateRequest,
)


@tool(writes=True)
async def save_note(note: str, kind: str = "note") -> NoteResponse:
    """Save a standing note for this website: a rule ('note') or a correction the
    user made ('feedback'). In the user's words; check
    the notes table first and update the overlapping note instead of adding a
    near-duplicate."""
    ctx = require_site()
    body = NoteCreateRequest(note=note, kind=kind)
    async with unit_of_work() as db:
        saved = await note_service.create_note(db, ctx.user_id, ctx.site_id, body)
    return NoteResponse.model_validate(saved)


@tool(writes=True)
async def update_note(
    note_id: str, note: str | None = None, kind: str | None = None
) -> NoteResponse:
    """Rewrite an existing note's text and/or kind by its id (from the notes
    table)."""
    ctx = require_site()
    body = NoteUpdateRequest(note=note, kind=kind)
    async with unit_of_work() as db:
        updated = await note_service.update_note(db, ctx.site_id, note_id, body)
    return NoteResponse.model_validate(updated)


@tool(writes=True)
async def delete_note(note_id: str) -> NoteDeleteResponse:
    """Delete a note by its id (from the notes table). Only when the user asks."""
    ctx = require_site()
    async with unit_of_work() as db:
        record = await note_service.delete_note(db, ctx.site_id, note_id)
    return NoteDeleteResponse(id=record.id)
