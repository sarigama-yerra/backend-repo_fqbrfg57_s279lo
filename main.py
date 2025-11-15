import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
from database import create_document, get_documents, db

app = FastAPI(title="SaaS Image Generation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Text prompt to generate the image")
    style: Optional[str] = Field(None, description="Optional artistic style")
    size: Optional[str] = Field("square", description="square | portrait | landscape")

class GenerationResponse(BaseModel):
    id: str
    prompt: str
    style: Optional[str]
    size: Optional[str]
    image_url: str
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: datetime

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# --- Image Generation Demo Endpoints ---

# This demo uses a placeholder image service to simulate generation.
# Replace the image_url creation logic with a real provider if desired.

def size_to_dims(size: Optional[str]) -> tuple[int, int]:
    if size == "portrait":
        return (768, 1024)
    if size == "landscape":
        return (1024, 640)
    return (1024, 1024)

@app.post("/api/generate", response_model=GenerationResponse)
def generate_image(req: GenerateRequest):
    if not req.prompt or len(req.prompt.strip()) < 3:
        raise HTTPException(status_code=400, detail="Prompt is too short")

    width, height = size_to_dims(req.size)

    # Simulate image generation using picsum.photos while encoding prompt in query for traceability
    from urllib.parse import quote
    seed = quote((req.prompt + ("-" + req.style if req.style else "")).strip())
    image_url = f"https://picsum.photos/seed/{seed}/{width}/{height}"

    doc = {
        "prompt": req.prompt.strip(),
        "style": req.style.strip() if req.style else None,
        "size": req.size or "square",
        "image_url": image_url,
        "width": width,
        "height": height,
    }

    try:
        inserted_id = create_document("generation", doc)
    except Exception as e:
        # If DB is unavailable, still return a result but without persistence
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return GenerationResponse(
        id=inserted_id,
        prompt=doc["prompt"],
        style=doc["style"],
        size=doc["size"],
        image_url=doc["image_url"],
        width=doc["width"],
        height=doc["height"],
        created_at=datetime.now(timezone.utc),
    )

@app.get("/api/generations", response_model=List[GenerationResponse])
def list_generations(limit: int = 20):
    try:
        docs = get_documents("generation", {}, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    results: List[GenerationResponse] = []
    for d in docs:
        results.append(GenerationResponse(
            id=str(d.get("_id")),
            prompt=d.get("prompt"),
            style=d.get("style"),
            size=d.get("size"),
            image_url=d.get("image_url"),
            width=d.get("width"),
            height=d.get("height"),
            created_at=d.get("created_at", datetime.now(timezone.utc)),
        ))
    return results

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
