"""Tests for the mermaid module."""

import base64
import os

import pytest

from markdown_to_confluence.mermaid import MermaidProcessor, mermaid_ink_url


SIMPLE_GRAPH = "graph TD\n  A --> B"


class TestMermaidInkUrl:
    def test_returns_mermaid_ink_url(self):
        url = mermaid_ink_url(SIMPLE_GRAPH)
        assert url.startswith("https://mermaid.ink/img/")

    def test_url_contains_encoded_content(self):
        url = mermaid_ink_url(SIMPLE_GRAPH)
        token = url.split("/img/")[1]
        decoded = base64.urlsafe_b64decode(token).decode()
        assert SIMPLE_GRAPH in decoded


class TestMermaidProcessor:
    @pytest.fixture()
    def processor(self, tmp_path):
        """Processor with local CLI disabled so tests don't need mmdc."""
        return MermaidProcessor(output_dir=str(tmp_path), use_local_cli=False)

    def test_fallback_returns_url(self, processor):
        result, kind = processor.process(SIMPLE_GRAPH)
        assert kind == "url"
        assert result.startswith("https://mermaid.ink/img/")

    def test_counter_increments(self, processor):
        _, _ = processor.process(SIMPLE_GRAPH)
        _, _ = processor.process(SIMPLE_GRAPH)
        assert processor._counter == 2

    def test_output_dir_created(self, tmp_path):
        output = str(tmp_path / "sub" / "dir")
        proc = MermaidProcessor(output_dir=output, use_local_cli=False)
        proc.process(SIMPLE_GRAPH)
        assert os.path.isdir(output)
