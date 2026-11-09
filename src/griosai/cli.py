from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis_schema import (
    AnalysisValidationError,
    analysis_input_schema_json,
    format_analysis_validation_json,
    format_analysis_validation_text,
    require_valid_analysis_payload,
    validate_analysis_payload,
    validation_exit_code,
)
from .agent_harness import (
    CLAIM_STRATEGIES,
    adjudicate_agent_plan,
    allocate_agent_traffic,
    assess_agent_readiness,
    audit_agent_harness,
    balance_agent_experiment,
    budget_agent_harness,
    check_agent_rollout_stage,
    claim_agent_run,
    compare_agent_experiment,
    curate_agent_curriculum,
    decide_agent_experiment,
    detect_agent_drift,
    advance_agent_pipeline,
    create_agent_arena,
    create_agent_judge_panel,
    create_agent_pipeline,
    create_agent_curriculum_plan,
    create_agent_run,
    create_agent_suite_plan,
    cycle_agent_harness,
    dispatch_agent_plan,
    evaluate_agent_circuit,
    evaluate_agent_mix,
    evaluate_agent_slo,
    evolve_agent_experiment,
    gate_agent_plan,
    format_agent_adjudication_text,
    format_agent_allocation_text,
    format_agent_arena_report_text,
    format_agent_arena_text,
    format_agent_audit_text,
    format_agent_balance_text,
    format_agent_budget_text,
    format_agent_capacity_text,
    format_agent_circuit_text,
    format_agent_config_text,
    format_agent_comparison_text,
    format_agent_cycle_text,
    format_agent_curriculum_text,
    format_agent_dashboard_text,
    format_agent_decision_text,
    format_agent_dispatch_text,
    format_agent_drift_text,
    format_agent_evolve_text,
    format_agent_watchdog_text,
    format_agent_improvement_text,
    format_agent_claim_text,
    format_agent_gate_text,
    format_agent_hold_text,
    format_agent_heartbeat_text,
    format_agent_ingest_text,
    format_agent_judge_panel_report_text,
    format_agent_judge_panel_text,
    format_agent_leaderboard_text,
    format_agent_loop_text,
    format_agent_manifest_text,
    format_agent_manifest_verification_text,
    format_agent_memory_text,
    format_agent_merge_text,
    format_agent_mix_text,
    format_agent_orchestration_text,
    format_agent_outcome_text,
    format_agent_plan_text,
    format_agent_pipeline_advance_text,
    format_agent_pipeline_text,
    format_agent_power_text,
    format_agent_preflight_text,
    format_agent_promotion_text,
    format_agent_quarantine_text,
    format_agent_quorum_text,
    format_agent_readiness_text,
    format_agent_recovery_text,
    format_agent_retry_text,
    format_agent_rollout_check_text,
    format_agent_rollout_text,
    format_agent_route_text,
    format_agent_run_text,
    format_agent_scorecard_text,
    format_agent_schedule_report_text,
    format_agent_schedule_text,
    format_agent_slo_text,
    format_agent_snapshot_text,
    format_agent_status_text,
    format_agent_suite_report_text,
    format_agent_suite_text,
    format_agent_timeline_text,
    format_agent_work_packet_text,
    improve_agent_experiment,
    heartbeat_agent_claim,
    hold_agent_experiment,
    ingest_agent_results,
    loop_agent_harness,
    merge_agent_plan,
    orchestrate_agent_dispatch,
    create_agent_matrix_plan,
    create_agent_plan,
    log_agent_outcome,
    plan_agent_capacity,
    plan_agent_power,
    plan_agent_rollout,
    preflight_agent_harness,
    propose_agent_config,
    promote_agent_experiment,
    quorum_agent_plan,
    remember_agent_experiment,
    report_agent_arena,
    report_agent_judge_panel,
    report_agent_schedule,
    report_agent_suite,
    recover_agent_harness,
    release_agent_quarantine,
    release_agent_hold,
    retry_agent_run,
    route_agent_lanes,
    schedule_agent_batch,
    score_agent_run,
    quarantine_agent_slice,
    summarize_agent_harness,
    timeline_agent_harness,
    watchdog_agent_harness,
    write_agent_dashboard,
    write_agent_leaderboard,
    write_agent_manifest,
    write_agent_snapshot,
    write_agent_work_packet,
    verify_agent_manifest,
)
from .brain import AnalysisRecord, ensure_vault, slugify, write_analysis_note
from .broker import CredentialBroker, CredentialBrokerError
from .config import GriosConfig
from .dashboard import write_dashboard
from .doctor import doctor_exit_code, format_doctor_json, format_doctor_text, run_doctor
from .lineage import (
    format_lineage_json,
    format_lineage_text,
    lineage_exit_code,
    verify_lineage,
    write_lineage_manifest,
)
from .mlflow_client import (
    STATUS_FINALIZE_FAILED,
    MlflowConfig,
    MlflowError,
    log_analysis_to_mlflow,
)
from .notebook import NotebookConnectorAdapter, NotebookPacketError
from .obsidian import ObsidianConfig, ObsidianError, publish_analysis_to_obsidian
from .ollama_client import (
    DEFAULT_IMAGE_PROMPT,
    ImageTooLargeError,
    OllamaError,
    UnsupportedImageError,
    analyze_image,
)
from .openapi import openapi_json
from .server import create_sample, run_server
from .vault_archive import VaultArchiveError, backup_vault, restore_vault, verify_backup
from .vault_audit import audit_exit_code, audit_vault, format_audit_json, format_audit_text


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except KeyboardInterrupt:
        print("error: interrupted", file=sys.stderr)
        return 130
    except _CLI_USER_ERRORS as exc:
        print(_format_cli_error(exc), file=sys.stderr)
        return 1


