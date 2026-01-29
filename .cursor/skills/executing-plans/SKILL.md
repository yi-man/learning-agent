---
name: executing-plans
description: Use when you have a written implementation plan to execute in a separate session; run all tasks to completion, then one review reminder and merge on confirmation
---

# Executing Plans

## Overview

Load plan, review critically, execute all tasks to completion (no mid-execution checkpoints), then remind for one overall review; when the user confirms review is done, run finishing-a-development-branch and execute option 1 (merge).

**Core principle:** Run entire plan to completion, then single review → confirm → merge (option 1).

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically - identify any questions or concerns about the plan
3. If concerns: Raise them with your human partner before starting
4. If no concerns: Create TodoWrite and proceed

### Step 2: Execute All Tasks
**Execute every task in the plan** — no batching, no stopping for feedback between tasks.

For each task:
1. Mark as in_progress
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified
4. Mark as completed

Continue to the next task until all are done. **Stop only when:** you hit a blocker (missing dependency, test fails, instruction unclear, verification fails repeatedly). Then ask for help; don't guess.

### Step 3: Report Once (When All Tasks Complete)
When **all** tasks are complete and verified:
- Briefly list what was implemented and verification results
- Say exactly: **"Execution is complete. Please review all changes locally. When you're done reviewing, reply and I'll execute option 1 (merge back to base branch)."**
- Wait for the user's reply

### Step 4: On User Confirmation — Complete Development
When the user confirms review is done (e.g. "review done", "go ahead", "选 1", "merge"):
- Do **not** ask again which option; proceed to merge
- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use superpowers:finishing-a-development-branch
- Follow that skill: verify tests, then **execute option 1** (merge locally). If the user instead says they want changes or a different option (e.g. create PR), address that first or follow their choice

## When to Stop and Ask for Help

**STOP executing immediately when:**
- Hit a blocker mid-task (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- You don't understand an instruction
- Verification fails repeatedly

**Ask for clarification rather than guessing.**

## When to Revisit Earlier Steps

**Return to Review (Step 1) when:**
- Partner updates the plan based on your feedback
- Fundamental approach needs rethinking

**Don't force through blockers** - stop and ask.

## Remember
- Review plan critically first
- Follow plan steps exactly
- Don't skip verifications
- Reference skills when plan says to
- Run all tasks to completion; only then report and ask for review
- Stop when blocked, don't guess
