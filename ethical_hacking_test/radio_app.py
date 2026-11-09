"""Stand-alone Atlanta Radio app: the stations plus a daily wake-up alarm."""
from __future__ import annotations

import getpass
import sys
from datetime import datetime, timedelta
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QTime, QTimer, QUrl
from PyQt6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPen, QPixmap
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QTimeEdit,
    QVBoxLayout, QWidget,
)

from ethical_hacking_test.alarm import (
    SNOOZE_MINUTES, AlarmSettings, AlarmStore, apply_windows_task, is_due, next_fire, write_beep_wav,
)
from ethical_hacking_test.app import default_data_dir
from ethical_hacking_test.radio import STATIONS
from ethical_hacking_test.radio_widget import RadioWidget

try:
    from PyQt6.QtMultimedia import QSoundEffect
except ImportError:
    QSoundEffect = None

TITLE = "Atlanta Radio"
SERVER_NAME = "AtlantaRadio-" + getpass.getuser()
RERING_GUARD = timedelta(minutes=5)  # ignore a second trigger (Windows task + open app) for the same alarm


def draw_icon(size: int = 256) -> QImage:
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 256
    p.setPen(QPen(QColor("#e0e0e0"), 10 * s))
    p.drawLine(QPointF(70 * s, 90 * s), QPointF(190 * s, 30 * s))  # antenna
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#1f8a4c"))
    p.drawRoundedRect(QRectF(16 * s, 80 * s, 224 * s, 150 * s), 28 * s, 28 * s)
    p.setBrush(QColor("#1e1e1e"))
    p.drawEllipse(QPointF(90 * s, 155 * s), 48 * s, 48 * s)  # speaker
    p.setBrush(QColor("#3cc47c"))
    p.drawEllipse(QPointF(90 * s, 155 * s), 18 * s, 18 * s)
    p.setBrush(QColor("#e0e0e0"))
    for i in range(3):
        p.drawRoundedRect(QRectF(160 * s, (115 + i * 30) * s, 56 * s, 14 * s), 6 * s, 6 * s)
    p.end()
    return img


def write_icon(path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not draw_icon().save(str(path)):
        raise OSError(f"could not write icon {path}")
    return path


class AlarmPanel(QFrame):
    def __init__(self, radio: RadioWidget, data_dir: Path, clock=datetime.now, task_runner=None, tone=None):
        super().__init__()
        self.radio, self.clock, self.task_runner = radio, clock, task_runner
        self.store = AlarmStore(Path(data_dir) / "alarm.json")
        self.settings = self.store.load()
        self.ringing = False
        self.snooze_until: datetime | None = None
        self.last_rang: datetime | None = None
        self.last_check = clock()
        self.fallback_ms = 20000
        self.last_task_result: tuple[bool, str] | None = None
        self.tone = tone if tone is not None else self._make_tone(Path(data_dir) / "alarm-beep.wav")

        self.setStyleSheet("QFrame { background: #262626; border: 1px solid #444; border-radius: 8px; }"
                           "QLabel, QCheckBox { border: none; }")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 6, 10, 6)
        self.enabled = QCheckBox("Alarm on")
        self.enabled.setChecked(self.settings.enabled)
        self.time = QTimeEdit(QTime(self.settings.hour, self.settings.minute))
        self.time.setDisplayFormat("h:mm AP")
        self.station = QComboBox()
        self.station.addItems([s.name for s in STATIONS])
        self.station.setCurrentIndex(self.settings.station if self.settings.station < len(STATIONS) else 0)
        self.info = QLabel()
        self.info.setStyleSheet("color: #aaa;")
        self.snooze_button = QPushButton(f"Snooze {SNOOZE_MINUTES} min")
        self.stop_button = QPushButton("Stop alarm")
        self.stop_button.setStyleSheet("background: #c0392b;")
        for w in (self.enabled, QLabel("Wake me at"), self.time, QLabel("to"), self.station):
            row.addWidget(w)
        row.addWidget(self.info, 1)
        row.addWidget(self.snooze_button)
        row.addWidget(self.stop_button)
        self.snooze_button.hide()
        self.stop_button.hide()

        self.task_debounce = QTimer(self)
        self.task_debounce.setSingleShot(True)
        self.task_debounce.setInterval(1500)
        self.task_debounce.timeout.connect(self.sync_task)
        self.enabled.toggled.connect(self._changed)
        self.time.timeChanged.connect(self._changed)
        self.station.currentIndexChanged.connect(self._changed)
        self.snooze_button.clicked.connect(self.snooze)
        self.stop_button.clicked.connect(self.stop_alarm)
        self.check_timer = QTimer(self)
        self.check_timer.setInterval(10000)
        self.check_timer.timeout.connect(self.check)
        self.check_timer.start()
        self._update_info()

    @staticmethod
    def _make_tone(path: Path):
        if QSoundEffect is None:
            return None
        if not path.exists():
            write_beep_wav(path)
        tone = QSoundEffect()
        tone.setSource(QUrl.fromLocalFile(str(path)))
        tone.setLoopCount(QSoundEffect.Loop.Infinite.value)
        return tone

    def _changed(self, *_):
        t = self.time.time()
        self.settings = AlarmSettings(self.enabled.isChecked(), t.hour(), t.minute(), self.station.currentIndex())
        self.store.save(self.settings)
        self.last_check = self.clock()
        self.task_debounce.start()
        self._update_info()

    def sync_task(self) -> tuple[bool, str]:
        kwargs = {"runner": self.task_runner} if self.task_runner else {}
        self.last_task_result = apply_windows_task(self.settings, **kwargs)
        return self.last_task_result

    def _update_info(self):
        if self.ringing:
            self.info.setText(f"ALARM - {STATIONS[self.settings.station].name}")
            self.info.setStyleSheet("color: #ff7777; font-weight: bold;")
            return
        self.info.setStyleSheet("color: #aaa;")
        if self.snooze_until:
            self.info.setText(f"Snoozing until {self.snooze_until:%I:%M %p}".replace(" 0", " "))
            return
        nxt = next_fire(self.settings, self.clock())
        self.info.setText(f"Next: {nxt:%a %I:%M %p}".replace(" 0", " ") if nxt else "Alarm off")

    def check(self, now: datetime | None = None) -> bool:
        now = now or self.clock()
        snooze_due = self.snooze_until is not None and self.last_check < self.snooze_until <= now
        due = is_due(self.settings, self.last_check, now) or snooze_due
        self.last_check = now
        if due:
            self.ring(now, force=snooze_due)
        elif not self.ringing:
            self._update_info()
        return due

    def ring(self, now: datetime | None = None, force: bool = False):
        now = now or self.clock()
        if self.ringing or (not force and self.last_rang and now - self.last_rang < RERING_GUARD):
            return
        self.ringing, self.snooze_until, self.last_rang = True, None, now
        self.radio.select(self.settings.station)
        if self.radio.state.volume < 30:
            self.radio.volume.setValue(50)
        self.radio.start()
        self.snooze_button.show()
        self.stop_button.show()
        self._update_info()
        win = self.window()
        win.showNormal()
        win.raise_()
        win.activateWindow()
        QTimer.singleShot(self.fallback_ms, self._fallback)

    def _fallback(self):
        """No live stream (internet down or station offline): beep instead so the alarm still wakes you."""
        if self.ringing and not self.radio.is_live():
            self.radio.stop()
            if self.tone is not None:
                self.tone.play()

    def _silence(self):
        self.ringing = False
        self.radio.stop()
        if self.tone is not None:
            self.tone.stop()
        self.snooze_button.hide()
        self.stop_button.hide()

    def snooze(self):
        self._silence()
        self.snooze_until = self.clock() + timedelta(minutes=SNOOZE_MINUTES)
        self._update_info()

    def stop_alarm(self):
        self._silence()
        self.snooze_until = None
        self._update_info()


