"""Claude API → Music JSON with prompt caching."""
import json
import re
import anthropic

client = anthropic.Anthropic()

_SYSTEM = """You are a music composition AI. Return ONLY a valid JSON object — no markdown, no explanation.

JSON schema:
{
  "title": "string",
  "bpm": 90-160,
  "key": "C"|"D"|"E"|"F"|"G"|"A"|"B" with optional "b"/"#",
  "mode": "major"|"minor"|"dorian"|"phrygian",
  "description": "string (1-2 sentences)",
  "tracks": [
    {
      "name": "string",
      "channel": 0-15,
      "program": 0-127,
      "notes": [
        {"pitch": 0-127, "velocity": 40-120, "start_beat": 0.0, "duration_beats": 0.25-4.0}
      ]
    }
  ]
}

MIDI pitch reference (middle octave): C4=60 D4=62 E4=64 F4=65 G4=67 A4=69 B4=71 C5=72
MIDI programs: 0=Piano 4=Rhodes 24=NylonGuitar 25=SteelGuitar 32=AcousticBass
               33=FingerBass 40=Violin 48=Strings 73=Flute 80=SquareLead 88=Pad

Composition rules:
- Generate 8-16 bars (32-64 beats in 4/4)
- Use 3-4 tracks: melody + chords + bass (+ optional percussion on channel 9)
- Bass register: pitches 36-52 (C2-E3), program 32 or 33
- Chord register: pitches 48-72 (C3-C5)
- Melody register: pitches 60-84 (C4-C6)
- Chord rhythm: 4 chords per bar (each 1 beat) OR half-bar chords (2 beats)
- Create 2-bar phrases that repeat with variation
- Melody should have a clear shape (rise-fall-cadence)
- Add dynamics: vary velocity between notes (soft=50, medium=80, accent=110)
- Percussion channel 9: pitch 36=kick 38=snare 42=hihat_closed 46=hihat_open
- Return ONLY the JSON object"""


def generate_music(prompt: str) -> dict:
    """Call Claude API with cached system prompt, return parsed music dict."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=[{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Strip markdown fences if Claude wraps the JSON
    text = re.sub(r"^```[a-z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return json.loads(text)
