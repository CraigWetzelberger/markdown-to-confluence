"""Mermaid diagram to image conversion."""

import base64
import os
import subprocess
import tempfile
import urllib.parse
from pathlib import Path


def render_mermaid_to_file(mermaid_code: str, output_path: str) -> bool:
    """Render a mermaid diagram to a PNG file using the mermaid CLI (mmdc).

    Returns True on success, False otherwise.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as f:
        f.write(mermaid_code)
        input_file = f.name

    try:
        result = subprocess.run(
            ["mmdc", "-i", input_file, "-o", output_path, "--backgroundColor", "white"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    finally:
        try:
            os.unlink(input_file)
        except OSError:
            pass


def mermaid_ink_url(mermaid_code: str) -> str:
    """Build a mermaid.ink URL for online diagram rendering.

    This is used as a fallback when the local mermaid CLI is unavailable.
    """
    encoded = base64.urlsafe_b64encode(mermaid_code.encode()).decode()
    return f"https://mermaid.ink/img/{encoded}"


class MermaidProcessor:
    """Handle extraction and rendering of mermaid diagrams from markdown content."""

    def __init__(self, output_dir: str | None = None, use_local_cli: bool = True):
        self.output_dir = output_dir or tempfile.mkdtemp(prefix="mermaid_")
        self.use_local_cli = use_local_cli
        self._counter = 0
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def process(self, mermaid_code: str, label: str = "diagram") -> tuple[str, str]:
        """Process a mermaid code block and return (image_path_or_url, media_type).

        Returns:
            A tuple of (path_or_url, kind) where kind is "file" or "url".
        """
        self._counter += 1
        safe_label = "".join(c if c.isalnum() else "_" for c in label)
        filename = f"{safe_label}_{self._counter}.png"
        output_path = os.path.join(self.output_dir, filename)

        if self.use_local_cli and render_mermaid_to_file(mermaid_code, output_path):
            return output_path, "file"

        # Fallback: online rendering URL
        return mermaid_ink_url(mermaid_code), "url"