def _main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        vault = ensure_vault(Path(args.vault))
        print(f"Initialized GriosAI vault at {vault}")
        return 0
    if args.command == "sample":
        note, dashboard, lineage = create_sample(Path(args.vault))
        print(f"Wrote note: {note}")
        print(f"Wrote dashboard: {dashboard}")
        print(f"Wrote lineage: {lineage}")
        return 0
    if args.command == "analyze-image":
        config = GriosConfig.from_env(
            vault_dir=args.vault,
            ollama_url=args.ollama_url,
            vision_model=args.model,
        )
        record = analyze_image(
            Path(args.image),
            model=config.vision_model,
            ollama_url=config.ollama_url,
            prompt=args.prompt,
        )
        artifact_slug = slugify(args.slug or record.title)
        note = write_analysis_note(config.vault_dir, record, slug=artifact_slug)
        dashboard = write_dashboard(config.vault_dir, record, slug=artifact_slug)
        lineage = write_lineage_manifest(
            config.vault_dir,
            record,
            artifacts={"dashboard": dashboard, "note": note},
            slug=args.slug,
        )
        print(f"Wrote note: {note}")
        print(f"Wrote dashboard: {dashboard}")
        print(f"Wrote lineage: {lineage}")
        return 0
    if args.command == "add-analysis":
        payload = _load_json_payload(args.json_file)
        record = AnalysisRecord.from_mapping(payload, model="manual")
        artifact_slug = slugify(args.slug or record.title)
        note = write_analysis_note(Path(args.vault), record, slug=artifact_slug)
        dashboard = write_dashboard(Path(args.vault), record, slug=artifact_slug)
        lineage = write_lineage_manifest(
            Path(args.vault),
            record,
            artifacts={"dashboard": dashboard, "note": note},
            slug=args.slug,
        )
        print(f"Wrote note: {note}")
        print(f"Wrote dashboard: {dashboard}")
        print(f"Wrote lineage: {lineage}")
        return 0
    if args.command == "notebook-packet":
        payload = _load_json_payload(args.json_file)
        record = AnalysisRecord.from_mapping(payload, model="manual")
        packet_root = Path(args.packet_root) if args.packet_root else None
        adapter = NotebookConnectorAdapter(Path(args.vault), packet_root=packet_root)
        packet = adapter.write_packet(record, slug=args.slug)
        print(f"Wrote notebook packet: {packet.packet_dir}")
        print(json.dumps(packet.connector_payload(), indent=2))
        return 0
    if args.command == "obsidian-sync":
        payload = _load_json_payload(args.json_file)
        record = AnalysisRecord.from_mapping(payload, model="manual")
        verify_tls = False if args.insecure_skip_tls_verify else None
        result = publish_analysis_to_obsidian(
            ObsidianConfig.from_env(
                url=args.obsidian_url,
                api_key=args.obsidian_api_key,
                verify_tls=verify_tls,
            ),
            record,
            folder=args.folder,
            slug=args.slug,
            overwrite=args.overwrite,
        )
        action = "Replaced" if result.replaced else "Wrote"
        print(f"{action} Obsidian note: {result.path}")
        return 0
    if args.command == "mlflow-log":
        payload = _load_json_payload(args.json_file)
        record = AnalysisRecord.from_mapping(payload, model="manual")
        result = log_analysis_to_mlflow(
            MlflowConfig.from_env(
                tracking_uri=args.tracking_uri,
                experiment_name=args.experiment,
                tracking_token=args.tracking_token,
                allow_remote=True if args.allow_remote_tracking else None,
            ),
            record,
            slug=args.slug,
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 1 if result.status == STATUS_FINALIZE_FAILED else 0
    if args.command == "agent-run":
        config = _load_json_object(args.config_file)
        prompt_text = _load_optional_text(args.prompt_file)
        result = create_agent_run(
            Path(args.vault),
            config,
            subject_key=args.subject,
            prompt_text=prompt_text,
            prompt_source_name=args.prompt_file,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_run_text(result)
        )
        return 0
    if args.command == "agent-plan":
        config = _load_json_object(args.config_file)
        prompt_text = _load_optional_text(args.prompt_file)
        result = create_agent_plan(
            Path(args.vault),
            config,
            subject_key=args.subject,
            prompt_text=prompt_text,
            prompt_source_name=args.prompt_file,
            lanes=_parse_csv_tuple(args.lanes),
            replicas=args.replicas,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_plan_text(result)
        )
        return 0
    if args.command == "agent-matrix":
        config = _load_json_object(args.config_file)
        prompt_text = _load_optional_text(args.prompt_file)
        result = create_agent_matrix_plan(
            Path(args.vault),
            config,
            subject_key=args.subject,
            prompt_text=prompt_text,
            prompt_source_name=args.prompt_file,
            lanes=_parse_csv_tuple(args.lanes),
            replicas=args.replicas,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_plan_text(result)
        )
        return 0
    if args.command == "agent-suite":
        config = _load_json_object(args.config_file)
        suite = _load_json_object(args.suite_file)
        result = create_agent_suite_plan(
            Path(args.vault),
            config,
            suite,
            subject_prefix=args.subject_prefix,
            lanes=_parse_csv_tuple(args.lanes),
            replicas=args.replicas,
            mode=args.mode,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_suite_text(result)
        )
        return 0
    if args.command == "agent-curriculum-plan":
        config = _load_json_object(args.config_file)
        suite = _load_json_object(args.suite_file)
        result = create_agent_curriculum_plan(
            Path(args.vault),
            config,
            suite,
            subject_prefix=args.subject_prefix,
            curriculum_id=args.curriculum_id,
            baseline_variant_id=args.baseline_variant,
            variant_ids=_parse_csv_tuple(args.variants),
            lanes=_parse_csv_tuple(args.lanes),
            replicas=args.replicas,
            max_cases=args.max_cases,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_suite_text(result)
        )
        return 0
    if args.command == "agent-suite-report":
        result = report_agent_suite(
            Path(args.vault),
            suite_id=args.suite_id,
            baseline_variant_id=args.baseline_variant,
            min_completed_ratio=args.min_completed_ratio,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_suite_report_text(result)
        )
        return 0
    if args.command == "agent-pipeline":
        config = _load_json_object(args.config_file)
        pipeline = _load_json_object(args.pipeline_file)
        prompt_text = _load_optional_text(args.prompt_file)
        result = create_agent_pipeline(
            Path(args.vault),
            config,
            pipeline,
            subject_prefix=args.subject_prefix,
            prompt_text=prompt_text,
            prompt_source_name=args.prompt_file,
            schedule_initial=not args.no_schedule_initial,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_pipeline_text(result)
        )
        return 0
    if args.command == "agent-pipeline-advance":
        result = advance_agent_pipeline(
            Path(args.vault),
            pipeline_id=args.pipeline_id,
            max_stages=args.max_stages,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_pipeline_advance_text(result)
        )
        return 0
    if args.command == "agent-arena":
        config = _load_json_object(args.config_file)
        prompt_text = _load_optional_text(args.prompt_file)
        result = create_agent_arena(
            Path(args.vault),
            config,
            subject_key=args.subject,
            prompt_text=prompt_text,
            prompt_source_name=args.prompt_file,
            lanes=_parse_csv_tuple(args.lanes),
            replicas=args.replicas,
            max_runs=args.max_runs,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_arena_text(result)
        )
        return 0
    if args.command == "agent-arena-report":
        result = report_agent_arena(
            Path(args.vault),
            arena_id=args.arena_id,
            min_completed_ratio=args.min_completed_ratio,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_arena_report_text(result)
        )
        return 0
    if args.command == "agent-judge-panel":
        config = _load_json_object(args.config_file)
        result = create_agent_judge_panel(
            Path(args.vault),
            config,
            plan_id=args.plan_id,
            metric_name=args.metric,
            metric_direction=args.direction,
            judge_variants=_parse_csv_tuple(args.judge_variants),
            replicas=args.replicas,
            include_pending_targets=args.include_pending_targets,
            include_self_judges=args.include_self_judges,
            max_runs=args.max_runs,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_judge_panel_text(result)
        )
        return 0
    if args.command == "agent-judge-report":
        result = report_agent_judge_panel(
            Path(args.vault),
            panel_id=args.panel_id,
            min_completed_ratio=args.min_completed_ratio,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_judge_panel_report_text(result)
        )
        return 0
    if args.command == "agent-outcome":
        metrics = _load_metrics(args.metrics_json, args.metrics_file)
        usage = _load_usage(args.usage_json, args.usage_file)
        output_text = _load_optional_text(args.output_file)
        result = log_agent_outcome(
            Path(args.vault),
            run_id=args.run_id,
            status=args.status,
            metrics=metrics,
            usage=usage,
            output_text=output_text,
            output_source_name=args.output_file,
            failure_code=args.failure_code,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_outcome_text(result)
        )
        return 0
    if args.command == "agent-score":
        scores = _load_scores(args.scores_json, args.scores_file)
        usage = _load_usage(args.usage_json, args.usage_file)
        output_text = _load_optional_text(args.output_file)
        result = score_agent_run(
            Path(args.vault),
            run_id=args.run_id,
            status=args.status,
            scores=scores,
            usage=usage,
            output_text=output_text,
            output_source_name=args.output_file,
            failure_code=args.failure_code,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_scorecard_text(result)
        )
        return 0
    if args.command == "agent-ingest":
        results = _load_json_object(args.results_file)
        result = ingest_agent_results(
            Path(args.vault),
            results,
            source_name=args.results_file,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_ingest_text(result)
        )
        return 1 if result.failed else 0
    if args.command == "agent-merge":
        result = merge_agent_plan(Path(args.vault), plan_id=args.plan_id)
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_merge_text(result)
        )
        return 0
    if args.command == "agent-claim":
        result = claim_agent_run(
            Path(args.vault),
            plan_id=args.plan_id,
            client_id=args.client_id,
            lane_id=args.lane,
            ttl_seconds=args.ttl_seconds,
            claim_strategy=args.claim_strategy,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_claim_text(result)
        )
        return 0
    if args.command == "agent-dispatch":
        result = dispatch_agent_plan(
            Path(args.vault),
            plan_id=args.plan_id,
            client_prefix=args.client_prefix,
            count=args.count,
            lane_id=args.lane,
            ttl_seconds=args.ttl_seconds,
            claim_strategy=args.claim_strategy,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_dispatch_text(result)
        )
        return 0
    if args.command == "agent-hold":
        result = hold_agent_experiment(
            Path(args.vault),
            experiment=args.experiment,
            reason=args.reason,
            scopes=_parse_csv_tuple(args.scopes),
            ttl_seconds=args.ttl_seconds,
            operator=args.operator,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_hold_text(result)
        )
        return 0
    if args.command == "agent-release":
        result = release_agent_hold(
            Path(args.vault),
            experiment=args.experiment,
            reason=args.reason,
            hold_id=args.hold_id,
            scopes=_parse_csv_tuple(args.scopes),
            operator=args.operator,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_hold_text(result)
        )
        return 0
    if args.command == "agent-quarantine":
        result = quarantine_agent_slice(
            Path(args.vault),
            experiment=args.experiment,
            reason=args.reason,
            variant_ids=_parse_csv_tuple(args.variants),
            providers=_parse_csv_tuple(args.providers),
            lanes=_parse_csv_tuple(args.lanes),
            ttl_seconds=args.ttl_seconds,
            operator=args.operator,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_quarantine_text(result)
        )
        return 0
    if args.command == "agent-circuit":
        result = evaluate_agent_circuit(
            Path(args.vault),
            experiment=args.experiment,
            group_by=args.group_by,
            min_outcomes=args.min_outcomes,
            recent_limit=args.recent_limit,
            max_failure_rate=args.max_failure_rate,
            max_mean_latency_ms=args.max_mean_latency_ms,
            max_mean_cost_usd=args.max_mean_cost_usd,
            min_primary_metric=args.min_primary_metric,
            quarantine_on_trip=args.quarantine_on_trip,
            quarantine_ttl_seconds=args.quarantine_ttl_seconds,
            operator=args.operator,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_circuit_text(result)
        )
        return 1 if result.tripped else 0
    if args.command == "agent-unquarantine":
        result = release_agent_quarantine(
            Path(args.vault),
            experiment=args.experiment,
            reason=args.reason,
            quarantine_id=args.quarantine_id,
            variant_ids=_parse_csv_tuple(args.variants),
            providers=_parse_csv_tuple(args.providers),
            lanes=_parse_csv_tuple(args.lanes),
            operator=args.operator,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_quarantine_text(result)
        )
        return 0
    if args.command == "agent-orchestrate":
        result = orchestrate_agent_dispatch(
            Path(args.vault),
            plan_id=args.plan_id,
            suite_id=args.suite_id,
            client_prefix=args.client_prefix,
            max_concurrency=args.max_concurrency,
            batch_size=args.batch_size,
            lane_id=args.lane,
            ttl_seconds=args.ttl_seconds,
            stale_after_seconds=args.stale_after_seconds,
            claim_strategy=args.claim_strategy,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_orchestration_text(result)
        )
        return 0
    if args.command == "agent-heartbeat":
        result = heartbeat_agent_claim(
            Path(args.vault),
            claim_id=args.claim_id,
            client_id=args.client_id,
            ttl_seconds=args.ttl_seconds,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_heartbeat_text(result)
        )
        return 0
    if args.command == "agent-retry":
        result = retry_agent_run(
            Path(args.vault),
            run_id=args.run_id,
            reason=args.reason,
            variant_id=args.variant_id,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_retry_text(result)
        )
        return 0
    if args.command == "agent-recover":
        result = recover_agent_harness(
            Path(args.vault),
            experiment=args.experiment,
            max_retries=args.max_retries,
            stale_after_seconds=args.stale_after_seconds,
            include_failed=not args.no_failed,
            include_stale=not args.no_stale,
            include_expired=not args.no_expired,
            variant_id=args.variant_id,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_recovery_text(result)
        )
        return 0
    if args.command == "agent-cycle":
        result = cycle_agent_harness(
            Path(args.vault),
            experiment=args.experiment,
            plan_id=args.plan_id,
            suite_id=args.suite_id,
            client_prefix=args.client_prefix,
            max_concurrency=args.max_concurrency,
            batch_size=args.batch_size,
            lane_id=args.lane,
            ttl_seconds=args.ttl_seconds,
            stale_after_seconds=args.stale_after_seconds,
            claim_strategy=args.claim_strategy,
            max_retries=args.max_retries,
            skip_recovery=args.skip_recovery,
            skip_orchestration=args.skip_orchestration,
            dashboard_limit=args.dashboard_limit,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_cycle_text(result)
        )
        return 0
    if args.command == "agent-loop":
        result = loop_agent_harness(
            Path(args.vault),
            experiment=args.experiment,
            plan_id=args.plan_id,
            suite_id=args.suite_id,
            client_prefix=args.client_prefix,
            max_concurrency=args.max_concurrency,
            batch_size=args.batch_size,
            lane_id=args.lane,
            ttl_seconds=args.ttl_seconds,
            stale_after_seconds=args.stale_after_seconds,
            claim_strategy=args.claim_strategy,
            max_retries=args.max_retries,
            max_cycles=args.max_cycles,
            stop_after_idle_cycles=args.stop_after_idle_cycles,
            skip_recovery=args.skip_recovery,
            skip_orchestration=args.skip_orchestration,
            dashboard_limit=args.dashboard_limit,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_loop_text(result)
        )
        return 0
    if args.command == "agent-work":
        result = write_agent_work_packet(
            Path(args.vault),
            run_id=args.run_id,
            claim_id=args.claim_id,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_work_packet_text(result)
        )
        return 0
    if args.command == "agent-gate":
        result = gate_agent_plan(
            Path(args.vault),
            plan_id=args.plan_id,
            min_completed_ratio=args.min_completed_ratio,
            max_failures=args.max_failures,
            metric_threshold=args.metric_threshold,
            required_lanes=tuple(args.require_lane or ()),
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_gate_text(result)
        )
        return 0 if result.passed else 1
    if args.command == "agent-adjudicate":
        result = adjudicate_agent_plan(
            Path(args.vault),
            plan_id=args.plan_id,
            min_completed_ratio=args.min_completed_ratio,
            min_consensus_ratio=args.min_consensus_ratio,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_adjudication_text(result)
        )
        return 0 if result.accepted else 1
    if args.command == "agent-quorum":
        result = quorum_agent_plan(
            Path(args.vault),
            plan_id=args.plan_id,
            min_completed_ratio=args.min_completed_ratio,
            min_agreement_ratio=args.min_agreement_ratio,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_quorum_text(result)
        )
        return 0 if result.passed else 1
    if args.command == "agent-audit":
        result = audit_agent_harness(
            Path(args.vault),
            experiment=args.experiment,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_audit_text(result)
        )
        return 1 if result.failed else 0
    if args.command == "agent-manifest":
        result = write_agent_manifest(
            Path(args.vault),
            experiment=args.experiment,
            include_reports=args.include_reports,
            max_artifacts=args.max_artifacts,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_manifest_text(result)
        )
        return 0
    if args.command == "agent-verify-manifest":
        result = verify_agent_manifest(
            Path(args.vault),
            manifest_id=args.manifest_id,
            fail_on_extra=args.fail_on_extra,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_manifest_verification_text(result)
        )
        return 0 if result.verified else 1
    if args.command == "agent-preflight":
        result = preflight_agent_harness(
            Path(args.vault),
            experiment=args.experiment,
            plan_id=args.plan_id,
            suite_id=args.suite_id,
            min_pending_runs=args.min_pending_runs,
            max_active_claims=args.max_active_claims,
            stale_after_seconds=args.stale_after_seconds,
            require_cross_model=args.require_cross_model,
            require_lane_coverage=args.require_lane_coverage,
            require_variant_coverage=args.require_variant_coverage,
            max_pending_skew=args.max_pending_skew,
            block_failed_outcomes=args.block_failed_outcomes,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_preflight_text(result)
        )
        return 0 if result.ready else 1
    if args.command == "agent-compare":
        result = compare_agent_experiment(
            Path(args.vault),
            experiment=args.experiment,
            baseline_variant_id=args.baseline_variant,
            min_samples_per_variant=args.min_samples_per_variant,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_comparison_text(result)
        )
        return 0
    if args.command == "agent-decision":
        result = decide_agent_experiment(
            Path(args.vault),
            experiment=args.experiment,
            baseline_variant_id=args.baseline_variant,
            candidate_variant_id=args.candidate_variant,
            min_samples_per_variant=args.min_samples_per_variant,
            min_delta=args.min_delta,
            confidence_threshold=args.confidence_threshold,
            max_cost_usd=args.max_cost_usd,
            max_total_tokens=args.max_total_tokens,
            candidate_metric_floor=args.candidate_metric_floor,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_decision_text(result)
        )
        return 0
    if args.command == "agent-balance":
        result = balance_agent_experiment(
            Path(args.vault),
            experiment=args.experiment,
            suite_id=args.suite_id,
            plan_id=args.plan_id,
            dimensions=_parse_csv_tuple(args.dimensions) or ("variant", "lane"),
            min_count_per_cell=args.min_count_per_cell,
            max_skew=args.max_skew,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_balance_text(result)
        )
        return 0
    if args.command == "agent-timeline":
        result = timeline_agent_harness(
            Path(args.vault),
            experiment=args.experiment,
            limit=args.limit,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_timeline_text(result)
        )
        return 0
    if args.command == "agent-watchdog":
        result = watchdog_agent_harness(
            Path(args.vault),
            experiment=args.experiment,
            stale_after_seconds=args.stale_after_seconds,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_watchdog_text(result)
        )
        return 0
    if args.command == "agent-capacity":
        result = plan_agent_capacity(
            Path(args.vault),
            experiment=args.experiment,
            plan_id=args.plan_id,
            suite_id=args.suite_id,
            max_concurrency=args.max_concurrency,
            batch_size=args.batch_size,
            target_utilization=args.target_utilization,
            min_batch_size=args.min_batch_size,
            stale_after_seconds=args.stale_after_seconds,
            latency_window=args.latency_window,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_capacity_text(result)
        )
        return 0
    if args.command == "agent-slo":
        result = evaluate_agent_slo(
            Path(args.vault),
            experiment=args.experiment,
            plan_id=args.plan_id,
            suite_id=args.suite_id,
            min_completion_rate=args.min_completion_rate,
            max_failure_rate=args.max_failure_rate,
            max_stale_claims=args.max_stale_claims,
            max_expired_claims=args.max_expired_claims,
            max_active_claims=args.max_active_claims,
            max_quarantined_pending_runs=args.max_quarantined_pending_runs,
            max_mean_latency_ms=args.max_mean_latency_ms,
            require_no_active_holds=not args.allow_active_holds,
            require_no_active_quarantines=not args.allow_active_quarantines,
            stale_after_seconds=args.stale_after_seconds,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_slo_text(result)
        )
        return 0 if result.passed else 1
    if args.command == "agent-mix":
        result = evaluate_agent_mix(
            Path(args.vault),
            experiment=args.experiment,
            min_provider_count=args.min_provider_count,
            min_variant_count=args.min_variant_count,
            max_provider_weight_share=args.max_provider_weight_share,
            max_scheduled_provider_share=args.max_scheduled_provider_share,
            max_completed_provider_share=args.max_completed_provider_share,
            require_local_provider=args.require_local_provider,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_mix_text(result)
        )
        return 0 if result.passed else 1
    if args.command == "agent-snapshot":
        result = write_agent_snapshot(
            Path(args.vault),
            experiment=args.experiment,
            baseline_snapshot_id=args.baseline_snapshot_id,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_snapshot_text(result)
        )
        return 1 if args.fail_on_change and result.changed else 0
    if args.command == "agent-budget":
        result = budget_agent_harness(
            Path(args.vault),
            experiment=args.experiment,
            max_cost_usd=args.max_cost_usd,
            max_total_tokens=args.max_total_tokens,
            max_mean_latency_ms=args.max_mean_latency_ms,
            max_run_cost_usd=args.max_run_cost_usd,
            max_run_tokens=args.max_run_tokens,
            max_run_latency_ms=args.max_run_latency_ms,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_budget_text(result)
        )
        return 1 if result.over_budget else 0
    if args.command == "agent-drift":
        result = detect_agent_drift(
            Path(args.vault),
            experiment=args.experiment,
            metric_name=args.metric,
            baseline_window=args.baseline_window,
            recent_window=args.recent_window,
            min_samples=args.min_samples,
            max_metric_drop=args.max_metric_drop,
            max_cost_increase_ratio=args.max_cost_increase_ratio,
            max_latency_increase_ratio=args.max_latency_increase_ratio,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_drift_text(result)
        )
        return 1 if result.drift_detected else 0
    if args.command == "agent-readiness":
        result = assess_agent_readiness(
            Path(args.vault),
            experiment=args.experiment,
            min_outcomes=args.min_outcomes,
            max_failed_outcomes=args.max_failed_outcomes,
            require_comparison=args.require_comparison,
            require_budget=args.require_budget,
            require_route=args.require_route,
            require_memory=args.require_memory,
            require_quorum=args.require_quorum,
            require_promotion=args.require_promotion,
            require_balance=args.require_balance,
            require_drift=args.require_drift,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_readiness_text(result)
        )
        return 0 if result.ready else 1
    if args.command == "agent-rollout":
        result = plan_agent_rollout(
            Path(args.vault),
            experiment=args.experiment,
            candidate_variant_id=args.candidate_variant,
            champion_variant_id=args.champion_variant,
            stages=_parse_float_tuple(args.stages),
            min_observation_runs=args.min_observation_runs,
            max_stage_failed_outcomes=args.max_stage_failed_outcomes,
            require_readiness=args.require_readiness,
            require_promotion=args.require_promotion,
            require_budget=args.require_budget,
            require_drift=args.require_drift,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_rollout_text(result)
        )
        return 0 if result.ready else 1
    if args.command == "agent-rollout-check":
        result = check_agent_rollout_stage(
            Path(args.vault),
            rollout_id=args.rollout_id,
            stage_index=args.stage_index,
            min_stage_outcomes=args.min_stage_outcomes,
            max_stage_failed_outcomes=args.max_stage_failed_outcomes,
            max_share_deviation=args.max_share_deviation,
            min_metric_delta=args.min_metric_delta,
            require_budget=args.require_budget,
            require_readiness=args.require_readiness,
            require_drift=args.require_drift,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_rollout_check_text(result)
        )
        return 0 if result.decision == "advance" else 1
    if args.command == "agent-evolve":
        result = evolve_agent_experiment(
            Path(args.vault),
            experiment=args.experiment,
            min_trials_per_variant=args.min_trials_per_variant,
            min_samples_per_variant=args.min_samples_per_variant,
            max_lessons=args.max_lessons,
            allocation_strategy=args.allocation_strategy,
            route_strategy=args.route_strategy,
            exploration_floor=args.exploration_floor,
            max_share=args.max_share,
            cost_penalty=args.cost_penalty,
            champion_variant_id=args.champion_variant,
            min_delta=args.min_delta,
            max_cost_usd=args.max_cost_usd,
            max_total_tokens=args.max_total_tokens,
            max_mean_latency_ms=args.max_mean_latency_ms,
            require_budget=args.require_budget,
            require_route=args.require_route,
            require_drift=args.require_drift,
            plan_rollout=args.plan_rollout,
            rollout_stages=_parse_float_tuple(args.rollout_stages),
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_evolve_text(result)
        )
        return 1 if result.failed else 0
    if args.command == "agent-power":
        result = plan_agent_power(
            Path(args.vault),
            experiment=args.experiment,
            baseline_variant_id=args.baseline_variant,
            min_detectable_effect=args.min_detectable_effect,
            alpha=args.alpha,
            power=args.power,
            fallback_stddev=args.fallback_stddev,
            max_cost_usd=args.max_cost_usd,
            max_total_tokens=args.max_total_tokens,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_power_text(result)
        )
        return 0
    if args.command == "agent-schedule":
        result = schedule_agent_batch(
            Path(args.vault),
            experiment=args.experiment,
            subject_key=args.subject,
            lanes=_parse_csv_tuple(args.lanes),
            max_runs=args.max_runs,
            power_id=args.power_id,
            include_budget_limited=args.include_budget_limited,
            paired=not args.unpaired,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_schedule_text(result)
        )
        return 0
    if args.command == "agent-schedule-report":
        result = report_agent_schedule(
            Path(args.vault),
            schedule_id=args.schedule_id,
            min_completed_blocks_ratio=args.min_completed_blocks_ratio,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_schedule_report_text(result)
        )
        return 0
    if args.command == "agent-dashboard":
        result = write_agent_dashboard(
            Path(args.vault),
            experiment=args.experiment,
            limit=args.limit,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_dashboard_text(result)
        )
        return 0
    if args.command == "agent-leaderboard":
        result = write_agent_leaderboard(
            Path(args.vault),
            experiment=args.experiment,
            baseline_variant_id=args.baseline_variant,
            min_samples_per_variant=args.min_samples_per_variant,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_leaderboard_text(result)
        )
        return 0
    if args.command == "agent-config":
        result = propose_agent_config(
            Path(args.vault),
            experiment=args.experiment,
            source=args.source,
            exploration_floor=args.exploration_floor,
            max_share=args.max_share,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_config_text(result)
        )
        return 0
    if args.command == "agent-status":
        result = summarize_agent_harness(
            Path(args.vault),
            experiment=args.experiment,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_status_text(result)
        )
        return 0
    if args.command == "agent-improve":
        result = improve_agent_experiment(
            Path(args.vault),
            experiment=args.experiment,
            min_trials_per_variant=args.min_trials_per_variant,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_improvement_text(result)
        )
        return 0
    if args.command == "agent-memory":
        result = remember_agent_experiment(
            Path(args.vault),
            experiment=args.experiment,
            min_trials_per_variant=args.min_trials_per_variant,
            max_lessons=args.max_lessons,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_memory_text(result)
        )
        return 0
    if args.command == "agent-curriculum":
        result = curate_agent_curriculum(
            Path(args.vault),
            experiment=args.experiment,
            metric_threshold=args.metric_threshold,
            max_cases=args.max_cases,
            include_failed=not args.exclude_failed,
            include_low_metric=not args.exclude_low_metric,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_curriculum_text(result)
        )
        return 0
    if args.command == "agent-allocate":
        result = allocate_agent_traffic(
            Path(args.vault),
            experiment=args.experiment,
            strategy=args.strategy,
            exploration_floor=args.exploration_floor,
            max_share=args.max_share,
            min_trials_per_variant=args.min_trials_per_variant,
            cost_penalty=args.cost_penalty,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_allocation_text(result)
        )
        return 0
    if args.command == "agent-route":
        result = route_agent_lanes(
            Path(args.vault),
            experiment=args.experiment,
            strategy=args.strategy,
            exploration_floor=args.exploration_floor,
            max_share=args.max_share,
            min_trials_per_lane_variant=args.min_trials_per_lane_variant,
            cost_penalty=args.cost_penalty,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_route_text(result)
        )
        return 0
    if args.command == "agent-promote":
        result = promote_agent_experiment(
            Path(args.vault),
            experiment=args.experiment,
            champion_variant_id=args.champion_variant,
            min_trials_per_variant=args.min_trials_per_variant,
            min_delta=args.min_delta,
            require_passing_gate=args.require_passing_gate,
            require_suite_report=args.require_suite_report,
            require_pareto=args.require_pareto,
            require_budget=args.require_budget,
            require_balance=args.require_balance,
            require_drift=args.require_drift,
        )
        print(
            json.dumps(result.as_dict(), indent=2, sort_keys=True)
            if args.json
            else format_agent_promotion_text(result)
        )
        return 0
    if args.command == "backup":
        result = backup_vault(
            Path(args.vault),
            output_path=Path(args.output) if args.output else None,
            overwrite=args.overwrite,
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0
    if args.command == "restore":
        result = restore_vault(
            Path(args.archive),
            vault_dir=Path(args.vault),
            overwrite=args.overwrite,
        )
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0
    if args.command == "verify-backup":
        result = verify_backup(Path(args.archive))
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
        return 0
    if args.command == "openapi":
        print(openapi_json())
        return 0
    if args.command == "analysis-schema":
        print(analysis_input_schema_json())
        return 0
    if args.command == "validate-analysis":
        payload, source_bytes = _load_raw_json_payload(args.json_file)
        findings = validate_analysis_payload(payload, source_bytes=source_bytes)
        print(format_analysis_validation_json(findings) if args.json else format_analysis_validation_text(findings))
        return validation_exit_code(findings)
    if args.command == "credential-lease":
        lease = CredentialBroker().issue_env_lease(
            secret_name=args.secret_name,
            env_var=args.env_var,
            scopes=tuple(args.scope),
            client_id=args.client_id,
            ttl_seconds=args.ttl_seconds,
        )
        print(json.dumps(lease.audit_record(), indent=2, sort_keys=True))
        return 0
    if args.command == "doctor":
        checks = run_doctor(
            vault_dir=Path(args.vault) if args.vault else None,
            repo_dir=Path(args.repo) if args.repo else None,
        )
        print(format_doctor_json(checks) if args.json else format_doctor_text(checks))
        return doctor_exit_code(checks)
    if args.command == "vault-audit":
        audit = audit_vault(Path(args.vault))
        print(format_audit_json(audit) if args.json else format_audit_text(audit))
        return audit_exit_code(audit)
    if args.command == "lineage-verify":
        verification = verify_lineage(Path(args.vault))
        print(format_lineage_json(verification) if args.json else format_lineage_text(verification))
        return lineage_exit_code(verification)
    if args.command == "serve":
        config = GriosConfig.from_env(
            vault_dir=args.vault,
            host=args.host,
            port=args.port,
            ollama_url=args.ollama_url,
            vision_model=args.model,
            api_token=args.api_token,
            allowed_hosts=tuple(args.allow_host) if args.allow_host else None,
        )
        run_server(config)
        return 0
    parser.print_help()
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="griosai")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create the local vault layout")
    init.add_argument("--vault", required=True, help="Vault directory")

    sample = subparsers.add_parser("sample", help="Write a sample dashboard")
    sample.add_argument("--vault", required=True, help="Vault directory")

    analyze = subparsers.add_parser("analyze-image", help="Analyze an image through local Ollama")
    analyze.add_argument("image", help="Image path")
    analyze.add_argument("--vault", required=True, help="Vault directory")
    analyze.add_argument("--model", default=None, help="Ollama vision model")
    analyze.add_argument("--ollama-url", default=None, help="Ollama base URL")
    analyze.add_argument("--prompt", default=DEFAULT_IMAGE_PROMPT, help="Vision prompt")
    analyze.add_argument("--slug", default=None, help="Output slug")

    add_analysis = subparsers.add_parser("add-analysis", help="Import manual analysis JSON")
    add_analysis.add_argument("--vault", required=True, help="Vault directory")
    add_analysis.add_argument(
        "--json-file",
        default="-",
        help="JSON file to import, or '-' for stdin",
    )
    add_analysis.add_argument("--slug", default=None, help="Output slug")

    notebook = subparsers.add_parser(
        "notebook-packet",
        help="Create a sanitized NotebookLM-ready source packet",
    )
    notebook.add_argument("--vault", required=True, help="Vault directory")
    notebook.add_argument(
        "--json-file",
        default="-",
        help="Analysis JSON file to packetize, or '-' for stdin",
    )
    notebook.add_argument("--slug", default=None, help="Packet slug")
    notebook.add_argument(
        "--packet-root",
        default=None,
        help="Optional packet root inside the selected vault",
    )

    obsidian = subparsers.add_parser(
        "obsidian-sync",
        help="Write an analysis note through Obsidian Local REST API",
    )
    obsidian.add_argument(
        "--json-file",
        default="-",
        help="Analysis JSON file to sync, or '-' for stdin",
    )
    obsidian.add_argument(
        "--folder",
        default="GriosAI/notes",
        help="Relative Obsidian folder for synced notes",
    )
    obsidian.add_argument("--slug", default=None, help="Output slug")
    obsidian.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the existing Obsidian note instead of allocating a unique path",
    )
    obsidian.add_argument("--obsidian-url", default=None, help="Local Obsidian REST URL")
    obsidian.add_argument("--obsidian-api-key", default=None, help="Local Obsidian REST API key")
    obsidian.add_argument(
        "--insecure-skip-tls-verify",
        action="store_true",
        help="Allow a localhost self-signed Obsidian certificate",
    )

    mlflow = subparsers.add_parser(
        "mlflow-log",
        help="Log privacy-preserving analysis metadata to an MLflow Tracking server",
    )
    mlflow.add_argument(
        "--json-file",
        default="-",
        help="Analysis JSON file to track, or '-' for stdin",
    )
    mlflow.add_argument("--slug", default=None, help="Run slug")
    mlflow.add_argument("--tracking-uri", default=None, help="MLflow Tracking server URI")
    mlflow.add_argument("--experiment", default=None, help="MLflow experiment name")
    mlflow.add_argument(
        "--tracking-token",
        default=None,
        help="Optional bearer token for an authenticated MLflow proxy",
    )
    mlflow.add_argument(
        "--allow-remote-tracking",
        action="store_true",
        help="Allow non-localhost MLflow Tracking URIs",
    )

    agent_run = subparsers.add_parser(
        "agent-run",
        help="Assign a cross-model agent variant and write metadata-only run logs",
    )
    agent_run.add_argument("--vault", required=True, help="Vault directory")
    agent_run.add_argument("--config-file", required=True, help="Agent experiment JSON file")
    agent_run.add_argument(
        "--subject",
        required=True,
        help="Stable assignment key; hashed before it is written to the vault",
    )
    agent_run.add_argument(
        "--prompt-file",
        default=None,
        help="Optional prompt file to hash for metadata; raw prompt text is not logged",
    )
    agent_run.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_plan = subparsers.add_parser(
        "agent-plan",
        help="Create a parallel agent execution plan with lane-specific child runs",
    )
    agent_plan.add_argument("--vault", required=True, help="Vault directory")
    agent_plan.add_argument("--config-file", required=True, help="Agent experiment JSON file")
    agent_plan.add_argument(
        "--subject",
        required=True,
        help="Stable plan key; hashed before it is written to the vault",
    )
    agent_plan.add_argument(
        "--prompt-file",
        default=None,
        help="Optional prompt file to hash for metadata; raw prompt text is not logged",
    )
    agent_plan.add_argument(
        "--lanes",
        default=None,
        help="Comma-separated lane override, for example scout,implementer,reviewer",
    )
    agent_plan.add_argument(
        "--replicas",
        type=int,
        default=None,
        help="Optional replica count per lane",
    )
    agent_plan.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_matrix = subparsers.add_parser(
        "agent-matrix",
        help="Create a controlled variant-by-lane matrix plan for cross-model benchmarks",
    )
    agent_matrix.add_argument("--vault", required=True, help="Vault directory")
    agent_matrix.add_argument("--config-file", required=True, help="Agent experiment JSON file")
    agent_matrix.add_argument(
        "--subject",
        required=True,
        help="Stable matrix key; hashed before it is written to the vault",
    )
    agent_matrix.add_argument(
        "--prompt-file",
        default=None,
        help="Optional prompt file to hash for metadata; raw prompt text is not logged",
    )
    agent_matrix.add_argument(
        "--lanes",
        default=None,
        help="Comma-separated lane override, for example scout,implementer,reviewer",
    )
    agent_matrix.add_argument(
        "--replicas",
        type=int,
        default=None,
        help="Optional replica count per variant per lane",
    )
    agent_matrix.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_suite = subparsers.add_parser(
        "agent-suite",
        help="Create case-suite fanout plans for controlled cross-model experiments",
    )
    agent_suite.add_argument("--vault", required=True, help="Vault directory")
    agent_suite.add_argument("--config-file", required=True, help="Agent experiment JSON file")
    agent_suite.add_argument("--suite-file", required=True, help="Agent suite JSON file")
    agent_suite.add_argument(
        "--subject-prefix",
        required=True,
        help="Stable suite assignment prefix; hashed before it is written to the vault",
    )
    agent_suite.add_argument(
        "--mode",
        choices=["matrix", "weighted"],
        default="matrix",
        help="Matrix runs every variant per case; weighted uses traffic assignment",
    )
    agent_suite.add_argument(
        "--lanes",
        default=None,
        help="Comma-separated lane override, for example scout,implementer,reviewer",
    )
    agent_suite.add_argument(
        "--replicas",
        type=int,
        default=None,
        help="Optional replica count per case lane",
    )
    agent_suite.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_curriculum_plan = subparsers.add_parser(
        "agent-curriculum-plan",
        help="Create a focused suite from a private suite file and a curriculum artifact",
    )
    agent_curriculum_plan.add_argument("--vault", required=True, help="Vault directory")
    agent_curriculum_plan.add_argument("--config-file", required=True, help="Agent experiment JSON file")
    agent_curriculum_plan.add_argument("--suite-file", required=True, help="Private suite JSON file containing hard-case prompts")
    agent_curriculum_plan.add_argument(
        "--subject-prefix",
        required=True,
        help="Stable rerun assignment prefix; hashed before it is written to the vault",
    )
    agent_curriculum_plan.add_argument(
        "--curriculum-id",
        default=None,
        help="Curriculum id to use; defaults to the latest curriculum for the experiment",
    )
    agent_curriculum_plan.add_argument(
        "--baseline-variant",
        default=None,
        help="Baseline variant to include with weak variants; defaults to the current champion",
    )
    agent_curriculum_plan.add_argument(
        "--variants",
        default=None,
        help="Comma-separated variant override; defaults to baseline plus curriculum focus variants",
    )
    agent_curriculum_plan.add_argument(
        "--lanes",
        default=None,
        help="Comma-separated lane override; defaults to curriculum focus lanes or config lanes",
    )
    agent_curriculum_plan.add_argument(
        "--replicas",
        type=int,
        default=None,
        help="Optional replica count per selected case lane and variant",
    )
    agent_curriculum_plan.add_argument(
        "--max-cases",
        type=int,
        default=None,
        help="Maximum matching hard cases to schedule from the suite file",
    )
    agent_curriculum_plan.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_suite_report = subparsers.add_parser(
        "agent-suite-report",
        help="Report paired case evidence for an agent suite",
    )
    agent_suite_report.add_argument("--vault", required=True, help="Vault directory")
    agent_suite_report.add_argument("--suite-id", required=True, help="Agent suite id")
    agent_suite_report.add_argument(
        "--baseline-variant",
        default=None,
        help="Variant id to compare against; defaults to the highest-weight champion",
    )
    agent_suite_report.add_argument(
        "--min-completed-ratio",
        type=float,
        default=1.0,
        help="Case completion ratio required to count as complete",
    )
    agent_suite_report.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_pipeline = subparsers.add_parser(
        "agent-pipeline",
        help="Create a dependency-aware multi-stage agent pipeline",
    )
    agent_pipeline.add_argument("--vault", required=True, help="Vault directory")
    agent_pipeline.add_argument("--config-file", required=True, help="Agent experiment JSON file")
    agent_pipeline.add_argument("--pipeline-file", required=True, help="Agent pipeline JSON file")
    agent_pipeline.add_argument(
        "--subject-prefix",
        required=True,
        help="Stable pipeline assignment prefix; hashed before it is written to the vault",
    )
    agent_pipeline.add_argument(
        "--prompt-file",
        default=None,
        help="Optional prompt file to hash for every stage plan; raw prompt text is not logged",
    )
    agent_pipeline.add_argument(
        "--no-schedule-initial",
        action="store_true",
        help="Write the pipeline ledger without creating dependency-free stage plans",
    )
    agent_pipeline.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_pipeline_advance = subparsers.add_parser(
        "agent-pipeline-advance",
        help="Schedule dependency-unblocked stages for an existing agent pipeline",
    )
    agent_pipeline_advance.add_argument("--vault", required=True, help="Vault directory")
    agent_pipeline_advance.add_argument("--pipeline-id", required=True, help="Agent pipeline id")
    agent_pipeline_advance.add_argument(
        "--max-stages",
        type=int,
        default=None,
        help="Maximum ready stages to schedule in this advance pass",
    )
    agent_pipeline_advance.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_arena = subparsers.add_parser(
        "agent-arena",
        help="Create a round-robin head-to-head arena plan across experiment variants",
    )
    agent_arena.add_argument("--vault", required=True, help="Vault directory")
    agent_arena.add_argument("--config-file", required=True, help="Agent experiment JSON file")
    agent_arena.add_argument(
        "--subject",
        required=True,
        help="Stable arena key; hashed before it is written to the vault",
    )
    agent_arena.add_argument(
        "--prompt-file",
        default=None,
        help="Optional prompt file to hash for metadata; raw prompt text is not logged",
    )
    agent_arena.add_argument(
        "--lanes",
        default=None,
        help="Comma-separated lane override, for example scout,reviewer",
    )
    agent_arena.add_argument(
        "--replicas",
        type=int,
        default=None,
        help="Optional replica count per variant pair per lane",
    )
    agent_arena.add_argument(
        "--max-runs",
        type=int,
        default=512,
        help="Maximum arena child runs to schedule",
    )
    agent_arena.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_arena_report = subparsers.add_parser(
        "agent-arena-report",
        help="Report round-robin head-to-head arena evidence",
    )
    agent_arena_report.add_argument("--vault", required=True, help="Vault directory")
    agent_arena_report.add_argument("--arena-id", required=True, help="Agent arena id")
    agent_arena_report.add_argument(
        "--min-completed-ratio",
        type=float,
        default=1.0,
        help="Match completion ratio required to count as complete",
    )
    agent_arena_report.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_judge_panel = subparsers.add_parser(
        "agent-judge-panel",
        help="Create independent judge-agent runs for a completed source plan",
    )
    agent_judge_panel.add_argument("--vault", required=True, help="Vault directory")
    agent_judge_panel.add_argument("--config-file", required=True, help="Agent experiment JSON file")
    agent_judge_panel.add_argument("--plan-id", required=True, help="Source agent plan id to judge")
    agent_judge_panel.add_argument(
        "--metric",
        default="judge_score",
        help="Metric name judges should log, for example judge_score",
    )
    agent_judge_panel.add_argument(
        "--direction",
        choices=("maximize", "minimize"),
        default="maximize",
        help="Whether higher or lower judge metric values are better",
    )
    agent_judge_panel.add_argument(
        "--judge-variants",
        default=None,
        help="Comma-separated judge variant ids; defaults to every configured variant",
    )
    agent_judge_panel.add_argument(
        "--replicas",
        type=int,
        default=None,
        help="Optional judge replica count per target and judge variant",
    )
    agent_judge_panel.add_argument(
        "--include-pending-targets",
        action="store_true",
        help="Also schedule judges for source plan runs that do not yet have outcomes",
    )
    agent_judge_panel.add_argument(
        "--include-self-judges",
        action="store_true",
        help="Allow a judge variant to judge outputs from the same variant",
    )
    agent_judge_panel.add_argument(
        "--max-runs",
        type=int,
        default=512,
        help="Maximum judge child runs to schedule",
    )
    agent_judge_panel.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_judge_report = subparsers.add_parser(
        "agent-judge-report",
        help="Aggregate judge-panel metrics into target and variant rankings",
    )
    agent_judge_report.add_argument("--vault", required=True, help="Vault directory")
    agent_judge_report.add_argument("--panel-id", required=True, help="Agent judge panel id")
    agent_judge_report.add_argument(
        "--min-completed-ratio",
        type=float,
        default=1.0,
        help="Judge run completion ratio required to count as complete",
    )
    agent_judge_report.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_outcome = subparsers.add_parser(
        "agent-outcome",
        help="Log metadata-only metrics for a prior agent run",
    )
    agent_outcome.add_argument("--vault", required=True, help="Vault directory")
    agent_outcome.add_argument("--run-id", required=True, help="Agent run id returned by agent-run")
    agent_outcome.add_argument(
        "--status",
        required=True,
        choices=["succeeded", "failed", "cancelled", "timeout"],
        help="Outcome status",
    )
    agent_outcome.add_argument(
        "--metrics-json",
        default="{}",
        help="JSON object of numeric metrics, for example '{\"score\": 0.82}'",
    )
    agent_outcome.add_argument(
        "--metrics-file",
        default=None,
        help="Optional JSON file of numeric metrics; overrides --metrics-json",
    )
    agent_outcome.add_argument(
        "--usage-json",
        default="{}",
        help="Optional JSON usage metadata: tokens, latency_ms, cost_usd, tool_calls",
    )
    agent_outcome.add_argument(
        "--usage-file",
        default=None,
        help="Optional JSON file of usage metadata; overrides --usage-json",
    )
    agent_outcome.add_argument(
        "--output-file",
        default=None,
        help="Optional output file to hash for metadata; raw output text is not logged",
    )
    agent_outcome.add_argument(
        "--failure-code",
        default=None,
        help="Optional short failure label; do not put raw error text here",
    )
    agent_outcome.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_score = subparsers.add_parser(
        "agent-score",
        help="Score a run with the experiment rubric and log outcome metrics",
    )
    agent_score.add_argument("--vault", required=True, help="Vault directory")
    agent_score.add_argument("--run-id", required=True, help="Agent run id returned by agent-run")
    agent_score.add_argument(
        "--status",
        default="succeeded",
        choices=["succeeded", "failed", "cancelled", "timeout"],
        help="Outcome status to write with the scorecard metrics",
    )
    agent_score.add_argument(
        "--scores-json",
        default="{}",
        help="JSON object of rubric criterion scores, for example '{\"correctness\": 0.9}'",
    )
    agent_score.add_argument(
        "--scores-file",
        default=None,
        help="Optional JSON file of rubric criterion scores; overrides --scores-json",
    )
    agent_score.add_argument(
        "--usage-json",
        default="{}",
        help="Optional JSON usage metadata: tokens, latency_ms, cost_usd, tool_calls",
    )
    agent_score.add_argument(
        "--usage-file",
        default=None,
        help="Optional JSON file of usage metadata; overrides --usage-json",
    )
    agent_score.add_argument(
        "--output-file",
        default=None,
        help="Optional output file to hash for metadata; raw output text is not logged",
    )
    agent_score.add_argument(
        "--failure-code",
        default=None,
        help="Optional short failure label; do not put raw error text here",
    )
    agent_score.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_ingest = subparsers.add_parser(
        "agent-ingest",
        help="Batch ingest metadata-only worker result JSON into outcomes and scorecards",
    )
    agent_ingest.add_argument("--vault", required=True, help="Vault directory")
    agent_ingest.add_argument(
        "--results-file",
        required=True,
        help="JSON file with a results or outcomes array; raw outputs are rejected",
    )
    agent_ingest.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_merge = subparsers.add_parser(
        "agent-merge",
        help="Merge outcome metadata for a parallel agent plan",
    )
    agent_merge.add_argument("--vault", required=True, help="Vault directory")
    agent_merge.add_argument("--plan-id", required=True, help="Agent plan id returned by agent-plan")
    agent_merge.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_claim = subparsers.add_parser(
        "agent-claim",
        help="Claim the next uncompleted run from a parallel agent plan",
    )
    agent_claim.add_argument("--vault", required=True, help="Vault directory")
    agent_claim.add_argument("--plan-id", required=True, help="Agent plan id returned by agent-plan")
    agent_claim.add_argument("--client-id", required=True, help="Worker id for this claim")
    agent_claim.add_argument(
        "--lane",
        default=None,
        help="Optional lane id filter, for example scout or reviewer",
    )
    agent_claim.add_argument(
        "--ttl-seconds",
        type=int,
        default=3600,
        help="Claim lease TTL in seconds, max 86400",
    )
    agent_claim.add_argument(
        "--claim-strategy",
        choices=CLAIM_STRATEGIES,
        default="fifo",
        help="Pending-run selection strategy for this claim",
    )
    agent_claim.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_dispatch = subparsers.add_parser(
        "agent-dispatch",
        help="Claim a batch of plan runs and write worker handoff packets",
    )
    agent_dispatch.add_argument("--vault", required=True, help="Vault directory")
    agent_dispatch.add_argument("--plan-id", required=True, help="Agent plan id returned by agent-plan")
    agent_dispatch.add_argument(
        "--client-prefix",
        required=True,
        help="Worker id prefix; each claim receives a numeric suffix",
    )
    agent_dispatch.add_argument(
        "--count",
        type=int,
        required=True,
        help="Maximum number of pending runs to claim and packetize",
    )
    agent_dispatch.add_argument(
        "--lane",
        default=None,
        help="Optional lane id filter, for example scout or reviewer",
    )
    agent_dispatch.add_argument(
        "--ttl-seconds",
        type=int,
        default=3600,
        help="Claim lease TTL in seconds, max 86400",
    )
    agent_dispatch.add_argument(
        "--claim-strategy",
        choices=CLAIM_STRATEGIES,
        default="fifo",
        help="Pending-run selection strategy for each claim in the batch",
    )
    agent_dispatch.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_hold = subparsers.add_parser(
        "agent-hold",
        help="Set an operator hold that blocks new agent dispatch claims",
    )
    agent_hold.add_argument("--vault", required=True, help="Vault directory")
    agent_hold.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_hold.add_argument("--reason", required=True, help="Metadata-only reason for the hold")
    agent_hold.add_argument(
        "--scopes",
        default="all",
        help="Comma-separated hold scopes: all, dispatch, rollout, promotion, evolve",
    )
    agent_hold.add_argument(
        "--ttl-seconds",
        type=int,
        default=None,
        help="Optional hold expiry in seconds, max 2592000",
    )
    agent_hold.add_argument("--operator", default=None, help="Optional operator label")
    agent_hold.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_release = subparsers.add_parser(
        "agent-release",
        help="Release active agent holds for an experiment",
    )
    agent_release.add_argument("--vault", required=True, help="Vault directory")
    agent_release.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_release.add_argument("--reason", default="operator release", help="Metadata-only release reason")
    agent_release.add_argument("--hold-id", default=None, help="Specific active hold id to release")
    agent_release.add_argument(
        "--scopes",
        default="all",
        help="Comma-separated hold scopes to release when --hold-id is omitted",
    )
    agent_release.add_argument("--operator", default=None, help="Optional operator label")
    agent_release.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_quarantine = subparsers.add_parser(
        "agent-quarantine",
        help="Quarantine a provider, variant, or lane slice from new worker claims",
    )
    agent_quarantine.add_argument("--vault", required=True, help="Vault directory")
    agent_quarantine.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_quarantine.add_argument("--reason", required=True, help="Metadata-only reason for quarantine")
    agent_quarantine.add_argument(
        "--variants",
        default="",
        help="Comma-separated variant ids to quarantine",
    )
    agent_quarantine.add_argument(
        "--providers",
        default="",
        help="Comma-separated provider ids to quarantine",
    )
    agent_quarantine.add_argument(
        "--lanes",
        default="",
        help="Comma-separated lane ids to quarantine",
    )
    agent_quarantine.add_argument(
        "--ttl-seconds",
        type=int,
        default=None,
        help="Optional quarantine expiry in seconds, max 2592000",
    )
    agent_quarantine.add_argument("--operator", default=None, help="Optional operator label")
    agent_quarantine.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_circuit = subparsers.add_parser(
        "agent-circuit",
        help="Evaluate provider, variant, or lane circuit breakers from outcome metadata",
    )
    agent_circuit.add_argument("--vault", required=True, help="Vault directory")
    agent_circuit.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_circuit.add_argument(
        "--group-by",
        choices=("provider", "variant", "lane"),
        default="provider",
        help="Outcome grouping to evaluate",
    )
    agent_circuit.add_argument(
        "--min-outcomes",
        type=int,
        default=3,
        help="Minimum latest outcomes required before a group can trip",
    )
    agent_circuit.add_argument(
        "--recent-limit",
        type=int,
        default=None,
        help="Optional newest outcome count to evaluate across the experiment",
    )
    agent_circuit.add_argument(
        "--max-failure-rate",
        type=float,
        default=0.5,
        help="Maximum failed outcome ratio before tripping, from 0 to 1",
    )
    agent_circuit.add_argument(
        "--max-mean-latency-ms",
        type=float,
        default=None,
        help="Optional mean latency ceiling in milliseconds",
    )
    agent_circuit.add_argument(
        "--max-mean-cost-usd",
        type=float,
        default=None,
        help="Optional mean cost ceiling in USD",
    )
    agent_circuit.add_argument(
        "--min-primary-metric",
        type=float,
        default=None,
        help="Optional direction-aware primary metric floor",
    )
    agent_circuit.add_argument(
        "--quarantine-on-trip",
        action="store_true",
        help="Write matching quarantine artifacts for tripped groups",
    )
    agent_circuit.add_argument(
        "--quarantine-ttl-seconds",
        type=int,
        default=None,
        help="Optional expiry for automatic quarantine artifacts, max 2592000",
    )
    agent_circuit.add_argument("--operator", default=None, help="Optional operator label")
    agent_circuit.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_unquarantine = subparsers.add_parser(
        "agent-unquarantine",
        help="Release active agent quarantines by id or matching target",
    )
    agent_unquarantine.add_argument("--vault", required=True, help="Vault directory")
    agent_unquarantine.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_unquarantine.add_argument("--reason", default="operator release", help="Metadata-only release reason")
    agent_unquarantine.add_argument(
        "--quarantine-id",
        default=None,
        help="Specific active quarantine id to release",
    )
    agent_unquarantine.add_argument(
        "--variants",
        default="",
        help="Comma-separated variant ids to release when --quarantine-id is omitted",
    )
    agent_unquarantine.add_argument(
        "--providers",
        default="",
        help="Comma-separated provider ids to release when --quarantine-id is omitted",
    )
    agent_unquarantine.add_argument(
        "--lanes",
        default="",
        help="Comma-separated lane ids to release when --quarantine-id is omitted",
    )
    agent_unquarantine.add_argument("--operator", default=None, help="Optional operator label")
    agent_unquarantine.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_orchestrate = subparsers.add_parser(
        "agent-orchestrate",
        help="Dispatch plan or suite work up to a metadata-only concurrency cap",
    )
    agent_orchestrate.add_argument("--vault", required=True, help="Vault directory")
    orchestrate_scope = agent_orchestrate.add_mutually_exclusive_group(required=True)
    orchestrate_scope.add_argument("--plan-id", default=None, help="Agent plan id to schedule")
    orchestrate_scope.add_argument("--suite-id", default=None, help="Agent suite id to schedule")
    agent_orchestrate.add_argument(
        "--client-prefix",
        required=True,
        help="Worker id prefix used for generated dispatch batches",
    )
    agent_orchestrate.add_argument(
        "--max-concurrency",
        type=int,
        required=True,
        help="Maximum active claims allowed across the selected plan or suite",
    )
    agent_orchestrate.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Maximum claims to create per plan during this scheduler pass",
    )
    agent_orchestrate.add_argument(
        "--lane",
        default=None,
        help="Optional lane id filter, for example scout or reviewer",
    )
    agent_orchestrate.add_argument(
        "--ttl-seconds",
        type=int,
        default=3600,
        help="Claim lease TTL in seconds, max 86400",
    )
    agent_orchestrate.add_argument(
        "--stale-after-seconds",
        type=int,
        default=1800,
        help="Report active claims as stale after this many seconds without heartbeat",
    )
    agent_orchestrate.add_argument(
        "--claim-strategy",
        choices=CLAIM_STRATEGIES,
        default="fifo",
        help="Pending-run selection strategy for dispatches created by orchestration",
    )
    agent_orchestrate.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_heartbeat = subparsers.add_parser(
        "agent-heartbeat",
        help="Extend an active worker claim without storing raw work output",
    )
    agent_heartbeat.add_argument("--vault", required=True, help="Vault directory")
    agent_heartbeat.add_argument("--claim-id", required=True, help="Agent claim id")
    agent_heartbeat.add_argument("--client-id", required=True, help="Worker id that owns the claim")
    agent_heartbeat.add_argument(
        "--ttl-seconds",
        type=int,
        default=3600,
        help="Heartbeat lease TTL in seconds, max 86400",
    )
    agent_heartbeat.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_retry = subparsers.add_parser(
        "agent-retry",
        help="Create a replacement run for failed, stale, or manually retried work",
    )
    agent_retry.add_argument("--vault", required=True, help="Vault directory")
    agent_retry.add_argument("--run-id", required=True, help="Original agent run id to retry")
    agent_retry.add_argument(
        "--reason",
        default="manual",
        help="Short retry reason, for example adapter_timeout or stale_claim",
    )
    agent_retry.add_argument(
        "--variant-id",
        default=None,
        help="Optional variant override; defaults to the original run variant",
    )
    agent_retry.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_recover = subparsers.add_parser(
        "agent-recover",
        help="Batch retry failed, stale, or expired parallel agent work",
    )
    agent_recover.add_argument("--vault", required=True, help="Vault directory")
    agent_recover.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to scope recovery",
    )
    agent_recover.add_argument(
        "--max-retries",
        type=int,
        default=8,
        help="Maximum replacement runs to create in this recovery pass",
    )
    agent_recover.add_argument(
        "--stale-after-seconds",
        type=int,
        default=1800,
        help="Treat active claims without recent heartbeat as stale after this many seconds",
    )
    agent_recover.add_argument(
        "--variant-id",
        default=None,
        help="Optional replacement variant override; defaults to each original variant",
    )
    agent_recover.add_argument("--no-failed", action="store_true", help="Do not retry failed outcomes")
    agent_recover.add_argument("--no-stale", action="store_true", help="Do not retry stale active claims")
    agent_recover.add_argument("--no-expired", action="store_true", help="Do not retry expired claims")
    agent_recover.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_cycle = subparsers.add_parser(
        "agent-cycle",
        help="Run one metadata-only recover, orchestrate, watchdog, status, timeline, and dashboard loop",
    )
    agent_cycle.add_argument("--vault", required=True, help="Vault directory")
    agent_cycle.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to scope reports and recovery",
    )
    cycle_scope = agent_cycle.add_mutually_exclusive_group(required=False)
    cycle_scope.add_argument("--plan-id", default=None, help="Optional plan id to orchestrate")
    cycle_scope.add_argument("--suite-id", default=None, help="Optional suite id to orchestrate")
    agent_cycle.add_argument(
        "--client-prefix",
        default="cycle-worker",
        help="Worker id prefix used when orchestration creates dispatches",
    )
    agent_cycle.add_argument(
        "--max-concurrency",
        type=int,
        default=8,
        help="Maximum active claims allowed when orchestration runs",
    )
    agent_cycle.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Maximum claims to create per plan during orchestration",
    )
    agent_cycle.add_argument("--lane", default=None, help="Optional lane id filter")
    agent_cycle.add_argument(
        "--ttl-seconds",
        type=int,
        default=3600,
        help="Claim lease TTL in seconds, max 86400",
    )
    agent_cycle.add_argument(
        "--stale-after-seconds",
        type=int,
        default=1800,
        help="Treat active claims without recent heartbeat as stale after this many seconds",
    )
    agent_cycle.add_argument(
        "--claim-strategy",
        choices=CLAIM_STRATEGIES,
        default="fifo",
        help="Pending-run selection strategy for orchestration inside this cycle",
    )
    agent_cycle.add_argument(
        "--max-retries",
        type=int,
        default=8,
        help="Maximum replacement runs to create during recovery",
    )
    agent_cycle.add_argument("--skip-recovery", action="store_true", help="Skip the recovery phase")
    agent_cycle.add_argument(
        "--skip-orchestration",
        action="store_true",
        help="Skip the orchestration phase even when a plan or suite is provided",
    )
    agent_cycle.add_argument(
        "--dashboard-limit",
        type=int,
        default=80,
        help="Maximum newest timeline events to include in cycle timeline/dashboard artifacts",
    )
    agent_cycle.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_loop = subparsers.add_parser(
        "agent-loop",
        help="Run bounded metadata-only agent-cycle passes until idle or max cycles is reached",
    )
    agent_loop.add_argument("--vault", required=True, help="Vault directory")
    agent_loop.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to scope reports and recovery",
    )
    loop_scope = agent_loop.add_mutually_exclusive_group(required=False)
    loop_scope.add_argument("--plan-id", default=None, help="Optional plan id to orchestrate")
    loop_scope.add_argument("--suite-id", default=None, help="Optional suite id to orchestrate")
    agent_loop.add_argument(
        "--client-prefix",
        default="loop-worker",
        help="Worker id prefix used when cycle orchestration creates dispatches",
    )
    agent_loop.add_argument(
        "--max-concurrency",
        type=int,
        default=8,
        help="Maximum active claims allowed when orchestration runs",
    )
    agent_loop.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Maximum claims to create per plan during orchestration",
    )
    agent_loop.add_argument("--lane", default=None, help="Optional lane id filter")
    agent_loop.add_argument(
        "--ttl-seconds",
        type=int,
        default=3600,
        help="Claim lease TTL in seconds, max 86400",
    )
    agent_loop.add_argument(
        "--stale-after-seconds",
        type=int,
        default=1800,
        help="Treat active claims without recent heartbeat as stale after this many seconds",
    )
    agent_loop.add_argument(
        "--claim-strategy",
        choices=CLAIM_STRATEGIES,
        default="fifo",
        help="Pending-run selection strategy for orchestration inside each cycle",
    )
    agent_loop.add_argument(
        "--max-retries",
        type=int,
        default=8,
        help="Maximum replacement runs to create during each recovery pass",
    )
    agent_loop.add_argument(
        "--max-cycles",
        type=int,
        default=3,
        help="Maximum cycle passes to run, capped at 20",
    )
    agent_loop.add_argument(
        "--stop-after-idle-cycles",
        type=int,
        default=1,
        help="Stop after this many consecutive cycles that recover or dispatch no work; 0 disables early stop",
    )
    agent_loop.add_argument("--skip-recovery", action="store_true", help="Skip recovery in each cycle")
    agent_loop.add_argument(
        "--skip-orchestration",
        action="store_true",
        help="Skip orchestration in each cycle even when a plan or suite is provided",
    )
    agent_loop.add_argument(
        "--dashboard-limit",
        type=int,
        default=80,
        help="Maximum newest timeline events to include in cycle timeline/dashboard artifacts",
    )
    agent_loop.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_work = subparsers.add_parser(
        "agent-work",
        help="Write a sanitized worker handoff packet for a run or claim",
    )
    agent_work.add_argument("--vault", required=True, help="Vault directory")
    work_source = agent_work.add_mutually_exclusive_group(required=True)
    work_source.add_argument("--run-id", default=None, help="Agent run id")
    work_source.add_argument("--claim-id", default=None, help="Agent claim id")
    agent_work.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_gate = subparsers.add_parser(
        "agent-gate",
        help="Evaluate a parallel plan against completion, failure, lane, and metric gates",
    )
    agent_gate.add_argument("--vault", required=True, help="Vault directory")
    agent_gate.add_argument("--plan-id", required=True, help="Agent plan id returned by agent-plan")
    agent_gate.add_argument(
        "--min-completed-ratio",
        type=float,
        default=1.0,
        help="Minimum completed run ratio required to pass, from 0 to 1",
    )
    agent_gate.add_argument(
        "--max-failures",
        type=int,
        default=0,
        help="Maximum failed outcomes allowed",
    )
    agent_gate.add_argument(
        "--metric-threshold",
        type=float,
        default=None,
        help="Optional primary metric threshold; direction comes from the experiment config",
    )
    agent_gate.add_argument(
        "--require-lane",
        action="append",
        default=[],
        help="Lane id that must be present and complete; repeat for multiple lanes",
    )
    agent_gate.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_adjudicate = subparsers.add_parser(
        "agent-adjudicate",
        help="Create a decision ledger for a completed parallel agent plan",
    )
    agent_adjudicate.add_argument("--vault", required=True, help="Vault directory")
    agent_adjudicate.add_argument(
        "--plan-id",
        required=True,
        help="Agent plan id returned by agent-plan",
    )
    agent_adjudicate.add_argument(
        "--min-completed-ratio",
        type=float,
        default=1.0,
        help="Minimum completed run ratio required to accept, from 0 to 1",
    )
    agent_adjudicate.add_argument(
        "--min-consensus-ratio",
        type=float,
        default=0.5,
        help="Minimum lane agreement ratio required to accept, from 0 to 1",
    )
    agent_adjudicate.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_quorum = subparsers.add_parser(
        "agent-quorum",
        help="Write a lane vote quorum report for a parallel agent plan",
    )
    agent_quorum.add_argument("--vault", required=True, help="Vault directory")
    agent_quorum.add_argument(
        "--plan-id",
        required=True,
        help="Agent plan id returned by agent-plan",
    )
    agent_quorum.add_argument(
        "--min-completed-ratio",
        type=float,
        default=1.0,
        help="Minimum completed run ratio required to pass, from 0 to 1",
    )
    agent_quorum.add_argument(
        "--min-agreement-ratio",
        type=float,
        default=0.5,
        help="Minimum leading lane vote agreement ratio required to pass, from 0 to 1",
    )
    agent_quorum.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_audit = subparsers.add_parser(
        "agent-audit",
        help="Audit agent harness artifact references, privacy markers, and decision order",
    )
    agent_audit.add_argument("--vault", required=True, help="Vault directory")
    agent_audit.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to scope the audit",
    )
    agent_audit.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_manifest = subparsers.add_parser(
        "agent-manifest",
        help="Write a metadata-only SHA-256 manifest for agent harness artifacts",
    )
    agent_manifest.add_argument("--vault", required=True, help="Vault directory")
    agent_manifest.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to snapshot; defaults to all experiments",
    )
    agent_manifest.add_argument(
        "--include-reports",
        action="store_true",
        help="Include matching global agent-runs/_reports artifacts",
    )
    agent_manifest.add_argument(
        "--max-artifacts",
        type=int,
        default=50000,
        help="Maximum artifacts to include before failing closed",
    )
    agent_manifest.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_verify_manifest = subparsers.add_parser(
        "agent-verify-manifest",
        help="Verify agent artifact hashes against a prior agent-manifest snapshot",
    )
    agent_verify_manifest.add_argument("--vault", required=True, help="Vault directory")
    agent_verify_manifest.add_argument(
        "--manifest-id",
        default=None,
        help="Manifest id to verify; defaults to the latest manifest",
    )
    agent_verify_manifest.add_argument(
        "--fail-on-extra",
        action="store_true",
        help="Treat artifacts created after the manifest as failures instead of warnings",
    )
    agent_verify_manifest.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_preflight = subparsers.add_parser(
        "agent-preflight",
        help="Gate a worker launch before dispatching cross-model parallel work",
    )
    agent_preflight.add_argument("--vault", required=True, help="Vault directory")
    agent_preflight.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to scope preflight when no plan or suite is provided",
    )
    agent_preflight.add_argument(
        "--plan-id",
        default=None,
        help="Plan id to preflight before dispatch",
    )
    agent_preflight.add_argument(
        "--suite-id",
        default=None,
        help="Suite id to preflight before orchestration",
    )
    agent_preflight.add_argument(
        "--min-pending-runs",
        type=int,
        default=1,
        help="Minimum uncompleted and unclaimed runs required",
    )
    agent_preflight.add_argument(
        "--max-active-claims",
        type=int,
        default=None,
        help="Maximum active worker claims allowed before launch",
    )
    agent_preflight.add_argument(
        "--stale-after-seconds",
        type=int,
        default=1800,
        help="Treat active claims older than this as stale",
    )
    agent_preflight.add_argument(
        "--require-cross-model",
        action="store_true",
        help="Require pending work to cover at least two variants across at least two providers",
    )
    agent_preflight.add_argument(
        "--require-lane-coverage",
        action="store_true",
        help="Require pending work to include every scheduled lane",
    )
    agent_preflight.add_argument(
        "--require-variant-coverage",
        action="store_true",
        help="Require pending work to include every scheduled variant",
    )
    agent_preflight.add_argument(
        "--max-pending-skew",
        type=int,
        default=None,
        help="Maximum pending lane/variant cell count skew allowed",
    )
    agent_preflight.add_argument(
        "--block-failed-outcomes",
        action="store_true",
        help="Block launch when failed outcomes already exist in scope",
    )
    agent_preflight.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_compare = subparsers.add_parser(
        "agent-compare",
        help="Write statistical cross-model comparison evidence from outcome metrics",
    )
    agent_compare.add_argument("--vault", required=True, help="Vault directory")
    agent_compare.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_compare.add_argument(
        "--baseline-variant",
        default=None,
        help="Variant id to compare against; defaults to the highest-weight champion",
    )
    agent_compare.add_argument(
        "--min-samples-per-variant",
        type=int,
        default=None,
        help="Minimum primary-metric samples required before declaring a comparison eligible",
    )
    agent_compare.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_decision = subparsers.add_parser(
        "agent-decision",
        help="Write a sequential A/B stop, promote, or continue decision from outcome evidence",
    )
    agent_decision.add_argument("--vault", required=True, help="Vault directory")
    agent_decision.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_decision.add_argument(
        "--baseline-variant",
        default=None,
        help="Baseline variant id; defaults to the current highest-weight variant",
    )
    agent_decision.add_argument(
        "--candidate-variant",
        default=None,
        help="Candidate variant id; defaults to the best observed non-baseline challenger",
    )
    agent_decision.add_argument(
        "--min-samples-per-variant",
        type=int,
        default=None,
        help="Minimum primary-metric samples required for baseline and candidate",
    )
    agent_decision.add_argument(
        "--min-delta",
        type=float,
        default=0.0,
        help="Minimum directional metric delta required before stopping",
    )
    agent_decision.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.8,
        help="One-sided confidence threshold required before stopping, from 0 to 1",
    )
    agent_decision.add_argument(
        "--max-cost-usd",
        type=float,
        default=None,
        help="Optional observed cost guardrail for the compared baseline/candidate evidence",
    )
    agent_decision.add_argument(
        "--max-total-tokens",
        type=int,
        default=None,
        help="Optional observed token guardrail for the compared baseline/candidate evidence",
    )
    agent_decision.add_argument(
        "--candidate-metric-floor",
        type=float,
        default=None,
        help="Optional candidate mean guardrail; maximum allowed value for minimize metrics",
    )
    agent_decision.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_balance = subparsers.add_parser(
        "agent-balance",
        help="Report sample balance across variants, lanes, and cases before trusting A/B evidence",
    )
    agent_balance.add_argument("--vault", required=True, help="Vault directory")
    agent_balance.add_argument("--experiment", required=True, help="Experiment name or slug")
    balance_scope = agent_balance.add_mutually_exclusive_group(required=False)
    balance_scope.add_argument("--suite-id", default=None, help="Optional suite id to scope the balance report")
    balance_scope.add_argument("--plan-id", default=None, help="Optional plan id to scope the balance report")
    agent_balance.add_argument(
        "--dimensions",
        default="variant,lane",
        help="Comma-separated balance dimensions selected from variant,lane,case",
    )
    agent_balance.add_argument(
        "--min-count-per-cell",
        type=int,
        default=1,
        help="Minimum completed outcomes required in each observed cell",
    )
    agent_balance.add_argument(
        "--max-skew",
        type=int,
        default=1,
        help="Maximum completed-sample count difference allowed between cells",
    )
    agent_balance.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_timeline = subparsers.add_parser(
        "agent-timeline",
        help="Write a chronological metadata-only timeline of agent harness events",
    )
    agent_timeline.add_argument("--vault", required=True, help="Vault directory")
    agent_timeline.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to scope the timeline",
    )
    agent_timeline.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum newest events to include",
    )
    agent_timeline.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_watchdog = subparsers.add_parser(
        "agent-watchdog",
        help="Write a metadata-only stale claim and worker health report",
    )
    agent_watchdog.add_argument("--vault", required=True, help="Vault directory")
    agent_watchdog.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to scope the watchdog",
    )
    agent_watchdog.add_argument(
        "--stale-after-seconds",
        type=int,
        default=1800,
        help="Warn when active claims have not heartbeated within this many seconds",
    )
    agent_watchdog.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_capacity = subparsers.add_parser(
        "agent-capacity",
        help="Plan worker launch capacity from pending, active, stale, and recent latency metadata",
    )
    agent_capacity.add_argument("--vault", required=True, help="Vault directory")
    agent_capacity.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to scope capacity planning",
    )
    capacity_scope = agent_capacity.add_mutually_exclusive_group(required=False)
    capacity_scope.add_argument("--plan-id", default=None, help="Optional plan id to scope capacity planning")
    capacity_scope.add_argument("--suite-id", default=None, help="Optional suite id to scope capacity planning")
    agent_capacity.add_argument(
        "--max-concurrency",
        type=int,
        default=8,
        help="Maximum active claims allowed across this planning scope",
    )
    agent_capacity.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Optional maximum claims to recommend for the next dispatch",
    )
    agent_capacity.add_argument(
        "--target-utilization",
        type=float,
        default=0.85,
        help="Target share of max concurrency to keep filled, greater than 0 and at most 1",
    )
    agent_capacity.add_argument(
        "--min-batch-size",
        type=int,
        default=1,
        help="Minimum useful dispatch batch size when enough slots and pending runs exist",
    )
    agent_capacity.add_argument(
        "--stale-after-seconds",
        type=int,
        default=1800,
        help="Treat active claims without recent heartbeats as stale after this many seconds",
    )
    agent_capacity.add_argument(
        "--latency-window",
        type=int,
        default=20,
        help="Newest outcome latency samples to use for TTL recommendations",
    )
    agent_capacity.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_slo = subparsers.add_parser(
        "agent-slo",
        help="Evaluate a metadata-only SLO gate for parallel agent fleet health",
    )
    agent_slo.add_argument("--vault", required=True, help="Vault directory")
    agent_slo.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to scope SLO evaluation",
    )
    slo_scope = agent_slo.add_mutually_exclusive_group(required=False)
    slo_scope.add_argument("--plan-id", default=None, help="Optional plan id to scope SLO evaluation")
    slo_scope.add_argument("--suite-id", default=None, help="Optional suite id to scope SLO evaluation")
    agent_slo.add_argument(
        "--min-completion-rate",
        type=float,
        default=0.0,
        help="Minimum completed/scheduled run ratio required, from 0 to 1",
    )
    agent_slo.add_argument(
        "--max-failure-rate",
        type=float,
        default=0.1,
        help="Maximum failed/completed outcome ratio allowed, from 0 to 1",
    )
    agent_slo.add_argument(
        "--max-stale-claims",
        type=int,
        default=0,
        help="Maximum stale active claims allowed",
    )
    agent_slo.add_argument(
        "--max-expired-claims",
        type=int,
        default=0,
        help="Maximum expired claims allowed",
    )
    agent_slo.add_argument(
        "--max-active-claims",
        type=int,
        default=None,
        help="Optional maximum active claims allowed",
    )
    agent_slo.add_argument(
        "--max-quarantined-pending-runs",
        type=int,
        default=None,
        help="Optional maximum quarantined pending runs allowed",
    )
    agent_slo.add_argument(
        "--max-mean-latency-ms",
        type=float,
        default=None,
        help="Optional mean latency ceiling in milliseconds for scoped outcomes",
    )
    agent_slo.add_argument(
        "--allow-active-holds",
        action="store_true",
        help="Do not fail the SLO gate when active holds are present",
    )
    agent_slo.add_argument(
        "--allow-active-quarantines",
        action="store_true",
        help="Do not fail the SLO gate when active quarantines are present",
    )
    agent_slo.add_argument(
        "--stale-after-seconds",
        type=int,
        default=1800,
        help="Treat active claims without recent heartbeats as stale after this many seconds",
    )
    agent_slo.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_mix = subparsers.add_parser(
        "agent-mix",
        help="Evaluate provider, model, and adapter diversity for a cross-model experiment",
    )
    agent_mix.add_argument("--vault", required=True, help="Vault directory")
    agent_mix.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_mix.add_argument(
        "--min-provider-count",
        type=int,
        default=2,
        help="Minimum configured providers required",
    )
    agent_mix.add_argument(
        "--min-variant-count",
        type=int,
        default=2,
        help="Minimum configured model variants required",
    )
    agent_mix.add_argument(
        "--max-provider-weight-share",
        type=float,
        default=0.8,
        help="Maximum configured traffic weight share allowed for one provider",
    )
    agent_mix.add_argument(
        "--max-scheduled-provider-share",
        type=float,
        default=0.85,
        help="Maximum scheduled run share allowed for one provider",
    )
    agent_mix.add_argument(
        "--max-completed-provider-share",
        type=float,
        default=0.9,
        help="Maximum completed outcome share allowed for one provider",
    )
    agent_mix.add_argument(
        "--require-local-provider",
        action="store_true",
        help="Require at least one configured local provider such as Ollama",
    )
    agent_mix.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_snapshot = subparsers.add_parser(
        "agent-snapshot",
        help="Write a metadata-only reproducibility snapshot and diff it against a baseline",
    )
    agent_snapshot.add_argument("--vault", required=True, help="Vault directory")
    agent_snapshot.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_snapshot.add_argument(
        "--baseline-snapshot-id",
        default=None,
        help="Snapshot id to diff against; defaults to the latest snapshot for the experiment",
    )
    agent_snapshot.add_argument(
        "--fail-on-change",
        action="store_true",
        help="Exit nonzero when the snapshot differs from the baseline",
    )
    agent_snapshot.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_budget = subparsers.add_parser(
        "agent-budget",
        help="Write a metadata-only cost, token, and latency budget report",
    )
    agent_budget.add_argument("--vault", required=True, help="Vault directory")
    agent_budget.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to scope the budget",
    )
    agent_budget.add_argument(
        "--max-cost-usd",
        type=float,
        default=None,
        help="Maximum aggregate cost USD allowed for the selected scope",
    )
    agent_budget.add_argument(
        "--max-total-tokens",
        type=int,
        default=None,
        help="Maximum aggregate token usage allowed for the selected scope",
    )
    agent_budget.add_argument(
        "--max-mean-latency-ms",
        type=float,
        default=None,
        help="Maximum mean latency in milliseconds allowed for the selected scope",
    )
    agent_budget.add_argument(
        "--max-run-cost-usd",
        type=float,
        default=None,
        help="Maximum cost USD allowed for any single outcome",
    )
    agent_budget.add_argument(
        "--max-run-tokens",
        type=int,
        default=None,
        help="Maximum total tokens allowed for any single outcome",
    )
    agent_budget.add_argument(
        "--max-run-latency-ms",
        type=float,
        default=None,
        help="Maximum latency in milliseconds allowed for any single outcome",
    )
    agent_budget.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_drift = subparsers.add_parser(
        "agent-drift",
        help="Detect recent metric, cost, or latency drift against prior outcome windows",
    )
    agent_drift.add_argument("--vault", required=True, help="Vault directory")
    agent_drift.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_drift.add_argument(
        "--metric",
        default=None,
        help="Metric name to monitor; defaults to the experiment primary metric",
    )
    agent_drift.add_argument(
        "--baseline-window",
        type=int,
        default=5,
        help="Number of prior outcomes per variant or lane/variant window",
    )
    agent_drift.add_argument(
        "--recent-window",
        type=int,
        default=5,
        help="Number of newest outcomes per variant or lane/variant window",
    )
    agent_drift.add_argument(
        "--min-samples",
        type=int,
        default=2,
        help="Minimum baseline and recent samples needed for a drift window",
    )
    agent_drift.add_argument(
        "--max-metric-drop",
        type=float,
        default=0.05,
        help="Maximum allowed direction-aware metric regression",
    )
    agent_drift.add_argument(
        "--max-cost-increase-ratio",
        type=float,
        default=None,
        help="Maximum allowed recent mean cost increase ratio",
    )
    agent_drift.add_argument(
        "--max-latency-increase-ratio",
        type=float,
        default=None,
        help="Maximum allowed recent mean latency increase ratio",
    )
    agent_drift.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_readiness = subparsers.add_parser(
        "agent-readiness",
        help="Write an experiment readiness gate across comparison, budget, routing, memory, quorum, and promotion evidence",
    )
    agent_readiness.add_argument("--vault", required=True, help="Vault directory")
    agent_readiness.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_readiness.add_argument(
        "--min-outcomes",
        type=int,
        default=1,
        help="Minimum outcome count required for readiness",
    )
    agent_readiness.add_argument(
        "--max-failed-outcomes",
        type=int,
        default=0,
        help="Maximum failed outcome count allowed for readiness",
    )
    agent_readiness.add_argument(
        "--require-comparison",
        action="store_true",
        help="Require a latest agent-compare artifact with an eligible winner",
    )
    agent_readiness.add_argument(
        "--require-budget",
        action="store_true",
        help="Require the latest agent-budget artifact to be within limits",
    )
    agent_readiness.add_argument(
        "--require-route",
        action="store_true",
        help="Require the latest agent-route artifact to recommend lane policies",
    )
    agent_readiness.add_argument(
        "--require-memory",
        action="store_true",
        help="Require a latest metadata-only agent-memory artifact",
    )
    agent_readiness.add_argument(
        "--require-quorum",
        action="store_true",
        help="Require the latest agent-quorum artifact to be passing",
    )
    agent_readiness.add_argument(
        "--require-promotion",
        action="store_true",
        help="Require the latest agent-promote artifact to be ready",
    )
    agent_readiness.add_argument(
        "--require-balance",
        action="store_true",
        help="Require the latest agent-balance artifact to be balanced",
    )
    agent_readiness.add_argument(
        "--require-drift",
        action="store_true",
        help="Require the latest agent-drift artifact to be stable",
    )
    agent_readiness.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_rollout = subparsers.add_parser(
        "agent-rollout",
        help="Write a staged rollout and rollback plan for a challenger variant",
    )
    agent_rollout.add_argument("--vault", required=True, help="Vault directory")
    agent_rollout.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_rollout.add_argument(
        "--candidate-variant",
        default=None,
        help="Challenger variant id; defaults to promotion, comparison, or allocation winner",
    )
    agent_rollout.add_argument(
        "--champion-variant",
        default=None,
        help="Current champion variant id; defaults to the highest-weight variant",
    )
    agent_rollout.add_argument(
        "--stages",
        default="0.05,0.25,0.5,1",
        help="Comma-separated candidate traffic shares from 0 to 1",
    )
    agent_rollout.add_argument(
        "--min-observation-runs",
        type=int,
        default=3,
        help="Minimum stage outcome count before advancing",
    )
    agent_rollout.add_argument(
        "--max-stage-failed-outcomes",
        type=int,
        default=0,
        help="Maximum failed outcomes allowed in each stage",
    )
    agent_rollout.add_argument(
        "--require-readiness",
        action="store_true",
        help="Require the latest agent-readiness artifact to be ready",
    )
    agent_rollout.add_argument(
        "--require-promotion",
        action="store_true",
        help="Require the latest agent-promote artifact to be ready for the challenger",
    )
    agent_rollout.add_argument(
        "--require-budget",
        action="store_true",
        help="Require the latest agent-budget artifact to be within limits",
    )
    agent_rollout.add_argument(
        "--require-drift",
        action="store_true",
        help="Require the latest agent-drift artifact to be stable",
    )
    agent_rollout.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_rollout_check = subparsers.add_parser(
        "agent-rollout-check",
        help="Evaluate a rollout stage and write an advance, hold, or rollback decision",
    )
    agent_rollout_check.add_argument("--vault", required=True, help="Vault directory")
    agent_rollout_check.add_argument("--rollout-id", required=True, help="Rollout id from agent-rollout")
    agent_rollout_check.add_argument(
        "--stage-index",
        type=int,
        default=1,
        help="Rollout stage index to evaluate",
    )
    agent_rollout_check.add_argument(
        "--min-stage-outcomes",
        type=int,
        default=None,
        help="Override the stage's minimum challenger outcome count",
    )
    agent_rollout_check.add_argument(
        "--max-stage-failed-outcomes",
        type=int,
        default=None,
        help="Override the stage's maximum failed challenger outcome count",
    )
    agent_rollout_check.add_argument(
        "--max-share-deviation",
        type=float,
        default=0.5,
        help="Warn when observed challenger share differs from stage target by more than this ratio",
    )
    agent_rollout_check.add_argument(
        "--min-metric-delta",
        type=float,
        default=None,
        help="Rollback when challenger metric gap is below this directional floor",
    )
    agent_rollout_check.add_argument(
        "--require-budget",
        action="store_true",
        help="Require the latest agent-budget artifact to be within limits",
    )
    agent_rollout_check.add_argument(
        "--require-readiness",
        action="store_true",
        help="Require the latest agent-readiness artifact to be ready",
    )
    agent_rollout_check.add_argument(
        "--require-drift",
        action="store_true",
        help="Require the latest agent-drift artifact to be stable before advancing",
    )
    agent_rollout_check.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_evolve = subparsers.add_parser(
        "agent-evolve",
        help="Run the metadata-only compare, improve, memory, routing, promotion, and rollout loop",
    )
    agent_evolve.add_argument("--vault", required=True, help="Vault directory")
    agent_evolve.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_evolve.add_argument(
        "--min-trials-per-variant",
        type=int,
        default=None,
        help="Override the experiment's minimum trial count for improvement and allocation",
    )
    agent_evolve.add_argument(
        "--min-samples-per-variant",
        type=int,
        default=None,
        help="Override the minimum primary-metric samples for comparison",
    )
    agent_evolve.add_argument(
        "--max-lessons",
        type=int,
        default=12,
        help="Maximum metadata-only lessons to write",
    )
    agent_evolve.add_argument(
        "--allocation-strategy",
        choices=["softmax", "ucb1", "epsilon-greedy", "winner-take-most"],
        default="ucb1",
        help="Adaptive traffic strategy for variant allocation",
    )
    agent_evolve.add_argument(
        "--route-strategy",
        choices=["softmax", "ucb1", "epsilon-greedy", "winner-take-most"],
        default="ucb1",
        help="Adaptive routing strategy for lane policies",
    )
    agent_evolve.add_argument(
        "--exploration-floor",
        type=float,
        default=0.05,
        help="Minimum share reserved for measured variants",
    )
    agent_evolve.add_argument(
        "--max-share",
        type=float,
        default=0.85,
        help="Maximum share assigned to a single variant or lane route",
    )
    agent_evolve.add_argument(
        "--cost-penalty",
        type=float,
        default=0.0,
        help="Penalty multiplier for higher cost per outcome",
    )
    agent_evolve.add_argument(
        "--champion-variant",
        default=None,
        help="Current champion variant id for promotion and rollout evidence",
    )
    agent_evolve.add_argument(
        "--min-delta",
        type=float,
        default=0.0,
        help="Minimum directional metric delta needed for promotion readiness",
    )
    agent_evolve.add_argument(
        "--max-cost-usd",
        type=float,
        default=None,
        help="Optional total cost budget for the evolve pass",
    )
    agent_evolve.add_argument(
        "--max-total-tokens",
        type=int,
        default=None,
        help="Optional total token budget for the evolve pass",
    )
    agent_evolve.add_argument(
        "--max-mean-latency-ms",
        type=float,
        default=None,
        help="Optional mean latency budget for the evolve pass",
    )
    agent_evolve.add_argument(
        "--require-budget",
        action="store_true",
        help="Require budget evidence for promotion, readiness, and optional rollout",
    )
    agent_evolve.add_argument(
        "--require-route",
        action="store_true",
        help="Require lane routing evidence in the readiness step",
    )
    agent_evolve.add_argument(
        "--require-drift",
        action="store_true",
        help="Run drift detection and require stable drift evidence in promotion, readiness, and rollout",
    )
    agent_evolve.add_argument(
        "--plan-rollout",
        action="store_true",
        help="Write a staged rollout plan after promotion and readiness evidence",
    )
    agent_evolve.add_argument(
        "--rollout-stages",
        default="0.05,0.25,0.5,1",
        help="Comma-separated candidate traffic shares for optional rollout planning",
    )
    agent_evolve.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_power = subparsers.add_parser(
        "agent-power",
        help="Size the next cross-model A/B experiment from observed variance and budget limits",
    )
    agent_power.add_argument("--vault", required=True, help="Vault directory")
    agent_power.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_power.add_argument(
        "--baseline-variant",
        default=None,
        help="Baseline variant id; defaults to the current highest-weight variant",
    )
    agent_power.add_argument(
        "--min-detectable-effect",
        type=float,
        default=0.05,
        help="Minimum directional metric effect worth detecting",
    )
    agent_power.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Two-sided false-positive rate for the power estimate",
    )
    agent_power.add_argument(
        "--power",
        type=float,
        default=0.8,
        help="Target statistical power for detecting the effect",
    )
    agent_power.add_argument(
        "--fallback-stddev",
        type=float,
        default=None,
        help="Fallback metric standard deviation when pilot outcomes are insufficient",
    )
    agent_power.add_argument(
        "--max-cost-usd",
        type=float,
        default=None,
        help="Optional budget limit for the additional recommended samples",
    )
    agent_power.add_argument(
        "--max-total-tokens",
        type=int,
        default=None,
        help="Optional token limit for the additional recommended samples",
    )
    agent_power.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_schedule = subparsers.add_parser(
        "agent-schedule",
        help="Create a dispatchable next-batch plan from the latest agent-power report",
    )
    agent_schedule.add_argument("--vault", required=True, help="Vault directory")
    agent_schedule.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_schedule.add_argument(
        "--subject",
        required=True,
        help="Private scheduling subject key; only a hash is stored",
    )
    agent_schedule.add_argument(
        "--lanes",
        default=None,
        help="Optional comma-separated lanes for scheduled runs",
    )
    agent_schedule.add_argument(
        "--max-runs",
        type=int,
        default=24,
        help="Maximum scheduled runs to create in this batch",
    )
    agent_schedule.add_argument(
        "--power-id",
        default=None,
        help="Specific agent-power id; defaults to the latest power report",
    )
    agent_schedule.add_argument(
        "--include-budget-limited",
        action="store_true",
        help="Allow scheduling from budget-limited or budget-unknown power plans",
    )
    agent_schedule.add_argument(
        "--unpaired",
        action="store_true",
        help="Schedule quota-balanced runs without paired baseline/challenger blocks",
    )
    agent_schedule.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_schedule_report = subparsers.add_parser(
        "agent-schedule-report",
        help="Summarize paired baseline/challenger blocks from an agent-schedule batch",
    )
    agent_schedule_report.add_argument("--vault", required=True, help="Vault directory")
    agent_schedule_report.add_argument("--schedule-id", required=True, help="Schedule id to report")
    agent_schedule_report.add_argument(
        "--min-completed-blocks-ratio",
        type=float,
        default=1.0,
        help="Minimum complete paired block ratio before the schedule report is complete",
    )
    agent_schedule_report.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_dashboard = subparsers.add_parser(
        "agent-dashboard",
        help="Write a self-contained local HTML dashboard for agent harness operations",
    )
    agent_dashboard.add_argument("--vault", required=True, help="Vault directory")
    agent_dashboard.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to scope the dashboard",
    )
    agent_dashboard.add_argument(
        "--limit",
        type=int,
        default=80,
        help="Maximum newest timeline events to include",
    )
    agent_dashboard.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_leaderboard = subparsers.add_parser(
        "agent-leaderboard",
        help="Write a consolidated cross-model evidence leaderboard for an experiment",
    )
    agent_leaderboard.add_argument("--vault", required=True, help="Vault directory")
    agent_leaderboard.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_leaderboard.add_argument(
        "--baseline-variant",
        default=None,
        help="Baseline variant id; defaults to the current highest-weight variant",
    )
    agent_leaderboard.add_argument(
        "--min-samples-per-variant",
        type=int,
        default=None,
        help="Minimum primary-metric samples before metric rank points are awarded",
    )
    agent_leaderboard.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_config = subparsers.add_parser(
        "agent-config",
        help="Write a reviewable next experiment config proposal from harness evidence",
    )
    agent_config.add_argument("--vault", required=True, help="Vault directory")
    agent_config.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_config.add_argument(
        "--source",
        choices=("auto", "promotion", "leaderboard", "allocation", "route", "improvement"),
        default="auto",
        help="Evidence source to convert into the next config proposal",
    )
    agent_config.add_argument(
        "--exploration-floor",
        type=float,
        default=0.05,
        help="Minimum traffic share retained for each variant when leaderboard evidence is used",
    )
    agent_config.add_argument(
        "--max-share",
        type=float,
        default=0.85,
        help="Maximum traffic share allowed for any one variant when leaderboard evidence is used",
    )
    agent_config.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_status = subparsers.add_parser(
        "agent-status",
        help="Write a metadata-only agent harness scoreboard and action report",
    )
    agent_status.add_argument("--vault", required=True, help="Vault directory")
    agent_status.add_argument(
        "--experiment",
        default=None,
        help="Optional experiment name or slug to scope the status report",
    )
    agent_status.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_improve = subparsers.add_parser(
        "agent-improve",
        help="Summarize agent outcomes and write a self-improvement proposal",
    )
    agent_improve.add_argument("--vault", required=True, help="Vault directory")
    agent_improve.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_improve.add_argument(
        "--min-trials-per-variant",
        type=int,
        default=None,
        help="Override the experiment's minimum trial count for promotion guidance",
    )
    agent_improve.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_memory = subparsers.add_parser(
        "agent-memory",
        help="Write metadata-only lessons from outcomes, failures, usage, and harness evidence",
    )
    agent_memory.add_argument("--vault", required=True, help="Vault directory")
    agent_memory.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_memory.add_argument(
        "--min-trials-per-variant",
        type=int,
        default=None,
        help="Override the experiment's minimum primary-metric sample count",
    )
    agent_memory.add_argument(
        "--max-lessons",
        type=int,
        default=12,
        help="Maximum lessons to write into the memory artifact",
    )
    agent_memory.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_curriculum = subparsers.add_parser(
        "agent-curriculum",
        help="Mine metadata-only hard cases for the next focused suite or matrix wave",
    )
    agent_curriculum.add_argument("--vault", required=True, help="Vault directory")
    agent_curriculum.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_curriculum.add_argument(
        "--metric-threshold",
        type=float,
        default=None,
        help="Primary metric threshold for hard-case selection; defaults to the observed mean",
    )
    agent_curriculum.add_argument(
        "--max-cases",
        type=int,
        default=12,
        help="Maximum hard cases to include",
    )
    agent_curriculum.add_argument(
        "--exclude-failed",
        action="store_true",
        help="Do not include failed, cancelled, or timed-out outcomes as hard cases",
    )
    agent_curriculum.add_argument(
        "--exclude-low-metric",
        action="store_true",
        help="Do not include weak or missing primary-metric outcomes as hard cases",
    )
    agent_curriculum.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_allocate = subparsers.add_parser(
        "agent-allocate",
        help="Write an adaptive cross-model traffic allocation proposal",
    )
    agent_allocate.add_argument("--vault", required=True, help="Vault directory")
    agent_allocate.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_allocate.add_argument(
        "--strategy",
        choices=("ucb1", "epsilon-greedy", "equalize"),
        default="ucb1",
        help="Allocation strategy for next traffic weights",
    )
    agent_allocate.add_argument(
        "--exploration-floor",
        type=float,
        default=0.05,
        help="Minimum traffic share reserved per variant, from 0 to 1",
    )
    agent_allocate.add_argument(
        "--max-share",
        type=float,
        default=0.85,
        help="Maximum recommended traffic share for any variant, from 0 to 1",
    )
    agent_allocate.add_argument(
        "--min-trials-per-variant",
        type=int,
        default=None,
        help="Override minimum primary-metric samples before exploiting a variant",
    )
    agent_allocate.add_argument(
        "--cost-penalty",
        type=float,
        default=0.0,
        help="Subtract this multiplier times mean cost USD from reward",
    )
    agent_allocate.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_route = subparsers.add_parser(
        "agent-route",
        help="Write a lane-aware model routing policy from parallel outcome metadata",
    )
    agent_route.add_argument("--vault", required=True, help="Vault directory")
    agent_route.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_route.add_argument(
        "--strategy",
        choices=("ucb1", "epsilon-greedy", "equalize"),
        default="ucb1",
        help="Allocation strategy for each lane's next model shares",
    )
    agent_route.add_argument(
        "--exploration-floor",
        type=float,
        default=0.05,
        help="Minimum traffic share reserved per variant in each lane, from 0 to 1",
    )
    agent_route.add_argument(
        "--max-share",
        type=float,
        default=0.85,
        help="Maximum recommended lane share for any variant, from 0 to 1",
    )
    agent_route.add_argument(
        "--min-trials-per-lane-variant",
        type=int,
        default=None,
        help="Override minimum primary-metric samples per lane and variant",
    )
    agent_route.add_argument(
        "--cost-penalty",
        type=float,
        default=0.0,
        help="Subtract this multiplier times mean cost USD from each lane reward",
    )
    agent_route.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    agent_promote = subparsers.add_parser(
        "agent-promote",
        help="Write a champion/challenger promotion proposal from experiment evidence",
    )
    agent_promote.add_argument("--vault", required=True, help="Vault directory")
    agent_promote.add_argument("--experiment", required=True, help="Experiment name or slug")
    agent_promote.add_argument(
        "--champion-variant",
        default=None,
        help="Current champion variant id; defaults to the highest-weight variant",
    )
    agent_promote.add_argument(
        "--min-trials-per-variant",
        type=int,
        default=None,
        help="Override the experiment's minimum primary-metric sample count",
    )
    agent_promote.add_argument(
        "--min-delta",
        type=float,
        default=0.0,
        help="Minimum primary metric gap required to promote a challenger",
    )
    agent_promote.add_argument(
        "--require-passing-gate",
        action="store_true",
        help="Require the latest agent-gate result for the experiment to be passing",
    )
    agent_promote.add_argument(
        "--require-suite-report",
        action="store_true",
        help="Require the latest paired suite report winner to match the candidate",
    )
    agent_promote.add_argument(
        "--require-pareto",
        action="store_true",
        help="Require the candidate to appear on the latest Pareto frontier",
    )
    agent_promote.add_argument(
        "--require-budget",
        action="store_true",
        help="Require the latest agent-budget report to be within budget",
    )
    agent_promote.add_argument(
        "--require-balance",
        action="store_true",
        help="Require the latest agent-balance report to be balanced",
    )
    agent_promote.add_argument(
        "--require-drift",
        action="store_true",
        help="Require the latest agent-drift report to be stable",
    )
    agent_promote.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    backup = subparsers.add_parser(
        "backup",
        help="Create a safe zip backup of the selected vault",
    )
    backup.add_argument("--vault", required=True, help="Vault directory")
    backup.add_argument(
        "--output",
        default=None,
        help="Output zip file or directory; defaults to the vault parent",
    )
    backup.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the exact output archive path instead of allocating a unique path",
    )

    restore = subparsers.add_parser(
        "restore",
        help="Restore a GriosAI vault zip backup",
    )
    restore.add_argument("archive", help="Backup zip archive")
    restore.add_argument("--vault", required=True, help="Restore destination vault directory")
    restore.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing restore targets instead of failing",
    )

    verify_backup_parser = subparsers.add_parser(
        "verify-backup",
        help="Verify a GriosAI vault zip backup without restoring it",
    )
    verify_backup_parser.add_argument("archive", help="Backup zip archive")

    subparsers.add_parser("openapi", help="Print the local REST OpenAPI contract")

    subparsers.add_parser("analysis-schema", help="Print the analysis input JSON Schema")

    validate_analysis = subparsers.add_parser(
        "validate-analysis",
        help="Validate an analysis JSON payload before import or handoff",
    )
    validate_analysis.add_argument(
        "--json-file",
        default="-",
        help="Analysis JSON file to validate, or '-' for stdin",
    )
    validate_analysis.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    lease = subparsers.add_parser(
        "credential-lease",
        help="Validate a scoped runtime secret lease without printing the secret",
    )
    lease.add_argument("--secret-name", required=True, help="Human-readable secret handle")
    lease.add_argument("--env-var", required=True, help="Environment variable containing the secret")
    lease.add_argument(
        "--scope",
        action="append",
        required=True,
        help="Allowed action scope, for example obsidian:write",
    )
    lease.add_argument("--client-id", default="griosai-cli", help="Lease client identifier")
    lease.add_argument("--ttl-seconds", type=int, default=900, help="Lease TTL, max 3600 seconds")

    doctor = subparsers.add_parser("doctor", help="Run local safety and readiness checks")
    doctor.add_argument("--vault", default=None, help="Optional vault directory to inspect")
    doctor.add_argument("--repo", default=None, help="Optional repository directory to inspect")
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    vault_audit = subparsers.add_parser(
        "vault-audit",
        help="Inventory and integrity-check a GriosAI vault without reading raw content into output",
    )
    vault_audit.add_argument("--vault", required=True, help="Vault directory")
    vault_audit.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    lineage = subparsers.add_parser(
        "lineage-verify",
        help="Verify local analysis lineage manifests and artifact hashes",
    )
    lineage.add_argument("--vault", required=True, help="Vault directory")
    lineage.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    serve = subparsers.add_parser("serve", help="Run the local dashboard server")
    serve.add_argument("--vault", required=True, help="Vault directory")
    serve.add_argument("--host", default=None, help="Bind host; defaults to 127.0.0.1")
    serve.add_argument("--port", type=int, default=None, help="Bind port; defaults to 8765")
    serve.add_argument("--model", default=None, help="Ollama vision model")
    serve.add_argument("--ollama-url", default=None, help="Ollama base URL")
    serve.add_argument("--api-token", default=None, help="Bearer token for mutation APIs")
    serve.add_argument(
        "--allow-host",
        action="append",
        default=[],
        help="Additional allowed Host/Origin hostname for private proxies",
    )

    return parser


