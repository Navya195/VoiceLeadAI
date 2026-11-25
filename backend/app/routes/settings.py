from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pathlib import Path
import os
from app.config import settings
from app.ai_service import ai_service

router = APIRouter(prefix="/api/settings", tags=["Settings & Model Configuration"])

class ApiKeyUpdate(BaseModel):
    gemini_api_key: str = Field(..., min_length=10, description="Google Gemini API Key")

@router.get("/status")
def get_settings_status():
    has_key = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 10)
    key_preview = f"{settings.GEMINI_API_KEY[:6]}...{settings.GEMINI_API_KEY[-4:]}" if has_key else None
    return {
        "gemini_active": bool(ai_service.client is not None),
        "has_key": has_key,
        "key_preview": key_preview,
        "model_name": "gemini-3.5-flash-lite" if ai_service.client else "Autonomous Educational Counselor Engine"
    }

@router.post("/gemini-key")
def update_gemini_key(req: ApiKeyUpdate):
    """
    Saves new Gemini API key to .env and immediately reinitializes the AI service client.
    """
    key = req.gemini_api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty")

    settings.GEMINI_API_KEY = key
    os.environ["GEMINI_API_KEY"] = key

    # Persist to .env file
    env_path = settings.BASE_DIR / ".env"
    try:
        lines = []
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        found = False
        new_lines = []
        for line in lines:
            if line.startswith("GEMINI_API_KEY="):
                new_lines.append(f"GEMINI_API_KEY={key}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.insert(0, f"GEMINI_API_KEY={key}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        # Re-initialize Gemini client
        ai_service._init_gemini()

        return {
            "success": True,
            "message": "Gemini API key successfully saved and activated! AI model is now live.",
            "gemini_active": ai_service.client is not None,
            "model": "gemini-2.5-flash"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save API key: {e}")
