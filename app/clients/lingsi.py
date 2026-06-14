"""Client for Lingsi analytics API."""

import requests

from app.core.config import settings


class LingsiClient:
    base_url = "https://lingsiai.cn/api/v1"
    api_key = "lingsi-analytics-secure-key-2026"

    def dashboard_overview(self, time_range: str):
        response = requests.get(
            f"{self.base_url}/analytics/dashboard-overview",
            headers={"X-API-Key": self.api_key, "Content-Type": "application/json"},
            params={"time_range": time_range},
            timeout=settings.AI_DETECTOR_TIMEOUT,
        )
        return response
