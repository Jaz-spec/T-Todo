# Terminal Productivity Tool - Technical Specification

## 1. Overview

A terminal-based productivity tool for managing role-based to-do lists with window management and kanban views. Built with Python using a TUI (Text User Interface) framework with SQLite for data persistence.
**Target Platform**: macOS (MVP)
**Minimum Terminal Size**: Half screen

## 2. Technology Stack

- **Language**: Python 3.10+
- **TUI Framework**: Rich or Textual (recommended: Textual for better keyboard handling)
- **Database**: SQLite3
- **Dependencies**:
  - `textual` or `rich` for TUI
  - `sqlite3` (built-in)
  - `python-dateutil` for date parsing
  - `prompt_toolkit` for input handling with history

## 3. Data Model

### 3.1 Database Schema

```sql
-- Roles table
CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_number INTEGER UNIQUE NOT NULL,
    name TEXT NOT NULL,
    color TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks table
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    task_number INTEGER NOT NULL, -- per-role task numbering
    title TEXT NOT NULL,
    description TEXT, -- markdown formatted
    due_date TEXT, -- ISO format YYYY-MM-DD
    priority TEXT CHECK(priority IN ('High', 'Medium', 'Low')),
    story_points INTEGER CHECK(story_points IN (1, 2, 3, 5, 8, 13)),
    status TEXT CHECK(status IN ('todo', 'doing', 'done')) DEFAULT 'todo',
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    UNIQUE(role_id, task_number)
);

-- Task dependencies (blocking relationships)
CREATE TABLE task_dependencies (
    task_id INTEGER NOT NULL,
    blocks_task_id INTEGER NOT NULL, -- this task blocks another task
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (blocks_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, blocks_task_id)
);

-- Window layouts (persisted between sessions)
CREATE TABLE window_layout (
    id INTEGER PRIMARY KEY CHECK (id = 1), -- only one layout stored
    panel_count INTEGER NOT NULL,
    panel_roles TEXT NOT NULL -- JSON array of role IDs in order
);

-- Undo stack (for deletions only)
CREATE TABLE undo_stack (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT CHECK(action_type IN ('delete_task', 'delete_role')),
    data TEXT NOT NULL, -- JSON serialized data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Archive cleanup tracking
CREATE TABLE archived_tasks (
    task_id INTEGER PRIMARY KEY,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 Color Palette (Autumnal Theme)

```python
ROLE_COLORS = [
    "#D4A574",  # Tan
    "#C17817",  # Dark Orange
    "#8B4513",  # Saddle Brown
    "#CD853F",  # Peru
    "#A0522D",  # Sienna
    "#DAA520",  # Goldenrod
    "#B8860B",  # Dark Goldenrod
    "#8B7355",  # Burlywood Dark
]
```

## 4. User Interface Layout
### 4.1 Screen Structure
```
┌─────────────────────────────────────────────────────┐
│                                                     │
│           MAIN CONTENT AREA                         │
│         (Role Panels / Kanban View)                 │
│                                                     │
│                                                     │
└─────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────┐
│ > [command input box - full width]                  │
└─────────────────────────────────────────────────────┘
```

### 4.2 Role Panel Layout

```
┌─ Role Name (rX) ──────────────────────-┐
│                                        │
│ ┄┄┄┄┄┄┄┄┄ IN PROGRESS ┄┄┄┄┄┄┄┄┄┄┄┄┄┄   │
│ t1: Task title - Tomorrow              │
│ t2: Another task - Next Monday         │
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄   │
│                                        │
│ t3: Task title - Yesterday             │
│ t4: Task with dep - Tues 15 Oct        │
│ t5: Another task - 20 Oct              │
│                                        │
└────────────────────────────────────────┘
```

**Visual Details**:
- Border radius: 4px equivalent in terminal chars
- Gap between panels: 2 characters
- Active panel: brighter role color
- Inactive panels: normal role color
- Blocked tasks: dulled shade of role color (70% brightness)
- In-progress separator: thin dashed line in role color

### 4.3 Kanban View Layout

```
┌─ Role Name (rX) - KANBAN ────────────────────────────────┐
│                                                           │
│  TODO              DOING              DONE               │
│ ┌────────────┐    ┌────────────┐    ┌────────────┐      │
│ │t1: Task    │    │t2: Task    │    │t5: Task    │      │
│ │  Due: Tmrw │    │  Due: Mon  │    │  Completed │      │
│ │  Pri: High │    │  Pri: Med  │    │  SP: 5     │      │
│ │  SP: 3     │    │  SP: 8     │    │             │      │
│ │            │    │            │    │             │      │
│ │t3: Task    │    │            │    │             │      │
│ │  Due: 15Oct│    │            │    │             │      │
│ │  Pri: Low  │    │            │    │             │      │
│ │  SP: 2     │    │            │    │             │      │
│ └────────────┘    └────────────┘    └────────────┘      │
└───────────────────────────────────────────────────────────┘
```

### 4.4 Task Detail View

```
┌─ Task Details ──────────────────────────────────────────┐
│                                                          │
│ Task: t4 - Call boss about project                      │
│                                                          │
│ Due: Tomorrow (15 Oct 2025)                             │
│ Priority: High                                           │
│ Story Points: 5                                          │
│ Status: In Progress                                      │
│                                                          │
│ Blocks: t7, t9                                          │
│ Blocked by: t2                                          │
│                                                          │
│ Description:                                             │
│ ─────────────────────────────────────────────────────   │
│ Need to discuss the following:                          │
│ - Budget allocation                                      │
│ - Timeline adjustments                                   │
│ - Resource requirements                                  │
│                                                          │
│                                                          │
│ [Press any key to return]                               │
└──────────────────────────────────────────────────────────┘
```

## 5. Input Modes

### 5.1 Command Mode (Default)
- Text input box active
- Type commands
- Arrow up/down: cycle command history
- Enter: execute command
- Esc: clear current input

### 5.2 Navigation Mode
- Arrow keys: scroll through focused panel
- Space + Arrow keys: move window position
- Tab: cycle focus between visible panels
- Esc: return to command mode
- Any text key: return to command mode and start typing

**Mode Indicator**: Show "(nav)" in corner of command box when in navigation mode

## 6. Command Reference

### 6.1 Role Management

#### Create New Role
```
> new role
Role name: _
[user types and presses enter]
Select color: [TAB to cycle through colors, ENTER to confirm]
```

**Process**:
1. Input box expands to 1/3 screen height
2. Prompt for role name
3. Show color selector with visual preview
4. Assign next available display number
5. Create role in database
6. Return to normal view

#### List Roles
```
> r [TAB to cycle through roles]
Shows: r1 - Work, r2 - Personal, r3 - Learning, ...
```

#### Remap Role Numbers
```
> role remap
[Shows full list with current numbers]
1: Work
2: Personal
3: Learning

