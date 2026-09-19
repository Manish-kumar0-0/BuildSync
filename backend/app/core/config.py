import os
from decimal import Decimal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

load_dotenv()


class Settings(BaseModel):
    app_name: str = Field(default="BuildSync Backend")
    api_version: str = Field(default="1.0.0")
    environment: str = Field(default="development")
    database_url: str | None = Field(default=None)
    jwt_secret_key: str = Field(default="development-only-change-me-32-byte-key")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)
    evidence_max_file_size_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    ai_provider: str = Field(default="gemini")
    gemini_api_key: str | None = Field(default=None)
    gemini_model: str = Field(default="gemini-2.5-flash")
    gemini_vision_model: str | None = Field(default="gemini-2.5-flash")
    yolo_model_path: str | None = Field(default=None)
    yolo_classes: list[str] = Field(default_factory=list)
    weather_provider: str | None = Field(default=None)
    weather_api_key: str | None = Field(default=None)
    fusion_high_confidence_threshold: int = Field(default=80, ge=0, le=100)
    fusion_medium_confidence_threshold: int = Field(default=60, ge=0, le=100)
    fusion_high_reported_weight: Decimal = Field(default=Decimal("0.4"), ge=0, le=1)
    fusion_high_ai_weight: Decimal = Field(default=Decimal("0.6"), ge=0, le=1)
    fusion_medium_reported_weight: Decimal = Field(default=Decimal("0.6"), ge=0, le=1)
    fusion_medium_ai_weight: Decimal = Field(default=Decimal("0.4"), ge=0, le=1)
    minor_variance_threshold: Decimal = Field(default=Decimal("-5"))
    significant_variance_threshold: Decimal = Field(default=Decimal("-15"))
    risk_low_max_score: int = Field(default=24, ge=0, le=100)
    risk_medium_max_score: int = Field(default=49, ge=0, le=100)
    risk_high_max_score: int = Field(default=74, ge=0, le=100)
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True
    password_reset_expire_minutes: int = 10

    @model_validator(mode="after")
    def validate_jwt_secret(self) -> "Settings":
        if self.environment != "development" and len(self.jwt_secret_key.encode()) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 bytes outside development")
        if self.environment != "development" and self.ai_provider == "mock":
            raise ValueError("AI_PROVIDER=mock is only allowed in development")
        return self

    @classmethod
    def from_environment(cls) -> "Settings":
        origins = os.getenv("CORS_ORIGINS")
        return cls(
            app_name=os.getenv("APP_NAME", "BuildSync Backend"),
            api_version=os.getenv("API_VERSION", "1.0.0"),
            environment=os.getenv("ENVIRONMENT", "development"),
            database_url=os.getenv("DATABASE_URL") or None,
            jwt_secret_key=os.getenv("JWT_SECRET_KEY", "development-only-change-me"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_token_expire_minutes=int(
                os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
            ),
            evidence_max_file_size_bytes=int(
                os.getenv("EVIDENCE_MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024))
            ),
            ai_provider=os.getenv("AI_PROVIDER", "gemini").lower(),
            gemini_api_key=os.getenv("GEMINI_API_KEY") or None,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            gemini_vision_model=os.getenv(
                "GEMINI_VISION_MODEL", "gemini-2.5-flash"
            ),
            yolo_model_path=os.getenv("YOLO_MODEL_PATH") or None,
            yolo_classes=[
                item.strip()
                for item in os.getenv("YOLO_CLASSES", "").split(",")
                if item.strip()
            ],
            weather_provider=os.getenv("WEATHER_PROVIDER") or None,
            weather_api_key=os.getenv("WEATHER_API_KEY") or None,
            fusion_high_confidence_threshold=int(
                os.getenv("FUSION_HIGH_CONFIDENCE_THRESHOLD", "80")
            ),
            fusion_medium_confidence_threshold=int(
                os.getenv("FUSION_MEDIUM_CONFIDENCE_THRESHOLD", "60")
            ),
            fusion_high_reported_weight=Decimal(
                os.getenv("FUSION_HIGH_REPORTED_WEIGHT", "0.4")
            ),
            fusion_high_ai_weight=Decimal(
                os.getenv("FUSION_HIGH_AI_WEIGHT", "0.6")
            ),
            fusion_medium_reported_weight=Decimal(
                os.getenv("FUSION_MEDIUM_REPORTED_WEIGHT", "0.6")
            ),
            fusion_medium_ai_weight=Decimal(
                os.getenv("FUSION_MEDIUM_AI_WEIGHT", "0.4")
            ),
            minor_variance_threshold=Decimal(
                os.getenv("MINOR_VARIANCE_THRESHOLD", "-5")
            ),
            significant_variance_threshold=Decimal(
                os.getenv("SIGNIFICANT_VARIANCE_THRESHOLD", "-15")
            ),
            risk_low_max_score=int(os.getenv("RISK_LOW_MAX_SCORE", "24")),
            risk_medium_max_score=int(os.getenv("RISK_MEDIUM_MAX_SCORE", "49")),
            risk_high_max_score=int(os.getenv("RISK_HIGH_MAX_SCORE", "74")),
            cors_origins=(
                [origin.strip() for origin in origins.split(",") if origin.strip()]
                if origins
                else cls.model_fields["cors_origins"].default_factory()
            ),
            smtp_host=os.getenv("SMTP_HOST") or None,
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME") or None,
            smtp_password=os.getenv("SMTP_PASSWORD") or None,
            smtp_from_email=os.getenv("SMTP_FROM_EMAIL") or None,
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            password_reset_expire_minutes=int(
                os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", "10")
            ),
        )


settings = Settings.from_environment()
