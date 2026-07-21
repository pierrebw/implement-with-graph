# Graph contract

Use this contract when creating or restructuring an implementation graph. The JSON file is the durable source of truth; the terminal rendering is its human-facing view.

## State file shape

```json
{
  "schema_version": 1,
  "task": "Fix duplicate payment submission",
  "goal": "A single user action creates at most one charge",
  "request": "The user's original request, preserved without reinterpretation",
  "non_goals": ["Do not redesign the checkout UI"],
  "acceptance_criteria": [
    {
      "id": "A1",
      "text": "Repeated submission reuses the existing payment attempt",
      "status": "pending",
      "evidence": []
    }
  ],
  "invariants": [
    {
      "id": "I1",
      "text": "Existing successful checkout remains unchanged",
      "check": "pytest tests/checkout/test_success.py",
      "status": "pending",
      "evidence": []
    }
  ],
  "baseline": {
    "revision": "current commit or n/a",
    "working_tree": "clean, dirty, or a concise description",
    "checks": [
      {
        "command": "pytest tests/checkout",
        "status": "passed",
        "summary": "42 passed"
      }
    ],
    "pre_existing_failures": []
  },
  "nodes": [
    {
      "id": "N1",
      "title": "Reproduce duplicate submission",
      "kind": "work",
      "status": "ready",
      "scope": ["tests/checkout/test_idempotency.py"],
      "actions": ["Add a failing concurrency regression test"],
      "exit_checks": ["The test fails for the duplicate-charge reason"],
      "evidence": [],
      "attempt": 0,
      "max_attempts": 2,
      "notes": ""
    }
  ],
  "edges": [
    {"from": "N1", "to": "N2", "kind": "dependency", "label": "reproduced"},
    {"from": "G2", "to": "R1", "kind": "repair", "label": "fails"},
    {"from": "R1", "to": "G2", "kind": "retry", "label": "recheck"}
  ],
  "current_node": null,
  "next_action": "Start N1",
  "changed_files": [],
  "decisions": [],
  "risks": [],
  "last_checkpoint": ""
}
```

## Required semantics

### Contract fields

- Preserve `request` so later compression cannot silently change the task.
- Make acceptance criteria observable and binary where possible.
- Use invariants for behavior that must remain true while the requested behavior changes.
- Record non-goals to resist unrelated cleanup and scope drift.
- Keep `risks` for unresolved completion threats only. Use invariants for protected behavior and non-goals for scope boundaries; resolve or report every risk before completion.
- Record pre-existing failures separately; do not claim they were introduced by the task.

### Node fields

- `id`: Stable identifier such as `N1`, `D1`, `G1`, `R1`, or `T1`.
- `kind`: One of `contract`, `work`, `decision`, `gate`, `repair`, or `terminal`.
- `status`: One of `blocked`, `ready`, `active`, `passed`, `failed`, or `skipped`.
- `scope`: Expected files, modules, or behavior boundaries. Update before exceeding it.
- `actions`: Concrete operations; avoid vague verbs such as “improve” without an observable outcome.
- `exit_checks`: Commands or inspections that prove the node is complete.
- `evidence`: Fresh results supporting the current status. A passed node requires evidence.
- `attempt` and `max_attempts`: Bound repeated repair. Default to two attempts for uncertain work.

### Edge fields

- `dependency`: The destination cannot start until the source passes or is deliberately skipped.
- `branch`: A decision routes to one or more explicitly selected destinations; mark inactive alternatives skipped with a decision record.
- `repair`: A failed gate routes to diagnosis or repair.
- `retry`: Repair routes back to the exact invalidated gate, not automatically to the entire task.

When a branch or repair route is not taken, mark its nodes `skipped` and record why in `decisions`. Do not leave unused routes blocked at completion.

Dependency and branch edges must be acyclic. Repair and retry edges may form bounded cycles.

Every edge has exactly one source and one destination. If routing depends on new evidence, introduce a decision node; never use an ambiguous destination such as “A or B.” Every branch used by the task must visibly converge at a named integration or verification node.

Use only `dependency`, `branch`, `repair`, and `retry` as edge kinds. A merge is modeled by multiple dependency edges targeting the same node, never by a separate `merge` kind.

## Graph construction rules

1. Start with a contract/baseline node.
2. Put discovery before design decisions when repository evidence is needed.
   - Unknown cause: add a decision node and conditional solution branches.
   - Mutually exclusive hypotheses: never place their fixes on one unconditional path.
   - Unknown mechanism: keep implementation nodes conditional until evidence selects them.
3. Split independent implementation surfaces into separate nodes.
4. Merge them at an integration node.
5. Use a targeted verification gate before the regression gate.
6. Give every failure-prone gate a named repair route and retry limit.
7. End at exactly one terminal node.
8. Make the terminal node depend on the final regression and acceptance gate.

Keep the graph small enough to reason about. Prefer 6–15 nodes. If it exceeds 20, collapse detail into node actions or divide the task into graph phases with explicit handoff gates.

## Terminal presentation

Use the helper's rendering as the default. When writing one manually, use a fenced `text` block and keep IDs identical to the state file:

```text
── IMPLEMENTATION GRAPH ─────────────────────────────────────
TASK  Prevent duplicate payment submission
GOAL  One action creates at most one charge

[C0 ✓ PASSED] Contract + baseline
  └─locked→ [N1 ▶ ACTIVE] Reproduce duplicate submission
               └─reproduced→ [N2 ○ BLOCKED] Add idempotency boundary
                                  └─implemented→ [G1 ○ BLOCKED] Targeted tests
                                                       ├─pass→ [G2 ○ BLOCKED] Regression gate
                                                       └─fail→ [R1 ○ BLOCKED] Diagnose + repair
                                                                          └─retry→ [↩ G1]

CURRENT  N1 — Reproduce duplicate submission
NEXT     Run the concurrency reproduction test
```

The diagram must expose branches, merges, failure routes, and blocked work. Follow it with node contracts only when details would otherwise be lost.

For any non-linear graph, append a `ROUTES` ledger listing each edge as `SOURCE --label/kind--> TARGET`. This is the topology source of truth when terminal indentation is imperfect.

## Evidence freshness

Treat evidence as stale when any relevant source, test, configuration, dependency, schema, or generated artifact changed after the evidence was collected. Rerun the invalidated gate and replace or annotate the evidence; never silently carry a pass across a relevant edit.
