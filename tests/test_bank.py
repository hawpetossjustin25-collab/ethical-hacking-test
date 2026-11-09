from collections import Counter

from ethical_hacking_test.question_bank import (
    CAREER_MODULES, CAREER_TARGET, SKILL_TARGET, TARGET, build_bank, chapter_counts, core_questions, facts,
    question_id,
)

CAREER_CHAPTERS = ("Career Paths & Jobs", "Bug Bounty & CTFs", "Specialties & Advanced Practice")


def test_bank_size_and_unique():
    bank = build_bank()
    assert len(bank) == TARGET == 1200
    assert len({q["id"] for q in bank}) == len(bank)
    assert len({(q["question"], tuple(q["options"])) for q in bank}) == len(bank)


def test_every_question_valid():
    for q in build_bank():
        assert len(q["options"]) == 4 and len(set(q["options"])) == 4, q["question"]
        assert 0 <= q["correct"] < 4
        assert q["question"].strip() and q["explanation"].strip() and q["chapter"].strip()
        assert q["id"] == question_id(q)


def test_ids_stable_between_builds():
    assert [q["id"] for q in build_bank()] == [q["id"] for q in build_bank()]


def test_all_core_questions_included():
    ids = {q["id"] for q in build_bank()}
    for q in core_questions():
        assert question_id(q) in ids


def test_answer_positions_balanced():
    counts = Counter(q["correct"] for q in build_bank())
    assert all(counts[i] >= 150 for i in range(4)), counts


def test_facts_well_formed():
    for stem, correct, wrongs, explanation, chapter in facts():
        assert len(wrongs) == 3 and correct not in wrongs and len(set(wrongs)) == 3, stem


def test_chapters_cover_all_topics():
    chapters = chapter_counts(build_bank())
    for needed in ("Security Fundamentals", "Cryptography", "Networking", "Hacking Methodology", "Reconnaissance",
                   "Scanning & Enumeration", "Tools of the Trade", "Web Attacks", "Network & Wireless Attacks",
                   "Passwords & Access Attacks", "Malware & Social Engineering", "Defense & Hardening",
                   "Incident Response & Monitoring", "Law & Ethics") + CAREER_CHAPTERS:
        assert chapters.get(needed, 0) >= 30, chapters


def test_key_security_facts_present():
    text = " ".join(q["question"] + " " + " ".join(q["options"]) + " " + q["explanation"] for q in build_bank())
    for fact in ("CIA", "SQL injection", "parameterized", "XSS", "Nmap", "Metasploit", "Burp Suite", "phishing",
                 "privilege", "written authorization", "Computer Fraud and Abuse Act", "NIST", "salt"):
        assert fact in text, fact


def test_exactly_200_career_questions():
    bank = build_bank()
    career = [q for q in bank if q["chapter"] in CAREER_CHAPTERS]
    assert SKILL_TARGET == 1000 and CAREER_TARGET == 200
    assert len(career) == 200
    assert all(q["chapter"] in CAREER_CHAPTERS for q in bank[SKILL_TARGET:])
    assert not any(q["chapter"] in CAREER_CHAPTERS for q in bank[:SKILL_TARGET])


def test_skill_questions_unchanged_by_career_set():
    """Saved progress is keyed by question id, so adding the career set must not change the first 1000."""
    assert [q["id"] for q in build_bank()[:SKILL_TARGET]] == [q["id"] for q in build_bank(career_count=0)]


def test_career_answer_positions_spread():
    counts = Counter(q["correct"] for q in build_bank()[SKILL_TARGET:])
    assert all(counts[i] >= 35 for i in range(4)), counts
    core = Counter(q["correct"] for q in core_questions(CAREER_MODULES))
    assert len(core) == 4, core


def test_career_topics_present():
    text = " ".join(q["question"] + " " + " ".join(q["options"]) + " " + q["explanation"]
                    for q in build_bank()[SKILL_TARGET:])
    for fact in ("bug bounty", "scope", "CTF", "red team", "blue team", "purple", "SOC", "OSCP", "Security+",
                 "Hack The Box", "forensics", "malware", "cloud", "portfolio", "safe harbor"):
        assert fact.lower() in text.lower(), fact
