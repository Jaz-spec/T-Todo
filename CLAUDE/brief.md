# Terminal Productivity Tool - Technical Specification

## 1. Overview

A terminal-based productivity tool for managing role-based to-do lists with window management and kanban views. Built with Python using a TUI (Text User Interface) framework with SQLite for data persistence.
**Target Platform**: macOS (MVP)
**Minimum Terminal Size**: Half screen

## 2. Technology Stack

- **Language**: Typescript
- **Runtime**: Bun
- **TUI Frameworks**: Rich and Click
- **Database**: SQLite

## 3. Data Model

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

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_tasks_role_status
ON tasks(role_id, status, due_date);

CREATE INDEX IF NOT EXISTS idx_tasks_due_date
ON tasks(due_date);
```

## 4. User Interface Layout
- layout does not affect input behaviour of the app with the exeption of the task view. The only command available in task view is [esc] OR [any key]to exit the view.

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
**Layout Priority**:
- 1 panel: full screen
- 2 panels: side by side (50/50)
- 3 panels: left (50%) + right top/bottom (25% each)
- 4 panels: 2x2 grid
- 5 panels: left (50%) + right 3 stacked (16.6% each)
- 6 panels: 2x3 grid
- 7 panels: left 3 stacked + right 4 stacked
- 8 panels: left 4 stacked + right 4 stacked (max)

```
┌─ Role Name (rX) ──────────────────────-┐
│                                        │
│ ┄┄┄┄┄┄┄┄┄ IN PROGRESS ┄┄┄┄┄┄┄┄┄┄┄┄┄┄   │
│ t1: Task title                         │
│   Due: Tomorrow | Pri: High | SP: 3    │
│   Blocked by: t2 | Blocks: t4          │
│   Desc: Description preview...         │
│                                        │
│ t2: Another task                       │
│   Due: Next Monday | Pri: Medium       │
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄   │
│                                        │
│ t3: Task title                         │
│   Due: Yesterday | Pri: Low | SP: 5    │
│                                        │
│ t4: Task with dependencies             │
│   Due: Tues 15 Oct | SP: 8             │
│   Blocked by: t1, t3                   │
│                                        │
└────────────────────────────────────────┘
```

### 4.3 Kanban View Layout

```
┌─ Role Name (rX) - KANBAN ────────────────────────────────┐
│                                                          │
│  TODO              DOING              DONE               │
│ ┌────────────┐    ┌────────────┐    ┌────────────┐       │
│ │t1: Task    │    │t2: Task    │    │t5: Task    │       │
│ │  Due: Tmrw │    │  Due: Mon  │    │  Completed │       │
│ │  Pri: High │    │  Pri: Med  │    │  SP: 5     │       │
│ │  SP: 3     │    │  SP: 8     │    │            │       │
│ │            │    │            │    │            │       │
│ │t3: Task    │    │            │    │            │       │
│ │  Due: 15Oct│    │            │    │            │       │
│ │  Pri: Low  │    │            │    │            │       │
│ │  SP: 2     │    │            │    │            │       │
│ └────────────┘    └────────────┘    └────────────┘       │
└──────────────────────────────────────────────────────────┘
```

### 4.4 Task Detail View

```
┌─ Task Details ──────────────────────────────────────────┐
│                                                         │
│ Task: t4 - Call boss about project                      │
│                                                         │
│ Due: Tomorrow (15 Oct 2025)                             │
│ Priority: High                                          │
│ Story Points: 5                                         │
│ Status: In Progress                                     │
│                                                         │
│ Blocks: t7, t9                                          │
│ Blocked by: t2                                          │
│                                                         │
│ Description:                                            │
│ ─────────────────────────────────────────────────────   │
│ Need to discuss the following:                          │
│ - Budget allocation                                     │
│ - Timeline adjustments                                  │
│ - Resource requirements                                 │
│                                                         │
│                                                         │
│ [Press any key to return]                               │
└─────────────────────────────────────────────────────────┘
```

## 5. Input Modes
Modes change input behaviour of the app

### 5.1 Command Mode (Default)
Text input box active

#### Commands
- [up down arrow keys]: cycle through command history
- `h`: help box
- `r`: switch to role view
- `k`: switch to kanban view for selected role
- `n`: adds new role
- `m`: remap role IDs
- `w`: adds role to window layout -> tab through available roles
- `c`: removes active role from window layout
- `a`: add task
- `e[task-ID]`: edit task
- `p[task-ID]`: task in progress
- `d[task-ID]`: task done
- `t[task-ID]`: moves task back to todo status
- `v[task-ID]`: view task details
- `D[task-ID]`: delete task
- `Dr[role-ID]`: delete role
- [TAB]: enter navigation mode

### 5.2 Navigation Mode
**Mode Indicator**: Show "(nav)" in corner of command box when in navigation mode

#### Commands
- [arrow keys]: scroll through active panel to see more tasks in that role
- [space + arrow keys]: move panel postion to different location on screen
- [TAB]: cycle focus between visible panels
- [Esc]: return to command mode
- [Any text key]: return to command mode and start typing

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

### 8.4 Colors
    "#D4A574",  # Tan
    "#C17817",  # Dark Orange
    "#8B4513",  # Saddle Brown
    "#CD853F",  # Peru
    "#A0522D",  # Sienna
    "#DAA520",  # Goldenrod
    "#B8860B",  # Dark Goldenrod
    "#8B7355",  # Burlywood Dark

### 8.5 Empty States
- Empty role panel: Shows panel with role name, no tasks listed
- Empty kanban column: Shows column header, empty space below
- No roles: Empty main area with hint text: "Type 'new role' to get started"

---

## Terminal To-Do App - Architecture Documentation

```
┌─────────────────────────────────────────────────────────────────┐
│                          UI LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ InputHandler │  │   Display    │  │ CommandBox   │           │
│  │   (Entry)    │  │  (Renderer)  │  │  (History)   │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│          ↓                                                      │
│  ┌──────────────────────────────────────────────────┐           │
│  │           InputContext (State Manager)           │           │
│  └──────────────────────────────────────────────────┘           │
│          ↓                    ↓                                 │
│  ┌──────────────┐     ┌──────────────┐                          │
│  │ CommandMode  │     │NavigationMode│                          │
│  └──────────────┘     └──────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ TaskService  │  │ RoleService  │  │WindowManager │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                 │
│  ┌──────────────────────────────────────────────────┐           │
│  │         Commands (for undo operations)           │           │
│  │  ┌──────────────┐     ┌──────────────┐           │           │
│  │  │DeleteTaskCmd │     │DeleteRoleCmd │           │           │
│  │  └──────────────┘     └──────────────┘           │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                 │
│  ┌──────────────┐                                               │
│  │  UndoStack   │                                               │
│  └──────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
                 ↓                        ↓
