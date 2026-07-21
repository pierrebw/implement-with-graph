# Implement with Graph

A reliability-focused Codex skill that plans and executes non-trivial coding work as a persistent, terminal-style dependency graph.

It is designed for long-running implementation, bug-fix, refactor, improvement, and migration tasks where context compaction, repeated patching, regressions, or premature claims of completion can reduce reliability.

## Why this exists

Open-ended agent loops can drift after repeated prompts or context compression. A fix may solve one symptom while breaking protected behavior elsewhere, and prior goals or test evidence can disappear from the active context.

`implement-with-graph` makes the implementation graph the durable control record. Codex must recover from that record, the actual repository diff, and fresh verification evidence—not conversational memory alone.

## What it does

- Presents implementation plans as terminal-style graphs.
- Preserves the original request, measurable goal, acceptance criteria, invariants, non-goals, baseline results, decisions, risks, and changed files.
- Stores task state under `.codex/implementation-graphs/<task-slug>.json` during implementation.
- Divides work into bounded nodes with declared scope, actions, exit checks, evidence, and retry limits.
- Models dependencies, evidence-driven branches, repair routes, merges, and bounded retries.
- Keeps at most one node active unless parallel agent work is explicitly requested.
- Requires reproduction and regression coverage for defect fixes when feasible.
- Invalidates stale test evidence after relevant edits.
- Prevents the terminal node from passing while required criteria, invariants, nodes, routes, or risks remain unresolved.
- Prints a final terminal graph and evidence-based handoff.

## Example

```text
── IMPLEMENTATION GRAPH ─────────────────────────────────────
TASK     Fix duplicate payment submission
GOAL     One user action creates at most one charge
PROTECT  Existing successful checkout behavior

[C0 ✓ PASSED] Contract + baseline
    └─locked→ [N1 ▶ ACTIVE] Reproduce duplicate submission
        └─evidence→ [D1 ○ BLOCKED] ◆ Identify duplicate origin
            ├─request race→ [N2A ○ BLOCKED] Guard request boundary
            └─task retry→ [N2B ○ BLOCKED] Make task idempotent
                └─selected branch→ [G1 ○ BLOCKED] Targeted verification
                    ├─pass→ [G2 ○ BLOCKED] Regression + invariants
                    │   └─pass→ [T1 ○ BLOCKED] Verified completion
                    └─fail/repair→ [R1 ○ BLOCKED] Diagnose before editing
                        └─retry 1/2→ [↩ G1]

CURRENT  N1
NEXT     Add the failing concurrency regression test
```

## Usage

Invoke the skill explicitly when you want the guarded workflow:

```text
Use $implement-with-graph to implement this change and do not finish until every graph gate passes.
```

It can also activate automatically for non-trivial implementation, repair, improvement, refactor, migration, or resumed coding work.

### Plan-only mode

Codex inspects the project and returns a terminal graph with node contracts. It does not modify product files or create durable state unless implementation or a saved plan was authorized.

### Plan-and-implement mode

Codex creates a task-specific state file, validates and renders the graph, then executes one ready node at a time. Each node must pass its exit checks with current evidence before downstream work becomes ready.

### Resume after context compaction

Codex reloads the active state file, validates it, inspects the actual working tree and diff, reopens the current node's files, and reruns evidence that may have become stale before continuing.

## State helper

`scripts/graph_state.py` provides deterministic graph operations:

```bash
python3 scripts/graph_state.py init .codex/implementation-graphs/task.json \
  --task "Task description" \
  --goal "Observable outcome"

python3 scripts/graph_state.py validate .codex/implementation-graphs/task.json
python3 scripts/graph_state.py render .codex/implementation-graphs/task.json
python3 scripts/graph_state.py checkpoint .codex/implementation-graphs/task.json

python3 scripts/graph_state.py set-status \
  .codex/implementation-graphs/task.json N2 passed \
  --evidence "pytest tests/test_feature.py: 8 passed" \
  --next "Run integration gate G2"
```

The validator checks node and edge types, dependency cycles, active-node limits, retry budgets, required evidence, terminal criteria, unresolved risks, and incomplete graph routes.

## Repository structure

```text
SKILL.md                       Skill behavior and execution rules
agents/openai.yaml             Skill interface metadata
references/graph-contract.md   Durable state schema and graph contract
scripts/graph_state.py         State validator, renderer, and checkpoint helper
```

## Reliability boundaries

This skill does not replace Codex's internal reasoning engine and cannot guarantee that a weaker model will never make a mistake. It improves reliability by making scope, protected behavior, dependencies, evidence, recovery state, and completion rules explicit and machine-checkable.

Graph state files are local work artifacts by default. They should not be staged, committed, overwritten, or deleted unless the user requests it.
