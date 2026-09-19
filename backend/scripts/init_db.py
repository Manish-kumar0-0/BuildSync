from sqlalchemy import text

from app.core.database import Base, engine, ensure_schema
from app.models import User


if engine is None:
    raise RuntimeError("DATABASE_URL must be set before initializing the database")

if engine.dialect.name == "postgresql":
    with engine.begin() as connection:
        enum_exists = connection.scalar(
            text("SELECT 1 FROM pg_type WHERE typname = 'construction_event_type'")
        )
        if enum_exists:
            for value in ("PLANNED", "ARCHIVED"):
                connection.execute(
                    text(
                        "ALTER TYPE project_status "
                        f"ADD VALUE IF NOT EXISTS '{value}'"
                    )
                )
            connection.execute(
                text(
                    "ALTER TYPE construction_event_type "
                    "ADD VALUE IF NOT EXISTS 'QUALITY_INSPECTION_FAILED'"
                )
            )
            connection.execute(
                text(
                    "ALTER TYPE construction_event_type "
                    "ADD VALUE IF NOT EXISTS 'QUALITY_DEFECT'"
                )
            )
        for enum_name, values in {
            "notification_type": (
                "RISK", "DELAY", "SAFETY", "QUALITY", "MATERIAL",
                "EQUIPMENT", "WORKFORCE", "EVIDENCE",
            ),
        }.items():
            if connection.scalar(
                text("SELECT 1 FROM pg_type WHERE typname = :name"),
                {"name": enum_name},
            ):
                for value in values:
                    connection.execute(
                        text(
                            f"ALTER TYPE {enum_name} "
                            f"ADD VALUE IF NOT EXISTS '{value}'"
                        )
                    )

Base.metadata.create_all(bind=engine)
ensure_schema()
print("Database tables initialized. Existing data was preserved.")
