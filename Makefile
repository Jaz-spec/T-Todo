.PHONY: help install dev-install init test run clean reset build

# Default target
help:
	@echo "Terminal Todo - Makefile Commands"
	@echo "=================================="
	@echo "make install        - Install package in development mode"
	@echo "make dev-install    - Install with dev dependencies"
	@echo "make init           - Initialize database schema"
	@echo "make test           - Run foundation tests"
	@echo "make run            - Launch the application"
	@echo "make clean          - Remove venv, database, and build artifacts"
	@echo "make reset          - Clean and reinstall everything"
	@echo "make build          - Build distribution packages"

# Install package in development mode
install:
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Installing package in development mode..."
	./venv/bin/pip install -q --upgrade pip
	./venv/bin/pip install -q -e .
	@echo "✓ Installation complete"
	@echo "✓ You can now run: ttodo"

# Install with dev dependencies
dev-install:
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Installing package with dev dependencies..."
	./venv/bin/pip install -q --upgrade pip
	./venv/bin/pip install -q -e ".[dev]"
	@echo "✓ Dev installation complete"

# Initialize database
init:
	@echo "Initializing database..."
	./venv/bin/python -m ttodo.database.migrations
	@echo "✓ Database initialized"

# Run tests
test:
	@echo "Running foundation tests..."
	./venv/bin/python tests/test_foundation.py

# Run the application
run:
	./venv/bin/ttodo

# Build distribution packages
build:
	@echo "Building distribution packages..."
	./venv/bin/pip install -q build
	./venv/bin/python -m build
	@echo "✓ Build complete - check dist/ directory"

# Clean up
clean:
	@echo "Cleaning up..."
	rm -rf venv
	rm -rf build dist *.egg-info
	rm -f todo.db
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cleanup complete"

# Reset everything
reset: clean install init
	@echo "✓ Reset complete - ready to run!"
