import csv
import random

import pytest

from ethical_hacking_test.engine import MAX_WRONG, Attempt, ProgressStore, build_order
from ethical_hacking_test.question_bank import build_bank


@pytest.fixture
def store(tmp_path):
    return ProgressStore(tmp_path / "p.db")


@pytest.fixture
def bank():
    return build_bank()


def wrong_option(q):
    return (q["correct"] + 1) % 4


def test_order_puts_missed_first_then_unseen(store, bank):
    store.record(bank[0]["id"], False)
    store.record(bank[1]["id"], True)
    order = build_order(bank, store.stats(), random.Random(1))
    assert order[0]["id"] == bank[0]["id"]
    assert order[-1]["id"] == bank[1]["id"]
    assert len(order) == len(bank)


def test_sixteenth_wrong_triggers_restart(store, bank):
    a = Attempt(bank, store)
    for i in range(MAX_WRONG):
        a.select(wrong_option(a.question()))
        assert a.move(1) is False
    a.select(wrong_option(a.question()))
    assert a.move(1) is True
    assert a.wrong_count == MAX_WRONG + 1
    att = store.attempts()[-1]
    assert att["restarted"] == 1 and att["passed"] == 0


def test_right_answers_do_not_count(store, bank):
    a = Attempt(bank[:5], store)
    for _ in range(5):
        a.select(a.question()["correct"])
        a.move(1)
    assert a.wrong_count == 0


def test_changing_answer_rescores(store, bank):
    a = Attempt(bank[:3], store)
    a.select(wrong_option(a.question()))
    a.move(1)
    a.move(-1)
    assert a.wrong_count == 1
    a.select(a.question()["correct"])
    assert a.wrong_count == 0


def test_finish_counts_blanks_wrong_and_saves(store, bank):
    a = Attempt(bank[:20], store)
    a.select(a.question()["correct"])
    result = a.finish()
    assert result == {"score": 1, "wrong": 19, "total": 20, "passed": False}
    with pytest.raises(RuntimeError):
        a.finish()


def test_pass_when_at_limit(store, bank):
    a = Attempt(bank[:30], store)
    for i in range(30):
        q = a.question()
        a.select(wrong_option(q) if i < MAX_WRONG else q["correct"])
        a.move(1)
    assert a.finish()["passed"] is True


def test_progress_persists_and_reorders(tmp_path, bank):
    s1 = ProgressStore(tmp_path / "p.db")
    a = Attempt(bank[:10], s1)
    a.select(wrong_option(a.question()))
    missed = a.question()["id"]
    a.finish()
    s2 = ProgressStore(tmp_path / "p.db")
    assert build_order(bank, s2.stats(), random.Random(3))[0]["id"] == missed


def test_csv_export_and_clear(tmp_path, store, bank):
    a = Attempt(bank[:3], store)
    a.finish()
    out = tmp_path / "w.csv"
    assert store.export_wrong_csv(out) == 3
    rows = list(csv.reader(out.open()))
    assert rows[0][0] == "Question" and len(rows) == 4
    store.clear()
    assert store.export_wrong_csv(out) == 0 and store.stats() == {}


def test_bad_option_rejected(store, bank):
    with pytest.raises(ValueError):
        Attempt(bank[:2], store).select(7)


def test_wrong_answer_is_scored_and_locked_at_once(store, bank):
    a = Attempt(bank[:5], store)
    q = a.question()
    r = a.answer(wrong_option(q))
    assert r == {"right": False, "restart": False}
    assert a.wrong_count == 1 and a.locked[0] and a.scored[0]
    assert a.answer(q["correct"]) == {"right": None, "restart": False}
    assert a.answers[0] == wrong_option(q) and a.wrong_count == 1


def test_right_answer_not_locked(store, bank):
    a = Attempt(bank[:5], store)
    assert a.answer(a.question()["correct"])["right"] is True
    assert not a.locked[0] and a.wrong_count == 0


def test_answer_reports_restart_on_sixteenth_miss(store, bank):
    a = Attempt(bank, store)
    for _ in range(MAX_WRONG):
        assert a.answer(wrong_option(a.question()))["restart"] is False
        a.move(1)
    assert a.answer(wrong_option(a.question()))["restart"] is True
