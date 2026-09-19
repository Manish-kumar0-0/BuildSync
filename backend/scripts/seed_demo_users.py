import os

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import User, UserRole


DEMO_PASSWORD = os.getenv("DEMO_PASSWORD")
DEMO_USERS = {
    "worker@buildsync.demo": ("Demo Worker", UserRole.WORKER),
    "foreman@buildsync.demo": ("Demo Foreman", UserRole.FOREMAN),
    "engineer@buildsync.demo": ("Demo Field Engineer", UserRole.FIELD_ENGINEER),
    "site@buildsync.demo": ("Demo Site Engineer", UserRole.SITE_ENGINEER),
    "safety@buildsync.demo": ("Demo Safety Officer", UserRole.SAFETY_OFFICER),
    "qa@buildsync.demo": ("Demo QA/QC Engineer", UserRole.QA_QC_ENGINEER),
    "material@buildsync.demo": ("Demo Material Manager", UserRole.MATERIAL_MANAGER),
    "driver@buildsync.demo": ("Demo Driver", UserRole.DRIVER),
    "equipment@buildsync.demo": ("Demo Equipment Manager", UserRole.EQUIPMENT_MANAGER),
    "pm@buildsync.demo": ("Demo Project Manager", UserRole.PROJECT_MANAGER),
    "admin@buildsync.demo": ("Demo Admin", UserRole.ADMIN),
}


if engine is None or SessionLocal is None:
    raise RuntimeError("DATABASE_URL must be set before seeding demo users")
if not DEMO_PASSWORD:
    raise RuntimeError("DEMO_PASSWORD must be set before seeding demo users")

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    for email, (full_name, role) in DEMO_USERS.items():
        if db.query(User).filter(User.email == email).first() is None:
            db.add(
                User(
                    full_name=full_name,
                    email=email,
                    hashed_password=hash_password(DEMO_PASSWORD),
                    role=role,
                )
            )
    db.commit()
