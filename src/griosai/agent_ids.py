from __future__ import annotations

import secrets
from typing import Mapping

from .agent_core import _compact_timestamp, _hash_json, _hash_text


def _orchestration_id(
    generated_at: str,
    *,
    scope: Mapping[str, object],
    plan_ids: list[str],
    summary: Mapping[str, object],
    dispatches: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "scope": scope,
            "plan_ids": plan_ids,
            "summary": summary,
            "dispatches": dispatches,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"orchestration-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _run_id(
    *,
    generated_at: str,
    experiment_slug: str,
    variant_id: str,
    subject_hash: str,
    prompt_sha256: object,
) -> str:
    nonce = secrets.token_hex(4)
    digest = _hash_text(
        f"{generated_at}\0{experiment_slug}\0{variant_id}\0{subject_hash}\0{prompt_sha256}\0{nonce}"
    )
    return f"run-{_compact_timestamp(generated_at)}-{digest[:12]}"


def _plan_id(
    *,
    generated_at: str,
    experiment_slug: str,
    subject_hash: str,
    prompt_sha256: object,
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "experiment_slug": experiment_slug,
            "subject_hash": subject_hash,
            "prompt_sha256": prompt_sha256,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"plan-{_compact_timestamp(generated_at)}-{digest[:12]}"


def _claim_id(generated_at: str, plan_id: str, run_id: str, client_id: str) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "plan_id": plan_id,
            "run_id": run_id,
            "client_id": client_id,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"claim-{_compact_timestamp(generated_at)}-{digest[:10]}"


def _dispatch_id(
    generated_at: str,
    plan_id: str,
    client_prefix: str,
    entries: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "plan_id": plan_id,
            "client_prefix": client_prefix,
            "entries": entries,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"dispatch-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _hold_id(
    generated_at: str,
    experiment_slug: str,
    action: str,
    scopes: tuple[str, ...],
    reason: str,
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "experiment": experiment_slug,
            "action": action,
            "scopes": list(scopes),
            "reason": reason,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"hold-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _quarantine_id(
    generated_at: str,
    experiment_slug: str,
    action: str,
    target: Mapping[str, object],
    reason: str,
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "experiment": experiment_slug,
            "action": action,
            "target": target,
            "reason": reason,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"quarantine-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _circuit_id(
    generated_at: str,
    experiment_slug: str,
    group_by: str,
    summary: Mapping[str, object],
    groups: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "experiment": experiment_slug,
            "group_by": group_by,
            "summary": summary,
            "groups": groups,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"circuit-{_compact_timestamp(generated_at)}-{digest[:10]}"


def _agent_manifest_id(generated_at: str, scope: str, content_sha256: str) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "scope": scope,
            "content_sha256": content_sha256,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"agent-manifest-{_compact_timestamp(generated_at)}-{digest[:12]}"


def _agent_manifest_verification_id(
    generated_at: str,
    manifest_id: str,
    findings: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "manifest_id": manifest_id,
            "findings": findings,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"agent-manifest-verification-{_compact_timestamp(generated_at)}-{digest[:12]}"


def _ingest_id(
    generated_at: str,
    scope: list[str],
    result_count: int,
    entries: list[dict[str, object]],
    errors: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "scope": scope,
            "result_count": result_count,
            "entries": entries,
            "errors": errors,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"ingest-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _heartbeat_id(generated_at: str, claim_id: str, client_id: str) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "claim_id": claim_id,
            "client_id": client_id,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"heartbeat-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _retry_id(generated_at: str, original_run_id: str, replacement_run_id: str) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "original_run_id": original_run_id,
            "replacement_run_id": replacement_run_id,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"retry-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _recovery_id(
    generated_at: str,
    scope: str,
    candidates: list[dict[str, object]],
    entries: list[dict[str, object]],
    errors: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "scope": scope,
            "candidates": candidates,
            "entries": entries,
            "errors": errors,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"recovery-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _cycle_id(
    generated_at: str,
    scope: Mapping[str, object],
    summary: Mapping[str, object],
    artifacts: Mapping[str, object],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "scope": scope,
            "summary": summary,
            "artifacts": artifacts,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"cycle-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _agent_loop_id(
    generated_at: str,
    scope: Mapping[str, object],
    summary: Mapping[str, object],
    cycles: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "scope": scope,
            "summary": summary,
            "cycles": cycles,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"agent-loop-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _suite_id(
    *,
    generated_at: str,
    experiment_slug: str,
    suite_slug: str,
    subject_hash: str,
    suite_hash: str,
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "experiment_slug": experiment_slug,
            "suite_slug": suite_slug,
            "subject_hash": subject_hash,
            "suite_hash": suite_hash,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"suite-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _suite_report_id(
    generated_at: str,
    suite_id: str,
    baseline_variant_id: str,
    case_summaries: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "suite_id": suite_id,
            "baseline_variant_id": baseline_variant_id,
            "case_summaries": case_summaries,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"suite-report-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _pipeline_id(
    generated_at: str,
    experiment_slug: str,
    pipeline_slug: str,
    subject_hash: str,
    stages: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "experiment_slug": experiment_slug,
            "pipeline_slug": pipeline_slug,
            "subject_hash": subject_hash,
            "stages": stages,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"pipeline-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _pipeline_advance_id(
    generated_at: str,
    pipeline_id: str,
    summary: Mapping[str, object],
    plans: list[AgentPlanResult],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "pipeline_id": pipeline_id,
            "summary": dict(summary),
            "plans": [plan.plan_id for plan in plans],
            "nonce": secrets.token_hex(4),
        }
    )
    return f"pipeline-advance-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _arena_id(
    *,
    generated_at: str,
    experiment_slug: str,
    subject_hash: str,
    variant_ids: list[str],
    lane_ids: list[str],
    replicas: int,
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "experiment_slug": experiment_slug,
            "subject_hash": subject_hash,
            "variant_ids": variant_ids,
            "lane_ids": lane_ids,
            "replicas": replicas,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"arena-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _arena_report_id(
    generated_at: str,
    arena_id: str,
    summary: Mapping[str, object],
    variant_summaries: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "arena_id": arena_id,
            "summary": summary,
            "variant_summaries": [
                {
                    "variant_id": item.get("variant_id"),
                    "rank": item.get("rank"),
                    "wins": item.get("wins"),
                    "losses": item.get("losses"),
                    "ties": item.get("ties"),
                }
                for item in variant_summaries
            ],
            "nonce": secrets.token_hex(4),
        }
    )
    return f"arena-report-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _judge_panel_id(
    generated_at: str,
    experiment_slug: str,
    source_plan_id: str,
    target_run_ids: list[str],
    judge_variant_ids: list[str],
    metric: Mapping[str, object],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "experiment_slug": experiment_slug,
            "source_plan_id": source_plan_id,
            "target_run_ids": target_run_ids,
            "judge_variant_ids": judge_variant_ids,
            "metric": dict(metric),
            "nonce": secrets.token_hex(4),
        }
    )
    return f"judge-panel-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _judge_panel_report_id(
    generated_at: str,
    panel_id: str,
    summary: Mapping[str, object],
    variant_summaries: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "panel_id": panel_id,
            "summary": summary,
            "variant_summaries": [
                {
                    "variant_id": item.get("variant_id"),
                    "rank": item.get("rank"),
                    "score_mean": item.get("score_mean"),
                    "judged_target_count": item.get("judged_target_count"),
                }
                for item in variant_summaries
            ],
            "nonce": secrets.token_hex(4),
        }
    )
    return f"judge-report-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _outcome_id(
    run_id: str,
    status: str,
    metrics: Mapping[str, float],
) -> str:
    digest = _hash_json(
        {
            "run_id": run_id,
            "status": status,
            "metrics": dict(metrics),
            "nonce": secrets.token_hex(4),
        }
    )
    return f"outcome-{run_id}-{digest[:8]}"


