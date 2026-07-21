---
name: implement-with-graph
description: Plan and execute coding changes through a persistent terminal-style dependency graph with explicit contracts, invariants, regression gates, repair routes, retry limits, and evidence-based completion. Use when Codex is asked to implement, fix, improve, refactor, migrate, or resume a non-trivial code change, especially when lower intelligence settings, long-running work, context compaction, repeated regressions, or vague claims of completion could reduce reliability. Also use when the user asks for a graph-based implementation plan instead of an open-ended loop or linear checklist. Skip only truly atomic, low-risk edits unless explicitly invoked.
---

# Implement With Graph

Use a graph as the durable control plane for the task. Do not treat it as decoration. The graph decides what is ready, what is blocked, what must be verified, where a failure routes, and when completion is allowed.

## Choose the operating mode

- **Plan only:** Inspect without modifying product files. Present the terminal graph and node contracts in the response. Do not create a state file unless the user also authorized implementation or asked for a saved plan.
- **Plan and implement:** Create and maintain a task-specific state file, then execute one graph node at a time.
- **Resume or post-compaction:** Recover from the state file, repository diff, and fresh test evidence before making another edit. Never reconstruct task state from conversational memory alone.

## Establish durable state

For implementation work, create `.codex/implementation-graphs/<short-task-slug>.json` with `scripts/graph_state.py init`. Keep one file per task. If a matching active graph already exists, resume it; do not overwrite it. If a different active graph creates ambiguity, stop and ask which task to continue.

Treat this file as a local work artifact. Do not stage, commit, or delete it unless the user asks. If `.codex` cannot be used, place `implementation-graph.<slug>.json` at the workspace root; never use temporary storage for the only copy.

Read [references/graph-contract.md](references/graph-contract.md) when creating or materially restructuring a graph. Use the helper relative to this skill directory:

```bash
python3 <skill-dir>/scripts/graph_state.py init <state-file> --task "..." --goal "..."
python3 <skill-dir>/scripts/graph_state.py validate <state-file>
python3 <skill-dir>/scripts/graph_state.py render <state-file>
python3 <skill-dir>/scripts/graph_state.py checkpoint <state-file>
```

## Build the graph before editing

1. Read applicable repository instructions and inspect the current working tree. Preserve user changes and separate pre-existing failures from new ones.
2. Lock the contract:
   - original task and measurable goal;
   - acceptance criteria;
   - protected behavior and invariants;
   - non-goals;
   - baseline revision, working-tree state, and relevant checks;
   - risks and unresolved assumptions.
3. Create small nodes with concrete scope, actions, exit checks, evidence requirements, and bounded attempts. Split any node that changes multiple independent behaviors or cannot be verified locally.
4. Add explicit dependency, branch, repair, and retry edges. Show parallel-ready nodes, but execute sequentially unless the user explicitly requests subagents or parallel agent work.
   - When the cause or correct design is unknown, create a decision node after discovery and route evidence to conditional alternatives.
   - Never sequence mutually exclusive speculative fixes as though all must be implemented.
   - Do not choose a library, mechanism, schema, or architecture before its decision node has enough repository evidence.
   - Give every edge exactly one source and one destination. Never write an edge such as “return to A or B”; add a decision node with separate routes.
   - Make every selected branch visibly converge at an integration or verification node.
5. Include at least these gates for non-trivial changes:
   - contract and baseline;
   - implementation integration;
   - targeted verification;
   - regression and invariant verification;
   - final diff and acceptance review;
   - terminal completion.
6. Validate and render the graph. Present the terminal rendering before substantial edits.

## Use the mandatory terminal presentation

Make the primary plan a fenced `text` block, not a Mermaid diagram, prose-only list, or ordinary linear checklist. Use plain terminal characters and spaces—never HTML entities. Use stable IDs and these status markers: `○ BLOCKED`, `◇ READY`, `▶ ACTIVE`, `✓ PASSED`, `✗ FAILED`, and `– SKIPPED`.

For plan-only work, use `◇ READY` for the first executable discovery or contract node and `○ BLOCKED` for its dependents. Do not claim nodes passed without execution evidence. Show every meaningful branch, merge, gate failure, repair, and retry edge. Use this minimum shape:

```text
── IMPLEMENTATION GRAPH ─────────────────────────────────────
TASK     <preserved request>
GOAL     <observable outcome>
PROTECT  <critical existing behavior>

[C0 ◇ READY] Contract + baseline
    └─locked→ [N1 ○ BLOCKED] Evidence-gathering discovery
        └─evidence→ [D1 ○ BLOCKED] ◆ Cause / design decision
            ├─condition A→ [N2A ○ BLOCKED] Bounded implementation A
            └─condition B→ [N2B ○ BLOCKED] Bounded implementation B
                 └─selected branch(es)→ [G1 ○ BLOCKED] Targeted verification
                     ├─pass→ [G2 ○ BLOCKED] Regression + invariants
                     │   └─pass→ [T1 ○ BLOCKED] Verified completion
                     └─fail/repair→ [R1 ○ BLOCKED] Diagnose before editing
                         └─retry 1/2→ [↩ G1]

CURRENT  none
NEXT     Start C0
```

