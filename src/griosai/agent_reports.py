from __future__ import annotations

import json
from html import escape
from typing import Mapping

from .agent_constants import DEFAULT_CLAIM_STRATEGY
from .agent_text import _quarantine_target_text, _single_line, _table_number


def _render_scorecard_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    variant = payload["variant"]
    criteria = payload["criteria"]
    metrics = payload["metrics"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Scorecard ' + str(payload['scorecard_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Scorecard",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Run: {escape(_single_line(str(payload['run_id'])))}",
        f"Variant: {escape(_single_line(str(variant['id'])))}",
        f"Status: {escape(_single_line(str(payload['status'])))}",
        f"Aggregate: {escape(_single_line(str(payload['aggregate_metric'])))}="
        f"{_table_number(payload.get('aggregate_score'))}",
        "",
        "## Criteria",
        "",
        "| Criterion | Raw | Normalized | Weight | Weighted | Direction |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    if isinstance(criteria, list):
        for item in criteria:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('name', ''))))} | "
                f"{_table_number(item.get('raw_score'))} | "
                f"{_table_number(item.get('normalized_score'))} | "
                f"{_table_number(item.get('weight'))} | "
                f"{_table_number(item.get('weighted_score'))} | "
                f"{escape(_single_line(str(item.get('direction', ''))))} |"
            )
    lines.extend(["", "## Outcome Metrics", ""])
    if isinstance(metrics, dict):
        for key in sorted(metrics):
            lines.append(
                f"- {escape(_single_line(str(key)))}: {_table_number(metrics.get(key))}"
            )
    lines.append("")
    return "\n".join(lines)


def _render_work_packet_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    variant = payload["variant"]
    parallel = payload.get("parallel") if isinstance(payload.get("parallel"), dict) else {}
    claim = payload.get("claim") if isinstance(payload.get("claim"), dict) else {}
    rubric = payload.get("rubric") if isinstance(payload.get("rubric"), dict) else {}
    criteria = rubric.get("criteria") if isinstance(rubric, dict) else []
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Work Packet ' + str(payload['packet_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Work Packet",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Run: {escape(_single_line(str(payload['run_id'])))}",
        f"Variant: {escape(_single_line(str(variant['id'])))} "
        f"({escape(_single_line(str(variant['provider'])))}:{escape(_single_line(str(variant['model'])))})",
        f"Adapter: {escape(_single_line(str(variant.get('adapter') or '')))}",
        f"Lane: {escape(_single_line(str(parallel.get('lane_id') or '')))}",
        f"Role: {escape(_single_line(str(parallel.get('role') or '')))}",
        f"Objective: {escape(_single_line(str(parallel.get('objective') or '')))}",
        f"Claim: {escape(_single_line(str(claim.get('claim_id') or 'none')))} "
        f"({escape(_single_line(str(claim.get('status') or 'unclaimed')))})",
        "",
        "## Instructions",
        "",
    ]
    instructions = payload.get("instructions")
    if isinstance(instructions, list):
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in instructions)
    lines.extend(["", "## Rubric", ""])
    if isinstance(criteria, list):
        for item in criteria:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- {escape(_single_line(str(item.get('name', ''))))}: "
                f"weight={_table_number(item.get('weight'))}, "
                f"range={_table_number(item.get('min'))}-{_table_number(item.get('max'))}, "
                f"direction={escape(_single_line(str(item.get('direction', ''))))}"
            )
    lines.extend(["", "## Next Commands", ""])
    commands = payload.get("next_commands")
    if isinstance(commands, list):
        lines.extend(f"- `{escape(_single_line(str(item)))}`" for item in commands)
    lines.append("")
    return "\n".join(lines)


def _render_ingest_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"]
    entries = payload["entries"]
    errors = payload["errors"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Ingest ' + str(payload['ingest_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Ingest",
        "",
        f"Status: {escape(_single_line(str(payload['ingest_status'])))}",
        f"Scope: {escape(_single_line(str(payload.get('scope') or 'none')))}",
        f"Requested: {int(summary['requested_count'])}",
        f"Ingested: {int(summary['ingested_count'])}",
        f"Errors: {int(summary['error_count'])}",
        f"Outcomes: {int(summary['outcome_count'])}",
        f"Scorecards: {int(summary['scorecard_count'])}",
        "",
        "## Entries",
        "",
        "| Mode | Run | Variant | Status | Outcome | Scorecard |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if isinstance(entries, list):
        for item in entries:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('mode', ''))))} | "
                f"{escape(_single_line(str(item.get('run_id', ''))))} | "
                f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
                f"{escape(_single_line(str(item.get('status') or '')))} | "
                f"{escape(_single_line(str(item.get('outcome_id') or '')))} | "
                f"{escape(_single_line(str(item.get('scorecard_id') or '')))} |"
            )
    lines.extend(["", "## Errors", ""])
    if isinstance(errors, list) and errors:
        for item in errors:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- index {int(item.get('index') or 0)} "
                f"{escape(_single_line(str(item.get('run_id') or '')))} "
                f"{escape(_single_line(str(item.get('code') or '')))}: "
                f"{escape(_single_line(str(item.get('message') or '')))}"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_dispatch_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    entries = payload["entries"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Dispatch ' + str(payload['dispatch_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Dispatch",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Plan: {escape(_single_line(str(payload['plan_id'])))}",
        f"Status: {escape(_single_line(str(payload['dispatch_status'])))}",
        f"Lane: {escape(_single_line(str(payload.get('lane_id') or 'all')))}",
        f"Claim strategy: {escape(_single_line(str(payload.get('claim_strategy') or DEFAULT_CLAIM_STRATEGY)))}",
        f"Claims: {int(payload['claimed_count'])}/{int(payload['requested_count'])}",
        f"Work packets: {int(payload['work_packet_count'])}",
        "",
        "## Workers",
        "",
        "| Worker | Run | Lane | Role | Variant | Provider | Model | Claim | Work packet |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    if isinstance(entries, list):
        for item in entries:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('worker_id', ''))))} | "
                f"{escape(_single_line(str(item.get('run_id', ''))))} | "
                f"{escape(_single_line(str(item.get('lane_id') or '')))} | "
                f"{escape(_single_line(str(item.get('role') or '')))} | "
                f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
                f"{escape(_single_line(str(item.get('provider') or '')))} | "
                f"{escape(_single_line(str(item.get('model') or '')))} | "
                f"{escape(_single_line(str(item.get('claim_path') or '')))} | "
                f"{escape(_single_line(str(item.get('work_packet_path') or '')))} |"
            )
    lines.append("")
    return "\n".join(lines)


def _render_hold_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), Mapping) else {}
    active_holds = payload["active_holds"] if isinstance(payload.get("active_holds"), list) else []
    released = payload["released_hold_ids"] if isinstance(payload.get("released_hold_ids"), list) else []
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Hold ' + str(payload['hold_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Hold",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Action: {escape(_single_line(str(payload.get('action') or '')))}",
        f"Status: {escape(_single_line(str(payload.get('hold_status') or '')))}",
        f"Scopes: {escape(_single_line(', '.join(str(item) for item in payload.get('scopes', []))))}",
        f"Expires: {escape(_single_line(str(payload.get('expires_at') or 'none')))}",
        f"Reason: {escape(_single_line(str(payload.get('reason') or '')))}",
        "",
        "## Released Holds",
        "",
    ]
    if released:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in released)
    else:
        lines.append("- None")
    lines.extend(["", "## Active Holds", ""])
    if active_holds:
        lines.extend(
            [
                "| Hold | Scopes | Expires | Reason |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in active_holds:
            if not isinstance(item, Mapping):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('hold_id') or '')))} | "
                f"{escape(_single_line(', '.join(str(value) for value in item.get('scopes', []))))} | "
                f"{escape(_single_line(str(item.get('expires_at') or 'none')))} | "
                f"{escape(_single_line(str(item.get('reason') or '')))} |"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_quarantine_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), Mapping) else {}
    target = payload["target"] if isinstance(payload.get("target"), Mapping) else {}
    active_quarantines = (
        payload["active_quarantines"]
        if isinstance(payload.get("active_quarantines"), list)
        else []
    )
    released = (
        payload["released_quarantine_ids"]
        if isinstance(payload.get("released_quarantine_ids"), list)
        else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Quarantine ' + str(payload['quarantine_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Quarantine",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Action: {escape(_single_line(str(payload.get('action') or '')))}",
        f"Status: {escape(_single_line(str(payload.get('quarantine_status') or '')))}",
        f"Target: {escape(_single_line(_quarantine_target_text(target)))}",
        f"Expires: {escape(_single_line(str(payload.get('expires_at') or 'none')))}",
        f"Reason: {escape(_single_line(str(payload.get('reason') or '')))}",
        "",
        "## Released Quarantines",
        "",
    ]
    if released:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in released)
    else:
        lines.append("- None")
    lines.extend(["", "## Active Quarantines", ""])
    if active_quarantines:
        lines.extend(
            [
                "| Quarantine | Target | Expires | Reason |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in active_quarantines:
            if not isinstance(item, Mapping):
                continue
            item_target = item.get("target") if isinstance(item.get("target"), Mapping) else {}
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('quarantine_id') or '')))} | "
                f"{escape(_single_line(_quarantine_target_text(item_target)))} | "
                f"{escape(_single_line(str(item.get('expires_at') or 'none')))} | "
                f"{escape(_single_line(str(item.get('reason') or '')))} |"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_circuit_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), Mapping) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), Mapping) else {}
    policy = payload["policy"] if isinstance(payload.get("policy"), Mapping) else {}
    groups = payload["groups"] if isinstance(payload.get("groups"), list) else []
    findings = payload["findings"] if isinstance(payload.get("findings"), list) else []
    actions = payload["actions"] if isinstance(payload.get("actions"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Circuit Breaker ' + str(payload['circuit_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Circuit Breaker",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload.get('circuit_status') or '')))}",
        f"Tripped: {str(bool(payload.get('tripped'))).lower()}",
        f"Group by: {escape(_single_line(str(policy.get('group_by') or '')))}",
        f"Outcomes: {int(summary.get('outcome_count') or 0)}",
        f"Groups: {int(summary.get('group_count') or 0)}",
        f"Tripped groups: {int(summary.get('tripped_groups') or 0)}",
        f"Actions: {int(summary.get('action_count') or 0)}",
        "",
        "## Policy",
        "",
        f"- Min outcomes: {int(policy.get('min_outcomes') or 0)}",
        f"- Recent limit: {escape(_single_line(str(policy.get('recent_limit'))))}",
        f"- Max failure rate: {_table_number(policy.get('max_failure_rate'))}",
        f"- Max mean latency ms: {_table_number(policy.get('max_mean_latency_ms'))}",
        f"- Max mean cost USD: {_table_number(policy.get('max_mean_cost_usd'))}",
        f"- Min primary metric: {_table_number(policy.get('min_primary_metric'))}",
        f"- Quarantine on trip: {str(bool(policy.get('quarantine_on_trip'))).lower()}",
        "",
        "## Groups",
        "",
        "| Group | State | Outcomes | Failed | Failure rate | Metric mean | Latency ms | Cost USD | Failures | Warnings |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in groups:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('group') or '')))} | "
            f"{escape(_single_line(str(item.get('circuit_state') or '')))} | "
            f"{int(item.get('outcome_count') or 0)} | "
            f"{int(item.get('failed') or 0)} | "
            f"{_table_number(item.get('failure_rate'))} | "
            f"{_table_number(item.get('primary_metric_mean'))} | "
            f"{_table_number(item.get('mean_latency_ms'))} | "
            f"{_table_number(item.get('mean_cost_usd'))} | "
            f"{escape(_single_line(', '.join(str(value) for value in item.get('failures', []))))} | "
            f"{escape(_single_line(', '.join(str(value) for value in item.get('warnings', []))))} |"
        )
    lines.extend(["", "## Actions", ""])
    if actions:
        for item in actions:
            if not isinstance(item, Mapping):
                continue
            lines.append(
                f"- {escape(_single_line(str(item.get('action') or '')))} "
                f"{escape(_single_line(str(item.get('group_by') or '')))}="
                f"{escape(_single_line(str(item.get('group') or '')))} "
                f"{escape(_single_line(str(item.get('status') or '')))} "
                f"{escape(_single_line(str(item.get('quarantine_id') or item.get('error') or '')))}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Findings", ""])
    for item in findings:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
            f"{escape(_single_line(str(item.get('group', ''))))} "
            f"{escape(_single_line(str(item.get('code', ''))))}: "
            f"{escape(_single_line(str(item.get('message', ''))))}"
        )
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_orchestration_report(payload: Mapping[str, object]) -> str:
    scope = payload["scope"] if isinstance(payload.get("scope"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    plans = payload["plans"] if isinstance(payload.get("plans"), list) else []
    dispatches = payload["dispatches"] if isinstance(payload.get("dispatches"), list) else []
    active_holds = payload["active_holds"] if isinstance(payload.get("active_holds"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    policy = payload.get("policy") if isinstance(payload.get("policy"), Mapping) else {}
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Orchestration ' + str(payload['orchestration_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Orchestration",
        "",
        f"Status: {escape(_single_line(str(payload['orchestration_status'])))}",
        f"Scope: {escape(_single_line(str(scope.get('mode') or '')))}",
        f"Claim strategy: {escape(_single_line(str(policy.get('claim_strategy') or DEFAULT_CLAIM_STRATEGY)))}",
        f"Plans: {int(summary.get('plan_count') or 0)}",
        f"Pending runs: {int(summary.get('pending_runs') or 0)}",
        f"Active claims: {int(summary.get('active_claims') or 0)}",
        f"Active holds: {int(summary.get('active_holds') or 0)}",
        f"Dispatches: {int(summary.get('dispatch_count') or 0)}",
        f"Claimed: {int(summary.get('claimed_count') or 0)}",
        f"Remaining capacity: {int(summary.get('remaining_capacity') or 0)}",
        "",
        "## Plans",
        "",
        "| Plan | Case | Expected | Complete | Pending | Active | Stale | Expired |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in plans:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('plan_id') or '')))} | "
            f"{escape(_single_line(str(item.get('case_id') or '')))} | "
            f"{int(item.get('expected_runs') or 0)} | "
            f"{int(item.get('completed_runs') or 0)} | "
            f"{int(item.get('pending_runs') or 0)} | "
            f"{int(item.get('active_claims') or 0)} | "
            f"{int(item.get('stale_claims') or 0)} | "
            f"{int(item.get('expired_claims') or 0)} |"
        )
    lines.extend(["", "## Dispatches", ""])
    if dispatches:
        lines.extend(
            [
                "| Dispatch | Plan | Status | Claims | Work packets |",
                "| --- | --- | --- | ---: | ---: |",
            ]
        )
        for item in dispatches:
            if not isinstance(item, Mapping):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('dispatch_id') or '')))} | "
                f"{escape(_single_line(str(item.get('plan_id') or '')))} | "
                f"{escape(_single_line(str(item.get('dispatch_status') or '')))} | "
                f"{int(item.get('claimed_count') or 0)} | "
                f"{int(item.get('work_packet_count') or 0)} |"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Active Holds", ""])
    if active_holds:
        lines.extend(["| Hold | Experiment | Scopes | Expires |", "| --- | --- | --- | --- |"])
        for item in active_holds:
            if not isinstance(item, Mapping):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('hold_id') or '')))} | "
                f"{escape(_single_line(str(item.get('experiment') or '')))} | "
                f"{escape(_single_line(', '.join(str(value) for value in item.get('scopes', []))))} | "
                f"{escape(_single_line(str(item.get('expires_at') or 'none')))} |"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        for item in recommendations:
            lines.append(f"- {escape(_single_line(str(item)))}")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_retry_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    replacement = payload["replacement_run"]
    variant = payload["variant"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Retry ' + str(payload['retry_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Retry",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Plan: {escape(_single_line(str(payload.get('plan_id') or 'none')))}",
        f"Reason: {escape(_single_line(str(payload['reason'])))}",
        f"Original run: {escape(_single_line(str(payload['original_run_id'])))}",
        f"Replacement run: {escape(_single_line(str(replacement['run_id'])))}",
        f"Replacement policy: {escape(_single_line(str(payload['replacement_policy'])))}",
        f"Variant: {escape(_single_line(str(variant['id'])))} "
        f"({escape(_single_line(str(variant['provider'])))}:{escape(_single_line(str(variant['model'])))})",
        "",
    ]
    return "\n".join(lines)


