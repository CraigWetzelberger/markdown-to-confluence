---
name: markdown-to-confluence
description: Use this skill to publish markdown documents with mermaid diagrams to directly Confluence.
---

# Markdown To Confluence

## Pre-Requisites

1. Confirm `uv` is installed

   ```shell
   command -v "uv" || echo "NOT INSTALLED"
   ```

   If `uv` is not installed prompt for approval to install `uv`

   ```shell
     curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Confirm `mermaid-cli` is installed

   ```shell
   npm list -g @mermaid-js/mermaid-cli || echo "NOT INSTALLED" 
   ```

   If `mermaid-cli` is not installed prompt for approval to install `uv`

   ```shell
     npm install -g @mermaid-js/mermaid-cli
   ```

3. Confirm confluence configuration exists

   ```shell
   [ -f ~/.config/markdown-to-confluence/confluence_config.json ] && echo "Exists" || echo "Does not exist" 
   ```

   If Confluence Configuration file does not exist, direct user to visit [Configure Confluence Credentials](https://github.com/bholland-bh/markdown-to-confluence#configure-confluence-credentials) and terminate