def _load_json_payload(path: str) -> dict[str, object]:
    parsed, source_bytes = _load_raw_json_payload(path)
    return require_valid_analysis_payload(parsed, source_bytes=source_bytes)


def _load_raw_json_payload(path: str) -> tuple[object, int]:
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    parsed = json.loads(text)
    return parsed, len(text.encode("utf-8"))


def _load_json_object(path: str) -> dict[str, object]:
    parsed, _source_bytes = _load_raw_json_payload(path)
    if not isinstance(parsed, dict):
        raise ValueError("JSON payload must be an object")
    return parsed


def _load_metrics(metrics_json: str, metrics_file: str | None) -> dict[str, object]:
    if metrics_file:
        return _load_json_object(metrics_file)
    parsed = json.loads(metrics_json)
    if not isinstance(parsed, dict):
        raise ValueError("--metrics-json must be a JSON object")
    return parsed


def _load_scores(scores_json: str, scores_file: str | None) -> dict[str, object]:
    if scores_file:
        return _load_json_object(scores_file)
    parsed = json.loads(scores_json)
    if not isinstance(parsed, dict):
        raise ValueError("--scores-json must be a JSON object")
    return parsed


def _load_usage(usage_json: str, usage_file: str | None) -> dict[str, object]:
    if usage_file:
        return _load_json_object(usage_file)
    parsed = json.loads(usage_json)
    if not isinstance(parsed, dict):
        raise ValueError("--usage-json must be a JSON object")
    return parsed


