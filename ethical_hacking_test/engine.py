"""Test logic with no GUI: question order, live scoring, auto-restart and saved progress.

The desktop app and the tests drive this module; the web version mirrors the same rules in JavaScript.
"""
from __future__ import annotations

import csv
import random
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

MAX_WRONG = 15  # the 16th wrong answer restarts the test
REVEAL_SECONDS = 8  # how long the right answer is shown after a miss


@dataclass
class Miss:
    number: int
    qid: str
    question: str
    your_answer: str
    correct_answer: str
    explanation: str
    chapter: str


class ProgressStore:
    """SQLite memory of every question's history, attempts and missed questions."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS question_stats (
                    qid TEXT PRIMARY KEY,
                    times_right INTEGER NOT NULL DEFAULT 0,
                    times_wrong INTEGER NOT NULL DEFAULT 0,
                    last_wrong INTEGER NOT NULL DEFAULT 0,
                    answered INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_date TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    wrong INTEGER NOT NULL,
                    total INTEGER NOT NULL,
                    passed INTEGER NOT NULL,
                    restarted INTEGER NOT NULL,
                    seconds INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS wrong_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id INTEGER NOT NULL REFERENCES attempts(id),
                    test_date TEXT NOT NULL,
                    qid TEXT NOT NULL,
                    question TEXT NOT NULL,
                    your_answer TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    explanation TEXT NOT NULL,
                    chapter TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_wrong_date ON wrong_questions(test_date);
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.path))

    def stats(self) -> dict[str, tuple[int, int, int, int]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT qid, times_right, times_wrong, last_wrong, answered FROM question_stats")
            return {r[0]: tuple(r[1:]) for r in rows}

    def record(self, qid: str, correct: bool) -> None:
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO question_stats (qid, times_right, times_wrong, last_wrong, answered)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(qid) DO UPDATE SET
                    times_right = times_right + excluded.times_right,
                    times_wrong = times_wrong + excluded.times_wrong,
                    last_wrong = excluded.last_wrong,
                    answered = 1
            """, (qid, int(correct), int(not correct), int(not correct)))

    def save_attempt(self, score: int, wrong: int, total: int, passed: bool, restarted: bool, seconds: int,
                     misses: Iterable[Miss]) -> int:
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO attempts (test_date, score, wrong, total, passed, restarted, seconds)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (date, score, wrong, total, int(passed), int(restarted), seconds))
            attempt_id = int(cur.lastrowid)
            conn.executemany(
                "INSERT INTO wrong_questions (attempt_id, test_date, qid, question, your_answer, correct_answer,"
                " explanation, chapter) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [(attempt_id, date, m.qid, m.question, m.your_answer, m.correct_answer, m.explanation, m.chapter)
                 for m in misses])
        return attempt_id

    def attempts(self) -> list[dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            return [dict(r) for r in conn.execute("SELECT * FROM attempts ORDER BY id")]

    def wrong_history(self, limit: Optional[int] = 50) -> list[dict]:
        sql = ("SELECT question, your_answer, correct_answer, explanation, chapter, test_date FROM wrong_questions"
               " ORDER BY id DESC")
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql + (" LIMIT ?" if limit else ""), (limit,) if limit else ())
            return [dict(r) for r in rows]

    def export_wrong_csv(self, path: Path) -> int:
        rows = self.wrong_history(limit=None)
        if not rows:
            return 0
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Question", "Your Answer", "Correct Answer", "Explanation", "Chapter", "Date"])
            for r in rows:
                writer.writerow([r["question"], r["your_answer"], r["correct_answer"], r["explanation"],
                                 r["chapter"], r["test_date"]])
        return len(rows)

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM wrong_questions")
            conn.execute("DELETE FROM attempts")
            conn.execute("DELETE FROM question_stats")


def build_order(bank: list[dict], stats: dict, rng: random.Random) -> list[dict]:
    """Missed last time first, then never answered, then already answered right; each group shuffled."""
    missed, unseen, known = [], [], []
    for q in bank:
        s = stats.get(q["id"])
        if s is None or s[3] == 0:
            unseen.append(q)
        elif s[2] == 1:
            missed.append(q)
        else:
            known.append(q)
    for group in (missed, unseen, known):
        rng.shuffle(group)
    return missed + unseen + known


