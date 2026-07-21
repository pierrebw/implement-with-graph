# Graph contract

The JSON graph is the durable control plane. The terminal view is a compact status display, not a work diary.

## State file shape

```json
{
  "schema_version": 1,
  "task": "Fix dashboard card overlap",
  "goal": "Cards remain aligned and usable at supported widths",
  "request": "Preserve the user's original request verbatim",
  "visual_required": true,
  "non_goals": ["Do not redesign unrelated dashboard sections"],
  "acceptance_criteria": [
    {
      "id": "A1",
      "text": "Cards do not overlap at 768 px",
      "status": "pending",
      "evidence": []
    }
  ],
  "invariants": [
    {
      "id": "I1",
      "text": "Keyboard order and accessible names remain correct",
      "check": "Run the dashboard accessibility check",
      "status": "pending",
      "evidence": []
    }
  ],
  "baseline": {
    "revision": "current commit or n/a",
    "working_tree": "clean, dirty, or concise scoped description",
    "checks": [],
    "pre_existing_failures": []
  },
  "nodes": [
    {
      "id": "C0",
      "title": "Contract and baseline",
      "kind": "contract",
      "status": "passed",
      "scope": ["request, repository state, existing checks"],
      "actions": ["Lock acceptance criteria and protected behavior"],
      "exit_checks": ["Contract and baseline are recorded"],
      "evidence": ["Request, working tree, and baseline reviewed"],
      "attempt": 1,
      "max_attempts": 1,
      "notes": ""
    },
    {
      "id": "G1",
      "title": "Code and behavior verification",
      "kind": "gate",
      "status": "blocked",
      "scope": ["affected dashboard behavior and regressions"],
      "actions": ["Run targeted and affected checks"],
      "exit_checks": ["Affected code and behavior checks pass"],
      "evidence": [],
      "attempt": 0,
      "max_attempts": 2,
      "notes": ""
    },
    {
      "id": "GV",
      "title": "Rendered dashboard verification",
      "kind": "visual_gate",
      "status": "blocked",
      "scope": ["dashboard at 375, 768, and 1440 px"],
      "actions": ["Run the app and inspect representative states"],
      "exit_checks": ["Compare rendered output to the requirement after the final UI edit"],
      "evidence": [],
      "attempt": 0,
      "max_attempts": 2,
      "notes": ""
    },
    {
      "id": "RV",
      "title": "Diagnose visual mismatch",
      "kind": "repair",
      "status": "blocked",
      "scope": ["the failed visual criterion"],
      "actions": ["Identify one evidence-backed correction"],
      "exit_checks": ["A bounded correction is ready for reinspection"],
      "evidence": [],
      "attempt": 0,
      "max_attempts": 2,
      "notes": ""
    },
    {
      "id": "T1",
      "title": "Verified completion",
      "kind": "terminal",
      "status": "blocked",
      "scope": ["complete task diff and evidence"],
      "actions": ["Review acceptance, invariants, risks, and changed files"],
      "exit_checks": ["Every required gate has fresh passing evidence"],
      "evidence": [],
      "attempt": 0,
      "max_attempts": 1,
      "notes": ""
    }
  ],
  "edges": [
    {"from": "C0", "to": "G1", "kind": "dependency", "label": "contract locked"},
    {"from": "G1", "to": "GV", "kind": "dependency", "label": "code passes"},
    {"from": "GV", "to": "T1", "kind": "dependency", "label": "visual pass"},
    {"from": "GV", "to": "RV", "kind": "repair", "label": "visual mismatch"},
    {"from": "RV", "to": "GV", "kind": "retry", "label": "reinspect"}
  ],
  "current_node": null,
  "next_action": "Start the contract and baseline",
  "changed_files": [],
  "decisions": [],
  "risks": [],
  "last_checkpoint": ""
}
```

`visual_required` is optional for compatibility and defaults to `false`. Set it to `true` whenever success includes rendered UI, layout, styling, animation, responsive behavior, or visual parity.

## Contract semantics

- Preserve `request`; compaction must not reinterpret the job.
- Make acceptance criteria observable and binary.
- Protect existing behavior with invariants. Record non-goals to prevent scope drift.
- Separate pre-existing failures from task-caused failures.
- Keep `risks` limited to unresolved threats to completion. Resolve or report every risk.
- Keep state concise: record decisions and evidence, not narration.

## Nodes

