"""Desktop app (PyQt6): ethical hacking and cybersecurity adaptive practice test."""
from __future__ import annotations

import os
import random
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QRadioButton, QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

from ethical_hacking_test.engine import MAX_WRONG, REVEAL_SECONDS, Attempt, ProgressStore, build_order
from ethical_hacking_test.question_bank import build_bank, chapter_counts
from ethical_hacking_test.radio_widget import RadioWidget
from ethical_hacking_test.study_guide import STUDY_GUIDE_HTML

APP_TITLE = "Ethical Hacking & Cybersecurity Practice Test"


def default_data_dir() -> Path:
    if os.environ.get("ETHICAL_HACKING_TEST_HOME"):
        return Path(os.environ["ETHICAL_HACKING_TEST_HOME"])
    if os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "EthicalHackingTest"
    return Path.home() / ".ethical-hacking-test"


STYLE = """
    QMainWindow { background-color: #2b2b2b; }
    QLabel { font-size: 14px; color: #e0e0e0; }
    QPushButton { background-color: #1f8a4c; color: white; font-size: 14px; padding: 10px 20px; border: none;
                  border-radius: 4px; font-weight: bold; }
    QPushButton:hover { background-color: #23a058; }
    QPushButton:disabled { background-color: #555; color: #888; }
    QRadioButton { font-size: 15px; color: #e0e0e0; padding: 8px; spacing: 10px; }
    QRadioButton:hover { background-color: #3c3c3c; }
    QListWidget { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #444; font-size: 13px; }
    QTextEdit { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #444; font-size: 14px; }
    QProgressBar { border: 1px solid #444; border-radius: 4px; background: #1e1e1e; text-align: center;
                   font-weight: bold; color: #e0e0e0; height: 22px; }
    QProgressBar::chunk { background-color: #1f8a4c; }
    QTabWidget::pane { border: 1px solid #444; }
    QTabBar::tab { background: #1e1e1e; color: #e0e0e0; padding: 10px 20px; }
    QTabBar::tab:selected { background: #1f8a4c; color: white; }
"""
BAR_STYLES = {
    "idle": "background-color: #1e1e1e; padding: 10px; border: 1px solid #444; font-weight: bold; font-size: 14px;",
    "active": "background-color: #fff3cd; color: #856404; padding: 10px; font-weight: bold; font-size: 14px;",
    "fail": "background-color: #c0392b; color: white; padding: 10px; font-weight: bold; font-size: 14px;",
    "pass": "background-color: #28a745; color: white; padding: 10px; font-weight: bold; font-size: 14px;",
}


