# Blueprint User Guide

How to interact with Blueprint and the Warden agent.

---

## Quick Start

```bash
# Run Blueprint on a project
python -m src.cli run ./my-project

# Or use the Warden in chat
@warden/analyze ./my-project
@warden/run
```

---

## Warden Commands

The Warden is an LLM agent that operates Blueprint autonomously. Invoke commands in chat:

### Essential Commands

| Command | Description |
|---------|-------------|
| `@warden/help` | Show all available commands |
| `@warden/status` | Current state (boot status, memory, decisions) |
| `@warden/boot` | Check if Warden is ready to operate |
| `@warden/about` | Explain what the Warden is |

### Analysis

| Command | Description |
|---------|-------------|
| `@warden/analyze <path>` | Prepare to analyze a project |
| `@warden/analyze <path> --focus <subdir>` | Focus on specific directory |
| `@warden/domains` | List analysis domains |
| `@warden/domains enable <name>` | Enable a domain |
| `@warden/domains disable <name>` | Disable a domain |
| `@warden/run` | Execute analysis |
| `@warden/run --quick` | Quick run (xray + manifest only) |
| `@warden/run --full` | Full run (all domains) |

### Memory

| Command | Description |
|---------|-------------|
| `@warden/memory` | Show memory summary |
| `@warden/memory list [category]` | List memory items |
| `@warden/memory recall <key>` | Recall specific item |
| `@warden/memory forget <key>` | Remove item |
| `@warden/memory clear` | Clear all memory |

### Decisions

| Command | Description |
|---------|-------------|
| `@warden/decisions` | Show recent decisions |
| `@warden/decisions list` | List all decisions |
| `@warden/decisions --failed` | Show failed decisions |
| `@warden/decisions explain <id>` | Explain a decision |
| `@warden/decisions stats` | Decision statistics |

### Error Recovery

| Command | Description |
|---------|-------------|
| `@warden/errors` | Show recent errors |
| `@warden/errors clear` | Clear error history |
| `@warden/recover` | Get recovery suggestions |
| `@warden/retry` | Retry last failed operation |

### Checkpoints

| Command | Description |
|---------|-------------|
| `@warden/checkpoint [name]` | Create checkpoint |
| `@warden/checkpoints` | List checkpoints |
| `@warden/revert <id>` | Revert to checkpoint |
| `@warden/history` | Show change history |

### Configuration

| Command | Description |
|---------|-------------|
| `@warden/config` | Show configuration |
| `@warden/config set <key> <value>` | Set config value |
| `@warden/purpose` | Show current purpose |
| `@warden/purpose set <text>` | Set analysis purpose |

### Certificate

| Command | Description |
|---------|-------------|
| `@warden/certificate` | Check certificate status |
| `@warden/certificate issue` | Run tests and issue certificate |
| `@warden/certificate revoke` | Revoke certificate |

### Aliases

Short forms for common commands:

| Alias | Full Command |
|-------|--------------|
| `@w/h` | `@warden/help` |
| `@w/s` | `@warden/status` |
| `@w/a` | `@warden/analyze` |
| `@w/r` | `@warden/run` |
| `@w/e` | `@warden/errors` |
| `@w/m` | `@warden/memory` |
| `@w/d` | `@warden/decisions` |
| `@w/c` | `@warden/checkpoint` |

---

## Manual CLI Usage

### Basic Commands

```bash
# Analyze a local project
python -m src.cli run ./path/to/project

# Analyze with specific domains
python -m src.cli run ./project --domains xray,manifest,cortex

# Focus on a subdirectory
python -m src.cli run ./project --focus src/api

# Use a preset
python -m src.cli run ./project --preset minimal
python -m src.cli run ./project --preset standard
python -m src.cli run ./project --preset full
```

### Using deploy.yaml

Create `workspace/intake/deploy.yaml`:

