---
name: implement-with-graph
description: Plan and execute non-trivial coding changes through a persistent terminal-style dependency graph with concise communication, explicit contracts, invariants, regression and visual-runtime gates, repair routes, retry limits, and evidence-based completion. Use for implementation, fixes, improvements, refactors, migrations, UI work, or resumed tasks where context compaction, repeated regressions, visual/code mismatch, lower intelligence settings, or premature completion could reduce reliability. Also use when the user requests graph-based implementation rather than an open-ended loop. Skip only truly atomic, low-risk edits unless explicitly invoked.
---

# Implement With Graph

Use the graph as the task's durable control plane. Keep it useful, not ceremonial.

## Operating posture

- Act after the minimum inspection needed for a safe decision. Do not turn execution into an essay.
- Be pragmatic and critical. Prefer repository evidence, existing patterns, and the smallest coherent fix over speculative redesign.
- Challenge an unsafe or contradictory request with evidence, then offer the shortest safe route forward.
- Communicate only meaningful milestones, decisions, failures, and verified outcomes. Do not narrate routine tool use or repeat the plan.
- Persist while a safe evidence-backed route remains. Stop when continuing would be guessing, unsafe, unauthorized, or repetitive thrashing.
- Treat passing code checks and correct rendered behavior as separate facts. One never proves the other.

## Choose the mode

- **Plan only:** Inspect without modifying product files. Return a compact terminal graph. Mark the first executable node `ready` and all dependents `blocked`; never mark unexecuted work `active` or `passed`. Do not create state unless the user requested a saved plan.
- **Plan and implement:** Create durable state, present the graph, then execute ready nodes.
- **Resume or post-compaction:** Recover from durable state, the actual diff, and fresh checks. Never reconstruct task state from chat memory alone.

## Keep durable state

For implementation, create `.codex/implementation-graphs/<task-slug>.json` with `scripts/graph_state.py init`. Add `--visual-required` when success includes rendered UI, layout, styling, animation, or visual parity.

```bash
python3 <skill-dir>/scripts/graph_state.py init <state-file> --task "..." --goal "..." [--visual-required]
python3 <skill-dir>/scripts/graph_state.py validate <state-file>
python3 <skill-dir>/scripts/graph_state.py render <state-file>
python3 <skill-dir>/scripts/graph_state.py checkpoint <state-file>
```

Keep one state file per task. Resume a matching active graph; never overwrite it. Do not stage, commit, or delete graph state unless the user asks. Read [references/graph-contract.md](references/graph-contract.md) when creating or materially restructuring it.

## Build the minimum sufficient graph

1. Read applicable instructions, inspect `git status`, and separate user changes and pre-existing failures.
2. Lock the original request, observable acceptance criteria, protected invariants, non-goals, baseline checks, risks, and unresolved assumptions.
3. Scale the graph to risk:
   - small bounded change: about 4–7 nodes;
   - medium cross-file change: about 6–12 nodes;
   - large or high-risk change: about 10–15 nodes; split into phases before exceeding 20.
4. Give each node a narrow scope, concrete action, exit check, evidence requirement, and retry limit.
5. Put discovery before uncertain design. Route mutually exclusive hypotheses through a decision node; never implement every speculative fix.
6. Give every edge one source and one destination. Converge selected branches at a named integration or verification node.
7. Include only gates that prove the outcome:
   - targeted code/behavior verification;
   - regression and invariant verification;
   - visual-runtime verification when `visual_required` is true;
   - final diff, working-tree, and acceptance review;
   - one terminal completion node.
8. Give failure-prone gates an explicit repair route and bounded retry.

## Present it in terminal style

Use a fenced `text` block with plain terminal characters, stable IDs, and these states: `○ BLOCKED`, `◇ READY`, `▶ ACTIVE`, `✓ PASSED`, `✗ FAILED`, `– SKIPPED`.

```text
── IMPLEMENTATION GRAPH ─────────────────────────────────────
TASK     <preserved request>
GOAL     <observable outcome>
PROTECT  <critical existing behavior>
VISUAL   <required | not required>

[C0 ◇ READY] Contract + baseline
    └─locked→ [N1 ○ BLOCKED] Evidence-gathering discovery
        └─evidence→ [D1 ○ BLOCKED] ◆ Cause / design decision
            ├─condition A→ [N2A ○ BLOCKED] Bounded implementation A
            └─condition B→ [N2B ○ BLOCKED] Bounded implementation B
                └─selected→ [G1 ○ BLOCKED] Code + behavior gate
                    ├─pass→ [GV ○ BLOCKED] Visual-runtime gate
                    │   └─pass→ [T1 ○ BLOCKED] Verified completion
                    └─fail/repair→ [R1 ○ BLOCKED] Diagnose before editing
                        └─retry 1/2→ [↩ G1]

CURRENT  none
NEXT     Start C0
```

