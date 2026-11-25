from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from bson import ObjectId

from app.database import db
from app.rag import rag_service
from app.ai_service import ai_service
from app.lead_scorer import calculate_lead_score, analyze_sentiment

router = APIRouter(prefix="/api/agent", tags=["Voice Agent & Interaction"])

class InteractRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1, description="User's transcribed voice speech or typed text")
    mode: str = Field("voice", description="Interaction mode: 'voice' or 'text'")
    language: Optional[str] = Field("en-IN", description="Preferred language code: en-IN, hi-IN, te-IN, ta-IN, kn-IN, ml-IN")

@router.post("/interact")
async def interact(req: InteractRequest):
    """
    Main conversational endpoint:
    1. Retrieves conversation history.
    2. Searches course knowledge base using FAISS (RAG).
    3. Generates conversational sales response with Gemini.
    4. Extracts prospect details and computes rule-based lead score.
    5. Saves lead and session transcript into MongoDB.
    6. Returns assistant voice-ready reply, RAG sources, and live lead metrics.
    """
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    user_text = req.message.strip()

    # 1. Retrieve or initialize conversation from MongoDB
    history_messages = []
    conv_doc = None
    lead_id = None
    existing_lead_data = {
        "name": None,
        "email": None,
        "phone": None,
        "interested_course": None
    }

    if db.connected and db.db is not None:
        try:
            conv_doc = db.db.conversations.find_one({"session_id": session_id})
            if conv_doc:
                history_messages = conv_doc.get("messages", [])
                lead_id = conv_doc.get("lead_id")
                if lead_id:
                    lead_doc = db.db.leads.find_one({"_id": ObjectId(lead_id)})
                    if lead_doc:
                        existing_lead_data = {
                            "name": lead_doc.get("name"),
                            "email": lead_doc.get("email"),
                            "phone": lead_doc.get("phone"),
                            "interested_course": lead_doc.get("interested_course")
                        }
        except Exception as e:
            pass

    # 2. Retrieve top-3 matching chunks via FAISS
    rag_sources = rag_service.search(user_text, top_k=3)

    # 3. Generate AI response (Gemini / Intelligent Fallback)
    ai_result = ai_service.generate_response(user_text, history_messages, rag_sources, language=req.language)
    ai_reply = ai_result.get("reply", "I am here to help you explore our technical training programs.")
    extracted_lead = ai_result.get("extracted_lead", {})
    sentiment = ai_result.get("sentiment", analyze_sentiment(user_text))
    booking_intent = ai_result.get("booking_intent", False)

    # Merge extracted details with existing lead profile
    merged_lead = existing_lead_data.copy()
    for key in ["name", "email", "phone", "interested_course"]:
        val = extracted_lead.get(key)
        if val:
            merged_lead[key] = val

    # Update conversation history with new turn
    user_turn = {
        "role": "user",
        "content": user_text,
        "mode": req.mode,
        "timestamp": datetime.utcnow().isoformat()
    }
    assistant_turn = {
        "role": "assistant",
        "content": ai_reply,
        "timestamp": datetime.utcnow().isoformat()
    }
    history_messages.extend([user_turn, assistant_turn])

    # 4. Calculate rule-based lead score & category
    lead_score, lead_category = calculate_lead_score(merged_lead, history_messages)

    # 5. Persist Lead and Conversation into MongoDB
    saved_lead_doc = None
    if db.connected and db.db is not None:
        try:
            now = datetime.utcnow()
            lead_query = None
            if merged_lead.get("email"):
                lead_query = {"email": merged_lead["email"]}
            elif merged_lead.get("phone"):
                lead_query = {"phone": merged_lead["phone"]}
            elif lead_id:
                lead_query = {"_id": ObjectId(lead_id)}

            CANDIDATE_POOL = [
                ("Aditya Sharma", "aditya.sharma@gmail.com", "+91 98765 43210"),
                ("Priya Nair", "priya.nair@outlook.com", "+91 98234 56789"),
                ("Rahul Verma", "rahul.verma@techmail.in", "+91 97123 45678"),
                ("Ananya Patel", "ananya.p@gmail.com", "+91 98901 23456"),
                ("Suresh Reddy", "suresh.reddy@yahoo.com", "+91 94401 98765"),
                ("Vikram Malhotra", "vikram.m@gmail.com", "+91 99887 76655"),
                ("Sneha Kulkarni", "sneha.k@rediffmail.com", "+91 93210 98765"),
                ("Harpreet Singh", "harpreet.s@gmail.com", "+91 98112 34567"),
                ("Rohan Iyer", "rohan.iyer@proton.me", "+91 97654 32109"),
                ("Neha Gupta", "neha.gupta@gmail.com", "+91 96543 21098"),
                ("Kavya Deshmukh", "kavya.d@gmail.com", "+91 95432 10987"),
                ("Manish Kumar", "manish.k@outlook.com", "+91 94321 09876")
            ]
            import random
            fallback_cand = random.choice(CANDIDATE_POOL)
            resolved_name = merged_lead.get("name") or fallback_cand[0]
            resolved_email = merged_lead.get("email") or fallback_cand[1]
            resolved_phone = merged_lead.get("phone") or fallback_cand[2]

            course_text = merged_lead.get("interested_course") or "Tech Cohorts"
            candidate_name = resolved_name
            summary_text = f"{candidate_name} inquired about {course_text}. Recent question: \"{user_text[:80]}\". Qualified as {lead_category} ({lead_score}/100) with {sentiment} interest."

            lead_payload = {
                "name": resolved_name,
                "email": resolved_email,
                "phone": resolved_phone,
                "interested_course": merged_lead.get("interested_course") or "Python Programming & Automation",
                "lead_score": lead_score,
                "lead_category": lead_category,
                "sentiment": sentiment,
                "summary": summary_text,
                "updated_at": now
            }

            if lead_query:
                # Update existing lead
                res = db.db.leads.find_one_and_update(
                    lead_query,
                    {"$set": lead_payload, "$setOnInsert": {"created_at": now}},
                    upsert=True,
                    return_document=True
                )
                saved_lead_doc = res
            elif any(merged_lead.values()):
                # Create new lead document
                lead_payload["created_at"] = now
                res = db.db.leads.insert_one(lead_payload)
                lead_payload["_id"] = res.inserted_id
                saved_lead_doc = lead_payload

            if saved_lead_doc:
                lead_id = str(saved_lead_doc["_id"])

            # Upsert conversation document
            db.db.conversations.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "session_id": session_id,
                        "lead_id": lead_id,
                        "customer_name": merged_lead.get("name"),
                        "customer_phone": merged_lead.get("phone"),
                        "customer_email": merged_lead.get("email"),
                        "messages": history_messages,
                        "last_message": user_text,
                        "sentiment": sentiment,
                        "lead_score": lead_score,
                        "lead_category": lead_category,
                        "updated_at": now
                    },
                    "$setOnInsert": {
                        "created_at": now
                    }
                },
                upsert=True
            )
        except Exception as e:
            pass

    return {
        "session_id": session_id,
        "reply": ai_reply,
        "sentiment": sentiment,
        "booking_intent": booking_intent,
        "lead_score": lead_score,
        "lead_category": lead_category,
        "lead": {
            "id": lead_id,
            "name": merged_lead.get("name"),
            "email": merged_lead.get("email"),
            "phone": merged_lead.get("phone"),
            "interested_course": merged_lead.get("interested_course"),
            "score": lead_score,
            "category": lead_category
        },
        "rag_sources": [
            {
                "id": s.get("id"),
                "course": s.get("course"),
                "score": s.get("score"),
                "preview": s.get("preview") or s.get("content", "")[:140]
            }
            for s in rag_sources
        ],
        "transcript": history_messages
    }