def _render_recovery_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    entries = payload["entries"] if isinstance(payload.get("entries"), list) else []
    errors = payload["errors"] if isinstance(payload.get("errors"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Recovery ' + str(payload['recovery_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Recovery",
        "",
        f"Status: {escape(_single_line(str(payload['recovery_status'])))}",
        f"Scope: {escape(_single_line(str(payload.get('scope') or 'all')))}",
        f"Candidates: {int(summary.get('candidate_count') or 0)}",
        f"Selected: {int(summary.get('selected_count') or 0)}",
        f"Retries: {int(summary.get('retry_count') or 0)}",
        f"Errors: {int(summary.get('error_count') or 0)}",
        "",
        "## Retries",
        "",
        "| Reason | Original run | Replacement run | Variant | Retry |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in entries:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('reason') or '')))} | "
            f"{escape(_single_line(str(item.get('original_run_id') or '')))} | "
            f"{escape(_single_line(str(item.get('replacement_run_id') or '')))} | "
            f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('retry_id') or '')))} |"
        )
    lines.extend(["", "## Errors", ""])
    if errors:
        for item in errors:
            if not isinstance(item, Mapping):
                continue
            lines.append(
                f"- {escape(_single_line(str(item.get('run_id') or '')))} "
                f"{escape(_single_line(str(item.get('code') or '')))}: "
                f"{escape(_single_line(str(item.get('message') or '')))}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_cycle_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    artifacts = payload["artifacts"] if isinstance(payload.get("artifacts"), dict) else {}
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Cycle ' + str(payload['cycle_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Cycle",
        "",
        f"Status: {escape(_single_line(str(payload['cycle_status'])))}",
        f"Recovered runs: {int(summary.get('recovered_runs') or 0)}",
        f"Dispatched runs: {int(summary.get('dispatched_runs') or 0)}",
        f"Pending plan runs: {int(summary.get('pending_plan_runs') or 0)}",
        f"Claimed plan runs: {int(summary.get('claimed_plan_runs') or 0)}",
        f"Watchdog findings: {int(summary.get('watchdog_findings') or 0)}",
        "",
        "## Artifacts",
        "",
        "| Artifact | Status | Id | Path | Report |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, item in artifacts.items():
        if not isinstance(item, Mapping):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(name)))} | "
            f"{escape(_single_line(str(item.get('status') or '')))} | "
            f"{escape(_single_line(str(item.get('artifact_id') or '')))} | "
            f"{escape(_single_line(str(item.get('path') or '')))} | "
            f"{escape(_single_line(str(item.get('report_path') or '')))} |"
        )
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_loop_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    cycles = payload["cycles"] if isinstance(payload.get("cycles"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Loop ' + str(payload['loop_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Loop",
        "",
        f"Status: {escape(_single_line(str(payload['loop_status'])))}",
        f"Executed cycles: {int(summary.get('executed_cycles') or 0)}/{int(summary.get('requested_cycles') or 0)}",
        f"Stop reason: {escape(_single_line(str(summary.get('stop_reason') or '')))}",
        f"Acted cycles: {int(summary.get('acted_cycles') or 0)}",
        f"Recovered runs: {int(summary.get('recovered_runs') or 0)}",
        f"Dispatched runs: {int(summary.get('dispatched_runs') or 0)}",
        f"Pending plan runs: {int(summary.get('pending_plan_runs') or 0)}",
        f"Claimed plan runs: {int(summary.get('claimed_plan_runs') or 0)}",
        "",
        "## Cycles",
        "",
        "| # | Status | Recovered | Dispatched | Pending | Claimed | Cycle | Report |",
        "| ---: | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in cycles:
        if not isinstance(item, Mapping):
            continue
        cycle_summary = item.get("summary") if isinstance(item.get("summary"), Mapping) else {}
        lines.append(
            "| "
            f"{int(item.get('index') or 0)} | "
            f"{escape(_single_line(str(item.get('cycle_status') or '')))} | "
            f"{int(cycle_summary.get('recovered_runs') or 0)} | "
            f"{int(cycle_summary.get('dispatched_runs') or 0)} | "
            f"{int(cycle_summary.get('pending_plan_runs') or 0)} | "
            f"{int(cycle_summary.get('claimed_plan_runs') or 0)} | "
            f"{escape(_single_line(str(item.get('cycle_id') or '')))} | "
            f"{escape(_single_line(str(item.get('report_path') or '')))} |"
        )
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_comparison_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    metric = payload["primary_metric"]
    policy = payload["policy"]
    summary = payload["summary"]
    variants = payload["variant_summaries"]
    pairwise = payload["pairwise"]
    frontier = payload.get("efficiency_frontier")
    recommendations = payload["recommendations"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Comparison ' + str(payload['comparison_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Comparison",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Primary metric: {escape(_single_line(str(metric['name'])))} "
        f"({escape(_single_line(str(metric['direction'])))})",
        f"Baseline: {escape(_single_line(str(payload['baseline_variant_id'])))}",
        f"Winner: {escape(_single_line(str(payload.get('winner_variant_id') or 'none')))}",
        f"Minimum samples: {int(policy['min_samples_per_variant'])}",
        f"Eligible variants: {int(summary['eligible_variant_count'])}/{int(summary['variant_count'])}",
        f"Sample balance ratio: {_table_number(summary.get('sample_balance_ratio'))}",
        "",
        "## Variant Summary",
        "",
        "| Variant | Provider | Model | Samples | Mean | Stddev | CI low | CI high | Success rate | Avg tokens | Avg latency ms | Avg cost USD |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    if isinstance(variants, list):
        for item in variants:
            if not isinstance(item, dict):
                continue
            ci = item.get("primary_metric_ci95") if isinstance(item.get("primary_metric_ci95"), dict) else {}
            usage = item.get("usage") if isinstance(item.get("usage"), dict) else {}
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('variant_id', ''))))} | "
                f"{escape(_single_line(str(item.get('provider', ''))))} | "
                f"{escape(_single_line(str(item.get('model', ''))))} | "
                f"{int(item.get('primary_metric_count') or 0)} | "
                f"{_table_number(item.get('primary_metric_mean'))} | "
                f"{_table_number(item.get('primary_metric_stddev'))} | "
                f"{_table_number(ci.get('low'))} | "
                f"{_table_number(ci.get('high'))} | "
                f"{_table_number(item.get('success_rate'))} | "
                f"{_table_number(usage.get('total_tokens_mean'))} | "
                f"{_table_number(usage.get('latency_ms_mean'))} | "
                f"{_table_number(usage.get('cost_usd_mean'))} |"
            )
    lines.extend(
        [
            "",
            "## Efficiency Frontier",
            "",
            "| Variant | Metric | Avg tokens | Avg latency ms | Avg cost USD | Metric / USD | Metric / 1k tokens |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    if isinstance(frontier, list):
        for item in frontier:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('variant_id', ''))))} | "
                f"{_table_number(item.get('metric'))} | "
                f"{_table_number(item.get('total_tokens_mean'))} | "
                f"{_table_number(item.get('latency_ms_mean'))} | "
                f"{_table_number(item.get('cost_usd_mean'))} | "
                f"{_table_number(item.get('metric_per_usd'))} | "
                f"{_table_number(item.get('metric_per_1k_tokens'))} |"
            )
    lines.extend(
        [
            "",
            "## Baseline Comparisons",
            "",
            "| Candidate | Status | Samples | Mean | Delta | Lift % | CI low | CI high | Confidence |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    if isinstance(pairwise, list):
        for item in pairwise:
            if not isinstance(item, dict):
                continue
            ci = item.get("delta_ci95") if isinstance(item.get("delta_ci95"), dict) else {}
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('candidate_variant_id', ''))))} | "
                f"{escape(_single_line(str(item.get('status', ''))))} | "
                f"{int(item.get('candidate_samples') or 0)} | "
                f"{_table_number(item.get('candidate_mean'))} | "
                f"{_table_number(item.get('directional_delta'))} | "
                f"{_table_number(item.get('lift_percent'))} | "
                f"{_table_number(ci.get('low'))} | "
                f"{_table_number(ci.get('high'))} | "
                f"{escape(_single_line(str(item.get('confidence', ''))))} |"
            )
    lines.extend(["", "## Recommendations", ""])
    if isinstance(recommendations, list):
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    lines.append("")
    return "\n".join(lines)


def _render_balance_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    scope = payload["scope"] if isinstance(payload.get("scope"), Mapping) else {}
    policy = payload["policy"] if isinstance(payload.get("policy"), Mapping) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), Mapping) else {}
    cells = payload["cells"] if isinstance(payload.get("cells"), list) else []
    findings = payload["findings"] if isinstance(payload.get("findings"), list) else []
    recommendations = payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Balance ' + str(payload['balance_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Balance",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Scope: {escape(_single_line(str(scope.get('mode') or 'experiment')))}",
        f"Status: {escape(_single_line(str(payload['balance_status'])))}",
        f"Balanced: {str(bool(payload.get('balanced'))).lower()}",
        f"Dimensions: {escape(_single_line(','.join(str(item) for item in policy.get('dimensions', []))))}",
        f"Minimum completed outcomes per cell: {int(policy.get('min_count_per_cell') or 0)}",
        f"Maximum sample skew: {int(policy.get('max_skew') or 0)}",
        "",
        "## Summary",
        "",
        f"- Cells: {int(summary.get('cell_count') or 0)}",
        f"- Completed runs: {int(summary.get('completed_runs') or 0)}/{int(summary.get('expected_runs') or 0)}",
        f"- Missing runs: {int(summary.get('missing_runs') or 0)}",
        f"- Empty cells: {int(summary.get('empty_cells') or 0)}",
        f"- Completed sample skew: {int(summary.get('sample_skew') or 0)}",
        f"- Balance ratio: {_table_number(summary.get('sample_balance_ratio'))}",
        "",
        "## Cells",
        "",
        "| Cell | Expected | Completed | Missing | Succeeded | Failed | Completion |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cell in cells:
        if not isinstance(cell, Mapping):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(cell.get('cell_id') or '')))} | "
            f"{int(cell.get('expected_count') or 0)} | "
            f"{int(cell.get('completed_count') or 0)} | "
            f"{int(cell.get('missing_count') or 0)} | "
            f"{int(cell.get('succeeded_count') or 0)} | "
            f"{int(cell.get('failed_count') or 0)} | "
            f"{_table_number(cell.get('completion_ratio'))} |"
        )
    lines.extend(["", "## Findings", ""])
    for item in findings:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            f"- {escape(_single_line(str(item.get('severity', '')).upper()))}: "
            f"{escape(_single_line(str(item.get('code', ''))))} - "
            f"{escape(_single_line(str(item.get('message', ''))))}"
        )
    lines.extend(["", "## Recommendations", ""])
    lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    lines.append("")
    return "\n".join(lines)


