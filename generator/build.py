#!/usr/bin/env python3
"""
Rocq Stats - Static site generator for Rocq/Coq formalizations

Builds a static HTML site from Coq source files with:
- Lemma statistics with Main/Helper classification
- Dependency analysis
- Individual lemma detail pages
- Project overview pages
"""

import os
import re
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any
from tempfile import TemporaryDirectory

try:
    from jinja2 import Environment, FileSystemLoader
    import markdown
    import yaml
except ImportError:
    print("Error: Required packages not installed.")
    print("Run: pip install jinja2 markdown pyyaml")
    sys.exit(1)


# Default configuration
DEFAULT_OUTPUT_DIR = "../rocq-stats"
PROJECTS_DIR = "../projects"


@dataclass
class ProjectConfig:
    """Configuration for a single project."""
    name: str
    title: str
    description: str
    repo_url: str
    branch: str
    directories: List[str]
    index_file: str  # Markdown file for overview page
    
    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'ProjectConfig':
        """Load project config from YAML file."""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls(
            name=data['name'],
            title=data['title'],
            description=data.get('description', ''),
            repo_url=data['source']['repo'],
            branch=data['source']['branch'],
            directories=data['source']['directories'],
            index_file=data.get('index', ''),
        )


@dataclass
class LemmaInfo:
    file_name: str
    section: str
    name: str
    signature: str
    meaning: str
    proof_lines: int
    declaration_type: str = "Lemma"
    is_helper: bool = False
    is_main: bool = False
    uses: List[str] = field(default_factory=list)
    used_by: List[str] = field(default_factory=list)


def extract_preceding_comment(lines: List[str], lemma_line_idx: int) -> str:
    """Extract comment block immediately preceding a lemma."""
    idx = lemma_line_idx - 1
    
    while idx >= 0 and lines[idx].strip() == '':
        idx -= 1
    
    if idx >= 0:
        line = lines[idx].strip()
        if line.startswith('(*') and line.endswith('*)'):
            return line[2:-2].strip()
    
    in_comment = False
    comment_lines = []
    
    while idx >= 0:
        line = lines[idx].strip()
        
        if line.endswith('*)') and not in_comment:
            in_comment = True
            content = line[:-2].strip() if line != '*)' else ''
            if content:
                comment_lines.insert(0, content)
        elif line.startswith('(*') and in_comment:
            content = line[2:].strip() if line != '(*' else ''
            if content:
                comment_lines.insert(0, content)
            break
        elif in_comment:
            cleaned = line.lstrip('*').strip()
            if cleaned:
                comment_lines.insert(0, cleaned)
        elif line == '':
            if not in_comment:
                break
        else:
            break
        idx -= 1
    
    if comment_lines:
        result = ' '.join(comment_lines)
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
        line = re.sub(r'\(\*.*?\*\)', '', line)
        signature_lines.append(line)
        
        paren_depth += line.count('(') - line.count(')')
        paren_depth += line.count('[') - line.count(']')
        paren_depth += line.count('{') - line.count('}')
        
        if ':' in line:
            found_colon = True
        
        if line.rstrip().endswith('.') and paren_depth <= 0 and found_colon:
            break
        
        if 'Proof' in line or 'Proof.' in line:
            signature_lines[-1] = re.sub(r'\bProof\.?', '', signature_lines[-1]).strip()
            break
        
        idx += 1
        if idx - start_idx > 20:
            break
    
    sig = ' '.join(signature_lines)
    sig = re.sub(r'\s+', ' ', sig).strip()
    sig = re.sub(r'\s*Proof\.?\s*$', '', sig)
    return sig


def count_proof_lines(lines: List[str], start_idx: int) -> int:
    """Count the number of lines in a proof."""
    idx = start_idx
    proof_started = False
    proof_start_line = start_idx
    
    while idx < len(lines):
        line = lines[idx].strip()
        line_no_comment = re.sub(r'\(\*.*?\*\)', '', line)
        
        if re.search(r'\bProof\b', line_no_comment):
            proof_started = True
            proof_start_line = idx
            break
        
        if re.search(r'\b(Qed|Defined|Admitted)\b', line_no_comment):
            return 1
        
        idx += 1
        if idx - start_idx > 30:
            return 0
    
    if not proof_started:
        return 0
    
    proof_lines = 0
    idx = proof_start_line
    
    while idx < len(lines):
        line = lines[idx].strip()
        line_no_comment = re.sub(r'\(\*.*?\*\)', '', line)
        
        if line and not line.startswith('(*'):
            proof_lines += 1
        
        if re.search(r'\b(Qed|Defined|Admitted)\b', line_no_comment):
            break
        
        idx += 1
        if idx - proof_start_line > 500:
            break
    
    return max(1, proof_lines)