- `id`: stable ID such as `C0`, `N1`, `D1`, `G1`, `GV`, `R1`, or `T1`.
- `kind`: `contract`, `work`, `decision`, `gate`, `visual_gate`, `repair`, or `terminal`.
- `status`: `blocked`, `ready`, `active`, `passed`, `failed`, or `skipped`.
- `scope`: files, modules, behavior, viewports, or states the node may touch.
- `actions`: concrete operations, not vague goals.
- `exit_checks`: commands or inspections that prove completion.
- `evidence`: fresh result plus relevant command, runtime, screenshot, viewport, or artifact.
- `attempt` / `max_attempts`: bounded retries; default uncertain work to two attempts.

A passed node requires exit checks and evidence. A required `visual_gate` cannot be skipped. A passed terminal requires at least one acceptance criterion, one protected invariant, a passed code/behavior gate, and every required visual gate. The terminal must depend directly on a verification gate.

## Edges

- `dependency`: destination waits for the source to pass or be deliberately skipped.
- `branch`: a decision selects a route; record the choice and skip inactive alternatives.
- `repair`: a failed gate routes to diagnosis or correction.
- `retry`: repair returns to the exact invalidated gate.

Dependency and branch edges must be acyclic. Repair and retry edges may create bounded cycles. Every edge has one source and one destination. Converge selected branches at a named integration or gate node.

## Build only what controls the work

1. Start with contract and baseline.
2. Put evidence-gathering discovery before an uncertain decision.
3. Split only independently verifiable implementation surfaces.
4. Add targeted behavior, regression/invariant, and final acceptance gates.
5. When `visual_required` is true, add a `visual_gate` after code checks and before the terminal node.
6. Give failure-prone gates a repair route and retry limit.
7. End at exactly one terminal node.

Use about 4–7 nodes for a small change, 6–12 for medium work, and 10–15 for large or high-risk work. Split into phases before 20 nodes. A graph that takes longer to maintain than the change is too large.

## Visual proof

Code checks and source inspection cannot pass a visual gate. Evidence must come from the running product using browser, screenshot, or preview tooling and identify what was inspected.

Cover the states and viewports relevant to the request, including representative responsive widths and any affected theme. Inspect alignment, spacing, typography, clipping, overflow, stacking, visible focus, feedback, loading, empty, error, long-content, and disabled states as applicable. Keep semantic, accessible-name, and keyboard assertions in the code/behavior gate or a dedicated accessibility gate; visual similarity does not prove them.

Any relevant UI edit invalidates older visual evidence. If code passes but rendered output fails, route to a visual repair node, apply one bounded correction, then rerun affected code checks and the visual gate. If the app, tool, or required reference is unavailable, leave the gate blocked or failed; never infer a pass.

## Terminal presentation

```text
── IMPLEMENTATION GRAPH ─────────────────────────────────────
TASK     Fix dashboard card overlap
GOAL     Aligned and usable cards at supported widths
VISUAL   required

[C0 ✓ PASSED] Contract + baseline
    └─locked→ [N1 ▶ ACTIVE] Reproduce at 768 px
        └─evidence→ [N2 ○ BLOCKED] Bounded layout correction
            └─implemented→ [G1 ○ BLOCKED] Code + behavior gate
                ├─pass→ [GV ○ BLOCKED] Visual-runtime gate
                │   └─pass→ [T1 ○ BLOCKED] Verified completion
                └─fail/repair→ [R1 ○ BLOCKED] Diagnose before editing
                    └─retry 1/2→ [↩ G1]

CURRENT  N1
NEXT     Capture the 768 px failure
```

For non-linear graphs, append a `ROUTES` ledger as `SOURCE --label/kind--> TARGET`. Show node contracts only when the graph alone loses important scope or exit evidence.

In plan-only mode, the first executable node is `ready` and every dependent node is `blocked`. Nothing is `active` or `passed` without execution evidence. A branch, repair, retry, or multi-source merge always requires the complete `ROUTES` ledger; every selected branch must visibly converge.

## Freshness, retries, and stopping

- Evidence becomes stale after a relevant source, test, configuration, dependency, schema, generated artifact, or rendered UI change.
- Do not abandon the task on the first failure. Follow a distinct evidence-backed repair route.
- Do not repeat the same hypothesis more than twice. After the second failure, return to diagnosis or redesign instead of stacking patches.
- Stop only for missing authority or credentials, destructive ambiguity, unavailable required evidence, exhausted retry budget, or evidence that the outcome is unsafe or infeasible.
- On stop, preserve the graph and report the blocker, evidence, completed scope, and shortest unblock. Never mark partial work complete.
