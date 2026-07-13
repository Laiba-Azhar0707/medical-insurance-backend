from database import SessionLocal
from models import User
from auth import hash_password

db = SessionLocal()

users = [
    {"name": "Test User", "email": "user@test.com", "password": "password123", "role": "user"},
    {"name": "Admin User", "email": "admin@test.com", "password": "adminpass123", "role": "admin"},
]

for u in users:
    existing = db.query(User).filter(User.email == u["email"]).first()
    if not existing:
        new_user = User(
            name=u["name"],
            email=u["email"],
            password_hash=hash_password(u["password"]),
            role=u["role"],
        )
        db.add(new_user)

db.commit()
db.close()
print("Seed users created.")