import os

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import User, UserRole


DEMO_PASSWORD = os.getenv("DEMO_PASSWORD")
DEMO_USERS = {
    "engineer@buildsync.demo": ("Demo Field Engineer", UserRole.FIELD_ENGINEER),
    "pm@buildsync.demo": ("Demo Project Manager", UserRole.PROJECT_MANAGER),
    "admin@buildsync.demo": ("Demo Admin", UserRole.ADMIN),
}


if not DEMO_PASSWORD:
    raise RuntimeError("DEMO_PASSWORD must be configured when SEED_DEMO_USERS=true")
if engine is None or SessionLocal is None:
    raise RuntimeError("DATABASE_URL must be set before seeding demo users")

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    for email, (full_name, role) in DEMO_USERS.items():
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            db.add(
                User(
                    full_name=full_name,
                    email=email,
                    hashed_password=hash_password(DEMO_PASSWORD),
                    role=role,
                )
            )
        else:
            user.hashed_password = hash_password(DEMO_PASSWORD)
    db.commit()