Enter new mapping (leave blank to keep current):
Work: 3
Personal: 1
Learning: 2
```

#### Select Role
```
> r5
[Selects role 5 as active, all subsequent commands apply to this role]
[Visual indicator shows which role is active]
```

#### Delete Role
```
> delete
Are you sure you want to delete role "Work"? (yes/no): _
```

### 6.2 Window Management

#### Create Window Layout
```
> window 3
[Shows role selector, TAB to cycle, ENTER to confirm each]
Panel 1: [TAB through roles]
Panel 2: [TAB through roles]
Panel 3: [TAB through roles]
```

**Layout Priority**:
- 1 panel: full screen
- 2 panels: side by side (50/50)
- 3 panels: left (50%) + right top/bottom (25% each)
- 4 panels: 2x2 grid
- 5 panels: left (50%) + right 3 stacked (16.6% each)
- 6 panels: 2x3 grid
- 7 panels: left 3 stacked + right 4 stacked
- 8 panels: left 4 stacked + right 4 stacked (max)

#### Close Window
```
> close
[Closes currently focused panel]
```

### 6.3 Task Management (Role View)

#### Add Task (Interactive)
```
> add
Title: _
[user types and presses enter]
Description (optional, press ENTER to skip or type multi-line with SHIFT+ENTER): _
Due date (optional, format DD MM YY): _
Priority (High/Medium/Low, optional): _
Story points (1,2,3,5,8,13, optional): _
Blocked by task IDs (comma-separated, optional): _
```

#### Quick Add Task
```
> add "Call boss" 15 10 25 High 5
[Creates task with: title, due date, priority, story points]

