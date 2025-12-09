#!/usr/bin/env python3
"""
List all lemmas from Coq (.v) files in directories.

Outputs a table with:
- File name
- Section name
- Lemma name
- Signature
- Meaning (extracted from preceding comments)

Usage:
    python list_lemmas.py <dir1> [dir2 ...] [--format csv|markdown|tsv|html]
    python list_lemmas.py dumas2017dual -r --format html > index.html
"""

import os
import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class LemmaInfo:
    file_name: str
    section: str
    name: str
    signature: str
    meaning: str
    proof_lines: int


def extract_preceding_comment(lines: List[str], lemma_line_idx: int) -> str:
    """Extract comment block immediately preceding a lemma."""
    comments = []
    idx = lemma_line_idx - 1
    
    # Skip blank lines
    while idx >= 0 and lines[idx].strip() == '':
        idx -= 1
    
    # Check for single-line comment
    if idx >= 0:
        line = lines[idx].strip()
        if line.startswith('(*') and line.endswith('*)'):
            # Single line comment
            comment = line[2:-2].strip()
            return comment
    
    # Check for multi-line comment block
    in_comment = False
    comment_lines = []
    
    while idx >= 0:
        line = lines[idx].strip()
        
        if line.endswith('*)') and not in_comment:
            in_comment = True
            # Remove trailing *)
            content = line[:-2].strip() if line != '*)'else ''
            if content:
                comment_lines.insert(0, content)
        elif line.startswith('(*') and in_comment:
            # Remove leading (*
            content = line[2:].strip() if line != '(*' else ''
            if content:
                comment_lines.insert(0, content)
            break
        elif in_comment:
            # Clean up comment line markers
            cleaned = line.lstrip('*').strip()
            if cleaned:
                comment_lines.insert(0, cleaned)
        elif line == '':
            if in_comment:
                continue
            else:
                break
        else:
            break
        idx -= 1
    
    if comment_lines:
        # Join comment lines
        result = ' '.join(comment_lines)
        # Remove multiple spaces
        result = re.sub(r'\s+', ' ', result)
        return result
    
    return ''


def extract_signature(lines: List[str], start_idx: int) -> str:
    """Extract the full signature of a lemma/theorem."""
    signature_lines = []
    idx = start_idx
    paren_depth = 0
    found_colon = False
    
    while idx < len(lines):
        line = lines[idx].strip()
        
        # Remove comments from line
        line = re.sub(r'\(\*.*?\*\)', '', line)
        
        signature_lines.append(line)
        
        # Track parentheses
        paren_depth += line.count('(') - line.count(')')
        paren_depth += line.count('[') - line.count(']')
        paren_depth += line.count('{') - line.count('}')
        
        if ':' in line:
            found_colon = True
        
        # End of signature: line ends with . and balanced parens
        if line.rstrip().endswith('.') and paren_depth <= 0 and found_colon:
            break
        
        # Also check for Proof keyword
        if 'Proof' in line or 'Proof.' in line:
            # Remove Proof from last line
            signature_lines[-1] = re.sub(r'\bProof\.?', '', signature_lines[-1]).strip()
            break
        
        idx += 1
        if idx - start_idx > 20:  # Safety limit
            break
    
    sig = ' '.join(signature_lines)
    # Clean up
    sig = re.sub(r'\s+', ' ', sig)
    sig = sig.strip()
    # Remove trailing Proof if present
    sig = re.sub(r'\s*Proof\.?\s*$', '', sig)
    return sig


def count_proof_lines(lines: List[str], start_idx: int) -> int:
    """Count the number of lines in a proof (from Proof to Qed/Defined/Admitted)."""
    idx = start_idx
    proof_started = False
    proof_start_line = start_idx
    
    # Find Proof keyword
    while idx < len(lines):
        line = lines[idx].strip()
        # Remove comments
        line_no_comment = re.sub(r'\(\*.*?\*\)', '', line)
        
        if re.search(r'\bProof\b', line_no_comment):
            proof_started = True
            proof_start_line = idx
            break
        
        # Check for end markers without Proof (one-liner proofs)
        if re.search(r'\b(Qed|Defined|Admitted)\b', line_no_comment):
            return 1  # One-liner proof
        
        idx += 1
        if idx - start_idx > 30:  # Safety limit for finding Proof
            return 0
    
    if not proof_started:
        return 0
    
    # Count lines until Qed/Defined/Admitted
    proof_lines = 0
    idx = proof_start_line
    
    while idx < len(lines):
        line = lines[idx].strip()
        # Remove comments for checking end markers
        line_no_comment = re.sub(r'\(\*.*?\*\)', '', line)
        
        # Count non-empty, non-comment lines
        if line and not line.startswith('(*'):
            proof_lines += 1
        
        # Check for end of proof
        if re.search(r'\b(Qed|Defined|Admitted)\b', line_no_comment):
            break
        
        idx += 1
        if idx - proof_start_line > 500:  # Safety limit
            break
    
    return max(1, proof_lines)


