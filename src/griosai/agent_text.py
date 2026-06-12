from __future__ import annotations

from typing import Mapping

from .agent_constants import DEFAULT_CLAIM_STRATEGY


def _quarantine_target_text(target: Mapping[str, object]) -> str:
    parts: list[str] = []
    for key, label in (
        ("variant_ids", "variants"),
        ("providers", "providers"),
        ("lanes", "lanes"),
    ):
        values = target.get(key) if isinstance(target.get(key), list) else []
        if values:
            parts.append(f"{label}={','.join(str(item) for item in values)}")
    return "; ".join(parts) or "none"


def _table_number(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.6g}"
    return ""


def format_agent_run_text(result: object) -> str:
    variant = result.payload["selected_variant"]
    return "\n".join(
        [
            f"Run: {result.run_id}",
            f"Experiment: {result.experiment}",
            f"Variant: {variant['id']} ({variant['provider']}:{variant['model']})",
            f"Wrote: {result.path}",
        ]
    )


def format_agent_plan_text(result: object) -> str:
    return "\n".join(
        [
            f"Plan: {result.plan_id}",
            f"Experiment: {result.experiment}",
            f"Runs: {len(result.runs)}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_suite_text(result: object) -> str:
    return "\n".join(
        [
            f"Suite: {result.suite_id}",
            f"Experiment: {result.experiment}",
            f"Cases: {result.payload['case_count']}",
            f"Plans: {result.payload['plan_count']}",
            f"Runs: {result.payload['run_count']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_suite_report_text(result: object) -> str:
    summary = result.payload["summary"]
    winner = result.payload.get("winner_variant_id") or "none"
    return "\n".join(
        [
            f"Suite report: {result.report_id}",
            f"Suite: {result.suite_id}",
            f"Experiment: {result.experiment}",
            f"Baseline: {result.payload['baseline_variant_id']}",
            f"Winner: {winner}",
            f"Cases complete: {summary['complete_cases']}/{summary['case_count']}",
            f"Paired comparisons: {summary['paired_comparisons']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_pipeline_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Pipeline: {result.pipeline_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['pipeline_status']}",
            f"Stages planned: {summary['planned_stages']}/{summary['stage_count']}",
            f"Scheduled now: {summary['scheduled_now']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_pipeline_advance_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Pipeline advance: {result.advance_id}",
            f"Pipeline: {result.pipeline_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['advance_status']}",
            f"Stages planned: {summary['planned_stages']}/{summary['stage_count']}",
            f"Scheduled now: {summary['scheduled_now']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_arena_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Arena: {result.arena_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['arena_status']}",
            f"Matches: {summary['scheduled_matches']}/{summary['requested_matches']}",
            f"Runs: {summary['scheduled_runs']}/{summary['requested_runs']}",
            f"Plan: {result.plan_id or 'none'}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_arena_report_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Arena report: {result.report_id}",
            f"Arena: {result.arena_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['report_status']}",
            f"Winner: {result.payload.get('winner_variant_id') or 'none'}",
            f"Complete matches: {summary['complete_matches']}/{summary['scheduled_matches']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_judge_panel_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Judge panel: {result.panel_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['panel_status']}",
            f"Targets: {summary['target_count']}",
            f"Judge runs: {summary['scheduled_runs']}/{summary['requested_runs']}",
            f"Plan: {result.plan_id or 'none'}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_judge_panel_report_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Judge report: {result.report_id}",
            f"Panel: {result.panel_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['report_status']}",
            f"Winner variant: {result.payload.get('winner_variant_id') or 'none'}",
            f"Winner target: {result.payload.get('winner_target_run_id') or 'none'}",
            f"Judgements: {summary['completed_judgements']}/{summary['judge_run_count']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_merge_text(result: object) -> str:
    recommended = result.payload.get("recommended_run_id") or "none"
    return "\n".join(
        [
            f"Merge: {result.merge_id}",
            f"Plan: {result.plan_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['merge_status']}",
            f"Recommended run: {recommended}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_claim_text(result: object) -> str:
    claim = result.payload["claim"]
    run = result.payload["run"]
    scheduler = result.payload.get("scheduler") if isinstance(result.payload.get("scheduler"), dict) else {}
    return "\n".join(
        [
            f"Claim: {result.claim_id}",
            f"Plan: {result.plan_id}",
            f"Run: {result.run_id}",
            f"Lane: {run['lane_id']}",
            f"Client: {claim['client_id']}",
            f"Strategy: {scheduler.get('strategy', DEFAULT_CLAIM_STRATEGY)}",
            f"Expires: {claim['expires_at']}",
            f"Wrote: {result.path}",
        ]
    )


def format_agent_dispatch_text(result: object) -> str:
    return "\n".join(
        [
            f"Dispatch: {result.dispatch_id}",
            f"Plan: {result.plan_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['dispatch_status']}",
            f"Claims: {result.payload['claimed_count']}/{result.payload['requested_count']}",
            f"Claim strategy: {result.payload.get('claim_strategy', DEFAULT_CLAIM_STRATEGY)}",
            f"Work packets: {result.payload['work_packet_count']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_hold_text(result: object) -> str:
    active_holds = result.payload.get("active_holds") if isinstance(result.payload.get("active_holds"), list) else []
    return "\n".join(
        [
            f"Hold: {result.hold_id}",
            f"Experiment: {result.experiment}",
            f"Action: {result.payload['action']}",
            f"Status: {result.payload['hold_status']}",
            f"Scopes: {', '.join(str(item) for item in result.payload.get('scopes', []))}",
            f"Active holds: {len(active_holds)}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_quarantine_text(result: object) -> str:
    active_quarantines = (
        result.payload.get("active_quarantines")
        if isinstance(result.payload.get("active_quarantines"), list)
        else []
    )
    target = result.payload["target"] if isinstance(result.payload.get("target"), dict) else {}
    target_text = _quarantine_target_text(target)
    return "\n".join(
        [
            f"Quarantine: {result.quarantine_id}",
            f"Experiment: {result.experiment}",
            f"Action: {result.payload['action']}",
            f"Status: {result.payload['quarantine_status']}",
            f"Target: {target_text}",
            f"Active quarantines: {len(active_quarantines)}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_circuit_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Circuit: {result.circuit_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['circuit_status']}",
            f"Tripped: {str(result.tripped).lower()}",
            f"Groups: {summary['group_count']}",
            f"Tripped groups: {summary['tripped_groups']}",
            f"Actions: {summary['action_count']}",
            f"Findings: {summary['findings']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_orchestration_text(result: object) -> str:
    summary = result.payload["summary"]
    policy = result.payload.get("policy") if isinstance(result.payload.get("policy"), dict) else {}
    return "\n".join(
        [
            f"Orchestration: {result.orchestration_id}",
            f"Status: {result.payload['orchestration_status']}",
            f"Plans: {summary['plan_count']}",
            f"Pending runs: {summary['pending_runs']}",
            f"Active claims: {summary['active_claims']}",
            f"Active holds: {summary.get('active_holds', 0)}",
            f"Dispatches: {summary['dispatch_count']}",
            f"Claimed: {summary['claimed_count']}",
            f"Claim strategy: {policy.get('claim_strategy', DEFAULT_CLAIM_STRATEGY)}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_heartbeat_text(result: object) -> str:
    heartbeat = result.payload["heartbeat"]
    return "\n".join(
        [
            f"Heartbeat: {result.heartbeat_id}",
            f"Claim: {result.claim_id}",
            f"Run: {result.run_id}",
            f"Client: {heartbeat['client_id']}",
            f"Expires: {heartbeat['expires_at']}",
            f"Wrote: {result.path}",
        ]
    )


def format_agent_retry_text(result: object) -> str:
    return "\n".join(
        [
            f"Retry: {result.retry_id}",
            f"Experiment: {result.experiment}",
            f"Original run: {result.original_run_id}",
            f"Replacement run: {result.replacement_run_id}",
            f"Reason: {result.payload['reason']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_recovery_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Recovery: {result.recovery_id}",
            f"Status: {result.payload['recovery_status']}",
            f"Candidates: {summary['candidate_count']}",
            f"Retries: {summary['retry_count']}",
            f"Errors: {summary['error_count']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_gate_text(result: object) -> str:
    return "\n".join(
        [
            f"Gate: {result.gate_id}",
            f"Plan: {result.plan_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['gate_status']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_adjudication_text(result: object) -> str:
    recommended = result.payload.get("recommended_run_id") or "none"
    return "\n".join(
        [
            f"Adjudication: {result.adjudication_id}",
            f"Plan: {result.plan_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['decision_status']}",
            f"Accepted: {str(result.accepted).lower()}",
            f"Recommended run: {recommended}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_quorum_text(result: object) -> str:
    summary = result.payload["summary"]
    consensus = result.payload["consensus"]
    return "\n".join(
        [
            f"Quorum: {result.quorum_id}",
            f"Plan: {result.plan_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['quorum_status']}",
            f"Passed: {str(result.passed).lower()}",
            f"Leading variant: {consensus.get('leading_variant_id') or 'none'}",
            f"Agreement ratio: {consensus['agreement_ratio']}",
            f"Completed runs: {summary['completed_runs']}/{summary['expected_runs']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_audit_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Audit: {result.audit_id}",
            f"Status: {'fail' if result.failed else 'pass'}",
            f"Experiments: {summary['experiments']}",
            f"Findings: {summary['findings']}",
            f"Pass: {summary['pass']}",
            f"Warn: {summary['warn']}",
            f"Fail: {summary['fail']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_manifest_text(result: object) -> str:
    summary = result.payload["summary"]
    scope = result.payload["scope"]
    return "\n".join(
        [
            f"Manifest: {result.manifest_id}",
            f"Experiment: {scope['experiment']}",
            f"Include reports: {str(scope['include_reports']).lower()}",
            f"Artifacts: {summary['artifact_count']}",
            f"Total bytes: {summary['total_bytes']}",
            f"Content SHA-256: {result.payload['content_sha256']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_manifest_verification_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Manifest verification: {result.verification_id}",
            f"Manifest: {result.manifest_id}",
            f"Status: {result.payload['verification_status']}",
            f"Verified: {str(result.verified).lower()}",
            f"Checked artifacts: {summary['checked_artifacts']}",
            f"Changed artifacts: {summary['changed_artifacts']}",
            f"Missing artifacts: {summary['missing_artifacts']}",
            f"Extra artifacts: {summary['extra_artifacts']}",
            f"Findings: {summary['findings']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_preflight_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Preflight: {result.preflight_id}",
            f"Status: {result.payload['preflight_status']}",
            f"Ready: {str(result.ready).lower()}",
            f"Plans: {summary['plans']}",
            f"Pending runs: {summary['pending_runs']}",
            f"Active claims: {summary['active_claims']}",
            f"Active quarantines: {summary.get('active_quarantines', 0)}",
            f"Stale claims: {summary['stale_claims']}",
            f"Findings: {summary['findings']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_timeline_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Timeline: {result.timeline_id}",
            f"Experiments: {summary['experiments']}",
            f"Events: {summary['events']}",
            f"Total events: {summary['total_events']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_watchdog_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Watchdog: {result.watchdog_id}",
            f"Needs attention: {str(result.needs_attention).lower()}",
            f"Experiments: {summary['experiments']}",
            f"Pending runs: {summary['pending_runs']}",
            f"Active claims: {summary['active_claims']}",
            f"Stale claims: {summary['stale_claims']}",
            f"Expired claims: {summary['expired_claims']}",
            f"Failed outcomes: {summary['failed_outcomes']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_capacity_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Capacity: {result.capacity_id}",
            f"Status: {result.payload['capacity_status']}",
            f"Experiments: {summary['experiments']}",
            f"Pending runs: {summary['pending_runs']}",
            f"Active claims: {summary['active_claims']}",
            f"Available slots: {summary['available_slots']}",
            f"Recommended batch size: {summary['recommended_batch_size']}",
            f"Stale claims: {summary['stale_claims']}",
            f"Active holds: {summary['active_holds']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_slo_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"SLO: {result.slo_id}",
            f"Status: {result.payload['slo_status']}",
            f"Passed: {str(result.passed).lower()}",
            f"Experiments: {summary['experiments']}",
            f"Scheduled runs: {summary['scheduled_runs']}",
            f"Completed runs: {summary['completed_runs']}",
            f"Failed outcomes: {summary['failed_outcomes']}",
            f"Findings: {summary['findings']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_mix_text(result: object) -> str:
    summary = result.payload["summary"]
    experiment = result.payload["experiment"]
    return "\n".join(
        [
            f"Model mix: {result.mix_id}",
            f"Experiment: {experiment['slug']}",
            f"Status: {result.payload['mix_status']}",
            f"Passed: {str(result.passed).lower()}",
            f"Providers: {summary['provider_count']}",
            f"Variants: {summary['variant_count']}",
            f"Scheduled runs: {summary['scheduled_runs']}",
            f"Completed outcomes: {summary['completed_outcomes']}",
            f"Findings: {summary['findings']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_snapshot_text(result: object) -> str:
    summary = result.payload["summary"]
    experiment = result.payload["experiment"]
    return "\n".join(
        [
            f"Snapshot: {result.snapshot_id}",
            f"Experiment: {experiment['slug']}",
            f"Status: {result.payload['snapshot_status']}",
            f"Changed: {str(result.changed).lower()}",
            f"Baseline: {result.payload.get('baseline_snapshot_id') or 'none'}",
            f"Artifact records: {summary['artifact_records']}",
            f"Report records: {summary['report_records']}",
            f"Changed sections: {summary['changed_sections']}",
            f"Content SHA-256: {result.payload['content_sha256']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_budget_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Budget: {result.budget_id}",
            f"Status: {result.payload['budget_status']}",
            f"Over budget: {str(result.over_budget).lower()}",
            f"Experiments: {summary['experiments']}",
            f"Outcomes: {summary['outcome_count']}",
            f"Usage records: {summary['usage_count']}",
            f"Total cost USD: {_table_number(summary.get('total_cost_usd'))}",
            f"Total tokens: {int(summary.get('total_tokens') or 0)}",
            f"Mean latency ms: {_table_number(summary.get('mean_latency_ms'))}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_drift_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Drift: {result.drift_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['drift_status']}",
            f"Drift detected: {str(result.drift_detected).lower()}",
            f"Outcomes: {summary['outcome_count']}",
            f"Windows: {summary['window_count']}",
            f"Findings: {summary['findings']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_readiness_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Experiment: {result.experiment}",
            f"Readiness: {result.readiness_id}",
            f"Status: {result.payload['readiness_status']}",
            f"Ready: {str(result.ready).lower()}",
            f"Outcomes: {summary['outcome_count']}",
            f"Failed outcomes: {summary['failed_outcomes']}",
            f"Findings: {summary['findings']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_rollout_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Experiment: {result.experiment}",
            f"Rollout: {result.rollout_id}",
            f"Status: {result.payload['rollout_status']}",
            f"Ready: {str(result.ready).lower()}",
            f"Champion: {result.payload.get('champion_variant_id')}",
            f"Candidate: {result.payload.get('candidate_variant_id') or 'none'}",
            f"Stages: {summary['stage_count']}",
            f"Final candidate share: {_table_number(summary.get('final_candidate_share'))}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_rollout_check_text(result: object) -> str:
    summary = result.payload["summary"]
    stage = result.payload["stage"]
    return "\n".join(
        [
            f"Experiment: {result.experiment}",
            f"Rollout check: {result.check_id}",
            f"Rollout: {result.rollout_id}",
            f"Decision: {result.decision}",
            f"Stage: {stage['stage_index']}",
            f"Candidate outcomes: {summary['candidate_outcome_count']}",
            f"Failed candidate outcomes: {summary['failed_candidate_outcomes']}",
            f"Metric gap: {_table_number(summary.get('metric_gap'))}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_evolve_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Experiment: {result.experiment}",
            f"Evolve: {result.evolve_id}",
            f"Status: {result.payload['evolve_status']}",
            f"Steps: {summary['step_count']}",
            f"Written steps: {summary['written_steps']}",
            f"Failed steps: {summary['failed_steps']}",
            f"Attention steps: {summary['attention_steps']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_dashboard_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Dashboard: {result.dashboard_id}",
            f"Scope: {result.payload['scope']}",
            f"Experiments: {summary['experiments']}",
            f"Runs: {summary['runs']}",
            f"Plans: {summary['plans']}",
            f"Outcomes: {summary['outcomes']}",
            f"Pending plan runs: {summary['pending_plan_runs']}",
            f"Failed outcomes: {summary['failed_outcomes']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_status_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Status: {result.status_id}",
            f"Experiments: {summary['experiments']}",
            f"Runs: {summary['runs']}",
            f"Plans: {summary['plans']}",
            f"Claims: {summary['claims']}",
            f"Dispatches: {summary['dispatches']}",
            f"Holds: {summary.get('holds', 0)}",
            f"Active holds: {summary.get('active_holds', 0)}",
            f"Quarantines: {summary.get('quarantines', 0)}",
            f"Active quarantines: {summary.get('active_quarantines', 0)}",
            f"Circuits: {summary.get('circuits', 0)}",
            f"Heartbeats: {summary['heartbeats']}",
            f"Retries: {summary['retries']}",
            f"Gates: {summary['gates']}",
            f"Failed gates: {summary['failed_gates']}",
            f"Quorums: {summary['quorums']}",
            f"Allocations: {summary['allocations']}",
            f"Routes: {summary['routes']}",
            f"Readiness: {summary['readiness']}",
            f"Rollouts: {summary['rollouts']}",
            f"Rollout checks: {summary['rollout_checks']}",
            f"Evolutions: {summary['evolutions']}",
            f"Power reports: {summary['power_reports']}",
            f"Schedules: {summary['schedules']}",
            f"Mix reports: {summary.get('mix_reports', 0)}",
            f"Snapshots: {summary.get('snapshots', 0)}",
            f"Promotions: {summary['promotions']}",
            f"Comparisons: {summary['comparisons']}",
            f"Memories: {summary['memories']}",
            f"Curricula: {summary['curricula']}",
            f"Budget reports: {summary['budget_reports']}",
            f"Capacity reports: {summary['capacity_reports']}",
            f"SLO reports: {summary['slo_reports']}",
            f"Dashboard reports: {summary['dashboard_reports']}",
            f"Ingest reports: {summary['ingest_reports']}",
            f"Orchestration reports: {summary['orchestration_reports']}",
            f"Recovery reports: {summary['recovery_reports']}",
            f"Cycle reports: {summary['cycle_reports']}",
            f"Loop reports: {summary['loop_reports']}",
            f"Scorecards: {summary['scorecards']}",
            f"Work packets: {summary['work_packets']}",
            f"Adjudications: {summary['adjudications']}",
            f"Accepted adjudications: {summary['accepted_adjudications']}",
            f"Pending plan runs: {summary['pending_plan_runs']}",
            f"Claimed plan runs: {summary['claimed_plan_runs']}",
            f"Expired claims: {summary['expired_claims']}",
            f"Failed outcomes: {summary['failed_outcomes']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_cycle_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Cycle: {result.cycle_id}",
            f"Status: {result.payload['cycle_status']}",
            f"Recovered runs: {summary['recovered_runs']}",
            f"Dispatched runs: {summary['dispatched_runs']}",
            f"Pending plan runs: {summary['pending_plan_runs']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_loop_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Loop: {result.loop_id}",
            f"Status: {result.payload['loop_status']}",
            f"Executed cycles: {summary['executed_cycles']}/{summary['requested_cycles']}",
            f"Stop reason: {summary['stop_reason']}",
            f"Recovered runs: {summary['recovered_runs']}",
            f"Dispatched runs: {summary['dispatched_runs']}",
            f"Pending plan runs: {summary['pending_plan_runs']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_outcome_text(result: object) -> str:
    return "\n".join(
        [
            f"Run: {result.run_id}",
            f"Experiment: {result.experiment}",
            f"Variant: {result.variant_id}",
            f"Status: {result.payload['status']}",
            f"Wrote: {result.path}",
        ]
    )


def format_agent_scorecard_text(result: object) -> str:
    return "\n".join(
        [
            f"Scorecard: {result.scorecard_id}",
            f"Run: {result.run_id}",
            f"Experiment: {result.experiment}",
            f"Variant: {result.variant_id}",
            f"Aggregate: {result.payload['aggregate_metric']}={result.payload['aggregate_score']}",
            f"Outcome: {result.outcome.payload['outcome_id']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_ingest_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Ingest: {result.ingest_id}",
            f"Status: {result.payload['ingest_status']}",
            f"Failed: {str(result.failed).lower()}",
            f"Requested: {summary['requested_count']}",
            f"Ingested: {summary['ingested_count']}",
            f"Errors: {summary['error_count']}",
            f"Outcomes: {summary['outcome_count']}",
            f"Scorecards: {summary['scorecard_count']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_work_packet_text(result: object) -> str:
    variant = result.payload["variant"]
    parallel = result.payload.get("parallel")
    lane = parallel.get("lane_id") if isinstance(parallel, dict) else "none"
    return "\n".join(
        [
            f"Work packet: {result.packet_id}",
            f"Run: {result.run_id}",
            f"Experiment: {result.experiment}",
            f"Lane: {lane}",
            f"Variant: {variant['id']} ({variant['provider']}:{variant['model']})",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_improvement_text(result: object) -> str:
    winner = result.payload.get("winner_variant_id") or "none"
    return "\n".join(
        [
            f"Experiment: {result.experiment}",
            f"Loop: {result.loop_id}",
            f"Winner: {winner}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_memory_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Experiment: {result.experiment}",
            f"Memory: {result.memory_id}",
            f"Outcomes: {summary['outcome_count']}",
            f"Lessons: {summary['lesson_count']}",
            f"Failed outcomes: {summary['failed_outcomes']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_curriculum_text(result: object) -> str:
    summary = result.payload["summary"]
    next_wave = result.payload["next_wave"]
    return "\n".join(
        [
            f"Experiment: {result.experiment}",
            f"Curriculum: {result.curriculum_id}",
            f"Status: {result.payload['curriculum_status']}",
            f"Hard cases: {summary['hard_case_count']}",
            f"Failed cases: {summary['failed_case_count']}",
            f"Weak metric cases: {summary['weak_metric_case_count']}",
            f"Focus variants: {', '.join(str(item) for item in next_wave.get('focus_variants', [])) or 'none'}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_allocation_text(result: object) -> str:
    winner = result.payload.get("winner_variant_id") or "none"
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Experiment: {result.experiment}",
            f"Allocation: {result.allocation_id}",
            f"Strategy: {result.payload['strategy']}",
            f"Winner: {winner}",
            f"Measured variants: {summary['measured_variants']}/{summary['variant_count']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_route_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Experiment: {result.experiment}",
            f"Route: {result.route_id}",
            f"Lanes: {summary['measured_lanes']}/{summary['lane_count']}",
            f"Recommended routes: {summary['recommended_routes']}",
            f"Under-sampled lane variants: {summary['under_sampled_lane_variants']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_promotion_text(result: object) -> str:
    candidate = result.payload.get("candidate_variant_id") or "none"
    return "\n".join(
        [
            f"Experiment: {result.experiment}",
            f"Promotion: {result.promotion_id}",
            f"Status: {result.payload['promotion_status']}",
            f"Ready: {str(result.ready).lower()}",
            f"Champion: {result.payload['champion_variant_id']}",
            f"Candidate: {candidate}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_comparison_text(result: object) -> str:
    summary = result.payload["summary"]
    winner = result.payload.get("winner_variant_id") or "none"
    return "\n".join(
        [
            f"Comparison: {result.comparison_id}",
            f"Experiment: {result.experiment}",
            f"Baseline: {result.payload['baseline_variant_id']}",
            f"Winner: {winner}",
            f"Eligible variants: {summary['eligible_variant_count']}/{summary['variant_count']}",
            f"Beats baseline: {summary['beats_baseline']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_decision_text(result: object) -> str:
    summary = result.payload["summary"]
    candidate = result.payload.get("candidate_variant_id") or "none"
    return "\n".join(
        [
            f"Decision: {result.decision_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['decision_status']}",
            f"Action: {result.payload['decision']}",
            f"Baseline: {result.payload['baseline_variant_id']}",
            f"Candidate: {candidate}",
            f"Confidence: {_table_number(summary.get('confidence'))}",
            f"Directional delta: {_table_number(summary.get('directional_delta'))}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_balance_text(result: object) -> str:
    summary = result.payload["summary"]
    policy = result.payload["policy"]
    return "\n".join(
        [
            f"Balance: {result.balance_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['balance_status']}",
            f"Balanced: {str(result.balanced).lower()}",
            f"Dimensions: {','.join(str(item) for item in policy['dimensions'])}",
            f"Cells: {summary['cell_count']}",
            f"Completed runs: {summary['completed_runs']}/{summary['expected_runs']}",
            f"Sample skew: {summary['sample_skew']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_power_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Power: {result.power_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['power_status']}",
            f"Baseline: {result.payload['baseline_variant_id']}",
            f"Candidates: {summary['candidate_count']}",
            f"Ready candidates: {summary['ready_candidates']}",
            f"Total additional samples: {summary['total_additional_samples']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_schedule_text(result: object) -> str:
    summary = result.payload["summary"]
    return "\n".join(
        [
            f"Schedule: {result.schedule_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['schedule_status']}",
            f"Plan: {result.plan_id or 'none'}",
            f"Requested runs: {summary['requested_runs']}",
            f"Scheduled runs: {summary['scheduled_runs']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_schedule_report_text(result: object) -> str:
    summary = result.payload["summary"]
    winner = result.payload.get("winner_variant_id") or "none"
    return "\n".join(
        [
            f"Schedule report: {result.report_id}",
            f"Schedule: {result.schedule_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['report_status']}",
            f"Winner: {winner}",
            f"Complete blocks: {summary['complete_blocks']}/{summary['block_count']}",
            f"Paired comparisons: {summary['paired_comparisons']}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_leaderboard_text(result: object) -> str:
    summary = result.payload["summary"]
    winner = result.payload.get("winner_variant_id") or "none"
    return "\n".join(
        [
            f"Leaderboard: {result.leaderboard_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['leaderboard_status']}",
            f"Winner: {winner}",
            f"Measured variants: {summary['measured_variants']}/{summary['variant_count']}",
            f"Evidence sources: {summary['evidence_sources']}",
            f"Top score: {_table_number(summary.get('top_score'))}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )


def format_agent_config_text(result: object) -> str:
    summary = result.payload["summary"]
    source = result.payload["source"] if isinstance(result.payload.get("source"), dict) else {}
    return "\n".join(
        [
            f"Config proposal: {result.config_id}",
            f"Experiment: {result.experiment}",
            f"Status: {result.payload['config_status']}",
            f"Source: {source.get('selected') or source.get('requested') or 'unknown'}",
            f"Patch operations: {summary['operation_count']}",
            f"Changed weights: {summary['changed_weight_count']}",
            f"Config: {result.config_path}",
            f"Wrote: {result.path}",
            f"Report: {result.report_path}",
        ]
    )
