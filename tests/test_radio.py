import urllib.error
import urllib.request

import ssl

import pytest

from ethical_hacking_test.radio import DEFAULT_VOLUME, STATIONS, RadioState


def test_requested_atlanta_stations_present():
    names = [s.name for s in STATIONS]
    assert "V-103" in names and "Hot 107.9" in names
    assert all(s.urls and all(u.startswith("https://") for u in s.urls) for s in STATIONS)


def test_step_wraps_both_ways(tmp_path):
    r = RadioState(tmp_path / "radio.json")
    assert r.index == 0
    assert r.step(-1) == STATIONS[-1]
    assert r.step(1) == STATIONS[0]
    assert r.select(len(STATIONS) + 1) == STATIONS[1]


def test_volume_clamped(tmp_path):
    r = RadioState(tmp_path / "radio.json")
    assert r.volume == DEFAULT_VOLUME
    assert r.set_volume(150) == 100 and r.set_volume(-5) == 0


def test_choice_remembered(tmp_path):
    path = tmp_path / "radio.json"
    r = RadioState(path)
    r.select(1)
    r.set_volume(35)
    again = RadioState(path)
    assert again.index == 1 and again.volume == 35


@pytest.mark.parametrize("content", ["not json", '{"index": 99, "volume": 500}', "[]"])
def test_bad_saved_state_falls_back(tmp_path, content):
    path = tmp_path / "radio.json"
    path.write_text(content)
    r = RadioState(path)
    assert 0 <= r.index < len(STATIONS) and 0 <= r.volume <= 100


def test_no_stations_rejected():
    with pytest.raises(ValueError):
        RadioState(stations=())


def _tls_context() -> ssl.SSLContext:
    """Some Windows Python installs miss intermediate roots that browsers and Qt trust; certifi has them."""
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _is_offline(error: str) -> bool:
    return any(k in error for k in ("getaddrinfo", "Name or service", "timed out", "Network is unreachable",
                                    "No route to host", "Connection refused"))


@pytest.mark.parametrize("station", STATIONS, ids=[s.name for s in STATIONS])
def test_station_stream_is_live_audio(station):
    """Real network check: at least one stream URL answers with audio."""
    errors = []
    for url in station.urls:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-2047"})
        try:
            with urllib.request.urlopen(req, timeout=10, context=_tls_context()) as resp:
                kind = resp.headers.get("Content-Type", "")
                data = resp.read(2048)
            if kind.startswith("audio/") and len(data) > 512:
                return
            errors.append(f"{url}: {kind}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            errors.append(f"{url}: {e}")
    if all(_is_offline(e) for e in errors):
        pytest.skip("no network: " + "; ".join(errors))
    pytest.fail("; ".join(errors))
