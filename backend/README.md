# BuildSync Backend

FastAPI foundation for the BuildSync application.

## Setup

From this directory, install the dependencies:

```powershell
C:/Python314/python.exe -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`, set a real `DATABASE_URL` and a long random
`JWT_SECRET_KEY`, and adjust the other values for the local environment.

### YOLO model configuration

`YOLO_MODEL_PATH` accepts any compatible Ultralytics model path, preferably
relative to the backend working directory:

```text
YOLO_MODEL_PATH=models/yolo11n.pt
YOLO_CLASSES=
```

The current `yolo11n.pt` model is a COCO pretrained model and is not a
construction-specific detector. Its classes are discovered from the loaded
model at runtime. `YOLO_CLASSES` may filter those discovered classes, but an
unknown class produces a controlled configuration error. A future
construction-specific model can be configured without changing the pipeline:

```text
YOLO_MODEL_PATH=models/construction_yolo.pt
```

Construction detection is not claimed until that trained model is supplied.

## PostgreSQL

The backend reads `DATABASE_URL` from `backend/.env`; it never exposes that
value to the frontend. For Supabase, use the connection string supplied by
the project dashboard with the SQLAlchemy psycopg driver, for example:

```text
DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:5432/<database>
```

The password and host must remain only in `backend/.env`. Do not commit that
file or copy SQLite/demo data into Supabase automatically.

Initialize the schema without dropping existing data:

```powershell
C:/Python314/python.exe scripts/init_db.py
```

Before starting the API, verify the configured provider without printing the
connection string:

```powershell
C:/Python314/python.exe -c "from sqlalchemy import text; from app.core.database import engine; assert engine is not None; print(engine.dialect.name); print(engine.connect().execute(text('SELECT 1')).scalar_one())"
```

For a fresh Supabase database, `scripts/init_db.py` imports all SQLAlchemy
models and creates the complete schema. Run it before starting the API. This
project does not use Alembic; `ensure_schema()` performs only additive
compatibility updates and preserves existing rows. The API does not run schema
migrations during module import, so a slow or unavailable database cannot block
the web server from starting.

Seed development-only users for each supported role:

```powershell
C:/Python314/python.exe scripts/seed_demo_users.py
```

Set a development/staging-only `DEMO_PASSWORD` value in Render or a local `.env`
file before running the script. Existing demo
users are updated with the configured password, while missing users are created.

For Gemini, use a valid model available to the Gemini API, such as
`gemini-2.5-flash`, for both `GEMINI_MODEL` and `GEMINI_VISION_MODEL`. The API key
must be supplied through `GEMINI_API_KEY`; never commit it. If Gemini is
temporarily unavailable, the Project Assistant returns a deterministic answer
from the authorized database context instead of fabricating an answer or
failing with a generic provider message.

## Run

```powershell
C:/Python314/python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8000`, with versioned endpoints under
`/api/`.

## Project planning (Step 3)

All planning endpoints require a bearer token obtained from `/api/auth/login`.
Every authenticated role can read planning data. Creating, changing, and
deleting planning data requires `PROJECT_MANAGER` or `ADMIN`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST`/`GET` | `/api/projects` | Create or list projects |
| `GET`/`PUT`/`DELETE` | `/api/projects/{project_id}` | Read or manage a project |
| `GET` | `/api/projects/{project_id}/plan-summary` | Project plan summary |
| `GET`/`POST` | `/api/projects/{project_id}/wbs` | List or add work breakdown items |
| `GET`/`PUT`/`DELETE` | `/api/wbs/{wbs_id}` | Manage a WBS item |
| `GET`/`POST` | `/api/projects/{project_id}/boq` | List or add bill-of-quantities items |
| `GET`/`PUT`/`DELETE` | `/api/boq/{boq_id}` | Manage a BOQ item |
| `GET`/`POST` | `/api/projects/{project_id}/schedule` | List or add schedule activities |
| `GET`/`PUT`/`DELETE` | `/api/schedule/{activity_id}` | Manage an activity |
| `GET`/`POST` | `/api/schedule/{activity_id}/planned-progress` | List or add planned progress |

`Project`, `WBS`, `BOQItem`, `ScheduleActivity`, and `PlannedProgress` are
created by `scripts/init_db.py` using `create_all`, which preserves existing
tables and data. Request validation rejects negative amounts/quantities,
percentages outside 0–100, invalid date ranges, and cross-project references.

## Field activity and assignment (Step 4)

Field activities are persisted in `activities` and assignments in
`activity_assignments`; initializing the database uses `create_all` and
does not reset existing planning or user data. Activities follow the strictly
ordered lifecycle `NOT_STARTED -> STARTED -> IN_PROGRESS -> SUBMITTED ->
AI_ANALYZED -> VERIFIED -> COMPLETED`. Step 4 exposes the first three
field-user transitions; verification and AI integrations can advance the
later states in a subsequent step.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST`/`GET` | `/api/projects/{project_id}/activities` | Create or list field activities |
| `GET`/`PUT`/`DELETE` | `/api/activities/{activity_id}` | Read or manage an activity |
| `POST`/`GET` | `/api/activities/{activity_id}/assignments` | Assign or list assigned users |
| `DELETE` | `/api/activities/{activity_id}/assignments/{assignment_id}` | Remove an assignment |
| `PATCH` | `/api/activities/{activity_id}/progress` | Record field progress (0–100) |
| `POST` | `/api/activities/{activity_id}/start` | Move an assigned activity to `STARTED` |
| `POST` | `/api/activities/{activity_id}/submit` | Move `IN_PROGRESS` to `SUBMITTED` |
| `GET` | `/api/users/me/activities` | List assigned work with status, project, date, and zone filters |
| `GET` | `/api/projects/{project_id}/activity-summary` | Summarize field activity status and progress |

Project managers and administrators manage activities. Site engineers manage
assignments. Assigned field users (workers, foremen, field engineers, and site
engineers) can start, update, and submit their own activities; managers and
administrators retain broad access. Schedule, WBS, and BOQ references must
belong to the activity's project.

Example project request:

```json
{
  "project_code": "ML6-C3",
  "name": "Metro Line 6 - Package C3",
  "description": "North Viaduct Construction",
  "client": "Metro Authority",
  "location": "North Corridor",
  "package_name": "Package C3",
  "start_date": "2026-01-01",
  "planned_end_date": "2027-12-31",
  "status": "PLANNING"
}
```

### Validation

From `backend`, run the import and syntax check with:

```powershell
$env:PYTHONPATH = "."
C:/Python314/python.exe -m compileall -q app
C:/Python314/python.exe -c "from app.main import app; print(len(app.routes))"
```

## Health check

```powershell
Invoke-RestMethod http://localhost:8000/api/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "BuildSync Backend"
}
```

The `models` package is reserved for SQLAlchemy models, while `schemas`,
`routes`, and `services` provide extension points for future authentication,
projects, activities, evidence, AI, predictions, and notifications.