def _render_decision_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    metric = payload["primary_metric"] if isinstance(payload.get("primary_metric"), dict) else {}
    policy = payload["policy"] if isinstance(payload.get("policy"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    comparison = payload["comparison"] if isinstance(payload.get("comparison"), dict) else {}
    guardrails = payload["guardrails"] if isinstance(payload.get("guardrails"), dict) else {}
    variant_evidence = (
        payload["variant_evidence"] if isinstance(payload.get("variant_evidence"), dict) else {}
    )
    baseline = (
        variant_evidence.get("baseline")
        if isinstance(variant_evidence.get("baseline"), dict)
        else {}
    )
    candidate = (
        variant_evidence.get("candidate")
        if isinstance(variant_evidence.get("candidate"), dict)
        else {}
    )
    checks = guardrails.get("checks") if isinstance(guardrails.get("checks"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Decision ' + str(payload['decision_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Decision",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload['decision_status'])))}",
        f"Decision: {escape(_single_line(str(payload['decision'])))}",
        f"Primary metric: {escape(_single_line(str(metric.get('name') or '')))} "
        f"({escape(_single_line(str(metric.get('direction') or '')))})",
        f"Baseline: {escape(_single_line(str(payload.get('baseline_variant_id') or '')))}",
        f"Candidate: {escape(_single_line(str(payload.get('candidate_variant_id') or 'none')))}",
        f"Minimum samples: {int(policy.get('min_samples_per_variant') or 0)}",
        f"Minimum delta: {_table_number(policy.get('min_delta'))}",
        f"Confidence threshold: {_table_number(policy.get('confidence_threshold'))}",
        "",
        "## Sequential Evidence",
        "",
        "| Baseline samples | Candidate samples | Baseline mean | Candidate mean | Directional delta | Lift % | Z score | Confidence | Baseline confidence | Guardrails |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        "| "
        f"{int(summary.get('baseline_samples') or 0)} | "
        f"{int(summary.get('candidate_samples') or 0)} | "
        f"{_table_number(comparison.get('baseline_mean'))} | "
        f"{_table_number(comparison.get('candidate_mean'))} | "
        f"{_table_number(summary.get('directional_delta'))} | "
        f"{_table_number(summary.get('lift_percent'))} | "
        f"{_table_number(summary.get('z_score'))} | "
        f"{_table_number(summary.get('confidence'))} | "
        f"{_table_number(summary.get('baseline_confidence'))} | "
        f"{escape(_single_line(str(summary.get('guardrail_status') or '')))} |",
        "",
        "## Variant Evidence",
        "",
        "| Role | Variant | Provider | Model | Trials | Mean | Std err | Success | Avg tokens | Avg cost USD |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for role, item in (("baseline", baseline), ("candidate", candidate)):
        usage = item.get("usage") if isinstance(item.get("usage"), dict) else {}
        lines.append(
            "| "
            f"{role} | "
            f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('provider') or '')))} | "
            f"{escape(_single_line(str(item.get('model') or '')))} | "
            f"{int(item.get('trials') or 0)} | "
            f"{_table_number(item.get('primary_metric_mean'))} | "
            f"{_table_number(item.get('primary_metric_stderr'))} | "
            f"{_table_number(item.get('success_rate'))} | "
            f"{_table_number(usage.get('total_tokens_mean'))} | "
            f"{_table_number(usage.get('cost_usd_mean'))} |"
        )
    lines.extend(["", "## Guardrails", ""])
    if checks:
        lines.extend(
            [
                "| Check | Status | Observed | Limit |",
                "| --- | --- | ---: | ---: |",
            ]
        )
        for item in checks:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('name') or '')))} | "
                f"{escape(_single_line(str(item.get('status') or '')))} | "
                f"{_table_number(item.get('observed'))} | "
                f"{_table_number(item.get('limit'))} |"
            )
    else:
        lines.append("- No optional decision guardrails configured.")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_power_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    metric = payload["primary_metric"]
    policy = payload["policy"]
    summary = payload["summary"]
    plans = payload["variant_plans"]
    recommendations = payload["recommendations"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Power ' + str(payload['power_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Power",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Status: {escape(_single_line(str(payload['power_status'])))}",
        f"Primary metric: {escape(_single_line(str(metric['name'])))} "
        f"({escape(_single_line(str(metric['direction'])))})",
        f"Baseline: {escape(_single_line(str(payload['baseline_variant_id'])))}",
        f"Minimum detectable effect: {_table_number(policy.get('min_detectable_effect'))}",
        f"Alpha: {_table_number(policy.get('alpha'))}",
        f"Power: {_table_number(policy.get('power'))}",
        f"Max required samples per variant: {_table_number(summary.get('max_required_samples_per_variant'))}",
        f"Total additional samples: {int(summary.get('total_additional_samples') or 0)}",
        f"Estimated additional cost USD: {_table_number(summary.get('estimated_additional_cost_usd'))}",
        f"Estimated additional tokens: {_table_number(summary.get('estimated_additional_tokens'))}",
        "",
        "## Variant Plans",
        "",
        "| Candidate | Status | Current baseline | Current candidate | Required each | Add baseline | Add candidate | Delta | Stddev | Stddev source | Est cost USD | Est tokens |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    if isinstance(plans, list):
        for item in plans:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('candidate_variant_id', ''))))} | "
                f"{escape(_single_line(str(item.get('status', ''))))} | "
                f"{int(item.get('baseline_samples') or 0)} | "
                f"{int(item.get('candidate_samples') or 0)} | "
                f"{_table_number(item.get('required_samples_per_variant'))} | "
                f"{_table_number(item.get('additional_baseline_samples'))} | "
                f"{_table_number(item.get('additional_candidate_samples'))} | "
                f"{_table_number(item.get('observed_directional_delta'))} | "
                f"{_table_number(item.get('pooled_stddev'))} | "
                f"{escape(_single_line(str(item.get('stddev_source', ''))))} | "
                f"{_table_number(item.get('estimated_additional_cost_usd'))} | "
                f"{_table_number(item.get('estimated_additional_tokens'))} |"
            )
    lines.extend(["", "## Recommendations", ""])
    if isinstance(recommendations, list) and recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_schedule_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    quotas = payload["quotas"] if isinstance(payload.get("quotas"), list) else []
    candidates = payload["candidate_plans"] if isinstance(payload.get("candidate_plans"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Schedule ' + str(payload['schedule_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Schedule",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload['schedule_status'])))}",
        f"Power: {escape(_single_line(str(payload.get('power_id') or '')))}",
        f"Plan: {escape(_single_line(str(payload.get('plan_id') or 'none')))}",
        f"Requested runs: {int(summary.get('requested_runs') or 0)}",
        f"Scheduled runs: {int(summary.get('scheduled_runs') or 0)}",
        f"Max runs: {int(summary.get('max_runs') or 0)}",
        f"Paired: {str(bool(summary.get('paired'))).lower()}",
        f"Blocks: {int(summary.get('block_count') or 0)}",
        f"Truncated: {str(bool(summary.get('truncated'))).lower()}",
        "",
        "## Quotas",
        "",
        "| Variant | Scheduled runs |",
        "| --- | ---: |",
    ]
    for item in quotas:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
            f"{int(item.get('scheduled_runs') or 0)} |"
        )
    lines.extend(
        [
            "",
            "## Candidate Plans",
            "",
            "| Candidate | Power status | Add baseline | Add candidate | Scheduled |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    for item in candidates:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('candidate_variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('power_status') or '')))} | "
            f"{int(item.get('additional_baseline_samples') or 0)} | "
            f"{int(item.get('additional_candidate_samples') or 0)} | "
            f"{str(bool(item.get('scheduled'))).lower()} |"
        )
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_schedule_report_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    metric = payload["primary_metric"] if isinstance(payload.get("primary_metric"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    pairwise = payload["pairwise"] if isinstance(payload.get("pairwise"), list) else []
    lanes = payload["lane_summaries"] if isinstance(payload.get("lane_summaries"), list) else []
    blocks = payload["blocks"] if isinstance(payload.get("blocks"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Schedule Report ' + str(payload['report_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Schedule Report",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Schedule: {escape(_single_line(str(payload['schedule_id'])))}",
        f"Status: {escape(_single_line(str(payload['report_status'])))}",
        f"Baseline: {escape(_single_line(str(payload.get('baseline_variant_id') or '')))}",
        f"Winner: {escape(_single_line(str(payload.get('winner_variant_id') or 'none')))}",
        f"Primary metric: {escape(_single_line(str(metric.get('name') or '')))} "
        f"({escape(_single_line(str(metric.get('direction') or '')))})",
        f"Complete blocks: {int(summary.get('complete_blocks') or 0)}/{int(summary.get('block_count') or 0)}",
        f"Completed ratio: {_table_number(summary.get('completed_ratio'))}",
        f"Paired comparisons: {int(summary.get('paired_comparisons') or 0)}",
        "",
        "## Pairwise",
        "",
        "| Candidate | Status | Paired blocks | Mean directional delta | CI low | CI high | Wins | Losses | Ties | Confidence |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in pairwise:
        if not isinstance(item, dict):
            continue
        ci = item.get("delta_ci95") if isinstance(item.get("delta_ci95"), dict) else {}
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('candidate_variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('status') or '')))} | "
            f"{int(item.get('paired_blocks') or 0)} | "
            f"{_table_number(item.get('mean_directional_delta'))} | "
            f"{_table_number(ci.get('low') if isinstance(ci, dict) else None)} | "
            f"{_table_number(ci.get('high') if isinstance(ci, dict) else None)} | "
            f"{int(item.get('wins') or 0)} | "
            f"{int(item.get('losses') or 0)} | "
            f"{int(item.get('ties') or 0)} | "
            f"{escape(_single_line(str(item.get('confidence') or '')))} |"
        )
    lines.extend(
        [
            "",
            "## Lanes",
            "",
            "| Candidate | Lane | Paired blocks | Mean directional delta | Wins | Losses | Ties | Status |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for item in lanes:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('candidate_variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('lane_id') or '')))} | "
            f"{int(item.get('paired_blocks') or 0)} | "
            f"{_table_number(item.get('mean_directional_delta'))} | "
            f"{int(item.get('wins') or 0)} | "
            f"{int(item.get('losses') or 0)} | "
            f"{int(item.get('ties') or 0)} | "
            f"{escape(_single_line(str(item.get('status') or '')))} |"
        )
    lines.extend(
        [
            "",
            "## Blocks",
            "",
            "| Block | Lane | Candidate | Status | Baseline metric | Candidate metric | Directional delta |",
            "| --- | --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for item in blocks:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('block_id') or '')))} | "
            f"{escape(_single_line(str(item.get('lane_id') or '')))} | "
            f"{escape(_single_line(str(item.get('candidate_variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('block_status') or '')))} | "
            f"{_table_number(item.get('baseline_metric'))} | "
            f"{_table_number(item.get('candidate_metric'))} | "
            f"{_table_number(item.get('directional_delta'))} |"
        )
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_arena_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    matches = payload["matches"] if isinstance(payload.get("matches"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Arena ' + str(payload['arena_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Arena",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload['arena_status'])))}",
        f"Plan: {escape(_single_line(str(payload.get('plan_id') or 'none')))}",
        f"Matches: {int(summary.get('scheduled_matches') or 0)}/{int(summary.get('requested_matches') or 0)}",
        f"Runs: {int(summary.get('scheduled_runs') or 0)}/{int(summary.get('requested_runs') or 0)}",
        "",
        "## Matches",
        "",
        "| Match | Lane | Replica | Variant A | Variant B | Runs |",
        "| --- | --- | ---: | --- | --- | ---: |",
    ]
    for item in matches:
        if not isinstance(item, dict):
            continue
        runs = item.get("runs") if isinstance(item.get("runs"), list) else []
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('match_id') or '')))} | "
            f"{escape(_single_line(str(item.get('lane_id') or '')))} | "
            f"{int(item.get('replica') or 0)} | "
            f"{escape(_single_line(str(item.get('variant_a_id') or '')))} | "
            f"{escape(_single_line(str(item.get('variant_b_id') or '')))} | "
            f"{len(runs)} |"
        )
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_arena_report_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    metric = payload["primary_metric"] if isinstance(payload.get("primary_metric"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    variants = payload["variant_summaries"] if isinstance(payload.get("variant_summaries"), list) else []
    pairwise = payload["pairwise"] if isinstance(payload.get("pairwise"), list) else []
    matches = payload["matches"] if isinstance(payload.get("matches"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Arena Report ' + str(payload['report_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Arena Report",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Arena: {escape(_single_line(str(payload['arena_id'])))}",
        f"Status: {escape(_single_line(str(payload['report_status'])))}",
        f"Winner: {escape(_single_line(str(payload.get('winner_variant_id') or 'none')))}",
        f"Primary metric: {escape(_single_line(str(metric.get('name') or '')))} "
        f"({escape(_single_line(str(metric.get('direction') or '')))})",
        f"Complete matches: {int(summary.get('complete_matches') or 0)}/{int(summary.get('scheduled_matches') or 0)}",
        "",
        "## Variant Standings",
        "",
        "| Rank | Variant | Provider | Model | Wins | Losses | Ties | Win rate | Mean metric | Arena rating |",
        "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in variants:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            f"{int(item.get('rank') or 0)} | "
            f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('provider') or '')))} | "
            f"{escape(_single_line(str(item.get('model') or '')))} | "
            f"{int(item.get('wins') or 0)} | "
            f"{int(item.get('losses') or 0)} | "
            f"{int(item.get('ties') or 0)} | "
            f"{_table_number(item.get('win_rate'))} | "
            f"{_table_number(item.get('metric_mean'))} | "
            f"{_table_number(item.get('arena_rating'))} |"
        )
    lines.extend(
        [
            "",
            "## Pairwise",
            "",
            "| Pair | Status | Completed | Left | Right | Left wins | Right wins | Ties | Winner |",
            "| --- | --- | ---: | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for item in pairwise:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('pair_id') or '')))} | "
            f"{escape(_single_line(str(item.get('status') or '')))} | "
            f"{int(item.get('completed_matches') or 0)} | "
            f"{escape(_single_line(str(item.get('left_variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('right_variant_id') or '')))} | "
            f"{int(item.get('left_wins') or 0)} | "
            f"{int(item.get('right_wins') or 0)} | "
            f"{int(item.get('ties') or 0)} | "
            f"{escape(_single_line(str(item.get('winner_variant_id') or '')))} |"
        )
    lines.extend(
        [
            "",
            "## Matches",
            "",
            "| Match | Lane | Status | Variant A | Metric A | Variant B | Metric B | Winner |",
            "| --- | --- | --- | --- | ---: | --- | ---: | --- |",
        ]
    )
    for item in matches:
        if not isinstance(item, dict):
            continue
        runs = item.get("runs") if isinstance(item.get("runs"), list) else []
        left = runs[0] if len(runs) > 0 and isinstance(runs[0], dict) else {}
        right = runs[1] if len(runs) > 1 and isinstance(runs[1], dict) else {}
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('match_id') or '')))} | "
            f"{escape(_single_line(str(item.get('lane_id') or '')))} | "
            f"{escape(_single_line(str(item.get('match_status') or '')))} | "
            f"{escape(_single_line(str(left.get('variant_id') or '')))} | "
            f"{_table_number(left.get('metric'))} | "
            f"{escape(_single_line(str(right.get('variant_id') or '')))} | "
            f"{_table_number(right.get('metric'))} | "
            f"{escape(_single_line(str(item.get('winner_variant_id') or 'tie')))} |"
        )
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_judge_panel_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    targets = payload["targets"] if isinstance(payload.get("targets"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Judge Panel ' + str(payload['panel_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Judge Panel",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload['panel_status'])))}",
        f"Source plan: {escape(_single_line(str(payload.get('source_plan_id') or '')))}",
        f"Judge plan: {escape(_single_line(str(payload.get('plan_id') or 'none')))}",
        f"Targets: {int(summary.get('target_count') or 0)}",
        f"Judge runs: {int(summary.get('scheduled_runs') or 0)}/{int(summary.get('requested_runs') or 0)}",
        "",
        "## Targets",
        "",
        "| Target run | Variant | Outcome | Judge runs |",
        "| --- | --- | --- | ---: |",
    ]
    for item in targets:
        if not isinstance(item, dict):
            continue
        judge_runs = item.get("judge_runs") if isinstance(item.get("judge_runs"), list) else []
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('target_run_id') or '')))} | "
            f"{escape(_single_line(str(item.get('target_variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('outcome_status') or '')))} | "
            f"{len(judge_runs)} |"
        )
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_judge_panel_report_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    metric = payload["judge_metric"] if isinstance(payload.get("judge_metric"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    targets = payload["target_summaries"] if isinstance(payload.get("target_summaries"), list) else []
    variants = payload["variant_summaries"] if isinstance(payload.get("variant_summaries"), list) else []
    judges = payload["judge_summaries"] if isinstance(payload.get("judge_summaries"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Judge Report ' + str(payload['report_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Judge Report",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Panel: {escape(_single_line(str(payload['panel_id'])))}",
        f"Status: {escape(_single_line(str(payload['report_status'])))}",
        f"Winner variant: {escape(_single_line(str(payload.get('winner_variant_id') or 'none')))}",
        f"Winner target: {escape(_single_line(str(payload.get('winner_target_run_id') or 'none')))}",
        f"Judge metric: {escape(_single_line(str(metric.get('name') or '')))} "
        f"({escape(_single_line(str(metric.get('direction') or '')))})",
        f"Judgements: {int(summary.get('completed_judgements') or 0)}/{int(summary.get('judge_run_count') or 0)}",
        "",
        "## Variant Summary",
        "",
        "| Rank | Variant | Provider | Model | Targets | Judged | Mean score | Judgements |",
        "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for item in variants:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            f"{int(item.get('rank') or 0)} | "
            f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('provider') or '')))} | "
            f"{escape(_single_line(str(item.get('model') or '')))} | "
            f"{int(item.get('target_count') or 0)} | "
            f"{int(item.get('judged_target_count') or 0)} | "
            f"{_table_number(item.get('score_mean'))} | "
            f"{int(item.get('completed_judgements') or 0)} |"
        )
    lines.extend(
        [
            "",
            "## Targets",
            "",
            "| Target run | Variant | Status | Judgements | Mean score | CI low | CI high |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in targets:
        if not isinstance(item, dict):
            continue
        ci = item.get("score_ci95") if isinstance(item.get("score_ci95"), dict) else {}
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('target_run_id') or '')))} | "
            f"{escape(_single_line(str(item.get('target_variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('status') or '')))} | "
            f"{int(item.get('completed_judgements') or 0)}/{int(item.get('judge_run_count') or 0)} | "
            f"{_table_number(item.get('score_mean'))} | "
            f"{_table_number(ci.get('low'))} | "
            f"{_table_number(ci.get('high'))} |"
        )
    lines.extend(
        [
            "",
            "## Judges",
            "",
            "| Judge variant | Runs | Completed | Mean score |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for item in judges:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('judge_variant_id') or '')))} | "
            f"{int(item.get('judge_run_count') or 0)} | "
            f"{int(item.get('completed_judgements') or 0)} | "
            f"{_table_number(item.get('score_mean'))} |"
        )
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_pipeline_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    pipeline = payload["pipeline"] if isinstance(payload.get("pipeline"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    stages = payload["stage_statuses"] if isinstance(payload.get("stage_statuses"), list) else []
    plans = payload["plans"] if isinstance(payload.get("plans"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Pipeline ' + str(payload['pipeline_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Pipeline",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Pipeline: {escape(_single_line(str(pipeline.get('name') or pipeline.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload['pipeline_status'])))}",
        f"Stages: {int(summary.get('planned_stages') or 0)}/{int(summary.get('stage_count') or 0)} planned",
        f"Scheduled now: {int(summary.get('scheduled_now') or 0)}",
        "",
        "## Stages",
        "",
        "| Stage | Status | Gate | Depends on | Plan | Runs | Success | Required |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for item in stages:
        if not isinstance(item, dict):
            continue
        deps = item.get("depends_on") if isinstance(item.get("depends_on"), list) else []
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('stage_id') or '')))} | "
            f"{escape(_single_line(str(item.get('stage_status') or '')))} | "
            f"{escape(_single_line(str(item.get('gate_status') or '')))} | "
            f"{escape(_single_line(', '.join(str(dep) for dep in deps) or 'none'))} | "
            f"{escape(_single_line(str(item.get('plan_id') or '')))} | "
            f"{int(item.get('completed_runs') or 0)}/{int(item.get('expected_runs') or 0)} | "
            f"{_table_number(item.get('success_ratio'))} | "
            f"{_table_number(item.get('min_success_ratio'))} |"
        )
    lines.extend(["", "## Plans", ""])
    if plans:
        lines.extend(["| Stage | Plan | Runs |", "| --- | --- | ---: |"])
        for item in plans:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('stage_id') or '')))} | "
                f"{escape(_single_line(str(item.get('plan_id') or '')))} | "
                f"{int(item.get('run_count') or 0)} |"
            )
    else:
        lines.append("- No stage plans scheduled in this pass.")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_pipeline_advance_report(payload: Mapping[str, object]) -> str:
    pipeline_payload = dict(payload)
    pipeline_payload["pipeline_status"] = payload.get("advance_status")
    pipeline_payload["pipeline"] = {"name": payload.get("pipeline_id"), "slug": payload.get("pipeline_id")}
    rendered = _render_pipeline_report(pipeline_payload)
    return rendered.replace("# Agent Harness Pipeline", "# Agent Harness Pipeline Advance", 1)


def _render_leaderboard_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    metric = payload["primary_metric"] if isinstance(payload.get("primary_metric"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    rows = payload["leaderboard"] if isinstance(payload.get("leaderboard"), list) else []
    sources = payload["source_artifacts"] if isinstance(payload.get("source_artifacts"), dict) else {}
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Leaderboard ' + str(payload['leaderboard_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Leaderboard",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload['leaderboard_status'])))}",
        f"Baseline: {escape(_single_line(str(payload.get('baseline_variant_id') or '')))}",
        f"Winner: {escape(_single_line(str(payload.get('winner_variant_id') or 'none')))}",
        f"Primary metric: {escape(_single_line(str(metric.get('name') or '')))} "
        f"({escape(_single_line(str(metric.get('direction') or '')))})",
        f"Measured variants: {int(summary.get('measured_variants') or 0)}/{int(summary.get('variant_count') or 0)}",
        f"Evidence sources: {int(summary.get('evidence_sources') or 0)}",
        "",
        "## Ranking",
        "",
        "| Rank | Variant | Provider | Model | Score | Metric count | Mean | Success | Avg cost USD | Compare | Suite | Arena | Judge | Schedule | Decision | Route wins | Next share | Reasons |",
        "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- | ---: | ---: | --- |",
    ]
    for item in rows:
        if not isinstance(item, dict):
            continue
        evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
        comparison = evidence.get("comparison") if isinstance(evidence.get("comparison"), dict) else {}
        suite = evidence.get("suite") if isinstance(evidence.get("suite"), dict) else {}
        arena = evidence.get("arena") if isinstance(evidence.get("arena"), dict) else {}
        judge = evidence.get("judge") if isinstance(evidence.get("judge"), dict) else {}
        schedule = evidence.get("schedule") if isinstance(evidence.get("schedule"), dict) else {}
        decision = evidence.get("decision") if isinstance(evidence.get("decision"), dict) else {}
        route = evidence.get("route") if isinstance(evidence.get("route"), dict) else {}
        allocation = evidence.get("allocation") if isinstance(evidence.get("allocation"), dict) else {}
        usage = item.get("usage") if isinstance(item.get("usage"), dict) else {}
        reasons = item.get("reasons") if isinstance(item.get("reasons"), list) else []
        lines.append(
            "| "
            f"{int(item.get('rank') or 0)} | "
            f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('provider') or '')))} | "
            f"{escape(_single_line(str(item.get('model') or '')))} | "
            f"{_table_number(item.get('evidence_score'))} | "
            f"{int(item.get('primary_metric_count') or 0)} | "
            f"{_table_number(item.get('primary_metric_mean'))} | "
            f"{_table_number(item.get('success_rate'))} | "
            f"{_table_number(usage.get('cost_usd_mean') if isinstance(usage, dict) else None)} | "
            f"{escape(_single_line(str(comparison.get('status') or '')))} | "
            f"{escape(_single_line(str(suite.get('status') or '')))} | "
            f"{escape(_single_line(str(arena.get('status') or '')))} | "
            f"{escape(_single_line(str(judge.get('status') or '')))} | "
            f"{escape(_single_line(str(schedule.get('status') or '')))} | "
            f"{escape(_single_line(str(decision.get('decision') or decision.get('status') or '')))} | "
            f"{int(route.get('lane_wins') or 0)} | "
            f"{_table_number(allocation.get('recommended_share'))} | "
            f"{escape(_single_line(', '.join(str(reason) for reason in reasons)))} |"
        )
    lines.extend(["", "## Source Artifacts", ""])
    if sources:
        lines.extend(["| Source | Artifact | Status | Winner |", "| --- | --- | --- | --- |"])
        for name, raw_ref in sorted(sources.items()):
            if not isinstance(raw_ref, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(name)))} | "
                f"{escape(_single_line(str(raw_ref.get('artifact_id') or '')))} | "
                f"{escape(_single_line(str(raw_ref.get('status') or '')))} | "
                f"{escape(_single_line(str(raw_ref.get('winner_variant_id') or '')))} |"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_config_proposal_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    source = payload["source"] if isinstance(payload.get("source"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    patch = payload["patch"] if isinstance(payload.get("patch"), dict) else {}
    operations = patch.get("operations") if isinstance(patch.get("operations"), list) else []
    changed = summary.get("changed_variant_weights") if isinstance(summary.get("changed_variant_weights"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Config Proposal ' + str(payload['config_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Config Proposal",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload['config_status'])))}",
        f"Source: {escape(_single_line(str(source.get('selected') or source.get('requested') or '')))}",
        f"Reason: {escape(_single_line(str(source.get('reason') or '')))}",
        f"Config file: {escape(_single_line(str(payload.get('config_path') or '')))}",
        f"Patch operations: {int(summary.get('operation_count') or 0)}",
        f"Changed weights: {int(summary.get('changed_weight_count') or 0)}",
        f"Traffic salt changed: {str(bool(summary.get('traffic_salt_changed'))).lower()}",
        "",
        "## Variant Weights",
        "",
        "| Variant | Current | Proposed |",
        "| --- | ---: | ---: |",
    ]
    for item in changed:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
            f"{_table_number(item.get('current_weight'))} | "
            f"{_table_number(item.get('proposed_weight'))} |"
        )
    if not changed:
        lines.append("| none |  |  |")
    lines.extend(["", "## Patch", ""])
    if operations:
        for item in operations:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- `{escape(_single_line(str(item.get('op') or '')))} "
                f"{escape(_single_line(str(item.get('path') or '')))}"
                "`"
            )
    else:
        lines.append("- No patch operations.")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_promotion_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    primary_metric = payload["primary_metric"]
    evidence = payload["evidence"]
    confidence = evidence.get("confidence") if isinstance(evidence, dict) else {}
    latest_budget = evidence.get("latest_budget") if isinstance(evidence, dict) else None
    latest_balance = evidence.get("latest_balance") if isinstance(evidence, dict) else None
    latest_drift = evidence.get("latest_drift") if isinstance(evidence, dict) else None
    summaries = payload["variant_summaries"]
    patch = payload["patch"]
    operations = patch.get("operations") if isinstance(patch, dict) else []
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Promotion ' + str(payload['promotion_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Promotion",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Status: {escape(_single_line(str(payload['promotion_status'])))}",
        f"Ready: {str(bool(payload.get('ready'))).lower()}",
        f"Champion: {escape(_single_line(str(payload['champion_variant_id'])))}",
        f"Candidate: {escape(_single_line(str(payload.get('candidate_variant_id') or 'none')))}",
        f"Primary metric: {escape(_single_line(str(primary_metric['name'])))} "
        f"({escape(_single_line(str(primary_metric['direction'])))})",
        f"Metric gap: {_table_number(evidence.get('metric_gap') if isinstance(evidence, dict) else None)}",
        f"Confidence: {escape(_single_line(str(confidence.get('label') if isinstance(confidence, dict) else 'unknown')))}",
        f"Latest budget: {escape(_single_line(str(latest_budget.get('budget_status') if isinstance(latest_budget, dict) else 'none')))}",
        f"Latest balance: {escape(_single_line(str(latest_balance.get('balance_status') if isinstance(latest_balance, dict) else 'none')))}",
        f"Latest drift: {escape(_single_line(str(latest_drift.get('drift_status') if isinstance(latest_drift, dict) else 'none')))}",
        "",
        "## Variant Evidence",
        "",
        "| Variant | Provider | Model | Metric count | Mean | Std err | Success rate |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    if isinstance(summaries, list):
        for item in summaries:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('variant_id', ''))))} | "
                f"{escape(_single_line(str(item.get('provider', ''))))} | "
                f"{escape(_single_line(str(item.get('model', ''))))} | "
                f"{int(item.get('primary_metric_count') or 0)} | "
                f"{_table_number(item.get('primary_metric_mean'))} | "
                f"{_table_number(item.get('primary_metric_stderr'))} | "
                f"{_table_number(item.get('success_rate'))} |"
            )
    lines.extend(["", "## Proposed Patch", ""])
    if isinstance(operations, list) and operations:
        lines.extend(
            f"- `{escape(_single_line(str(item.get('op', ''))))}` "
            f"`{escape(_single_line(str(item.get('path', ''))))}` = "
            f"`{escape(_single_line(str(item.get('value', ''))))}`"
            for item in operations
            if isinstance(item, dict)
        )
    else:
        lines.append("- No config patch proposed.")
    lines.extend(["", "## Recommendations", ""])
    recommendations = payload.get("recommendations")
    if isinstance(recommendations, list):
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    lines.append("")
    return "\n".join(lines)


