"""
K-Creative-Cloud Video Shorts MCP Server
Creates 100-second educational viral short videos via Claude + Kokoro TTS + FFmpeg.
"""
import json
import sys
import os

# Use the venv that has kokoro_onnx, Pillow, anthropic, soundfile
VENV_SITE = "/storage/projekte/ki_pipeline_env_312/lib/python3.12/site-packages"
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from pipeline import create_short
from tts_kokoro import AVAILABLE_VOICES

mcp = FastMCP("video-shorts")


@mcp.tool()
def create_video_short(
    topic: str,
    voice: str = "af_heart",
    format: str = "portrait",
    output_name: str = "",
    extra_instructions: str = "",
) -> str:
    """
    Create a ~100-second fast-paced educational short video on any topic.
    Uses Claude Haiku for script + Kokoro TTS (local) + FFmpeg.

    Args:
        topic: What the video should explain (e.g. "Quantum Entanglement", "Why habits form", "Bitcoin explained")
        voice: TTS voice — af_heart (warm female), am_adam (deep male), bf_emma (British female)
        format: "portrait" (1080x1920, for Shorts/TikTok) or "landscape" (1920x1080, for YouTube)
        output_name: Custom filename (default: auto-generated from topic)
        extra_instructions: Optional style hints (e.g. "focus on neuroscience angle", "use analogies")

    Returns:
        JSON with output path, token usage, render time, and scene summary
    """
    result = create_short(
        topic=topic,
        voice=voice,
        format=format,
        output_name=output_name if output_name else "",
        extra_instructions=extra_instructions,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def list_voices() -> str:
    """
    List available TTS voices for video shorts.
    Returns JSON with voice names and descriptions.
    """
    return json.dumps(AVAILABLE_VOICES, indent=2)


@mcp.tool()
def estimate_tokens(topic_length_words: int = 5) -> str:
    """
    Estimate token cost for creating a video short.

    Args:
        topic_length_words: Approximate word count of your topic prompt

    Returns:
        JSON with token estimate and approximate cost in USD
    """
    input_est = 460 + topic_length_words * 1.3
    output_est = 850
    total = int(input_est + output_est)
    return json.dumps({
        "estimated_tokens": {
            "input": int(input_est),
            "output": output_est,
            "total": total,
        },
        "model": "claude-haiku-4-5-20251001",
        "cost_usd": {
            "haiku": round(total * 0.000001, 5),
            "sonnet": round(total * 0.000006, 5),
        },
        "note": "Actual output varies ~±200 tokens depending on topic complexity",
    })


def main():
    mcp.run()


if __name__ == "__main__":
    main()
