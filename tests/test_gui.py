import os
import random

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
QtWidgets = pytest.importorskip("PyQt6.QtWidgets")

from ethical_hacking_test.app import HackingTestWindow  # noqa: E402
from ethical_hacking_test.engine import MAX_WRONG  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def drain(qapp, w):
    for _ in range(50):
        qapp.processEvents()
        if not w.revealing:
            break


def test_full_flow(qapp, tmp_path):
    w = HackingTestWindow(data_dir=tmp_path, rng=random.Random(2), confirm_dialogs=False)
    w.restart_delay_ms = 0
    w.reveal_ms = 0
    w.start_test()
    assert w.attempt.total == 1200 and "Question 1 of 1200" in w.question_label.text()
    for n in range(MAX_WRONG + 1):
        q = w.attempt.question()
        w.on_answer_selected((q["correct"] + 1) % 4)
        assert w.revealing and "Correct answer:" in w.question_label.text()
        assert not w.answer_buttons[0].isEnabled() and not w.next_button.isEnabled()
        w.move(1)  # ignored while the answer is shown
        drain(qapp, w)
        if n < MAX_WRONG:
            assert w.attempt.current == n + 1
    assert "RESTARTING" in w.status_bar.text()
    w.start_test()
    q = w.attempt.question()
    w.on_answer_selected(q["correct"])
    assert not w.revealing and w.attempt.current == 0
    result = w.finish_test()
    assert result["score"] == 1 and not result["passed"]
    assert w.wrong_list.count() > 0
    assert w.export_wrong_questions() is not None
    w.close()


def test_radio_bar_at_bottom(qapp, tmp_path):
    from ethical_hacking_test.radio import STATIONS
    w = HackingTestWindow(data_dir=tmp_path, rng=random.Random(3), confirm_dialogs=False)
    layout = w.centralWidget().layout()
    assert layout.itemAt(layout.count() - 1).widget() is w.radio
    assert w.radio.combo.count() == len(STATIONS)
    w.radio.step(1)
    assert w.radio.combo.currentIndex() == 1 and w.radio.state.index == 1
    if w.radio.player is not None:
        assert w.radio.player.source().isEmpty()  # nothing streams until Play is pressed
    w.radio.combo.setCurrentIndex(2)
    assert w.radio.state.index == 2
    w.radio.volume.setValue(25)
    w.close()
    w2 = HackingTestWindow(data_dir=tmp_path, rng=random.Random(3), confirm_dialogs=False)
    assert w2.radio.combo.currentIndex() == 2 and w2.radio.volume.value() == 25
    w2.close()
