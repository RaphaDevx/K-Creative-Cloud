#!/usr/bin/env python3
"""
K-DJ Stick Organizer — automatische Bereinigung + Phasen-Struktur
1. Mac-Müll löschen (.DS_Store, ._*)
2. Duplikate aus 'My DJ Stick 0.5' entfernen (die auch in v1 sind)
3. Einzigartige 0.5-Tracks in v1 integrieren
4. K-DJ Set Phasen-Ordner erstellen + neue Downloads einsortieren
"""
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dj_set_tracks import PHASES, all_tracks

STICK     = Path("/mnt/kdj")
DOWNLOADS = Path(__file__).parent.parent / "downloads"
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".aiff", ".opus"}

PHASE_FOLDERS = {
    "1_WARMUP_INDIE_POP":     "01_Warmup_Indie_Pop",
    "2_LATIN_REGGAETON":      "02_Latin_Reggaeton",
    "3_FRENCH_TOUCH_GROOVE":  "03_French_Touch",
    "4_ABRISS_MITSING":       "04_Abriss_Hymnen",
    "5_90s_RAVE_CLASSICS":    "05_90s_Rave_Classics",
    "6_TECHNO_BOOTLEGS":      "06_Techno_Bootlegs",
    "7_FAST_TRANCE_EURODANCE":"07_Trance_Eurodance",
    "8_HARD_TECHNO_SCHRANZ":  "08_Hard_Techno_Schranz",
}


def _find_dir(pattern: str) -> Path | None:
    for d in STICK.iterdir():
        if pattern in d.name and d.is_dir() and not d.name.startswith('.'):
            return d
    return None


def _audio_files(folder: Path) -> dict[str, Path]:
    """Normalisierter-Name → Pfad mapping."""
    def norm(s): return re.sub(r'[^\w]', '', s.lower())
    return {
        norm(f.stem): f
        for f in folder.rglob('*')
        if f.suffix.lower() in AUDIO_EXTS and not f.name.startswith('._')
        and f.stat().st_size > 500_000
    }


def _free_gb() -> float:
    return shutil.disk_usage(STICK).free / 1e9


def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ─────────────────────────────────────────────────────────────────────────────

def step1_clean_stick():
    log("── Step 1: Stick bereinigen (non-MP3 + Mac-Müll) ──")
    deleted = 0
    freed_mb = 0

    # Alles löschen was kein MP3 ist: vdjstems, WAV, FLAC, FL-Studio, Installer, etc.
    # Ausnahme: Verzeichnisse und .mp3 bleiben
    KEEP_EXTS = {".mp3"}
    SKIP_NAMES = {"._", ".DS_Store"}

    for f in STICK.rglob("*"):
        if not f.is_file():
            continue
        if any(f.name.startswith(s) for s in SKIP_NAMES) or f.name == ".DS_Store":
            freed_mb += f.stat().st_size / 1e6
            try:
                f.unlink()
                deleted += 1
            except Exception:
                pass
            continue
        if f.suffix.lower() not in KEEP_EXTS:
            freed_mb += f.stat().st_size / 1e6
            try:
                f.unlink()
                deleted += 1
            except Exception:
                pass

    # Leere Ordner löschen
    for d in sorted(STICK.rglob("*"), reverse=True):
        if d.is_dir() and d != STICK:
            try:
                d.rmdir()  # nur wenn leer
            except Exception:
                pass

    log(f"  ✓ {deleted} Dateien gelöscht ({freed_mb:.0f} MB)  |  Frei: {_free_gb():.2f} GB")


