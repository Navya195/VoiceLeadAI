import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
# pyrefly: ignore[missing-import]
import pymongo
# pyrefly: ignore[missing-import]
from pymongo import MongoClient
from app.config import settings

logger = logging.getLogger("voiceleadai.database")


class _InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class _UpdateResult:
    def __init__(self, matched_count, modified_count):
        self.matched_count = matched_count
        self.modified_count = modified_count


class _DeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


class _LocalCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            for k, d in reversed(key_or_list):
                self._docs.sort(key=lambda x: str(x.get(k, "")), reverse=(d == -1))
        else:
            self._docs.sort(key=lambda x: str(x.get(key_or_list, "")), reverse=(direction == -1))
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def __iter__(self):
        return iter(self._docs)


class LocalCollection:
    """MongoDB-compatible collection backed by a local JSON file."""

    def __init__(self, name: str, store: dict, save_fn):
        self.name = name
        self._store = store
        self._save = save_fn

    def _docs(self) -> list:
        return self._store.setdefault(self.name, [])

    @staticmethod
    def _matches(doc: dict, query: dict) -> bool:
        if not query:
            return True
        for k, v in query.items():
            if k == "$or":
                if not any(LocalCollection._matches(doc, sub) for sub in v):
                    return False
                continue
            val = doc.get(k)
            if isinstance(v, dict):
                if "$regex" in v:
                    import re
                    flags = re.IGNORECASE if v.get("$options", "") == "i" else 0
                    if not re.search(v["$regex"], str(val or ""), flags):
                        return False
                elif "$gte" in v:
                    cmp_val = val.isoformat() if isinstance(val, datetime) else val
                    cmp_target = v["$gte"].isoformat() if isinstance(v["$gte"], datetime) else v["$gte"]
                    if cmp_val is None or cmp_val < cmp_target:
                        return False
                elif "$lte" in v:
                    cmp_val = val.isoformat() if isinstance(val, datetime) else val
                    cmp_target = v["$lte"].isoformat() if isinstance(v["$lte"], datetime) else v["$lte"]
                    if cmp_val is None or cmp_val > cmp_target:
                        return False
            elif val != v:
                return False
        return True

    def create_index(self, *args, **kwargs):
        pass

    def count_documents(self, query=None) -> int:
        return sum(1 for d in self._docs() if self._matches(d, query or {}))

    def find(self, query=None, projection=None):
        matched = [dict(d) for d in self._docs() if self._matches(d, query or {})]
        return _LocalCursor(matched)

    def find_one(self, query=None, projection=None):
        for d in self._docs():
            if self._matches(d, query or {}):
                return dict(d)
        return None

    def insert_one(self, doc: dict):
        if "_id" not in doc:
            doc["_id"] = str(uuid.uuid4())
        new_doc = dict(doc)
        self._docs().append(new_doc)
        self._save()
        return _InsertResult(new_doc["_id"])

    def insert_many(self, docs: list):
        ids = []
        for doc in docs:
            if "_id" not in doc:
                doc["_id"] = str(uuid.uuid4())
            self._docs().append(dict(doc))
            ids.append(doc["_id"])
        self._save()
        return ids

    def update_one(self, query: dict, update: dict, upsert: bool = False):
        for d in self._docs():
            if self._matches(d, query):
                if "$set" in update:
                    d.update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        d[k] = (d.get(k) or 0) + v
                if "$push" in update:
                    for k, v in update["$push"].items():
                        d.setdefault(k, []).append(v)
                self._save()
                return _UpdateResult(1, 1)
        if upsert:
            new_doc = dict(query)
            if "$setOnInsert" in update:
                new_doc.update(update["$setOnInsert"])
            if "$set" in update:
                new_doc.update(update["$set"])
            if "_id" not in new_doc:
                new_doc["_id"] = str(uuid.uuid4())
            self._docs().append(new_doc)
            self._save()
            return _UpdateResult(0, 1)
        return _UpdateResult(0, 0)

    def find_one_and_update(self, query: dict, update: dict, return_document=None, upsert: bool = False):
        for d in self._docs():
            if self._matches(d, query):
                if "$set" in update:
                    d.update(update["$set"])
                self._save()
                return dict(d)
        if upsert:
            self.update_one(query, update, upsert=True)
            return self.find_one(query)
        return None

    def delete_one(self, query: dict):
        docs = self._docs()
        for i, d in enumerate(docs):
            if self._matches(d, query):
                docs.pop(i)
                self._save()
                return _DeleteResult(1)
        return _DeleteResult(0)

    def aggregate(self, pipeline: list) -> list:
        docs = [dict(d) for d in self._docs()]
        for stage in pipeline:
            if "$match" in stage:
                docs = [d for d in docs if self._matches(d, stage["$match"])]
            elif "$group" in stage:
                spec = stage["$group"]
                group_key = spec.get("_id")
                groups = {}
                for d in docs:
                    if isinstance(group_key, str) and group_key.startswith("$"):
                        k = d.get(group_key[1:])
                    else:
                        k = group_key
                    if k not in groups:
                        groups[k] = {"_id": k}
                        for field, expr in spec.items():
                            if field != "_id":
                                groups[k][field] = 0
                    for field, expr in spec.items():
                        if field == "_id":
                            continue
                        if isinstance(expr, dict) and "$sum" in expr:
                            inc = expr["$sum"]
                            if isinstance(inc, (int, float)):
                                groups[k][field] += inc
                            elif isinstance(inc, str) and inc.startswith("$"):
                                groups[k][field] += d.get(inc[1:], 0) or 0
                docs = list(groups.values())
            elif "$sort" in stage:
                for k, direction in reversed(list(stage["$sort"].items())):
                    docs.sort(key=lambda x: str(x.get(k, "")), reverse=(direction == -1))
            elif "$limit" in stage:
                docs = docs[:stage["$limit"]]
        return docs