def parse_coq_file(filepath: Path, base_dir: Path) -> List[LemmaInfo]:
    """Parse a Coq file and extract lemma information."""
    lemmas = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
    except Exception as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return []
    
    # Get relative path from base directory
    try:
        relative_path = filepath.relative_to(base_dir)
    except ValueError:
        relative_path = filepath
    
    current_section = "Top-level"
    section_stack = ["Top-level"]
    
    # Pattern for lemmas/theorems/corollaries
    lemma_pattern = re.compile(
        r'^\s*(Lemma|Theorem|Corollary|Proposition|Fact|Remark)\s+(\w+)',
        re.MULTILINE
    )
    
    # Pattern for sections
    section_start = re.compile(r'^\s*Section\s+(\w+)\s*\.', re.MULTILINE)
    section_end = re.compile(r'^\s*End\s+(\w+)\s*\.', re.MULTILINE)
    
    for idx, line in enumerate(lines):
        # Track sections
        section_match = section_start.match(line)
        if section_match:
            section_name = section_match.group(1)
            section_stack.append(section_name)
            current_section = section_name
            continue
        
        end_match = section_end.match(line)
        if end_match:
            if len(section_stack) > 1:
                section_stack.pop()
                current_section = section_stack[-1]
            continue
        
        # Find lemmas
        lemma_match = lemma_pattern.match(line)
        if lemma_match:
            lemma_type = lemma_match.group(1)
            lemma_name = lemma_match.group(2)
            
            # Extract signature
            signature = extract_signature(lines, idx)
            
            # Extract meaning from preceding comment
            meaning = extract_preceding_comment(lines, idx)
            
            # Count proof lines
            proof_lines = count_proof_lines(lines, idx)
            
            lemmas.append(LemmaInfo(
                file_name=str(relative_path),
                section=current_section,
                name=lemma_name,
                signature=signature,
                meaning=meaning,
                proof_lines=proof_lines
            ))
    
    return lemmas


def format_table_markdown(lemmas: List[LemmaInfo]) -> str:
    """Format lemmas as a Markdown table."""
    lines = []
    lines.append("| File | Section | Name | Lines | Signature | Meaning |")
    lines.append("|------|---------|------|------:|-----------|---------|")
    
    for l in lemmas:
        # Escape pipe characters
        sig = l.signature.replace('|', '\\|')
        meaning = l.meaning.replace('|', '\\|')
        lines.append(f"| {l.file_name} | {l.section} | `{l.name}` | {l.proof_lines} | `{sig}` | {meaning} |")
    
    return '\n'.join(lines)


def format_table_csv(lemmas: List[LemmaInfo]) -> str:
    """Format lemmas as CSV."""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['File', 'Section', 'Name', 'ProofLines', 'Signature', 'Meaning'])
    
    for l in lemmas:
        writer.writerow([l.file_name, l.section, l.name, l.proof_lines, l.signature, l.meaning])
    
    return output.getvalue()


def format_table_tsv(lemmas: List[LemmaInfo]) -> str:
    """Format lemmas as TSV (tab-separated)."""
    lines = []
    lines.append("File\tSection\tName\tProofLines\tSignature\tMeaning")
    
    for l in lemmas:
        sig = l.signature.replace('\t', ' ')
        meaning = l.meaning.replace('\t', ' ')
        lines.append(f"{l.file_name}\t{l.section}\t{l.name}\t{l.proof_lines}\t{sig}\t{meaning}")
    
    return '\n'.join(lines)


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#39;'))


