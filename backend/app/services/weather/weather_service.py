from datetime import datetime
from typing import Any

from app.core.config import settings


def get_weather(
    latitude: float,
    longitude: float,
    start_time: datetime,
    end_time: datetime | None,
) -> dict[str, Any]:
    del latitude, longitude, start_time, end_time
    if not settings.weather_provider or not settings.weather_api_key:
        return {"status": "NOT_CONFIGURED"}
    return {"status": "NOT_CONFIGURED"}
