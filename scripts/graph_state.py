#!/usr/bin/env python3
"""Create, validate, update, and render persistent implementation graphs."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
NODE_KINDS = {"contract", "work", "decision", "gate", "visual_gate", "repair", "terminal"}
NODE_STATUSES = {"blocked", "ready", "active", "passed", "failed", "skipped"}
EDGE_KINDS = {"dependency", "branch", "repair", "retry"}
CHECK_STATUSES = {"not_run", "pending", "passed", "failed", "blocked"}
STATUS_MARKS = {
    "blocked": "○ BLOCKED",
    "ready": "◇ READY",
    "active": "▶ ACTIVE",
    "passed": "✓ PASSED",
    "failed": "✗ FAILED",
    "skipped": "– SKIPPED",
}


class GraphError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_graph(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GraphError(f"state file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise GraphError(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise GraphError("top-level graph value must be an object")
    return data


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def require_list(value: Any, location: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{location} must be a list")
        return []
    return value


def validate_graph(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must equal {SCHEMA_VERSION}")

    visual_required = data.get("visual_required", False)
    if not isinstance(visual_required, bool):
        errors.append("visual_required must be a boolean when present")
        visual_required = False

    for field in ("task", "goal", "request", "next_action", "last_checkpoint"):
        if not isinstance(data.get(field), str):
            errors.append(f"{field} must be a string")
    next_action = data.get("next_action")
    if isinstance(next_action, str) and ("\n" in next_action or len(next_action) > 240):
        errors.append("next_action must be one concise line of at most 240 characters")

    for field in ("non_goals", "changed_files", "decisions", "risks"):
        require_list(data.get(field), field, errors)

    for collection_name in ("acceptance_criteria", "invariants"):
        entries = require_list(data.get(collection_name), collection_name, errors)
        seen_entry_ids: set[str] = set()
        for index, entry in enumerate(entries):
            location = f"{collection_name}[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{location} must be an object")
                continue
            entry_id = entry.get("id")
            if not isinstance(entry_id, str) or not entry_id:
                errors.append(f"{location}.id must be a non-empty string")
            elif entry_id in seen_entry_ids:
                errors.append(f"duplicate {collection_name} id: {entry_id}")
            else:
                seen_entry_ids.add(entry_id)
            if not isinstance(entry.get("text"), str) or not entry.get("text"):
                errors.append(f"{location}.text must be a non-empty string")
            status = entry.get("status")
            if status not in CHECK_STATUSES:
                errors.append(f"{location}.status must be one of {sorted(CHECK_STATUSES)}")
            evidence = require_list(entry.get("evidence"), f"{location}.evidence", errors)
            if status == "passed" and not evidence:
                errors.append(f"{location} is passed but has no evidence")
            if collection_name == "invariants" and not isinstance(entry.get("check"), str):
                errors.append(f"{location}.check must be a string")

    baseline = data.get("baseline")
    if not isinstance(baseline, dict):
        errors.append("baseline must be an object")
    else:
        for field in ("revision", "working_tree"):
            if not isinstance(baseline.get(field), str):
                errors.append(f"baseline.{field} must be a string")
        checks = require_list(baseline.get("checks"), "baseline.checks", errors)
        require_list(baseline.get("pre_existing_failures"), "baseline.pre_existing_failures", errors)
        for index, check in enumerate(checks):
            location = f"baseline.checks[{index}]"
            if not isinstance(check, dict):
                errors.append(f"{location} must be an object")
                continue
            if not isinstance(check.get("command"), str):
                errors.append(f"{location}.command must be a string")
            if check.get("status") not in CHECK_STATUSES:
                errors.append(f"{location}.status must be one of {sorted(CHECK_STATUSES)}")
            if not isinstance(check.get("summary"), str):
                errors.append(f"{location}.summary must be a string")

    nodes = require_list(data.get("nodes"), "nodes", errors)
    node_map: dict[str, dict[str, Any]] = {}
    active_ids: list[str] = []
    terminal_ids: list[str] = []
    gate_ids: list[str] = []
    visual_gate_ids: list[str] = []
    for index, node in enumerate(nodes):
        location = f"nodes[{index}]"
        if not isinstance(node, dict):
            errors.append(f"{location} must be an object")
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", node_id):
            errors.append(f"{location}.id must start with a letter and contain only letters, digits, _ or -")
            continue
        if node_id in node_map:
            errors.append(f"duplicate node id: {node_id}")
            continue
        node_map[node_id] = node
        if not isinstance(node.get("title"), str) or not node.get("title"):
            errors.append(f"{location}.title must be a non-empty string")
        if node.get("kind") not in NODE_KINDS:
            errors.append(f"{location}.kind must be one of {sorted(NODE_KINDS)}")
        status = node.get("status")
        if status not in NODE_STATUSES:
            errors.append(f"{location}.status must be one of {sorted(NODE_STATUSES)}")
        if status == "active":
            active_ids.append(node_id)
        if node.get("kind") == "terminal":
            terminal_ids.append(node_id)
        if node.get("kind") == "gate":
            gate_ids.append(node_id)
        if node.get("kind") == "visual_gate":
            visual_gate_ids.append(node_id)
            if visual_required and status == "skipped":
                errors.append(f"{location} is a required visual gate and cannot be skipped")
        for field in ("scope", "actions", "exit_checks", "evidence"):
            require_list(node.get(field), f"{location}.{field}", errors)
        if not isinstance(node.get("notes"), str):
            errors.append(f"{location}.notes must be a string")
        attempt = node.get("attempt")
        max_attempts = node.get("max_attempts")
        if not isinstance(attempt, int) or attempt < 0:
            errors.append(f"{location}.attempt must be a non-negative integer")
        if not isinstance(max_attempts, int) or max_attempts < 1:
            errors.append(f"{location}.max_attempts must be an integer of at least 1")
        if isinstance(attempt, int) and isinstance(max_attempts, int) and attempt > max_attempts:
            errors.append(f"{location}.attempt exceeds max_attempts")
        if status == "passed" and not node.get("exit_checks"):
            errors.append(f"{location} is passed but has no exit_checks")
        if status == "passed" and not node.get("evidence"):
            errors.append(f"{location} is passed but has no evidence")

    if len(active_ids) > 1:
        errors.append(f"at most one node may be active; found {active_ids}")
    if len(nodes) > 20:
        errors.append("a graph may contain at most 20 nodes; split larger work into phases")
    if nodes and len(terminal_ids) != 1:
        errors.append(f"a populated graph must contain exactly one terminal node; found {terminal_ids}")
    if nodes and visual_required and not visual_gate_ids:
        errors.append("visual_required is true but the graph has no visual_gate node")

    current_node = data.get("current_node")
    if current_node is not None and current_node not in node_map:
        errors.append(f"current_node references unknown node: {current_node}")
    if active_ids and current_node != active_ids[0]:
        errors.append(f"current_node must match active node {active_ids[0]}")
    if not active_ids and current_node is not None:
        errors.append("current_node must be null when no node is active")

    edges = require_list(data.get("edges"), "edges", errors)
    dependency_adjacency: dict[str, list[str]] = defaultdict(list)
    incoming_dependencies: dict[str, list[str]] = defaultdict(list)
    outgoing_repair: set[str] = set()
    edge_keys: set[tuple[str, str, str, str]] = set()
    for index, edge in enumerate(edges):
        location = f"edges[{index}]"
        if not isinstance(edge, dict):
            errors.append(f"{location} must be an object")
            continue
        source, target, kind, label = edge.get("from"), edge.get("to"), edge.get("kind"), edge.get("label")
        if source not in node_map:
            errors.append(f"{location}.from references unknown node: {source}")
        if target not in node_map:
            errors.append(f"{location}.to references unknown node: {target}")
        if kind not in EDGE_KINDS:
            errors.append(f"{location}.kind must be one of {sorted(EDGE_KINDS)}")
        if not isinstance(label, str):
            errors.append(f"{location}.label must be a string")
            label = ""
        key = (str(source), str(target), str(kind), label)
        if key in edge_keys:
            errors.append(f"duplicate edge: {source} -> {target} ({kind}, {label})")
        edge_keys.add(key)
        if source in node_map and target in node_map and kind in {"dependency", "branch"}:
            dependency_adjacency[source].append(target)
            incoming_dependencies[target].append(source)
        if source in node_map and kind == "repair":
            outgoing_repair.add(source)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            errors.append(f"dependency/branch cycle detected at {node_id}; use repair/retry edges for bounded cycles")
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        for child in dependency_adjacency.get(node_id, []):
            visit(child)
        visiting.remove(node_id)
        visited.add(node_id)

    for node_id in node_map:
        visit(node_id)

    for node_id, node in node_map.items():
        if node.get("status") in {"ready", "active"}:
            unmet = [source for source in incoming_dependencies.get(node_id, []) if node_map[source].get("status") not in {"passed", "skipped"}]
            if unmet:
                errors.append(f"{node_id} is {node.get('status')} but dependencies are unmet: {unmet}")
        if node.get("status") == "failed" and node_id not in outgoing_repair:
            errors.append(f"{node_id} is failed but has no outgoing repair edge")

    for terminal_id in terminal_ids:
        gate_predecessors = [
            source
            for source in incoming_dependencies.get(terminal_id, [])
            if node_map[source].get("kind") in {"gate", "visual_gate"}
        ]
        if not gate_predecessors:
            errors.append(f"terminal node {terminal_id} must depend directly on a verification gate")

    if visual_required:
        for visual_gate_id in visual_gate_ids:
            code_gate_predecessors = [
                source
                for source in incoming_dependencies.get(visual_gate_id, [])
                if node_map[source].get("kind") == "gate"
            ]
            if not code_gate_predecessors:
                errors.append(
                    f"required visual gate {visual_gate_id} must depend directly on a code/behavior gate"
                )
            if visual_gate_id not in outgoing_repair:
                errors.append(f"required visual gate {visual_gate_id} must have an outgoing repair edge")

    for terminal_id in terminal_ids:
        terminal = node_map[terminal_id]
        if terminal.get("status") == "passed":
            incomplete_nodes = [
                node_id
                for node_id, node in node_map.items()
                if node_id != terminal_id and node.get("status") not in {"passed", "skipped"}
            ]
            if incomplete_nodes:
                errors.append(f"terminal node passed while required nodes remain incomplete: {incomplete_nodes}")
            incomplete_acceptance = [
                entry.get("id") for entry in data.get("acceptance_criteria", []) if entry.get("status") != "passed"
            ]
            incomplete_invariants = [
                entry.get("id") for entry in data.get("invariants", []) if entry.get("status") != "passed"
            ]
            if incomplete_acceptance:
                errors.append(f"terminal node passed with incomplete acceptance criteria: {incomplete_acceptance}")
            if not data.get("acceptance_criteria"):
                errors.append("terminal node passed without acceptance criteria")
            if incomplete_invariants:
                errors.append(f"terminal node passed with incomplete invariants: {incomplete_invariants}")
            if not data.get("invariants"):
                errors.append("terminal node passed without protected invariants")
            if not any(node_map[node_id].get("status") == "passed" for node_id in gate_ids):
                errors.append("terminal node passed without a passed code/behavior gate")
            if data.get("risks"):
                errors.append("terminal node passed while unresolved risks remain")
            if visual_required:
                incomplete_visual = [
                    node_id for node_id in visual_gate_ids if node_map[node_id].get("status") != "passed"
                ]
                if incomplete_visual:
                    errors.append(f"terminal node passed with incomplete visual gates: {incomplete_visual}")

    return errors


def index_nodes(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {node["id"]: node for node in data.get("nodes", []) if isinstance(node, dict) and "id" in node}


def edge_text(edge: dict[str, Any]) -> str:
    label = str(edge.get("label") or edge.get("kind") or "next")
    if edge.get("kind") == "repair":
        return f"{label}/repair"
    if edge.get("kind") == "retry":
        return f"{label}/retry"
    return label


def node_text(node: dict[str, Any], reference: bool = False) -> str:
    marker = STATUS_MARKS.get(node.get("status"), "? UNKNOWN")
    prefix = "↩ " if reference else ""
    return f"[{prefix}{node.get('id', '?')} {marker}] {node.get('title', '')}"


def render_graph(data: dict[str, Any]) -> str:
    node_map = index_nodes(data)
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming_count: dict[str, int] = defaultdict(int)
    for edge in data.get("edges", []):
        if not isinstance(edge, dict):
            continue
        source, target = edge.get("from"), edge.get("to")
        if source in node_map and target in node_map:
            outgoing[source].append(edge)
            if edge.get("kind") in {"dependency", "branch"}:
                incoming_count[target] += 1

    for edge_list in outgoing.values():
        edge_list.sort(key=lambda edge: (str(edge.get("kind")), str(edge.get("to"))))

    roots = sorted(node_id for node_id in node_map if incoming_count[node_id] == 0)
    if not roots and node_map:
        roots = [sorted(node_map)[0]]

    lines = [
        "── IMPLEMENTATION GRAPH " + "─" * 39,
        f"TASK     {data.get('task', '')}",
        f"GOAL     {data.get('goal', '')}",
        f"VISUAL   {'required' if data.get('visual_required', False) else 'not required'}",
        "",
    ]
    expanded: set[str] = set()

    def walk(node_id: str, indent: str = "", connector: str = "") -> None:
        already_expanded = node_id in expanded
        lines.append(indent + connector + node_text(node_map[node_id], reference=already_expanded))
        if already_expanded:
            return
        expanded.add(node_id)
        children = outgoing.get(node_id, [])
        for index, edge in enumerate(children):
            child_id = edge["to"]
            last = index == len(children) - 1
            branch = "└─" if last else "├─"
            connector_text = f"{branch}{edge_text(edge)}→ "
            walk(child_id, indent + "    ", connector_text)

    for index, root in enumerate(roots):
        if root in expanded:
            continue
        if index:
            lines.append("")
        walk(root)

    unrendered = sorted(set(node_map) - expanded)
    if unrendered:
        lines.extend(["", "UNREACHED / CONDITIONAL"])
        for node_id in unrendered:
            lines.append("  " + node_text(node_map[node_id]))

    if data.get("edges"):
        lines.extend(["", "ROUTES"])
        for edge in sorted(
            data.get("edges", []),
            key=lambda item: (str(item.get("from")), str(item.get("to")), str(item.get("kind"))),
        ):
            route_label = str(edge.get("label") or "next")
            lines.append(
                f"  {edge.get('from')} --{route_label}/{edge.get('kind')}--> {edge.get('to')}"
            )

    current = data.get("current_node") or "none"
    lines.extend(
        [
            "",
            f"CURRENT  {current}",
            f"NEXT     {data.get('next_action', '') or 'not recorded'}",
            f"STATE    {data.get('last_checkpoint', '') or 'not checkpointed'}",
        ]
    )
    return "\n".join(lines)


def checkpoint_text(data: dict[str, Any]) -> str:
    node_map = index_nodes(data)
    by_status: dict[str, list[str]] = defaultdict(list)
    for node_id, node in node_map.items():
        by_status[str(node.get("status"))].append(node_id)

    def joined(status: str) -> str:
        return ", ".join(sorted(by_status.get(status, []))) or "none"

    acceptance = data.get("acceptance_criteria", [])
    invariants = data.get("invariants", [])
    visual_gates = [node for node in node_map.values() if node.get("kind") == "visual_gate"]
    visual_summary = (
        f"required — {sum(1 for node in visual_gates if node.get('status') == 'passed')}/{len(visual_gates)} passed"
        if data.get("visual_required", False)
        else "not required"
    )
    lines = [
        "── RECOVERY CHECKPOINT " + "─" * 39,
        f"TASK       {data.get('task', '')}",
        f"GOAL       {data.get('goal', '')}",
        f"CURRENT    {data.get('current_node') or 'none'}",
        f"NEXT       {data.get('next_action', '') or 'not recorded'}",
        f"PASSED     {joined('passed')}",
        f"READY      {joined('ready')}",
        f"FAILED     {joined('failed')}",
        f"BLOCKED    {joined('blocked')}",
        f"ACCEPTANCE {sum(1 for item in acceptance if item.get('status') == 'passed')}/{len(acceptance)} passed",
        f"INVARIANTS {sum(1 for item in invariants if item.get('status') == 'passed')}/{len(invariants)} passed",
        f"VISUAL     {visual_summary}",
        f"CHANGED    {', '.join(data.get('changed_files', [])) or 'none recorded'}",
        f"RISKS      {len(data.get('risks', []))}",
        f"UPDATED    {data.get('last_checkpoint', '') or 'not checkpointed'}",
    ]
    if data.get("decisions"):
        lines.append("DECISIONS")
        for decision in data["decisions"][-5:]:
            lines.append(f"  - {decision}")
    if data.get("risks"):
        lines.append("OPEN RISKS")
        for risk in data["risks"]:
            lines.append(f"  - {risk}")
    return "\n".join(lines)


def command_init(args: argparse.Namespace) -> None:
    path = Path(args.path)
    if path.exists() and not args.force:
        raise GraphError(f"refusing to overwrite existing state file: {path}")
    data: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task": args.task,
        "goal": args.goal,
        "request": args.request or args.task,
        "visual_required": args.visual_required,
        "non_goals": [],
        "acceptance_criteria": [],
        "invariants": [],
        "baseline": {
            "revision": "",
            "working_tree": "",
            "checks": [],
            "pre_existing_failures": [],
        },
        "nodes": [],
        "edges": [],
        "current_node": None,
        "next_action": "Define the contract, baseline, nodes, and gates",
        "changed_files": [],
        "decisions": [],
        "risks": [],
        "last_checkpoint": utc_now(),
    }
    atomic_write(path, data)
    print(f"initialized {path}")


def command_validate(args: argparse.Namespace) -> None:
    data = read_graph(Path(args.path))
    errors = validate_graph(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise GraphError(f"graph validation failed with {len(errors)} error(s)")
    print("graph valid")


def command_render(args: argparse.Namespace) -> None:
    data = read_graph(Path(args.path))
    errors = validate_graph(data)
    if errors and not args.allow_invalid:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise GraphError("refusing to render invalid graph; pass --allow-invalid to inspect it")
    print(render_graph(data))


def command_checkpoint(args: argparse.Namespace) -> None:
    data = read_graph(Path(args.path))
    print(checkpoint_text(data))


def incoming_blockers(data: dict[str, Any], node_id: str) -> list[str]:
    node_map = index_nodes(data)
    blockers: list[str] = []
    for edge in data.get("edges", []):
        if edge.get("to") != node_id or edge.get("kind") not in {"dependency", "branch"}:
            continue
        source = edge.get("from")
        if source in node_map and node_map[source].get("status") not in {"passed", "skipped"}:
            blockers.append(source)
    return blockers


def refresh_routed_states(data: dict[str, Any], source_id: str, source_status: str) -> None:
    node_map = index_nodes(data)
    if source_status in {"passed", "skipped"}:
        for candidate_id, candidate in node_map.items():
            if candidate.get("status") != "blocked":
                continue
            incoming = [
                edge
                for edge in data.get("edges", [])
                if edge.get("to") == candidate_id and edge.get("kind") in {"dependency", "branch"}
            ]
            if not incoming or any(edge.get("kind") == "branch" for edge in incoming):
                continue
            if all(node_map[edge["from"]].get("status") in {"passed", "skipped"} for edge in incoming):
                candidate["status"] = "ready"

    route_kind = "repair" if source_status == "failed" else "retry" if source_status == "passed" else None
    if route_kind:
        for edge in data.get("edges", []):
            if edge.get("from") != source_id or edge.get("kind") != route_kind:
                continue
            target = node_map.get(edge.get("to"))
            if target and target.get("status") in {"blocked", "failed"}:
                if target.get("attempt", 0) < target.get("max_attempts", 1):
                    target["status"] = "ready"
                else:
                    risk = (
                        f"Retry budget exhausted for {target.get('id')} after "
                        f"{target.get('attempt')} attempt(s); reassess the graph before further edits"
                    )
                    if risk not in data.setdefault("risks", []):
                        data["risks"].append(risk)


def command_set_status(args: argparse.Namespace) -> None:
    path = Path(args.path)
    data = read_graph(path)
    errors = validate_graph(data)
    if errors:
        raise GraphError("graph is invalid before transition: " + "; ".join(errors))
    node_map = index_nodes(data)
    if args.node_id not in node_map:
        raise GraphError(f"unknown node: {args.node_id}")
    node = node_map[args.node_id]
    previous_status = node.get("status")

    if args.status == "active" and previous_status != "ready":
        raise GraphError(f"only a ready node can become active; {args.node_id} is {previous_status}")
    if args.status in {"passed", "failed"} and previous_status != "active":
        raise GraphError(f"only an active node can become {args.status}; {args.node_id} is {previous_status}")
    if args.status == "skipped" and previous_status not in {"blocked", "ready"}:
        raise GraphError(f"only a blocked or ready node can be skipped; {args.node_id} is {previous_status}")

    if args.status == "active":
        active = [item["id"] for item in data["nodes"] if item.get("status") == "active" and item["id"] != args.node_id]
        if active:
            raise GraphError(f"another node is already active: {active}")
        blockers = incoming_blockers(data, args.node_id)
        if blockers:
            raise GraphError(f"cannot activate {args.node_id}; unmet dependencies: {blockers}")
        if node.get("attempt", 0) >= node.get("max_attempts", 1):
            raise GraphError(f"cannot activate {args.node_id}; retry budget exhausted")
        node["attempt"] = node.get("attempt", 0) + 1
        data["current_node"] = args.node_id

    if args.status in {"passed", "failed"} and args.evidence:
        node.setdefault("evidence", []).append(args.evidence)
    if args.status in {"passed", "failed"} and not node.get("evidence"):
        raise GraphError(f"{args.status} transition requires --evidence or existing evidence")
    if args.status == "passed" and not node.get("exit_checks"):
        raise GraphError("passed transition requires at least one exit check")
    if args.status == "failed":
        repair_edges = [
            edge for edge in data.get("edges", []) if edge.get("from") == args.node_id and edge.get("kind") == "repair"
        ]
        if not repair_edges:
            raise GraphError("failed transition requires an outgoing repair edge")

    node["status"] = args.status
    if args.status != "active" and data.get("current_node") == args.node_id:
        data["current_node"] = None
    refresh_routed_states(data, args.node_id, args.status)
    if args.next_action is not None:
        data["next_action"] = args.next_action
    data["last_checkpoint"] = utc_now()

    post_errors = validate_graph(data)
    if post_errors:
        raise GraphError("transition produced invalid graph: " + "; ".join(post_errors))
    atomic_write(path, data)
    print(f"{args.node_id}: {args.status}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="create a new graph state file")
    init_parser.add_argument("path")
    init_parser.add_argument("--task", required=True)
    init_parser.add_argument("--goal", required=True)
    init_parser.add_argument("--request")
    init_parser.add_argument(
        "--visual-required",
        action="store_true",
        help="require a passed visual-runtime gate before verified completion",
    )
    init_parser.add_argument("--force", action="store_true", help="overwrite an existing file")
    init_parser.set_defaults(func=command_init)

    validate_parser = subparsers.add_parser("validate", help="validate graph structure and state")
    validate_parser.add_argument("path")
    validate_parser.set_defaults(func=command_validate)

    render_parser = subparsers.add_parser("render", help="render a terminal-style graph")
    render_parser.add_argument("path")
    render_parser.add_argument("--allow-invalid", action="store_true")
    render_parser.set_defaults(func=command_render)

    checkpoint_parser = subparsers.add_parser("checkpoint", help="print a compact recovery checkpoint")
    checkpoint_parser.add_argument("path")
    checkpoint_parser.set_defaults(func=command_checkpoint)

    status_parser = subparsers.add_parser("set-status", help="transition a node status")
    status_parser.add_argument("path")
    status_parser.add_argument("node_id")
    status_parser.add_argument("status", choices=sorted(NODE_STATUSES))
    status_parser.add_argument("--evidence")
    status_parser.add_argument("--next", dest="next_action")
    status_parser.set_defaults(func=command_set_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except GraphError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
