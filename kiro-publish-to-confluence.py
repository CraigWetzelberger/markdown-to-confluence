#!/usr/bin/env python3
"""Publish processed markdown to a Confluence page section.

Usage:
    python3 kiro-publish-to-confluence.py <page_id> <section_heading> [output_dir]

Prerequisites:
    - Run kiro-publish-processing.sh first to render mermaid diagrams
    - pip3 install -r requirements.txt
    - Fill in confluence_config.json (next to this script)
"""
import json, os, re, sys, glob
import mistune, requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "confluence_config.json")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        sys.exit(
            f"ERROR: Config file not found.\n"
            f"Create {CONFIG_PATH} with:\n"
            f'{{\n  "confluence_url": "https://example.atlassian.net/wiki",\n'
            f'  "username": "user@example.com",\n'
            f'  "api_token": "<your-api-token>"\n}}'
        )
    cfg = json.load(open(CONFIG_PATH))
    missing = [k for k in ("confluence_url", "username", "api_token") if not cfg.get(k)]
    if missing:
        sys.exit(
            f"ERROR: Missing config values: {', '.join(missing)}\n"
            f"Update {CONFIG_PATH} with your Confluence credentials."
        )
    return cfg


def make_session(cfg):
    s = requests.Session()
    s.auth = (cfg["username"], cfg["api_token"])
    s.headers["X-Atlassian-Token"] = "nocheck"
    return s, cfg["confluence_url"].rstrip("/") + "/rest/api"


def check_auth(session, api):
    r = session.get(f"{api}/user/current")
    if r.status_code in (401, 403):
        sys.exit(
            f"ERROR: Authentication failed (HTTP {r.status_code}).\n"
            f"Check your username and api_token in:\n  {CONFIG_PATH}"
        )
    r.raise_for_status()


def upload_attachments(session, api, page_id, output_dir):
    for png in sorted(glob.glob(os.path.join(output_dir, "*.png"))):
        fname = os.path.basename(png)
        print(f"Uploading: {fname}")
        r = session.post(
            f"{api}/content/{page_id}/child/attachment",
            files={"file": (fname, open(png, "rb"), "image/png")},
            data={"minorEdit": "true"},
        )
        if r.status_code == 200:
            print("  Created")
            continue
        # Try updating existing attachment
        att_r = session.get(f"{api}/content/{page_id}/child/attachment", params={"filename": fname})
        results = att_r.json().get("results", [])
        if results:
            att_id = results[0]["id"]
            ur = session.post(
                f"{api}/content/{page_id}/child/attachment/{att_id}/data",
                files={"file": (fname, open(png, "rb"), "image/png")},
                data={"minorEdit": "true"},
            )
            print(f"  Updated (HTTP {ur.status_code})")
        else:
            print(f"  WARNING: Could not upload {fname}")


def md_to_confluence_html(md_path):
    content = open(md_path).read()
    # Strip YAML frontmatter
    content = re.sub(r"^---\n.*?\n---\n", "", content, count=1, flags=re.DOTALL)
    # Replace mermaid images with placeholders before conversion
    content = re.sub(
        r"!\[Mermaid Diagram\]\(([^)]+\.png)\)",
        lambda m: f"ACIMG|||{m.group(1)}|||ENDACIMG",
        content,
    )
    html = mistune.html(content)
    # Placeholders → Confluence ac:image
    html = re.sub(
        r"ACIMG\|\|\|(.+?)\|\|\|ENDACIMG",
        r'<ac:image ac:width="760"><ri:attachment ri:filename="\1"/></ac:image>',
        html,
    )
    # <pre><code> → Confluence code macro
    def pre_to_macro(m):
        lang_m = re.search(r'class="language-(\w+)"', m.group(1) or "")
        lang = lang_m.group(1) if lang_m else ""
        code = m.group(2).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        lang_param = f'<ac:parameter ac:name="language">{lang}</ac:parameter>' if lang else ""
        return (
            f'<ac:structured-macro ac:name="code" ac:schema-version="1">'
            f"{lang_param}"
            f"<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>"
            f"</ac:structured-macro>"
        )
    html = re.sub(r"<pre><code([^>]*)>(.*?)</code></pre>", pre_to_macro, html, flags=re.DOTALL)
    return html


def merge_section(current, section, new_html):
    h1_pat = re.compile(r"<h1[^>]*>", re.IGNORECASE)
    positions = [m.start() for m in h1_pat.finditer(current)]
    target_idx = None
    for i, pos in enumerate(positions):
        end_h1 = current.index("</h1>", pos) + 5
        h1_text = re.sub(r"<[^>]+>", "", current[pos:end_h1]).strip()
        if h1_text.lower() == section.lower().strip():
            target_idx = i
            break
    if target_idx is not None:
        start = positions[target_idx]
        end = positions[target_idx + 1] if target_idx + 1 < len(positions) else len(current)
        return current[:start] + new_html + current[end:]
    if positions:
        return current + "<h1>" + section + "</h1>" + new_html
    return current + new_html


def publish(session, api, page_id, section, new_html):
    r = session.get(f"{api}/content/{page_id}", params={"expand": "body.storage,version"})
    r.raise_for_status()
    page = r.json()
    current = page["body"]["storage"]["value"]
    version = page["version"]["number"]
    title = page["title"]

    merged = merge_section(current, section, new_html)

    r = session.put(
        f"{api}/content/{page_id}",
        json={
            "version": {"number": version + 1},
            "title": title,
            "type": "page",
            "body": {"storage": {"value": merged, "representation": "storage"}},
        },
    )
    r.raise_for_status()
    resp = r.json()
    print("✅ Published:", resp["_links"]["base"] + resp["_links"]["webui"])


def main():
    if len(sys.argv) < 3:
        sys.exit("Usage: python3 kiro-publish-to-confluence.py <page_id> <section_heading> [output_dir]")

    page_id = sys.argv[1]
    section = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else os.path.join(SCRIPT_DIR, "output")

    cfg = load_config()
    session, api = make_session(cfg)
    check_auth(session, api)

    md_files = glob.glob(os.path.join(output_dir, "*.md"))
    if not md_files:
        sys.exit(f"ERROR: No .md file in {output_dir}")

    upload_attachments(session, api, page_id, output_dir)

    new_html = md_to_confluence_html(md_files[0])
    print(f"Converted markdown to HTML ({len(new_html)} bytes)")

    publish(session, api, page_id, section, new_html)


if __name__ == "__main__":
    main()