def step2_dedupe_v05():
    log("── Step 2: Duplikate aus 'My DJ Stick 0.5' entfernen ──")
    v1  = _find_dir("DJ Stick") if not _find_dir("0.5") else None
    # Robust: finde v1 (kein 0.5) und v05
    v1  = next((d for d in STICK.iterdir() if 'DJ Stick' in d.name and '0.5' not in d.name and d.is_dir() and not d.name.startswith('.')), None)
    v05 = next((d for d in STICK.iterdir() if '0.5' in d.name and d.is_dir() and not d.name.startswith('.')), None)

    if not v1 or not v05:
        log("  ! Ordner nicht gefunden — übersprungen")
        return

    v1_map  = _audio_files(v1)
    v05_map = _audio_files(v05)

    dupes  = set(v1_map) & set(v05_map)
    unique = set(v05_map) - set(v1_map)

    log(f"  v1: {len(v1_map)} Tracks  |  0.5: {len(v05_map)} Tracks")
    log(f"  Duplikate (sicher löschbar): {len(dupes)}")
    log(f"  Unikal in 0.5 (→ v1 integrieren): {len(unique)}")

    # Duplikate aus 0.5 löschen (bereits in v1 vorhanden)
    removed_mb = 0
    for k in dupes:
        f = v05_map[k]
        removed_mb += f.stat().st_size / 1e6
        try:
            f.unlink()
        except Exception as e:
            log(f"  ! Fehler beim Löschen {f.name}: {e}")

    log(f"  ✓ {len(dupes)} Duplikate gelöscht ({removed_mb:.0f} MB)  |  Frei: {_free_gb():.2f} GB")

    # Unikal-0.5-Tracks → "My DJ Stick/Aus 0.5"
    if unique:
        dest_folder = v1 / "Aus DJ Stick 0.5"
        dest_folder.mkdir(exist_ok=True)
        moved = 0
        for k in unique:
            src = v05_map[k]
            dst = dest_folder / src.name
            if not dst.exists():
                try:
                    shutil.move(str(src), dst)
                    moved += 1
                except Exception as e:
                    log(f"  ! Move-Fehler {src.name}: {e}")
        log(f"  ✓ {moved} unikal-0.5-Tracks → {dest_folder.name}")

    # Leere 0.5-Ordner aufräumen
    for d in sorted(v05.rglob('*'), reverse=True):
        if d.is_dir():
            try:
                d.rmdir()
            except Exception:
                pass


def step3_copy_dj_set():
    log("── Step 3: DJ-Set Tracks → Phasen-Ordner ──")
    free = _free_gb()
    log(f"  Freier Platz vor Copy: {free:.2f} GB")

    if free < 0.5:
        log("  ! Zu wenig Platz — bitte manuell Speicher freigeben")
        return

    phase_root = STICK / "K-DJ Set"
    phase_root.mkdir(exist_ok=True)

    def norm(s): return re.sub(r'[^\w]', '', s.lower())

    def find_download(artist: str, title: str) -> Path | None:
        words_t = [w for w in re.sub(r'[^\w\s]', ' ', title.lower()).split() if len(w) > 2]
        words_a = [w for w in re.sub(r'[^\w\s]', ' ', artist.lower()).split() if len(w) > 2]
        best, best_score = None, 0
        for f in DOWNLOADS.iterdir():
            if f.suffix.lower() not in AUDIO_EXTS:
                continue
            if f.stat().st_size < 2_000_000:
                continue
            fn = norm(f.stem)
            score = sum(2 for w in words_t if w in fn) + sum(1 for w in words_a if w in fn)
            if score > best_score:
                best_score, best = score, f
        return best if best_score >= 2 else None

    copied = skipped = missing = 0
    for phase_key, artist, title, _ in all_tracks():
        folder = phase_root / PHASE_FOLDERS.get(phase_key, phase_key)
        folder.mkdir(exist_ok=True)

        src = find_download(artist, title)
        if not src:
            missing += 1
            continue

        dst = folder / src.name
        if dst.exists():
            skipped += 1
            continue

        if _free_gb() < 0.1:
            log(f"  ! Kein Platz mehr — stoppe bei {artist} — {title}")
            break
        try:
            shutil.copy2(src, dst)
            copied += 1
        except Exception as e:
            log(f"  ! {src.name}: {e}")

    log(f"  ✓ {copied} kopiert  |  {skipped} bereits vorhanden  |  {missing} noch nicht geladen")
    log(f"  Freier Platz nach Copy: {_free_gb():.2f} GB")


def step4_report():
    log("── Step 4: Status-Report ──")
    phase_root = STICK / "K-DJ Set"
    if not phase_root.exists():
        log("  Keine K-DJ Set Ordner vorhanden")
        return

    total = 0
    for phase_folder in sorted(phase_root.iterdir()):
        if not phase_folder.is_dir():
            continue
        tracks = [f for f in phase_folder.iterdir() if f.suffix.lower() in AUDIO_EXTS]
        log(f"  {phase_folder.name}: {len(tracks)} Tracks")
        total += len(tracks)

    log(f"\n  Gesamt im K-DJ Set: {total} Tracks")
    log(f"  Freier Platz: {_free_gb():.2f} GB")


def main():
    if not STICK.exists():
        print(f"✗ Stick nicht gemountet: {STICK}")
        sys.exit(1)

    log(f"K-DJ Stick Organizer gestartet  |  Frei: {_free_gb():.2f} GB")

    step1_clean_stick()
    step2_dedupe_v05()
    step3_copy_dj_set()
    step4_report()

    log("✓ Alle Schritte abgeschlossen.")


if __name__ == "__main__":
    main()
