────────

name: render-terminal-graphs description: Render workflows, architecture, implementation plans, task dependencies, troubleshooting paths, data flows, and completion states as lightweight terminal-style inline HTML graphs. Use whenever the user asks for a graph, dependency graph, terminal-style graph, visual workflow, architecture flow, implementation map, or asks to make an explanation look like the rack-tool graph. Also use when an interconnected process would be substantially clearer as a graph. Do not use for ordinary single facts, one-step instructions, or simple comparisons with no meaningful dependencies.

Render Terminal Graphs

Display the finished graph directly in the conversation as responsive inline HTML. Preserve the visual language of the rack-tool graph: transparent surface, monospace text, numbered nodes, thin SVG connectors, generous vertical spacing, and restrained status color.

Build the graph

1. Reduce the subject to actions, inputs, checks, decisions, repair routes, and outcomes.
2. Assign short labels such as [01], [02A], and [02B].
3. Arrange prerequisites above their dependents. Place parallel nodes in the same row, with no more than three nodes per row.
4. Keep each node to a short name and at most three compact detail lines.
5. Label comparison inputs EXPECTED and OBSERVED when applicable.
6. Distinguish confirmed failures from missing evidence. Use FAIL for a demonstrated problem and INCOMPLETE for an unverified result.
7. Connect only real dependencies. Merge parallel branches at their next shared dependency.

Render it

Use scripts/render_terminal_graph.py to keep the appearance consistent. Create a temporary JSON specification matching this shape:

```json
{
  "title": "$ rack-tool / proposed workflow",
  "aria_label": "A short accessible description of the complete graph.",
  "rows": [
    [{"id":"1","label":"[01] USER","name":"Choose action","details":["Select a rack"]}],
    [
      {"id":"2","label":"[02A] PLAN","name":"NetBox","details":["Expected endpoints"]},
      {"id":"3","label":"[02B] LIVE","name":"Arista EOS","details":["Observed state"]}
    ],
    [{"id":"4","label":"[03] RESULT","name":"PASS","status":"pass","details":["Checks agree"]}]
  ],
  "edges": [["1","2"],["1","3"],["2","4"],["3","4"]]
}
```

Run:

```bash
python3 <skill-root>/scripts/render_terminal_graph.py graph.json /workspace/<concise-title>.html
```

Write inline visualization files to /workspace as lowercase hyphenated names. The generator produces an HTML fragment, not a standalone webpage.

Display the generated file using the host’s inline visualization content reference. Do not provide a download link, expose the HTML source, or describe the rendering mechanism unless the user explicitly asks.

Appearance contract

• Keep the background transparent and the overall surface unframed.
• Use monospace text and centered node content.
• Use no cards, boxes, shadows, gradients, decorative borders, or oversized icons.
• Draw thin neutral connector lines with small arrowheads behind the node text.
• Use neutral theme-aware colors for text and lines.
• Use green only for PASS or ACCEPTED, red only for FAIL or REPAIR, and orange only for INCOMPLETE or UNKNOWN.
• Reflow at narrow widths without clipped or overlapping text.
• Include a concise visible terminal title beginning with $.
• Include an accessible description covering the full graph.

Response contract

Return the rendered graph as the main answer. Add at most one short sentence outside it when the user needs a key limitation or decision explained.

Always use inline HTML for these graphs. Do not substitute Mermaid, ASCII art, Markdown tables, or an HTML code block merely because they are faster. If the runtime cannot display inline HTML visualizations, state that briefly and use Mermaid as the emergency fallback.


## Visual communication

Use terminal-style dependency graphs when explaining:

- Architecture and data flow
- Implementation plans
- Task dependencies
- Troubleshooting paths
- Testing and completion status

Graph requirements:

- Use a monospace terminal appearance.
- Use numbered nodes such as `[01]`, `[02A]`, and `[02B]`.
- Connect dependent nodes with visible lines and arrows.
- Keep node descriptions short and easy to scan.
- Show parallel work in adjacent columns.
- Show decision gates and repair paths.
- End implementation graphs with `PASS`, `FAIL`, and `INCOMPLETE`
  states where appropriate.
- Prefer a rendered HTML visualization when available.
- Use Mermaid as a fallback.
- Use plain text only when rendered formats are unavailable.










# Implement with Graph

A Codex skill for executing non-trivial code changes through a persistent terminal-style dependency graph.

It is built for the failure modes that waste the most time: context compaction, vague completion claims, repeated patching, regressions, weaker-model drift, and UI changes where tests pass but the rendered result is still wrong.

## Core behavior

- Acts after the minimum safe inspection instead of turning implementation into an essay.
- Keeps user-facing updates to decisions, evidence, blockers, and verified outcomes.
- Preserves the original request, acceptance criteria, protected invariants, non-goals, baseline, decisions, risks, and changed files in durable state.
- Breaks work into bounded nodes with explicit dependencies, branches, repair routes, and retry limits.
- Requires fresh evidence before a node can pass.
- Recovers after context compaction from graph state, the real diff, and rerun checks—not chat memory.
- Treats passing code checks and correct rendered behavior as separate facts.
- Persists through evidence-backed repair routes, but stops before blind patch stacking or unsafe guessing.

## Code proof is not visual proof

For UI work, the graph has two independent gates:

