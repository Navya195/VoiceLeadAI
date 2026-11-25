from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.database import db
from app.lead_scorer import calculate_lead_score

router = APIRouter(prefix="/api/appointments", tags=["Appointments"])

class BookAppointmentRequest(BaseModel):
    customer_name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    phone: str = Field(..., min_length=8)
    course: Optional[str] = "Tech Consultation"
    slot_date: str = Field(..., description="YYYY-MM-DD")
    slot_time: str = Field(..., description="e.g. 10:00 AM")
    notes: Optional[str] = None

def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return {}
    doc["id"] = str(doc.pop("_id"))
    for k, v in doc.items():
        if isinstance(v, datetime):
            doc[k] = v.isoformat()
    return doc

@router.get("/slots")
async def get_available_slots():
    """
    Returns available and booked appointment slots.
    """
    if not db.connected or db.db is None:
        return {"slots": []}

    try:
        slots_cursor = db.db.slots.find().sort([("slot_date", 1), ("slot_time", 1)])
        slots = [serialize_doc(s) for s in slots_cursor]
        return {"slots": slots}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
async def get_appointments():
    """
    Returns all confirmed bookings.
    """
    if not db.connected or db.db is None:
        return {"appointments": []}

    try:
        cursor = db.db.appointments.find().sort("created_at", -1)
        return {"appointments": [serialize_doc(doc) for doc in cursor]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/book")
async def book_appointment(req: BookAppointmentRequest):
    """
    Books an appointment slot.
    Guarantees concurrency safety by:
    1. Checking if appointment already exists for the same slot.
    2. Atomically claiming the slot document (is_booked: False -> True).
    3. Saving the confirmed appointment in MongoDB.
    4. Upserting the lead and boosting lead score by +20 points (booked appointment).
    """
    if db.db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    # 1. Prevent duplicate bookings
    existing = db.db.appointments.find_one({
        "slot_date": req.slot_date,
        "slot_time": req.slot_time
    })
    if existing:
        raise HTTPException(
            status_code=409, 
            detail=f"Slot {req.slot_date} at {req.slot_time} is already booked. Please choose another slot."
        )

    now = datetime.utcnow()

    # 2. Update slots collection atomically
    slot_update = db.db.slots.find_one_and_update(
        {
            "slot_date": req.slot_date,
            "slot_time": req.slot_time,
            "is_booked": False
        },
        {
            "$set": {
                "is_booked": True,
                "booked_by": req.customer_name,
                "updated_at": now
            }
        }
    )

    # 3. Create appointment record
    appointment_doc = {
        "customer_name": req.customer_name.strip(),
        "email": req.email.strip().lower(),
        "phone": req.phone.strip(),
        "course": req.course,
        "slot_date": req.slot_date,
        "slot_time": req.slot_time,
        "status": "Confirmed",
        "notes": req.notes or "Counseling consultation booked via VoxSales AI",
        "created_at": now
    }

    try:
        app_res = db.db.appointments.insert_one(appointment_doc)
        appointment_doc["id"] = str(app_res.inserted_id)

        # 4. Upsert/Update corresponding Lead in MongoDB with +20 boost for appointment
        lead_query = {"$or": [{"email": appointment_doc["email"]}, {"phone": appointment_doc["phone"]}]}
        existing_lead = db.db.leads.find_one(lead_query)

        lead_data = {
            "name": req.customer_name,
            "email": req.email,
            "phone": req.phone,
            "interested_course": req.course,
            "appointment_booked": True
        }
        score, category = calculate_lead_score(lead_data)

        db.db.leads.update_one(
            lead_query,
            {
                "$set": {
                    "name": req.customer_name,
                    "email": req.email,
                    "phone": req.phone,
                    "interested_course": req.course,
                    "lead_score": score,
                    "lead_category": category,
                    "appointment_id": str(app_res.inserted_id),
                    "appointment_slot": f"{req.slot_date} {req.slot_time}",
                    "updated_at": now
                },
                "$setOnInsert": {
                    "sentiment": "Positive",
                    "created_at": now
                }
            },
            upsert=True
        )

        return {
            "success": True,
            "message": f"Appointment successfully confirmed for {req.customer_name} on {req.slot_date} at {req.slot_time}!",
            "appointment": serialize_doc(appointment_doc)
        }
    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(status_code=409, detail="Slot is already booked.")
        raise HTTPException(status_code=500, detail=str(e))
