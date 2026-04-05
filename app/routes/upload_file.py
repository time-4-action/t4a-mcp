import os
import uuid
import aiofiles
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from bson import ObjectId

from app.auth import require_api_key
from app.db.mongo import get_sources_col
from app.pipeline.ingester import ingest_source
import app.config as settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt", ".csv", ".html", ".md"}


@router.post("/admin/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    label: str = Form(None),
    _: str = Depends(require_api_key),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    dest = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4()}{ext}")

    async with aiofiles.open(dest, "wb") as f:
        content = await file.read()
        await f.write(content)

    col = get_sources_col()
    source_doc = {
        "_id": ObjectId(),
        "type": "file",
        "label": label or file.filename,
        "originalName": file.filename,
        "filePath": dest,
        "mimeType": file.content_type,
        "status": "pending",
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }
    await col.insert_one(source_doc)

    try:
        updates = await ingest_source(source_doc=source_doc)
        updates["updatedAt"] = datetime.now(timezone.utc)
        await col.update_one({"_id": source_doc["_id"]}, {"$set": updates})
    except Exception as e:
        await col.update_one(
            {"_id": source_doc["_id"]},
            {"$set": {"status": "error", "errorMessage": str(e)}}
        )
        raise HTTPException(500, f"Ingestion failed: {e}")

    return {
        "sourceId": str(source_doc["_id"]),
        "label": source_doc["label"],
        "status": updates.get("status"),
        "totalChunks": updates.get("totalChunks", 0),
    }
