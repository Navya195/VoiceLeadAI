from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.database import db
from app.lead_scorer import calculate_lead_score

router = APIRouter(prefix="/api/leads", tags=["Lead Management"])

class LeadCreate(BaseModel):
    name: str = Field(..., min_length=1)
    email: Optional[str] = None
    phone: Optional[str] = None
    interested_course: Optional[str] = "General Tech Courses"
    summary: Optional[str] = None
    notes: Optional[str] = None

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    interested_course: Optional[str] = None
    lead_category: Optional[str] = None
    sentiment: Optional[str] = None
    summary: Optional[str] = None
    notes: Optional[str] = None

def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return {}
    doc["id"] = str(doc.pop("_id"))
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc

@router.get("")
async def get_leads(
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    category: Optional[str] = Query(None, description="Filter by Hot, Warm, Cold"),
    course: Optional[str] = Query(None, description="Filter by course"),
    limit: int = 50,
    skip: int = 0
):
    """
    Returns list of leads from MongoDB with optional search and category filters.
    """
    if not db.connected or db.db is None:
        return {"total": 0, "leads": []}

    query = {}
    if category and category.lower() != "all":
        query["lead_category"] = category.capitalize()

    if course and course.lower() != "all":
        query["interested_course"] = {"$regex": course, "$options": "i"}

    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"name": search_regex},
            {"email": search_regex},
            {"phone": search_regex},
            {"interested_course": search_regex}
        ]

    try:
        total = db.db.leads.count_documents(query)
        cursor = db.db.leads.find(query).sort("created_at", -1).skip(skip).limit(limit)
        leads = [serialize_doc(doc) for doc in cursor]
        return {
            "total": total,
            "leads": leads
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{lead_id}")
async def get_lead(lead_id: str):
    if not db.connected or db.db is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    try:
        doc = db.db.leads.find_one({"_id": ObjectId(lead_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Lead not found")
        return serialize_doc(doc)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid lead id: {e}")

@router.post("")
async def create_lead(lead: LeadCreate):
    if not db.connected or db.db is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    lead_dict = lead.model_dump()
    score, category = calculate_lead_score(lead_dict)
    now = datetime.utcnow()
    lead_dict.update({
        "lead_score": score,
        "lead_category": category,
        "sentiment": "Neutral",
        "created_at": now,
        "updated_at": now
    })

    res = db.db.leads.insert_one(lead_dict)
    lead_dict["id"] = str(res.inserted_id)
    return serialize_doc(lead_dict)

@router.put("/{lead_id}")
async def update_lead(lead_id: str, update: LeadUpdate):
    if not db.connected or db.db is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    fields = {k: v for k, v in update.model_dump().items() if v is not None}
    fields["updated_at"] = datetime.utcnow()

    # Recalculate score if core properties changed
    if any(k in fields for k in ["name", "email", "phone", "interested_course"]):
        current = db.db.leads.find_one({"_id": ObjectId(lead_id)})
        if current:
            merged = {**current, **fields}
            score, category = calculate_lead_score(merged)
            fields["lead_score"] = score
            if "lead_category" not in fields:
                fields["lead_category"] = category

    try:
        updated = db.db.leads.find_one_and_update(
            {"_id": ObjectId(lead_id)},
            {"$set": fields},
            return_document=True
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Lead not found")
        return serialize_doc(updated)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{lead_id}")
async def delete_lead(lead_id: str):
    if not db.connected or db.db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    try:
        res = db.db.leads.delete_one({"_id": ObjectId(lead_id)})
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Lead not found")
        return {"success": True, "message": "Lead deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
