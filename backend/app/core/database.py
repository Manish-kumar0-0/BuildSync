from collections.abc import Generator

from fastapi import HTTPException, status
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs() -> dict[str, object]:
    if not settings.database_url:
        return {}
    if settings.database_url.startswith(("postgresql://", "postgresql+")):
        return {
            "connect_args": {"connect_timeout": 10},
            "pool_timeout": 15,
            "pool_recycle": 1800,
        }
    return {"pool_timeout": 15}


engine = (
    create_engine(settings.database_url, pool_pre_ping=True, **_engine_kwargs())
    if settings.database_url
    else None
)
SessionLocal = (
    sessionmaker(bind=engine, autoflush=False, autocommit=False)
    if engine
    else None
)


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured. Set DATABASE_URL first.",
        )

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    """Create new additive demo metrics structures without replacing existing data."""
    if engine is None:
        return
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        inspector = inspect(connection)
        columns = {column["name"] for column in inspector.get_columns("activities")}
        if "required_workers" not in columns:
            connection.execute(text("ALTER TABLE activities ADD COLUMN required_workers INTEGER"))
        columns = {column["name"] for column in inspector.get_columns("schedule_activities")}
        if "schedule_approval_status" not in columns:
            connection.execute(text(
                "ALTER TABLE schedule_activities ADD COLUMN schedule_approval_status VARCHAR(20) NOT NULL DEFAULT 'PENDING'"
            ))
        if "approved_by" not in columns:
            connection.execute(text("ALTER TABLE schedule_activities ADD COLUMN approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL"))
        if "approved_at" not in columns:
            connection.execute(text("ALTER TABLE schedule_activities ADD COLUMN approved_at DATETIME"))
        columns = {column["name"] for column in inspector.get_columns("progress_assessments")}
        if "measured_progress" not in columns:
            connection.execute(text(
                "ALTER TABLE progress_assessments ADD COLUMN measured_progress NUMERIC(5, 2)"
            ))
        if "comparison_id" not in columns:
            connection.execute(text(
                "ALTER TABLE progress_assessments ADD COLUMN comparison_id INTEGER "
                "REFERENCES evidence_comparison_analyses(id) ON DELETE SET NULL"
            ))
        columns = {column["name"] for column in inspector.get_columns("evidence_comparison_analyses")}
        if "absolute_progress_estimate" not in columns:
            connection.execute(text(
                "ALTER TABLE evidence_comparison_analyses ADD COLUMN "
                "absolute_progress_estimate NUMERIC(5, 2)"
            ))
        if "absolute_progress_confidence" not in columns:
            connection.execute(text(
                "ALTER TABLE evidence_comparison_analyses ADD COLUMN "
                "absolute_progress_confidence NUMERIC(4, 3)"
            ))
        columns = {column["name"] for column in inspector.get_columns("activity_risk_predictions")}
        if "comparison_id" not in columns:
            connection.execute(text(
                "ALTER TABLE activity_risk_predictions ADD COLUMN comparison_id INTEGER "
                "REFERENCES evidence_comparison_analyses(id) ON DELETE SET NULL"
            ))
        duplicate_groups = connection.execute(text(
            "SELECT activity_id, assessment_date "
            "FROM progress_assessments "
            "GROUP BY activity_id, assessment_date "
            "HAVING COUNT(*) > 1"
        )).fetchall()
        for activity_id, assessment_date in duplicate_groups:
            keep_id = connection.execute(text(
                "SELECT id "
                "FROM progress_assessments "
                "WHERE activity_id = :activity_id AND assessment_date = :assessment_date "
                "ORDER BY (comparison_id IS NOT NULL) DESC, id DESC "
                "LIMIT 1"
            ), {
                "activity_id": activity_id,
                "assessment_date": assessment_date,
            }).scalar_one()
            connection.execute(text(
                "DELETE FROM progress_assessments "
                "WHERE activity_id = :activity_id "
                "AND assessment_date = :assessment_date "
                "AND id != :keep_id"
            ), {
                "activity_id": activity_id,
                "assessment_date": assessment_date,
                "keep_id": keep_id,
            })
        index_names = {index["name"] for index in inspector.get_indexes("progress_assessments")}
        if "uq_progress_assessment_activity_date" not in index_names:
            connection.execute(text(
                "CREATE UNIQUE INDEX uq_progress_assessment_activity_date "
                "ON progress_assessments (activity_id, assessment_date)"
            ))