```yaml
version: "1.0"

# What to analyze
targets:
  - type: local
    name: my-app
    path: ./path/to/my-app
    focus: src/

# Which domains to run
domains:
  - xray      # Entity extraction
  - manifest  # Project structure
  - cortex    # Dependencies
  - registry  # Symbol index
  - sonar     # Quality metrics
  - synapse   # Cross-references

# Output settings
output:
  formats:
    - json
    - markdown

# Warden guidance
purpose: "Analyze React component relationships for refactoring"

warden:
  auto_recover: true
  checkpoint_before_changes: true
  sync_after_run: true
  max_retries: 3
```

Then run:

```bash
python -m src.cli run --deploy workspace/intake/deploy.yaml
```

---

## System Prompts for Chat

Use these prompts to instruct the LLM on how to operate Blueprint:

### Basic Analysis Prompt

```
You are operating Blueprint, a codebase analysis tool. Use the Warden
commands to analyze projects safely. Always check @warden/status before
starting and @warden/boot to ensure the certificate is valid.

When analyzing:
1. Use @warden/analyze <path> to set up analysis
2. Use @warden/run to execute
3. Report findings clearly
4. Use @warden/checkpoint before risky operations
```

### Autonomous Operation Prompt

```
You are the Warden, Blueprint's autonomous operator. Your role is to:

1. Analyze codebases using Blueprint's domains
2. Make decisions and log them with @warden/decide
3. Remember learnings across sessions with @warden/memory
4. Recover gracefully from errors using @warden/recover
5. Create checkpoints before risky operations

You CANNOT:
- Modify source code (analyze only)
- Access external APIs
- Handle credentials or secrets

Always verify certificate status before operating. Log all decisions
with confidence levels and reasoning.
```

### Interactive Assistant Prompt

```
Help the user analyze their codebase using Blueprint. Available tools:

- @warden/analyze <path> - Analyze a project
- @warden/domains - Show/configure analysis domains
- @warden/run - Execute analysis
- @warden/errors - Check for problems
- @warden/recover - Get fix suggestions

Guide them through the process, explain what each domain does, and
help interpret the results.
```

---

## What the Warden Can Do

### Analyze
- Extract entities (functions, classes, components)
- Map project structure and dependencies
- Index symbols for search
- Calculate quality metrics
- Find cross-file references

### Decide
- Choose which domains to run
- Skip irrelevant paths
- Prioritize analysis targets
- Select recovery strategies

### Remember
- Project types and patterns
- Error patterns and fixes
- Successful strategies
- User preferences

### Recover
- Detect error patterns
- Suggest fixes based on history
- Retry with adjusted settings
- Revert to checkpoints

---

## What the Warden Cannot Do

- **No code modification** - analyze only, never write
- **No external access** - everything is local files
- **No secrets** - doesn't handle credentials
- **No system changes** - no installs, no permissions

---

## Workflow Examples

### Analyze a New Project

```
@warden/status                    # Check if ready
@warden/analyze ./my-react-app    # Set up analysis
@warden/purpose set "Find unused components"
@warden/run                       # Execute
```

### Recover from Errors

```
@warden/errors                    # See what failed
@warden/recover                   # Get suggestions
@warden/config set auto_recover true
@warden/retry                     # Try again
```

### Safe Experimentation

```
@warden/checkpoint before-experiment
# ... try things ...
@warden/revert before-experiment  # If it breaks
```

### Export for Portability

```
@warden/bundle create             # Create bundle in project
@warden/bundle export             # Save state to bundle
# Now the project can be moved with its analysis history
```

---

## File Locations

```
blueprint/
├── workspace/
│   ├── intake/          # Input projects
│   │   └── deploy.yaml  # Configuration
│   ├── results/         # Analysis output
│   ├── warden/          # Warden state
│   │   ├── memory/
│   │   ├── decisions/
│   │   └── commits/
│   └── status/          # Run status
│
└── src/
    ├── warden/          # Warden implementation
    │   ├── AGENT.md     # Agent specification
    │   └── COMMANDS.md  # Command reference
    └── ...
```

---

## Getting Help

- `@warden/help` - All commands
- `@warden/about` - What is the Warden
- `src/warden/AGENT.md` - Full agent specification
- `src/warden/COMMANDS.md` - Detailed command reference
