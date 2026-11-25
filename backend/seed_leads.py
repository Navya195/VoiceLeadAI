from pymongo import MongoClient

client = MongoClient('mongodb://127.0.0.1:27017/')
db = client['voxsales_db']

names_pool = [
    ('Aditya Sharma', 'aditya.sharma@gmail.com', '+91 98765 43210'),
    ('Priya Nair', 'priya.nair@outlook.com', '+91 98234 56789'),
    ('Rahul Verma', 'rahul.verma@techmail.in', '+91 97123 45678'),
    ('Ananya Patel', 'ananya.p@gmail.com', '+91 98901 23456'),
    ('Suresh Reddy', 'suresh.reddy@yahoo.com', '+91 94401 98765'),
    ('Vikram Malhotra', 'vikram.m@gmail.com', '+91 99887 76655'),
    ('Sneha Kulkarni', 'sneha.k@rediffmail.com', '+91 93210 98765'),
    ('Harpreet Singh', 'harpreet.s@gmail.com', '+91 98112 34567'),
    ('Rohan Iyer', 'rohan.iyer@proton.me', '+91 97654 32109'),
    ('Neha Gupta', 'neha.gupta@gmail.com', '+91 96543 21098'),
    ('Kavya Deshmukh', 'kavya.d@gmail.com', '+91 95432 10987'),
    ('Manish Kumar', 'manish.k@outlook.com', '+91 94321 09876')
]

leads = list(db.leads.find())
print(f'Total leads in DB: {len(leads)}')

updated_count = 0
for i, doc in enumerate(leads):
    current_name = doc.get('name')
    if not current_name or current_name == 'Anonymous Prospect':
        cand_name, cand_email, cand_phone = names_pool[i % len(names_pool)]
        db.leads.update_one(
            {'_id': doc['_id']},
            {'$set': {
                'name': cand_name,
                'email': cand_email,
                'phone': cand_phone,
                'summary': f"{cand_name} inquired about {doc.get('interested_course', 'Tech Cohorts')}. Qualified as {doc.get('lead_category', 'Cold')} ({doc.get('lead_score', 30)}/100) with {doc.get('sentiment', 'Positive')} interest."
            }}
        )
        updated_count += 1

print(f'Updated {updated_count} anonymous leads with realistic candidate profiles!')
