"""Radio player bar shown at the bottom of the desktop app."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSlider

from ethical_hacking_test.radio import RadioState

try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
except ImportError:  # Qt build without multimedia: show the bar but explain why it can't play
    QAudioOutput = QMediaPlayer = None


class RadioWidget(QFrame):
    def __init__(self, state_path: Path | None = None, parent=None):
        super().__init__(parent)
        self.state = RadioState(state_path)
        self.url_index = 0
        self.playing = False
        self.setStyleSheet("QFrame { background: #262626; border: 1px solid #444; border-radius: 8px; }"
                           "QLabel { border: none; }")
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 6, 10, 6)
        row.addWidget(QLabel("Radio:"))
        self.prev_button = QPushButton("<<")
        self.play_button = QPushButton("Play")
        self.next_button = QPushButton(">>")
        self.combo = QComboBox()
        for s in self.state.stations:
            self.combo.addItem(f"{s.name} ({s.dial}) - {s.genre}")
        self.combo.setCurrentIndex(self.state.index)
        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(self.state.volume)
        self.volume.setFixedWidth(110)
        self.status = QLabel("Stopped")
        self.status.setStyleSheet("color: #aaa;")
        for w in (self.prev_button, self.play_button, self.next_button):
            w.setFixedWidth(60)
            row.addWidget(w)
        row.addWidget(self.combo, 1)
        row.addWidget(QLabel("Vol"))
        row.addWidget(self.volume)
        row.addWidget(self.status)

        self.player = self.audio = None
        if QMediaPlayer is None:
            self._set_status("Radio needs Qt Multimedia")
            self.play_button.setEnabled(False)
        else:
            self.player, self.audio = QMediaPlayer(self), QAudioOutput(self)
            self.player.setAudioOutput(self.audio)
            self.audio.setVolume(self.state.volume / 100)
            self.player.errorOccurred.connect(self._on_error)
            self.player.mediaStatusChanged.connect(self._on_media_status)

        self.play_button.clicked.connect(self.toggle)
        self.prev_button.clicked.connect(lambda: self.step(-1))
        self.next_button.clicked.connect(lambda: self.step(1))
        self.combo.currentIndexChanged.connect(self.select)
        self.volume.valueChanged.connect(self.set_volume)

    def _set_status(self, text: str):
        self.status.setText(text)

    def _load_source(self):
        if self.player is not None:
            self.player.setSource(QUrl(self.state.station.urls[self.url_index]))

    def select(self, index: int):
        if index % len(self.state.stations) == self.state.index:
            return
        self.state.select(index)
        self.url_index = 0
        if self.combo.currentIndex() != self.state.index:
            self.combo.blockSignals(True)
            self.combo.setCurrentIndex(self.state.index)
            self.combo.blockSignals(False)
        if self.playing:
            self._load_source()
            self.player.play()
            self._set_status("Connecting...")

    def step(self, delta: int):
        self.select((self.state.index + delta) % len(self.state.stations))

    def toggle(self):
        if self.player is None:
            return
        if self.playing:
            self.player.stop()
            self.player.setSource(QUrl())
            self.playing = False
            self.play_button.setText("Play")
            self._set_status("Stopped")
        else:
            self.playing = True
            self.play_button.setText("Stop")
            self._set_status("Connecting...")
            self.url_index = 0
            self._load_source()
            self.player.play()

    def set_volume(self, value: int):
        v = self.state.set_volume(value)
        if self.audio is not None:
            self.audio.setVolume(v / 100)

    def _on_media_status(self, status):
        if not self.playing:
            return
        if status in (QMediaPlayer.MediaStatus.LoadingMedia, QMediaPlayer.MediaStatus.StalledMedia):
            self._set_status("Connecting...")
        elif status in (QMediaPlayer.MediaStatus.BufferingMedia, QMediaPlayer.MediaStatus.BufferedMedia):
            self._set_status(f"Playing {self.state.station.name}")

    def _on_error(self, *_):
        """Try the station's backup stream once; then report it offline."""
        if self.url_index + 1 < len(self.state.station.urls):
            self.url_index += 1
            self._load_source()
            if self.playing:
                self.player.play()
            return
        self.playing = False
        self.play_button.setText("Play")
        self._set_status(f"{self.state.station.name} is offline - try another station")

    def start(self):
        if not self.playing:
            self.toggle()

    def stop(self):
        if self.playing:
            self.toggle()

    def is_live(self) -> bool:
        return self.player is not None and self.playing and self.player.mediaStatus() in (
            QMediaPlayer.MediaStatus.BufferingMedia, QMediaPlayer.MediaStatus.BufferedMedia)

    def shutdown(self):
        if self.player is not None:
            self.player.stop()
