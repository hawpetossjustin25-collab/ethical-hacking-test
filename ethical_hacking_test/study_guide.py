"""Plain-language study guide shown in the app's Study Guide tab."""

STUDY_GUIDE_HTML = """
<h2>0. The rule that matters most</h2>
<ul><li>Only test systems you <b>own</b> or have <b>written authorization</b> (signed scope / rules of engagement) to
test. Without it, even a simple scan can be a crime under the Computer Fraud and Abuse Act (18 U.S.C. 1030).</li>
<li>Legal places to practice: your own virtual-machine lab, Hack The Box, TryHackMe, PortSwigger Web Security
Academy, OWASP Juice Shop, and official bug bounty programs (stay inside their scope).</li></ul>
<h2>1. Beginner: the fundamentals</h2>
<ul><li><b>CIA triad</b>: Confidentiality, Integrity, Availability. <b>AAA</b>: Authentication, Authorization,
Accounting.</li>
<li>Vulnerability = weakness; exploit = what abuses it; payload = what runs after; risk = likelihood x impact.</li>
<li>Networking: OSI layers, IP (L3) vs MAC (L2), TCP (reliable, handshake) vs UDP (fast), common ports 21 FTP,
22 SSH, 23 Telnet, 25 SMTP, 53 DNS, 80 HTTP, 443 HTTPS, 445 SMB, 3389 RDP.</li>
<li>Crypto: symmetric (AES, one key) vs asymmetric (RSA/ECC, key pair); hashing (SHA-256) is one-way;
salt + slow hash (bcrypt/Argon2) for passwords; TLS protects data in transit.</li></ul>
<h2>2. Intermediate: the methodology</h2>
<ol><li><b>Reconnaissance</b> - passive (OSINT, WHOIS, DNS, Google dorks, Shodan) and active.</li>
<li><b>Scanning &amp; enumeration</b> - Nmap (-sS SYN, -sV versions, -O OS), banner grabbing, SMB/DNS
enumeration, vulnerability scanners (Nessus, OpenVAS, Nikto).</li>
<li><b>Gaining access</b> - exploiting a confirmed weakness (Metasploit, web flaws, weak passwords).</li>
<li><b>Maintaining access</b> - persistence, privilege escalation (vertical/horizontal), lateral movement,
pivoting.</li>
<li><b>Reporting</b> - ethical testers do not hide tracks from the client; they document findings, evidence, risk
and fixes.</li></ol>
<h2>3. Advanced: attack families and their fixes</h2>
<ul><li>Web (OWASP Top 10): SQL injection -> parameterized queries; XSS -> output encoding + CSP; CSRF -> tokens +
SameSite cookies; IDOR -> server-side authorization checks; SSRF, command injection, directory traversal.</li>
<li>Network/wireless: MITM, ARP and DNS spoofing, SYN floods and DDoS, rogue/evil-twin APs, WEP is broken, WPA2
handshakes can be cracked offline if the passphrase is weak - use WPA3 and long passphrases.</li>
<li>Passwords: brute force, dictionary, spraying, credential stuffing, rainbow tables (beaten by salt),
pass-the-hash. MFA is the biggest single fix.</li>
<li>Malware: virus, worm, trojan, ransomware, rootkit, spyware, botnet, logic bomb.</li>
<li>Social engineering: phishing, spear phishing, whaling, vishing, smishing, pretexting, baiting,
tailgating.</li>
<li>Memory: buffer overflows; defenses ASLR, DEP, stack canaries, bounds checking.</li></ul>
<h2>4. Defense and incident response</h2>
<ul><li>Patch fast, least privilege, defense in depth, zero trust, segmentation, MFA, EDR, logging to a SIEM,
offline tested backups.</li>
<li>NIST incident response: Preparation; Detection &amp; Analysis; Containment, Eradication &amp; Recovery;
Post-Incident lessons learned. Preserve evidence and chain of custody.</li>
<li>Responsible disclosure: report privately, give the vendor time to fix, then disclose.</li></ul>
<h2>5. What you can do once you know more</h2>
<ul><li><b>Bug bounties</b> (HackerOne, Bugcrowd, Intigriti): get paid for flaws you report, but only inside the
program's scope. Duplicates usually pay nothing; read the rules first.</li>
<li><b>CTFs</b>: legal competitions (picoCTF to start, DEF CON CTF at the top). Jeopardy = separate puzzles;
attack-defense = attack other teams while defending your own.</li>
<li><b>Jobs</b>: SOC analyst (usual first job), penetration tester, red team, blue team, purple team, threat hunter,
incident responder, forensics examiner, malware analyst, AppSec engineer, cloud security engineer, GRC.</li>
<li><b>Specialties</b>: cloud (IAM and misconfiguration), mobile apps and APIs, IoT/hardware firmware, cars (CAN
bus), physical testing (always with a signed authorization letter), exploit development.</li>
<li><b>Certifications path</b>: Security+ -> PenTest+ / CEH / eJPT -> OSCP; CISSP later for leadership.</li>
<li><b>Portfolio</b>: home lab, CTF write-ups, disclosed CVEs, and open-source tools prove skill better than
claims. Never publish client findings without written permission.</li></ul>
<h2>6. Build a safe home lab</h2>
<ul><li>Install VirtualBox, then a Kali Linux VM (attacker) and an intentionally vulnerable VM such as
Metasploitable 2 or OWASP Juice Shop (target).</li>
<li>Put both on a <b>host-only</b> network so nothing touches your home network or the internet.</li>
<li>Work through free paths: TryHackMe "Pre Security" and "Jr Penetration Tester", PortSwigger Academy for web,
then Hack The Box. Certifications to aim for: CompTIA Security+, then PenTest+ or CEH, then OSCP.</li></ul>
"""
