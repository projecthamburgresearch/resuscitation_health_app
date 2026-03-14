# Warden Commands

Invoke these commands in chat with `@warden/{command}` or `/warden {command}`

---

## Help & Info

### `@warden/help`
Show all available commands and what the Warden can do.

### `@warden/status`
Show current Warden state:
- Certificate status (valid/expired/missing)
- Memory items count
- Recent decisions count
- Active project (if any)
- Last error (if any)

### `@warden/about`
Explain what the Warden is and its role in Blueprint.

---

## Analysis Commands

### `@warden/analyze <path>`
Analyze a project at the given path.
```
@warden/analyze ./my-project
@warden/analyze C:\Users\me\code\app
```

### `@warden/analyze --focus <subdir>`
Focus analysis on a specific subdirectory.
```
@warden/analyze ./my-project --focus src/api
```

### `@warden/domains`
List available analysis domains and their status.
```
xray     - Entity extraction      [enabled]
manifest - Project structure      [enabled]
cortex   - Dependency analysis    [enabled]
registry - Symbol indexing        [enabled]
sonar    - Quality metrics        [enabled]
synapse  - Cross-reference        [enabled]
```

### `@warden/domains enable <domain>`
Enable a specific domain.

### `@warden/domains disable <domain>`
Disable a specific domain.

---

## Memory Commands

### `@warden/memory`
Show memory summary by category.

### `@warden/memory list [category]`
List memory items, optionally filtered by category.
```
@warden/memory list learnings
@warden/memory list patterns
```

### `@warden/memory recall <key>`
Recall a specific memory item.
```
@warden/memory recall project_type
```

### `@warden/memory forget <key>`
Remove a memory item.

### `@warden/memory clear [category]`
Clear all memory or a specific category.

---

## Decision Commands

### `@warden/decisions`
Show recent decisions with outcomes.

### `@warden/decisions list [--failed]`
List all decisions, optionally filter to failed ones.

### `@warden/decisions explain <id>`
Explain why a specific decision was made.

### `@warden/decisions stats`
Show decision statistics (success rate, common actions).

---

## Checkpoint & Recovery

### `@warden/checkpoint [name]`
Create a checkpoint of current state.
```
@warden/checkpoint before-refactor
```

### `@warden/checkpoints`
List available checkpoints.

### `@warden/revert <checkpoint-id>`
Revert to a previous checkpoint.

### `@warden/history`
Show change history since last checkpoint.

---

## Error Handling

### `@warden/errors`
Show recent errors.

### `@warden/errors clear`
Clear error history.

### `@warden/recover`
Get recovery suggestions based on error patterns.

### `@warden/retry`
Retry the last failed operation.

---

## Project Commands

### `@warden/project`
Show current project info.

### `@warden/project open <path>`
Open a project for analysis.

### `@warden/project close`
Close current project.

### `@warden/project list`
List all known projects.

### `@warden/project sync`
Sync current project with its bundle.

---

## Bundle Commands

### `@warden/bundle`
Show bundle status for current project.

### `@warden/bundle create`
Create a bundle for current project.

### `@warden/bundle export`
Export workspace state to bundle.

### `@warden/bundle import`
Import state from bundle to workspace.

---

## Configuration

### `@warden/config`
Show current configuration.

### `@warden/config set <key> <value>`
Set a configuration value.
```
@warden/config set auto_recover true
@warden/config set max_retries 5
```

### `@warden/config reset`
Reset to default configuration.

### `@warden/purpose`
Show the current purpose statement.

### `@warden/purpose set <text>`
Set a new purpose for guidance.
```
@warden/purpose set "Analyze React components for refactoring"
```

---

## Certificate & Boot

### `@warden/certificate`
Show certificate status.

### `@warden/certificate issue`
Run tests and issue a new certificate.

### `@warden/certificate revoke`
Revoke current certificate (requires re-testing).

### `@warden/boot`
Check if Warden can boot (certificate valid).

---

## Context Management

### `@warden/context`
Show what Warden knows about current session.

### `@warden/context summarize <data>`
Summarize data to fit context window.

### `@warden/context priority`
Show prioritized context items.

---

## Quick Actions

### `@warden/run`
Run analysis with current settings.

### `@warden/run --quick`
Quick run (xray + manifest only).

### `@warden/run --full`
Full run (all domains).

### `@warden/stop`
Stop current operation.

### `@warden/reset`
Reset Warden state (keeps memory).

### `@warden/reset --hard`
Full reset (clears everything).

---

## Examples

```
# Start analyzing a project
@warden/analyze ./my-react-app

# Check what Warden learned
@warden/memory list learnings

# See why something failed
@warden/errors
@warden/recover

# Create safety checkpoint before changes
@warden/checkpoint pre-experiment

# If things go wrong
@warden/revert pre-experiment

# Export everything to bundle for portability
@warden/bundle export
```

---

## Command Aliases

| Short | Full Command |
|-------|--------------|
| `@w/h` | `@warden/help` |
| `@w/s` | `@warden/status` |
| `@w/a` | `@warden/analyze` |
| `@w/r` | `@warden/run` |
| `@w/e` | `@warden/errors` |
| `@w/m` | `@warden/memory` |
| `@w/d` | `@warden/decisions` |
| `@w/c` | `@warden/checkpoint` |
