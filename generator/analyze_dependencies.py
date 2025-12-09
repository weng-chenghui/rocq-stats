#!/usr/bin/env python3
"""
Analyze lemma dependencies in Coq files.

For each lemma in a stats CSV file, find which other lemmas from the same
stats file are used in its proof.

Usage:
    python analyze_dependencies.py <stats.csv> <coq_dir> [--format csv|markdown|html]
"""

import os
import re
import sys
import csv
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Set, Optional
from datetime import datetime


@dataclass
class LemmaInfo:
    file_name: str
    section: str
    name: str
    proof_lines: int
    signature: str
    meaning: str


def load_stats_csv(csv_path: Path) -> List[LemmaInfo]:
    """Load lemma information from a CSV stats file."""
    lemmas = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lemmas.append(LemmaInfo(
                file_name=row['File'],
                section=row['Section'],
                name=row['Name'],
                proof_lines=int(row['ProofLines']),
                signature=row['Signature'],
                meaning=row['Meaning']
            ))
    return lemmas


def extract_proof_body(lines: List[str], start_idx: int) -> str:
    """Extract the proof body from a lemma starting at start_idx."""
    idx = start_idx
    proof_started = False
    proof_lines = []
    
    while idx < len(lines):
        line = lines[idx].strip()
        line_no_comment = re.sub(r'\(\*.*?\*\)', '', line)
        
        if re.search(r'\bProof\b', line_no_comment):
            proof_started = True
            proof_lines.append(line)
            idx += 1
            break
        
        if re.search(r'\b(Qed|Defined|Admitted)\b', line_no_comment):
            return line
        
        idx += 1
        if idx - start_idx > 30:
            return ''
    
    if not proof_started:
        return ''
    
    while idx < len(lines):
        line = lines[idx]
        proof_lines.append(line)
        
        line_no_comment = re.sub(r'\(\*.*?\*\)', '', line)
        if re.search(r'\b(Qed|Defined|Admitted)\b', line_no_comment):
            break
        
        idx += 1
        if len(proof_lines) > 500:
            break
    
    return '\n'.join(proof_lines)


def find_used_lemmas(proof_body: str, all_lemma_names: Set[str], own_name: str) -> List[str]:
    """Find which lemmas from the set are referenced in the proof body."""
    used = []
    proof_clean = re.sub(r'\(\*.*?\*\)', '', proof_body, flags=re.DOTALL)
    
    for name in all_lemma_names:
        if name == own_name:
            continue
        pattern = rf'\b{re.escape(name)}\b'
        if re.search(pattern, proof_clean):
            used.append(name)
    
    return sorted(used)


def analyze_dependencies(stats: List[LemmaInfo], coq_dirs: List[Path]) -> Dict[str, List[str]]:
    """Analyze dependencies for all lemmas in the stats."""
    all_names = {l.name for l in stats}
    dependencies = {}
    
    files_to_lemmas: Dict[str, List[LemmaInfo]] = {}
    for l in stats:
        if l.file_name not in files_to_lemmas:
            files_to_lemmas[l.file_name] = []
        files_to_lemmas[l.file_name].append(l)
    
    for file_name, lemmas in files_to_lemmas.items():
        filepath = None
        for coq_dir in coq_dirs:
            candidate = coq_dir / file_name
            if candidate.exists():
                filepath = candidate
                break
        
        if not filepath:
            print(f"Warning: Could not find file {file_name}", file=sys.stderr)
            for l in lemmas:
                dependencies[l.name] = []
            continue
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.read().split('\n')
        except Exception as e:
            print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
            for l in lemmas:
                dependencies[l.name] = []
            continue
        
        for lemma in lemmas:
            proof_body = None
            lemma_pattern = re.compile(
                rf'^\s*(Lemma|Theorem|Corollary|Proposition|Fact|Remark)\s+{re.escape(lemma.name)}\b'
            )
            
            for idx, line in enumerate(lines):
                if lemma_pattern.match(line):
                    proof_body = extract_proof_body(lines, idx)
                    break
            
            if proof_body:
                used = find_used_lemmas(proof_body, all_names, lemma.name)
                dependencies[lemma.name] = used
            else:
                dependencies[lemma.name] = []
    
    return dependencies


def escape_html(text: str) -> str:
    return (text.replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def format_csv(stats: List[LemmaInfo], deps: Dict[str, List[str]]) -> str:
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Lemma', 'File', 'Section', 'Dependencies', 'Dep_Count'])
    for l in stats:
        dep_list = deps.get(l.name, [])
        writer.writerow([l.name, l.file_name, l.section, ', '.join(dep_list), len(dep_list)])
    return output.getvalue()


def format_markdown(stats: List[LemmaInfo], deps: Dict[str, List[str]]) -> str:
    lines = ["| Lemma | File | Section | Dependencies |",
             "|-------|------|---------|--------------|"]
    for l in stats:
        dep_list = deps.get(l.name, [])
        dep_str = ', '.join(f'`{d}`' for d in dep_list) if dep_list else '—'
        lines.append(f"| `{l.name}` | {l.file_name} | {l.section} | {dep_str} |")
    return '\n'.join(lines)


def format_html(stats: List[LemmaInfo], deps: Dict[str, List[str]], title: str) -> str:
    files = {}
    for l in stats:
        if l.file_name not in files:
            files[l.file_name] = []
        files[l.file_name].append(l)
    
    total_deps = sum(len(deps.get(l.name, [])) for l in stats)
    max_deps = max((len(deps.get(l.name, [])) for l in stats), default=0)
    
    rows_html = ""
    for l in stats:
        dep_list = deps.get(l.name, [])
        if dep_list:
            deps_html = ' '.join(f'<span class="tag">{escape_html(d)}</span>' for d in dep_list)
        else:
            deps_html = '<span class="none">—</span>'
        rows_html += f'''<tr data-lemma="{escape_html(l.name)}">
            <td class="name">{escape_html(l.name)}</td>
            <td class="file">{escape_html(l.file_name)}</td>
            <td>{escape_html(l.section)}</td>
            <td class="count">{len(dep_list)}</td>
            <td class="deps">{deps_html}</td>
        </tr>\n'''
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape_html(title)}</title>
<style>
:root {{ --bg:#0d1117; --bg2:#161b22; --bg3:#21262d; --txt:#c9d1d9; --txt2:#8b949e;
         --accent:#58a6ff; --border:#30363d; --green:#3fb950; --yellow:#d29922; --purple:#a371f7; }}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;
        background:var(--bg); color:var(--txt); line-height:1.6; padding:2rem; }}