┌──────────────────────────┐    ┌──────────────────────────┐
│     DOMAIN LAYER         │    │      DATA LAYER          │
│  ┌────────────────┐      │    │  ┌────────────────┐      │
│  │     Task       │      │    │  │   Database     │      │
│  │  (data+rules)  │      │    │  │ (connection)   │      │
│  └────────────────┘      │    │  └────────────────┘      │
│  ┌────────────────┐      │    │         ↓                │
│  │     Role       │      │    │  ┌────────────────┐      │
│  │  (data+rules)  │      │    │  │TaskRepository  │      │
│  └────────────────┘      │    │  └────────────────┘      │
│  ┌────────────────┐      │    │  ┌────────────────┐      │
│  │   Priority     │      │    │  │RoleRepository  │      │
│  │    (enum)      │      │    │  └────────────────┘      │
│  └────────────────┘      │    │  ┌────────────────┐      │
│  ┌────────────────┐      │    │  │WindowRepository│      │
│  │    Status      │      │    │  └────────────────┘      │
│  │    (enum)      │      │    │                          │
│  └────────────────┘      │    └──────────────────────────┘
└──────────────────────────┘
```

## Complete Class Relationships

### UI Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                        UI LAYER                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  InputHandler                                                   │
│    ├── has-a → InputContext                                     │
│    └── delegates to → current_mode                              │
│                                                                 │
│  InputContext                                                   │
│    ├── has-a → Application                                      │
│    ├── has-a → CommandBox                                       │
│    ├── has-a → WindowManager                                    │
│    └── has-a → InputMode (current_mode)                         │
│                                                                 │
│  InputMode (abstract)                                           │
│    ├── CommandMode                                              │
│    │    └── implements → handle_key()                           │
│    └── NavigationMode                                           │
│         └── implements → handle_key()                           │
│                                                                 │
│  Display                                                        │
│    ├── has-a → LayoutStrategy (TileLayout/KanbanLayout)         │
│    └── uses → TaskRepository (to get data)                      │
│                                                                 │
│  LayoutStrategy (abstract)                                      │
│    ├── TileLayout                                               │
│    │    └── implements → render()                               │
│    └── KanbanLayout                                             │
│         └── implements → render()                               │
│                                                                 │
│  CommandBox                                                     │
│    ├── stores → command history (List[str])                     │
│    └── manages → current input text                             │
│                                                                 │
│  Panel                                                          │
│    ├── displays → tasks for a role                              │
│    └── manages → scroll position                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Application Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Application                                                    │
│    ├── has-a → TaskService                                      │
│    ├── has-a → RoleService                                      │
│    ├── has-a → WindowManager                                    │
│    ├── has-a → UndoStack                                        │
│    ├── has-a → CommandParser                                    │
│    ├── has-a → ApplicationState                                 │
│    └── method: execute_command(text: str)                       │
│                                                                 │
│  TaskService                                                    │
│    ├── uses → TaskRepository                                    │
│    ├── uses → RoleRepository                                    │
│    ├── creates → Task (domain objects)                          │
│    └── methods:                                                 │
│        ├── add(title, role_id, due_date, ...)                   │
│        ├── edit(task_id, **kwargs)                              │
│        ├── mark_done(task_id)                                   │
│        └── get_tasks_for_role(role_id)                          │
│                                                                 │
│  RoleService                                                    │
│    ├── uses → RoleRepository                                    │
│    └── methods:                                                 │
│        ├── create(name, color)                                  │
│        ├── get_all()                                            │
│        └── delete(role_id)                                      │
│                                                                 │
│  WindowManager                                                  │
│    ├── has-many → Panel                                         │
│    ├── uses → WindowRepository                                  │
│    └── methods:                                                 │
│        ├── create_layout(panel_count, role_ids)                 │
│        ├── focus_next_panel()                                   │
│        └── get_focused_panel()                                  │
│                                                                 │
│  Command (abstract - only for undo operations)                  │
│    ├── abstract methods:                                        │
│    │    ├── execute(context)                                    │
│    │    └── undo(context)                                       │
│    ├── DeleteTaskCommand                                        │
│    │     ├── uses → TaskRepository                              │
│    │     └── stores → deleted task data                         │
│    └── DeleteRoleCommand                                        │
│          ├── uses → RoleRepository                              │
│          └── stores → deleted role data                         │
│                                                                 │
│  UndoStack                                                      │
│    ├── stores → List[Command]                                   │
│    └── methods:                                                 │
│        ├── push(command)                                        │
│        └── pop() → Command                                      │
│                                                                 │
│  ApplicationState                                               │
│    ├── current_role_id: int                                     │
│    └── current_view_mode: ViewMode                              │
│                                                                 │
│  CommandParser                                                  │
│    └── method: parse(text: str) → dict                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
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
- Task reset for a role with no tasks - restarts tasks from 1

### 9.4 Startup Behavior
- Load saved window layout from database
- If no layout exists, show empty interface
- No tutorial or prompts
- Command box ready for input

### 9.5 Task Sorting
Default sort order in role view:
1. In-progress tasks (by due date, then created date)
2. Separator line
3. Todo tasks (by due date, then created date)
4. Tasks without due date at bottom (by created date)

### 9.6 Input Validation and Constraints
Comprehensive validation system to ensure data integrity and provide helpful error messages:

#### 9.6.1 Length Constraints
- **Role names**: Maximum 50 characters
- **Task titles**: Maximum 200 characters
- **Task descriptions**: Maximum 2000 characters
- Error messages indicate the specific constraint violated

#### 9.6.2 Value Normalization
- **Priority**: Case-insensitive input, normalized to capitalized form
  - Accepts: "high", "HIGH", "High" → Stored as: "High"
  - Valid values: High, Medium, Low
- **Status**: Case-insensitive, normalized to lowercase
  - Accepts: "TODO", "todo", "ToDo" → Stored as: "todo"
  - Valid values: todo, doing, done

#### 9.6.3 Dependency Validation
- **Circular dependency detection**: Prevents infinite blocking chains
  - Algorithm recursively checks if adding a dependency would create a cycle
  - Error message: "Cannot add dependency: would create circular dependency chain"
- **Task existence validation**: Ensures blocking tasks exist in the same role
- **Self-blocking prevention**: Tasks cannot block themselves

---

### Domain Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Task                                                           │
│    ├── Properties:                                              │
│    │   ├── id: int                                              │
│    │   ├── role_id: int                                         │
│    │   ├── task_number: int                                     │
│    │   ├── title: str                                           │
│    │   ├── description: str                                     │
│    │   ├── due_date: date                                       │
│    │   ├── priority: Priority                                   │
│    │   ├── story_points: int                                    │
│    │   ├── status: Status                                       │
│    │   └── completed_at: datetime                               │
│    │                                                            │
│    ├── Business Logic Methods:                                  │
│    │   ├── mark_complete()                                      │
│    │   ├── is_overdue() → bool                                  │
│    │   ├── is_blocked() → bool                                  │
│    │   ├── can_be_deleted() → bool                              │
│    │   └── should_be_archived() → bool                          │
│    │                                                            │
│    └── Relationships:                                           │
│        └── blocking_tasks: List[Task]                           │
│                                                                 │
│  Role                                                           │
│    ├── Properties:                                              │
│    │   ├── id: int                                              │
│    │   ├── name: str                                            │
│    │   ├── color: str                                           │
│    │   ├── display_number: int                                  │
│    │   └── created_at: datetime                                 │
│    │                                                            │
│    ├── Business Logic Methods:                                  │
│    │   ├── has_active_tasks() → bool                            │
│    │   └── validate_color() → bool                              │
│    │                                                            │
│    └── Validation:                                              │
│        └── color must be in valid palette                       │
│                                                                 │
│  Status (enum)                                                  │
│    ├── TODO                                                     │
│    ├── DOING                                                    │
│    └── DONE                                                     │
│                                                                 │
│  Priority (enum)                                                │
│    ├── HIGH                                                     │
│    ├── MEDIUM                                                   │
│    └── LOW                                                      │
│                                                                 │
│  ViewMode (enum)                                                │
│    ├── TILE                                                     │
│    └── KANBAN                                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Database                                                       │
│    ├── manages → SQLite connection                              │
│    ├── property: connection                                     │
│    └── methods:                                                 │
│        ├── execute(query, params) → cursor                      │
│        └── close()                                              │
│                                                                 │
│  TaskRepository                                                 │
│    ├── depends-on → Database                                    │
│    ├── converts → DB rows ↔ Task objects                        │
│    └── methods:                                                 │
│        ├── save(task: Task) → int                               │
│        ├── get(task_id: int) → Task                             │
│        ├── get_tasks_for_role(role_id: int) → List[Task]        │
│        ├── delete(task_id: int)                                 │
│        ├── get_next_task_number(role_id: int) → int             │
│        └── _row_to_task(row) → Task (private)                   │
│                                                                 │
│  RoleRepository                                                 │
│    ├── depends-on → Database                                    │
│    ├── converts → DB rows ↔ Role objects                        │
│    └── methods:                                                 │
│        ├── save(role: Role) → int                               │
│        ├── get(role_id: int) → Role                             │
│        ├── get_all() → List[Role]                               │
│        ├── delete(role_id: int)                                 │
│        ├── exists(role_id: int) → bool                          │
│        └── _row_to_role(row) → Role (private)                   │
│                                                                 │
│  WindowRepository                                               │
│    ├── depends-on → Database                                    │
│    └── methods:                                                 │
│        ├── save_layout(panel_count, role_ids)                   │
│        └── load_layout() → dict                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```