class LocalDB:
    """Persistent JSON-backed database mimicking PyMongo's Database interface."""

    def __init__(self, path: Path):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if self._path.exists():
            try:
                self._store = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._store = {}
        else:
            self._store = {}

    def _save(self):
        def _default(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)
        self._path.write_text(json.dumps(self._store, default=_default, indent=2), encoding="utf-8")

    def __getattr__(self, name: str) -> LocalCollection:
        return LocalCollection(name, self._store, self._save)


class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False

    def connect(self):
        try:
            self.client = MongoClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=3000,
                connectTimeoutMS=3000
            )
            # Verify connection
            self.client.admin.command('ping')
            self.db = self.client[settings.DATABASE_NAME]
            self.connected = True
            logger.info(f"Connected to MongoDB database: {settings.DATABASE_NAME}")
            self._ensure_indexes()
            self._seed_default_slots()
        except Exception as e:
            logger.warning(f"Failed to connect to MongoDB ({e}). Using persistent local JSON database.")
            self.db = LocalDB(settings.KB_FILE_PATH.parent / "local_db.json")
            self.connected = True
            self._seed_default_slots()
            self._seed_initial_data()

    def _seed_initial_data(self):
        if self.db is None:
            return
        try:
            now = datetime.utcnow()
            if self.db.leads.count_documents({}) == 0:
                self.db.leads.insert_many([
                    {
                        "name": "Aarav Sharma",
                        "email": "aarav.sharma@example.com",
                        "phone": "9876543210",
                        "interested_course": "AI, Machine Learning & LLM Specialist",
                        "score": 85,
                        "category": "Hot",
                        "sentiment": "Positive",
                        "source": "Voice Agent",
                        "created_at": (now - timedelta(hours=5)).isoformat(),
                        "updated_at": (now - timedelta(hours=5)).isoformat(),
                    },
                    {
                        "name": "Priya Nair",
                        "email": "priya.nair@example.com",
                        "phone": "9123456780",
                        "interested_course": "Full Stack Web Development (MERN + Next.js)",
                        "score": 72,
                        "category": "Hot",
                        "sentiment": "Positive",
                        "source": "Voice Agent",
                        "created_at": (now - timedelta(days=1)).isoformat(),
                        "updated_at": (now - timedelta(days=1)).isoformat(),
                    },
                    {
                        "name": "Rohan Verma",
                        "email": "rohan.v@example.com",
                        "phone": "9988776655",
                        "interested_course": "Java Enterprise & Microservices",
                        "score": 55,
                        "category": "Warm",
                        "sentiment": "Neutral",
                        "source": "Voice Agent",
                        "created_at": (now - timedelta(days=2)).isoformat(),
                        "updated_at": (now - timedelta(days=2)).isoformat(),
                    },
                ])
            if self.db.conversations.count_documents({}) == 0:
                self.db.conversations.insert_many([
                    {
                        "session_id": "demo_session_1",
                        "customer_name": "Aarav Sharma",
                        "interested_course": "AI, Machine Learning & LLM Specialist",
                        "sentiment": "Positive",
                        "messages": [
                            {"role": "user", "content": "Tell me about the AI & ML Specialist program.", "timestamp": "10:15 AM"},
                            {"role": "assistant", "content": "Our AI, Machine Learning & LLM Specialist track is a 20-week program (INR 4,999) covering PyTorch, Generative AI, Vector RAG with FAISS, and MLOps with 100% placement support.", "timestamp": "10:15 AM"},
                        ],
                        "created_at": (now - timedelta(hours=5)).isoformat(),
                        "updated_at": (now - timedelta(hours=5)).isoformat(),
                    },
                    {
                        "session_id": "demo_session_2",
                        "customer_name": "Priya Nair",
                        "interested_course": "Full Stack Web Development (MERN + Next.js)",
                        "sentiment": "Positive",
                        "messages": [
                            {"role": "user", "content": "What is the fee for Full Stack Web Development?", "timestamp": "04:30 PM"},
                            {"role": "assistant", "content": "The Full Stack Web Development program (MERN + Next.js 14) is INR 4,499 with our placement discount, or INR 750/month on no-cost EMI.", "timestamp": "04:30 PM"},
                        ],
                        "created_at": (now - timedelta(days=1)).isoformat(),
                        "updated_at": (now - timedelta(days=1)).isoformat(),
                    },
                ])
        except Exception as e:
            logger.error(f"Error seeding initial data: {e}")

    def _ensure_indexes(self):
        if not self.connected or self.db is None:
            return
        try:
            # Leads indexes
            self.db.leads.create_index([("email", pymongo.ASCENDING)])
            self.db.leads.create_index([("phone", pymongo.ASCENDING)])
            self.db.leads.create_index([("created_at", pymongo.DESCENDING)])
            
            # Appointments unique index to prevent duplicate bookings
            self.db.appointments.create_index(
                [("slot_date", pymongo.ASCENDING), ("slot_time", pymongo.ASCENDING)],
                unique=True
            )
            
            # Slots index
            self.db.slots.create_index(
                [("slot_date", pymongo.ASCENDING), ("slot_time", pymongo.ASCENDING)],
                unique=True
            )
            
            # Conversations index
            self.db.conversations.create_index([("session_id", pymongo.ASCENDING)], unique=True)
            self.db.conversations.create_index([("created_at", pymongo.DESCENDING)])
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

    def _seed_default_slots(self):
        """
        Seed available counseling appointment slots for the upcoming 7 days if none exist.
        """
        if not self.connected or self.db is None:
            return
        try:
            existing_count = self.db.slots.count_documents({})
            if existing_count > 0:
                return

            time_slots = [
                "10:00 AM",
                "11:30 AM",
                "02:00 PM",
                "03:30 PM",
                "05:00 PM",
                "06:30 PM"
            ]

            today = datetime.now().date()
            slots_to_insert = []
            
            # Seed next 5 days
            for day_offset in range(1, 6):
                slot_date = (today + timedelta(days=day_offset)).strftime("%Y-%m-%d")
                for slot_time in time_slots:
                    slots_to_insert.append({
                        "slot_date": slot_date,
                        "slot_time": slot_time,
                        "is_booked": False,
                        "booked_by": None,
                        "created_at": datetime.utcnow()
                    })

            if slots_to_insert:
                self.db.slots.insert_many(slots_to_insert, ordered=False)
                logger.info(f"Seeded {len(slots_to_insert)} appointment slots into MongoDB.")
        except Exception as e:
            logger.error(f"Error seeding default appointment slots: {e}")

db = Database()
