# Implementation: Execute All Tasks with Parallel Agents

## Objective
Execute all 43 tasks in /home/vfeenstr/devel/prompt-engineering/tasks/ using parallel haiku agents according to the execution plan, ensuring no test breakage, proper archiving, and successful code review.

## Context
- Research completed: @.prompts/001-task-execution-research/task-execution-research.md
- Plan completed: @.prompts/002-task-execution-plan/task-execution-plan.md
- All execution phases and parallel groups defined
- Quality gates and validation checkpoints established

## Requirements

### 1. Pre-Execution Setup
Before starting any tasks:
```bash
# Verify clean state
git status  # Must be clean or only expected changes
pytest -q  # All tests must pass
pytest tests/e2e/test_cli_end_to_end.py  # E2E must pass
```

### 2. Task Execution Protocol
For EACH task, the agent must:

#### 2.1 Read and Parse Task
```python
# Read task file
task_file = f"/home/vfeenstr/devel/prompt-engineering/tasks/{task_id}.md"
# Parse XML structure to extract requirements
```

#### 2.2 Implement Changes
- Follow developer section instructions exactly
- Make minimal changes (no scope creep)
- Preserve existing functionality
- Add no unnecessary dependencies

#### 2.3 Validate Changes
```bash
# Run task-specific tests from <tests> section
{test_command_from_task}
# Verify no test failures
```

#### 2.4 Archive and Commit
```bash
# Archive completed task
mkdir -p /home/vfeenstr/devel/prompt-engineering/tasks/archive
mv /home/vfeenstr/devel/prompt-engineering/tasks/{task_id}.md \
   /home/vfeenstr/devel/prompt-engineering/tasks/archive/

# Commit changes
git add -A
git commit -m "Complete {task_id}: {task_summary}"
```

### 3. Parallel Execution Groups

Execute tasks in parallel groups as defined in the plan. Use this exact pattern:

```python
# CRITICAL: Launch all agents in ONE message for true parallel execution
agents = [
    Task(
        subagent_type="general-purpose",
        model="haiku",
        description=f"Execute {task_id}",
        prompt=f"""
        Execute task {task_id} from /home/vfeenstr/devel/prompt-engineering/tasks/{task_id}.md

        Steps:
        1. Read the task file
        2. Implement ALL changes specified in <developer> section
        3. Run tests specified in <tests> section: {test_command}
        4. If tests pass, archive task to tasks/archive/
        5. Commit with message: "Complete {task_id}: {summary}"
        6. Report success/failure with details

        Requirements:
        - Make ONLY the changes specified
        - Do NOT add extra improvements
        - Tests MUST pass before committing
        - If tests fail, report the failure and stop
        """
    )
    for task_id, summary, test_command in parallel_group
]
```

### 4. Sequential Execution
For tasks that must run sequentially (file conflicts):

```python
# Execute one at a time
for task_id in sequential_tasks:
    agent = Task(
        subagent_type="general-purpose",
        model="haiku",
        # ... same execution instructions
    )
    # Wait for completion before next
```

### 5. Phase Validation
After each execution phase:

```bash
# Run full test suite
pytest -q

# Run E2E tests
pytest tests/e2e/test_cli_end_to_end.py -v

# Check for any broken functionality
ruff check .
```

### 6. Failure Handling
If any task fails:

1. **Stop parallel group** - Don't continue if tests break
2. **Report failure** - Include task ID, error details, test output
3. **Rollback if needed** - `git reset --hard HEAD~1` for last commit
4. **Decision point** - Fix and retry, skip task, or abort

### 7. Code Review Preparation
After all tasks complete successfully:

```bash
# Final validation
pytest -q  # All tests
pytest tests/e2e/test_cli_end_to_end.py  # E2E tests
ruff check .  # Linting

# Generate change summary
git log --oneline -n 43  # Review all commits

# Prepare review documentation
echo "Code Review Ready" > REVIEW_READY.md
echo "All 43 tasks completed" >> REVIEW_READY.md
echo "All tests passing" >> REVIEW_READY.md
```

## Execution Order

Based on the research and plan, execute in this order:

### Phase 1: Independent Foundation Tasks (Parallel)
Tasks with no dependencies or file conflicts:
- TASK-0034, TASK-0037, TASK-0040 (code style/organization)
- Run all simultaneously with haiku agents

### Phase 2: Core Module Updates (Mixed)
Parallel groups:
- Group A: TASK-0035, TASK-0039 (type hints, docstrings)
- Group B: TASK-0041, TASK-0043 (centralization)

Sequential (file conflicts):
- TASK-0036 (exception handling)
- TASK-0038 (IR builder fix)

### Phase 3: Complex Features (Sequential)
High-risk or complex changes:
- TASK-0050 (validation)
- TASK-0051 (test coverage)
- TASK-0054 (schema validation)

### Phase 4: Infrastructure (Parallel)
- TASK-0042, TASK-0044 (path/fs improvements)
- TASK-0046 (logging)
- TASK-0052, TASK-0053 (exit codes, performance)

### Phase 5: Optimizations (Parallel)
- TASK-0045, TASK-0047, TASK-0048, TASK-0049

## Output Specification
Real-time execution updates and final report.

## Success Criteria
- All 43 tasks completed
- No test failures at any point
- All tasks archived to tasks/archive/
- Each task has a commit
- E2E tests passing
- Code review passes
- No regression in functionality