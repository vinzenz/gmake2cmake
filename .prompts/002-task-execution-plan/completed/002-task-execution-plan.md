# Plan: Parallel Task Execution Strategy

## Objective
Create a detailed execution plan for implementing all tasks using parallel agents with the haiku model, ensuring no test breakage, proper archiving, and successful code review.

## Context
- Research completed: @.prompts/001-task-execution-research/task-execution-research.md
- 43 tasks to execute across multiple code quality categories
- Requirements: parallel execution, haiku model, no test breakage, archive + commit after each task
- All changes must pass e2e testing and code review

## Requirements

### 1. Execution Architecture
Design the multi-agent execution strategy:
- **Agent allocation**: How many parallel agents per layer
- **Model specification**: All agents use haiku model
- **Coordination mechanism**: How agents communicate completion
- **Failure handling**: What happens if an agent fails

### 2. Task Grouping Strategy
Based on research findings, create execution groups:
- **Group by independence**: Tasks with no file overlap
- **Group by module**: Tasks affecting same module together
- **Group by risk**: Low-risk tasks first, high-risk sequential
- **Group by type**: Similar changes together (e.g., all docstrings)

### 3. Quality Gates
Define validation checkpoints:
- **Pre-execution**: Verify clean working tree, all tests passing
- **Per-task validation**: Run affected tests after each task
- **Layer validation**: Full test suite after each layer
- **Final validation**: Complete e2e testing before review

### 4. Task Execution Template
For each task, specify:
```
Task: [ID]
Agent: haiku
Actions:
1. Read task file
2. Implement changes
3. Run specified tests
4. Archive task to /tasks/archive/
5. Commit with message: "Complete [ID]: [summary]"
```

### 5. Parallel Execution Instructions
Structure for parallel agent spawning:
```
PARALLEL_BATCH_1: [
  {agent: "haiku", task: "TASK-0034", ...},
  {agent: "haiku", task: "TASK-0035", ...},
  ...
]
```

### 6. Code Review Preparation
Plan for review phase:
- **Change grouping**: Logical commits for review
- **Documentation**: Update notes for reviewer
- **Test evidence**: Capture test results
- **Rollback plan**: How to revert if needed

## Output Specification
Save to: `/home/vfeenstr/devel/prompt-engineering/.prompts/002-task-execution-plan/task-execution-plan.md`

Structure the output as:

```markdown
# Task Execution Plan

## Executive Summary
[Overview of execution strategy]

## Execution Phases

### Phase 1: Foundation Tasks
<phase_1>
Parallel Batch 1A (Independent, Low Risk):
- TASK-[ID]: [Summary] - Agent: haiku
- TASK-[ID]: [Summary] - Agent: haiku
[List all tasks in this batch]

Sequential (File conflicts):
- TASK-[ID]: [Summary] - Agent: haiku
[List sequential tasks]

Validation: [Test suites to run]
</phase_1>

### Phase 2: Core Improvements
<phase_2>
[Similar structure]
</phase_2>

[Additional phases as needed]

## Agent Coordination

### Parallel Execution Commands
<parallel_commands>
# Batch 1A - Launch all simultaneously
agents = [
  Task(subagent_type="general-purpose", model="haiku", prompt="Execute TASK-0034..."),
  Task(subagent_type="general-purpose", model="haiku", prompt="Execute TASK-0035..."),
  ...
]
</parallel_commands>

### Sequential Execution Commands
<sequential_commands>
# Run one at a time for conflicting tasks
[Specific instructions]
</sequential_commands>

## Quality Gates

### Pre-Execution Checklist
<pre_execution>
- [ ] Working tree clean
- [ ] All tests passing
- [ ] Dependencies installed
- [ ] Backup created
</pre_execution>

### Per-Task Validation
<per_task_validation>
1. Run task-specific tests
2. Verify no test breakage
3. Check file modifications correct
4. Archive and commit
</per_task_validation>

### Phase Validation
<phase_validation>
After each phase:
- [ ] Run full test suite
- [ ] Check e2e tests
- [ ] Review changes
- [ ] Document any issues
</phase_validation>

## Failure Recovery

### Rollback Procedures
<rollback>
If task fails:
1. [Specific rollback steps]
</rollback>

### Skip Lists
<skip_conditions>
Skip task if:
- [Conditions when to skip]
</skip_conditions>

## Code Review Preparation

### Review Checklist
<review_prep>
- [ ] All tasks completed
- [ ] Tests passing
- [ ] Changes documented
- [ ] Commits organized
</review_prep>

## Implementation Timeline
<timeline>
Estimated execution:
- Phase 1: [X tasks, Y parallel, Z sequential]
- Phase 2: [X tasks, Y parallel, Z sequential]
Total: [Estimated based on complexity]
</timeline>

<metadata>
<confidence>high|medium|low</confidence>
<dependencies>
- Research findings from 001-task-execution-research
- Clean working tree
- Test suite functional
</dependencies>
<open_questions>
- [Any unresolved planning questions]
</open_questions>
<assumptions>
- Haiku model available for all agents
- Tests are deterministic
- Git operations allowed
</assumptions>
</metadata>
```

## Success Criteria
- Clear execution phases defined
- All tasks assigned to parallel or sequential execution
- Agent coordination instructions complete
- Quality gates comprehensive
- Failure recovery planned
- Code review preparation included
- No test breakage strategy validated
- Archive and commit procedures specified