def _scorecard_id(
    generated_at: str,
    run_id: str,
    aggregate_metric: str,
    aggregate_score: float,
) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "run_id": run_id,
            "aggregate_metric": aggregate_metric,
            "aggregate_score": aggregate_score,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"scorecard-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _work_packet_id(generated_at: str, run_id: str, claim_id: str | None) -> str:
    digest = _hash_json(
        {
            "generated_at": generated_at,
            "run_id": run_id,
            "claim_id": claim_id,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"work-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _loop_id(generated_at: str, experiment_slug: str, summaries: list[dict[str, object]]) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "summaries": summaries,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"loop-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _memory_id(generated_at: str, experiment_slug: str, lessons: list[dict[str, object]]) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "lessons": lessons,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"memory-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _curriculum_id(
    generated_at: str,
    experiment_slug: str,
    summary: Mapping[str, object],
    hard_cases: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "summary": summary,
            "cases": [
                {
                    "run_id": item.get("run_id"),
                    "outcome_id": item.get("outcome_id"),
                    "priority": item.get("priority"),
                    "variant_id": item.get("variant_id"),
                }
                for item in hard_cases
            ],
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"curriculum-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _allocation_id(
    generated_at: str,
    experiment_slug: str,
    strategy: str,
    allocations: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "strategy": strategy,
            "allocations": allocations,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"allocation-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _route_id(
    generated_at: str,
    experiment_slug: str,
    lane_policies: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "lane_policies": lane_policies,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"route-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _promotion_id(
    generated_at: str,
    experiment_slug: str,
    champion_variant_id: str,
    candidate_variant_id: str | None,
    decision: Mapping[str, object],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "champion": champion_variant_id,
            "candidate": candidate_variant_id,
            "status": decision.get("status"),
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"promotion-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _comparison_id(
    generated_at: str,
    experiment_slug: str,
    baseline_variant_id: str,
    summaries: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "baseline": baseline_variant_id,
            "summaries": summaries,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"compare-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _balance_id(
    generated_at: str,
    experiment_slug: str,
    scope: Mapping[str, object],
    summary: Mapping[str, object],
    dimensions: tuple[str, ...],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "scope": dict(scope),
            "summary": dict(summary),
            "dimensions": list(dimensions),
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"balance-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _decision_id(
    generated_at: str,
    experiment_slug: str,
    baseline_variant_id: str,
    candidate_variant_id: str | None,
    summary: Mapping[str, object],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "baseline": baseline_variant_id,
            "candidate": candidate_variant_id,
            "summary": summary,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"decision-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _power_id(
    generated_at: str,
    experiment_slug: str,
    baseline_variant_id: str,
    min_detectable_effect: float,
    summary: Mapping[str, object],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "baseline": baseline_variant_id,
            "min_detectable_effect": min_detectable_effect,
            "summary": summary,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"power-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _schedule_id(
    generated_at: str,
    experiment_slug: str,
    power_id: str,
    quotas: Mapping[str, int],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "power_id": power_id,
            "quotas": dict(sorted(quotas.items())),
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"schedule-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _schedule_report_id(
    generated_at: str,
    schedule_id: str,
    summary: Mapping[str, object],
    pairwise: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "schedule_id": schedule_id,
            "summary": summary,
            "pairwise": [
                {
                    "candidate_variant_id": item.get("candidate_variant_id"),
                    "paired_blocks": item.get("paired_blocks"),
                    "mean_directional_delta": item.get("mean_directional_delta"),
                    "status": item.get("status"),
                }
                for item in pairwise
            ],
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"schedule-report-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _leaderboard_id(
    generated_at: str,
    experiment_slug: str,
    summary: Mapping[str, object],
    rows: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "summary": summary,
            "rows": [
                {
                    "variant_id": row.get("variant_id"),
                    "rank": row.get("rank"),
                    "evidence_score": row.get("evidence_score"),
                }
                for row in rows
            ],
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"leaderboard-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _config_proposal_id(
    generated_at: str,
    experiment_slug: str,
    proposal: Mapping[str, object],
    patch: Mapping[str, object],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "source": proposal.get("source"),
            "artifact": proposal.get("artifact"),
            "patch": patch,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"config-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _status_id(generated_at: str, scope: str) -> str:
    digest = _hash_json(
        {
            "scope": scope,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"status-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _audit_id(generated_at: str, scope: str) -> str:
    digest = _hash_json(
        {
            "scope": scope,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"audit-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _preflight_id(
    generated_at: str,
    scope: Mapping[str, object],
    policy: Mapping[str, object],
    summary: Mapping[str, object],
) -> str:
    digest = _hash_json(
        {
            "scope": dict(scope),
            "policy": dict(policy),
            "summary": dict(summary),
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"preflight-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _timeline_id(generated_at: str, scope: str) -> str:
    digest = _hash_json(
        {
            "scope": scope,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"timeline-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _watchdog_id(generated_at: str, scope: str) -> str:
    digest = _hash_json(
        {
            "scope": scope,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"watchdog-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _capacity_id(
    generated_at: str,
    scope: Mapping[str, object],
    policy: Mapping[str, object],
    summary: Mapping[str, object],
) -> str:
    digest = _hash_json(
        {
            "scope": dict(scope),
            "generated_at": generated_at,
            "policy": dict(policy),
            "summary": dict(summary),
            "nonce": secrets.token_hex(4),
        }
    )
    return f"capacity-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _slo_id(
    generated_at: str,
    scope: Mapping[str, object],
    policy: Mapping[str, object],
    summary: Mapping[str, object],
) -> str:
    digest = _hash_json(
        {
            "scope": dict(scope),
            "generated_at": generated_at,
            "policy": dict(policy),
            "summary": dict(summary),
            "nonce": secrets.token_hex(4),
        }
    )
    return f"slo-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _mix_id(
    generated_at: str,
    experiment_slug: str,
    policy: Mapping[str, object],
    summary: Mapping[str, object],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "policy": dict(policy),
            "summary": dict(summary),
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"mix-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _snapshot_id(generated_at: str, experiment_slug: str, content_sha256: str) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "content_sha256": content_sha256,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"snapshot-{_compact_timestamp(generated_at)}-{digest[:10]}"


def _budget_id(generated_at: str, scope: str, policy: Mapping[str, object]) -> str:
    digest = _hash_json(
        {
            "scope": scope,
            "generated_at": generated_at,
            "policy": dict(policy),
            "nonce": secrets.token_hex(4),
        }
    )
    return f"budget-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _drift_id(
    generated_at: str,
    experiment_slug: str,
    policy: Mapping[str, object],
    summary: Mapping[str, object],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "policy": dict(policy),
            "summary": dict(summary),
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"drift-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _readiness_id(
    generated_at: str,
    experiment_slug: str,
    policy: Mapping[str, object],
    findings: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "generated_at": generated_at,
            "policy": dict(policy),
            "findings": findings,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"readiness-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _rollout_id(
    generated_at: str,
    experiment_slug: str,
    champion_variant_id: str,
    candidate_variant_id: str | None,
    policy: Mapping[str, object],
    findings: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "champion": champion_variant_id,
            "candidate": candidate_variant_id,
            "generated_at": generated_at,
            "policy": dict(policy),
            "findings": findings,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"rollout-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _rollout_check_id(
    generated_at: str,
    rollout_id: str,
    stage_index: int,
    decision: str,
    findings: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "rollout_id": rollout_id,
            "stage_index": stage_index,
            "decision": decision,
            "generated_at": generated_at,
            "findings": findings,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"rollout-check-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _evolve_id(
    generated_at: str,
    experiment_slug: str,
    steps: list[dict[str, object]],
) -> str:
    digest = _hash_json(
        {
            "experiment": experiment_slug,
            "generated_at": generated_at,
            "steps": steps,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"evolve-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _dashboard_id(generated_at: str, scope: str) -> str:
    digest = _hash_json(
        {
            "scope": scope,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"agent-dashboard-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _timeline_event_id(
    timestamp: str,
    experiment: str,
    event_type: str,
    artifact_id: str | None,
) -> str:
    digest = _hash_json(
        {
            "timestamp": timestamp,
            "experiment": experiment,
            "event_type": event_type,
            "artifact_id": artifact_id,
        }
    )
    return f"event-{digest[:16]}"


def _gate_id(generated_at: str, plan_id: str, findings: list[dict[str, str]]) -> str:
    digest = _hash_json(
        {
            "plan_id": plan_id,
            "findings": findings,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"gate-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _adjudication_id(
    generated_at: str,
    plan_id: str,
    findings: list[dict[str, str]],
) -> str:
    digest = _hash_json(
        {
            "plan_id": plan_id,
            "findings": findings,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"adjudication-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _quorum_id(
    generated_at: str,
    plan_id: str,
    consensus: Mapping[str, object],
    findings: list[dict[str, str]],
) -> str:
    digest = _hash_json(
        {
            "plan_id": plan_id,
            "consensus": dict(consensus),
            "findings": findings,
            "generated_at": generated_at,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"quorum-{_compact_timestamp(generated_at)}-{digest[:8]}"


def _merge_id(generated_at: str, plan_id: str, summaries: list[dict[str, object]]) -> str:
    digest = _hash_json(
        {
            "plan_id": plan_id,
            "summaries": summaries,
            "nonce": secrets.token_hex(4),
        }
    )
    return f"merge-{_compact_timestamp(generated_at)}-{digest[:8]}"