def _render_improvement_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    primary_metric = payload["primary_metric"]
    summaries = payload["variant_summaries"]
    recommendations = payload["recommendations"]
    winner = payload.get("winner_variant_id") or "none"
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Improvement ' + str(payload['loop_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Improvement",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Primary metric: {escape(_single_line(str(primary_metric['name'])))} "
        f"({escape(_single_line(str(primary_metric['direction'])))})",
        f"Winner: {escape(_single_line(str(winner)))}",
        "",
        "## Variant Summary",
        "",
        "| Variant | Provider | Model | Trials | Success rate | Metric mean |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    if isinstance(summaries, list):
        for item in summaries:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('variant_id', ''))))} | "
                f"{escape(_single_line(str(item.get('provider', ''))))} | "
                f"{escape(_single_line(str(item.get('model', ''))))} | "
                f"{int(item.get('trials') or 0)} | "
                f"{_table_number(item.get('success_rate'))} | "
                f"{_table_number(item.get('primary_metric_mean'))} |"
            )
    lines.extend(["", "## Recommendations", ""])
    if isinstance(recommendations, list):
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    lines.append("")
    return "\n".join(lines)


def _render_memory_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    lessons = payload["lessons"] if isinstance(payload.get("lessons"), list) else []
    failure_modes = payload["failure_modes"] if isinstance(payload.get("failure_modes"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Memory ' + str(payload['memory_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Memory",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Outcomes: {int(summary.get('outcome_count') or 0)}",
        f"Failed outcomes: {int(summary.get('failed_outcomes') or 0)}",
        f"Lessons: {int(summary.get('lesson_count') or 0)}",
        "",
        "## Lessons",
        "",
        "| Priority | Category | Code | Recommendation |",
        "| --- | --- | --- | --- |",
    ]
    for item in lessons:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('priority') or '')))} | "
            f"{escape(_single_line(str(item.get('category') or '')))} | "
            f"{escape(_single_line(str(item.get('code') or '')))} | "
            f"{escape(_single_line(str(item.get('recommendation') or '')))} |"
        )
    lines.extend(["", "## Failure Modes", ""])
    if failure_modes:
        lines.extend(["| Code | Variant | Count |", "| --- | --- | ---: |"])
        for item in failure_modes:
            if not isinstance(item, Mapping):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('failure_code') or '')))} | "
                f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
                f"{int(item.get('count') or 0)} |"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_curriculum_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    metric = payload["primary_metric"] if isinstance(payload.get("primary_metric"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    hard_cases = payload["hard_cases"] if isinstance(payload.get("hard_cases"), list) else []
    weak_variants = payload["weak_variants"] if isinstance(payload.get("weak_variants"), list) else []
    weak_lanes = payload["weak_lanes"] if isinstance(payload.get("weak_lanes"), list) else []
    next_wave = payload["next_wave"] if isinstance(payload.get("next_wave"), dict) else {}
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Curriculum ' + str(payload['curriculum_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Curriculum",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload['curriculum_status'])))}",
        f"Primary metric: {escape(_single_line(str(metric.get('name') or '')))} "
        f"({escape(_single_line(str(metric.get('direction') or '')))})",
        f"Outcomes: {int(summary.get('outcome_count') or 0)}",
        f"Hard cases: {int(summary.get('hard_case_count') or 0)}",
        f"Failed cases: {int(summary.get('failed_case_count') or 0)}",
        f"Weak metric cases: {int(summary.get('weak_metric_case_count') or 0)}",
        f"Metric threshold: {_table_number(summary.get('metric_threshold'))} "
        f"({escape(_single_line(str(summary.get('metric_threshold_source') or '')))})",
        "",
        "## Hard Cases",
        "",
        "| Rank | Priority | Reasons | Variant | Lane | Case | Status | Metric | Threshold | Failure | Run |",
        "| ---: | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for item in hard_cases:
        if not isinstance(item, dict):
            continue
        reasons = item.get("reasons") if isinstance(item.get("reasons"), list) else []
        lines.append(
            "| "
            f"{int(item.get('rank') or 0)} | "
            f"{escape(_single_line(str(item.get('priority') or '')))} | "
            f"{escape(_single_line(', '.join(str(reason) for reason in reasons)))} | "
            f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
            f"{escape(_single_line(str(item.get('lane_id') or '')))} | "
            f"{escape(_single_line(str(item.get('case_id') or item.get('case_hash') or '')))} | "
            f"{escape(_single_line(str(item.get('status') or '')))} | "
            f"{_table_number(item.get('metric_value'))} | "
            f"{_table_number(item.get('metric_threshold'))} | "
            f"{escape(_single_line(str(item.get('failure_code') or '')))} | "
            f"{escape(_single_line(str(item.get('run_id') or '')))} |"
        )
    if not hard_cases:
        lines.append("| 0 | none |  |  |  |  |  |  |  |  |  |")
    lines.extend(["", "## Weak Variants", ""])
    if weak_variants:
        lines.extend(
            [
                "| Variant | Provider | Model | Hard cases | Failed | Weak metric | Missing metric | Mean | Focus lanes |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
        for item in weak_variants:
            if not isinstance(item, dict):
                continue
            lanes = item.get("focus_lanes") if isinstance(item.get("focus_lanes"), list) else []
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
                f"{escape(_single_line(str(item.get('provider') or '')))} | "
                f"{escape(_single_line(str(item.get('model') or '')))} | "
                f"{int(item.get('hard_case_count') or 0)} | "
                f"{int(item.get('failed_count') or 0)} | "
                f"{int(item.get('weak_metric_count') or 0)} | "
                f"{int(item.get('missing_metric_count') or 0)} | "
                f"{_table_number(item.get('primary_metric_mean'))} | "
                f"{escape(_single_line(', '.join(str(lane) for lane in lanes)))} |"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Weak Lanes", ""])
    if weak_lanes:
        lines.extend(["| Lane | Role | Hard cases | Failed | Variants | Cases |", "| --- | --- | ---: | ---: | --- | --- |"])
        for item in weak_lanes:
            if not isinstance(item, dict):
                continue
            variants = item.get("variant_ids") if isinstance(item.get("variant_ids"), list) else []
            case_ids = item.get("case_ids") if isinstance(item.get("case_ids"), list) else []
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('lane_id') or '')))} | "
                f"{escape(_single_line(str(item.get('role') or '')))} | "
                f"{int(item.get('hard_case_count') or 0)} | "
                f"{int(item.get('failed_count') or 0)} | "
                f"{escape(_single_line(', '.join(str(variant) for variant in variants)))} | "
                f"{escape(_single_line(', '.join(str(case_id) for case_id in case_ids)))} |"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Next Wave", ""])
    lines.append(f"- Mode: {escape(_single_line(str(next_wave.get('mode') or '')))}")
    lines.append(
        "- Focus variants: "
        + escape(_single_line(", ".join(str(item) for item in next_wave.get("focus_variants", []) if item) or "none"))
    )
    lines.append(
        "- Focus lanes: "
        + escape(_single_line(", ".join(str(item) for item in next_wave.get("focus_lanes", []) if item) or "none"))
    )
    lines.append(f"- Recommended cases: {int(next_wave.get('recommended_case_count') or 0)}")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_allocation_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    primary_metric = payload["primary_metric"]
    policy = payload["policy"]
    summary = payload["summary"]
    allocations = payload["allocations"]
    recommendations = payload["recommendations"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Allocation ' + str(payload['allocation_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Allocation",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Strategy: {escape(_single_line(str(payload['strategy'])))}",
        f"Primary metric: {escape(_single_line(str(primary_metric['name'])))} "
        f"({escape(_single_line(str(primary_metric['direction'])))})",
        f"Winner: {escape(_single_line(str(payload.get('winner_variant_id') or 'none')))}",
        f"Measured variants: {int(summary['measured_variants'])}/{int(summary['variant_count'])}",
        f"Under-sampled variants: {int(summary['under_sampled_variants'])}",
        f"Exploration floor: {_table_number(policy.get('exploration_floor'))}",
        f"Max share: {_table_number(policy.get('max_share'))}",
        "",
        "## Allocation",
        "",
        "| Variant | Provider | Model | Samples | Mean | Reward | Bonus | Score | Current share | Next share | Reason |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    if isinstance(allocations, list):
        for item in allocations:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('variant_id', ''))))} | "
                f"{escape(_single_line(str(item.get('provider', ''))))} | "
                f"{escape(_single_line(str(item.get('model', ''))))} | "
                f"{int(item.get('primary_metric_count') or 0)} | "
                f"{_table_number(item.get('primary_metric_mean'))} | "
                f"{_table_number(item.get('reward_score'))} | "
                f"{_table_number(item.get('exploration_bonus'))} | "
                f"{_table_number(item.get('allocation_score'))} | "
                f"{_table_number(item.get('current_share'))} | "
                f"{_table_number(item.get('recommended_share'))} | "
                f"{escape(_single_line(str(item.get('reason', ''))))} |"
            )
    lines.extend(["", "## Recommendations", ""])
    if isinstance(recommendations, list):
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    lines.append("")
    return "\n".join(lines)


def _render_route_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    primary_metric = payload["primary_metric"]
    policy = payload["policy"]
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    lane_policies = payload["lane_policies"] if isinstance(payload.get("lane_policies"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Route ' + str(payload['route_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Route",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Primary metric: {escape(_single_line(str(primary_metric['name'])))} "
        f"({escape(_single_line(str(primary_metric['direction'])))})",
        f"Strategy: {escape(_single_line(str(policy['strategy'])))}",
        f"Lanes: {int(summary.get('measured_lanes') or 0)}/{int(summary.get('lane_count') or 0)}",
        f"Recommended routes: {int(summary.get('recommended_routes') or 0)}",
        "",
        "## Lane Policies",
        "",
        "| Lane | Role | Outcomes | Winner | Under-sampled variants |",
        "| --- | --- | ---: | --- | ---: |",
    ]
    for lane in lane_policies:
        if not isinstance(lane, Mapping):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(lane.get('lane_id') or '')))} | "
            f"{escape(_single_line(str(lane.get('role') or '')))} | "
            f"{int(lane.get('outcome_count') or 0)} | "
            f"{escape(_single_line(str(lane.get('winner_variant_id') or 'none')))} | "
            f"{int(lane.get('under_sampled_variants') or 0)} |"
        )
    lines.extend(["", "## Shares", ""])
    for lane in lane_policies:
        if not isinstance(lane, Mapping):
            continue
        allocations = lane.get("allocations") if isinstance(lane.get("allocations"), list) else []
        lines.extend(
            [
                f"### {escape(_single_line(str(lane.get('lane_id') or 'lane')))}",
                "",
                "| Variant | Provider | Model | Samples | Mean | Share | Reason |",
                "| --- | --- | --- | ---: | ---: | ---: | --- |",
            ]
        )
        for item in allocations:
            if not isinstance(item, Mapping):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
                f"{escape(_single_line(str(item.get('provider') or '')))} | "
                f"{escape(_single_line(str(item.get('model') or '')))} | "
                f"{int(item.get('primary_metric_count') or 0)} | "
                f"{_table_number(item.get('primary_metric_mean'))} | "
                f"{_table_number(item.get('recommended_share'))} | "
                f"{escape(_single_line(str(item.get('reason') or '')))} |"
            )
        lines.append("")
    lines.extend(["## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_plan_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    parallel = payload["parallel"]
    runs = payload["runs"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Plan ' + str(payload['plan_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Plan",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Plan: {escape(_single_line(str(payload['plan_id'])))}",
        f"Runs: {int(parallel['run_count'])}",
        f"Merge strategy: {escape(_single_line(str(parallel['merge_strategy'])))}",
        "",
        "## Parallel Runs",
        "",
        "| Lane | Role | Replica | Variant | Run |",
        "| --- | --- | ---: | --- | --- |",
    ]
    if isinstance(runs, list):
        for item in runs:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('lane_id', ''))))} | "
                f"{escape(_single_line(str(item.get('role', ''))))} | "
                f"{int(item.get('replica') or 0)} | "
                f"{escape(_single_line(str(item.get('variant_id', ''))))} | "
                f"{escape(_single_line(str(item.get('run_id', ''))))} |"
            )
    lines.append("")
    return "\n".join(lines)


def _render_merge_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    metric = payload["primary_metric"]
    lanes = payload["lane_summaries"]
    recommended = payload.get("recommended_run_id") or "none"
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Merge ' + str(payload['merge_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Merge",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Plan: {escape(_single_line(str(payload['plan_id'])))}",
        f"Status: {escape(_single_line(str(payload['merge_status'])))}",
        f"Completed runs: {int(payload['completed_runs'])}/{int(payload['expected_runs'])}",
        f"Primary metric: {escape(_single_line(str(metric['name'])))} "
        f"({escape(_single_line(str(metric['direction'])))})",
        f"Recommended run: {escape(_single_line(str(recommended)))}",
        "",
        "## Lane Summary",
        "",
        "| Lane | Role | Complete | Success rate | Best run | Best variant | Best metric |",
        "| --- | --- | ---: | ---: | --- | --- | ---: |",
    ]
    if isinstance(lanes, list):
        for item in lanes:
            if not isinstance(item, dict):
                continue
            complete = f"{int(item.get('completed_runs') or 0)}/{int(item.get('expected_runs') or 0)}"
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('lane_id', ''))))} | "
                f"{escape(_single_line(str(item.get('role', ''))))} | "
                f"{complete} | "
                f"{_table_number(item.get('success_rate'))} | "
                f"{escape(_single_line(str(item.get('best_run_id') or '')))} | "
                f"{escape(_single_line(str(item.get('best_variant_id') or '')))} | "
                f"{_table_number(item.get('best_metric'))} |"
            )
    lines.append("")
    return "\n".join(lines)


