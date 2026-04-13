"""Tests for the markdown-to-Confluence converter."""

import os
import tempfile
from pathlib import Path

import pytest

from markdown_to_confluence.converter import MarkdownToConfluenceConverter, ConversionResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def converter(tmp_path):
    """Return a converter that skips the local mermaid CLI."""
    return MarkdownToConfluenceConverter(
        mermaid_output_dir=str(tmp_path),
        use_local_mermaid_cli=False,
    )


def write_md(tmp_path: Path, filename: str, content: str) -> str:
    p = tmp_path / filename
    p.write_text(content)
    return str(p)


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------

class TestHeadings:
    def test_h1(self, converter):
        result = converter._markdown_to_html("# Hello World")
        assert "<h1>Hello World</h1>" in result

    def test_h2(self, converter):
        result = converter._markdown_to_html("## Section Two")
        assert "<h2>Section Two</h2>" in result

    def test_h6(self, converter):
        result = converter._markdown_to_html("###### Deep Heading")
        assert "<h6>Deep Heading</h6>" in result


# ---------------------------------------------------------------------------
# Inline formatting
# ---------------------------------------------------------------------------

class TestInlineFormatting:
    def test_bold_asterisk(self, converter):
        assert "<strong>text</strong>" in converter._inline("**text**")

    def test_bold_underscore(self, converter):
        assert "<strong>text</strong>" in converter._inline("__text__")

    def test_italic_asterisk(self, converter):
        assert "<em>text</em>" in converter._inline("*text*")

    def test_italic_underscore(self, converter):
        assert "<em>text</em>" in converter._inline("_text_")

    def test_inline_code(self, converter):
        assert "<code>snippet</code>" in converter._inline("`snippet`")

    def test_strikethrough(self, converter):
        assert "<del>gone</del>" in converter._inline("~~gone~~")

    def test_link(self, converter):
        result = converter._inline("[GitHub](https://github.com)")
        assert '<a href="https://github.com">GitHub</a>' in result

    def test_inline_image(self, converter):
        result = converter._inline("![alt](https://example.com/img.png)")
        assert 'ri:value="https://example.com/img.png"' in result


# ---------------------------------------------------------------------------
# Code blocks
# ---------------------------------------------------------------------------

class TestCodeBlocks:
    def test_fenced_code_block_python(self, converter):
        md = "```python\nprint('hello')\n```"
        result = converter._markdown_to_html(md)
        assert 'ac:name="code"' in result
        assert 'language">python' in result
        assert "print('hello')" in result

    def test_fenced_code_block_no_lang(self, converter):
        md = "```\nsome code\n```"
        result = converter._markdown_to_html(md)
        assert 'ac:name="code"' in result
        assert "some code" in result


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

class TestLists:
    def test_unordered_list(self, converter):
        md = "- item one\n- item two\n- item three"
        result = converter._markdown_to_html(md)
        assert "<ul>" in result
        assert "<li>item one</li>" in result
        assert "<li>item three</li>" in result

    def test_ordered_list(self, converter):
        md = "1. first\n2. second\n3. third"
        result = converter._markdown_to_html(md)
        assert "<ol>" in result
        assert "<li>first</li>" in result
        assert "<li>third</li>" in result


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class TestTables:
    def test_basic_table(self, converter):
        md = "| Name | Age |\n|------|-----|\n| Alice | 30 |\n| Bob | 25 |"
        result = converter._markdown_to_html(md)
        assert "<table>" in result
        assert "<th>Name</th>" in result
        assert "<td>Alice</td>" in result
        assert "<td>25</td>" in result

    def test_table_ends_correctly(self, converter):
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = converter._markdown_to_html(md)
        assert "</table>" in result


# ---------------------------------------------------------------------------
# Horizontal rule / blockquote
# ---------------------------------------------------------------------------

class TestMiscElements:
    def test_horizontal_rule(self, converter):
        result = converter._markdown_to_html("---")
        assert "<hr/>" in result

    def test_blockquote(self, converter):
        result = converter._markdown_to_html("> A quoted line")
        assert "<blockquote>" in result
        assert "A quoted line" in result


# ---------------------------------------------------------------------------
# Mermaid diagrams
# ---------------------------------------------------------------------------

class TestMermaidDiagrams:
    def test_mermaid_block_replaced_with_image_tag(self, converter):
        md = "# Title\n\n```mermaid\ngraph TD\n  A --> B\n```\n"
        body, attachments = converter._convert(md)
        # With no local CLI, should fall back to mermaid.ink URL
        assert "<ac:image>" in body
        assert "mermaid" not in body.lower() or "ac:image" in body

    def test_mermaid_ink_url_fallback(self, converter):
        """When the local CLI is unavailable the output uses mermaid.ink."""
        md = "```mermaid\ngraph LR\n  X --> Y\n```"
        body, attachments = converter._convert(md)
        assert "mermaid.ink" in body
        assert len(attachments) == 0  # no local files when using URL fallback


# ---------------------------------------------------------------------------
# Title extraction
# ---------------------------------------------------------------------------

class TestTitleExtraction:
    def test_extracts_first_h1(self, converter):
        md = "# My Design Doc\n\nSome text\n\n## Subsection"
        assert converter._extract_title(md) == "My Design Doc"

    def test_returns_none_when_no_h1(self, converter):
        md = "## Only H2\n\nNo H1 here."
        assert converter._extract_title(md) is None


# ---------------------------------------------------------------------------
# convert_file
# ---------------------------------------------------------------------------

class TestConvertFile:
    def test_convert_file_returns_result(self, converter, tmp_path):
        md_file = write_md(tmp_path, "design.md", "# My Design\n\nHello world.\n")
        result = converter.convert_file(str(md_file))
        assert isinstance(result, ConversionResult)
        assert result.title == "My Design"
        assert "<p>" in result.body

    def test_title_from_filename_when_no_h1(self, converter, tmp_path):
        md_file = write_md(tmp_path, "api-guide.md", "No heading here.\n")
        result = converter.convert_file(str(md_file))
        assert result.title == "Api Guide"


# ---------------------------------------------------------------------------
# Sections (multiple files)
# ---------------------------------------------------------------------------

class TestSections:
    def test_sections_returns_single_result(self, converter, tmp_path):
        f1 = write_md(tmp_path, "a.md", "# Alpha\n\nContent A.\n")
        f2 = write_md(tmp_path, "b.md", "# Beta\n\nContent B.\n")
        result = converter.convert_files_as_sections([f1, f2])
        assert isinstance(result, ConversionResult)

    def test_sections_uses_expand_macro(self, converter, tmp_path):
        f1 = write_md(tmp_path, "a.md", "# Alpha\n\nContent A.\n")
        f2 = write_md(tmp_path, "b.md", "# Beta\n\nContent B.\n")
        result = converter.convert_files_as_sections([f1, f2])
        assert 'ac:name="expand"' in result.body
        assert "Alpha" in result.body
        assert "Beta" in result.body

    def test_sections_title_from_first_file(self, converter, tmp_path):
        f1 = write_md(tmp_path, "first.md", "# First Title\n\nContent.\n")
        f2 = write_md(tmp_path, "second.md", "# Second Title\n\nMore content.\n")
        result = converter.convert_files_as_sections([f1, f2])
        assert result.title == "First Title"