Omit `GV` when visual verification is irrelevant. Add a `ROUTES` ledger for non-linear topology using only `dependency`, `branch`, `repair`, and `retry` edge kinds. Keep node contracts to `scope`, `action`, and `exit evidence`, and include them only when the graph alone is insufficient.

For every branch, repair, retry, or multi-source merge, the `ROUTES` ledger is mandatory. List every edge so both branch alternatives visibly converge at the same integration or verification node; indentation alone is not proof of topology.

## Keep communication operational

- Opening update: one sentence stating the immediate action.
- Milestone update: result, decisive evidence, and next action in at most three short lines.
- Blocker update: blocker, evidence, completed scope, and shortest unblock; omit speculation.
- Plan-only response: terminal graph plus only the contracts or caveats needed to execute it.
- Final response: outcome first, latest compact graph, verification, and real limitations.

Do not explain graph theory, restate the request, list routine tool calls, or write a chronological work log unless the user asks.

## Execute without drift

- Keep at most one node `active` unless the user explicitly authorized parallel agents.
- Before a node, reread state, inspect the diff, confirm dependencies, and open only relevant files.
- Mark the node active, make the smallest coherent change, run its exit checks, and inspect its scoped diff.
- Exceed declared scope only after updating and validating the graph.
- Pass a node only with concise, fresh evidence: command or inspection, result, and relevant artifact.
- Update `changed_files`, decisions, unresolved risks, `next_action`, and the checkpoint after each node. Keep entries short; do not turn state into a transcript.
- Never weaken requirements, assertions, tests, types, lint, security controls, or accessibility checks merely to obtain a pass.

## Verify code and rendered reality

Use the smallest verification matrix that covers the risk.

### Code and behavior gate

- Reproduce defects before modifying when feasible; keep the regression test.
- Run targeted tests first, then affected integration and regression checks.
- Exercise adjacent behavior, error paths, boundary contracts, and protected invariants in proportion to risk.
- Inspect runtime logs and console errors when the changed path executes.

### Visual-runtime gate

Require this gate for user-visible UI, layout, styling, responsive behavior, animation, visual assets, or design-reference work.

- Run the actual application; source review and component tests alone cannot pass this gate.
- Inspect rendered output with available browser, screenshot, or preview tooling.
- Compare against the stated requirement or reference at representative viewport sizes and relevant themes.
- Check alignment, spacing, clipping, overflow, typography, stacking, responsive reflow, focus states, and interaction feedback.
- Exercise relevant loading, empty, error, long-content, and disabled states rather than checking only the happy-path screenshot.
- Pair visual inspection with accessibility and interaction checks; visual similarity cannot prove semantics or keyboard behavior.
- Keep semantic, accessible-name, and keyboard assertions in the code/behavior gate or a dedicated accessibility gate. The visual gate may inspect visible focus, contrast, and rendered feedback, but never substitutes for those assertions.
- Record what was inspected and where. Any relevant UI edit after inspection invalidates the visual pass.
- If visual tooling or a required reference is unavailable, mark the gate `blocked` or `not verified`; never infer a visual pass from code.

If code passes but visuals fail, route to a visual repair node, apply one bounded correction, then rerun both affected code checks and the visual gate.

## Persist, diagnose, or stop

- Do not give up after the first failure. Record the exact failure and follow the repair edge while a distinct, evidence-backed action remains.
- Do not repeat the same hypothesis more than twice. On the second failure, stop patch stacking and return to diagnosis or redesign.
- Stop when authorization or credentials are missing, the next action is destructive or materially ambiguous, required evidence cannot be obtained, the retry budget is exhausted, or evidence shows the requested outcome is unsafe or infeasible.
- When stopped, preserve state and report only: the blocker, evidence, completed scope, and shortest action that would unblock progress. Never label partial work complete.

## Recover after compaction

1. Locate the active graph and run `checkpoint` plus `validate`.
2. Inspect actual `git status` and diff.
3. Reopen the current node's files and artifacts.
4. Rerun checks invalidated by later edits.
5. State the current node and next action in one concise update, then continue.

## Complete honestly

Pass the terminal node only when every required criterion and invariant has fresh evidence, all required nodes passed, unused routes are explicitly skipped, code and required visual gates passed after the final relevant edit, the complete diff and untracked files are accounted for, and no unresolved risk contradicts completion.

In the final handoff, lead with the outcome, paste the latest compact terminal graph, then list verification evidence, limitations, working-tree scope, and state path. Distinguish `verified`, `blocked`, and `not run`; omit process narration.