.container {{ max-width:1400px; margin:0 auto; }}
h1 {{ border-bottom:1px solid var(--border); padding-bottom:.5rem; margin-bottom:1rem; }}
.stats {{ display:flex; gap:2rem; margin-bottom:2rem; flex-wrap:wrap; }}
.stat {{ background:var(--bg2); border:1px solid var(--border); border-radius:6px; padding:1rem 1.5rem; }}
.stat .val {{ font-size:2rem; font-weight:600; color:var(--accent); }}
.stat .lbl {{ color:var(--txt2); font-size:.9rem; }}
input {{ width:100%; max-width:400px; padding:.75rem 1rem; background:var(--bg2);
         border:1px solid var(--border); border-radius:6px; color:var(--txt); font-size:1rem; margin-bottom:1.5rem; }}
input:focus {{ outline:none; border-color:var(--accent); }}
table {{ width:100%; border-collapse:collapse; background:var(--bg2); border-radius:6px; overflow:hidden; }}
th {{ background:var(--bg3); text-align:left; padding:.75rem 1rem; font-weight:600; color:var(--txt2); }}
td {{ padding:.75rem 1rem; border-bottom:1px solid var(--border); vertical-align:top; }}
tr:hover {{ background:var(--bg3); }}
.name {{ font-family:Consolas,monospace; color:var(--green); font-weight:500; }}
.file {{ color:var(--txt2); font-size:.85rem; }}
.count {{ text-align:center; font-weight:600; color:var(--yellow); }}
.deps {{ display:flex; flex-wrap:wrap; gap:.5rem; }}
.tag {{ font-family:Consolas,monospace; font-size:.8rem; background:var(--bg3);
        border:1px solid var(--border); padding:.2rem .5rem; border-radius:3px; color:var(--purple); }}
.none {{ color:var(--txt2); font-style:italic; }}
.timestamp {{ color:var(--txt2); font-size:.85rem; margin-top:2rem; padding-top:1rem; border-top:1px solid var(--border); }}
</style>
</head>
<body>
<div class="container">
<h1>{escape_html(title)}</h1>
<div class="stats">
<div class="stat"><div class="val">{len(stats)}</div><div class="lbl">Lemmas</div></div>
<div class="stat"><div class="val">{total_deps}</div><div class="lbl">Total Dependencies</div></div>
<div class="stat"><div class="val">{max_deps}</div><div class="lbl">Max Dependencies</div></div>
<div class="stat"><div class="val">{len(files)}</div><div class="lbl">Files</div></div>
</div>
<input type="text" id="search" placeholder="Search lemmas...">
<table>
<thead><tr><th>Lemma</th><th>File</th><th>Section</th><th style="text-align:center">#</th><th>Uses (from stats)</th></tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
<div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
</div>
<script>
document.getElementById('search').addEventListener('input', function(e) {{
    const q = e.target.value.toLowerCase();
    document.querySelectorAll('tbody tr').forEach(r => {{
        r.style.display = r.getAttribute('data-lemma').toLowerCase().includes(q) ? '' : 'none';
    }});
}});
</script>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(description='Analyze lemma dependencies from a stats CSV file')
    parser.add_argument('stats_csv', help='Path to the stats CSV file')
    parser.add_argument('coq_dirs', nargs='+', help='Directories containing the Coq source files')
    parser.add_argument('--format', '-f', choices=['csv', 'markdown', 'html'], default='markdown')
    parser.add_argument('--title', '-t', default='Lemma Dependencies')
    
    args = parser.parse_args()
    
    csv_path = Path(args.stats_csv)
    if not csv_path.exists():
        print(f"Error: Stats file '{csv_path}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    coq_dirs = [Path(d) for d in args.coq_dirs if Path(d).exists()]
    if not coq_dirs:
        print("Error: No valid Coq directories provided", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading stats from {csv_path}...", file=sys.stderr)
    stats = load_stats_csv(csv_path)
    print(f"Found {len(stats)} lemmas", file=sys.stderr)
    
    print("Analyzing dependencies...", file=sys.stderr)
    deps = analyze_dependencies(stats, coq_dirs)
    
    total_deps = sum(len(d) for d in deps.values())
    print(f"Found {total_deps} internal dependencies", file=sys.stderr)
    
    if args.format == 'csv':
        output = format_csv(stats, deps)
    elif args.format == 'html':
        output = format_html(stats, deps, args.title)
    else:
        output = format_markdown(stats, deps)
    
    print(output)


if __name__ == '__main__':
    main()