def _render_status_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"]
    experiments = payload["experiments"]
    recommendations = payload["recommendations"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Status ' + str(payload['status_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Status",
        "",
        f"Experiments: {int(summary['experiments'])}",
        f"Runs: {int(summary['runs'])}",
        f"Plans: {int(summary['plans'])}",
        f"Suites: {int(summary['suites'])}",
        f"Suite reports: {int(summary['suite_reports'])}",
        f"Arenas: {int(summary['arenas'])}",
        f"Arena reports: {int(summary['arena_reports'])}",
        f"Judge panels: {int(summary['judge_panels'])}",
        f"Judge reports: {int(summary['judge_reports'])}",
        f"Pipelines: {int(summary['pipelines'])}",
        f"Pipeline advances: {int(summary['pipeline_advances'])}",
        f"Outcomes: {int(summary['outcomes'])}",
        f"Claims: {int(summary['claims'])}",
        f"Dispatches: {int(summary['dispatches'])}",
        f"Holds: {int(summary.get('holds') or 0)}",
        f"Active holds: {int(summary.get('active_holds') or 0)}",
        f"Quarantines: {int(summary.get('quarantines') or 0)}",
        f"Active quarantines: {int(summary.get('active_quarantines') or 0)}",
        f"Circuits: {int(summary.get('circuits') or 0)}",
        f"Heartbeats: {int(summary['heartbeats'])}",
        f"Retries: {int(summary['retries'])}",
        f"Gates: {int(summary['gates'])}",
        f"Failed gates: {int(summary['failed_gates'])}",
        f"Quorums: {int(summary['quorums'])}",
        f"Allocations: {int(summary['allocations'])}",
        f"Routes: {int(summary['routes'])}",
        f"Readiness: {int(summary['readiness'])}",
        f"Rollouts: {int(summary['rollouts'])}",
        f"Rollout checks: {int(summary['rollout_checks'])}",
        f"Evolutions: {int(summary['evolutions'])}",
        f"Power reports: {int(summary['power_reports'])}",
        f"Schedules: {int(summary['schedules'])}",
        f"Schedule reports: {int(summary['schedule_reports'])}",
        f"Leaderboards: {int(summary['leaderboards'])}",
        f"Config proposals: {int(summary['config_proposals'])}",
        f"Mix reports: {int(summary.get('mix_reports') or 0)}",
        f"Snapshots: {int(summary.get('snapshots') or 0)}",
        f"Promotions: {int(summary['promotions'])}",
        f"Comparisons: {int(summary['comparisons'])}",
        f"Decisions: {int(summary['decisions'])}",
        f"Memories: {int(summary['memories'])}",
        f"Curricula: {int(summary['curricula'])}",
        f"Budget reports: {int(summary['budget_reports'])}",
        f"Capacity reports: {int(summary['capacity_reports'])}",
        f"SLO reports: {int(summary['slo_reports'])}",
        f"Dashboard reports: {int(summary['dashboard_reports'])}",
        f"Ingest reports: {int(summary['ingest_reports'])}",
        f"Orchestration reports: {int(summary['orchestration_reports'])}",
        f"Recovery reports: {int(summary['recovery_reports'])}",
        f"Cycle reports: {int(summary['cycle_reports'])}",
        f"Loop reports: {int(summary['loop_reports'])}",
        f"Scorecards: {int(summary['scorecards'])}",
        f"Work packets: {int(summary['work_packets'])}",
        f"Adjudications: {int(summary['adjudications'])}",
        f"Accepted adjudications: {int(summary['accepted_adjudications'])}",
        f"Pending plan runs: {int(summary['pending_plan_runs'])}",
        f"Claimed plan runs: {int(summary['claimed_plan_runs'])}",
        f"Expired claims: {int(summary['expired_claims'])}",
        f"Failed outcomes: {int(summary['failed_outcomes'])}",
        "",
        "## Experiments",
        "",
        "| Experiment | Runs | Plans | Suites | Suite reports | Arenas | Arena reports | Judge panels | Judge reports | Pipelines | Pipeline advances | Budget reports | Dashboard reports | Orchestrations | Outcomes | Scorecards | Work packets | Claims | Dispatches | Heartbeats | Retries | Gates | Quorums | Adjudications | Allocations | Routes | Readiness | Rollouts | Rollout checks | Evolutions | Power | Schedules | Schedule reports | Leaderboards | Config proposals | Mix reports | Snapshots | Promotions | Comparisons | Decisions | Memories | Curricula | Queued | Claimed | Expired | Failed | Latest merge | Latest gate | Latest adjudication | Latest allocation | Latest readiness | Latest rollout | Latest rollout check | Latest evolve | Latest power | Latest arena | Latest arena report | Latest judge | Latest judge report | Latest pipeline | Latest pipeline advance | Latest schedule | Latest schedule report | Latest leaderboard | Latest config | Latest mix | Latest snapshot | Latest promotion | Latest comparison | Latest decision | Latest curriculum |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    if isinstance(experiments, list):
        for item in experiments:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('experiment', ''))))} | "
                f"{int(item.get('run_count') or 0)} | "
                f"{int(item.get('plan_count') or 0)} | "
                f"{int(item.get('suite_count') or 0)} | "
                f"{int(item.get('suite_report_count') or 0)} | "
                f"{int(item.get('arena_count') or 0)} | "
                f"{int(item.get('arena_report_count') or 0)} | "
                f"{int(item.get('judge_panel_count') or 0)} | "
                f"{int(item.get('judge_report_count') or 0)} | "
                f"{int(item.get('pipeline_count') or 0)} | "
                f"{int(item.get('pipeline_advance_count') or 0)} | "
                f"{int(item.get('budget_report_count') or 0)} | "
                f"{int(item.get('dashboard_report_count') or 0)} | "
                f"{int(item.get('orchestration_report_count') or 0)} | "
                f"{int(item.get('outcome_count') or 0)} | "
                f"{int(item.get('scorecard_count') or 0)} | "
                f"{int(item.get('work_packet_count') or 0)} | "
                f"{int(item.get('claim_count') or 0)} | "
                f"{int(item.get('dispatch_count') or 0)} | "
                f"{int(item.get('heartbeat_count') or 0)} | "
                f"{int(item.get('retry_count') or 0)} | "
                f"{int(item.get('gate_count') or 0)} | "
                f"{int(item.get('quorum_count') or 0)} | "
                f"{int(item.get('adjudication_count') or 0)} | "
                f"{int(item.get('allocation_count') or 0)} | "
                f"{int(item.get('route_count') or 0)} | "
                f"{int(item.get('readiness_count') or 0)} | "
                f"{int(item.get('rollout_count') or 0)} | "
                f"{int(item.get('rollout_check_count') or 0)} | "
                f"{int(item.get('evolution_count') or 0)} | "
                f"{int(item.get('power_count') or 0)} | "
                f"{int(item.get('schedule_count') or 0)} | "
                f"{int(item.get('schedule_report_count') or 0)} | "
                f"{int(item.get('leaderboard_count') or 0)} | "
                f"{int(item.get('config_proposal_count') or 0)} | "
                f"{int(item.get('mix_count') or 0)} | "
                f"{int(item.get('snapshot_count') or 0)} | "
                f"{int(item.get('promotion_count') or 0)} | "
                f"{int(item.get('comparison_count') or 0)} | "
                f"{int(item.get('decision_count') or 0)} | "
                f"{int(item.get('memory_count') or 0)} | "
                f"{int(item.get('curriculum_count') or 0)} | "
                f"{int(item.get('pending_plan_runs') or 0)} | "
                f"{int(item.get('claimed_plan_runs') or 0)} | "
                f"{int(item.get('expired_claims') or 0)} | "
                f"{int(item.get('failed_outcomes') or 0)} | "
                f"{escape(_single_line(str(item.get('latest_merge_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_gate_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_adjudication_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_allocation_winner') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_readiness_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_rollout_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_rollout_check_decision') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_evolve_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_power_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_arena_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_arena_winner') or item.get('latest_arena_report_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_judge_panel_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_judge_winner') or item.get('latest_judge_report_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_pipeline_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_pipeline_advance_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_schedule_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_schedule_report_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_leaderboard_winner') or item.get('latest_leaderboard_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_config_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_mix_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_snapshot_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_promotion_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_comparison_winner') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_decision') or item.get('latest_decision_status') or '')))} | "
                f"{escape(_single_line(str(item.get('latest_curriculum_status') or '')))} |"
            )
    lines.extend(["", "## Recommendations", ""])
    if isinstance(recommendations, list):
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    lines.append("")
    return "\n".join(lines)


def _render_suite_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    suite = payload["suite"]
    curriculum = payload.get("curriculum") if isinstance(payload.get("curriculum"), Mapping) else {}
    cases = payload["cases"]
    plans = payload["plans"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Suite ' + str(payload['suite_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Suite",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Suite: {escape(_single_line(str(suite['name'])))}",
        f"Mode: {escape(_single_line(str(suite['mode'])))}",
        f"Cases: {int(payload['case_count'])}",
        f"Plans: {int(payload['plan_count'])}",
        f"Runs: {int(payload['run_count'])}",
        f"Runs per case: {int(payload['runs_per_case'])}",
        f"Curriculum: {escape(_single_line(str(curriculum.get('curriculum_id') or 'none')))}",
        "",
        "## Cases",
        "",
        "| Case | Tags | Prompt chars | Plan | Runs |",
        "| --- | --- | ---: | --- | ---: |",
    ]
    if isinstance(cases, list):
        for item in cases:
            if not isinstance(item, dict):
                continue
            prompt = item.get("prompt") if isinstance(item.get("prompt"), dict) else {}
            tags = item.get("tags") if isinstance(item.get("tags"), list) else []
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('case_id', ''))))} | "
                f"{escape(_single_line(', '.join(str(tag) for tag in tags)))} | "
                f"{int(prompt.get('chars') or 0)} | "
                f"{escape(_single_line(str(item.get('plan_id', ''))))} | "
                f"{int(item.get('run_count') or 0)} |"
            )
    lines.extend(["", "## Plans", ""])
    if isinstance(plans, list):
        for item in plans:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- {escape(_single_line(str(item.get('case_id', ''))))}: "
                f"{escape(_single_line(str(item.get('plan_id', ''))))} "
                f"({int(item.get('run_count') or 0)} run(s))"
            )
    lines.append("")
    return "\n".join(lines)


def _render_suite_report_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    suite = payload["suite"]
    metric = payload["primary_metric"]
    summary = payload["summary"]
    variants = payload["variant_summaries"]
    cases = payload["case_summaries"]
    pairwise = payload["pairwise"]
    frontier = payload.get("efficiency_frontier")
    recommendations = payload["recommendations"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Suite Report ' + str(payload['report_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Suite Report",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Suite: {escape(_single_line(str(suite.get('name') or suite.get('slug') or payload['suite_id'])))}",
        f"Baseline: {escape(_single_line(str(payload['baseline_variant_id'])))}",
        f"Winner: {escape(_single_line(str(payload.get('winner_variant_id') or 'none')))}",
        f"Primary metric: {escape(_single_line(str(metric['name'])))} "
        f"({escape(_single_line(str(metric['direction'])))})",
        f"Completed runs: {int(summary['completed_runs'])}/{int(summary['expected_runs'])}",
        f"Complete cases: {int(summary['complete_cases'])}/{int(summary['case_count'])}",
        "",
        "## Variant Summary",
        "",
        "| Variant | Cases | Mean | Std err | Wins | Outcomes | Avg tokens | Avg latency ms | Avg cost USD |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    if isinstance(variants, list):
        for item in variants:
            if not isinstance(item, dict):
                continue
            usage = item.get("usage") if isinstance(item.get("usage"), dict) else {}
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('variant_id', ''))))} | "
                f"{int(item.get('measured_cases') or 0)} | "
                f"{_table_number(item.get('case_metric_mean'))} | "
                f"{_table_number(item.get('case_metric_stderr'))} | "
                f"{int(item.get('case_wins') or 0)} | "
                f"{int(item.get('outcome_count') or 0)} | "
                f"{_table_number(usage.get('total_tokens_mean'))} | "
                f"{_table_number(usage.get('latency_ms_mean'))} | "
                f"{_table_number(usage.get('cost_usd_mean'))} |"
            )
    lines.extend(
        [
            "",
            "## Efficiency Frontier",
            "",
            "| Variant | Metric | Avg tokens | Avg latency ms | Avg cost USD | Metric / USD | Metric / 1k tokens |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    if isinstance(frontier, list):
        for item in frontier:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('variant_id', ''))))} | "
                f"{_table_number(item.get('metric'))} | "
                f"{_table_number(item.get('total_tokens_mean'))} | "
                f"{_table_number(item.get('latency_ms_mean'))} | "
                f"{_table_number(item.get('cost_usd_mean'))} | "
                f"{_table_number(item.get('metric_per_usd'))} | "
                f"{_table_number(item.get('metric_per_1k_tokens'))} |"
            )
    lines.extend(
        [
            "",
            "## Paired Baseline Comparisons",
            "",
            "| Candidate | Status | Paired cases | Mean delta | CI low | CI high | Wins | Losses | Confidence |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    if isinstance(pairwise, list):
        for item in pairwise:
            if not isinstance(item, dict):
                continue
            ci = item.get("delta_ci95") if isinstance(item.get("delta_ci95"), dict) else {}
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('candidate_variant_id', ''))))} | "
                f"{escape(_single_line(str(item.get('status', ''))))} | "
                f"{int(item.get('paired_cases') or 0)} | "
                f"{_table_number(item.get('mean_directional_delta'))} | "
                f"{_table_number(ci.get('low'))} | "
                f"{_table_number(ci.get('high'))} | "
                f"{int(item.get('wins') or 0)} | "
                f"{int(item.get('losses') or 0)} | "
                f"{escape(_single_line(str(item.get('confidence', ''))))} |"
            )
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Case | Status | Complete | Best variant | Best metric | Missing variants |",
            "| --- | --- | ---: | --- | ---: | --- |",
        ]
    )
    if isinstance(cases, list):
        for item in cases:
            if not isinstance(item, dict):
                continue
            complete = f"{int(item.get('completed_runs') or 0)}/{int(item.get('expected_runs') or 0)}"
            missing = item.get("missing_variants") if isinstance(item.get("missing_variants"), list) else []
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('case_id', ''))))} | "
                f"{escape(_single_line(str(item.get('status', ''))))} | "
                f"{complete} | "
                f"{escape(_single_line(str(item.get('best_variant_id') or '')))} | "
                f"{_table_number(item.get('best_metric'))} | "
                f"{escape(_single_line(', '.join(str(value) for value in missing)))} |"
            )
    lines.extend(["", "## Recommendations", ""])
    if isinstance(recommendations, list):
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    lines.append("")
    return "\n".join(lines)


def _render_audit_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"]
    experiments = payload["experiments"]
    findings = payload["findings"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Audit ' + str(payload['audit_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Audit",
        "",
        f"Experiments: {int(summary['experiments'])}",
        f"Pass: {int(summary['pass'])}",
        f"Warn: {int(summary['warn'])}",
        f"Fail: {int(summary['fail'])}",
        "",
        "## Experiment Counts",
        "",
        "| Experiment | Runs | Plans | Suites | Suite reports | Arenas | Arena reports | Judge panels | Judge reports | Pipelines | Pipeline advances | Outcomes | Claims | Dispatches | Heartbeats | Retries | Scorecards | Work packets | Merges | Gates | Adjudications | Allocations | Routes | Readiness | Rollouts | Rollout checks | Evolutions | Power | Schedules | Schedule reports | Leaderboards | Config proposals | Mix reports | Snapshots | Promotions | Comparisons | Decisions | Curricula |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    if isinstance(experiments, list):
        for item in experiments:
            if not isinstance(item, dict):
                continue
            counts = item.get("counts") if isinstance(item.get("counts"), dict) else {}
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('experiment', ''))))} | "
                f"{int(counts.get('runs') or 0)} | "
                f"{int(counts.get('plans') or 0)} | "
                f"{int(counts.get('suites') or 0)} | "
                f"{int(counts.get('suite_reports') or 0)} | "
                f"{int(counts.get('arenas') or 0)} | "
                f"{int(counts.get('arena_reports') or 0)} | "
                f"{int(counts.get('judge_panels') or 0)} | "
                f"{int(counts.get('judge_reports') or 0)} | "
                f"{int(counts.get('pipelines') or 0)} | "
                f"{int(counts.get('pipeline_advances') or 0)} | "
                f"{int(counts.get('outcomes') or 0)} | "
                f"{int(counts.get('claims') or 0)} | "
                f"{int(counts.get('dispatches') or 0)} | "
                f"{int(counts.get('heartbeats') or 0)} | "
                f"{int(counts.get('retries') or 0)} | "
                f"{int(counts.get('scorecards') or 0)} | "
                f"{int(counts.get('work_packets') or 0)} | "
                f"{int(counts.get('merges') or 0)} | "
                f"{int(counts.get('gates') or 0)} | "
                f"{int(counts.get('adjudications') or 0)} | "
                f"{int(counts.get('allocations') or 0)} | "
                f"{int(counts.get('routes') or 0)} | "
                f"{int(counts.get('readiness') or 0)} | "
                f"{int(counts.get('rollouts') or 0)} | "
                f"{int(counts.get('rollout_checks') or 0)} | "
                f"{int(counts.get('evolutions') or 0)} | "
                f"{int(counts.get('power') or 0)} | "
                f"{int(counts.get('schedules') or 0)} | "
                f"{int(counts.get('schedule_reports') or 0)} | "
                f"{int(counts.get('leaderboards') or 0)} | "
                f"{int(counts.get('config_proposals') or 0)} | "
                f"{int(counts.get('mix') or 0)} | "
                f"{int(counts.get('snapshots') or 0)} | "
                f"{int(counts.get('promotions') or 0)} | "
                f"{int(counts.get('comparisons') or 0)} | "
                f"{int(counts.get('decisions') or 0)} | "
                f"{int(counts.get('curricula') or 0)} |"
            )
    lines.extend(["", "## Findings", ""])
    if isinstance(findings, list):
        for item in findings:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('experiment', ''))))} "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))}"
            )
    lines.append("")
    return "\n".join(lines)


