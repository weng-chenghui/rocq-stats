# Rocq Stats - Makefile
# Static site generator for Rocq/Coq formalizations

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
GENERATOR := generator
OUTPUT := rocq-stats

.PHONY: all build setup clean help

# Default target
all: build

# Setup virtual environment and install dependencies
setup: $(VENV)/bin/activate

$(VENV)/bin/activate:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install jinja2 markdown pyyaml
	@echo ""
	@echo "Setup complete! Run 'make build' to generate the site."

# Build the static site
build: $(VENV)/bin/activate
	cd $(GENERATOR) && ../$(PYTHON) build.py

# Clean generated output (keeps venv)
clean:
	rm -rf $(OUTPUT)/*/lemmas/*.html
	rm -rf $(OUTPUT)/*/index.html
	rm -rf $(OUTPUT)/*/stats.html
	rm -rf $(OUTPUT)/*/dependencies.html
	@echo "Cleaned generated HTML files."

# Clean everything including venv
clean-all: clean
	rm -rf $(VENV)
	@echo "Cleaned virtual environment."

# Help
help:
	@echo "Rocq Stats - Available targets:"
	@echo ""
	@echo "  make setup     - Create venv and install dependencies"
	@echo "  make build     - Build the static site (runs setup if needed)"
	@echo "  make clean     - Remove generated HTML files"
	@echo "  make clean-all - Remove generated files and venv"
	@echo "  make help      - Show this help message"
	@echo ""
	@echo "First time? Just run 'make' or 'make build'"

