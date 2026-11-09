import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from PyQt6.QtGui import QImage  # noqa: E402

from ethical_hacking_test.radio import STATIONS  # noqa: E402
from ethical_hacking_test.radio_app import RadioWindow, draw_icon, main, write_icon  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_window_has_only_the_radio(qapp, tmp_path):
    w = RadioWindow(data_dir=tmp_path)
    assert w.windowTitle() == "Atlanta Radio"
    assert w.radio.combo.count() == len(STATIONS)
    w.radio.step(1)
    w.close()
    assert RadioWindow(data_dir=tmp_path).radio.state.index == 1  # shares saved choice


def test_icon_is_drawn_and_saved_as_ico(qapp, tmp_path):
    img = draw_icon(64)
    assert img.width() == 64 and img.pixelColor(32, 40).alpha() > 0
    path = write_icon(tmp_path / "radio.ico")
    assert path.stat().st_size > 1000 and not QImage(str(path)).isNull()


def test_make_icon_command(qapp, tmp_path, capsys):
    out = tmp_path / "x" / "radio.ico"
    assert main(["radio", "--make-icon", str(out)]) == 0
    assert out.exists() and str(out) in capsys.readouterr().out


class FakeTone:
    def __init__(self):
        self.playing = False

    def play(self):
        self.playing = True

    def stop(self):
        self.playing = False


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def make(tmp_path, clock, monkeypatch):
    from ethical_hacking_test.radio_widget import RadioWidget
    started = []
    monkeypatch.setattr(RadioWidget, "start", lambda self: started.append(self.state.index) or None)
    monkeypatch.setattr(RadioWidget, "stop", lambda self: None)
    monkeypatch.setattr(RadioWidget, "is_live", lambda self: False)
    calls = []

    class R:
        returncode, stdout, stderr = 0, "", ""

    w = RadioWindow(data_dir=tmp_path, clock=clock, task_runner=lambda cmd, **kw: calls.append(cmd) or R(),
                    tone=FakeTone())
    return w, started, calls


def test_alarm_rings_station_then_snooze_and_stop(qapp, tmp_path, monkeypatch):
    from datetime import datetime, timedelta

    from PyQt6.QtCore import QTime
    clock = Clock(datetime(2026, 11, 9, 6, 59, 55))
    w, started, calls = make(tmp_path, clock, monkeypatch)
    a = w.alarm
    a.fallback_ms = 0
    a.time.setTime(QTime(7, 0))
    a.station.setCurrentIndex(2)
    a.enabled.setChecked(True)
    assert "Next:" in a.info.text()
    assert a.sync_task()[0] and "-WakeToRun" in calls[-1][-1]
    clock.t += timedelta(seconds=2)
    assert not a.check()
    clock.t = datetime(2026, 11, 9, 7, 0, 5)
    assert a.check() and a.ringing and started == [2] and w.radio.state.index == 2
    assert not a.stop_button.isHidden() and "ALARM" in a.info.text()
    for _ in range(5):
        qapp.processEvents()
    assert a.tone.playing  # stream not live -> beep fallback
    a.snooze()
    assert not a.ringing and not a.tone.playing and "Snoozing" in a.info.text()
    clock.t += timedelta(minutes=9, seconds=5)
    assert a.check() and a.ringing
    a.stop_alarm()
    assert not a.ringing and a.stop_button.isHidden() and "Next:" in a.info.text()
    a.ring()  # duplicate trigger from the Windows task right after: ignored
    assert not a.ringing
    w.close()


def test_alarm_settings_saved(qapp, tmp_path, monkeypatch):
    from datetime import datetime

    from PyQt6.QtCore import QTime
    w, _, _ = make(tmp_path, Clock(datetime(2026, 11, 9, 5, 0)), monkeypatch)
    w.alarm.time.setTime(QTime(6, 30))
    w.alarm.enabled.setChecked(True)
    w.close()
    w2, _, _ = make(tmp_path, Clock(datetime(2026, 11, 9, 5, 0)), monkeypatch)
    assert w2.alarm.enabled.isChecked() and w2.alarm.time.time() == QTime(6, 30)
    w2.close()


def test_second_launch_with_ring_reaches_open_window(qapp, tmp_path):
    from ethical_hacking_test.radio_app import send_to_running, start_server
    import subprocess
    import sys
    import time
    name = f"atl-radio-test-{os.getpid()}"
    got = []
    server = start_server(name, got.append)
    # a real second launch is another process
    code = ("import sys; from PyQt6.QtCore import QCoreApplication; app = QCoreApplication([]); "
            "from ethical_hacking_test.radio_app import send_to_running; "
            f"sys.exit(0 if send_to_running({name!r}, 'ring') else 3)")
    proc = subprocess.Popen([sys.executable, "-c", code], cwd=os.path.dirname(os.path.dirname(__file__)))
    deadline = time.time() + 20
    while time.time() < deadline and (proc.poll() is None or not got):
        qapp.processEvents()
        time.sleep(0.01)
    server.close()
    assert proc.wait(timeout=5) == 0
    assert got == ["ring"]
    assert not send_to_running(f"atl-radio-none-{os.getpid()}", "ring")
