"""Simple client for Garmin Connect Personal API (official, launched Oct 2026).

User obtains API key at: https://connect.garmin.com/app/settings/personalApiToken
"""
import os
import requests
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any

BASE_URL = "https://personal.connectapi.garmin.com"
TOKEN_URL = f"{BASE_URL}/personalapitoken-service/personal-api/personal-api-key/token"


class GarminPersonalClient:
    def __init__(self, api_key: str):
        self.api_key = api_key.strip()
        self.access_token: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        self.session = requests.Session()

    def _ensure_token(self) -> str:
        if self.access_token and self.token_expires and datetime.utcnow() < self.token_expires - timedelta(minutes=5):
            return self.access_token
        headers = {"Authorization": f"ApiKey {self.api_key}", "Accept": "*/*"}
        resp = self.session.post(TOKEN_URL, headers=headers, timeout=30)
        resp.raise_for_status()
        # Official endpoint returns the bearer token as plain text (JWT), not JSON
        token_text = resp.text.strip()
        if not token_text:
            raise ValueError("Token endpoint returned empty response")
        self.access_token = token_text
        # Default to 24h; JWT exp claim can be parsed later if needed
        self.token_expires = datetime.utcnow() + timedelta(hours=23)
        return self.access_token

    def get(self, path: str, params: Optional[Dict] = None) -> Any:
        token = self._ensure_token()
        url = f"{BASE_URL}{path}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        resp = self.session.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        if not resp.content:
            return None
        return resp.json()

    # Convenience methods matching common needs
    def get_daily_hrv(self, d: date | str) -> Any:
        ds = d.isoformat() if isinstance(d, date) else d
        return self.get(f"/hrv-service/hrv/{ds}")

    def get_daily_sleep(self, d: date | str) -> Any:
        ds = d.isoformat() if isinstance(d, date) else d
        return self.get("/sleep-service/sleep/dailySleep", params={"date": ds})

    def get_daily_heart_rate(self, d: date | str) -> Any:
        ds = d.isoformat() if isinstance(d, date) else d
        return self.get("/wellness-service/wellness/dailyHeartRate", params={"date": ds})

    def get_daily_summaries(self, start: date | str, end: date | str) -> Any:
        return self.get(
            "/usersummary-service/v2/dailysummaries",
            params={"startDate": start if isinstance(start, str) else start.isoformat(),
                    "endDate": end if isinstance(end, str) else end.isoformat()},
        )

    def get_body_battery(self, start: date | str, end: date | str) -> Any:
        return self.get(
            "/wellness-service/wellness/bodyBattery/reports/daily",
            params={"startDate": start if isinstance(start, str) else start.isoformat(),
                    "endDate": end if isinstance(end, str) else end.isoformat()},
        )

    def search_activities(self, start: int = 0, limit: int = 20, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Any:
        params = {"start": start, "limit": limit}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        return self.get("/activitylist-service/activities/search/activities", params=params)

    def get_daily_stress(self, start: date | str, end: date | str) -> Any:
        return self.get(
            f"/usersummary-service/stats/stress/daily/{start if isinstance(start, str) else start.isoformat()}/{end if isinstance(end, str) else end.isoformat()}"
        )


def iso(d: date) -> str:
    return d.isoformat()