Adapt the topology rather than copying irrelevant nodes. Follow the graph with compact node contracts containing `scope`, `action`, and `exit evidence`. Keep proposed solutions conditional when discovery has not resolved the decision.

After any graph containing a branch, merge, repair, or retry, include a terminal route ledger so topology cannot depend on indentation alone:

```text
ROUTES
  C0 --locked/dependency--> N1
  D1 --condition A/branch--> N2A
  D1 --condition B/branch--> N2B
  N2A --selected/dependency--> G1
  N2B --selected/dependency--> G1
  G1 --fail/repair--> R1
  R1 --recheck/retry--> G1
```

The route kind after `/` must be exactly one of `dependency`, `branch`, `repair`, or `retry`. Represent a merge with separate `dependency` edges from each selected branch into the merge node; `merge` is not an edge kind.

## Execute by node state

Use only these states: `blocked`, `ready`, `active`, `passed`, `failed`, and `skipped`.

- Keep at most one node `active` unless parallel work was explicitly authorized.
- Before starting a node, reread the state file, inspect the current diff, and confirm its incoming dependencies passed.
- Mark a node `active` before editing. Touch only its declared scope. If new scope becomes necessary, update and validate the graph first.
- Make the smallest coherent change that satisfies the node. Do not stack speculative fixes.
- Run the node's exit checks and inspect its diff. Mark it `passed` only with concrete evidence.
- Update `changed_files`, decisions, risks, `next_action`, and the checkpoint after every node and before any operation likely to consume substantial context.
- Use `risks` only for unresolved conditions that could invalidate completion. Put standing protections in invariants and scope limits in non-goals. Remove a risk only after recording the evidence or decision that resolved it.
- Never silently weaken an acceptance criterion, invariant, test, type check, lint rule, or security control to obtain a pass.

Use `set-status` for transitions when practical:

```bash
python3 <skill-dir>/scripts/graph_state.py set-status <state-file> N2 active --next "Implement the bounded change"
python3 <skill-dir>/scripts/graph_state.py set-status <state-file> N2 passed --evidence "pytest tests/test_feature.py: 8 passed" --next "Run integration gate G2"
```

## Route failures instead of looping blindly

- Record the failing command, symptom, and current hypothesis as evidence.
- Follow the graph's repair edge to a diagnostic or repair node.
- Reproduce before modifying when feasible. For a defect, prefer a failing regression test before the fix.
- Rerun the smallest affected checks, then all downstream gates invalidated by the repair.
- Respect `max_attempts`. If the same gate fails twice or the retry budget is exhausted, stop patching, create or activate a diagnosis node, reassess the graph, and report the blocker if evidence does not support a safe route.

## Prevent regressions

- Establish a baseline before changing behavior whenever feasible.
- Convert every user-visible requirement and important existing behavior into an acceptance criterion or invariant with an explicit check.
- Test the changed path, adjacent behavior, error paths, and integration boundaries in proportion to risk.
- For bug fixes, keep the regression test that proves the original defect remains fixed.
- Inspect the complete diff for unrelated changes, accidental API/schema changes, disabled checks, deleted coverage, debug code, unsafe migrations, and unhandled failure paths.
- After a repair, rerun every gate whose evidence may have become stale; never reuse invalidated evidence.

## Survive context compaction

At the beginning of every resumed turn, after suspected compaction, and before continuing from a summary:

1. Locate and read the active graph file.
2. Run `checkpoint` and `validate`.
3. Inspect `git status` and the actual diff.
4. Reopen the files owned by the current or next node.
5. Rerun any check whose recorded evidence no longer matches the diff.
6. State the current node and next action, then continue.

Do not trust a prior “done,” “fixed,” or “tests pass” statement without matching durable evidence.

## Completion gate

Do not mark the terminal node `passed` until all of the following are true:

- every required acceptance criterion and invariant is `passed` with evidence;
- every required non-skipped node is `passed`;
- every untaken branch or unused repair route is explicitly `skipped` with the routing decision recorded;
- targeted and regression checks passed after the final relevant edit;
- the final diff was reviewed against the locked contract and non-goals;
- final `git status` was inspected, including untracked files, and every task-created artifact is intentional or safely cleaned up without touching unknown user files;
- no unresolved risk or blocker contradicts completion;
- the delivered behavior, not merely the code shape, was verified.

The final user-facing handoff must paste the latest fenced terminal graph from `render`; do not replace it with a link or prose summary. Then provide the evidence summary, known limitations, final working-tree scope, and state-file path. Use precise claims: distinguish verified, partially verified, blocked, and not run.
