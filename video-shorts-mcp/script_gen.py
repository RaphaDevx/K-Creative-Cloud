"""
Script generation via Claude Haiku — produces a tight, timestamped JSON storyboard.
~1300 tokens per video (prompt + output).
API key: set ANTHROPIC_API_KEY env var, or place in ~/.config/kcloud/.env
"""
import json
import os
from pathlib import Path
import anthropic

def _load_env_key():
    """Load API key from ~/.config/kcloud/.env if not already in environment."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env_path = Path.home() / ".config" / "kcloud" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()
                return

_load_env_key()

SYSTEM = """You are a viral educational video scriptwriter. Your videos are 100 seconds long,
fast-paced, and teach one concept clearly. Format optimized for YouTube Shorts / TikTok.

Rules:
- HOOK in first 3 seconds: shocking stat, counterintuitive fact, or bold claim
- 5-7 scenes total, each 8-18 seconds
- Every scene has: spoken text (what the voice says), headline (3-6 words MAX, ALL CAPS),
  subtext (one short clarification line), emoji (single relevant emoji)
- Language: energetic, direct, second-person ("you"), zero filler words
- Total spoken word count: ~240-280 words (fits ~100s at 150wpm with natural pauses)
- End with a punchy takeaway, not a call-to-action

Output ONLY valid JSON, no markdown, no explanation:
{
  "title": "...",
  "scenes": [
    {
      "id": 0,
      "type": "hook",
      "headline": "...",
      "subtext": "...",
      "emoji": "...",
      "spoken": "...",
      "accent_hex": "#FFD700"
    }
  ]
}

accent_hex color guide:
- hook: #FF4444 (red — shock)
- fact/stat: #FFD700 (gold — valuable info)
- explanation: #4FC3F7 (blue — clarity)
- warning/myth: #FF7043 (orange — alert)
- tip/insight: #66BB6A (green — action)
- takeaway: #CE93D8 (purple — wisdom)"""


def generate_script(topic: str, extra_instructions: str = "") -> dict:
    client = anthropic.Anthropic()
    user_prompt = f"Topic: {topic}"
    if extra_instructions:
        user_prompt += f"\nExtra: {extra_instructions}"

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1200,
        system=SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    script = json.loads(raw)
    script["_tokens"] = {
        "input": message.usage.input_tokens,
        "output": message.usage.output_tokens,
        "total": message.usage.input_tokens + message.usage.output_tokens,
    }
    return script