@dataclass
class Attempt:
    """One run through the whole bank. Scoring happens as you move off a question, like the permit test."""

    questions: list[dict]
    store: ProgressStore
    max_wrong: int = MAX_WRONG
    answers: list[int] = field(init=False)
    scored: list[bool] = field(init=False)
    scored_right: list[bool] = field(init=False)
    locked: list[bool] = field(init=False)
    misses: list[Miss] = field(init=False, default_factory=list)
    current: int = 0
    finished: bool = False
    restart_needed: bool = False
    seconds: int = 0

    def __post_init__(self) -> None:
        n = len(self.questions)
        self.answers = [-1] * n
        self.scored = [False] * n
        self.scored_right = [False] * n
        self.locked = [False] * n

    @property
    def wrong_count(self) -> int:
        return len(self.misses)

    @property
    def total(self) -> int:
        return len(self.questions)

    def question(self) -> dict:
        return self.questions[self.current]

    def _miss(self, i: int) -> Miss:
        q = self.questions[i]
        ans = self.answers[i]
        return Miss(i + 1, q["id"], q["question"], q["options"][ans] if ans != -1 else "(no answer)",
                    q["options"][q["correct"]], q["explanation"], q["chapter"])

    def _check_limit(self) -> bool:
        if self.wrong_count > self.max_wrong and not self.restart_needed:
            self.restart_needed = True
            self.store.save_attempt(self.score(), self.wrong_count, self.total, False, True, self.seconds,
                                    self.misses)
        return self.restart_needed

    def select(self, option: int) -> bool:
        """Choose an answer for the current question. Returns True if this forces a restart."""
        if self.finished or self.restart_needed or self.locked[self.current]:
            return self.restart_needed
        if not 0 <= option < len(self.question()["options"]):
            raise ValueError(f"option {option} out of range")
        i = self.current
        if self.answers[i] == option:
            return False
        self.answers[i] = option
        if self.scored[i]:
            q = self.questions[i]
            now_right = option == q["correct"]
            if now_right != self.scored_right[i]:
                self.scored_right[i] = now_right
                self.store.record(q["id"], now_right)
                self.misses = [m for m in self.misses if m.number != i + 1]
                if not now_right:
                    self.misses.append(self._miss(i))
            elif not now_right:
                self.misses = [m if m.number != i + 1 else self._miss(i) for m in self.misses]
            return self._check_limit()
        return False

    def answer(self, option: int) -> dict:
        """Pick an answer. A wrong pick is scored and locked at once so the right answer can be shown."""
        if self.finished or self.restart_needed or self.locked[self.current]:
            return {"right": None, "restart": self.restart_needed}
        restart = self.select(option)
        right = option == self.question()["correct"]
        if not right:
            restart = self._score(self.current) or restart
            self.locked[self.current] = True
        return {"right": right, "restart": restart}

    def _score(self, i: int) -> bool:
        if self.scored[i] or self.answers[i] == -1:
            return False
        self.scored[i] = True
        q = self.questions[i]
        right = self.answers[i] == q["correct"]
        self.scored_right[i] = right
        self.store.record(q["id"], right)
        if not right:
            self.misses.append(self._miss(i))
        return self._check_limit()

    def move(self, step: int) -> bool:
        """Score the current question, then go forward/back. Returns True if the test must restart."""
        if self.finished or self.restart_needed:
            return self.restart_needed
        if self._score(self.current):
            return True
        self.current = max(0, min(self.total - 1, self.current + step))
        return False

    def score(self) -> int:
        return sum(1 for i, q in enumerate(self.questions) if self.answers[i] == q["correct"])

    def unanswered(self) -> int:
        return sum(1 for a in self.answers if a == -1)

    def finish(self) -> dict:
        """Score everything left (blank counts as wrong) and save the attempt."""
        if self.finished:
            raise RuntimeError("attempt already finished")
        for i in range(self.total):
            if self.scored[i]:
                continue
            self.scored[i] = True
            q = self.questions[i]
            right = self.answers[i] == q["correct"]
            self.scored_right[i] = right
            if self.answers[i] != -1:
                self.store.record(q["id"], right)
            if not right:
                self.misses.append(self._miss(i))
        self.finished = True
        passed = self.wrong_count <= self.max_wrong
        self.store.save_attempt(self.score(), self.wrong_count, self.total, passed, False, self.seconds, self.misses)
        return {"score": self.score(), "wrong": self.wrong_count, "total": self.total, "passed": passed}
