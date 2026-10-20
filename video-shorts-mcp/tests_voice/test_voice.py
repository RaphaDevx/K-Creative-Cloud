import os, sys, tempfile, wave
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
HOME = Path(__file__).resolve().parents[2] / "voice-data"
from voice.segment import segment, load_lexicon

LEX = load_lexicon(HOME / "lexicon.json")


def test_mixed_sentence_splits_english_terms():
    s = segment("Der Safety Stock schützt vor Nachfrageschwankungen.", LEX)
    assert [x.lang for x in s] == ["de", "en", "de"]
    assert s[1].text.lower() == "safety stock"


def test_explicit_markup():
    s = segment("Das nennt man {en:Backorder} im Lager.", LEX)
    assert any(x.lang == "en" and x.text == "Backorder" for x in s)


def test_english_sentence_stays_english():
    s = segment("This is the reorder point and it is simple.", LEX)
    assert [x.lang for x in s] == ["en"]


def test_german_sentence_stays_german():
    s = segment("Das ist der Meldebestand und er ist einfach.", LEX)
    assert [x.lang for x in s] == ["de"]


def test_synth_end_to_end_and_lock(tmp_path, monkeypatch):
    monkeypatch.setenv("K_CREATIVE_VOICE_HOME", str(tmp_path))
    (tmp_path / "lexicon.json").write_text((HOME / "lexicon.json").read_text())
    from voice import registry, synthesize
    v = {"de": {"engine": "piper", "voice": "de_DE-thorsten-medium", "params": {}},
         "en": {"engine": "kokoro", "voice": "am_adam", "params": {}}}
    registry.create_persona("prof", "Prof", v)
    registry.bind_channel("kanal", "prof")
    out = tmp_path / "a.wav"
    meta = synthesize("Der Safety Stock schützt dich.", str(out), channel="kanal")
    assert out.exists() and meta["duration"] > 1.0
    assert {s["lang"] for s in meta["segments"]} == {"de", "en"}
    assert out.with_suffix(".voice.json").exists()
