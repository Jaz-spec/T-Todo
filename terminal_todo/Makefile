.PHONY: help install init test run clean

# Default target
help:
	@echo "Terminal Todo - Makefile Commands"
	@echo "=================================="
	@echo "make install    - Create venv and install dependencies"
	@echo "make init       - Initialize database schema"
	@echo "make test       - Run foundation tests"
	@echo "make run        - Launch the application"
	@echo "make clean      - Remove venv and database"
	@echo "make reset      - Clean and reinstall everything"

# Install dependencies
install:
	@echo "Creating virtual environment..."
	python3 -m venv venv
	@echo "Installing dependencies..."
	./venv/bin/pip install -q --upgrade pip
	./venv/bin/pip install -q -r requirements.txt
	@echo "✓ Installation complete"

# Initialize database
init:
	@echo "Initializing database..."
	./venv/bin/python -m database.migrations
	@echo "✓ Database initialized"

# Run tests
test:
	@echo "Running foundation tests..."
	./venv/bin/python test_foundation.py

# Run the application
run:
	./venv/bin/python main.py

# Clean up
clean:
	@echo "Cleaning up..."
	rm -rf venv
	rm -f todo.db
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Cleanup complete"

# Reset everything
reset: clean install init
	@echo "✓ Reset complete - ready to run!"