class RadioWindow(QMainWindow):
    def __init__(self, data_dir: Path | None = None, clock=datetime.now, task_runner=None, tone=None):
        super().__init__()
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.setWindowTitle(TITLE)
        self.setWindowIcon(QIcon(QPixmap.fromImage(draw_icon(64))))
        self.setStyleSheet("QMainWindow, QWidget { background: #1e1e1e; color: #e0e0e0; font-size: 14px; }"
                           "QPushButton { background: #1f8a4c; color: white; border: none; border-radius: 6px;"
                           " padding: 8px; font-weight: bold; } QPushButton:hover { background: #28a745; }"
                           "QComboBox, QTimeEdit { background: #333; border: 1px solid #555; padding: 6px; }")
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        title = QLabel(TITLE)
        title.setStyleSheet("color: #3cc47c; font-size: 22px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        lineup = QLabel("\n".join(f"{s.name}  -  {s.dial}  -  {s.genre}" for s in STATIONS))
        lineup.setStyleSheet("color: #aaa;")
        lineup.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lineup)
        self.radio = RadioWidget(self.data_dir / "radio.json")
        layout.addWidget(self.radio)
        self.alarm = AlarmPanel(self.radio, self.data_dir, clock=clock, task_runner=task_runner, tone=tone)
        layout.addWidget(self.alarm)
        note = QLabel("The alarm also wakes the laptop and opens this app if it's closed (keep it plugged in).")
        note.setStyleSheet("color: #777; font-size: 12px;")
        layout.addWidget(note)
        self.resize(860, 300)

    def handle_message(self, msg: str):
        if msg == "ring":
            self.alarm.ring()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        self.alarm._silence()
        self.radio.shutdown()
        super().closeEvent(event)


def send_to_running(name: str, msg: str) -> bool:
    """Hand a message to an already-open window (in another process); False if none is running."""
    sock = QLocalSocket()
    sock.connectToServer(name)
    if not sock.waitForConnected(1000):
        return False
    sock.write(msg.encode())
    sock.flush()
    sock.waitForBytesWritten(1000)
    sock.waitForReadyRead(3000)  # server acks; closing before that can drop the message on Windows pipes
    sock.disconnectFromServer()
    return True


def start_server(name: str, handler) -> QLocalServer:
    server = QLocalServer()
    QLocalServer.removeServer(name)
    if not server.listen(name):
        raise OSError(server.errorString())

    def accept():
        while server.hasPendingConnections():
            conn = server.nextPendingConnection()
            done = []

            def on_ready(conn=conn, done=done):
                data = bytes(conn.readAll()).decode(errors="ignore").strip()
                if not data or done:
                    return
                done.append(True)
                conn.write(b"ok")
                conn.flush()
                handler(data)
                conn.disconnectFromServer()

            conn.readyRead.connect(on_ready)
            if conn.bytesAvailable():
                on_ready()

    server.newConnection.connect(accept)
    return server


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    app = QApplication.instance() or QApplication(argv)
    if len(argv) > 2 and argv[1] == "--make-icon":
        print(write_icon(Path(argv[2])))
        return 0
    ring = "--ring" in argv
    if send_to_running(SERVER_NAME, "ring" if ring else "show"):
        return 0  # already open: that window handles it
    window = RadioWindow()
    server = start_server(SERVER_NAME, window.handle_message)
    window.show()
    if ring:
        window.alarm.ring()
    code = app.exec()
    server.close()
    return code


if __name__ == "__main__":
    sys.exit(main())
