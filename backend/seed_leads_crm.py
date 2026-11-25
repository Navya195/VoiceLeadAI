from app.database import db
from datetime import datetime, timedelta, timezone

db.connect()

now = datetime.now(timezone.utc)

seed_leads = [
    {
        'name': 'Suresh Gupta',
        'email': 'suresh.gupta@example.com',
        'phone': '+91 98112 44320',
        'interested_course': 'Python Programming & Automation',
        'lead_score': 32,
        'lead_category': 'Cold',
        'sentiment': 'Negative',
        'summary': 'Suresh Gupta in New Delhi has basic IT support background. Inquired about Python Automation course but hesitated on INR 3,499 fee, requesting higher scholarship discounts.',
        'created_at': now - timedelta(minutes=5),
        'updated_at': now - timedelta(minutes=5)
    },
    {
        'name': 'Vikram Malhotra',
        'email': 'vikram.m@example.com',
        'phone': '+91 98450 12890',
        'interested_course': 'Full Stack Web Development',
        'lead_score': 56,
        'lead_category': 'Warm',
        'sentiment': 'Neutral',
        'summary': 'Vikram Malhotra in Faridabad has 2 years manual QA experience. Wants Full Stack MERN bootcamp for placement transition, but evaluating weekend study hours.',
        'created_at': now - timedelta(minutes=10),
        'updated_at': now - timedelta(minutes=10)
    },
    {
        'name': 'Ananya Verma',
        'email': 'ananya.verma@example.com',
        'phone': '+91 99201 55678',
        'interested_course': 'AI, Machine Learning & LLM Specialist',
        'lead_score': 82,
        'lead_category': 'Hot',
        'sentiment': 'Positive',
        'summary': 'Ananya Verma from Noida seeking 20-week AI & ML Specialist program. Looking to build real LLM & GenAI apps with 1-on-1 mentorship. Very keen to enroll.',
        'created_at': now - timedelta(minutes=15),
        'updated_at': now - timedelta(minutes=15)
    },
    {
        'name': 'Harpreet Singh',
        'email': 'harpreet.singh@example.com',
        'phone': '+91 98765 33210',
        'interested_course': 'DSA & System Design Masterclass',
        'lead_score': 68,
        'lead_category': 'Warm',
        'sentiment': 'Neutral',
        'summary': 'Harpreet Singh in Ludhiana inquired about DSA & System Design Masterclass for upcoming tech company placement drives. Inquired about mock interview schedules.',
        'created_at': now - timedelta(minutes=20),
        'updated_at': now - timedelta(minutes=20)
    },
    {
        'name': 'Priya Nair',
        'email': 'priya.nair@example.com',
        'phone': '+91 98220 77114',
        'interested_course': 'Java Enterprise & Microservices',
        'lead_score': 92,
        'lead_category': 'Hot',
        'sentiment': 'Positive',
        'summary': 'Priya Nair in Gurugram seeks Java Enterprise & Microservices program for senior software engineer banking transitions. Booked 1-on-1 advisor slot.',
        'created_at': now - timedelta(minutes=25),
        'updated_at': now - timedelta(minutes=25)
    }
]

for l in seed_leads:
    db.db.leads.update_one({'email': l['email']}, {'$set': l}, upsert=True)

print('Updated 5 leads at top timestamps!')