> add "Quick task"
[Creates task with just title, rest defaults]
```

#### View Task
```
> t4 view
[Shows full-screen task detail view]
```

#### Edit Task
```
> t4 edit
[Goes through same prompts as add, showing current values]
Title (Call boss): _
Description (...): _
[etc.]
```

#### Delete Task
```
> t4 delete
Are you sure? (yes/no): _
```

#### Mark Task Status
```
> t4 doing
[Moves task to "doing" status]

> t4 done
[Moves task to "done" status, sets completed_at timestamp]

> t4 todo
[Moves task back to "todo" status]
```

#### Batch Operations
```
> t1,t3,t5 delete
Are you sure you want to delete 3 tasks? (yes/no): _

> t2,t4,t6 doing
[Moves all specified tasks to doing]
```

### 6.4 Kanban View

#### Enter Kanban View
```
> k
[Shows kanban board for currently selected role]
```

#### Exit Kanban View
```
> r
[Returns to role view]
```

Task commands work identically in kanban view (t4 edit, t4 doing, etc.)

### 6.5 Utility Commands

#### Help
```
> help
[Shows command reference]

> help roles
[Shows role-specific commands]

> help tasks
[Shows task-specific commands]
```

#### Undo
```
> undo
[Restores last deleted task or role]
[Shows: "Restored task: 't4 - Call boss'"]
```

#### Exit
```
> exit
[Exits application]

Ctrl+C also exits
```

## 7. Date Handling

### 7.1 Input Formats
```python
# Accepted formats
DD MM YY          # 15 10 25
DD MM YYYY        # 15 10 2025
+Xd               # +3d (3 days from now)
tomorrow
today
```

### 7.2 Display Formats
```python
# Relative display rules
same_day = "Today"
next_day = "Tomorrow"
previous_day = "Yesterday"
within_7_days = "Next Monday", "Next Friday", etc.
same_week_past = "Monday", "Tuesday", etc.
beyond_7_days = "Tues 15 Oct", "Wed 23 Oct", etc.
```

## 8. Visual Design System

### 8.1 Typography
- Font: Monospace (system default)
- All text inherits role color
- Blocked task text: 70% brightness of role color

### 8.2 Borders and Spacing
- Border radius: Use Unicode box drawing characters with rounded corners where possible
- Panel gap: 2 character spaces
- Internal padding: 1 character space
- Border characters: `┌─┐│└┘` (standard) or `╭─╮│╰╯` (rounded)

### 8.3 Color Brightness Levels
- Active panel: 100% brightness
- Inactive panel: 100% brightness (no dimming when not selected, only brighten on selection)
- Selected panel: 120% brightness
- Blocked task: 70% brightness
- In-progress separator: 100% brightness, dashed line

### 8.4 Empty States
- Empty role panel: Shows panel with role name, no tasks listed
- Empty kanban column: Shows column header, empty space below
- No roles: Empty main area with hint text: "Type 'new role' to get started"

## 9. Application Behavior

### 9.1 Auto-save
- All changes save immediately to database
- No manual save command needed
- Debounce rapid changes (300ms) to avoid excessive writes

### 9.2 Auto-archive
- Background task checks every hour for completed tasks
- Tasks in "done" status for >24 hours moved to archived_tasks table
- Archived tasks deleted from main tasks table
- No UI indication of archiving (silent cleanup)

### 9.3 Task Numbering
- Task numbers are per-role and sequential
- When task deleted, number is NOT reused
- Display shows: `t1`, `t2`, `t3`, etc.
- When new task added, gets next available number for that role

### 9.4 Startup Behavior
- Load saved window layout from database
- If no layout exists, show empty interface
- No tutorial or prompts
- Command box ready for input

### 9.5 Error Handling
```python
# Error message examples
"Task t99 not found in role r3"
"Invalid command. Type 'help' for available commands"
"Role r10 does not exist"
"Invalid date format. Use DD MM YY"
"Cannot delete role with active tasks. Move or delete tasks first"
```

### 9.6 Task Sorting
Default sort order in role view:
1. In-progress tasks (by due date, then created date)
2. Separator line
3. Todo tasks (by due date, then created date)
4. Tasks without due date at bottom (by created date)

## 10. Keyboard Shortcuts Summary

```
COMMAND MODE (default)
- Type any command
- ↑/↓         Command history
- Enter       Execute command
- Esc         Clear input
- Tab         Autocomplete (context-aware)

