# Markdown to Confluence Publisher

Tools for publishing markdown documents with mermaid diagrams to Confluence.

## Skill

```shell
npx skills add CraigWetzelberger/mermaid2conf --global --skill '*' --agent kiro-cli --agent codex
```

## Prerequisites

- Python 3.12+
- Node.js / npm
- [uv](https://docs.astral.sh/uv/)
  - `curl -LsSf https://astral.sh/uv/install.sh | sh` OR `brew install uv`
- [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli):
  ```
  npm install -g @mermaid-js/mermaid-cli
  ```

### Configure Confluence credentials

Visit [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens) to create api-token

Create `confluence_config.json` in the current directory, or pass an explicit path with `--config`:

```
{
  "confluence_url": "https://example.atlassian.net/wiki",
  "username": "user@example.com",
  "api_token": "<your-api-token>"
}
```

## Development workflow

### Local changes only

1. Remove skill if previously installed from remote github repo
   ```shell
   npx skill remove CraigWetzelberger/mermaid2conf
   ```
2. Make changes as needed to the python scripts
3. Open a shell in the repo root directory
   ```shell
   npx skills add . --global --skill '*' --agent kiro-cli --agent codex
   ```
4. invoke skill via agent prompt, or via `$mermaid2conf /path/to/diagram.md`

### From a remote branch

1. Remove skill if previously installed from remote github repo
   ```shell
   npx skill remove CraigWetzelberger/mermaid2conf
   ```
2. Create new branch
3. Make changes as needed to the python scripts
4. Push changes up to remote
5. ```shell
   npx skills add CraigWetzelberger/mermaid2conf#branch-name --global --skill '*' --agent kiro-cli --agent codex
   ```
6. invoke skill via agent prompt, or via `$mermaid2conf /path/to/diagram.md`

### dev dependencies

```shell
brew install pipx yamllint
pipx install mdformat yamlfixer-opt-nc
pipx inject mdformat mdformat-gfm mdformat-frontmatter mdformat-footnote mdformat-gfm-alerts
```

#### Pre-Commit

This repo uses `pre-commit` to apply a small set of formatting and hygiene checks before commits:

- `ruff-check --fix`: lint Python code and apply safe autofixes where possible
- `ruff-format`: format Python source files
- `trailing-whitespace`: remove trailing whitespace from non-Markdown files
- `end-of-file-fixer`: ensure non-Markdown files end with a newline
- `mdformat`: normalize Markdown formatting, including frontmatter, GFM, footnotes, and alerts
- `uv-lock`: keep `uv.lock` in sync with `pyproject.toml`

Common commands:

```shell
pre-commit install
pre-commit run -a
```

## Installation and usage without agent invokation

Install the tool globally with `uv`:

```bash
uv tool install ./skills/mermaid2conf/scripts
```

For local development, install it in editable mode:

```bash
uv tool install --editable ./skills/mermaid2conf/scripts
```

Or run it directly from the checkout without installing:

```bash
uv run --project ./skills/mermaid2conf/scripts mermaid2conf process docs/example.md
```

To execute it ephemerally with `uv tool run` from this checkout:

```bash
uv tool run --from ./skills/mermaid2conf/scripts mermaid2conf process docs/example.md
```

## Scripts

| Command                      | Purpose                                                        |
| ---------------------------- | -------------------------------------------------------------- |
| `mermaid2conf process`       | Renders mermaid diagrams to PNG and writes processed markdown  |
| `mermaid2conf publish`       | Uploads attachments and publishes to a Confluence page section |
| `mermaid2conf mermaid`       | Low-level helper for rendering Mermaid blocks to PNG           |
| `kiro-publish-processing.sh` | Repo-local compatibility wrapper around `uv run --project`     |

Legacy aliases are still available for compatibility:

- `kiro-publish-processing`
- `kiro-publish-to-confluence`
- `md2conf-mermaid`

## Usage

### Step 1: Preprocess (render mermaid diagrams)

```bash
mermaid2conf process <source.md>
```

Output goes to `./output/` by default and includes the processed markdown plus PNG images.

### Step 2: Publish to Confluence

```bash
mermaid2conf publish <page_id> "<section_heading>" [output_dir] --config ./confluence_config.json
```

The publish script:

- Uploads all PNG files as attachments (creates new or updates existing)
- Strips YAML frontmatter from the processed markdown
- Replaces `![Mermaid Diagram](file.png)` with Confluence `<ac:image>` attachment markup
- Does a section-level update: finds the `<h1>` matching `<section_heading>` and replaces that section, preserving all other sections
- If the section doesn't exist, appends it at the end
