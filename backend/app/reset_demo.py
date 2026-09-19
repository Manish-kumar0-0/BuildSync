"""Remove only the repeatable BuildSync SIH demo dataset."""

from sqlalchemy import delete, select

from app.core.database import SessionLocal, engine
from app.models import Project, ProjectUserAssignment, User

PROJECT_CODE = "ML6-C3"


def reset_demo() -> None:
    if engine is None or SessionLocal is None:
        raise RuntimeError("DATABASE_URL must be configured before resetting demo data")
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.project_code == PROJECT_CODE))
        if project is not None:
            db.delete(project)
        demo_users = db.scalars(select(User).where(User.email.like("%@buildsync.demo"))).all()
        for user in demo_users:
            db.delete(user)
        db.commit()
        print(f"Demo data reset: {PROJECT_CODE}")


if __name__ == "__main__":
    reset_demo()