## File Structure

```
terminal_todo/
│
├── main.py                      # Entry point
│
├── ui/                          # UI LAYER
│   ├── __init__.py
│   ├── input_handler.py         # InputHandler
│   ├── input_context.py         # InputContext
│   ├── input_modes.py           # CommandMode, NavigationMode
│   ├── display.py               # Display
│   ├── renderers.py             # TileLayout, KanbanLayout
│   ├── command_box.py           # CommandBox
│   └── panel.py                 # Panel
│
├── application/                 # APPLICATION LAYER
│   ├── __init__.py
│   ├── application.py           # Application
│   ├── services/
│   │   ├── __init__.py
│   │   ├── task_service.py      # TaskService
│   │   └── role_service.py      # RoleService
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── base.py              # Command (abstract)
│   │   ├── delete_task.py       # DeleteTaskCommand
│   │   └── delete_role.py       # DeleteRoleCommand
│   ├── undo_stack.py            # UndoStack
│   ├── command_parser.py        # CommandParser
│   ├── window_manager.py        # WindowManager
│   └── state.py                 # ApplicationState
│
├── domain/                      # DOMAIN LAYER
│   ├── __init__.py
│   ├── task.py                  # Task
│   ├── role.py                  # Role
│   └── enums.py                 # Status, Priority, ViewMode
│
├── data/                        # DATA LAYER
│   ├── __init__.py
│   ├── database.py              # Database
│   ├── task_repository.py       # TaskRepository
│   ├── role_repository.py       # RoleRepository
│   └── window_repository.py     # WindowRepository
│
└── utils/                       # Utilities
    ├── __init__.py
    ├── date_parser.py           # Date parsing helpers
    └── colors.py                # Color definitions
```
