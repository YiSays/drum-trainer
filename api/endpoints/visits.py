"""
Server-side visitor tracking with JSON file persistence.
"""

import json
import os
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.config import get_storage_dir


class VisitStats(BaseModel):
    total_page_loads: int
    total_unique_visitors: int
    today_page_loads: int
    today_unique_visitors: int
    days: dict


class VisitsTracker:
    def __init__(self, data_path: Optional[Path] = None):
        if data_path is None:
            data_path = get_storage_dir() / "analytics" / "visits.json"
        self._data_path = data_path
        self._lock = threading.Lock()
        self._data: dict = self._load()

    def _default_data(self) -> dict:
        return {"total_page_loads": 0, "days": {}}

    def _load(self) -> dict:
        if not self._data_path.exists():
            return self._default_data()
        try:
            with open(self._data_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return self._default_data()

    def _save(self) -> None:
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._data_path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp_path, self._data_path)

    def _cleanup_old_ips(self) -> None:
        today_str = date.today().isoformat()
        for day_key, day_data in list(self._data["days"].items()):
            if day_key != today_str and "ips" in day_data:
                del day_data["ips"]

    def record_visit(self, client_ip: str) -> dict:
        with self._lock:
            today_str = date.today().isoformat()
            self._data["total_page_loads"] += 1

            if today_str not in self._data["days"]:
                self._data["days"][today_str] = {
                    "page_loads": 0,
                    "unique_count": 0,
                    "ips": [],
                }

            today_data = self._data["days"][today_str]
            today_data["page_loads"] += 1

            if client_ip not in today_data.get("ips", []):
                today_data["ips"] = today_data.get("ips", [])
                today_data["ips"].append(client_ip)
                today_data["unique_count"] = len(today_data["ips"])

            self._cleanup_old_ips()
            self._save()
            return self.get_stats()

    def get_stats(self) -> dict:
        total_unique = sum(
            d.get("unique_count", 0) for d in self._data["days"].values()
        )
        today_str = date.today().isoformat()
        today_data = self._data["days"].get(today_str, {})

        return {
            "total_page_loads": self._data["total_page_loads"],
            "total_unique_visitors": total_unique,
            "today_page_loads": today_data.get("page_loads", 0),
            "today_unique_visitors": today_data.get("unique_count", 0),
            "days": {
                k: {
                    "page_loads": v.get("page_loads", 0),
                    "unique_count": v.get("unique_count", 0),
                }
                for k, v in self._data["days"].items()
            },
        }


router = APIRouter(prefix="/visits", tags=["Visits"])
visits_tracker = VisitsTracker()


@router.get("", summary="Get visit stats")
async def get_visits() -> dict:
    return visits_tracker.get_stats()
