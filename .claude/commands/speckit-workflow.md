---
description: Execute the complete SDD workflow (specify → clarify → plan → tasks → analyze → implement) in a single command.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

This command automates the complete Spec-Driven Development (SDD) 6-phase workflow.

### Phases

1. **Specify** (`/speckit.specify`) - Create feature specification from description
2. **Clarify** (`/speckit.clarify`) - Identify and resolve underspecified areas
3. **Plan** (`/speckit.plan`) - Generate technical implementation plan
4. **Tasks** (`/speckit.tasks`) - Create actionable task breakdown
5. **Analyze** (`/speckit.analyze`) - Validate cross-artifact consistency before implementation
6. **Implement** (`/speckit.implement`) - Execute the implementation plan

### Execution

1. **Parse arguments**:
   - Extract feature description from `$ARGUMENTS`
   - Check for `--ultrathink` flag (enables extended thinking mode)
   - If no description provided: ERROR "Feature description required. Usage: /speckit-workflow [feature-description] [--ultrathink]"

2. **Phase 1: Specify**
   - Execute the `/speckit.specify` workflow with the feature description
   - Wait for completion and any clarification questions
   - If user clarifications needed, pause for user input

3. **Phase 2: Clarify**
   - Execute `/speckit.clarify` to identify underspecified areas
   - Present clarification questions (max 5) to user
   - Update spec with user responses
   - Continue when all clarifications resolved

4. **Phase 3: Plan**
   - Execute `/speckit.plan` to create technical plan
   - If `--ultrathink` was specified, use extended analysis mode
   - Generate: plan.md, data-model.md (if needed), contracts/ (if needed)

5. **Phase 4: Tasks**
   - Execute `/speckit.tasks` to generate task breakdown
   - Create dependency-ordered tasks.md
   - Report task count and estimated complexity

6. **Phase 5: Analyze**
   - Execute `/speckit.analyze` for cross-artifact validation
   - Check consistency between spec, plan, and tasks
   - If issues found, fix them before proceeding to implementation
   - Report validation status

7. **Phase 6: Implement**
   - Execute `/speckit.implement` to run all tasks
   - Follow TDD approach (tests before code)
   - Track progress and report completion status

### Progress Tracking

After each phase, report:
```
Phase [N/6] Complete: [Phase Name]
  - Artifacts: [list of created/updated files]
  - Status: [PASS/NEEDS ATTENTION]
  - Next: [next phase name]
```

### Error Handling

- If any phase fails, halt execution and report:
  - Which phase failed
  - Error details
  - Suggested remediation
  - Command to resume from that phase

### Final Report

Upon completion, provide summary:
```
SDD Workflow Complete

Feature: [feature name]
Branch: [branch name]
Phases: 6/6 completed

Artifacts Created:
  - specs/[NNN]-[feature]/spec.md
  - specs/[NNN]-[feature]/plan.md
  - specs/[NNN]-[feature]/tasks.md
  - [additional artifacts]

Implementation Status:
  - Tasks: [X/Y completed]
  - Tests: [pass/fail count]
  - Coverage: [percentage if available]

Quality Analysis: [PASS/ISSUES FOUND]

Next Steps:
  - [recommended actions if any]
```

## Options

| Option | Description |
|--------|-------------|
| `--ultrathink` | Enable extended thinking mode for deeper analysis in plan phase |

## Examples

```bash
# Basic usage
/speckit-workflow Add user authentication with OAuth2

# With ultrathink for complex features
/speckit-workflow Implement real-time collaboration system --ultrathink

# Multi-word feature descriptions
/speckit-workflow "Add payment processing with Stripe integration"
```

## Notes

- This command combines 6 individual speckit commands into one streamlined workflow
- Each phase must complete successfully before proceeding to the next
- User interaction may be required during Specify and Clarify phases
- The workflow respects all validation checkpoints from individual commands
- For resuming from a specific phase, use the individual `/speckit.[phase]` command
