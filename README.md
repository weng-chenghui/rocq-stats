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

## Usage

### Adding a New Project

1. Create a YAML configuration file in `projects/`:

```yaml
name: my-project
title: "My Project Title"
description: "Short description of the project"

source:
  repo: "https://github.com/user/repo.git"
  branch: "main"
  directories:
    - "src"

index: "path/to/overview.md"
```

2. The site will be rebuilt automatically via GitHub Actions, or run manually:

```bash
cd generator
pip install jinja2 markdown pyyaml
python build.py
```

### Local Development

```bash
# Clone the repository
git clone https://github.com/weng-chenghui/rocq-stats.git
cd rocq-stats

# Install dependencies
pip install jinja2 markdown pyyaml

# Build with a local source directory
cd generator
python build.py --local /path/to/local/repo

# Or build from remote repositories
python build.py
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
│   ├── list_lemmas.py        # Lemma parser
│   ├── analyze_dependencies.py
│   ├── templates/            # Jinja2 HTML templates
│   └── static/               # CSS, JS
├── projects/                 # Project configurations
│   └── dsdp.yaml
├── rocq-stats/               # Generated output (GitHub Pages)
│   ├── index.html            # Root index listing all projects
│   └── dsdp/                 # DSDP project subsite
└── .github/workflows/
    └── build.yml             # CI workflow
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