NAVIGATION MODE
- Arrow keys  Scroll in focused panel
- Space+Arrow Move panel position
- Tab         Cycle focus between panels
- Esc         Return to command mode
- Any letter  Start typing command

UNIVERSAL
- Ctrl+C      Exit application
```

## 11. Implementation Notes

### 11.1 Recommended Python Packages
```python
# requirements.txt
textual>=0.40.0
python-dateutil>=2.8.0
sqlite3  # built-in
rich>=13.0.0  # for markdown rendering
```

### 11.2 Project Structure
```
terminal_todo/
├── main.py                 # Entry point
├── app.py                  # Main TUI application class
├── database/
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy models or raw SQL
│   └── migrations.py      # Schema setup
├── ui/
│   ├── __init__.py
│   ├── panels.py          # Role panel widgets
│   ├── kanban.py          # Kanban view widget
│   ├── input_box.py       # Command input widget
│   └── task_detail.py     # Task detail view
├── commands/
│   ├── __init__.py
│   ├── parser.py          # Command parsing logic
│   ├── role_commands.py
│   ├── task_commands.py
│   └── window_commands.py
├── utils/
│   ├── __init__.py
│   ├── date_utils.py      # Date parsing and formatting
│   ├── colors.py          # Color management
│   └── validators.py      # Input validation
└── config.py              # Constants and configuration
```

### 11.3 Performance Considerations
- Lazy load tasks (only load visible tasks)
- Index database on role_id, status, due_date
- Debounce auto-save operations
- Limit undo stack to last 20 operations

### 11.4 Testing Strategy
- Unit tests for command parser
- Unit tests for date utilities
- Integration tests for database operations
- Manual TUI testing for layout and navigation

## 12. Future Feature Placeholders

Document these for future implementation:
- Task filtering and advanced ordering
- Customizable task detail visibility
- Archive viewing and restoration
- Export/import functionality
- Multi-platform support (Windows, Linux)
- Themes beyond autumnal
- Recurring tasks
- Time tracking
- Search functionality
- Statistics and reports

## 13. MVP Checklist

Priority order for implementation:

1. ✓ Database schema and models
2. ✓ Basic TUI framework setup
3. ✓ Command input box with history
4. ✓ Role creation and management
5. ✓ Single role panel display
6. ✓ Task CRUD operations (add, edit, delete, view)
7. ✓ Task status management (todo/doing/done)
8. ✓ Date parsing and relative display
9. ✓ Window management (multiple panels)
10. ✓ Navigation mode and keyboard controls
11. ✓ Kanban view
12. ✓ Task dependencies (blocking)
13. ✓ Auto-archive completed tasks
14. ✓ Undo for deletions
15. ✓ Window layout persistence
16. ✓ Help system
17. ✓ Error handling and validation
18. ✓ Polish and visual refinements

## 14. Example Usage Flow

```bash
# First launch
$ python main.py

> new role
Role name: Work
Select color: [TAB] [TAB] [ENTER]

> r1

> add "Prepare presentation" 17 10 25 High 8
> add "Email team update"
> add "Review pull requests" 16 10 25 Medium 3

> window 2
Panel 1: [TAB to Work] [ENTER]
Panel 2: [TAB to create new role or select existing]

> new role
Role name: Personal
[Select color]

> r2
> add "Grocery shopping" tomorrow
> add "Call dentist" 18 10 25

> k
[View kanban board for Personal]

> t1 doing
> r
[Back to role view]

> help
[Shows command reference]
```

---

## Document Version
- Version: 1.0
- Date: October 13, 2025
- Status: Ready for Implementation