def extract_proof_body(lines: List[str], start_idx: int) -> str:
    """Extract the proof body from a lemma."""
    idx = start_idx
    proof_started = False
    proof_lines = []
    
    while idx < len(lines):
        line = lines[idx].strip()
        line_no_comment = re.sub(r'\(\*.*?\*\)', '', line)
        
        if re.search(r'\bProof\b', line_no_comment):
            proof_started = True
            proof_lines.append(lines[idx])
            idx += 1
            break
        
        if re.search(r'\b(Qed|Defined|Admitted)\b', line_no_comment):
            return lines[idx]
        
        idx += 1
        if idx - start_idx > 30:
            return ''
    
    if not proof_started:
        return ''
    
    while idx < len(lines):
        proof_lines.append(lines[idx])
        line_no_comment = re.sub(r'\(\*.*?\*\)', '', lines[idx])
        if re.search(r'\b(Qed|Defined|Admitted)\b', line_no_comment):
            break
        idx += 1
        if len(proof_lines) > 500:
            break
    
    return '\n'.join(proof_lines)


def classify_lemma(lemma: LemmaInfo) -> None:
    """Classify lemma as Main or Helper based on type and comment."""
    meaning_lower = lemma.meaning.lower()
    
    if lemma.declaration_type == 'Theorem':
        lemma.is_main = True
        lemma.is_helper = False
    elif 'main' in meaning_lower:
        lemma.is_main = True
        lemma.is_helper = False
    else:
        lemma.is_main = False
        lemma.is_helper = True


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
    
    try:
        relative_path = filepath.relative_to(base_dir)
    except ValueError:
        relative_path = filepath
    
    current_section = "Top-level"
    section_stack = ["Top-level"]
    
    lemma_pattern = re.compile(
        r'^\s*(Lemma|Theorem|Corollary|Proposition|Fact|Remark)\s+(\w+)',
        re.MULTILINE
    )
    
    section_start = re.compile(r'^\s*Section\s+(\w+)\s*\.', re.MULTILINE)
    section_end = re.compile(r'^\s*End\s+(\w+)\s*\.', re.MULTILINE)
    
    for idx, line in enumerate(lines):
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
        
        lemma_match = lemma_pattern.match(line)
        if lemma_match:
            decl_type = lemma_match.group(1)
            lemma_name = lemma_match.group(2)
            
            signature = extract_signature(lines, idx)
            meaning = extract_preceding_comment(lines, idx)
            proof_lines = count_proof_lines(lines, idx)
            
            lemma = LemmaInfo(
                file_name=str(relative_path),
                section=current_section,
                name=lemma_name,
                signature=signature,
                meaning=meaning,
                proof_lines=proof_lines,
                declaration_type=decl_type
            )
            classify_lemma(lemma)
            lemmas.append(lemma)
    
    return lemmas


def analyze_dependencies(lemmas: List[LemmaInfo], coq_dirs: List[Path]) -> None:
    """Analyze which lemmas use other lemmas."""
    all_names = {l.name for l in lemmas}
    
    files_to_lemmas: Dict[str, List[LemmaInfo]] = {}
    for l in lemmas:
        if l.file_name not in files_to_lemmas:
            files_to_lemmas[l.file_name] = []
        files_to_lemmas[l.file_name].append(l)
    
    for file_name, file_lemmas in files_to_lemmas.items():
        filepath = None
        for coq_dir in coq_dirs:
            candidate = coq_dir / file_name
            if candidate.exists():
                filepath = candidate
                break
        
        if not filepath:
            continue
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.read().split('\n')
        except Exception:
            continue
        
        for lemma in file_lemmas:
            lemma_pattern = re.compile(
                rf'^\s*(Lemma|Theorem|Corollary|Proposition|Fact|Remark)\s+{re.escape(lemma.name)}\b'
            )
            
            for idx, line in enumerate(lines):
                if lemma_pattern.match(line):
                    proof_body = extract_proof_body(lines, idx)
                    proof_clean = re.sub(r'\(\*.*?\*\)', '', proof_body, flags=re.DOTALL)
                    
                    for name in all_names:
                        if name == lemma.name:
                            continue
                        if re.search(rf'\b{re.escape(name)}\b', proof_clean):
                            lemma.uses.append(name)
                    break
    
    name_to_lemma = {l.name: l for l in lemmas}
    for lemma in lemmas:
        for used_name in lemma.uses:
            if used_name in name_to_lemma:
                name_to_lemma[used_name].used_by.append(lemma.name)


def load_index_markdown(index_path: Path) -> str:
    """Load and convert index markdown file to HTML."""
    if not index_path.exists():
        return "<p>Index documentation not found.</p>"
    
    with open(index_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    html = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'toc']
    )
    return html


