"""Daily radio alarm: settings, when it is due, a fallback beep, and the Windows wake-up task."""
from __future__ import annotations

import json
import math
import struct
import subprocess
import sys
import wave
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

SNOOZE_MINUTES = 9
LATE_GRACE = timedelta(minutes=30)  # after a long sleep, don't ring hours late
TASK_NAME = "Atlanta Radio Alarm"


@dataclass
class AlarmSettings:
    enabled: bool = False
    hour: int = 7
    minute: int = 0
    station: int = 0

    def __post_init__(self):
        if not (0 <= self.hour <= 23 and 0 <= self.minute <= 59):
            raise ValueError("alarm time out of range")


class AlarmStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> AlarmSettings:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return AlarmSettings(bool(data["enabled"]), int(data["hour"]), int(data["minute"]), int(data["station"]))
        except (OSError, ValueError, TypeError, KeyError):
            return AlarmSettings()

    def save(self, settings: AlarmSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(settings)), encoding="utf-8")
        tmp.replace(self.path)


def _latest_at_or_before(s: AlarmSettings, now: datetime) -> datetime:
    t = now.replace(hour=s.hour, minute=s.minute, second=0, microsecond=0)
    return t if t <= now else t - timedelta(days=1)


def next_fire(s: AlarmSettings, now: datetime) -> datetime | None:
    if not s.enabled:
        return None
    t = now.replace(hour=s.hour, minute=s.minute, second=0, microsecond=0)
    return t if t > now else t + timedelta(days=1)


def is_due(s: AlarmSettings, last_check: datetime, now: datetime) -> bool:
    """True once when the alarm time passed between two checks (and not too long ago)."""
    if not s.enabled or now <= last_check:
        return False
    t = _latest_at_or_before(s, now)
    return last_check < t <= now and now - t <= LATE_GRACE


def write_beep_wav(path: Path, seconds: float = 2.0, rate: int = 22050) -> Path:
    """Two-tone beep-beep pattern used when the station can't be reached."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for n in range(int(seconds * rate)):
        t = n / rate
        on = (t % 0.5) < 0.25
        sample = int(12000 * math.sin(2 * math.pi * 880 * t)) if on else 0
        frames += struct.pack("<h", sample)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))
    return path


def _ps_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def windows_task_script(s: AlarmSettings, pythonw: str, workdir: str) -> str:
    """PowerShell that registers (or removes) a daily task that wakes the PC and rings the alarm."""
    if not s.enabled:
        return (f"Unregister-ScheduledTask -TaskName {_ps_quote(TASK_NAME)} -Confirm:$false "
                "-ErrorAction SilentlyContinue")
    return "; ".join([
        f"$a = New-ScheduledTaskAction -Execute {_ps_quote(pythonw)} "
        f"-Argument '-m ethical_hacking_test.radio_app --ring' -WorkingDirectory {_ps_quote(workdir)}",
        f"$t = New-ScheduledTaskTrigger -Daily -At '{s.hour:02d}:{s.minute:02d}'",
        "$s = New-ScheduledTaskSettingsSet -WakeToRun -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
        "-ExecutionTimeLimit (New-TimeSpan -Hours 2)",
        f"Register-ScheduledTask -TaskName {_ps_quote(TASK_NAME)} -Action $a -Trigger $t -Settings $s -Force "
        "| Out-Null",
    ])


def apply_windows_task(s: AlarmSettings, pythonw: str | None = None, workdir: str | None = None,
                       runner=subprocess.run) -> tuple[bool, str]:
    """Keep the Windows task in sync with the settings. No-op elsewhere (the open app still rings)."""
    if sys.platform != "win32" and runner is subprocess.run:
        return False, "wake-up task only on Windows"
    pythonw = pythonw or str(Path(sys.executable).with_name("pythonw.exe"))
    workdir = workdir or str(Path(__file__).resolve().parent.parent)
    try:
        r = runner(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                    windows_task_script(s, pythonw, workdir)],
                   capture_output=True, text=True, timeout=60,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    return r.returncode == 0, (r.stderr or r.stdout or "").strip()
