"""Question bank builder.

build_bank() returns 1200 unique ethical-hacking / cybersecurity questions: 1000 core-skill questions plus 200 on
what you can legally do with the skills (careers, bug bounties, CTFs, specialties). Each set is built from:
  - hand-written core questions (content_*.CORE)
  - generated variants of fact entries (content_*.FACTS): reworded stems and rotated answer positions

Topics follow CompTIA Security+/Network+/PenTest+ and EC-Council CEH objectives: fundamentals, cryptography,
networking, the penetration-testing methodology, tools, attack types, defense, incident response, and the law and
ethics of authorized testing. This is a study tool; only test systems you own or are authorized in writing to test.
"""
from __future__ import annotations

import hashlib
from collections import Counter

from ethical_hacking_test import (
    content_attacks, content_career, content_defense, content_fundamentals, content_methodology,
)

SKILL_MODULES = (content_fundamentals, content_methodology, content_attacks, content_defense)
CAREER_MODULES = (content_career,)
CONTENT_MODULES = SKILL_MODULES + CAREER_MODULES
SKILL_TARGET = 1000
CAREER_TARGET = 200
TARGET = SKILL_TARGET + CAREER_TARGET

_STEM_PREFIXES = (
    "In cybersecurity, {}?",
    "For an ethical hacker, {}?",
    "On a penetration test, {}?",
    "On the exam: {}?",
)
_NO_PREFIX = ("What", "Which", "How", "When", "Who", "Why", "Where", "If ", "In ", "On ", "Under ", "At ", "A ",
              "An ", "The ", "True", "After", "Before", "During", "For ")


def _q(question: str, options: list[str], correct: int, explanation: str, chapter: str) -> dict:
    return {"question": question, "options": list(options), "correct": correct, "explanation": explanation,
            "chapter": chapter}


def core_questions(modules: tuple = CONTENT_MODULES) -> list[dict]:
    out = []
    for module in modules:
        for question, options, correct, explanation in module.CORE:
            out.append(_q(question, options, correct, explanation, module.CHAPTER_OF.get(question, module.CHAPTER)))
    return out


def facts(modules: tuple = CONTENT_MODULES) -> list[tuple]:
    out = []
    for module in modules:
        out.extend(module.FACTS)
    return out


def variants(stem: str, correct: str, wrongs: list[str], explanation: str, chapter: str,
             offset: int = 0) -> list[dict]:
    """Reworded stems x the four answer positions, ordered so each next variant moves the correct letter."""
    stems = [stem if stem.endswith("?") else stem + "?"]
    if not stem.startswith(_NO_PREFIX):
        low = stem[0].lower() + stem[1:]
        stems += [p.format(low.rstrip("?")) for p in _STEM_PREFIXES]
    out = []
    for k in range(4 * len(stems)):
        pos = (k + offset) % 4
        s = stems[k // 4]
        rotated = wrongs[pos % 3:] + wrongs[:pos % 3]
        it = iter(rotated)
        opts = [correct if i == pos else next(it) for i in range(4)]
        out.append(_q(s, opts, pos, explanation, chapter))
    return out


def question_id(q: dict) -> str:
    return hashlib.md5((q["question"] + "|" + "|".join(q["options"])).encode()).hexdigest()[:12]


def _fill(bank: list[dict], seen: set[tuple], modules: tuple, count: int) -> None:
    """Append `count` new questions from `modules`: every core question first, then fact variants round-robin."""
    goal = len(bank) + count

    def add(q: dict) -> None:
        key = (q["question"], tuple(q["options"]))
        if key in seen or len(bank) >= goal:
            return
        seen.add(key)
        q["id"] = question_id(q)
        bank.append(q)

    for q in core_questions(modules):
        add(q)
    per_fact = [variants(*f, offset=i) for i, f in enumerate(facts(modules))]
    depth = 0
    while len(bank) < goal:
        added = 0
        for vs in per_fact:
            if depth < len(vs):
                add(vs[depth])
                added += 1
            if len(bank) >= goal:
                break
        if added == 0:
            break
        depth += 1


def build_bank(skill_count: int = SKILL_TARGET, career_count: int = CAREER_TARGET) -> list[dict]:
    """Skill questions first (unchanged order and IDs, so saved progress carries over), then the career set."""
    bank: list[dict] = []
    seen: set[tuple] = set()
    _fill(bank, seen, SKILL_MODULES, skill_count)
    _fill(bank, seen, CAREER_MODULES, career_count)
    return bank


def chapter_counts(bank: list[dict]) -> dict[str, int]:
    return dict(sorted(Counter(q["chapter"] for q in bank).items()))


if __name__ == "__main__":
    b = build_bank()
    print(f"Bank size: {len(b)}  unique question texts: {len({q['question'] for q in b})}")
    for ch, n in chapter_counts(b).items():
        print(f"  {ch}: {n}")