class HackingTestWindow(QMainWindow):
    def __init__(self, data_dir: Path | None = None, bank: list[dict] | None = None,
                 rng: random.Random | None = None, confirm_dialogs: bool = True):
        super().__init__()
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.store = ProgressStore(self.data_dir / "ethical_hacking_results.db")
        self.bank = bank if bank is not None else build_bank()
        self.rng = rng or random.Random()
        self.confirm_dialogs = confirm_dialogs
        self.attempt: Attempt | None = None
        self.restart_delay_ms = 1500
        self.reveal_ms = REVEAL_SECONDS * 1000
        self.revealing = False

        self.setWindowTitle(APP_TITLE + " - Adaptive")
        self.setGeometry(80, 80, 1000, 800)
        self.setStyleSheet(STYLE)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_timer)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        title = QLabel(APP_TITLE)
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #3cc47c; margin-bottom: 10px;")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.test_tab, self.wrong_tab, self.guide_tab, self.info_tab = QWidget(), QWidget(), QWidget(), QWidget()
        self._setup_test_tab()
        self._setup_wrong_tab()
        self._setup_guide_tab()
        self._setup_info_tab()
        self.tabs.addTab(self.test_tab, "Take Test")
        self.tabs.addTab(self.wrong_tab, "Wrong Answers - Study These")
        self.tabs.addTab(self.guide_tab, "Study Guide")
        self.tabs.addTab(self.info_tab, "Info")

        self.status_bar = QLabel("Ready - click 'Start Test' when you are ready")
        self.status_bar.setStyleSheet(BAR_STYLES["idle"])
        layout.addWidget(self.status_bar)
        self.radio = RadioWidget(self.data_dir / "radio.json")
        layout.addWidget(self.radio)
        self.load_wrong_history()

    def closeEvent(self, event):
        self.radio.shutdown()
        super().closeEvent(event)

    # ---------- layout ----------
    def _setup_test_tab(self):
        layout = QVBoxLayout(self.test_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        top = QHBoxLayout()
        self.timer_label = QLabel("Time: 0:00")
        self.timer_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.wrong_label = QLabel(f"Wrong: 0/{MAX_WRONG}")
        self.wrong_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.wrong_label.setStyleSheet("padding-left: 30px;")
        top.addWidget(self.timer_label)
        top.addWidget(self.wrong_label)
        top.addStretch()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.bank))
        self.progress_bar.setValue(0)
        top.addWidget(self.progress_bar, stretch=2)
        layout.addLayout(top)

        self.question_label = QLabel(
            f"Ethical hacking & cybersecurity practice test - beginner to advanced\n\n"
            f"- All {len(self.bank)} questions every run, shuffled\n"
            f"- Max {MAX_WRONG} wrong: the {MAX_WRONG + 1}th wrong answer restarts the test instantly\n"
            "- Questions you missed come back FIRST next time\n\nClick 'Start Test' to begin.")
        self.question_label.setWordWrap(True)
        self.question_label.setFont(QFont("Arial", 14))
        self.question_label.setStyleSheet(
            "padding: 20px; background-color: #1e1e1e; border-radius: 5px; border: 1px solid #444;")
        self.question_label.setMinimumHeight(170)
        layout.addWidget(self.question_label)

        self.answer_group = QButtonGroup(self)
        self.answer_buttons = []
        for i in range(4):
            rb = QRadioButton()
            rb.setVisible(False)
            self.answer_group.addButton(rb, i)
            self.answer_buttons.append(rb)
            layout.addWidget(rb)
        self.answer_group.idClicked.connect(self.on_answer_selected)

        nav = QHBoxLayout()
        self.start_button = QPushButton("Start Test")
        self.start_button.clicked.connect(self.start_test)
        self.prev_button = QPushButton("< Previous")
        self.prev_button.clicked.connect(lambda: self.move(-1))
        self.next_button = QPushButton("Next >")
        self.next_button.clicked.connect(lambda: self.move(1))
        self.submit_button = QPushButton("Submit Test")
        self.submit_button.clicked.connect(self.confirm_submit)
        for b in (self.prev_button, self.next_button, self.submit_button):
            b.setEnabled(False)
        for b in (self.start_button, self.prev_button, self.next_button, self.submit_button):
            nav.addWidget(b)
        layout.addLayout(nav)

    def _setup_wrong_tab(self):
        layout = QVBoxLayout(self.wrong_tab)
        layout.addWidget(QLabel("Every question you missed, with the right answer and why:"))
        self.wrong_list = QListWidget()
        self.wrong_list.setWordWrap(True)
        layout.addWidget(self.wrong_list)
        row = QHBoxLayout()
        export = QPushButton("Export Wrong Answers to CSV")
        export.clicked.connect(self.export_wrong_questions)
        clear = QPushButton("Clear All History")
        clear.clicked.connect(self.clear_history)
        row.addWidget(export)
        row.addWidget(clear)
        layout.addLayout(row)

    def _setup_guide_tab(self):
        layout = QVBoxLayout(self.guide_tab)
        guide = QTextEdit()
        guide.setReadOnly(True)
        guide.setHtml(STUDY_GUIDE_HTML)
        layout.addWidget(guide)

    def _setup_info_tab(self):
        layout = QVBoxLayout(self.info_tab)
        counts = "".join(f"<li>{ch}: {n}</li>" for ch, n in chapter_counts(self.bank).items())
        info = QTextEdit()
        info.setReadOnly(True)
        info.setHtml(
            f"<h2>How it works</h2><ul><li>All {len(self.bank)} questions every run, in a new shuffle.</li>"
            f"<li>Get {MAX_WRONG + 1} wrong and the test restarts right away.</li>"
            "<li>Missed questions come first next time, then ones you have never seen, then ones you know.</li>"
            "<li>Your progress is saved on this computer between sessions.</li></ul>"
            f"<h2>Topics</h2><ul>{counts}</ul>"
            "<h2>Important</h2><p>This is a study tool modeled on CompTIA Security+/PenTest+ and CEH topics. "
            "Only practice on systems you own or have written permission to test (your own lab VMs, Hack The "
            "Box, TryHackMe). Accessing other people's systems without authorization is a crime under the "
            "Computer Fraud and Abuse Act and similar laws.</p>"
            f"<p>Progress file: {self.store.path}</p>")
        layout.addWidget(info)

    # ---------- test flow ----------
    def start_test(self):
        self.attempt = Attempt(build_order(self.bank, self.store.stats(), self.rng), self.store)
        self.progress_bar.setMaximum(self.attempt.total)
        self.progress_bar.setFormat(f"Question %v of {self.attempt.total}")
        self.timer_label.setText("Time: 0:00")
        self._update_wrong_label()
        for rb in self.answer_buttons:
            rb.setVisible(True)
        self.start_button.setEnabled(False)
        self.next_button.setEnabled(True)
        self.submit_button.setEnabled(True)
        self.status_bar.setText(f"Test in progress - answer all {self.attempt.total} questions, max {MAX_WRONG} wrong")
        self.status_bar.setStyleSheet(BAR_STYLES["active"])
        self.update_question_display()
        self.timer.start()

    def _update_wrong_label(self):
        n = self.attempt.wrong_count if self.attempt else 0
        self.wrong_label.setText(f"Wrong: {n}/{MAX_WRONG}")
        self.wrong_label.setStyleSheet(
            "padding-left: 30px; " + ("color: #ff6666; font-weight: bold;" if n else "color: #e0e0e0;"))

    def on_answer_selected(self, option: int):
        if not self.attempt or self.attempt.finished or self.revealing:
            return
        result = self.attempt.answer(option)
        self._update_wrong_label()
        if result["right"] is False:
            self.show_reveal(result["restart"])
        elif result["restart"]:
            self.auto_restart()

    def show_reveal(self, restart: bool):
        """Show the right answer for a few seconds after a miss, then move on (or restart)."""
        a = self.attempt
        q = a.question()
        self.revealing = True
        right = q["options"][q["correct"]]
        self.question_label.setText(
            f"Question {a.current + 1} of {a.total}   [{q['chapter']}]\n\n{q['question']}\n\n"
            f"WRONG - Correct answer: {chr(65 + q['correct'])}. {right}\nWhy: {q['explanation']}")
        for i, rb in enumerate(self.answer_buttons):
            rb.setEnabled(False)
            rb.setStyleSheet("color: #7fd77f; font-weight: bold;" if i == q["correct"] else
                             ("color: #ff7777;" if i == a.answers[a.current] else ""))
        for b in (self.prev_button, self.next_button, self.submit_button):
            b.setEnabled(False)
        self.status_bar.setText(f"Wrong - study the right answer ({REVEAL_SECONDS} seconds)...")
        self.status_bar.setStyleSheet(BAR_STYLES["fail"])
        QTimer.singleShot(self.reveal_ms, lambda: self._after_reveal(restart))

    def _after_reveal(self, restart: bool):
        self.revealing = False
        for rb in self.answer_buttons:
            rb.setEnabled(True)
            rb.setStyleSheet("")
        if restart:
            self.auto_restart()
            return
        self.submit_button.setEnabled(True)
        self.status_bar.setText(f"Test in progress - answer all {self.attempt.total} questions, max {MAX_WRONG} wrong")
        self.status_bar.setStyleSheet(BAR_STYLES["active"])
        if self.attempt.current < self.attempt.total - 1:
            self.move(1)
        else:
            self.update_question_display()

    def move(self, step: int):
        if not self.attempt or self.attempt.finished or self.revealing:
            return
        if self.attempt.move(step):
            self._update_wrong_label()
            self.auto_restart()
            return
        self._update_wrong_label()
        self.update_question_display()

    def auto_restart(self):
        self.timer.stop()
        self.status_bar.setText(
            f"{MAX_WRONG + 1} WRONG ANSWERS - TEST RESTARTING... your missed questions come back first!")
        self.status_bar.setStyleSheet(BAR_STYLES["fail"])
        for b in (self.prev_button, self.next_button, self.submit_button):
            b.setEnabled(False)
        QApplication.beep()
        QTimer.singleShot(self.restart_delay_ms, self.start_test)

    def update_question_display(self):
        a = self.attempt
        q = a.question()
        self.question_label.setText(f"Question {a.current + 1} of {a.total}   [{q['chapter']}]\n\n{q['question']}")
        self.answer_group.setExclusive(False)
        for i, rb in enumerate(self.answer_buttons):
            rb.setText(f"{chr(65 + i)}.  {q['options'][i]}")
            rb.setChecked(a.answers[a.current] == i)
        self.answer_group.setExclusive(True)
        self.progress_bar.setValue(a.current + 1)
        self.prev_button.setEnabled(a.current > 0)
        self.next_button.setEnabled(a.current < a.total - 1)

    def update_timer(self):
        if not self.attempt or self.attempt.finished:
            return
        self.attempt.seconds += 1
        m, s = divmod(self.attempt.seconds, 60)
        h, m = divmod(m, 60)
        self.timer_label.setText(f"Time: {h}:{m:02d}:{s:02d}" if h else f"Time: {m}:{s:02d}")

    def confirm_submit(self):
        if not self.attempt:
            return
        if self.confirm_dialogs:
            msg = "Submit your test now?"
            left = self.attempt.unanswered()
            if left:
                msg += f"\n\nWarning: {left} question(s) still unanswered - they count as WRONG."
            reply = QMessageBox.question(self, "Submit Test", msg,
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.finish_test()

    def finish_test(self) -> dict:
        self.timer.stop()
        result = self.attempt.finish()
        verdict = "PASSED" if result["passed"] else f"FAILED (more than {MAX_WRONG} wrong)"
        summary = f"Score: {result['score']}/{result['total']} | Wrong: {result['wrong']}/{MAX_WRONG} - {verdict}"
        self.status_bar.setText(summary + " - check the 'Wrong Answers' tab to study")
        self.status_bar.setStyleSheet(BAR_STYLES["pass" if result["passed"] else "fail"])
        self.question_label.setText(
            f"TEST COMPLETE\n\n{summary}\n\nYou missed {result['wrong']} question(s). Review every one in the "
            "'Wrong Answers - Study These' tab.\nNext test: your missed questions come back FIRST.")
        for rb in self.answer_buttons:
            rb.setVisible(False)
        for b in (self.prev_button, self.next_button, self.submit_button):
            b.setEnabled(False)
        self.start_button.setEnabled(True)
        self.start_button.setText("Take Test Again")
        self.update_wrong_tab()
        return result

    # ---------- study / history ----------
    def update_wrong_tab(self):
        self.wrong_list.clear()
        if not self.attempt or not self.attempt.misses:
            self.wrong_list.addItem(QListWidgetItem("No wrong answers on your last test - great job!"))
            return
        for m in self.attempt.misses:
            self.wrong_list.addItem(QListWidgetItem(
                f"Q{m.number} [{m.chapter}]\n{m.question}\n\nYour answer: {m.your_answer}\n"
                f"Correct answer: {m.correct_answer}\nWhy: {m.explanation}\n{'-' * 70}"))
        self.tabs.setCurrentWidget(self.wrong_tab)

    def load_wrong_history(self):
        for row in self.store.wrong_history(limit=50):
            self.wrong_list.addItem(QListWidgetItem(
                f"[{row['chapter']}] (missed {row['test_date']})\n{row['question']}\n\nYour answer: "
                f"{row['your_answer']}\nCorrect answer: {row['correct_answer']}\nWhy: {row['explanation']}\n"
                f"{'-' * 70}"))

    def export_wrong_questions(self) -> Path | None:
        path = self.data_dir / f"wrong_questions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        n = self.store.export_wrong_csv(path)
        if self.confirm_dialogs:
            if n:
                QMessageBox.information(self, "Export Complete", f"Exported {n} questions to:\n{path}")
            else:
                QMessageBox.information(self, "Nothing to Export", "No wrong answers saved yet.")
        return path if n else None

    def clear_history(self):
        if self.confirm_dialogs:
            reply = QMessageBox.question(
                self, "Clear History", "Delete ALL saved history including wrong-answer memory?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.store.clear()
        self.wrong_list.clear()


def main() -> int:
    app = QApplication(sys.argv)
    window = HackingTestWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