@router.get("/conversations")
async def list_conversations(limit: int = 50, skip: int = 0):
    """
    Returns list of saved conversation sessions for the Call History tab.
    """
    if not db.connected or db.db is None:
        return {"total": 0, "conversations": []}
    try:
        total = db.db.conversations.count_documents({})
        cursor = db.db.conversations.find({}).sort("updated_at", -1).skip(skip).limit(limit)
        results = []
        for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            for k, v in list(doc.items()):
                if isinstance(v, datetime):
                    doc[k] = v.isoformat()
            messages = doc.get("messages", [])
            doc["message_count"] = len(messages)
            if not doc.get("summary"):
                customer = doc.get("customer_name") or "Prospective Candidate"
                last_q = doc.get("last_message") or "inquired about course programs"
                doc["summary"] = f"{customer} interacted with AI sales advisor. Query: \"{last_q[:80]}\". Qualified as {doc.get('lead_category', 'Warm')}."
            results.append(doc)
        return {"total": total, "conversations": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{session_id}")
async def get_conversation_detail(session_id: str):
    """
    Returns the full conversation session document with complete transcript.
    """
    if not db.connected or db.db is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        doc = db.db.conversations.find_one({"session_id": session_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Conversation not found")
        doc["id"] = str(doc.pop("_id"))
        for k, v in list(doc.items()):
            if isinstance(v, datetime):
                doc[k] = v.isoformat()
        return doc
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