def clone_repo(repo_url: str, branch: str, dest_dir: Path) -> bool:
    """Clone a git repository."""
    try:
        cmd = ['git', 'clone', '--depth', '1', '--branch', branch, repo_url, str(dest_dir)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Warning: Failed to clone {repo_url}: {result.stderr}", file=sys.stderr)
            return False
        return True
    except Exception as e:
        print(f"Warning: Exception cloning {repo_url}: {e}", file=sys.stderr)
        return False


def build_project(
    config: ProjectConfig,
    source_root: Path,
    output_dir: Path,
    env: Environment,
    base_context: Dict[str, Any]
) -> Dict[str, Any]:
    """Build a single project's documentation site."""
    project_output = output_dir / config.name
    project_output.mkdir(parents=True, exist_ok=True)
    (project_output / 'lemmas').mkdir(exist_ok=True)
    (project_output / 'static').mkdir(exist_ok=True)
    
    # Copy static files
    static_src = Path(__file__).parent / 'static'
    static_dst = project_output / 'static'
    for f in static_src.glob('*'):
        shutil.copy(f, static_dst / f.name)
    
    # Parse Coq files
    print(f"  Parsing Coq files for {config.name}...")
    all_lemmas = []
    coq_dirs = []
    
    for dir_name in config.directories:
        coq_dir = source_root / dir_name
        if not coq_dir.exists():
            print(f"  Warning: Directory {coq_dir} not found", file=sys.stderr)
            continue
        
        coq_dirs.append(coq_dir)
        for vfile in sorted(coq_dir.rglob('*.v')):
            lemmas = parse_coq_file(vfile, coq_dir)
            all_lemmas.extend(lemmas)
    
    print(f"  Found {len(all_lemmas)} lemmas")
    
    # Analyze dependencies
    analyze_dependencies(all_lemmas, coq_dirs)
    
    # Calculate statistics
    total_lemmas = len(all_lemmas)
    total_files = len(set(l.file_name for l in all_lemmas))
    main_lemmas = [l for l in all_lemmas if l.is_main]
    helper_lemmas = [l for l in all_lemmas if l.is_helper]
    theorems = [l for l in all_lemmas if l.declaration_type == 'Theorem']
    total_deps = sum(len(l.uses) for l in all_lemmas)
    
    # GitHub URLs
    github_repo = config.repo_url.replace('.git', '').replace('https://github.com/', '')
    github_blob_base = f"https://github.com/{github_repo}/blob/{config.branch}"
    github_raw_base = f"https://raw.githubusercontent.com/{github_repo}/{config.branch}"
    
    # Project-specific context
    project_context = {
        **base_context,
        'site_title': config.title,
        'site_description': config.description,
        'project_name': config.name,
        'total_lemmas': total_lemmas,
        'total_files': total_files,
        'github_blob_base': github_blob_base,
        'github_raw_base': github_raw_base,
        'coq_source_root': config.directories[0] if config.directories else '',
    }
    
    # Load index markdown
    index_html = ""
    if config.index_file:
        index_path = source_root / config.index_file
        index_html = load_index_markdown(index_path)
    
    # Build index page
    print(f"  Building index page...")
    index_template = env.get_template('index.html')
    index_content = index_template.render(
        **project_context,
        active_tab='overview',
        is_subpage=False,
        layer_design_html=index_html,
        main_count=len(main_lemmas),
        helper_count=len(helper_lemmas),
        theorem_count=len(theorems),
    )
    with open(project_output / 'index.html', 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    # Build stats page
    print(f"  Building stats page...")
    files_dict = {}
    for l in all_lemmas:
        if l.file_name not in files_dict:
            files_dict[l.file_name] = {'main': [], 'helper': []}
        if l.is_helper:
            files_dict[l.file_name]['helper'].append(l)
        else:
            files_dict[l.file_name]['main'].append(l)
    
    stats_template = env.get_template('stats.html')
    stats_content = stats_template.render(
        **project_context,
        active_tab='stats',
        is_subpage=False,
        lemmas=all_lemmas,
        main_lemmas=main_lemmas,
        helper_lemmas=helper_lemmas,
        files=files_dict,
        main_count=len(main_lemmas),
        helper_count=len(helper_lemmas),
    )
    with open(project_output / 'stats.html', 'w', encoding='utf-8') as f:
        f.write(stats_content)
    
    # Build dependencies page
    print(f"  Building dependencies page...")
    deps_template = env.get_template('dependencies.html')
    deps_content = deps_template.render(
        **project_context,
        active_tab='dependencies',
        is_subpage=False,
        lemmas=all_lemmas,
        total_deps=total_deps,
    )
    with open(project_output / 'dependencies.html', 'w', encoding='utf-8') as f:
        f.write(deps_content)
    
    # Build individual lemma pages
    print(f"  Building lemma detail pages...")
    lemma_template = env.get_template('lemma.html')
    name_to_lemma = {l.name: l for l in all_lemmas}
    
    for lemma in all_lemmas:
        lemma_content = lemma_template.render(
            **project_context,
            active_tab=None,
            is_subpage=True,
            lemma=lemma,
            uses_lemmas=[name_to_lemma[n] for n in lemma.uses if n in name_to_lemma],
            used_by_lemmas=[name_to_lemma[n] for n in lemma.used_by if n in name_to_lemma],
        )
        with open(project_output / 'lemmas' / f'{lemma.name}.html', 'w', encoding='utf-8') as f:
            f.write(lemma_content)
    
    return {
        'name': config.name,
        'title': config.title,
        'description': config.description,
        'total_lemmas': total_lemmas,
        'total_files': total_files,
        'main_count': len(main_lemmas),
        'helper_count': len(helper_lemmas),
        'theorem_count': len(theorems),
        'total_deps': total_deps,
    }


def build_root_index(
    projects_info: List[Dict[str, Any]],
    output_dir: Path,
    env: Environment
) -> None:
    """Build the root index page listing all projects."""
    root_template = env.get_template('root_index.html')
    root_content = root_template.render(
        site_title='Rocq Stats',
        site_description='Lemma statistics and documentation for Rocq/Coq formalizations',
        projects=projects_info,
        generated_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    )
    with open(output_dir / 'index.html', 'w', encoding='utf-8') as f:
        f.write(root_content)
    
    # Copy static files to root
    static_src = Path(__file__).parent / 'static'
    static_dst = output_dir / 'static'
    static_dst.mkdir(exist_ok=True)
    for f in static_src.glob('*'):
        shutil.copy(f, static_dst / f.name)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Build Rocq Stats documentation site')
    parser.add_argument(
        '--project', '-p',
        action='append',
        help='Project YAML file(s) to build (can be specified multiple times)'
    )
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Output directory (default: ../rocq-stats)'
    )
    parser.add_argument(
        '--local', '-l',
        help='Use local source directory instead of cloning'
    )
    parser.add_argument(
        '--projects-dir',
        default=None,
        help='Directory containing project YAML files (default: ../projects)'
    )
    args = parser.parse_args()
    
    generator_dir = Path(__file__).parent
    
    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = (generator_dir / DEFAULT_OUTPUT_DIR).resolve()
    
    # Determine projects directory
    if args.projects_dir:
        projects_dir = Path(args.projects_dir)
    else:
        projects_dir = (generator_dir / PROJECTS_DIR).resolve()
    
    # Load project configurations
    project_configs = []
    if args.project:
        for p in args.project:
            project_configs.append(ProjectConfig.from_yaml(Path(p)))
    else:
        # Load all projects from projects directory
        if projects_dir.exists():
            for yaml_file in sorted(projects_dir.glob('*.yaml')):
                project_configs.append(ProjectConfig.from_yaml(yaml_file))
    
    if not project_configs:
        print("Error: No project configurations found.", file=sys.stderr)
        print(f"Add YAML files to {projects_dir} or specify with --project", file=sys.stderr)
        sys.exit(1)
    
    print(f"Building {len(project_configs)} project(s)...")
    print(f"Output: {output_dir}")
    
    # Setup output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup Jinja environment
    env = Environment(
        loader=FileSystemLoader(generator_dir / 'templates'),
        autoescape=True
    )
    
    base_context = {
        'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    projects_info = []
    
    for config in project_configs:
        print(f"\nBuilding project: {config.title}")
        
        if args.local:
            # Use local source directory
            source_root = Path(args.local)
            if not source_root.exists():
                print(f"Error: Local source not found: {source_root}", file=sys.stderr)
                continue
            
            info = build_project(config, source_root, output_dir, env, base_context)
            projects_info.append(info)
        else:
            # Clone repo to temporary directory
            with TemporaryDirectory() as tmpdir:
                source_root = Path(tmpdir)
                print(f"  Cloning {config.repo_url} ({config.branch})...")
                if clone_repo(config.repo_url, config.branch, source_root):
                    info = build_project(config, source_root, output_dir, env, base_context)
                    projects_info.append(info)
                else:
                    print(f"  Skipping {config.name} due to clone failure")
    
    # Build root index
    print("\nBuilding root index...")
    build_root_index(projects_info, output_dir, env)
    
    print(f"\nSite built successfully!")
    print(f"Output: {output_dir}")
    for info in projects_info:
        print(f"  - {info['name']}: {info['total_lemmas']} lemmas ({info['main_count']} main, {info['helper_count']} helper)")


if __name__ == '__main__':
    main()
