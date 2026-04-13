# Markdown to Confluence Publisher

Tools for publishing markdown documents with mermaid diagrams to Confluence.

## Prerequisites

- Python 3
- Node.js / npm
- [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli):
  ```
  npm install -g @mermaid-js/mermaid-cli
  ```

## Install

```
pip3 install -r requirements.txt
```

## Scripts

| Script | Purpose |
|---|---|
| `kiro-publish-processing.sh` | Renders mermaid diagrams to PNG, outputs processed markdown |
| `kiro-publish-to-confluence.py` | Uploads attachments and publishes to a Confluence page section |
| `md2conf-mermaid.py` | Python helper for mermaid rendering (called by processing script) |

## Usage

### Step 1: Preprocess (render mermaid diagrams)
```bash
bash kiro-publish-processing.sh <source.md>
```
Output goes to `./output/` — processed markdown + PNG images.

### Step 2: Configure Confluence credentials

Edit `confluence_config.json` (next to the scripts):
```json
{
  "confluence_url": "https://example.atlassian.net/wiki",
  "username": "user@example.com",
  "api_token": "<your-api-token>"
}
```

### Step 3: Publish to Confluence
```bash
python3 kiro-publish-to-confluence.py <page_id> "<section_heading>" [output_dir]
```

The publish script:
- Uploads all PNG files as attachments (creates new or updates existing)
- Strips YAML frontmatter from the processed markdown
- Replaces `![Mermaid Diagram](file.png)` with Confluence `<ac:image>` attachment markup
- Does a section-level update: finds the `<h1>` matching `<section_heading>` and replaces that section, preserving all other sections
- If the section doesn't exist, appends it at the end

## Step 4 Install Kiro Prompt Integration

```
./install_kiro_prompt.sh
```


Once installed run the prompt
```
@publish-design
```


