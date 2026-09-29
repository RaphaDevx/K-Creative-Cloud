#!/usr/bin/env python3
"""
1. Merge My DJ Stick 0.5 content → K-DJ Archiv folder
2. BPM-analyze all K-DJ Set tracks
3. Re-sort mismatches into correct phase folders by BPM

BPM ranges (from dj_set_tracks phase definitions):
  01_Warmup_Indie_Pop     : 100–126 BPM
  02_Latin_Reggaeton      : 124–130 BPM (overlaps warmup)
  03_French_Touch_Groove  : 126–128 BPM
  04_Abriss_Mitsing       : 128–132 BPM
  05_90s_Rave_Classics    : 128–135 BPM
  06_Techno_Bootlegs      : 135–145 BPM
  07_Trance_Eurodance     : 142–148 BPM
  08_Hard_Techno_Schranz  : 150–175 BPM
"""
import shutil
import time
from pathlib import Path

STICK       = Path("/mnt/kdj")
KDJ_SET     = STICK / "K-DJ Set"
KDJ_ARCHIV  = STICK / "K-DJ Archiv"
AUDIO_EXTS  = {".mp3", ".wav", ".flac", ".m4a", ".aiff"}

PHASE_FOLDERS = {
    "01_Warmup_Indie_Pop":      (80,  127),
    "02_Latin_Reggaeton":       (80,  131),
    "03_French_Touch":          (124, 132),
    "04_Abriss_Hymnen":         (126, 136),
    "05_90s_Rave_Classics":     (128, 140),
    "06_Techno_Bootlegs":       (132, 148),
    "07_Trance_Eurodance":      (138, 152),
    "08_Hard_Techno_Schranz":   (148, 200),
}

# Phase priority order for BPM assignment (most distinctive first)
# When BPM falls in multiple ranges, pick the most appropriate phase
BPM_PHASE_ORDER = [
    ("08_Hard_Techno_Schranz",  148, 200),
    ("07_Trance_Eurodance",     140, 152),
    ("06_Techno_Bootlegs",      133, 148),
    ("05_90s_Rave_Classics",    128, 140),
    ("04_Abriss_Hymnen",        126, 135),
    ("03_French_Touch",         124, 132),
    ("02_Latin_Reggaeton",       95, 130),
    ("01_Warmup_Indie_Pop",      80, 127),
]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ─── Step 1: Merge 0.5 content ───────────────────────────────────────────────

def step1_merge_05():
    log("── Step 1: My DJ Stick 0.5 → K-DJ Archiv ──")

    # Find the My DJ Stick folder (has unicode char in name)
    dj_stick_folder = None
    for item in STICK.iterdir():
        if "My DJ Stick" in item.name and item.is_dir():
            dj_stick_folder = item
            break

    if not dj_stick_folder:
        log("  ! 'My DJ Stick' folder not found — skipping")
        return

    log(f"  Found: {dj_stick_folder.name!r}")

    KDJ_ARCHIV.mkdir(exist_ok=True)

    moved = 0
    for subfolder in sorted(dj_stick_folder.iterdir()):
        if not subfolder.is_dir():
            continue

        mp3s = [f for f in subfolder.rglob("*") if f.suffix.lower() in AUDIO_EXTS
                and not f.name.startswith("._") and f.stat().st_size > 500_000]

        if not mp3s:
            log(f"  Skip empty: {subfolder.name}")
            continue

        dest_folder = KDJ_ARCHIV / subfolder.name
        dest_folder.mkdir(exist_ok=True)

        for f in mp3s:
            dst = dest_folder / f.name
            if dst.exists():
                continue
            try:
                shutil.copy2(f, dst)
                moved += 1
            except Exception as e:
                log(f"  ! Copy error {f.name}: {e}")

    log(f"  ✓ {moved} tracks → K-DJ Archiv")

    # Clean up empty artist folders in My DJ Stick (keep Aus DJ Stick 0.5)
    deleted_dirs = 0
    for subfolder in sorted(dj_stick_folder.iterdir()):
        if not subfolder.is_dir():
            continue
        audio_count = sum(1 for f in subfolder.rglob("*")
                         if f.suffix.lower() in AUDIO_EXTS and f.stat().st_size > 500_000)
        if audio_count == 0:
            try:
                shutil.rmtree(subfolder)
                deleted_dirs += 1
            except Exception:
                pass

    log(f"  ✓ {deleted_dirs} empty artist folders removed from My DJ Stick")


# ─── Step 2: BPM Analysis ────────────────────────────────────────────────────

def detect_bpm(path: Path) -> float | None:
    try:
        import librosa
        y, sr = librosa.load(str(path), duration=60, mono=True, res_type="kaiser_fast")
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo[0]) if hasattr(tempo, "__len__") else float(tempo)
        # librosa sometimes returns half/double tempo — normalize to 100-200 range
        while bpm < 80:
            bpm *= 2
        while bpm > 200:
            bpm /= 2
        return round(bpm, 1)
    except Exception as e:
        return None


