# @publish-design

Publish design documentation written in Markdown to Confluence.

## What this prompt does

When you invoke `@publish-design`, this prompt guides you to:

1. Identify the Markdown file(s) containing the design documentation.
2. Locate any **mermaid** diagrams in those files and render them as PNG images.
3. Convert the Markdown content to **Confluence storage format** (XHTML).
4. Publish each converted document as a Confluence page, attaching generated images.
5. Optionally group multiple files into a single Confluence page as collapsible **sections**.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.9+ | Runtime for the conversion tool |
| `markdown-to-confluence` CLI | Run `pip install -e .` in the repo root |
| Mermaid CLI (`mmdc`) | `npm install -g @mermaid-js/mermaid-cli` – used for local image generation |
| Atlassian API token | Generate at <https://id.atlassian.com/manage/api-tokens> |

Set the following environment variables (or add them to a `.env` file):

```bash
CONFLUENCE_URL=https://<your-org>.atlassian.net/wiki
CONFLUENCE_USERNAME=you@example.com
CONFLUENCE_API_TOKEN=<your-api-token>
CONFLUENCE_SPACE_KEY=<space-key>
# Optional – page ID under which new pages will be created:
CONFLUENCE_PARENT_ID=<parent-page-id>
```

---

## Usage examples

### Publish a single design document

```bash
markdown-to-confluence path/to/design.md
```

### Publish multiple files as separate child pages

```bash
markdown-to-confluence docs/overview.md docs/api-design.md docs/data-model.md
```

### Combine multiple files into one page with expandable sections

```bash
markdown-to-confluence --sections docs/overview.md docs/api-design.md docs/data-model.md \
  --title "Architecture Overview"
```

### Preview the generated Confluence markup without publishing

```bash
markdown-to-confluence --dry-run path/to/design.md
```

### Use a specific output directory for mermaid images

```bash
markdown-to-confluence --mermaid-output-dir ./diagrams path/to/design.md
```

### Skip the local mermaid CLI and use online rendering (mermaid.ink)

```bash
markdown-to-confluence --no-local-mermaid path/to/design.md
```

---

## Workflow guide (step-by-step)

1. **Write your design document** in Markdown, using standard syntax plus mermaid code blocks:

   ````markdown
   # My Service Design

   ## Overview

   Describe the service here.

   ## Architecture

   ```mermaid
   graph TD
     A[Client] --> B[API Gateway]
     B --> C[Service A]
     B --> D[Service B]
   ```

   ## API Endpoints

   | Endpoint | Method | Description |
   |----------|--------|-------------|
   | /health  | GET    | Health check |
   ````

2. **Preview** the Confluence output locally:

   ```bash
   markdown-to-confluence --dry-run my-design.md
   ```

3. **Publish** once you are satisfied:

   ```bash
   markdown-to-confluence my-design.md
   ```

4. **Multi-file designs** – use `--sections` to keep everything on one Confluence page:

   ```bash
   markdown-to-confluence --sections \
     docs/overview.md \
     docs/sequence-diagrams.md \
     docs/data-model.md \
     --title "Service Design – Sprint 42"
   ```

---

## Mermaid diagram tips

- All standard mermaid diagram types are supported: `graph`, `sequenceDiagram`, `classDiagram`, `erDiagram`, `gantt`, `pie`, etc.
- Diagrams are rendered to PNG by the local `mmdc` binary (when available) and attached to the Confluence page.
- If `mmdc` is not installed the tool falls back to [mermaid.ink](https://mermaid.ink) URLs (requires internet access from Confluence).

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `mmdc: command not found` | Install mermaid CLI: `npm install -g @mermaid-js/mermaid-cli` |
| `401 Unauthorized` from Confluence | Check `CONFLUENCE_USERNAME` and `CONFLUENCE_API_TOKEN` |
| Page not found in space | Verify `CONFLUENCE_SPACE_KEY` is correct |
| Mermaid diagram not rendering | Preview with `--dry-run` and inspect the generated XML |