def format_table_html(lemmas: List[LemmaInfo], title: str = "Coq Lemma Statistics") -> str:
    """Format lemmas as a standalone HTML page suitable for GitHub Pages."""
    
    # Group lemmas by file for better organization
    files = {}
    for l in lemmas:
        if l.file_name not in files:
            files[l.file_name] = []
        files[l.file_name].append(l)
    
    # Calculate statistics
    total_lemmas = len(lemmas)
    total_files = len(files)
    total_proof_lines = sum(l.proof_lines for l in lemmas)
    
    # Build HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)}</title>
    <style>
        :root {{
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent: #58a6ff;
            --accent-hover: #79c0ff;
            --border: #30363d;
            --code-bg: #1f2428;
            --success: #3fb950;
            --warning: #d29922;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            padding: 2rem;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        h1 {{
            color: var(--text-primary);
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
            margin-bottom: 1rem;
        }}
        
        h2 {{
            color: var(--accent);
            margin: 2rem 0 1rem 0;
            font-size: 1.3rem;
        }}
        
        .stats {{
            display: flex;
            gap: 2rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }}
        
        .stat-card {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1rem 1.5rem;
            min-width: 150px;
        }}
        
        .stat-card .value {{
            font-size: 2rem;
            font-weight: 600;
            color: var(--accent);
        }}
        
        .stat-card .label {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        .search-box {{
            margin-bottom: 1.5rem;
        }}
        
        .search-box input {{
            width: 100%;
            max-width: 400px;
            padding: 0.75rem 1rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text-primary);
            font-size: 1rem;
        }}
        
        .search-box input:focus {{
            outline: none;
            border-color: var(--accent);
        }}
        
        .file-section {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 6px;
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}
        
        .file-header {{
            background: var(--bg-tertiary);
            padding: 0.75rem 1rem;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .file-header:hover {{
            background: var(--border);
        }}
        
        .file-name {{
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            color: var(--accent);
        }}
        
        .file-count {{
            color: var(--text-secondary);
            font-size: 0.9rem;
        }}
        
        .file-content {{
            display: none;
        }}
        
        .file-content.expanded {{
            display: block;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            background: var(--bg-tertiary);
            text-align: left;
            padding: 0.75rem 1rem;
            font-weight: 600;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border);
            position: sticky;
            top: 0;
        }}
        
        td {{
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            vertical-align: top;
        }}
        
        tr:hover {{
            background: var(--bg-tertiary);
        }}
        
        .lemma-name {{
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            color: var(--success);
            font-weight: 500;
        }}
        
        .section-name {{
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}
        
        .proof-lines {{
            text-align: right;
            font-family: 'SFMono-Regular', Consolas, monospace;
            color: var(--warning);
        }}
        
        .signature {{
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 0.85rem;
            background: var(--code-bg);
            padding: 0.25rem 0.5rem;
            border-radius: 3px;
            white-space: pre-wrap;
            word-break: break-word;
            max-width: 400px;
        }}
        
        .meaning {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            max-width: 400px;
        }}
        
        .timestamp {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
        }}
        
        .expand-all {{
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            margin-bottom: 1rem;
        }}
        
        .expand-all:hover {{
            background: var(--border);
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 1rem;
            }}
            .stats {{
                flex-direction: column;
                gap: 1rem;
            }}
            .signature, .meaning {{
                max-width: 100%;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{escape_html(title)}</h1>
        
        <div class="stats">
            <div class="stat-card">
                <div class="value">{total_lemmas}</div>
                <div class="label">Total Lemmas</div>
            </div>
            <div class="stat-card">
                <div class="value">{total_files}</div>
                <div class="label">Files</div>
            </div>
            <div class="stat-card">
                <div class="value">{total_proof_lines}</div>
                <div class="label">Proof Lines</div>
            </div>
        </div>
        
        <div class="search-box">
            <input type="text" id="search" placeholder="Search lemmas by name, signature, or meaning...">
        </div>
        
        <button class="expand-all" onclick="toggleAll()">Expand/Collapse All</button>
        
        <div id="content">
'''
    
    # Add each file section
    for file_name in sorted(files.keys()):
        file_lemmas = files[file_name]
        html += f'''
            <div class="file-section" data-file="{escape_html(file_name)}">
                <div class="file-header" onclick="toggleSection(this)">
                    <span class="file-name">{escape_html(file_name)}</span>
                    <span class="file-count">{len(file_lemmas)} lemmas</span>
                </div>
                <div class="file-content">
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Section</th>
                                <th>Lines</th>
                                <th>Signature</th>
                                <th>Meaning</th>
                            </tr>
                        </thead>
                        <tbody>
'''
        for l in file_lemmas:
            html += f'''
                            <tr data-search="{escape_html((l.name + ' ' + l.signature + ' ' + l.meaning).lower())}">
                                <td class="lemma-name">{escape_html(l.name)}</td>
                                <td class="section-name">{escape_html(l.section)}</td>
                                <td class="proof-lines">{l.proof_lines}</td>
                                <td><code class="signature">{escape_html(l.signature)}</code></td>
                                <td class="meaning">{escape_html(l.meaning)}</td>
                            </tr>
'''
        html += '''
                        </tbody>
                    </table>
                </div>
            </div>
'''
    
    html += f'''
        </div>
        
        <div class="timestamp">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
    
    <script>
        function toggleSection(header) {{
            const content = header.nextElementSibling;
            content.classList.toggle('expanded');
        }}
        
        function toggleAll() {{
            const contents = document.querySelectorAll('.file-content');
            const anyExpanded = Array.from(contents).some(c => c.classList.contains('expanded'));
            contents.forEach(c => {{
                if (anyExpanded) {{
                    c.classList.remove('expanded');
                }} else {{
                    c.classList.add('expanded');
                }}
            }});
        }}
        
        document.getElementById('search').addEventListener('input', function(e) {{
            const query = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('tbody tr');
            const sections = document.querySelectorAll('.file-section');
            
            if (query === '') {{
                rows.forEach(r => r.style.display = '');
                sections.forEach(s => s.style.display = '');
                return;
            }}
            
            sections.forEach(section => {{
                const sectionRows = section.querySelectorAll('tbody tr');
                let hasVisible = false;
                
                sectionRows.forEach(row => {{
                    const searchText = row.getAttribute('data-search');
                    if (searchText.includes(query)) {{
                        row.style.display = '';
                        hasVisible = true;
                    }} else {{
                        row.style.display = 'none';
                    }}
                }});
                
                section.style.display = hasVisible ? '' : 'none';
                if (hasVisible && query) {{
                    section.querySelector('.file-content').classList.add('expanded');
                }}
            }});
        }});
    </script>
</body>
</html>
'''
    
    return html


def main():
    parser = argparse.ArgumentParser(
        description='List all lemmas from Coq files in directories'
    )
    parser.add_argument(
        'directories',
        nargs='+',
        help='Directories containing .v files to analyze'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['csv', 'markdown', 'tsv', 'html'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Search directories recursively'
    )
    parser.add_argument(
        '--title', '-t',
        default='Coq Lemma Statistics',
        help='Title for HTML output (default: "Coq Lemma Statistics")'
    )
    
    args = parser.parse_args()
    
    all_lemmas = []
    total_files = 0
    
    for dir_path in args.directories:
        target = Path(dir_path)
        if not target.exists():
            print(f"Warning: Directory '{target}' does not exist, skipping", file=sys.stderr)
            continue
        
        # Find all .v files
        if args.recursive:
            v_files = list(target.rglob('*.v'))
        else:
            v_files = list(target.glob('*.v'))
        
        if not v_files:
            print(f"Warning: No .v files found in {target}", file=sys.stderr)
            continue
        
        total_files += len(v_files)
        
        # Parse all files
        for vfile in sorted(v_files):
            lemmas = parse_coq_file(vfile, target)
            all_lemmas.extend(lemmas)
    
    if not all_lemmas:
        print("Error: No lemmas found in any directory", file=sys.stderr)
        sys.exit(1)
    
    # Format output
    if args.format == 'csv':
        output = format_table_csv(all_lemmas)
    elif args.format == 'tsv':
        output = format_table_tsv(all_lemmas)
    elif args.format == 'html':
        output = format_table_html(all_lemmas, args.title)
    else:
        output = format_table_markdown(all_lemmas)
    
    print(output)
    print(f"\n# Total: {len(all_lemmas)} lemmas in {total_files} files", file=sys.stderr)


if __name__ == '__main__':
    main()

