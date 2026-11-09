"""Atlanta radio stations and the player state shared by the desktop and phone versions."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Station:
    name: str
    dial: str
    genre: str
    urls: tuple[str, ...]  # tried in order; later ones are fallbacks


STATIONS: tuple[Station, ...] = (
    Station("V-103", "103.3 FM WVEE", "R&B, hip-hop & throwbacks",
            ("https://live.amperwave.net/direct/audacy-wveefmaac-imc",)),
    Station("Hot 107.9", "107.9 FM WHTA", "Hip-hop & R&B",
            ("https://playerservices.streamtheworld.com/api/livestream-redirect/WHTAFMAAC.aac",
             "https://playerservices.streamtheworld.com/api/livestream-redirect/WHTAFM.mp3")),
    Station("Majic 107.5/97.5", "107.5 / 97.5 FM WAMJ", "R&B & throwbacks (95.5 The Beat is off the air)",
            ("https://playerservices.streamtheworld.com/api/livestream-redirect/WAMJFMAAC.aac",
             "https://playerservices.streamtheworld.com/api/livestream-redirect/WAMJFM.mp3")),
)

DEFAULT_VOLUME = 60


class RadioState:
    """Selected station and volume, remembered between runs in a small JSON file."""

    def __init__(self, path: Path | None = None, stations: tuple[Station, ...] = STATIONS):
        if not stations:
            raise ValueError("at least one station is required")
        self.path = Path(path) if path else None
        self.stations = stations
        self.index = 0
        self.volume = DEFAULT_VOLUME
        self.load()

    @property
    def station(self) -> Station:
        return self.stations[self.index]

    def select(self, index: int) -> Station:
        self.index = index % len(self.stations)
        self.save()
        return self.station

    def step(self, delta: int) -> Station:
        return self.select(self.index + delta)

    def set_volume(self, volume: int) -> int:
        self.volume = max(0, min(100, int(volume)))
        self.save()
        return self.volume

    def load(self) -> None:
        if not self.path or not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            index, volume = int(data.get("index", 0)), int(data.get("volume", DEFAULT_VOLUME))
        except (OSError, ValueError, TypeError, AttributeError):
            return
        self.index = index if 0 <= index < len(self.stations) else 0
        self.volume = max(0, min(100, volume))

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"index": self.index, "volume": self.volume}), encoding="utf-8")
        tmp.replace(self.path)


def stations_json() -> str:
    return json.dumps([{"n": s.name, "d": s.dial, "g": s.genre, "u": list(s.urls)} for s in STATIONS],
                      separators=(",", ":"))
