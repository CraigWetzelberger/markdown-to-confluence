#!/usr/bin/env python3
import re
import subprocess
import sys
from pathlib import Path
import tempfile

def slugify(text):
    text = re.sub(r'[^\w\s-]', '', text.lower().strip())
    return re.sub(r'[\s-]+', '_', text)[:60]

def extract_mermaid_blocks(content):
    results = []
    for m in re.finditer(r'```mermaid\n(.*?)```', content, re.DOTALL):
        preceding = content[:m.start()]
        heading = re.findall(r'^#+\s+(.+)$', preceding, re.MULTILINE)
        title = slugify(heading[-1]) if heading else None
        results.append((m.group(1), title))
    return results

def render_mermaid(code, output_path):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as f:
        f.write(code)
        mmd_path = f.name
    
    subprocess.run(['mmdc', '-i', mmd_path, '-o', output_path, '-s', '1.5', '-w', '1536'], check=True)
    Path(mmd_path).unlink()

def convert_markdown(input_file, output_dir):
    content = Path(input_file).read_text()
    blocks = extract_mermaid_blocks(content)
    
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    for i, (block, title) in enumerate(blocks):
        img_name = f'{title}_{i}.png' if title else f'mermaid_{i}.png'
        img_path = output_dir / img_name
        render_mermaid(block, str(img_path))
        content = content.replace(f'```mermaid\n{block}```', f'![Mermaid Diagram]({img_name})', 1)
    
    output_file = output_dir / Path(input_file).name
    output_file.write_text(content)
    return output_file

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: md2conf-mermaid.py <input.md> [output_dir]')
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'output'
    
    result = convert_markdown(input_file, output_dir)
    print(f'Converted: {result}')
