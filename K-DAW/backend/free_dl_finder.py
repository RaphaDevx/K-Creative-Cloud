"""
Scannt YouTube/SoundCloud Beschreibungen nach Free-Download-Links.
Probiert die gefundenen Links in Qualitäts-Reihenfolge:
  1. Bandcamp (FLAC/WAV via Free-Flow)
  2. Google Drive / Dropbox / Mediafire (Direktdownload)
  3. Hypeddit / Toneden / SendOwl (scrape Redirect)
  4. Direkte .mp3/.wav/.flac URLs
"""
import re
import requests
from pathlib import Path
from bs4 import BeautifulSoup

DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Muster die auf Free-Download-Links hinweisen
_FREE_PATTERNS = [
    r'https?://[^\s<>"]+\.bandcamp\.com/[^\s<>"]+',
    r'https?://hypeddit\.com/[^\s<>"]+',
    r'https?://toneden\.io/[^\s<>"]+',
    r'https?://drive\.google\.com/[^\s<>"]+',
    r'https?://www\.dropbox\.com/[^\s<>"]+',
    r'https?://www\.mediafire\.com/[^\s<>"]+',
    r'https?://[^\s<>"]+\.(mp3|wav|flac|aiff|zip)[^\s<>"]*',
    r'https?://sendowl\.com/[^\s<>"]+',
    r'https?://soundcloud\.com/[^\s<>"]+/s-[A-Za-z0-9]+',  # SoundCloud secret URLs
]

_FREE_KEYWORDS = [
    'free download', 'free dl', '[free]', 'freedownload',
    'free.dl', 'gratis download', 'kostenlos',
]


def find_free_links(description: str) -> list[str]:
    """Gibt alle potenziellen Free-Download-Links aus einer Beschreibung zurück."""
    if not description:
        return []
    desc_lower = description.lower()

    # Nur suchen wenn "free" o.ä. erwähnt
    has_free_hint = any(kw in desc_lower for kw in _FREE_KEYWORDS) or \
                    'download' in desc_lower or 'dl' in desc_lower

    links = []
    for pat in _FREE_PATTERNS:
        for m in re.finditer(pat, description, re.IGNORECASE):
            url = m.group(0).rstrip('.,;)')
            if url not in links:
                links.append(url)

    return links


def _dl_priority(url: str) -> int:
    """Niedrigere Zahl = höhere Priorität."""
    if 'bandcamp.com' in url:    return 0   # FLAC möglich
    if 'drive.google.com' in url: return 1
    if 'dropbox.com' in url:     return 1
    if 'mediafire.com' in url:   return 2
    if 'hypeddit.com' in url:    return 3
    if 'toneden.io' in url:      return 3
    if any(url.endswith(e) for e in ('.wav', '.flac', '.aiff')): return 1
    if url.endswith('.mp3'):     return 4
    return 5


def _try_direct_audio(url: str, filename_hint: str, job: dict) -> bool:
    """Lade direkte Audio-URL herunter (.mp3/.wav/.flac)."""
    ext = url.split('?')[0].rsplit('.', 1)[-1].lower()
    if ext not in {'mp3', 'wav', 'flac', 'aiff', 'm4a'}:
        return False
    dest = DOWNLOADS_DIR / f"{filename_hint}.{ext}"
    try:
        job["progress"] = f"Direktdownload {ext.upper()}: {url[:60]}..."
        with requests.get(url, headers=_HEADERS, stream=True, timeout=60, allow_redirects=True) as r:
            r.raise_for_status()
            ct = r.headers.get('content-type', '')
            if 'audio' not in ct and 'octet' not in ct and 'zip' not in ct:
                return False
            total = int(r.headers.get('content-length', 0))
            done = 0
            with open(dest, 'wb') as f:
                for chunk in r.iter_content(65536):
                    f.write(chunk)
                    done += len(chunk)
                    if total:
                        job["progress"] = f"[download] {done*100//total}% · {ext.upper()}"
        job["files"].append(dest.name)
        return True
    except Exception:
        return False


