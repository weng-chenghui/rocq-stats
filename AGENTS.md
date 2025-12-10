# AI Agent Instructions

## Quick Start with Makefile

The easiest way to build the site:

```bash
make setup   # First time: create venv and install deps
make build   # Build the static site
```

Or just run `make` which will do both (setup if needed, then build).

## Virtual Environment Setup

This project uses a Python virtual environment for dependency management:

```bash
# Create and activate venv (first time)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install jinja2 markdown pyyaml
```

To activate the venv in subsequent sessions:
```bash
source venv/bin/activate
```

## Important: Sandbox Restrictions

**Do NOT use sandbox mode when installing Python dependencies.** The pip command requires full system access to read SSL certificates and write to the virtual environment.

When running `pip install`, always use:
```
required_permissions: ["all"]
```

## Building the Site

After activating the venv, run the build script:
```bash
cd generator
python build.py
```

This will clone the source repository and generate the static site in `rocq-stats/`.

