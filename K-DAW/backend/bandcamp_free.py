"""Bandcamp free/NaYP download — FLAC-Qualität via $0-Checkout-Flow."""
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"

# Format-Präferenz nach Ziel-Format
_FORMAT_PREF = {
    "flac": ["flac", "wav", "aiff-lossless", "mp3-320", "mp3-v0"],
    "wav":  ["wav", "flac", "aiff-lossless", "mp3-320"],
    "mp3":  ["mp3-320", "mp3-v0", "vorbis", "aac-hi", "flac"],
}
_EXT_MAP = {
    "flac": "flac", "wav": "wav", "aiff-lossless": "aiff",
    "mp3-320": "mp3", "mp3-v0": "mp3", "vorbis": "ogg", "aac-hi": "m4a",
}
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def is_bandcamp(url: str) -> bool:
    return "bandcamp.com" in url


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(_HEADERS)
    return s


def _get_tralbum(sess: requests.Session, url: str) -> tuple[dict, BeautifulSoup]:
    r = sess.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    el = soup.find(attrs={"data-tralbum": True})
    if not el:
        raise ValueError("Kein Bandcamp-Tralbum auf dieser Seite")
    return json.loads(el["data-tralbum"]), soup


def _safe_filename(artist: str, title: str, ext: str) -> str:
    name = f"{artist} - {title}" if artist else title
    name = re.sub(r'[^\w\s\-]', '', name).strip()[:80]
    return f"{name}.{ext}"


def _stream_download(sess: requests.Session, url: str, dest: Path, job: dict):
    with sess.get(url, stream=True, timeout=120, allow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                done += len(chunk)
                if total:
                    job["progress"] = f"[download] {done * 100 // total}% von {total // 1048576}MB"


def _links_from_dl_page(soup: BeautifulSoup, base: str) -> dict[str, str]:
    """Extract enc→URL from a Bandcamp download page."""
    links = {}
    for a in soup.find_all("a", href=re.compile(r"/download/(track|album)")):
        href = a.get("href", "")
        enc = re.search(r"enc=([^&]+)", href)
        if enc:
            full = urljoin(base, href)
            links[enc.group(1)] = full
    return links


def _pick_and_download(
    sess: requests.Session,
    links: dict[str, str],
    fmt: str,
    tralbum: dict,
    job: dict,
) -> bool:
    prefs = _FORMAT_PREF.get(fmt, _FORMAT_PREF["mp3"])
    chosen_enc = next((p for p in prefs if p in links), None)
    if not chosen_enc:
        chosen_enc = next(iter(links), None)
    if not chosen_enc:
        return False

    chosen_url = links[chosen_enc]
    ext = _EXT_MAP.get(chosen_enc, "mp3")
    artist = tralbum.get("artist", "")
    title = (tralbum.get("current") or {}).get("title", "bandcamp_track")
    filename = _safe_filename(artist, title, ext)
    dest = DOWNLOADS_DIR / filename

    job["progress"] = f"Bandcamp {chosen_enc.upper()} — lade {filename}..."
    _stream_download(sess, chosen_url, dest, job)
    job["files"].append(filename)
    job["status"] = "done"
    job["progress"] = f"Fertig ({chosen_enc.upper()})"
    return True


# ─── Öffentliche Funktion ────────────────────────────────────────────────────

def try_bandcamp_free(url: str, fmt: str, job: dict) -> bool:
    """
    Versucht kostenlosen Bandcamp-Download (Free oder NaYP mit $0).
    Gibt True zurück wenn erfolgreich, False wenn yt-dlp Fallback nötig.
    """
    sess = _session()

    try:
        tralbum, soup = _get_tralbum(sess, url)
    except Exception as e:
        job["progress"] = f"Bandcamp-Seite nicht lesbar ({e}) — versuche yt-dlp..."
        return False

    item_type = tralbum.get("item_type", "track")
    current = tralbum.get("current") or {}

    # ── Fall 1: Direkte Free-Download-Seite (kein Email nötig) ──────────────
    free_dl_page = tralbum.get("freeDownloadPage")
    if free_dl_page:
        job["progress"] = "Free-Download-Seite gefunden — lade FLAC..."
        try:
            r = sess.get(free_dl_page, timeout=30)
            dl_soup = BeautifulSoup(r.text, "lxml")
            links = _links_from_dl_page(dl_soup, "https://bandcamp.com")
            if links:
                return _pick_and_download(sess, links, fmt, tralbum, job)
        except Exception as e:
            job["progress"] = f"Free-Page Fehler ({e}) — versuche yt-dlp..."
            return False

    # ── Fall 2: Name-Your-Price mit Mindestpreis $0 ──────────────────────────
    min_price = current.get("minimum_price") or current.get("minimum_price_nonzero")
    is_purchasable = tralbum.get("is_purchasable", False)
    is_nyp = is_purchasable and (min_price == 0 or min_price is None)

    if not is_nyp:
        job["progress"] = "Kein Free Download verfügbar — versuche yt-dlp..."
        return False

    job["progress"] = "Name-Your-Price ($0) erkannt — starte Checkout..."

    item_id = tralbum.get("id")
    type_char = "t" if item_type == "track" else "a"
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    # Crumb (CSRF-Token) aus der Seite holen
    crumb_el = soup.find("meta", attrs={"name": "bc-crumb"})
    crumb = crumb_el["content"] if crumb_el else ""

    try:
        r = sess.post(
            "https://bandcamp.com/checkout_redeemer",
            data={
                "email_addr": "download@k-daw.local",
                "email_confirm": "download@k-daw.local",
                "fan_id": "",
                "item_id": str(item_id),
                "item_type": type_char,
                "unit_price": "0",
                "currency": "USD",
                "quantity": "1",
                "option": "",
                "crumb": crumb,
            },
            headers={
                "Referer": url,
                "Origin": origin,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
        )
        data = r.json()
    except Exception as e:
        job["progress"] = f"Checkout fehlgeschlagen ({e}) — versuche yt-dlp..."
        return False

    dl_url = data.get("download_url") or data.get("url")
    if not dl_url:
        job["progress"] = "Checkout: kein Download-Link erhalten — versuche yt-dlp..."
        return False

    # Download-Seite laden und Links extrahieren
    try:
        r = sess.get(dl_url, timeout=30)
        dl_soup = BeautifulSoup(r.text, "lxml")
        links = _links_from_dl_page(dl_soup, dl_url)
        if links:
            return _pick_and_download(sess, links, fmt, tralbum, job)
    except Exception as e:
        job["progress"] = f"Download-Seite Fehler ({e}) — versuche yt-dlp..."

    return False


def get_bandcamp_info(url: str) -> dict:
    """Gibt Infos zurück (Titel, Artist, Typ, ob Free/NaYP) ohne herunterzuladen."""
    sess = _session()
    try:
        tralbum, _ = _get_tralbum(sess, url)
    except Exception as e:
        return {"error": str(e)}

    current = tralbum.get("current") or {}
    min_price = current.get("minimum_price") or current.get("minimum_price_nonzero") or 0
    is_purchasable = tralbum.get("is_purchasable", False)
    free_dl = bool(tralbum.get("freeDownloadPage"))
    is_nyp = is_purchasable and min_price == 0

    tracks = tralbum.get("trackinfo") or []

    return {
        "title": current.get("title", ""),
        "artist": tralbum.get("artist", ""),
        "item_type": tralbum.get("item_type", "track"),
        "track_count": len(tracks),
        "is_free": free_dl,
        "is_nyp": is_nyp,
        "min_price": min_price,
        "available": free_dl or is_nyp,
    }
