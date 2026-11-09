# Ethical Hacking & Cybersecurity Practice Test

Adaptive 1,200-question practice test that teaches hacking from beginner to advanced the way the
CompTIA Security+ / PenTest+ and EC-Council CEH certifications do: terms, the penetration-testing methodology,
tools, attack types and their fixes, defense, incident response, and the law and ethics of authorized testing.

Phone/web version: https://hawpetossjustin25-collab.github.io/ethical-hacking-test/

## Topics
Security fundamentals, cryptography, networking, hacking methodology, reconnaissance, scanning & enumeration,
tools of the trade (Nmap, Wireshark, Metasploit, Burp Suite, Kali, Hashcat...), web attacks (OWASP Top 10),
network & wireless attacks, password attacks, malware & social engineering, defense & hardening, incident
response, law & ethics, plus 200 questions on what you can legally do once you know more: careers
(pentester, red/blue/purple team, SOC, forensics, malware analysis), bug bounties, CTFs and specialties
(cloud, mobile, IoT, cars, exploit development). A Study Guide tab includes a safe home-lab setup.

## How the test works
- All 1,200 questions every run. Max 15 wrong; the 16th wrong answer restarts the test instantly.
- Miss a question and the right answer and explanation are shown for 8 seconds, then the next question comes up.
- Missed questions come first next time, then unseen ones, then ones you already know. Progress is saved (SQLite).
- Wrong Answers tab with explanations and CSV export.
- Radio player bar at the bottom (V-103, Hot 107.9, Majic 107.5/97.5).

## Run
```
pip install PyQt6
python -m ethical_hacking_test
```
Web version: `python -m ethical_hacking_test.webgen` writes `index.html`.

## Develop
```
pip install -e .[test]
QT_QPA_PLATFORM=offscreen pytest
```

## Legal
Study tool only. Practice only on systems you own or have written permission to test. Unauthorized access is a
crime under the Computer Fraud and Abuse Act (18 U.S.C. 1030) and similar laws.
