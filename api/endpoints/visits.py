"""
Server-side visitor tracking with JSONL file persistence.

Data format (visits.jsonl):
  Line 1: {"type": "summary", "total_page_loads": N, "archived": {"page_loads": N, "unique_count": N}}
  Lines+: {"type": "day", "date": "YYYY-MM-DD", "page_loads": N, "unique_count": N}
  Today's line includes "ips": [...] for dedup (stripped on next day's first write).
"""

import json
import os
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from api.config import get_storage_dir

RETENTION_DAYS = 180


class VisitStats(BaseModel):
    total_page_loads: int
    total_unique_visitors: int
    today_page_loads: int
    today_unique_visitors: int
    archived: dict
    days: dict


class VisitsTracker:
    def __init__(self, data_path: Optional[Path] = None):
        if data_path is None:
            data_path = get_storage_dir() / "analytics" / "visits.jsonl"
        self._data_path = data_path
        self._lock = threading.Lock()
        self._data: dict = self._load()

    def _default_data(self) -> dict:
        return {
            "total_page_loads": 0,
            "archived": {"page_loads": 0, "unique_count": 0},
            "days": {},
        }

    def _load(self) -> dict:
        if not self._data_path.exists():
            return self._default_data()
        try:
            data = self._default_data()
            with open(self._data_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry.get("type") == "summary":
                        data["total_page_loads"] = entry.get("total_page_loads", 0)
                        data["archived"] = entry.get("archived", data["archived"])
                    elif entry.get("type") == "day":
                        day_key = entry["date"]
                        data["days"][day_key] = {
                            "page_loads": entry.get("page_loads", 0),
                            "unique_count": entry.get("unique_count", 0),
                        }
                        if "ips" in entry:
                            data["days"][day_key]["ips"] = entry["ips"]
            return data
        except (json.JSONDecodeError, OSError):
            return self._default_data()

    def _save(self) -> None:
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._data_path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            summary = {
                "type": "summary",
                "total_page_loads": self._data["total_page_loads"],
                "archived": self._data["archived"],
            }
            f.write(json.dumps(summary) + "\n")
            for day_key in sorted(self._data["days"]):
                day_data = self._data["days"][day_key]
                entry = {
                    "type": "day",
                    "date": day_key,
                    "page_loads": day_data["page_loads"],
                    "unique_count": day_data["unique_count"],
                }
                if "ips" in day_data:
                    entry["ips"] = day_data["ips"]
                f.write(json.dumps(entry) + "\n")
        os.replace(tmp_path, self._data_path)

    def _cleanup(self) -> None:
        today_str = date.today().isoformat()
        cutoff = (date.today() - timedelta(days=RETENTION_DAYS)).isoformat()

        for day_key, day_data in list(self._data["days"].items()):
            if day_key != today_str and "ips" in day_data:
                del day_data["ips"]
            if day_key < cutoff:
                self._data["archived"]["page_loads"] += day_data.get("page_loads", 0)
                self._data["archived"]["unique_count"] += day_data.get(
                    "unique_count", 0
                )
                del self._data["days"][day_key]

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

            self._cleanup()
            self._save()
            return self.get_stats()

    def get_stats(self) -> dict:
        archived = self._data["archived"]
        days_unique = sum(
            d.get("unique_count", 0) for d in self._data["days"].values()
        )
        today_str = date.today().isoformat()
        today_data = self._data["days"].get(today_str, {})

        return {
            "total_page_loads": self._data["total_page_loads"],
            "total_unique_visitors": archived["unique_count"] + days_unique,
            "today_page_loads": today_data.get("page_loads", 0),
            "today_unique_visitors": today_data.get("unique_count", 0),
            "archived": archived,
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