| Gate | Proves | Does not prove |
|---|---|---|
| Code + behavior | Tests, types, integration behavior, invariants, keyboard order, accessible names | Pixel alignment, clipping, responsive reflow, visual parity |
| Visual runtime | The running product renders correctly at relevant viewports, themes, and states | Semantics, keyboard behavior, or correctness hidden behind the screenshot |

When `visual_required` is true, verified completion is impossible unless a `visual_gate` passes after the final relevant UI edit. The visual gate cannot be skipped. If the app, preview tooling, or required reference is unavailable, the task stays blocked or not verified.

## Example

```text
── IMPLEMENTATION GRAPH ─────────────────────────────────────
TASK     Fix dashboard cards overlapping at 768 px
GOAL     Match the reference without regressing 375 or 1440 px
PROTECT  Keyboard order, accessible names, and dark theme
VISUAL   required

[C0 ✓ PASSED] Contract + baseline
    └─locked→ [N1 ▶ ACTIVE] Reproduce and isolate the layout cause
        └─evidence→ [N2 ○ BLOCKED] Apply one bounded correction
            └─implemented→ [G1 ○ BLOCKED] Code + behavior gate
                ├─pass→ [GV ○ BLOCKED] Visual-runtime gate
                │   ├─pass→ [T1 ○ BLOCKED] Verified completion
                │   └─mismatch/repair→ [RV ○ BLOCKED] Visual repair
                │       └─recheck/retry 1/2→ [↩ G1]
                └─fail/repair→ [RC ○ BLOCKED] Code repair
                    └─retry 1/2→ [↩ G1]

CURRENT  N1
NEXT     Capture the 768 px failure and compare it to the reference

ROUTES
  C0 --locked/dependency--> N1
  N1 --evidence/dependency--> N2
  N2 --implemented/dependency--> G1
  G1 --pass/dependency--> GV
  G1 --fail/repair--> RC
  RC --retry 1/2/retry--> G1
  GV --pass/dependency--> T1
  GV --mismatch/repair--> RV
  RV --recheck 1/2/retry--> G1
```

For non-visual work, `VISUAL` is `not required` and the visual gate is omitted.

## Usage

Invoke it directly:

```text
Use $implement-with-graph to implement this change.
```

The skill also supports three operating modes:

- **Plan only:** inspect and return a compact terminal graph; the first executable node is ready and dependents are blocked. Nothing is active or passed without evidence.
- **Plan and implement:** create durable graph state, present the graph, and execute ready nodes.
- **Resume:** recover from state, diff, and fresh verification after interruption or context compaction.

## State helper

Graph state lives at `.codex/implementation-graphs/<task-slug>.json` during implementation.

```bash
python3 scripts/graph_state.py init .codex/implementation-graphs/task.json \
  --task "Task description" \
  --goal "Observable outcome" \
  --visual-required

python3 scripts/graph_state.py validate .codex/implementation-graphs/task.json
python3 scripts/graph_state.py render .codex/implementation-graphs/task.json
python3 scripts/graph_state.py checkpoint .codex/implementation-graphs/task.json

python3 scripts/graph_state.py set-status \
  .codex/implementation-graphs/task.json G1 passed \
  --evidence "Affected test suite: 42 passed" \
  --next "Run visual gate GV"
```

Existing schema-version-1 files without `visual_required` remain valid and default to non-visual work.

## Machine-enforced safeguards

The validator rejects:

- multiple active nodes;
- invalid dependencies and unbounded topology;
- graphs larger than 20 nodes instead of phased work;
- passed nodes without exit checks and evidence;
- completion without acceptance criteria, protected invariants, or a passed code/behavior gate;
- a terminal node that does not depend directly on verification;
- required visual work without a visual gate, a preceding code gate, or a visual repair route;
- skipped or incomplete required visual gates;
- completion with incomplete nodes, criteria, invariants, or unresolved risks;
- verbose multi-line `next_action` state that is hard to recover from.

## Visual-runtime verification

A visual pass requires the running product. Source review and unit tests are insufficient.

Inspect the relevant viewport sizes, themes, and states. Depending on the change, check alignment, spacing, typography, clipping, overflow, stacking, responsive reflow, visible focus, feedback, loading, empty, error, long-content, and disabled states. Record what was inspected and where. Any relevant UI edit invalidates the previous visual evidence.

If code passes but the rendered result fails, the graph routes to one bounded visual correction, then reruns affected code checks and visual inspection.

## Persistence and stopping

The skill does not quit after the first failure. It follows a distinct evidence-backed repair route while a safe path remains.

It stops when credentials or authority are missing, the next action is destructive or materially ambiguous, required evidence cannot be obtained, the retry budget is exhausted, or evidence shows the requested outcome is unsafe or infeasible. A stopped task reports the blocker, evidence, completed scope, and shortest unblock; it is never labeled complete.

## Repository structure

```text
SKILL.md                       Skill behavior and execution rules
agents/openai.yaml             Skill interface metadata
references/graph-contract.md   Durable state schema and graph contract
scripts/graph_state.py         State validator, renderer, and checkpoint helper
```

## Reliability boundary

This skill cannot make a weak model infallible. It makes drift and premature completion harder by turning scope, invariants, routing, retry limits, code evidence, visual evidence, and recovery state into explicit, machine-checked constraints.

Graph state files are local work artifacts by default. Do not stage, commit, overwrite, or delete them unless the user requests it.
