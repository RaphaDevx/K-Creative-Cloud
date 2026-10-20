"""Zerlegt Text in Sprachsegmente (de/en), damit englische Fachbegriffe englisch gesprochen werden.

Reihenfolge der Entscheidung (deterministisch, ohne Netz):
1. Explizites Markup  {en:Safety Stock}  /  {de:Lieferzeit}
2. Lexikon (lexicon.json: "en_terms") — Mehrwortbegriffe zuerst, ohne Gross-/Kleinschreibung
3. Basissprache des Satzes via langid (auf de/en eingeschränkt)
"""
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

_MARK = re.compile(r"\{(en|de):([^{}]+)\}")
_SENT = re.compile(r"(?<=[.!?:;])\s+|\n+")


@dataclass(frozen=True)
class Segment:
    lang: str
    text: str


def voice_home() -> Path:
    default = Path(__file__).resolve().parents[2] / "voice-data"
    return Path(os.environ.get("K_CREATIVE_VOICE_HOME", default))


def load_lexicon(path: Path | None = None) -> dict:
    p = path or voice_home() / "lexicon.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"en_terms": [], "pronounce": {}}


def sentence_lang(text: str) -> str:
    import langid
    langid.set_languages(["de", "en"])
    return langid.classify(text)[0]


def _split_terms(text: str, lang: str, terms: list[str]) -> list[Segment]:
    if lang != "de" or not terms:
        return [Segment(lang, text)] if text.strip() else []
    pat = re.compile(r"\b(" + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)) + r")\b", re.I)
    out, pos = [], 0
    for m in pat.finditer(text):
        if text[pos:m.start()].strip():
            out.append(Segment("de", text[pos:m.start()]))
        out.append(Segment("en", m.group(0)))
        pos = m.end()
    if text[pos:].strip():
        out.append(Segment("de", text[pos:]))
    return out


def segment(text: str, lexicon: dict | None = None, base: str | None = None) -> list[Segment]:
    lex = lexicon if lexicon is not None else load_lexicon()
    terms = lex.get("en_terms", [])
    segs: list[Segment] = []
    for sent in _SENT.split(text.strip()):
        if not sent.strip():
            continue
        pos, parts = 0, []
        for m in _MARK.finditer(sent):  # explizites Markup
            if sent[pos:m.start()].strip():
                parts.append((None, sent[pos:m.start()]))
            parts.append((m.group(1), m.group(2)))
            pos = m.end()
        if sent[pos:].strip():
            parts.append((None, sent[pos:]))
        plain = " ".join(t for l, t in parts if l is None)
        sl = base or (sentence_lang(plain) if plain.strip() else "de")
        for lang, chunk in parts:
            if lang:
                segs.append(Segment(lang, chunk))
            else:
                segs.extend(_split_terms(chunk, sl, terms))
    merged: list[Segment] = []
    for s in segs:  # gleiche Nachbarsprachen zusammenfassen
        if merged and merged[-1].lang == s.lang:
            merged[-1] = Segment(s.lang, merged[-1].text.rstrip() + " " + s.text.lstrip())
        else:
            merged.append(s)
    return merged


def apply_pronunciation(text: str, lang: str, lexicon: dict) -> str:
    for src, dst in (lexicon.get("pronounce", {}).get(lang, {})).items():
        text = re.sub(r"\b" + re.escape(src) + r"\b", dst, text)
    return text
