import wave
from datetime import datetime, timedelta

import pytest

from ethical_hacking_test.alarm import (
    TASK_NAME, AlarmSettings, AlarmStore, apply_windows_task, is_due, next_fire, windows_task_script,
    write_beep_wav,
)

ON = AlarmSettings(enabled=True, hour=7, minute=0, station=1)
D = datetime(2026, 11, 9)


def at(h, m, s=0, day=0):
    return D + timedelta(days=day, hours=h, minutes=m, seconds=s)


def test_due_only_when_time_passes_between_checks():
    assert not is_due(ON, at(6, 59, 40), at(6, 59, 50))
    assert is_due(ON, at(6, 59, 55), at(7, 0, 5))
    assert not is_due(ON, at(7, 0, 5), at(7, 0, 15))  # rings once


def test_not_due_when_disabled_or_clock_goes_back():
    assert not is_due(AlarmSettings(False, 7, 0), at(6, 59), at(7, 1))
    assert not is_due(ON, at(7, 1), at(6, 59))


def test_late_grace_after_sleep():
    assert is_due(ON, at(6, 0), at(7, 20))  # laptop woke 20 min late: still ring
    assert not is_due(ON, at(6, 0), at(9, 0))  # hours late: don't


def test_midnight_alarm_wraps():
    s = AlarmSettings(True, 0, 0)
    assert is_due(s, at(23, 59, 55), at(0, 0, 5, day=1))


def test_next_fire():
    assert next_fire(ON, at(6, 0)) == at(7, 0)
    assert next_fire(ON, at(7, 0)) == at(7, 0, day=1)
    assert next_fire(AlarmSettings(), at(6, 0)) is None


def test_invalid_time_rejected():
    with pytest.raises(ValueError):
        AlarmSettings(True, 24, 0)


def test_store_roundtrip_and_corrupt(tmp_path):
    store = AlarmStore(tmp_path / "alarm.json")
    assert store.load() == AlarmSettings()
    store.save(ON)
    assert store.load() == ON
    (tmp_path / "alarm.json").write_text('{"enabled": true, "hour": 99, "minute": 0, "station": 0}')
    assert store.load() == AlarmSettings()


def test_beep_wav(tmp_path):
    p = write_beep_wav(tmp_path / "b.wav", seconds=1.0)
    with wave.open(str(p)) as w:
        assert w.getnchannels() == 1 and w.getframerate() == 22050 and w.getnframes() == 22050


def test_windows_task_script_wakes_pc():
    ps = windows_task_script(AlarmSettings(True, 6, 5), r"C:\Py\pythonw.exe", r"C:\Users\o'neil\app")
    assert "-WakeToRun" in ps and "-Daily -At '06:05'" in ps and "--ring" in ps
    assert r"'C:\Users\o''neil\app'" in ps and f"'{TASK_NAME}'" in ps


def test_disabled_removes_task():
    assert windows_task_script(AlarmSettings(), "p", "w").startswith("Unregister-ScheduledTask")


def test_apply_uses_runner():
    calls = []

    class R:
        returncode, stdout, stderr = 0, "", ""

    def runner(cmd, **kw):
        calls.append(cmd)
        return R()

    ok, _ = apply_windows_task(ON, "pythonw.exe", "app", runner=runner)
    assert ok and calls[0][0] == "powershell" and "-WakeToRun" in calls[0][-1]