def _render_manifest_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"] if isinstance(payload.get("summary"), Mapping) else {}
    scope = payload["scope"] if isinstance(payload.get("scope"), Mapping) else {}
    artifacts = payload["artifacts"] if isinstance(payload.get("artifacts"), list) else []
    schema_counts = summary.get("schema_counts") if isinstance(summary.get("schema_counts"), Mapping) else {}
    type_counts = (
        summary.get("artifact_type_counts")
        if isinstance(summary.get("artifact_type_counts"), Mapping)
        else {}
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Manifest ' + str(payload['manifest_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Manifest",
        "",
        f"Experiment: {escape(_single_line(str(scope.get('experiment') or 'all')))}",
        f"Include reports: {str(bool(scope.get('include_reports'))).lower()}",
        f"Artifacts: {int(summary.get('artifact_count') or 0)}",
        f"Total bytes: {int(summary.get('total_bytes') or 0)}",
        f"Content SHA-256: {escape(_single_line(str(payload.get('content_sha256') or '')))}",
        "",
        "## Artifact Types",
        "",
    ]
    if type_counts:
        for key, value in sorted(type_counts.items()):
            lines.append(f"- {escape(_single_line(str(key)))}: {int(value or 0)}")
    else:
        lines.append("- None")
    lines.extend(["", "## Schemas", ""])
    if schema_counts:
        for key, value in sorted(schema_counts.items()):
            lines.append(f"- {escape(_single_line(str(key)))}: {int(value or 0)}")
    else:
        lines.append("- None")
    lines.extend(["", "## Artifacts", ""])
    lines.extend(
        [
            "| Path | Type | Bytes | SHA-256 |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for item in artifacts[:200]:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('path') or '')))} | "
            f"{escape(_single_line(str(item.get('artifact_type') or '')))} | "
            f"{int(item.get('bytes') or 0)} | "
            f"{escape(_single_line(str(item.get('sha256') or '')))} |"
        )
    if len(artifacts) > 200:
        lines.append(f"| ... {len(artifacts) - 200} more artifact(s) omitted from Markdown view |  |  |  |")
    lines.append("")
    return "\n".join(lines)


def _render_manifest_verification_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"] if isinstance(payload.get("summary"), Mapping) else {}
    findings = payload["findings"] if isinstance(payload.get("findings"), list) else []
    lines = [
        "---",
        f"title: {json.dumps('Agent Manifest Verification ' + str(payload['verification_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Manifest Verification",
        "",
        f"Manifest: {escape(_single_line(str(payload.get('manifest_id') or '')))}",
        f"Status: {escape(_single_line(str(payload.get('verification_status') or '')))}",
        f"Verified: {str(bool(payload.get('verified'))).lower()}",
        f"Checked artifacts: {int(summary.get('checked_artifacts') or 0)}",
        f"Changed artifacts: {int(summary.get('changed_artifacts') or 0)}",
        f"Missing artifacts: {int(summary.get('missing_artifacts') or 0)}",
        f"Extra artifacts: {int(summary.get('extra_artifacts') or 0)}",
        f"Fail: {int(summary.get('fail') or 0)}",
        f"Warn: {int(summary.get('warn') or 0)}",
        "",
        "## Findings",
        "",
    ]
    if findings:
        for item in findings:
            if not isinstance(item, Mapping):
                continue
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('path', ''))))} "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))}"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_preflight_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"] if isinstance(payload.get("summary"), Mapping) else {}
    policy = payload["policy"] if isinstance(payload.get("policy"), Mapping) else {}
    coverage = payload["coverage"] if isinstance(payload.get("coverage"), Mapping) else {}
    experiments = payload["experiments"] if isinstance(payload.get("experiments"), list) else []
    findings = payload["findings"] if isinstance(payload.get("findings"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Preflight ' + str(payload['preflight_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Preflight",
        "",
        f"Status: {escape(_single_line(str(payload['preflight_status'])))}",
        f"Ready: {str(bool(payload.get('ready'))).lower()}",
        f"Experiments: {int(summary.get('experiments') or 0)}",
        f"Plans: {int(summary.get('plans') or 0)}",
        f"Pending runs: {int(summary.get('pending_runs') or 0)}",
        f"Active claims: {int(summary.get('active_claims') or 0)}",
        f"Active holds: {int(summary.get('active_holds') or 0)}",
        f"Active quarantines: {int(summary.get('active_quarantines') or 0)}",
        f"Quarantined pending runs: {int(summary.get('quarantined_pending_runs') or 0)}",
        f"Stale claims: {int(summary.get('stale_claims') or 0)}",
        f"Failed outcomes: {int(summary.get('failed_outcomes') or 0)}",
        "",
        "## Policy",
        "",
        f"- Min pending runs: {int(policy.get('min_pending_runs') or 0)}",
        f"- Max active claims: {escape(_single_line(str(policy.get('max_active_claims'))))}",
        f"- Stale after seconds: {int(policy.get('stale_after_seconds') or 0)}",
        f"- Require cross model: {str(bool(policy.get('require_cross_model'))).lower()}",
        f"- Require lane coverage: {str(bool(policy.get('require_lane_coverage'))).lower()}",
        f"- Require variant coverage: {str(bool(policy.get('require_variant_coverage'))).lower()}",
        f"- Max pending skew: {escape(_single_line(str(policy.get('max_pending_skew'))))}",
        f"- Block failed outcomes: {str(bool(policy.get('block_failed_outcomes'))).lower()}",
        "",
        "## Coverage",
        "",
        f"- Pending lanes: {escape(_single_line(', '.join(str(item) for item in coverage.get('pending_lanes', []))))}",
        f"- Pending variants: {escape(_single_line(', '.join(str(item) for item in coverage.get('pending_variants', []))))}",
        f"- Pending providers: {escape(_single_line(', '.join(str(item) for item in coverage.get('pending_providers', []))))}",
        f"- Pending adapters: {escape(_single_line(', '.join(str(item) for item in coverage.get('pending_adapters', []))))}",
        f"- Pending sample skew: {int(coverage.get('pending_sample_skew') or 0)}",
        "",
        "## Experiment Counts",
        "",
        "| Experiment | Plans | Scheduled | Pending | Quarantined | Completed | Active claims | Active holds | Active quarantines | Stale | Expired | Failed | Skew |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in experiments:
        if not isinstance(item, Mapping):
            continue
        counts = item.get("counts") if isinstance(item.get("counts"), Mapping) else {}
        item_coverage = item.get("coverage") if isinstance(item.get("coverage"), Mapping) else {}
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('experiment') or '')))} | "
            f"{int(counts.get('plans') or 0)} | "
                f"{int(counts.get('scheduled_runs') or 0)} | "
                f"{int(counts.get('pending_runs') or 0)} | "
                f"{int(counts.get('quarantined_pending_runs') or 0)} | "
                f"{int(counts.get('completed_runs') or 0)} | "
                f"{int(counts.get('active_claims') or 0)} | "
                f"{int(counts.get('active_holds') or 0)} | "
                f"{int(counts.get('active_quarantines') or 0)} | "
                f"{int(counts.get('stale_claims') or 0)} | "
            f"{int(counts.get('expired_claims') or 0)} | "
            f"{int(counts.get('failed_outcomes') or 0)} | "
            f"{int(item_coverage.get('pending_sample_skew') or 0)} |"
        )
    lines.extend(["", "## Findings", ""])
    if findings:
        for item in findings:
            if not isinstance(item, Mapping):
                continue
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('experiment', ''))))} "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_timeline_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"]
    events = payload["events"]
    event_types = summary.get("event_types") if isinstance(summary, dict) else {}
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Timeline ' + str(payload['timeline_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Timeline",
        "",
        f"Scope: {escape(_single_line(str(payload.get('scope') or 'all')))}",
        f"Experiments: {int(summary['experiments'])}",
        f"Events: {int(summary['events'])}",
        f"Total events: {int(summary['total_events'])}",
        "",
        "## Event Types",
        "",
    ]
    if isinstance(event_types, dict) and event_types:
        for event_type, count in sorted(event_types.items()):
            lines.append(
                f"- {escape(_single_line(str(event_type)))}: {int(count or 0)}"
            )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Events",
            "",
            "| Time | Experiment | Type | Artifact | Run | Plan | Lane | Variant | Status | Message |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    if isinstance(events, list):
        for item in events:
            if not isinstance(item, dict):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('timestamp', ''))))} | "
                f"{escape(_single_line(str(item.get('experiment', ''))))} | "
                f"{escape(_single_line(str(item.get('event_type', ''))))} | "
                f"{escape(_single_line(str(item.get('artifact_id') or item.get('artifact') or '')))} | "
                f"{escape(_single_line(str(item.get('run_id') or '')))} | "
                f"{escape(_single_line(str(item.get('plan_id') or '')))} | "
                f"{escape(_single_line(str(item.get('lane_id') or '')))} | "
                f"{escape(_single_line(str(item.get('variant_id') or '')))} | "
                f"{escape(_single_line(str(item.get('status') or '')))} | "
                f"{escape(_single_line(str(item.get('message') or '')))} |"
            )
    lines.append("")
    return "\n".join(lines)


def _render_watchdog_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"]
    policy = payload["policy"]
    experiments = payload["experiments"]
    findings = payload["findings"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Watchdog ' + str(payload['watchdog_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Watchdog",
        "",
        f"Scope: {escape(_single_line(str(payload.get('scope') or 'all')))}",
        f"Needs attention: {str(bool(summary['needs_attention'])).lower()}",
        f"Stale after seconds: {int(policy['stale_after_seconds'])}",
        f"Pending runs: {int(summary['pending_runs'])}",
        f"Active claims: {int(summary['active_claims'])}",
        f"Stale claims: {int(summary['stale_claims'])}",
        f"Expired claims: {int(summary['expired_claims'])}",
        f"Failed outcomes: {int(summary['failed_outcomes'])}",
        "",
        "## Experiment Counts",
        "",
        "| Experiment | Plans | Claims | Heartbeats | Pending | Active claims | Stale claims | Expired claims | Failed outcomes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    if isinstance(experiments, list):
        for item in experiments:
            if not isinstance(item, dict):
                continue
            counts = item.get("counts") if isinstance(item.get("counts"), dict) else {}
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('experiment', ''))))} | "
                f"{int(counts.get('plans') or 0)} | "
                f"{int(counts.get('claims') or 0)} | "
                f"{int(counts.get('heartbeats') or 0)} | "
                f"{int(counts.get('pending_runs') or 0)} | "
                f"{int(counts.get('active_claims') or 0)} | "
                f"{int(counts.get('stale_claims') or 0)} | "
                f"{int(counts.get('expired_claims') or 0)} | "
                f"{int(counts.get('failed_outcomes') or 0)} |"
            )
    lines.extend(["", "## Findings", ""])
    if isinstance(findings, list):
        for item in findings:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('experiment', ''))))} "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))}"
            )
    lines.append("")
    return "\n".join(lines)


