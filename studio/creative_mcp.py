"""MCP stdio adapter: use the same actions as the K-Creative visual editor."""
import json
import os
import urllib.request
import urllib.error
import urllib.parse
from mcp.server.fastmcp import FastMCP

BASE = os.environ.get('K_CREATIVE_URL', 'http://127.0.0.1:47200').rstrip('/')
mcp = FastMCP('K-Creative')


def request(endpoint, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + endpoint, data=body, headers={'Content-Type': 'application/json', 'X-K-Creative-Token': os.environ.get('K_CREATIVE_TOKEN', '')})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        return {'ok': False, 'error': json.loads(exc.read()).get('detail', str(exc))}


@mcp.tool()
def creative_actions() -> dict:
    """Discover every typed editor action and its parameter schema."""
    return request('/api/creative/actions')


@mcp.tool()
def creative_execute(action: str, params: dict, project_id: str = '') -> dict:
    """Execute an editor action. UI and MCP share persisted state and undo history."""
    payload = {'action': action, 'params': params}
    if project_id:
        payload['project_id'] = project_id
    return request('/api/creative/action', payload)


@mcp.tool()
def creative_export(project_id: str, kind: str) -> dict:
    """Start real photo/audio/video export and return a job ID."""
    return request('/api/creative/export', {'project_id': project_id, 'kind': kind})


@mcp.tool()
def creative_job(job_id: str) -> dict:
    """Read export or voice-generation status and output path."""
    if not job_id.isalnum():
        return {'ok': False, 'error': 'Invalid job id'}
    return request('/api/creative/jobs/' + job_id)


@mcp.tool()
def creative_speech(text: str, provider: str = 'kokoro', voice: str = 'af_heart', speed: float = 1.0, language: str = 'en-us') -> dict:
    """Generate local speech as an editable audio asset; unavailable models fail explicitly."""
    return request('/api/creative/tts', dict(text=text, provider=provider, voice=voice, speed=speed, language=language))


@mcp.tool()
def creative_tools() -> dict:
    """Inspect installed creative programs and engine availability."""
    return request('/api/creative/tools')


@mcp.tool()
def creative_workflows(kind: str = '') -> dict:
    """Discover adapters by medium. Found tools require runtime probes;
    candidates require review and cannot be launched from this inventory.
    """
    query = '?' + urllib.parse.urlencode({'kind': kind}) if kind else ''
    return request('/api/creative/workflows' + query)


@mcp.tool()
def creative_autocut(path: str, threshold: float = 0.3) -> dict:
    """Detect scene boundaries non-destructively. Returns job with segment manifest."""
    return request('/api/creative/autocut', dict(path=path, threshold=threshold))


@mcp.tool()
def creative_blender(path: str, frame_start: int = 1, frame_end: int = 30, fps: float = 30) -> dict:
    """Render an existing editable Blender asset to a clip using local CPU."""
    return request('/api/creative/blender', dict(path=path, frame_start=frame_start, frame_end=frame_end, fps=fps))


@mcp.tool()
def creative_launch(tool: str, path: str = '') -> dict:
    """Open an installed allowlisted creative application with optional project asset."""
    return request('/api/creative/launch', dict(tool=tool, **({'path': path} if path else {})))


@mcp.tool()
def creative_generators() -> dict:
    """Inspect optional local ComfyUI availability and installed checkpoints."""
    return request('/api/creative/generators')


@mcp.tool()
def creative_generate_image(prompt: str, checkpoint: str = '', negative: str = '', seed: int = 0, width: int = 1024, height: int = 1024, steps: int = 20) -> dict:
    """Queue local AI image generation; requires an available ComfyUI checkpoint."""
    return request('/api/creative/generate/image', dict(prompt=prompt, checkpoint=checkpoint or None, negative=negative, seed=seed, width=width, height=height, steps=steps))


@mcp.tool()
def creative_generate_workflow(workflow: dict) -> dict:
    """Queue a model-specific ComfyUI image/video workflow, returning actual output assets."""
    return request('/api/creative/generate/workflow', {'workflow': workflow})


@mcp.tool()
def creative_lmms_export(project_id: str, render: bool = True) -> dict:
    """Create an editable LMMS DAW project and optionally render its real instrument audio."""
    return request('/api/creative/lmms', dict(project_id=project_id, render=render))


if __name__ == '__main__':
    mcp.run(transport='stdio')
