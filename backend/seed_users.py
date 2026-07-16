import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.user import User, Role
from app.core.security import get_password_hash

def seed_users():
    db = SessionLocal()
    try:
        # Check if users already exist
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        analyst = db.query(User).filter(User.email == "analyst@example.com").first()

        if not admin:
            admin = User(
                name="System Admin",
                email="admin@example.com",
                password_hash=get_password_hash("password123"),
                role=Role.Admin
            )
            db.add(admin)
            print("Admin user created (admin@example.com / password123).")
        else:
            print("Admin user already exists.")

        if not analyst:
            analyst = User(
                name="Test Analyst",
                email="analyst@example.com",
                password_hash=get_password_hash("password123"),
                role=Role.Analyst
            )
            db.add(analyst)
            print("Analyst user created (analyst@example.com / password123).")
        else:
            print("Analyst user already exists.")

        db.commit()
    except Exception as e:
        print(f"Error seeding users: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Seeding database...")
    seed_users()
    print("Done.")