def bpm_to_phase(bpm: float) -> str | None:
    for phase, lo, hi in BPM_PHASE_ORDER:
        if lo <= bpm < hi:
            return phase
    if bpm < 80:
        return "01_Warmup_Indie_Pop"
    return "08_Hard_Techno_Schranz"


def step2_bpm_sort():
    log("── Step 2: BPM Analysis & Re-Sort ──")

    if not KDJ_SET.exists():
        log("  ! K-DJ Set not found")
        return

    # Gather all tracks
    all_tracks: list[tuple[str, Path]] = []
    for phase_dir in sorted(KDJ_SET.iterdir()):
        if not phase_dir.is_dir():
            continue
        for f in sorted(phase_dir.iterdir()):
            if f.suffix.lower() in AUDIO_EXTS and not f.name.startswith("._"):
                all_tracks.append((phase_dir.name, f))

    log(f"  {len(all_tracks)} tracks to analyze (this takes a few minutes)...")

    moved = 0
    errors = 0
    results = []

    for i, (current_phase, track_path) in enumerate(all_tracks, 1):
        bpm = detect_bpm(track_path)
        if bpm is None:
            log(f"  [{i:3d}/{len(all_tracks)}] BPM?  {track_path.name[:55]}")
            errors += 1
            results.append((current_phase, track_path, None, current_phase))
            continue

        target_phase = bpm_to_phase(bpm)
        results.append((current_phase, track_path, bpm, target_phase))

        match_icon = "✓" if target_phase == current_phase else "→"
        log(f"  [{i:3d}/{len(all_tracks)}] {bpm:5.1f} BPM  {match_icon}  {track_path.name[:55]}")

    # Print summary of mismatches
    log("\n  ── Mismatches to re-sort ──")
    mismatches = [(c, p, b, t) for c, p, b, t in results if t != c and b is not None]
    log(f"  {len(mismatches)} tracks need moving")

    for current_phase, track_path, bpm, target_phase in mismatches:
        target_dir = KDJ_SET / target_phase
        if not target_dir.exists():
            log(f"  ! Target dir missing: {target_dir}")
            continue

        dst = target_dir / track_path.name
        if dst.exists():
            log(f"  Skip (exists): {track_path.name[:50]}")
            track_path.unlink()  # remove duplicate from wrong phase
            moved += 1
            continue

        try:
            shutil.move(str(track_path), dst)
            log(f"  Moved {bpm:.0f} BPM: [{current_phase}] → [{target_phase}] {track_path.name[:45]}")
            moved += 1
        except Exception as e:
            log(f"  ! Move error {track_path.name}: {e}")

    log(f"\n  ✓ {moved} tracks moved | {errors} BPM errors")


# ─── Step 3: Remove duplicates within K-DJ Set ──────────────────────────────

def step3_dedupe():
    log("── Step 3: Remove duplicates in K-DJ Set ──")
    seen: dict[str, Path] = {}
    removed = 0

    for phase_dir in sorted(KDJ_SET.iterdir()):
        if not phase_dir.is_dir():
            continue
        for f in sorted(phase_dir.iterdir()):
            if f.suffix.lower() not in AUDIO_EXTS:
                continue
            key = f.name.lower()
            if key in seen:
                log(f"  Duplicate: {f.name[:55]} — removing from {phase_dir.name}")
                try:
                    f.unlink()
                    removed += 1
                except Exception:
                    pass
            else:
                seen[key] = f

    log(f"  ✓ {removed} duplicates removed")


# ─── Step 4: Report ──────────────────────────────────────────────────────────

def step4_report():
    log("── Step 4: Final Status ──")
    total = 0
    for phase_dir in sorted(KDJ_SET.iterdir()):
        if not phase_dir.is_dir():
            continue
        tracks = [f for f in phase_dir.iterdir() if f.suffix.lower() in AUDIO_EXTS]
        log(f"  {phase_dir.name}: {len(tracks)} tracks")
        total += len(tracks)

    archiv_total = sum(1 for f in KDJ_ARCHIV.rglob("*") if f.suffix.lower() in AUDIO_EXTS) if KDJ_ARCHIV.exists() else 0
    log(f"\n  K-DJ Set: {total} tracks total")
    log(f"  K-DJ Archiv: {archiv_total} tracks (old DJ Stick 0.5)")

    free_gb = shutil.disk_usage(STICK).free / 1e9
    log(f"  Free space: {free_gb:.2f} GB")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not STICK.exists():
        print("✗ Stick not mounted at /mnt/kdj")
        raise SystemExit(1)

    step1_merge_05()
    step3_dedupe()  # dedupe before BPM analysis (fewer files to process)
    step2_bpm_sort()
    step4_report()

    log("✓ Done.")
