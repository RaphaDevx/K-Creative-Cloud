# Video Shorts MCP — Setup

## Was es macht

Gibt dir das Tool `create_video_short(topic)` — Claude Haiku schreibt das Script,
Kokoro TTS (lokal) spricht es ein, FFmpeg rendert das fertige Video.

```
Dein Befehl → Claude Haiku (Script) → Kokoro TTS (Voice) → Pillow (Frames) → FFmpeg (Video)
```

## Einmaliger Setup: API-Key

```bash
nano ~/.config/kcloud/.env
# Eintragen:
ANTHROPIC_API_KEY=sk-ant-dein-echter-key
```

## MCP-Server starten

Im K-Creative-Cloud-Ordner `claude` starten — `video-shorts` lädt automatisch.

## Nutzung in Claude

```
"Erstelle einen Short über Quantenverschränkung"
"Make a video short about why habits take 66 days"
"Create a portrait short about the Pareto principle, voice: am_adam"
```

## Verfügbare Stimmen

| Voice | Stil |
|-------|------|
| `af_heart` | Warm, expressiv, weiblich (Standard) |
| `af_nova` | Energetisch, jung, weiblich |
| `am_adam` | Tief, autoritativ, männlich |
| `am_echo` | Klar, neutral, männlich |
| `bf_emma` | Britisch, formal, weiblich |
| `bm_george` | Britisch, Professor-Stil |

## Token-Kosten pro Video

| Modell | Tokens | Kosten |
|--------|--------|--------|
| Claude Haiku | ~1300 | ~$0.001 |
| Claude Sonnet | ~1300 | ~$0.006 |

→ **1000 Videos = ~$1 mit Haiku**

## Output-Pfad

```
~/renders/shorts/[topic].mp4
```

## Technischer Stack

- **Script:** Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
- **TTS:** Kokoro ONNX v0.5 (lokal, offline, Modell: 89MB)
- **Frames:** Pillow (Python), 1080×1920 PNG
- **Assembly:** FFmpeg 8.0 (fade in/out per Szene, AAC audio)
- **Format:** H.264 MP4, Portrait 1080×1920
