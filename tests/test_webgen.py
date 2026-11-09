import json
import re

from ethical_hacking_test.engine import MAX_WRONG
from ethical_hacking_test.question_bank import build_bank
from ethical_hacking_test.webgen import render_html


def test_web_bank_matches_python_bank():
    html = render_html(build_bank())
    data = json.loads(re.search(r"const BANK=(\[.*?\]);\n", html, re.S).group(1))
    bank = build_bank()
    assert [d["id"] for d in data] == [q["id"] for q in bank]
    assert all(d["c"] == q["correct"] and d["o"] == q["options"] for d, q in zip(data, bank))
    assert f"const MAX_WRONG={MAX_WRONG};" in html
    assert "const REVEAL_MS=8000;" in html and "function pick(" in html
    assert "__" not in html.replace("__proto__", "")


def test_no_script_breakout():
    bank = build_bank()
    bank[0]["question"] = "</script><b>x"
    html = render_html(bank)
    assert html.count("</script>") == 1


def test_web_radio_matches_station_list():
    from ethical_hacking_test.radio import STATIONS
    html = render_html(build_bank())
    data = json.loads(re.search(r"const STATIONS=(\[.*?\]);", html).group(1))
    assert [d["n"] for d in data] == [s.name for s in STATIONS]
    assert [d["u"] for d in data] == [list(s.urls) for s in STATIONS]
    assert html.index('id="radio"') < html.index("<script>")


def test_no_leftover_tax_deed_branding():
    import re
    from ethical_hacking_test import app, study_guide
    html = render_html([])
    page = re.sub(r"const STATIONS=.*?;", "", html, flags=re.S)
    for text in (page, app.APP_TITLE, study_guide.STUDY_GUIDE_HTML):
        for word in ("Georgia", "tax deed", "Tax Deed", "code liens", "real estate", "attorney"):
            assert word not in text, word
    assert "written permission" in html
