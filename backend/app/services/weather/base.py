from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class WeatherProvider(ABC):
    @abstractmethod
    def get_weather(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime | None,
    ) -> dict[str, Any]:
        """Return confirmed weather data without creating disruptions."""
