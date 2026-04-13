"""Convert markdown content to Confluence storage format (XHTML)."""

import re
import html
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .mermaid import MermaidProcessor


@dataclass
class ConversionResult:
    """Result of a markdown → Confluence conversion."""

    title: str
    body: str
    attachments: list[str] = field(default_factory=list)


class MarkdownToConfluenceConverter:
    """Convert markdown (including mermaid diagrams) to Confluence storage format."""

    def __init__(
        self,
        mermaid_output_dir: Optional[str] = None,
        use_local_mermaid_cli: bool = True,
    ):
        self._mermaid = MermaidProcessor(
            output_dir=mermaid_output_dir,
            use_local_cli=use_local_mermaid_cli,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert_file(self, path: str) -> ConversionResult:
        """Convert a single markdown file and return a ConversionResult."""
        p = Path(path)
        content = p.read_text(encoding="utf-8")
        title = self._extract_title(content) or p.stem.replace("-", " ").replace("_", " ").title()
        body, attachments = self._convert(content)
        return ConversionResult(title=title, body=body, attachments=attachments)

    def convert_files_as_sections(self, paths: list[str]) -> ConversionResult:
        """Combine multiple markdown files into a single Confluence page with sections.

        Each file becomes an expand/section macro titled with the file's first heading.
        """
        combined_parts: list[str] = []
        all_attachments: list[str] = []
        overall_title = "Combined Documentation"

        for idx, path in enumerate(paths):
            p = Path(path)
            content = p.read_text(encoding="utf-8")
            file_title = self._extract_title(content) or p.stem.replace("-", " ").replace("_", " ").title()

            if idx == 0:
                overall_title = file_title

            body, attachments = self._convert(content)
            all_attachments.extend(attachments)

            section_html = (
                f'<ac:structured-macro ac:name="expand">'
                f'<ac:parameter ac:name="title">{html.escape(file_title)}</ac:parameter>'
                f"<ac:rich-text-body>{body}</ac:rich-text-body>"
                f"</ac:structured-macro>"
            )
            combined_parts.append(section_html)

        return ConversionResult(
            title=overall_title,
            body="\n".join(combined_parts),
            attachments=all_attachments,
        )

    # ------------------------------------------------------------------
    # Internal conversion helpers
    # ------------------------------------------------------------------

    def _extract_title(self, content: str) -> Optional[str]:
        """Return the text of the first H1 heading, or None."""
        m = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        return m.group(1).strip() if m else None

    def _convert(self, content: str) -> tuple[str, list[str]]:
        """Convert markdown content to Confluence storage format.

        Returns (html_body, list_of_attachment_paths).
        """
        attachments: list[str] = []
        content = self._process_mermaid_blocks(content, attachments)
        body = self._markdown_to_html(content)
        return body, attachments

    # ------------------------------------------------------------------
    # Mermaid handling
    # ------------------------------------------------------------------

    def _process_mermaid_blocks(self, content: str, attachments: list[str]) -> str:
        """Replace ```mermaid blocks with Confluence image macros."""

        def replace(match: re.Match) -> str:
            code = match.group(1).strip()
            result, kind = self._mermaid.process(code)
            if kind == "file":
                attachments.append(result)
                filename = os.path.basename(result)
                return (
                    f'<ac:image><ri:attachment ri:filename="{filename}"/></ac:image>'
                )
            # URL-based fallback (mermaid.ink)
            return f'<ac:image><ri:url ri:value="{result}"/></ac:image>'

        return re.sub(
            r"```mermaid\s*\n(.*?)```",
            replace,
            content,
            flags=re.DOTALL,
        )

    # ------------------------------------------------------------------
    # Markdown → Confluence XHTML
    # ------------------------------------------------------------------

    def _markdown_to_html(self, content: str) -> str:
        """Walk through markdown lines and produce Confluence storage format HTML."""
        lines = content.splitlines()
        output: list[str] = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # ---- fenced code blocks ----
            fence_match = re.match(r"^```(\w*)$", line)
            if fence_match:
                lang = fence_match.group(1)
                code_lines: list[str] = []
                i += 1
                while i < len(lines) and not lines[i].startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                output.append(self._code_macro(lang, "\n".join(code_lines)))
                i += 1  # skip closing ```
                continue

            # ---- already-converted image tags (mermaid) ----
            if line.strip().startswith("<ac:image>"):
                output.append(line.strip())
                i += 1
                continue

            # ---- ATX headings ----
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                text = self._inline(heading_match.group(2))
                output.append(f"<h{level}>{text}</h{level}>")
                i += 1
                continue

            # ---- horizontal rule ----
            if re.match(r"^[-*_]{3,}\s*$", line):
                output.append("<hr/>")
                i += 1
                continue

            # ---- blockquote ----
            if line.startswith("> "):
                quote_lines: list[str] = []
                while i < len(lines) and lines[i].startswith("> "):
                    quote_lines.append(lines[i][2:])
                    i += 1
                inner = self._markdown_to_html("\n".join(quote_lines))
                output.append(f"<blockquote>{inner}</blockquote>")
                continue

            # ---- unordered list ----
            if re.match(r"^[\*\-\+]\s+", line):
                items, i = self._collect_list(lines, i, ordered=False)
                output.append(items)
                continue

            # ---- ordered list ----
            if re.match(r"^\d+\.\s+", line):
                items, i = self._collect_list(lines, i, ordered=True)
                output.append(items)
                continue

            # ---- table ----
            if "|" in line and line.strip().startswith("|"):
                table_lines: list[str] = []
                while i < len(lines) and "|" in lines[i] and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                output.append(self._table(table_lines))
                continue

            # ---- blank line ----
            if not line.strip():
                i += 1
                continue

            # ---- regular paragraph ----
            output.append(f"<p>{self._inline(line)}</p>")
            i += 1

        return "\n".join(output)

    # ------------------------------------------------------------------
    # List helpers
    # ------------------------------------------------------------------

    def _collect_list(self, lines: list[str], start: int, ordered: bool) -> tuple[str, int]:
        tag = "ol" if ordered else "ul"
        pattern = r"^\d+\.\s+" if ordered else r"^[\*\-\+]\s+"
        items: list[str] = []
        i = start
        while i < len(lines) and re.match(pattern, lines[i]):
            text = re.sub(pattern, "", lines[i])
            items.append(f"<li>{self._inline(text)}</li>")
            i += 1
        return f"<{tag}>{''.join(items)}</{tag}>", i

    # ------------------------------------------------------------------
    # Table helper
    # ------------------------------------------------------------------

    def _table(self, rows: list[str]) -> str:
        parts: list[str] = ["<table>"]
        header_done = False
        for row in rows:
            # Skip separator rows like |---|---|
            if re.match(r"^\|[\s\-:|]+\|$", row.strip()):
                continue
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            if not header_done:
                parts.append("<tr>" + "".join(f"<th>{self._inline(c)}</th>" for c in cells) + "</tr>")
                header_done = True
            else:
                parts.append("<tr>" + "".join(f"<td>{self._inline(c)}</td>" for c in cells) + "</tr>")
        parts.append("</table>")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Inline markdown → HTML
    # ------------------------------------------------------------------

    def _inline(self, text: str) -> str:
        """Convert inline markdown elements to HTML."""
        # Inline images  ![alt](url)
        text = re.sub(
            r"!\[([^\]]*)\]\(([^)]+)\)",
            lambda m: f'<ac:image><ri:url ri:value="{m.group(2)}"/></ac:image>',
            text,
        )
        # Links  [text](url)
        text = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
            text,
        )
        # Bold  **text** or __text__
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
        # Italic  *text* or _text_
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
        # Inline code  `code`
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        # Strikethrough  ~~text~~
        text = re.sub(r"~~(.+?)~~", r"<del>\1</del>", text)
        return text

    # ------------------------------------------------------------------
    # Code macro
    # ------------------------------------------------------------------

    def _code_macro(self, language: str, code: str) -> str:
        lang_param = language if language else "none"
        return (
            f'<ac:structured-macro ac:name="code">'
            f'<ac:parameter ac:name="language">{lang_param}</ac:parameter>'
            f"<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>"
            f"</ac:structured-macro>"
        )
