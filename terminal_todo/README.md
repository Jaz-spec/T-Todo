# Terminal Todo

A terminal-based productivity tool for managing role-based to-do lists with window management and kanban views.

## Current Status

**Iteration 1 Complete** - Foundation established

### What's Working
- ✅ Project structure with modular organization
- ✅ SQLite database with complete schema (6 tables)
- ✅ Autumnal color palette with brightness adjustments
- ✅ Basic Textual TUI with command input
- ✅ Command parser foundation
- ✅ Database initialization and migrations

### What's Next
- Iteration 2: Role creation and single-panel task management
- Iteration 3: Task CRUD operations (view, edit, delete, status)
- Iterations 4-9: Window management, kanban views, navigation, polish

## Installation

### Quick Start with Makefile

```bash
make install    # Create venv and install dependencies
make init       # Initialize database
make test       # Run tests to verify everything works
make run        # Launch the application!
```

### Other Makefile Commands
```bash
make help       # Show all available commands
make clean      # Remove venv and database
make reset      # Clean and reinstall everything
```

### Manual Installation

1. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize database**
   ```bash
   python -m database.migrations
   ```

## Usage

### Run the application
```bash
make run
# or manually: python main.py
```

### Available Commands (Iteration 1)
- `help` - Show help message
- `exit` - Exit application (or press Ctrl+C)
- `hello` - Test command (echoes back)

### Keyboard Shortcuts
- `Ctrl+C` - Quit application
- `Esc` - Clear command input

## Testing

```bash
make test
# or manually: python test_foundation.py
```

## Project Structure

```
terminal_todo/
├── main.py                 # Entry point
├── app.py                  # Main TUI application
├── config.py               # Configuration constants
├── requirements.txt        # Python dependencies
├── database/
│   ├── models.py          # Database connection and operations
│   └── migrations.py      # Schema creation
├── ui/
│   ├── panels.py          # Role panel widgets (coming in Iteration 2)
│   ├── kanban.py          # Kanban view (coming in Iteration 5)
│   ├── input_box.py       # Command input widget
│   └── task_detail.py     # Task detail view
├── commands/
│   ├── parser.py          # Command parsing
│   ├── role_commands.py   # Role management commands
│   ├── task_commands.py   # Task management commands
│   └── window_commands.py # Window management commands
└── utils/
    ├── colors.py          # Color management
    ├── date_utils.py      # Date parsing and formatting
    └── validators.py      # Input validation
```

## Technology Stack

- **Language**: Python 3.10+
- **TUI Framework**: Textual 6.3.0
- **Database**: SQLite3
- **Styling**: Rich 14.2.0
- **Date Handling**: python-dateutil 2.9.0

## Development Philosophy

This project follows an iterative, learning-focused approach:
- Each iteration produces a working, testable application
- Features are built horizontally (across the app) before adding depth
- Simplicity first, complexity added incrementally
- Continuous testing and refactoring

## License

See project root for license information.

## Iteration Progress

- [x] **Iteration 1**: Foundation (Database, TUI shell, Colors)
- [ ] **Iteration 2**: Core Flow (Roles, Tasks, Single Panel)
- [ ] **Iteration 3**: Task Management (Edit, Delete, Status)
- [ ] **Iteration 4**: Window Management (Multi-panel)
- [ ] **Iteration 5**: Kanban Views
- [ ] **Iteration 6**: Navigation & Role Management
- [ ] **Iteration 7**: Dependencies & Batch Operations
- [ ] **Iteration 8**: Validation & Error Handling
- [ ] **Iteration 9**: Polish & Optimization
