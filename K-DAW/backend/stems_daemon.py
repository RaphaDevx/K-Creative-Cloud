"""
Stems-Daemon — läuft im Hintergrund, verarbeitet neue Downloads mit Demucs.
CPU-limitiert auf 50% (8 von 16 Kernen via taskset + nice).
Überwacht downloads/ und verarbeitet neue Dateien automatisch.
"""
import subprocess
import sys
import time
import logging
from pathlib import Path

DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"
STEMS_DIR     = Path(__file__).parent.parent / "stems"
MODEL         = "htdemucs_6s"
LOG_FILE      = STEMS_DIR / "stems_daemon.log"
POLL_INTERVAL = 30   # Sekunden zwischen Checks
CPU_CORES     = "0-7"  # Nur 8 von 16 Kernen (50%)
NICE_LEVEL    = 15     # Niedrige Priorität (19 = absolut niedrigste)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)

AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".aiff"}


def already_processed(path: Path) -> bool:
    stem_dir = STEMS_DIR / MODEL / path.stem
    if not stem_dir.exists():
        return False
    wavs = list(stem_dir.glob("*.wav"))
    return len(wavs) >= 5


def run_demucs(path: Path):
    log.info(f"▶ Starte Stems: {path.name}")
    start = time.time()
    cmd = [
        "taskset", "-c", CPU_CORES,
        "nice", f"-n{NICE_LEVEL}",
        sys.executable, "-m", "demucs",
        "--name", MODEL,
        "--out", str(STEMS_DIR),
        "--jobs", "4",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = int(time.time() - start)
    if result.returncode == 0:
        log.info(f"✓ Fertig ({elapsed}s): {path.name}")
    else:
        log.error(f"✗ FEHLER bei {path.name}: {result.stderr[-300:]}")


def main():
    STEMS_DIR.mkdir(parents=True, exist_ok=True)
    log.info("=" * 50)
    log.info(f"Stems-Daemon gestartet")
    log.info(f"  CPU-Kerne: {CPU_CORES}  Nice: {NICE_LEVEL}")
    log.info(f"  Modell:    {MODEL}")
    log.info(f"  Poll:      alle {POLL_INTERVAL}s")
    log.info("=" * 50)

    processed = set()

    while True:
        files = [
            f for f in DOWNLOADS_DIR.iterdir()
            if f.suffix.lower() in AUDIO_EXTS
            and f.name not in processed
            and not already_processed(f)
        ]

        if files:
            log.info(f"→ {len(files)} neue Datei(en) gefunden")
            for f in sorted(files, key=lambda x: x.stat().st_mtime):
                run_demucs(f)
                processed.add(f.name)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
