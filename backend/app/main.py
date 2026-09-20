from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes.auth import router as auth_router
from app.routes.planning import router as planning_router
from app.routes.field_activity import router as field_activity_router
from app.routes.evidence import router as evidence_router
from app.routes.progress_assessment import router as progress_assessment_router
from app.routes.risk_prediction import router as risk_prediction_router
from app.routes.recovery import router as recovery_router
from app.routes.dashboard import router as dashboard_router
from app.routes.notifications import router as notifications_router
from app.routes.events import router as events_router
from app.routes.memory import router as memory_router
from app.routes.assistant import router as assistant_router
from app.routes.evidence_comparison import router as evidence_comparison_router
from app.routes.vision_comparison import router as vision_comparison_router
from app.routes.disruptions import router as disruptions_router
from app.routes.resources import router as resources_router
from app.routes.workforce import router as workforce_router
from app.routes.safety import router as safety_router
from app.routes.quality import router as quality_router
from app.routes.admin import router as admin_router
from app.routes.analytics import router as analytics_router
from app.routes.execution_intelligence import router as execution_intelligence_router
from app.routes.activity_measured_progress import router as activity_measured_progress_router
app = FastAPI(
    title="BuildSync Backend",
    version=settings.api_version,
    description="Backend API foundation for BuildSync.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(planning_router)
app.include_router(field_activity_router)
app.include_router(evidence_router)
app.include_router(progress_assessment_router)
app.include_router(risk_prediction_router)
app.include_router(recovery_router)
app.include_router(dashboard_router)
app.include_router(notifications_router)
app.include_router(events_router)
app.include_router(memory_router)
app.include_router(assistant_router)
app.include_router(evidence_comparison_router)
app.include_router(vision_comparison_router)
app.include_router(disruptions_router)
app.include_router(resources_router)
app.include_router(workforce_router)
app.include_router(safety_router)
app.include_router(quality_router)
app.include_router(admin_router)
app.include_router(analytics_router)
app.include_router(execution_intelligence_router)
app.include_router(activity_measured_progress_router)


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "BuildSync Backend"}


@app.get("/api/health/vision", tags=["health"])
def vision_health_check() -> dict[str, object]:
    checks: dict[str, object] = {}
    try:
        import cv2

        checks["opencv"] = {"status": "ok", "version": cv2.__version__}
    except Exception as exc:
        checks["opencv"] = {"status": "error", "error": type(exc).__name__}
    try:
        from app.services.vision.yolo_service import model_metadata

        metadata = model_metadata()
        checks["yolo"] = {
            "status": "ok",
            "model": metadata.filename,
            "classes": len(metadata.available_classes),
        }
    except Exception as exc:
        checks["yolo"] = {"status": "error", "error": type(exc).__name__}
    checks["gemini"] = {
        "status": "ok" if settings.gemini_api_key else "not_configured",
        "model": settings.gemini_vision_model or settings.gemini_model,
    }
    overall = "ok" if all(
        check.get("status") == "ok"
        for check in checks.values()
    ) else "degraded"
    return {"status": overall, "checks": checks}


@app.get("/health", tags=["health"])
def root_health_check() -> dict[str, str]:
    return {"status": "ok"}
