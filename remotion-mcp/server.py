"""
K-Creative-Cloud Remotion MCP Server
Creates animated 1080x1920 educational shorts via Remotion + Kokoro TTS.
"""
import json
import sys
import os
from pathlib import Path

VENV_SITE = "/storage/projekte/ki_pipeline_env_312/lib/python3.12/site-packages"
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.fastmcp import FastMCP
from render_remotion import create_remotion_short

mcp = FastMCP("remotion-shorts")


@mcp.tool()
def create_animated_reel(
    topic: str,
    voice: str = "am_adam",
    format: str = "portrait",
    output_name: str = "",
    extra_instructions: str = "",
    style: str = "minimal",
    character_id: str = "default",
) -> str:
    """
    Create a fully animated ~100-second educational reel using Remotion.
    Produces 1080x1920 MP4 with spring() physics animations and Kokoro TTS voiceover.

    Args:
        topic: Topic to explain (e.g. "Forschungsdesign qualitativ vs quantitativ ESF HSG")
        voice: TTS voice — am_adam (deep male), af_heart (warm female), bm_george (British professor)
        format: "portrait" (1080x1920 Reels/TikTok) or "landscape" (1920x1080 YouTube)
        output_name: Custom filename (auto-generated from topic if empty)
        extra_instructions: Style hints (e.g. "focus on exam relevance")
        style: Visual style — "minimal" (default dark), "2D" (cartoon + lip sync), "kinetic" (bold text), "3D" (depth cards)
        character_id: For style=2D — character variant: "default", "dark", "light", "cool"

    Returns:
        JSON with output path, render time, token usage, scene count, style used
    """
    result = create_remotion_short(
        topic=topic,
        voice=voice,
        format=format,
        output_name=output_name,
        extra_instructions=extra_instructions,
        style=style,
        character_id=character_id,
    )
    return json.dumps(result, indent=2)


@mcp.tool()
def list_reel_styles() -> str:
    """List available visual styles for Remotion reels."""
    styles = {
        "minimal": "Dark bg + emoji + spring animations (default)",
        "2D": "Cartoon character (Open Peeps style) + Rhubarb lip sync",
        "kinetic": "Bold word-by-word typography, no character",
        "3D": "CSS perspective depth, floating glass cards",
    }
    return json.dumps(styles, indent=2)


@mcp.tool()
def list_reel_voices() -> str:
    """List available TTS voices for Remotion reels."""
    voices = {
        "am_adam": "Deep, authoritative male — best for educational content",
        "af_heart": "Warm, expressive female — best for narrative content",
        "af_nova": "Energetic, young female — best for motivational hooks",
        "bf_emma": "British female, formal — best for academic topics",
        "bm_george": "British professor style — best for formal definitions",
        "am_echo": "Clear, neutral male — best for factual explainers",
    }
    return json.dumps(voices, indent=2)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