def _try_google_drive(url: str, filename_hint: str, job: dict) -> bool:
    """Google Drive Direktdownload (Bypass Virus-Warning-Seite)."""
    # Extrahiere File-ID
    m = re.search(r'/d/([A-Za-z0-9_-]+)', url) or re.search(r'id=([A-Za-z0-9_-]+)', url)
    if not m:
        return False
    file_id = m.group(1)
    dl_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    job["progress"] = f"Google Drive Download..."
    try:
        sess = requests.Session()
        sess.headers.update(_HEADERS)
        r = sess.get(dl_url, stream=True, timeout=60, allow_redirects=True)
        r.raise_for_status()
        # Dateiname aus Content-Disposition
        cd = r.headers.get('content-disposition', '')
        fn_match = re.search(r'filename[^;=\n]*=(["\']?)([^;\n"\']+)', cd)
        fname = fn_match.group(2).strip() if fn_match else f"{filename_hint}.mp3"
        dest = DOWNLOADS_DIR / fname
        total = int(r.headers.get('content-length', 0))
        done = 0
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
                done += len(chunk)
                if total:
                    job["progress"] = f"[download] {done*100//total}% · Drive"
        job["files"].append(dest.name)
        return True
    except Exception:
        return False


def _try_dropbox(url: str, filename_hint: str, job: dict) -> bool:
    """Dropbox: dl=0 → dl=1 für Direktdownload."""
    dl_url = re.sub(r'[?&]dl=0', '', url)
    dl_url += ('&' if '?' in dl_url else '?') + 'dl=1'
    return _try_direct_audio(dl_url, filename_hint, job)


def _try_hypeddit(url: str, filename_hint: str, job: dict) -> bool:
    """Hypeddit: Scrape die Secret SoundCloud URL oder den Direktlink."""
    try:
        job["progress"] = f"Hypeddit: suche Download-Link..."
        r = requests.get(url, headers=_HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, 'lxml')

        # Suche nach data-url (SoundCloud Secret URL)
        for el in soup.find_all(attrs={"data-url": True}):
            data_url = el['data-url']
            if 'soundcloud.com' in data_url and '/s-' in data_url:
                job["progress"] = f"Hypeddit → SoundCloud Secret URL gefunden"
                job["_hypeddit_sc_url"] = data_url
                return False  # Signal: yt-dlp mit dieser URL verwenden

        # Suche nach direkten Audio-Links
        for a in soup.find_all('a', href=re.compile(r'\.(mp3|wav|flac)', re.I)):
            if _try_direct_audio(a['href'], filename_hint, job):
                return True
    except Exception:
        pass
    return False


def try_free_download(description: str, fmt: str, filename_hint: str, job: dict) -> bool:
    """
    Hauptfunktion: scannt Beschreibung, probiert alle Free-Links in Qualitäts-Reihenfolge.
    Gibt True zurück wenn erfolgreich heruntergeladen.
    Sets job['_yt_override_url'] wenn ein besserer yt-dlp URL gefunden wurde.
    """
    links = find_free_links(description)
    if not links:
        return False

    # Sortiere nach Qualitäts-Priorität
    links.sort(key=_dl_priority)

    for url in links:
        job["progress"] = f"Free-DL: probiere {url[:55]}..."

        if 'bandcamp.com' in url:
            from bandcamp_free import is_bandcamp, try_bandcamp_free
            if is_bandcamp(url):
                if try_bandcamp_free(url, fmt, job):
                    return True

        elif 'drive.google.com' in url:
            if _try_google_drive(url, filename_hint, job):
                return True

        elif 'dropbox.com' in url:
            if _try_dropbox(url, filename_hint, job):
                return True

        elif 'hypeddit.com' in url:
            if _try_hypeddit(url, filename_hint, job):
                return True
            # Hypeddit hat SoundCloud Secret URL gefunden → yt-dlp damit
            sc_url = job.pop("_hypeddit_sc_url", None)
            if sc_url:
                job["_yt_override_url"] = sc_url
                return False

        elif any(url.lower().endswith(e) for e in ('.mp3', '.wav', '.flac', '.aiff')):
            if _try_direct_audio(url, filename_hint, job):
                return True

    return False