def _load_optional_text(path: str | None) -> str | None:
    if path is None:
        return None
    return Path(path).read_text(encoding="utf-8")


def _parse_csv_tuple(value: str | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    items = tuple(item.strip() for item in value.split(",") if item.strip())
    return items or None


def _parse_float_tuple(value: str | None) -> tuple[float, ...]:
    if value is None:
        return ()
    items = tuple(float(item.strip()) for item in value.split(",") if item.strip())
    if not items:
        raise ValueError("comma-separated float list must not be empty")
    return items


_CLI_USER_ERRORS = (
    AnalysisValidationError,
    CredentialBrokerError,
    FileExistsError,
    FileNotFoundError,
    ImageTooLargeError,
    json.JSONDecodeError,
    MlflowError,
    NotebookPacketError,
    ObsidianError,
    OllamaError,
    OSError,
    PermissionError,
    UnsupportedImageError,
    ValueError,
    VaultArchiveError,
)


def _format_cli_error(exc: BaseException) -> str:
    if isinstance(exc, json.JSONDecodeError):
        message = f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
    else:
        message = str(exc).strip() or exc.__class__.__name__
    lines = message.splitlines() or [exc.__class__.__name__]
    return "\n".join(
        f"error: {line}" if index == 0 else f"       {line}"
        for index, line in enumerate(lines)
    )


if __name__ == "__main__":
    raise SystemExit(main())