def _render_agent_dashboard_html(payload: Mapping[str, object]) -> str:
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    experiments = payload["experiments"] if isinstance(payload.get("experiments"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    events = payload["events"] if isinstance(payload.get("events"), list) else []
    title = "Agent Harness Dashboard"
    scope = escape(_single_line(str(payload.get("scope") or "all")))
    generated_at = escape(_single_line(str(payload.get("generated_at") or "")))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; style-src 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none';">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #f8f8f5;
      --ink: #171717;
      --muted: #5c625f;
      --panel: #ffffff;
      --line: #d9ddd8;
      --accent: #006d77;
      --ok: #1f7a4d;
      --warn: #9a6700;
      --bad: #b42318;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #101211;
        --ink: #f3f4ef;
        --muted: #b9bdb7;
        --panel: #181b19;
        --line: #343a35;
        --accent: #6cc7d2;
        --ok: #73d69a;
        --warn: #f1c45d;
        --bad: #ff8a7d;
      }}
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}
    main {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 42px;
    }}
    header {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 18px;
      margin-bottom: 20px;
    }}
    h1 {{
      font-size: clamp(2rem, 4vw, 3.5rem);
      line-height: 1.05;
      margin: 0 0 10px;
      letter-spacing: 0;
    }}
    h2 {{
      color: var(--accent);
      font-size: 1rem;
      margin: 0 0 12px;
      text-transform: uppercase;
      letter-spacing: 0;
    }}
    h3 {{
      font-size: 1rem;
      margin: 18px 0 8px;
      letter-spacing: 0;
    }}
    section {{
      border-bottom: 1px solid var(--line);
      padding: 20px 0;
    }}
    .meta, .metrics {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .meta span, .metric {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      max-width: 100%;
      overflow-wrap: anywhere;
    }}
    .meta span {{
      color: var(--muted);
      font-size: .86rem;
      padding: 5px 8px;
    }}
    .metric {{
      min-width: 132px;
      padding: 10px 12px;
    }}
    .metric strong {{
      display: block;
      font-size: 1.35rem;
      line-height: 1.1;
    }}
    .metric span {{
      color: var(--muted);
      font-size: .78rem;
      text-transform: uppercase;
    }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 760px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 10px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }}
    th {{
      color: var(--muted);
      font-size: .78rem;
      text-transform: uppercase;
      letter-spacing: 0;
      white-space: nowrap;
    }}
    td.number, th.number {{
      text-align: right;
      white-space: nowrap;
    }}
    tr:last-child td {{
      border-bottom: 0;
    }}
    ul {{
      margin: 0;
      padding-left: 1.2rem;
    }}
    li + li {{
      margin-top: 8px;
    }}
    .status-ok {{ color: var(--ok); }}
    .status-warn {{ color: var(--warn); }}
    .status-bad {{ color: var(--bad); }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{title}</h1>
      <div class="meta">
        <span>Scope: {scope}</span>
        <span>Generated: {generated_at}</span>
        <span>Privacy: metadata-only</span>
      </div>
    </header>
    <section>
      <h2>Control Plane</h2>
      <div class="metrics">
        {_dashboard_metric("Experiments", summary.get("experiments"))}
        {_dashboard_metric("Runs", summary.get("runs"))}
        {_dashboard_metric("Plans", summary.get("plans"))}
        {_dashboard_metric("Dispatches", summary.get("dispatches"))}
        {_dashboard_metric("Suites", summary.get("suites"))}
        {_dashboard_metric("Arenas", summary.get("arenas"))}
        {_dashboard_metric("Arena Reports", summary.get("arena_reports"))}
        {_dashboard_metric("Judge Panels", summary.get("judge_panels"))}
        {_dashboard_metric("Judge Reports", summary.get("judge_reports"))}
        {_dashboard_metric("Pipelines", summary.get("pipelines"))}
        {_dashboard_metric("Pipeline Advances", summary.get("pipeline_advances"))}
        {_dashboard_metric("Outcomes", summary.get("outcomes"))}
        {_dashboard_metric("Pending", summary.get("pending_plan_runs"))}
        {_dashboard_metric("Claimed", summary.get("claimed_plan_runs"))}
        {_dashboard_metric("Failed", summary.get("failed_outcomes"))}
        {_dashboard_metric("Quorums", summary.get("quorums"))}
        {_dashboard_metric("Allocations", summary.get("allocations"))}
        {_dashboard_metric("Routes", summary.get("routes"))}
        {_dashboard_metric("Readiness", summary.get("readiness"))}
        {_dashboard_metric("Rollouts", summary.get("rollouts"))}
        {_dashboard_metric("Rollout Checks", summary.get("rollout_checks"))}
        {_dashboard_metric("Evolutions", summary.get("evolutions"))}
        {_dashboard_metric("Power", summary.get("power_reports"))}
        {_dashboard_metric("Schedules", summary.get("schedules"))}
        {_dashboard_metric("Schedule Reports", summary.get("schedule_reports"))}
        {_dashboard_metric("Leaderboards", summary.get("leaderboards"))}
        {_dashboard_metric("Config Proposals", summary.get("config_proposals"))}
        {_dashboard_metric("Mix", summary.get("mix_reports"))}
        {_dashboard_metric("Snapshots", summary.get("snapshots"))}
        {_dashboard_metric("Decisions", summary.get("decisions"))}
        {_dashboard_metric("Memories", summary.get("memories"))}
        {_dashboard_metric("Curricula", summary.get("curricula"))}
        {_dashboard_metric("Budgets", summary.get("budget_reports"))}
        {_dashboard_metric("Capacity", summary.get("capacity_reports"))}
        {_dashboard_metric("SLOs", summary.get("slo_reports"))}
        {_dashboard_metric("Ingests", summary.get("ingest_reports"))}
        {_dashboard_metric("Orchestrations", summary.get("orchestration_reports"))}
        {_dashboard_metric("Recoveries", summary.get("recovery_reports"))}
        {_dashboard_metric("Cycles", summary.get("cycle_reports"))}
        {_dashboard_metric("Loops", summary.get("loop_reports"))}
      </div>
    </section>
    <section>
      <h2>Experiments</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Experiment</th>
              <th class="number">Runs</th>
              <th class="number">Plans</th>
              <th class="number">Outcomes</th>
              <th class="number">Pending</th>
              <th class="number">Claimed</th>
              <th class="number">Failed</th>
              <th>Latest gate</th>
              <th>Latest readiness</th>
              <th>Latest rollout</th>
              <th>Latest rollout check</th>
              <th>Latest evolve</th>
              <th>Latest power</th>
              <th>Latest arena</th>
              <th>Latest arena report</th>
              <th>Latest judge</th>
              <th>Latest judge report</th>
              <th>Latest pipeline</th>
              <th>Latest pipeline advance</th>
              <th>Latest schedule</th>
              <th>Latest schedule report</th>
              <th>Latest leaderboard</th>
              <th>Latest config</th>
              <th>Latest promotion</th>
              <th>Latest decision</th>
              <th>Latest curriculum</th>
              <th>Latest winner</th>
            </tr>
          </thead>
          <tbody>
            {_dashboard_experiment_rows(experiments)}
          </tbody>
        </table>
      </div>
    </section>
    {_dashboard_variant_sections(experiments)}
    <section>
      <h2>Recommendations</h2>
      {_dashboard_recommendations(recommendations)}
    </section>
    <section>
      <h2>Recent Events</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Experiment</th>
              <th>Type</th>
              <th>Artifact</th>
              <th>Status</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {_dashboard_event_rows(events)}
          </tbody>
        </table>
      </div>
    </section>
  </main>
</body>
</html>
"""


def _dashboard_metric(label: str, value: object) -> str:
    return (
        '<div class="metric">'
        f"<strong>{escape(_single_line(_table_number(value)))}</strong>"
        f"<span>{escape(_single_line(label))}</span>"
        "</div>"
    )


def _dashboard_experiment_rows(experiments: list[object]) -> str:
    rows: list[str] = []
    for item in experiments:
        if not isinstance(item, dict):
            continue
        failed = int(item.get("failed_outcomes") or 0)
        pending = int(item.get("pending_plan_runs") or 0)
        status_class = "status-bad" if failed else "status-warn" if pending else "status-ok"
        rows.append(
            "<tr>"
            f"<td>{escape(_single_line(str(item.get('experiment') or '')))}</td>"
            f"<td class=\"number\">{int(item.get('run_count') or 0)}</td>"
            f"<td class=\"number\">{int(item.get('plan_count') or 0)}</td>"
            f"<td class=\"number\">{int(item.get('outcome_count') or 0)}</td>"
            f"<td class=\"number {status_class}\">{pending}</td>"
            f"<td class=\"number\">{int(item.get('claimed_plan_runs') or 0)}</td>"
            f"<td class=\"number {status_class}\">{failed}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_gate_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_readiness_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_rollout_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_rollout_check_decision') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_evolve_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_power_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_arena_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_arena_winner') or item.get('latest_arena_report_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_judge_panel_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_judge_winner') or item.get('latest_judge_report_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_pipeline_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_pipeline_advance_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_schedule_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_schedule_report_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_leaderboard_winner') or item.get('latest_leaderboard_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_config_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_promotion_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_decision') or item.get('latest_decision_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_curriculum_status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('latest_comparison_winner') or '')))}</td>"
            "</tr>"
        )
    return "\n".join(rows) or '<tr><td colspan="27">No agent experiments found.</td></tr>'


def _dashboard_variant_sections(experiments: list[object]) -> str:
    sections: list[str] = []
    for experiment in experiments:
        if not isinstance(experiment, dict):
            continue
        variants = experiment.get("variant_summaries")
        if not isinstance(variants, list) or not variants:
            continue
        rows: list[str] = []
        for item in variants:
            if not isinstance(item, dict):
                continue
            usage = item.get("usage") if isinstance(item.get("usage"), dict) else {}
            rows.append(
                "<tr>"
                f"<td>{escape(_single_line(str(item.get('variant_id') or '')))}</td>"
                f"<td>{escape(_single_line(str(item.get('provider') or '')))}</td>"
                f"<td>{escape(_single_line(str(item.get('model') or '')))}</td>"
                f"<td class=\"number\">{int(item.get('trials') or 0)}</td>"
                f"<td class=\"number\">{_table_number(item.get('success_rate'))}</td>"
                f"<td class=\"number\">{_table_number(item.get('primary_metric_mean'))}</td>"
                f"<td class=\"number\">{_table_number(usage.get('total_tokens_mean'))}</td>"
                f"<td class=\"number\">{_table_number(usage.get('cost_usd_mean'))}</td>"
                "</tr>"
            )
        if not rows:
            continue
        sections.append(
            "<section>"
            f"<h2>Variants: {escape(_single_line(str(experiment.get('experiment') or '')))}</h2>"
            '<div class="table-wrap"><table><thead><tr>'
            "<th>Variant</th><th>Provider</th><th>Model</th>"
            '<th class="number">Trials</th>'
            '<th class="number">Success</th>'
            '<th class="number">Metric</th>'
            '<th class="number">Avg tokens</th>'
            '<th class="number">Avg cost</th>'
            "</tr></thead><tbody>"
            + "\n".join(rows)
            + "</tbody></table></div></section>"
        )
    return "\n".join(sections)


def _dashboard_recommendations(recommendations: list[object]) -> str:
    items = [
        f"<li>{escape(_single_line(str(item)))}</li>"
        for item in recommendations
        if str(item).strip()
    ]
    return "<ul>" + "".join(items) + "</ul>" if items else "<p>No immediate action required.</p>"


def _dashboard_event_rows(events: list[object]) -> str:
    rows: list[str] = []
    for item in events:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{escape(_single_line(str(item.get('timestamp') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('experiment') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('event_type') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('artifact_id') or item.get('artifact') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('status') or '')))}</td>"
            f"<td>{escape(_single_line(str(item.get('message') or '')))}</td>"
            "</tr>"
        )
    return "\n".join(rows) or '<tr><td colspan="6">No events found.</td></tr>'


def _render_budget_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"]
    policy = payload["policy"]
    experiments = payload["experiments"]
    findings = payload["findings"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Budget ' + str(payload['budget_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Budget",
        "",
        f"Scope: {escape(_single_line(str(payload.get('scope') or 'all')))}",
        f"Status: {escape(_single_line(str(payload['budget_status'])))}",
        f"Over budget: {str(bool(payload.get('over_budget'))).lower()}",
        f"Experiments: {int(summary['experiments'])}",
        f"Outcomes: {int(summary['outcome_count'])}",
        f"Usage records: {int(summary['usage_count'])}",
        f"Missing usage records: {int(summary['missing_usage_count'])}",
        f"Total cost USD: {_table_number(summary.get('total_cost_usd'))}",
        f"Total tokens: {int(summary.get('total_tokens') or 0)}",
        f"Mean latency ms: {_table_number(summary.get('mean_latency_ms'))}",
        "",
        "## Policy",
        "",
        f"- Max cost USD: {_table_number(policy.get('max_cost_usd'))}",
        f"- Max total tokens: {_table_number(policy.get('max_total_tokens'))}",
        f"- Max mean latency ms: {_table_number(policy.get('max_mean_latency_ms'))}",
        f"- Max run cost USD: {_table_number(policy.get('max_run_cost_usd'))}",
        f"- Max run tokens: {_table_number(policy.get('max_run_tokens'))}",
        f"- Max run latency ms: {_table_number(policy.get('max_run_latency_ms'))}",
        "",
        "## Experiments",
        "",
        "| Experiment | Outcomes | Usage | Missing usage | Cost USD | Tokens | Mean latency ms | Max run cost | Max run tokens | Max run latency |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    if isinstance(experiments, list):
        for item in experiments:
            if not isinstance(item, dict):
                continue
            stats = item.get("summary") if isinstance(item.get("summary"), dict) else {}
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('experiment', ''))))} | "
                f"{int(stats.get('outcome_count') or 0)} | "
                f"{int(stats.get('usage_count') or 0)} | "
                f"{int(stats.get('missing_usage_count') or 0)} | "
                f"{_table_number(stats.get('total_cost_usd'))} | "
                f"{int(stats.get('total_tokens') or 0)} | "
                f"{_table_number(stats.get('mean_latency_ms'))} | "
                f"{_table_number(stats.get('max_run_cost_usd'))} | "
                f"{_table_number(stats.get('max_run_tokens'))} | "
                f"{_table_number(stats.get('max_run_latency_ms'))} |"
            )
    lines.extend(["", "## Findings", ""])
    if isinstance(findings, list):
        for item in findings:
            if not isinstance(item, dict):
                continue
            actual = _table_number(item.get("actual")) if item.get("actual") is not None else "n/a"
            limit = _table_number(item.get("limit")) if item.get("limit") is not None else "n/a"
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('experiment', ''))))} "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))} "
                f"(actual={actual}, limit={limit})"
            )
    lines.append("")
    return "\n".join(lines)


def _render_capacity_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"] if isinstance(payload.get("summary"), Mapping) else {}
    policy = payload["policy"] if isinstance(payload.get("policy"), Mapping) else {}
    experiments = payload["experiments"] if isinstance(payload.get("experiments"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Capacity ' + str(payload['capacity_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Capacity",
        "",
        f"Scope: {escape(_single_line(str(payload.get('scope') or 'all')))}",
        f"Status: {escape(_single_line(str(payload.get('capacity_status') or '')))}",
        f"Experiments: {int(summary.get('experiments') or 0)}",
        f"Pending runs: {int(summary.get('pending_runs') or 0)}",
        f"Active claims: {int(summary.get('active_claims') or 0)}",
        f"Available slots: {int(summary.get('available_slots') or 0)}",
        f"Recommended batch size: {int(summary.get('recommended_batch_size') or 0)}",
        "",
        "## Policy",
        "",
        f"- Max concurrency: {int(policy.get('max_concurrency') or 0)}",
        f"- Batch size: {escape(_single_line(str(policy.get('batch_size'))))}",
        f"- Target utilization: {_table_number(policy.get('target_utilization'))}",
        f"- Min batch size: {int(policy.get('min_batch_size') or 0)}",
        f"- Stale after seconds: {int(policy.get('stale_after_seconds') or 0)}",
        f"- Latency window: {int(policy.get('latency_window') or 0)}",
        "",
        "## Experiments",
        "",
        "| Experiment | Status | Pending | Active | Stale | Holds | Quarantined | Slots | Batch | Strategy | TTL | Mean latency ms |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for item in experiments:
        if not isinstance(item, Mapping):
            continue
        counts = item.get("counts") if isinstance(item.get("counts"), Mapping) else {}
        recommendation = item.get("recommendation") if isinstance(item.get("recommendation"), Mapping) else {}
        latency = item.get("recent_latency") if isinstance(item.get("recent_latency"), Mapping) else {}
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('experiment') or '')))} | "
            f"{escape(_single_line(str(item.get('capacity_status') or '')))} | "
            f"{int(counts.get('pending_runs') or 0)} | "
            f"{int(counts.get('active_claims') or 0)} | "
            f"{int(counts.get('stale_claims') or 0)} | "
            f"{int(counts.get('active_holds') or 0)} | "
            f"{int(counts.get('quarantined_pending_runs') or 0)} | "
            f"{int(recommendation.get('available_slots') or 0)} | "
            f"{int(recommendation.get('batch_size') or 0)} | "
            f"{escape(_single_line(str(recommendation.get('claim_strategy') or '')))} | "
            f"{int(recommendation.get('claim_ttl_seconds') or 0)} | "
            f"{_table_number(latency.get('mean_latency_ms'))} |"
        )
    lines.extend(["", "## Bottlenecks", ""])
    any_bottleneck = False
    for item in experiments:
        if not isinstance(item, Mapping):
            continue
        bottlenecks = item.get("bottlenecks") if isinstance(item.get("bottlenecks"), list) else []
        for bottleneck in bottlenecks:
            if not isinstance(bottleneck, Mapping):
                continue
            any_bottleneck = True
            lines.append(
                f"- {escape(_single_line(str(item.get('experiment') or '')))} "
                f"{escape(_single_line(str(bottleneck.get('code') or '')))} "
                f"({int(bottleneck.get('count') or 0)}): "
                f"{escape(_single_line(str(bottleneck.get('message') or '')))}"
            )
    if not any_bottleneck:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_slo_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"] if isinstance(payload.get("summary"), Mapping) else {}
    policy = payload["policy"] if isinstance(payload.get("policy"), Mapping) else {}
    experiments = payload["experiments"] if isinstance(payload.get("experiments"), list) else []
    findings = payload["findings"] if isinstance(payload.get("findings"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness SLO ' + str(payload['slo_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness SLO",
        "",
        f"Scope: {escape(_single_line(str(payload.get('scope') or 'all')))}",
        f"Status: {escape(_single_line(str(payload.get('slo_status') or '')))}",
        f"Passed: {str(bool(payload.get('passed'))).lower()}",
        f"Scheduled runs: {int(summary.get('scheduled_runs') or 0)}",
        f"Completed runs: {int(summary.get('completed_runs') or 0)}",
        f"Failed outcomes: {int(summary.get('failed_outcomes') or 0)}",
        f"Findings: {int(summary.get('findings') or 0)}",
        "",
        "## Policy",
        "",
        f"- Min completion rate: {_table_number(policy.get('min_completion_rate'))}",
        f"- Max failure rate: {_table_number(policy.get('max_failure_rate'))}",
        f"- Max stale claims: {int(policy.get('max_stale_claims') or 0)}",
        f"- Max expired claims: {int(policy.get('max_expired_claims') or 0)}",
        f"- Max active claims: {escape(_single_line(str(policy.get('max_active_claims'))))}",
        f"- Max quarantined pending runs: {escape(_single_line(str(policy.get('max_quarantined_pending_runs'))))}",
        f"- Max mean latency ms: {_table_number(policy.get('max_mean_latency_ms'))}",
        f"- Require no active holds: {str(bool(policy.get('require_no_active_holds'))).lower()}",
        f"- Require no active quarantines: {str(bool(policy.get('require_no_active_quarantines'))).lower()}",
        "",
        "## Experiments",
        "",
        "| Experiment | Status | Scheduled | Completed | Completion rate | Failed | Failure rate | Pending | Active | Stale | Expired | Holds | Quarantined | Mean latency ms |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in experiments:
        if not isinstance(item, Mapping):
            continue
        metrics = item.get("metrics") if isinstance(item.get("metrics"), Mapping) else {}
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('experiment') or '')))} | "
            f"{escape(_single_line(str(item.get('slo_status') or '')))} | "
            f"{int(metrics.get('scheduled_runs') or 0)} | "
            f"{int(metrics.get('completed_runs') or 0)} | "
            f"{_table_number(metrics.get('completion_rate'))} | "
            f"{int(metrics.get('failed_outcomes') or 0)} | "
            f"{_table_number(metrics.get('failure_rate'))} | "
            f"{int(metrics.get('pending_runs') or 0)} | "
            f"{int(metrics.get('active_claims') or 0)} | "
            f"{int(metrics.get('stale_claims') or 0)} | "
            f"{int(metrics.get('expired_claims') or 0)} | "
            f"{int(metrics.get('active_holds') or 0)} | "
            f"{int(metrics.get('quarantined_pending_runs') or 0)} | "
            f"{_table_number(metrics.get('mean_latency_ms'))} |"
        )
    lines.extend(["", "## Findings", ""])
    if findings:
        for item in findings:
            if not isinstance(item, Mapping):
                continue
            actual = _table_number(item.get("actual")) if item.get("actual") is not None else "n/a"
            limit = _table_number(item.get("limit")) if item.get("limit") is not None else "n/a"
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('experiment', ''))))} "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))} "
                f"(actual={actual}, limit={limit})"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_mix_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"] if isinstance(payload.get("summary"), Mapping) else {}
    policy = payload["policy"] if isinstance(payload.get("policy"), Mapping) else {}
    providers = payload["providers"] if isinstance(payload.get("providers"), list) else []
    lanes = payload["lanes"] if isinstance(payload.get("lanes"), list) else []
    findings = payload["findings"] if isinstance(payload.get("findings"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), Mapping) else {}
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Model Mix ' + str(payload['mix_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Model Mix",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload.get('mix_status') or '')))}",
        f"Passed: {str(bool(payload.get('passed'))).lower()}",
        f"Providers: {int(summary.get('provider_count') or 0)}",
        f"Variants: {int(summary.get('variant_count') or 0)}",
        f"Scheduled runs: {int(summary.get('scheduled_runs') or 0)}",
        f"Completed outcomes: {int(summary.get('completed_outcomes') or 0)}",
        f"Max provider weight share: {_table_number(summary.get('max_provider_weight_share'))}",
        f"Max scheduled provider share: {_table_number(summary.get('max_scheduled_provider_share'))}",
        f"Max completed provider share: {_table_number(summary.get('max_completed_provider_share'))}",
        "",
        "## Policy",
        "",
        f"- Minimum providers: {int(policy.get('min_provider_count') or 0)}",
        f"- Minimum variants: {int(policy.get('min_variant_count') or 0)}",
        f"- Max provider weight share: {_table_number(policy.get('max_provider_weight_share'))}",
        f"- Max scheduled provider share: {_table_number(policy.get('max_scheduled_provider_share'))}",
        f"- Max completed provider share: {_table_number(policy.get('max_completed_provider_share'))}",
        f"- Require local provider: {str(bool(policy.get('require_local_provider'))).lower()}",
        "",
        "## Providers",
        "",
        "| Provider | Local | Variants | Weight share | Scheduled | Scheduled share | Completed | Completed share | Failed | Adapters | Models |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in providers:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('provider') or '')))} | "
            f"{str(bool(item.get('local'))).lower()} | "
            f"{int(item.get('configured_variants') or 0)} | "
            f"{_table_number(item.get('configured_weight_share'))} | "
            f"{int(item.get('scheduled_runs') or 0)} | "
            f"{_table_number(item.get('scheduled_share'))} | "
            f"{int(item.get('completed_outcomes') or 0)} | "
            f"{_table_number(item.get('completed_share'))} | "
            f"{int(item.get('failed_outcomes') or 0)} | "
            f"{escape(_single_line(', '.join(str(value) for value in item.get('adapters', []))))} | "
            f"{escape(_single_line(', '.join(str(value) for value in item.get('models', []))))} |"
        )
    lines.extend(
        [
            "",
            "## Lanes",
            "",
            "| Lane | Providers | Scheduled | Completed |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for item in lanes:
        if not isinstance(item, Mapping):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('lane_id') or '')))} | "
            f"{int(item.get('provider_count') or 0)} | "
            f"{int(item.get('scheduled_runs') or 0)} | "
            f"{int(item.get('completed_outcomes') or 0)} |"
        )
    lines.extend(["", "## Findings", ""])
    if findings:
        for item in findings:
            if not isinstance(item, Mapping):
                continue
            actual = _table_number(item.get("actual")) if item.get("actual") is not None else "n/a"
            limit = _table_number(item.get("limit")) if item.get("limit") is not None else "n/a"
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))} "
                f"(actual={actual}, limit={limit})"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_snapshot_report(payload: Mapping[str, object]) -> str:
    summary = payload["summary"] if isinstance(payload.get("summary"), Mapping) else {}
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), Mapping) else {}
    changes = payload["changes"] if isinstance(payload.get("changes"), list) else []
    state = payload["state"] if isinstance(payload.get("state"), Mapping) else {}
    artifact_counts = state.get("artifact_counts") if isinstance(state.get("artifact_counts"), Mapping) else {}
    outcome_summary = state.get("outcomes") if isinstance(state.get("outcomes"), Mapping) else {}
    plan_summary = state.get("plans") if isinstance(state.get("plans"), Mapping) else {}
    variant_summary = state.get("variants") if isinstance(state.get("variants"), Mapping) else {}
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Snapshot ' + str(payload['snapshot_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Snapshot",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload.get('snapshot_status') or '')))}",
        f"Changed: {str(bool(payload.get('changed'))).lower()}",
        f"Baseline: {escape(_single_line(str(payload.get('baseline_snapshot_id') or 'none')))}",
        f"Content SHA-256: {escape(_single_line(str(payload.get('content_sha256') or '')))}",
        f"Artifact records: {int(summary.get('artifact_records') or 0)}",
        f"Report records: {int(summary.get('report_records') or 0)}",
        f"Changed sections: {int(summary.get('changed_sections') or 0)}",
        "",
        "## Experiment Counts",
        "",
        "| Artifact | Count |",
        "| --- | ---: |",
    ]
    for key, value in sorted(artifact_counts.items()):
        lines.append(f"| {escape(_single_line(str(key)))} | {int(value or 0)} |")
    lines.extend(
        [
            "",
            "## Execution Shape",
            "",
            f"Plans: {int(plan_summary.get('count') or 0)}",
            f"Scheduled plan runs: {int(plan_summary.get('scheduled_runs') or 0)}",
            f"Outcome records: {int(outcome_summary.get('count') or 0)}",
            "",
            "### Scheduled Variants",
            "",
        ]
    )
    scheduled = variant_summary.get("scheduled") if isinstance(variant_summary.get("scheduled"), Mapping) else {}
    if scheduled:
        for key, value in sorted(scheduled.items()):
            lines.append(f"- {escape(_single_line(str(key)))}: {int(value or 0)}")
    else:
        lines.append("- None")
    lines.extend(["", "## Changes", ""])
    if changes:
        lines.extend(
            [
                "| Section | Type | Baseline SHA-256 | Current SHA-256 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for item in changes:
            if not isinstance(item, Mapping):
                continue
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('section') or '')))} | "
                f"{escape(_single_line(str(item.get('change_type') or '')))} | "
                f"{escape(_single_line(str(item.get('baseline_sha256') or '')))} | "
                f"{escape(_single_line(str(item.get('current_sha256') or '')))} |"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_drift_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), Mapping) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), Mapping) else {}
    policy = payload["policy"] if isinstance(payload.get("policy"), Mapping) else {}
    windows = payload["windows"] if isinstance(payload.get("windows"), list) else []
    findings = payload["findings"] if isinstance(payload.get("findings"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Drift ' + str(payload['drift_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Drift",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload['drift_status'])))}",
        f"Drift detected: {str(bool(payload.get('drift_detected'))).lower()}",
        f"Outcomes: {int(summary.get('outcome_count') or 0)}",
        f"Windows: {int(summary.get('window_count') or 0)}",
        f"Findings: {int(summary.get('findings') or 0)}",
        "",
        "## Policy",
        "",
        f"- Metric: {escape(_single_line(str(policy.get('metric_name') or '')))}",
        f"- Baseline window: {int(policy.get('baseline_window') or 0)}",
        f"- Recent window: {int(policy.get('recent_window') or 0)}",
        f"- Min samples: {int(policy.get('min_samples') or 0)}",
        f"- Max metric regression: {_table_number(policy.get('max_metric_drop'))}",
        f"- Max cost increase ratio: {_table_number(policy.get('max_cost_increase_ratio'))}",
        f"- Max latency increase ratio: {_table_number(policy.get('max_latency_increase_ratio'))}",
        "",
        "## Windows",
        "",
        "| Scope | Status | Baseline | Recent | Baseline mean | Recent mean | Regression | Cost ratio | Latency ratio |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in windows:
        if not isinstance(item, Mapping):
            continue
        metric = item.get("metric") if isinstance(item.get("metric"), Mapping) else {}
        usage = item.get("usage") if isinstance(item.get("usage"), Mapping) else {}
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('scope') or '')))}:{escape(_single_line(str(item.get('name') or '')))} | "
            f"{escape(_single_line(str(item.get('status') or '')))} | "
            f"{int(item.get('baseline_count') or 0)} | "
            f"{int(item.get('recent_count') or 0)} | "
            f"{_table_number(metric.get('baseline_mean'))} | "
            f"{_table_number(metric.get('recent_mean'))} | "
            f"{_table_number(metric.get('regression'))} | "
            f"{_table_number(usage.get('cost_increase_ratio'))} | "
            f"{_table_number(usage.get('latency_increase_ratio'))} |"
        )
    lines.extend(["", "## Findings", ""])
    if findings:
        for item in findings:
            if not isinstance(item, Mapping):
                continue
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('scope', ''))))} "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_readiness_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    policy = payload["policy"] if isinstance(payload.get("policy"), dict) else {}
    evidence = payload["evidence"] if isinstance(payload.get("evidence"), dict) else {}
    findings = payload["findings"] if isinstance(payload.get("findings"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Readiness ' + str(payload['readiness_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Readiness",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload['readiness_status'])))}",
        f"Ready: {str(bool(payload.get('ready'))).lower()}",
        f"Runs: {int(summary.get('run_count') or 0)}",
        f"Plans: {int(summary.get('plan_count') or 0)}",
        f"Outcomes: {int(summary.get('outcome_count') or 0)}",
        f"Failed outcomes: {int(summary.get('failed_outcomes') or 0)}",
        f"Sampled variants: {int(summary.get('sampled_variants') or 0)}/{int(summary.get('variant_count') or 0)}",
        f"Findings: {int(summary.get('findings') or 0)}",
        "",
        "## Policy",
        "",
        f"- Min outcomes: {int(policy.get('min_outcomes') or 0)}",
        f"- Max failed outcomes: {int(policy.get('max_failed_outcomes') or 0)}",
        f"- Require comparison: {str(bool(policy.get('require_comparison'))).lower()}",
        f"- Require budget: {str(bool(policy.get('require_budget'))).lower()}",
        f"- Require route: {str(bool(policy.get('require_route'))).lower()}",
        f"- Require memory: {str(bool(policy.get('require_memory'))).lower()}",
        f"- Require quorum: {str(bool(policy.get('require_quorum'))).lower()}",
        f"- Require promotion: {str(bool(policy.get('require_promotion'))).lower()}",
        f"- Require balance: {str(bool(policy.get('require_balance'))).lower()}",
        f"- Require drift: {str(bool(policy.get('require_drift'))).lower()}",
        "",
        "## Evidence",
        "",
        "| Artifact | Id | Status | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for label, id_key, status_key, detail_key in (
        ("Comparison", "comparison_id", "winner_variant_id", "eligible_variant_count"),
        ("Budget", "budget_id", "budget_status", "total_cost_usd"),
        ("Balance", "balance_id", "balance_status", "sample_skew"),
        ("Drift", "drift_id", "drift_status", "fail"),
        ("Route", "route_id", "recommended_routes", "lane_count"),
        ("Memory", "memory_id", "lesson_count", "failure_mode_count"),
        ("Quorum", "quorum_id", "quorum_status", "agreement_ratio"),
        ("Gate", "gate_id", "gate_status", "plan_id"),
        ("Promotion", "promotion_id", "promotion_status", "candidate_variant_id"),
        ("Suite report", "report_id", "winner_variant_id", "complete_cases"),
        ("Allocation", "allocation_id", "winner_variant_id", "measured_variants"),
    ):
        record_key = "latest_" + label.lower().replace(" ", "_")
        record = evidence.get(record_key)
        if not isinstance(record, dict):
            lines.append(f"| {label} |  | missing |  |")
            continue
        lines.append(
            "| "
            f"{label} | "
            f"{escape(_single_line(str(record.get(id_key) or '')))} | "
            f"{escape(_single_line(str(record.get(status_key) or '')))} | "
            f"{escape(_single_line(_table_number(record.get(detail_key))))} |"
        )
    lines.extend(["", "## Findings", ""])
    if findings:
        for item in findings:
            if not isinstance(item, dict):
                continue
            artifact = item.get("artifact_id")
            suffix = f" ({artifact})" if artifact else ""
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))}"
                f"{escape(_single_line(suffix))}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_rollout_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    policy = payload["policy"] if isinstance(payload.get("policy"), dict) else {}
    evidence = payload["evidence"] if isinstance(payload.get("evidence"), dict) else {}
    stages = payload["stages"] if isinstance(payload.get("stages"), list) else []
    findings = payload["findings"] if isinstance(payload.get("findings"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    rollback = payload["rollback_policy"] if isinstance(payload.get("rollback_policy"), dict) else {}
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Rollout ' + str(payload['rollout_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Rollout",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload['rollout_status'])))}",
        f"Ready: {str(bool(payload.get('ready'))).lower()}",
        f"Champion: {escape(_single_line(str(payload.get('champion_variant_id') or 'none')))}",
        f"Candidate: {escape(_single_line(str(payload.get('candidate_variant_id') or 'none')))}",
        f"Stages: {int(summary.get('stage_count') or 0)}",
        f"Final candidate share: {_table_number(summary.get('final_candidate_share'))}",
        "",
        "## Policy",
        "",
        f"- Min observation runs per stage: {int(policy.get('min_observation_runs') or 0)}",
        f"- Max failed outcomes per stage: {int(policy.get('max_stage_failed_outcomes') or 0)}",
        f"- Require readiness: {str(bool(policy.get('require_readiness'))).lower()}",
        f"- Require promotion: {str(bool(policy.get('require_promotion'))).lower()}",
        f"- Require budget: {str(bool(policy.get('require_budget'))).lower()}",
        f"- Require drift: {str(bool(policy.get('require_drift'))).lower()}",
        "",
        "## Evidence",
        "",
        "| Artifact | Id | Status | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for label, record_key, id_key, status_key, detail_key in (
        ("Readiness", "latest_readiness", "readiness_id", "readiness_status", "warn"),
        ("Promotion", "latest_promotion", "promotion_id", "promotion_status", "candidate_variant_id"),
        ("Budget", "latest_budget", "budget_id", "budget_status", "total_cost_usd"),
        ("Drift", "latest_drift", "drift_id", "drift_status", "fail"),
        ("Comparison", "latest_comparison", "comparison_id", "winner_variant_id", "eligible_variant_count"),
        ("Allocation", "latest_allocation", "allocation_id", "winner_variant_id", "measured_variants"),
        ("Route", "latest_route", "route_id", "recommended_routes", "lane_count"),
    ):
        record = evidence.get(record_key)
        if not isinstance(record, dict):
            lines.append(f"| {label} |  | missing |  |")
            continue
        lines.append(
            "| "
            f"{label} | "
            f"{escape(_single_line(str(record.get(id_key) or '')))} | "
            f"{escape(_single_line(str(record.get(status_key) or '')))} | "
            f"{escape(_single_line(_table_number(record.get(detail_key))))} |"
        )
    lines.extend(
        [
            "",
            "## Stages",
            "",
            "| Stage | Candidate share | Champion share | Min observations | Max failed | Entry requirements | Exit checks |",
            "| ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for item in stages:
        if not isinstance(item, dict):
            continue
        entry = item.get("entry_requirements") if isinstance(item.get("entry_requirements"), list) else []
        checks = item.get("exit_checks") if isinstance(item.get("exit_checks"), list) else []
        lines.append(
            "| "
            f"{int(item.get('stage_index') or 0)} | "
            f"{_table_number(item.get('candidate_share'))} | "
            f"{_table_number(item.get('champion_share'))} | "
            f"{int(item.get('min_observation_runs') or 0)} | "
            f"{int(item.get('max_failed_outcomes') or 0)} | "
            f"{escape(_single_line(', '.join(str(value) for value in entry)))} | "
            f"{escape(_single_line(', '.join(str(value) for value in checks)))} |"
        )
    lines.extend(["", "## Rollback", ""])
    lines.append(f"- Fallback: {escape(_single_line(str(rollback.get('fallback') or '')))}")
    rollback_checks = rollback.get("checks") if isinstance(rollback.get("checks"), list) else []
    if rollback_checks:
        lines.append(
            "- Checks: "
            + escape(_single_line(", ".join(str(value) for value in rollback_checks)))
        )
    lines.extend(["", "## Findings", ""])
    if findings:
        for item in findings:
            if not isinstance(item, dict):
                continue
            artifact = item.get("artifact_id")
            suffix = f" ({artifact})" if artifact else ""
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))}"
                f"{escape(_single_line(suffix))}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_rollout_check_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    stage = payload["stage"] if isinstance(payload.get("stage"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    policy = payload["policy"] if isinstance(payload.get("policy"), dict) else {}
    evidence = payload["evidence"] if isinstance(payload.get("evidence"), dict) else {}
    findings = payload["findings"] if isinstance(payload.get("findings"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    usage = summary.get("usage") if isinstance(summary.get("usage"), dict) else {}
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Rollout Check ' + str(payload['check_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Rollout Check",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Rollout: {escape(_single_line(str(payload.get('rollout_id') or '')))}",
        f"Stage: {int(stage.get('stage_index') or 0)}",
        f"Decision: {escape(_single_line(str(payload.get('decision') or '')))}",
        f"Target candidate share: {_table_number(summary.get('target_candidate_share'))}",
        f"Observed candidate share: {_table_number(summary.get('observed_candidate_share'))}",
        f"Candidate outcomes: {int(summary.get('candidate_outcome_count') or 0)}",
        f"Champion outcomes: {int(summary.get('champion_outcome_count') or 0)}",
        f"Failed candidate outcomes: {int(summary.get('failed_candidate_outcomes') or 0)}",
        f"Candidate metric mean: {_table_number(summary.get('candidate_metric_mean'))}",
        f"Champion metric mean: {_table_number(summary.get('champion_metric_mean'))}",
        f"Metric gap: {_table_number(summary.get('metric_gap'))}",
        f"Usage records: {int(usage.get('usage_count') or 0)}",
        f"Total cost USD: {_table_number(usage.get('total_cost_usd'))}",
        "",
        "## Policy",
        "",
        f"- Min stage outcomes: {int(policy.get('min_stage_outcomes') or 0)}",
        f"- Max stage failed outcomes: {int(policy.get('max_stage_failed_outcomes') or 0)}",
        f"- Max share deviation: {_table_number(policy.get('max_share_deviation'))}",
        f"- Min metric delta: {_table_number(policy.get('min_metric_delta'))}",
        f"- Require budget: {str(bool(policy.get('require_budget'))).lower()}",
        f"- Require readiness: {str(bool(policy.get('require_readiness'))).lower()}",
        f"- Require drift: {str(bool(policy.get('require_drift'))).lower()}",
        "",
        "## Evidence",
        "",
        "| Artifact | Id | Status | Detail |",
        "| --- | --- | --- | --- |",
    ]
    for label, record_key, id_key, status_key, detail_key in (
        ("Rollout", "rollout", "rollout_id", "rollout_status", "stage_count"),
        ("Previous check", "previous_check", "check_id", "decision", "stage_index"),
        ("Budget", "latest_budget", "budget_id", "budget_status", "total_cost_usd"),
        ("Readiness", "latest_readiness", "readiness_id", "readiness_status", "warn"),
        ("Drift", "latest_drift", "drift_id", "drift_status", "fail"),
    ):
        record = evidence.get(record_key)
        if not isinstance(record, dict):
            lines.append(f"| {label} |  | missing |  |")
            continue
        lines.append(
            "| "
            f"{label} | "
            f"{escape(_single_line(str(record.get(id_key) or '')))} | "
            f"{escape(_single_line(str(record.get(status_key) or '')))} | "
            f"{escape(_single_line(_table_number(record.get(detail_key))))} |"
        )
    lines.extend(["", "## Findings", ""])
    if findings:
        for item in findings:
            if not isinstance(item, dict):
                continue
            artifact = item.get("artifact_id")
            suffix = f" ({artifact})" if artifact else ""
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))}"
                f"{escape(_single_line(suffix))}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_evolve_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"] if isinstance(payload.get("experiment"), dict) else {}
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    policy = payload["policy"] if isinstance(payload.get("policy"), dict) else {}
    steps = payload["steps"] if isinstance(payload.get("steps"), list) else []
    recommendations = (
        payload["recommendations"] if isinstance(payload.get("recommendations"), list) else []
    )
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Evolve ' + str(payload['evolve_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Evolve",
        "",
        f"Experiment: {escape(_single_line(str(experiment.get('name') or experiment.get('slug') or '')))}",
        f"Status: {escape(_single_line(str(payload['evolve_status'])))}",
        f"Steps: {int(summary.get('step_count') or 0)}",
        f"Written steps: {int(summary.get('written_steps') or 0)}",
        f"Failed steps: {int(summary.get('failed_steps') or 0)}",
        f"Attention steps: {int(summary.get('attention_steps') or 0)}",
        "",
        "## Policy",
        "",
        f"- Min trials per variant: {int(policy.get('min_trials_per_variant') or 0)}",
        f"- Min samples per variant: {int(policy.get('min_samples_per_variant') or 0)}",
        f"- Allocation strategy: {escape(_single_line(str(policy.get('allocation_strategy') or '')))}",
        f"- Route strategy: {escape(_single_line(str(policy.get('route_strategy') or '')))}",
        f"- Require budget: {str(bool(policy.get('require_budget'))).lower()}",
        f"- Require route: {str(bool(policy.get('require_route'))).lower()}",
        f"- Require drift: {str(bool(policy.get('require_drift'))).lower()}",
        f"- Plan rollout: {str(bool(policy.get('plan_rollout'))).lower()}",
        "",
        "## Steps",
        "",
        "| Step | Status | Artifact status | Artifact | Id | Message |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in steps:
        if not isinstance(item, dict):
            continue
        lines.append(
            "| "
            f"{escape(_single_line(str(item.get('step') or '')))} | "
            f"{escape(_single_line(str(item.get('status') or '')))} | "
            f"{escape(_single_line(str(item.get('artifact_status') or '')))} | "
            f"{escape(_single_line(str(item.get('artifact_type') or '')))} | "
            f"{escape(_single_line(str(item.get('artifact_id') or '')))} | "
            f"{escape(_single_line(str(item.get('message') or '')))} |"
        )
    lines.extend(["", "## Recommendations", ""])
    if recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_adjudication_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    summary = payload["summary"]
    consensus = payload["consensus"]
    lanes = payload["lane_decisions"]
    findings = payload["findings"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Adjudication ' + str(payload['adjudication_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Adjudication",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Plan: {escape(_single_line(str(payload['plan_id'])))}",
        f"Status: {escape(_single_line(str(payload['decision_status'])))}",
        f"Accepted: {str(bool(payload.get('accepted'))).lower()}",
        f"Recommended run: {escape(_single_line(str(payload.get('recommended_run_id') or 'none')))}",
        f"Recommended variant: {escape(_single_line(str(payload.get('recommended_variant_id') or 'none')))}",
        f"Completed runs: {int(summary['completed_runs'])}/{int(summary['expected_runs'])}",
        f"Agreement ratio: {_table_number(consensus.get('agreement_ratio'))}",
        "",
        "## Lane Decisions",
        "",
        "| Lane | Role | Complete | Status | Best run | Best variant | Best metric |",
        "| --- | --- | ---: | --- | --- | --- | ---: |",
    ]
    if isinstance(lanes, list):
        for item in lanes:
            if not isinstance(item, dict):
                continue
            complete = f"{int(item.get('completed_runs') or 0)}/{int(item.get('expected_runs') or 0)}"
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('lane_id', ''))))} | "
                f"{escape(_single_line(str(item.get('role', ''))))} | "
                f"{complete} | "
                f"{escape(_single_line(str(item.get('status', ''))))} | "
                f"{escape(_single_line(str(item.get('best_run_id') or '')))} | "
                f"{escape(_single_line(str(item.get('best_variant_id') or '')))} | "
                f"{_table_number(item.get('best_metric'))} |"
            )
    lines.extend(["", "## Findings", ""])
    if isinstance(findings, list):
        for item in findings:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))}"
            )
    lines.append("")
    return "\n".join(lines)


def _render_quorum_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    summary = payload["summary"]
    consensus = payload["consensus"]
    lane_votes = payload["lane_votes"]
    findings = payload["findings"]
    recommendations = payload["recommendations"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Quorum ' + str(payload['quorum_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Quorum",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Plan: {escape(_single_line(str(payload['plan_id'])))}",
        f"Status: {escape(_single_line(str(payload['quorum_status'])))}",
        f"Passed: {str(bool(payload.get('passed'))).lower()}",
        f"Leading variant: {escape(_single_line(str(consensus.get('leading_variant_id') or 'none')))}",
        f"Recommended variant: {escape(_single_line(str(payload.get('recommended_variant_id') or 'none')))}",
        f"Completed runs: {int(summary['completed_runs'])}/{int(summary['expected_runs'])}",
        f"Agreement ratio: {_table_number(consensus.get('agreement_ratio'))}",
        f"Split brain: {str(bool(consensus.get('split_brain'))).lower()}",
        "",
        "## Lane Votes",
        "",
        "| Lane | Role | Complete | Status | Vote run | Vote variant | Metric |",
        "| --- | --- | ---: | --- | --- | --- | ---: |",
    ]
    if isinstance(lane_votes, list):
        for item in lane_votes:
            if not isinstance(item, dict):
                continue
            complete = f"{int(item.get('completed_runs') or 0)}/{int(item.get('expected_runs') or 0)}"
            lines.append(
                "| "
                f"{escape(_single_line(str(item.get('lane_id', ''))))} | "
                f"{escape(_single_line(str(item.get('role', ''))))} | "
                f"{complete} | "
                f"{escape(_single_line(str(item.get('status', ''))))} | "
                f"{escape(_single_line(str(item.get('vote_run_id') or '')))} | "
                f"{escape(_single_line(str(item.get('vote_variant_id') or '')))} | "
                f"{_table_number(item.get('vote_metric'))} |"
            )
    lines.extend(["", "## Findings", ""])
    if isinstance(findings, list):
        for item in findings:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))}"
            )
    lines.extend(["", "## Recommendations", ""])
    if isinstance(recommendations, list) and recommendations:
        lines.extend(f"- {escape(_single_line(str(item)))}" for item in recommendations)
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _render_gate_report(payload: Mapping[str, object]) -> str:
    experiment = payload["experiment"]
    summary = payload["summary"]
    policy = payload["policy"]
    findings = payload["findings"]
    lines = [
        "---",
        f"title: {json.dumps('Agent Harness Gate ' + str(payload['gate_id']))}",
        f"created_at: {json.dumps(str(payload['generated_at']))}",
        "privacy: metadata-only",
        "---",
        "",
        "# Agent Harness Gate",
        "",
        f"Experiment: {escape(_single_line(str(experiment['name'])))}",
        f"Plan: {escape(_single_line(str(payload['plan_id'])))}",
        f"Status: {escape(_single_line(str(payload['gate_status'])))}",
        f"Completed runs: {int(summary['completed_runs'])}/{int(summary['expected_runs'])}",
        f"Failed runs: {int(summary['failed_runs'])}",
        f"Policy: min_completed_ratio={_table_number(policy.get('min_completed_ratio'))}, "
        f"max_failures={int(policy.get('max_failures') or 0)}, "
        f"metric_threshold={_table_number(policy.get('metric_threshold'))}",
        "",
        "## Findings",
        "",
    ]
    if isinstance(findings, list):
        for item in findings:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"- [{escape(_single_line(str(item.get('severity', ''))).upper())}] "
                f"{escape(_single_line(str(item.get('code', ''))))}: "
                f"{escape(_single_line(str(item.get('message', ''))))}"
            )
    lines.append("")
    return "\n".join(lines)
