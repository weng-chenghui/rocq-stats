# Rocq Stats

A static site generator for Rocq/Coq formalization documentation. Generates browsable HTML documentation with lemma statistics, dependency analysis, and source code links.

## Features

- **Automatic lemma extraction** from `.v` files
- **Main/Helper classification** based on declaration type and comments
- **Dependency analysis** between lemmas
- **Individual lemma detail pages** with GitHub source code links
- **Dark/light theme support**
- **Multi-project support** via YAML configuration

## Live Site

Visit the generated documentation at: https://weng-chenghui.github.io/rocq-stats/

## Projects

Currently documented projects:

- **[DSDP Formalization](https://weng-chenghui.github.io/rocq-stats/dsdp/)** - Dual protocols for private multi-party matrix multiplication

## Adding or Updating a Project

External projects can add or update their documentation by submitting a Pull Request.

### Step 1: Prepare Your YAML Configuration

Create a YAML file with your project configuration:

```yaml
name: my-project
title: "My Project Title"
description: "Short description of the project"

source:
  repo: "https://github.com/user/repo.git"
  branch: "main"
  commit: "abc123def456789..."  # Full 40-character commit hash
  directories:
    - "src"

index: "path/to/overview.md"  # Optional: Markdown file for overview page
```

**Important:** The `commit` field must be a full 40-character SHA hash. This ensures reproducible builds and precise source code links.

### Step 2: Submit a Pull Request

1. Fork this repository
2. Add your YAML file to the `projects/` directory (or update an existing one)
3. Submit a Pull Request

The PR will automatically:
- Validate your YAML configuration
- Build the documentation site
- Commit the generated HTML back to your PR
- Auto-merge once the build succeeds

### Step 3: Update Your Documentation

When your source repository changes, submit a new PR with an updated `commit` hash in your YAML file.

---

## Local Development

```bash
# Clone the repository
git clone https://github.com/weng-chenghui/rocq-stats.git
cd rocq-stats

# Setup and build (using Makefile)
make setup   # Create venv and install dependencies
make build   # Build the site

# Or manually:
pip install jinja2 markdown pyyaml
cd generator
python build.py

# Build with a local source directory (skip cloning)
python build.py --local /path/to/local/repo
```

### Command Line Options

```
usage: build.py [-h] [--project PROJECT] [--output OUTPUT] [--local LOCAL] [--projects-dir PROJECTS_DIR]

Build Rocq Stats documentation site

options:
  -h, --help            show this help message and exit
  --project PROJECT, -p PROJECT
                        Project YAML file(s) to build (can be specified multiple times)
  --output OUTPUT, -o OUTPUT
                        Output directory (default: ../rocq-stats)
  --local LOCAL, -l LOCAL
                        Use local source directory instead of cloning
  --projects-dir PROJECTS_DIR
                        Directory containing project YAML files (default: ../projects)
```

## Directory Structure

```
rocq-stats/
├── generator/                # Site generator scripts
│   ├── build.py              # Main build script
│   ├── templates/            # Jinja2 HTML templates
│   └── static/               # CSS, JS
├── projects/                 # Project configurations (YAML files)
│   └── dsdp.yaml
├── rocq-stats/               # Generated output (GitHub Pages)
│   ├── index.html            # Root index listing all projects
│   └── dsdp/                 # DSDP project subsite
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md  # PR template for project submissions
│   └── workflows/
│       ├── build.yml         # Main build & deploy workflow
│       └── pr-build.yml      # PR build & auto-merge workflow
├── Makefile                  # Build automation
└── AGENTS.md                 # AI agent instructions
```

## Lemma Classification

Lemmas are classified as **Main** or **Helper** based on:

- **Main Results**: `Theorem` declarations OR lemmas with "main" in their comment
- **Helper Lemmas**: Everything else

To mark a lemma as a main result, add "main" to the comment:

```coq
(* Main privacy lemma: H((V2,V3) | constraint) = log(m) *)
Lemma dsdp_centropy_uniform_solutions : `H(VarRV | CondRV) = log (m%:R : R).
```

## License

MIT License

## Related

- [Rocq Prover](https://rocq-prover.org/) - The Rocq proof assistant (formerly Coq)
- [infotheo](https://github.com/affeldt-aist/infotheo) - Information theory and error-correcting codes in Coq

