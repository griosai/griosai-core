import io
import json
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import griosai.agent_harness as agent_harness_module
from griosai.agent_harness import (
    ExperimentSpec,
    adjudicate_agent_plan,
    advance_agent_pipeline,
    allocate_agent_traffic,
    assess_agent_readiness,
    assign_variant,
    audit_agent_harness,
    balance_agent_experiment,
    budget_agent_harness,
    check_agent_rollout_stage,
    claim_agent_run,
    compare_agent_experiment,
    create_agent_curriculum_plan,
    decide_agent_experiment,
    detect_agent_drift,
    create_agent_arena,
    create_agent_judge_panel,
    create_agent_matrix_plan,
    create_agent_plan,
    create_agent_pipeline,
    create_agent_run,
    create_agent_suite_plan,
    curate_agent_curriculum,
    cycle_agent_harness,
    dispatch_agent_plan,
    evaluate_agent_mix,
    evaluate_agent_slo,
    evaluate_agent_circuit,
    evolve_agent_experiment,
    gate_agent_plan,
    heartbeat_agent_claim,
    hold_agent_experiment,
    improve_agent_experiment,
    ingest_agent_results,
    log_agent_outcome,
    loop_agent_harness,
    merge_agent_plan,
    orchestrate_agent_dispatch,
    plan_agent_capacity,
    plan_agent_power,
    plan_agent_rollout,
    preflight_agent_harness,
    propose_agent_config,
    promote_agent_experiment,
    quorum_agent_plan,
    quarantine_agent_slice,
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
from griosai.brain import ensure_vault
from griosai.cli import main


AGENT_CONFIG = {
    "experiment": "Cross Model Agent",
    "description": "A/B model routing for local-first agent runs",
    "primary_metric": {"name": "quality", "direction": "maximize"},
    "rubric": {
        "aggregate_metric": "quality",
        "criteria": [
            {"name": "correctness", "weight": 0.5, "min": 0, "max": 1},
            {"name": "safety", "weight": 0.3, "min": 0, "max": 1},
            {"name": "efficiency", "weight": 0.2, "min": 0, "max": 1},
        ],
    },
    "min_trials_per_variant": 1,
    "guardrails": ["metadata only logs", "local vault artifacts"],
    "parallel": {
        "lanes": [
            {"id": "scout", "role": "scout", "objective": "map options"},
            {"id": "builder", "role": "implementer", "objective": "ship focused changes"},
            {"id": "reviewer", "role": "reviewer", "objective": "find risks"},
        ],
        "replicas": 1,
        "merge_strategy": "scoreboard",
    },
    "variants": [
        {
            "id": "claude-primary",
            "provider": "anthropic",
            "model": "claude-sonnet",
            "weight": 1,
            "adapter": "claude-code",
            "settings": {"temperature": 0.2, "max_tokens": 4096},
        },
        {
            "id": "openai-backup",
            "provider": "openai",
            "model": "gpt-model",
            "weight": 1,
            "adapter": "responses",
            "settings": {"temperature": 0.2},
        },
        {
            "id": "ollama-local",
            "provider": "ollama",
            "model": "qwen2.5:14b",
            "weight": 1,
        },
    ],
}


class AgentHarnessTests(unittest.TestCase):
    def test_create_agent_run_hashes_private_prompt_and_subject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            secret = "sk-" + ("C" * 24)
            prompt = f"Private customer request {secret}"

            result = create_agent_run(
                vault,
                AGENT_CONFIG,
                subject_key="thread-private-customer",
                prompt_text=prompt,
                prompt_source_name="/Users/gustavorios/private/prompt.md",
            )
            payload = json.loads(result.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)

            self.assertEqual(payload["schema"], "griosai.agent-run.v1")
            self.assertEqual(result.path.parent.parent.name, "cross-model-agent")
            self.assertIn(payload["selected_variant"]["provider"], {"anthropic", "openai", "ollama"})
            self.assertEqual(payload["prompt"]["chars"], len(prompt))
            self.assertEqual(len(payload["prompt"]["sha256"]), 64)
            self.assertNotIn(prompt, encoded)
            self.assertNotIn(secret, encoded)
            self.assertNotIn("thread-private-customer", encoded)
            self.assertNotIn("/Users/gustavorios", encoded)

    def test_assignment_is_deterministic_for_same_subject(self) -> None:
        spec = ExperimentSpec.from_mapping(AGENT_CONFIG)

        first, first_bucket = assign_variant(spec, "stable-thread")
        second, second_bucket = assign_variant(spec, "stable-thread")

        self.assertEqual(first.id, second.id)
        self.assertEqual(first_bucket, second_bucket)

    def test_outcome_logs_metrics_without_raw_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            run = create_agent_run(vault, AGENT_CONFIG, subject_key="outcome-thread")
            private_output = "Answer includes private local context"

            outcome = log_agent_outcome(
                vault,
                run_id=run.run_id,
                status="succeeded",
                metrics={"quality": 0.91, "latency_ms": 1200},
                usage={
                    "prompt_tokens": 100,
                    "completion_tokens": 40,
                    "latency_ms": 1200,
                    "cost_usd": 0.0123,
                },
                output_text=private_output,
                output_source_name="/Users/gustavorios/private/answer.md",
            )
            payload = json.loads(outcome.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)

            self.assertEqual(payload["schema"], "griosai.agent-outcome.v1")
            self.assertEqual(payload["metrics"]["quality"], 0.91)
            self.assertEqual(payload["usage"]["total_tokens"], 140)
            self.assertEqual(outcome.as_dict()["usage"]["cost_usd"], 0.0123)
            self.assertEqual(payload["output"]["chars"], len(private_output))
            self.assertEqual(len(payload["output"]["sha256"]), 64)
            self.assertNotIn(private_output, encoded)
            self.assertNotIn("/Users/gustavorios", encoded)

    def test_scorecard_logs_rubric_metrics_without_raw_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            run = create_agent_run(vault, AGENT_CONFIG, subject_key="score-thread")
            private_output = "Private scored answer"

            scorecard = score_agent_run(
                vault,
                run_id=run.run_id,
                scores={"correctness": 0.9, "safety": 1.0, "efficiency": 0.5},
                usage={"total_tokens": 250, "latency_ms": 900, "cost_usd": 0.02},
                output_text=private_output,
                output_source_name="/Users/gustavorios/private/scored.md",
            )
            payload = json.loads(scorecard.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)

            self.assertEqual(payload["schema"], "griosai.agent-scorecard.v1")
            self.assertAlmostEqual(payload["aggregate_score"], 0.85)
            self.assertEqual(payload["metrics"]["quality"], 0.85)
            self.assertEqual(payload["usage"]["total_tokens"], 250)
            self.assertEqual(scorecard.outcome.payload["metrics"]["quality"], 0.85)
            self.assertTrue(scorecard.report_path.exists())
            self.assertNotIn(private_output, encoded)
            self.assertNotIn("/Users/gustavorios", encoded)

    def test_ingest_batch_logs_results_and_rejects_raw_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            run_one = create_agent_run(vault, AGENT_CONFIG, subject_key="ingest-one")
            run_two = create_agent_run(vault, AGENT_CONFIG, subject_key="ingest-two")

            ingest = ingest_agent_results(
                vault,
                {
                    "results": [
                        {
                            "run_id": run_one.run_id,
                            "status": "succeeded",
                            "metrics": {"quality": 0.88},
                            "usage": {"total_tokens": 111, "latency_ms": 700, "cost_usd": 0.01},
                            "output": {
                                "present": True,
                                "chars": 42,
                                "sha256": "a" * 64,
                                "source_name": "worker-one.md",
                            },
                        },
                        {
                            "run_id": run_two.run_id,
                            "status": "succeeded",
                            "scores": {"correctness": 0.9, "safety": 1.0, "efficiency": 0.5},
                            "usage": {"total_tokens": 123, "latency_ms": 800, "cost_usd": 0.02},
                        },
                        {
                            "run_id": run_two.run_id,
                            "status": "failed",
                            "metrics": {"quality": 0.1},
                            "raw_output": "private raw worker result",
                        },
                    ]
                },
                source_name="/Users/gustavorios/private/results.json",
            )
            payload = json.loads(ingest.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = ingest.report_path.read_text(encoding="utf-8")
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)

            self.assertTrue(ingest.failed)
            self.assertEqual(payload["schema"], "griosai.agent-ingest.v1")
            self.assertEqual(payload["ingest_status"], "failed")
            self.assertEqual(payload["summary"]["requested_count"], 3)
            self.assertEqual(payload["summary"]["ingested_count"], 2)
            self.assertEqual(payload["summary"]["error_count"], 1)
            self.assertEqual(payload["summary"]["outcome_count"], 2)
            self.assertEqual(payload["summary"]["scorecard_count"], 1)
            self.assertEqual(payload["source"]["source_name"], "results.json")
            self.assertEqual(status.payload["summary"]["ingest_reports"], 1)
            self.assertIn("Agent Harness Ingest", report)
            self.assertIn(
                "results-ingested",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertNotIn("private raw worker result", encoded)
            self.assertNotIn("/Users/gustavorios", encoded)
            self.assertTrue(str(payload["entries"][0]["outcome_id"]).startswith("outcome-"))

    def test_scorecard_rejects_unknown_or_missing_rubric_scores(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            run = create_agent_run(vault, AGENT_CONFIG, subject_key="bad-score-thread")

            with self.assertRaises(ValueError):
                score_agent_run(
                    vault,
                    run_id=run.run_id,
                    scores={"correctness": 0.9, "safety": 1.0},
                )
            with self.assertRaises(ValueError):
                score_agent_run(
                    vault,
                    run_id=run.run_id,
                    scores={
                        "correctness": 0.9,
                        "safety": 1.0,
                        "efficiency": 0.5,
                        "extra": 0.1,
                    },
                )

    def test_improvement_loop_promotes_best_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            subjects = _subjects_by_variant(
                AGENT_CONFIG,
                {"claude-primary", "openai-backup", "ollama-local"},
            )
            scores = {"claude-primary": 0.95, "openai-backup": 0.6, "ollama-local": 0.7}
            for variant_id, subject in subjects.items():
                run = create_agent_run(vault, AGENT_CONFIG, subject_key=subject)
                self.assertEqual(run.variant_id, variant_id)
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": scores[variant_id]},
                )

            proposal = improve_agent_experiment(
                vault,
                experiment="cross-model-agent",
                min_trials_per_variant=1,
            )
            payload = json.loads(proposal.path.read_text(encoding="utf-8"))
            report = proposal.report_path.read_text(encoding="utf-8")

            self.assertEqual(payload["schema"], "griosai.agent-improvement.v1")
            self.assertEqual(payload["winner_variant_id"], "claude-primary")
            weights = {
                item["id"]: item["weight"]
                for item in payload["next_config"]["variants"]
            }
            self.assertEqual(weights["claude-primary"], 3.0)
            self.assertIn("claude-primary", report)
            self.assertNotIn("raw_output", report)

    def test_agent_memory_persists_lessons_without_raw_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            subjects = _subjects_by_variant(
                AGENT_CONFIG,
                {"claude-primary", "openai-backup"},
            )
            success = create_agent_run(vault, AGENT_CONFIG, subject_key=subjects["claude-primary"])
            failed = create_agent_run(vault, AGENT_CONFIG, subject_key=subjects["openai-backup"])
            log_agent_outcome(
                vault,
                run_id=success.run_id,
                status="succeeded",
                metrics={"quality": 0.94},
                usage={"total_tokens": 100, "latency_ms": 800, "cost_usd": 0.01},
            )
            log_agent_outcome(
                vault,
                run_id=failed.run_id,
                status="failed",
                metrics={"quality": 0.2},
                failure_code="adapter_timeout",
                output_text="private memory failure output",
            )

            memory = remember_agent_experiment(
                vault,
                experiment="cross-model-agent",
                min_trials_per_variant=1,
                max_lessons=8,
            )
            payload = json.loads(memory.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = memory.report_path.read_text(encoding="utf-8")
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)
            lesson_codes = {item["code"] for item in payload["lessons"]}

            self.assertEqual(payload["schema"], "griosai.agent-memory.v1")
            self.assertEqual(payload["summary"]["failed_outcomes"], 1)
            self.assertEqual(payload["summary"]["failure_mode_count"], 1)
            self.assertIn("top-failure-mode", lesson_codes)
            self.assertIn("missing-usage-metadata", lesson_codes)
            self.assertEqual(status.payload["summary"]["memories"], 1)
            self.assertIn(
                "memory-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertIn("Agent Harness Memory", report)
            self.assertNotIn("private memory", encoded)

    def test_curriculum_mines_hard_cases_without_raw_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="private curriculum subject",
                prompt_text="private curriculum prompt",
                lanes=("scout", "reviewer"),
            )
            for item in plan.runs:
                quality = 0.92
                status = "succeeded"
                failure_code = None
                if item.variant_id == "openai-backup":
                    quality = 0.31
                if item.variant_id == "ollama-local" and item.payload["parallel"]["lane_id"] == "reviewer":
                    quality = 0.1
                    status = "failed"
                    failure_code = "tool_error"
                log_agent_outcome(
                    vault,
                    run_id=item.run_id,
                    status=status,
                    metrics={"quality": quality},
                    failure_code=failure_code,
                    output_text=f"private curriculum output {item.variant_id}",
                )

            curriculum = curate_agent_curriculum(
                vault,
                experiment="cross-model-agent",
                metric_threshold=0.5,
                max_cases=6,
            )
            payload = json.loads(curriculum.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault, experiment="cross-model-agent")
            dashboard = write_agent_dashboard(vault, experiment="cross-model-agent")

            self.assertEqual(payload["schema"], "griosai.agent-curriculum.v1")
            self.assertEqual(payload["curriculum_status"], "ready")
            self.assertGreaterEqual(payload["summary"]["hard_case_count"], 2)
            self.assertGreaterEqual(payload["summary"]["failed_case_count"], 1)
            self.assertIn("openai-backup", payload["next_wave"]["focus_variants"])
            self.assertEqual(status.payload["summary"]["curricula"], 1)
            self.assertEqual(status.payload["experiments"][0]["latest_curriculum_status"], "ready")
            self.assertIn(
                "curriculum-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertIn("Curricula", dashboard.path.read_text(encoding="utf-8"))
            self.assertNotIn("private curriculum", encoded)

    def test_curriculum_plan_creates_focused_private_suite_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            suite_data = {
                "suite": "Curriculum Seed",
                "cases": [
                    {"id": "case-easy", "prompt": "private easy curriculum prompt"},
                    {"id": "case-hard", "prompt": "private hard curriculum prompt"},
                    {"id": "case-fail", "prompt": "private failing curriculum prompt"},
                ],
            }
            seed = create_agent_suite_plan(
                vault,
                AGENT_CONFIG,
                suite_data,
                subject_prefix="curriculum-seed",
                lanes=("scout", "reviewer"),
            )
            for plan in seed.plans:
                for run in plan.runs:
                    parallel = run.payload["parallel"]
                    case_id = parallel["case_id"]
                    lane_id = parallel["lane_id"]
                    quality = 0.95
                    status = "succeeded"
                    failure_code = None
                    if case_id == "case-hard" and run.variant_id == "openai-backup":
                        quality = 0.2
                    if case_id == "case-fail" and run.variant_id == "ollama-local" and lane_id == "reviewer":
                        quality = 0.1
                        status = "failed"
                        failure_code = "tool_error"
                    log_agent_outcome(
                        vault,
                        run_id=run.run_id,
                        status=status,
                        metrics={"quality": quality},
                        failure_code=failure_code,
                        output_text="private curriculum seed output",
                    )

            curriculum = curate_agent_curriculum(
                vault,
                experiment="cross-model-agent",
                metric_threshold=0.5,
                max_cases=4,
            )
            rerun = create_agent_curriculum_plan(
                vault,
                AGENT_CONFIG,
                suite_data,
                subject_prefix="curriculum-rerun",
                curriculum_id=curriculum.curriculum_id,
                baseline_variant_id="claude-primary",
                max_cases=2,
            )
            payload = json.loads(rerun.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            case_ids = {item["case_id"] for item in payload["cases"]}
            variant_ids = set(payload["parallel"]["matrix_variant_ids"])
            plan_contexts = [
                run.payload["parallel"]
                for plan in rerun.plans
                for run in plan.runs
            ]

            self.assertEqual(payload["schema"], "griosai.agent-suite.v1")
            self.assertEqual(payload["curriculum"]["curriculum_id"], curriculum.curriculum_id)
            self.assertEqual(case_ids, {"case-hard", "case-fail"})
            self.assertEqual(variant_ids, {"claude-primary", "openai-backup", "ollama-local"})
            self.assertTrue(all(context.get("curriculum_id") == curriculum.curriculum_id for context in plan_contexts))
            self.assertTrue(all(context.get("curriculum_case_rank") for context in plan_contexts))
            self.assertIn("curriculum", rerun.as_dict())
            self.assertNotIn("private", encoded)

            config_path = Path(tmp) / "agent-config.json"
            suite_path = Path(tmp) / "agent-suite.json"
            config_path.write_text(json.dumps(AGENT_CONFIG), encoding="utf-8")
            suite_path.write_text(json.dumps(suite_data), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-curriculum-plan",
                            "--vault",
                            str(vault),
                            "--config-file",
                            str(config_path),
                            "--suite-file",
                            str(suite_path),
                            "--subject-prefix",
                            "curriculum-cli-rerun",
                            "--curriculum-id",
                            curriculum.curriculum_id,
                            "--baseline-variant",
                            "claude-primary",
                            "--max-cases",
                            "1",
                            "--json",
                        ]
                    ),
                    0,
                )
            cli_payload = json.loads(output.getvalue())
            self.assertEqual(cli_payload["curriculum"]["curriculum_id"], curriculum.curriculum_id)
            self.assertEqual(cli_payload["case_count"], 1)
            self.assertTrue(Path(cli_payload["report_path"]).exists())
            self.assertNotIn("private hard curriculum prompt", output.getvalue())
            self.assertNotIn("private curriculum seed output", output.getvalue())

    def test_adaptive_allocation_recommends_cross_model_traffic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            subjects = _subjects_by_variant(
                AGENT_CONFIG,
                {"claude-primary", "openai-backup", "ollama-local"},
            )
            scores = {"claude-primary": 0.96, "openai-backup": 0.68, "ollama-local": 0.74}
            for variant_id, subject in subjects.items():
                run = create_agent_run(vault, AGENT_CONFIG, subject_key=subject)
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": scores[variant_id]},
                    usage={"total_tokens": 100, "latency_ms": 800, "cost_usd": 0.01},
                )

            allocation = allocate_agent_traffic(
                vault,
                experiment="cross-model-agent",
                strategy="ucb1",
                exploration_floor=0.05,
                max_share=0.8,
                min_trials_per_variant=1,
            )
            payload = json.loads(allocation.path.read_text(encoding="utf-8"))
            report = allocation.report_path.read_text(encoding="utf-8")
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)

            self.assertEqual(payload["schema"], "griosai.agent-allocation.v1")
            self.assertEqual(payload["winner_variant_id"], "claude-primary")
            shares = {
                item["variant_id"]: item["recommended_share"]
                for item in payload["allocations"]
            }
            self.assertGreater(shares["claude-primary"], shares["openai-backup"])
            self.assertGreater(shares["claude-primary"], shares["ollama-local"])
            weights = {
                item["id"]: item["weight"]
                for item in payload["next_config"]["variants"]
            }
            self.assertEqual(weights["claude-primary"], shares["claude-primary"])
            self.assertEqual(status.payload["summary"]["allocations"], 1)
            self.assertIn(
                "allocation-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertIn("Agent Harness Allocation", report)
            self.assertNotIn("/Users/gustavorios", json.dumps(payload, sort_keys=True))

    def test_lane_routing_recommends_different_models_per_agent_role(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="lane-route-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            for run in plan.runs:
                parallel = run.payload["parallel"]
                lane_id = str(parallel["lane_id"])
                if lane_id == "scout":
                    quality = 0.96 if run.variant_id == "openai-backup" else 0.55
                else:
                    quality = 0.97 if run.variant_id == "claude-primary" else 0.5
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": quality},
                    usage={"total_tokens": 100, "latency_ms": 800, "cost_usd": 0.01},
                )

            route = route_agent_lanes(
                vault,
                experiment="cross-model-agent",
                strategy="ucb1",
                min_trials_per_lane_variant=1,
            )
            payload = json.loads(route.path.read_text(encoding="utf-8"))
            report = route.report_path.read_text(encoding="utf-8")
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)
            by_lane = {item["lane_id"]: item for item in payload["lane_policies"]}

            self.assertEqual(payload["schema"], "griosai.agent-route.v1")
            self.assertEqual(payload["summary"]["lane_count"], 2)
            self.assertEqual(payload["summary"]["recommended_routes"], 2)
            self.assertEqual(by_lane["scout"]["winner_variant_id"], "openai-backup")
            self.assertEqual(by_lane["reviewer"]["winner_variant_id"], "claude-primary")
            self.assertEqual(status.payload["summary"]["routes"], 1)
            self.assertIn(
                "route-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertIn("Agent Harness Route", report)
            self.assertNotIn("lane-route-thread", json.dumps(payload, sort_keys=True))

    def test_promotion_proposal_requires_evidence_and_writes_patch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            subjects = _subjects_by_variant_count(
                AGENT_CONFIG,
                {"claude-primary", "openai-backup", "ollama-local"},
                count=2,
            )
            scores = {
                "claude-primary": (0.62, 0.64),
                "openai-backup": (0.91, 0.94),
                "ollama-local": (0.7, 0.72),
            }
            for variant_id, variant_subjects in subjects.items():
                for index, subject in enumerate(variant_subjects):
                    run = create_agent_run(vault, AGENT_CONFIG, subject_key=subject)
                    self.assertEqual(run.variant_id, variant_id)
                    log_agent_outcome(
                        vault,
                        run_id=run.run_id,
                        status="succeeded",
                        metrics={"quality": scores[variant_id][index]},
                        output_text=f"private output for {variant_id}",
                    )

            promotion = promote_agent_experiment(
                vault,
                experiment="cross-model-agent",
                champion_variant_id="claude-primary",
                min_trials_per_variant=2,
                min_delta=0.1,
            )
            payload = json.loads(promotion.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = promotion.report_path.read_text(encoding="utf-8")

            self.assertTrue(promotion.ready)
            self.assertEqual(payload["schema"], "griosai.agent-promotion.v1")
            self.assertEqual(payload["promotion_status"], "ready")
            self.assertEqual(payload["candidate_variant_id"], "openai-backup")
            self.assertGreater(payload["evidence"]["metric_gap"], 0.1)
            self.assertTrue(payload["patch"]["operations"])
            self.assertIn("Agent Harness Promotion", report)
            self.assertNotIn("private output", encoded)

    def test_promotion_holds_when_variants_are_under_sampled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            run = create_agent_run(vault, AGENT_CONFIG, subject_key="one-sample")
            log_agent_outcome(
                vault,
                run_id=run.run_id,
                status="succeeded",
                metrics={"quality": 0.9},
            )

            promotion = promote_agent_experiment(
                vault,
                experiment="cross-model-agent",
                min_trials_per_variant=2,
            )

            self.assertFalse(promotion.ready)
            self.assertEqual(promotion.payload["promotion_status"], "collect-more-data")
            self.assertTrue(promotion.payload["evidence"]["under_sampled_variants"])
            self.assertFalse(promotion.payload["patch"]["operations"])

    def test_comparison_reports_pairwise_confidence_without_raw_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            subjects = _subjects_by_variant_count(
                AGENT_CONFIG,
                {"claude-primary", "openai-backup", "ollama-local"},
                count=3,
            )
            scores = {
                "claude-primary": (0.6, 0.61, 0.62),
                "openai-backup": (0.91, 0.93, 0.95),
                "ollama-local": (0.72, 0.73, 0.74),
            }
            for variant_id, variant_subjects in subjects.items():
                for index, subject in enumerate(variant_subjects):
                    run = create_agent_run(vault, AGENT_CONFIG, subject_key=subject)
                    self.assertEqual(run.variant_id, variant_id)
                    log_agent_outcome(
                        vault,
                        run_id=run.run_id,
                        status="succeeded",
                        metrics={"quality": scores[variant_id][index]},
                        usage={
                            "total_tokens": 100 + index,
                            "latency_ms": 1000 + (index * 10),
                            "cost_usd": 0.01 + (index * 0.001),
                        },
                        output_text=f"private compare output {variant_id}",
                    )

            comparison = compare_agent_experiment(
                vault,
                experiment="cross-model-agent",
                baseline_variant_id="claude-primary",
                min_samples_per_variant=3,
            )
            payload = json.loads(comparison.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = comparison.report_path.read_text(encoding="utf-8")
            by_candidate = {item["candidate_variant_id"]: item for item in payload["pairwise"]}
            by_variant = {item["variant_id"]: item for item in payload["variant_summaries"]}

            self.assertEqual(payload["schema"], "griosai.agent-comparison.v1")
            self.assertEqual(payload["baseline_variant_id"], "claude-primary")
            self.assertEqual(payload["winner_variant_id"], "openai-backup")
            self.assertEqual(payload["summary"]["eligible_variant_count"], 3)
            self.assertEqual(by_variant["openai-backup"]["usage"]["total_tokens_mean"], 101.0)
            self.assertEqual(by_variant["openai-backup"]["usage"]["latency_ms_count"], 3)
            self.assertEqual(payload["efficiency_frontier"][0]["variant_id"], "openai-backup")
            self.assertGreater(payload["efficiency_frontier"][0]["metric_per_1k_tokens"], 0)
            self.assertEqual(by_candidate["openai-backup"]["status"], "beats-baseline")
            self.assertGreater(by_candidate["openai-backup"]["directional_delta"], 0.2)
            self.assertIn("Agent Harness Comparison", report)
            self.assertNotIn("private compare output", encoded)

    def test_balance_reports_matrix_coverage_before_ab_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="balance-thread",
                lanes=("scout", "reviewer"),
            )
            for run in plan.runs[:-1]:
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": 0.8},
                )

            partial = balance_agent_experiment(
                vault,
                experiment="cross-model-agent",
                plan_id=plan.plan_id,
                dimensions=("variant", "lane"),
                min_count_per_cell=1,
                max_skew=0,
            )
            partial_payload = json.loads(partial.path.read_text(encoding="utf-8"))

            self.assertEqual(partial_payload["schema"], "griosai.agent-balance.v1")
            self.assertEqual(partial_payload["balance_status"], "insufficient")
            self.assertFalse(partial.balanced)
            self.assertEqual(partial_payload["summary"]["cell_count"], 6)
            self.assertEqual(partial_payload["summary"]["missing_runs"], 1)

            log_agent_outcome(
                vault,
                run_id=plan.runs[-1].run_id,
                status="succeeded",
                metrics={"quality": 0.82},
            )
            balanced = balance_agent_experiment(
                vault,
                experiment="cross-model-agent",
                plan_id=plan.plan_id,
                dimensions=("variant", "lane"),
                min_count_per_cell=1,
                max_skew=0,
            )
            payload = json.loads(balanced.path.read_text(encoding="utf-8"))
            status = summarize_agent_harness(vault, experiment="cross-model-agent")
            timeline = timeline_agent_harness(vault, experiment="cross-model-agent")
            report = balanced.report_path.read_text(encoding="utf-8")

            self.assertEqual(payload["balance_status"], "balanced")
            self.assertTrue(balanced.balanced)
            self.assertEqual(payload["summary"]["sample_skew"], 0)
            self.assertEqual(status.payload["summary"]["balances"], 2)
            self.assertEqual(status.payload["experiments"][0]["latest_balance_status"], "balanced")
            self.assertIn(
                "balance-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertIn("Agent Harness Balance", report)

    def test_balance_can_gate_promotion_and_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="balance-gate-thread",
                lanes=("scout", "reviewer"),
            )
            scores = {
                "claude-primary": 0.72,
                "openai-backup": 0.92,
                "ollama-local": 0.66,
            }
            for run in plan.runs[:-1]:
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": scores[run.variant_id]},
                )

            partial = balance_agent_experiment(
                vault,
                experiment="cross-model-agent",
                plan_id=plan.plan_id,
                dimensions=("variant", "lane"),
                min_count_per_cell=1,
                max_skew=0,
            )
            blocked = promote_agent_experiment(
                vault,
                experiment="cross-model-agent",
                champion_variant_id="claude-primary",
                min_trials_per_variant=1,
                min_delta=0.05,
                require_balance=True,
            )
            blocked_readiness = assess_agent_readiness(
                vault,
                experiment="cross-model-agent",
                min_outcomes=len(plan.runs) - 1,
                require_balance=True,
            )
            blocked_codes = {item["code"] for item in blocked_readiness.payload["findings"]}

            self.assertFalse(partial.balanced)
            self.assertEqual(blocked.payload["promotion_status"], "blocked-by-balance")
            self.assertEqual(blocked.payload["evidence"]["latest_balance"]["balance_status"], "insufficient")
            self.assertTrue(blocked.payload["policy"]["require_balance"])
            self.assertFalse(blocked_readiness.ready)
            self.assertIn("balance-not-passing", blocked_codes)

            last_run = plan.runs[-1]
            log_agent_outcome(
                vault,
                run_id=last_run.run_id,
                status="succeeded",
                metrics={"quality": scores[last_run.variant_id]},
            )
            balanced = balance_agent_experiment(
                vault,
                experiment="cross-model-agent",
                plan_id=plan.plan_id,
                dimensions=("variant", "lane"),
                min_count_per_cell=1,
                max_skew=0,
            )
            ready = promote_agent_experiment(
                vault,
                experiment="cross-model-agent",
                champion_variant_id="claude-primary",
                min_trials_per_variant=1,
                min_delta=0.05,
                require_balance=True,
            )
            ready_readiness = assess_agent_readiness(
                vault,
                experiment="cross-model-agent",
                min_outcomes=len(plan.runs),
                require_balance=True,
            )

            self.assertTrue(balanced.balanced)
            self.assertTrue(ready.ready)
            self.assertEqual(ready.payload["promotion_status"], "ready")
            self.assertEqual(ready.payload["evidence"]["latest_balance"]["balance_status"], "balanced")
            self.assertTrue(ready_readiness.ready)
            self.assertEqual(
                ready_readiness.payload["evidence"]["latest_balance"]["balance_status"],
                "balanced",
            )

    def test_decision_stops_for_confident_candidate_without_raw_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            subjects = _subjects_by_variant_count(
                AGENT_CONFIG,
                {"claude-primary", "openai-backup", "ollama-local"},
                count=3,
            )
            scores = {
                "claude-primary": (0.70, 0.71, 0.72),
                "openai-backup": (0.91, 0.92, 0.93),
                "ollama-local": (0.74, 0.75, 0.76),
            }
            for variant_id, variant_subjects in subjects.items():
                for index, subject in enumerate(variant_subjects):
                    run = create_agent_run(vault, AGENT_CONFIG, subject_key=subject)
                    log_agent_outcome(
                        vault,
                        run_id=run.run_id,
                        status="succeeded",
                        metrics={"quality": scores[variant_id][index]},
                        usage={
                            "total_tokens": 100,
                            "latency_ms": 900,
                            "cost_usd": 0.01,
                        },
                        output_text=f"private decision output {variant_id}",
                    )

            decision = decide_agent_experiment(
                vault,
                experiment="cross-model-agent",
                baseline_variant_id="claude-primary",
                candidate_variant_id="openai-backup",
                min_samples_per_variant=3,
                min_delta=0.05,
                confidence_threshold=0.8,
                max_cost_usd=1.0,
                max_total_tokens=1000,
                candidate_metric_floor=0.8,
            )
            payload = json.loads(decision.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault, experiment="cross-model-agent")
            dashboard = write_agent_dashboard(vault, experiment="cross-model-agent")

            self.assertEqual(payload["schema"], "griosai.agent-decision.v1")
            self.assertEqual(payload["decision"], "stop-promote")
            self.assertEqual(payload["decision_status"], "ready")
            self.assertEqual(payload["candidate_variant_id"], "openai-backup")
            self.assertGreater(payload["summary"]["confidence"], 0.8)
            self.assertEqual(payload["guardrails"]["status"], "pass")
            self.assertEqual(status.payload["summary"]["decisions"], 1)
            self.assertEqual(status.payload["experiments"][0]["latest_decision"], "stop-promote")
            self.assertIn(
                "decision-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertIn("Decisions", dashboard.path.read_text(encoding="utf-8"))
            self.assertNotIn("private decision output", encoded)

    def test_parallel_plan_creates_lane_child_runs_without_raw_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            secret = "sk-" + ("D" * 24)
            prompt = f"Private parallel prompt {secret}"

            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="parallel-private-thread",
                prompt_text=prompt,
                prompt_source_name="/Users/gustavorios/private/parallel.md",
                lanes=("scout", "builder"),
                replicas=2,
            )
            payload = json.loads(plan.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)

            self.assertEqual(payload["schema"], "griosai.agent-plan.v1")
            self.assertEqual(payload["parallel"]["run_count"], 4)
            self.assertEqual(len(plan.runs), 4)
            self.assertNotIn(prompt, encoded)
            self.assertNotIn(secret, encoded)
            self.assertNotIn("parallel-private-thread", encoded)
            self.assertNotIn("/Users/gustavorios", encoded)
            for run in plan.runs:
                run_payload = json.loads(run.path.read_text(encoding="utf-8"))
                self.assertEqual(run_payload["parallel"]["plan_id"], plan.plan_id)
                self.assertIn(run_payload["parallel"]["lane_id"], {"scout", "builder"})

    def test_matrix_plan_covers_every_variant_per_lane_and_replica(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            secret = "sk-" + ("M" * 24)
            prompt = f"Private matrix prompt {secret}"

            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="matrix-private-thread",
                prompt_text=prompt,
                prompt_source_name="/Users/gustavorios/private/matrix.md",
                lanes=("scout", "reviewer"),
                replicas=2,
            )
            payload = json.loads(plan.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            expected_variants = {"claude-primary", "openai-backup", "ollama-local"}

            self.assertEqual(payload["schema"], "griosai.agent-plan.v1")
            self.assertEqual(payload["parallel"]["strategy"], "variant-matrix")
            self.assertEqual(payload["parallel"]["variant_count"], 3)
            self.assertEqual(payload["parallel"]["run_count"], 12)
            self.assertEqual(len(plan.runs), 12)
            self.assertNotIn(prompt, encoded)
            self.assertNotIn(secret, encoded)
            self.assertNotIn("/Users/gustavorios", encoded)
            for lane in ("scout", "reviewer"):
                for replica in (1, 2):
                    variants = {
                        item["variant_id"]
                        for item in payload["runs"]
                        if item["lane_id"] == lane and item["replica"] == replica
                    }
                    self.assertEqual(variants, expected_variants)
            for run in plan.runs:
                run_payload = json.loads(run.path.read_text(encoding="utf-8"))
                self.assertEqual(run_payload["assignment"]["strategy"], "variant-matrix")
                self.assertEqual(
                    run_payload["assignment"]["forced_variant_id"],
                    run_payload["selected_variant"]["id"],
                )
                self.assertTrue(run_payload["parallel"]["matrix_cell"])

    def test_arena_creates_round_robin_matches_and_reports_champion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            secret = "sk-" + ("A" * 24)
            prompt = f"Private arena prompt {secret}"

            arena = create_agent_arena(
                vault,
                AGENT_CONFIG,
                subject_key="arena-private-thread",
                prompt_text=prompt,
                prompt_source_name="/Users/gustavorios/private/arena.md",
                lanes=("reviewer",),
                replicas=1,
            )
            payload = json.loads(arena.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)

            self.assertEqual(payload["schema"], "griosai.agent-arena.v1")
            self.assertEqual(payload["arena_status"], "scheduled")
            self.assertEqual(payload["summary"]["pair_count"], 3)
            self.assertEqual(payload["summary"]["scheduled_matches"], 3)
            self.assertEqual(payload["summary"]["scheduled_runs"], 6)
            self.assertEqual(len(payload["matches"]), 3)
            self.assertTrue(payload["plan_id"])
            self.assertTrue(Path(str(payload["plan_path"])).exists() or payload["plan_path"])
            self.assertNotIn(prompt, encoded)
            self.assertNotIn(secret, encoded)
            self.assertNotIn("arena-private-thread", encoded)
            self.assertNotIn("/Users/gustavorios", encoded)
            for run in arena.runs:
                run_payload = json.loads(run.path.read_text(encoding="utf-8"))
                self.assertEqual(run_payload["assignment"]["strategy"], "arena-round-robin")
                self.assertEqual(run_payload["parallel"]["arena_id"], arena.arena_id)
                self.assertIn(run_payload["parallel"]["arena_role"], {"a", "b"})
                quality = {
                    "openai-backup": 0.95,
                    "claude-primary": 0.82,
                    "ollama-local": 0.55,
                }[run.variant_id]
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": quality},
                    usage={"total_tokens": 100, "latency_ms": 700, "cost_usd": 0.01},
                    output_text="private arena output",
                )

            report = report_agent_arena(vault, arena_id=arena.arena_id)
            report_payload = json.loads(report.path.read_text(encoding="utf-8"))
            report_encoded = json.dumps(report_payload, sort_keys=True)
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)
            leaderboard = write_agent_leaderboard(
                vault,
                experiment="cross-model-agent",
                baseline_variant_id="claude-primary",
                min_samples_per_variant=1,
            )
            leaderboard_payload = json.loads(leaderboard.path.read_text(encoding="utf-8"))

            self.assertEqual(report_payload["schema"], "griosai.agent-arena-report.v1")
            self.assertEqual(report_payload["report_status"], "complete")
            self.assertEqual(report_payload["winner_variant_id"], "openai-backup")
            self.assertEqual(report_payload["summary"]["complete_matches"], 3)
            self.assertEqual(report_payload["variant_summaries"][0]["variant_id"], "openai-backup")
            self.assertEqual(status.payload["summary"]["arenas"], 1)
            self.assertEqual(status.payload["summary"]["arena_reports"], 1)
            self.assertEqual(status.payload["experiments"][0]["latest_arena_winner"], "openai-backup")
            event_types = {event["event_type"] for event in timeline.payload["events"]}
            self.assertIn("arena-created", event_types)
            self.assertIn("arena-reported", event_types)
            self.assertIn("arena_report", leaderboard_payload["source_artifacts"])
            openai_row = next(
                item for item in leaderboard_payload["leaderboard"] if item["variant_id"] == "openai-backup"
            )
            self.assertEqual(openai_row["evidence"]["arena"]["status"], "champion")
            self.assertNotIn("private arena output", report_encoded)

    def test_judge_panel_creates_independent_judge_runs_and_reports_winner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            secret = "sk-" + ("B" * 24)
            prompt = f"Private judge source prompt {secret}"

            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="judge-private-thread",
                prompt_text=prompt,
                prompt_source_name="/Users/gustavorios/private/judge.md",
                lanes=("builder",),
                replicas=1,
            )
            for run in plan.runs:
                quality = {
                    "openai-backup": 0.94,
                    "claude-primary": 0.81,
                    "ollama-local": 0.52,
                }[run.variant_id]
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": quality},
                    usage={"total_tokens": 90, "latency_ms": 600, "cost_usd": 0.01},
                    output_text="private source output for judge panel",
                )

            panel = create_agent_judge_panel(
                vault,
                AGENT_CONFIG,
                plan_id=plan.plan_id,
                judge_variants=("claude-primary", "openai-backup"),
                replicas=1,
            )
            panel_payload = json.loads(panel.path.read_text(encoding="utf-8"))
            panel_encoded = json.dumps(panel_payload, sort_keys=True)

            self.assertEqual(panel_payload["schema"], "griosai.agent-judge-panel.v1")
            self.assertEqual(panel_payload["panel_status"], "scheduled")
            self.assertEqual(panel_payload["summary"]["target_count"], 3)
            self.assertEqual(panel_payload["summary"]["scheduled_runs"], 4)
            self.assertTrue(panel_payload["plan_id"])
            self.assertTrue(panel.plan_path)
            self.assertNotIn(prompt, panel_encoded)
            self.assertNotIn(secret, panel_encoded)
            self.assertNotIn("judge-private-thread", panel_encoded)
            self.assertNotIn("/Users/gustavorios", panel_encoded)
            self.assertNotIn("private source output for judge panel", panel_encoded)

            for run in panel.runs:
                run_payload = json.loads(run.path.read_text(encoding="utf-8"))
                parallel = run_payload["parallel"]
                self.assertEqual(run_payload["assignment"]["strategy"], "judge-panel")
                self.assertEqual(parallel["judge_panel_id"], panel.panel_id)
                self.assertEqual(parallel["source_plan_id"], plan.plan_id)
                self.assertNotEqual(parallel["judge_variant_id"], parallel["target_variant_id"])
                score = {
                    "openai-backup": 0.97,
                    "claude-primary": 0.84,
                    "ollama-local": 0.48,
                }[parallel["target_variant_id"]]
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"judge_score": score},
                    usage={"total_tokens": 70, "latency_ms": 450, "cost_usd": 0.01},
                    output_text="private judge rationale",
                )

            report = report_agent_judge_panel(vault, panel_id=panel.panel_id)
            report_payload = json.loads(report.path.read_text(encoding="utf-8"))
            report_encoded = json.dumps(report_payload, sort_keys=True)
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)
            dashboard = write_agent_dashboard(vault, experiment="cross-model-agent")
            leaderboard = write_agent_leaderboard(
                vault,
                experiment="cross-model-agent",
                baseline_variant_id="claude-primary",
                min_samples_per_variant=1,
            )
            leaderboard_payload = json.loads(leaderboard.path.read_text(encoding="utf-8"))

            self.assertEqual(report_payload["schema"], "griosai.agent-judge-panel-report.v1")
            self.assertEqual(report_payload["report_status"], "complete")
            self.assertEqual(report_payload["winner_variant_id"], "openai-backup")
            self.assertEqual(report_payload["summary"]["completed_judgements"], 4)
            self.assertEqual(report_payload["variant_summaries"][0]["variant_id"], "openai-backup")
            self.assertEqual(status.payload["summary"]["judge_panels"], 1)
            self.assertEqual(status.payload["summary"]["judge_reports"], 1)
            self.assertEqual(status.payload["experiments"][0]["latest_judge_winner"], "openai-backup")
            event_types = {event["event_type"] for event in timeline.payload["events"]}
            self.assertIn("judge-panel-created", event_types)
            self.assertIn("judge-panel-reported", event_types)
            self.assertIn("judge_report", leaderboard_payload["source_artifacts"])
            openai_row = next(
                item for item in leaderboard_payload["leaderboard"] if item["variant_id"] == "openai-backup"
            )
            self.assertEqual(openai_row["evidence"]["judge"]["status"], "winner")
            self.assertIn("Judge Panels", dashboard.path.read_text(encoding="utf-8"))
            self.assertNotIn("private source output for judge panel", report_encoded)
            self.assertNotIn("private judge rationale", report_encoded)

    def test_pipeline_advances_dependency_gated_stage_plans(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            secret = "sk-" + ("C" * 24)
            prompt = f"Private pipeline prompt {secret}"
            pipeline_data = {
                "pipeline": "Ship Loop",
                "stages": [
                    {
                        "id": "scout",
                        "lanes": ["scout"],
                        "mode": "weighted",
                        "replicas": 1,
                        "min_success_ratio": 1,
                    },
                    {
                        "id": "build",
                        "depends_on": ["scout"],
                        "lanes": ["builder"],
                        "mode": "matrix",
                        "replicas": 1,
                        "min_success_ratio": 1,
                    },
                    {
                        "id": "review",
                        "depends_on": ["build"],
                        "lanes": ["reviewer"],
                        "mode": "weighted",
                        "replicas": 1,
                        "min_success_ratio": 1,
                    },
                ],
            }

            pipeline = create_agent_pipeline(
                vault,
                AGENT_CONFIG,
                pipeline_data,
                subject_prefix="pipeline-private-thread",
                prompt_text=prompt,
                prompt_source_name="/Users/gustavorios/private/pipeline.md",
            )
            payload = json.loads(pipeline.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)

            self.assertEqual(payload["schema"], "griosai.agent-pipeline.v1")
            self.assertEqual(payload["pipeline_status"], "scheduled")
            self.assertEqual(payload["summary"]["stage_count"], 3)
            self.assertEqual(payload["summary"]["planned_stages"], 1)
            self.assertEqual(len(pipeline.plans), 1)
            self.assertEqual(payload["stage_statuses"][0]["stage_id"], "scout")
            self.assertEqual(payload["stage_statuses"][1]["stage_status"], "waiting")
            self.assertNotIn(prompt, encoded)
            self.assertNotIn(secret, encoded)
            self.assertNotIn("pipeline-private-thread", encoded)
            self.assertNotIn("/Users/gustavorios", encoded)

            for run in pipeline.plans[0].runs:
                run_payload = json.loads(run.path.read_text(encoding="utf-8"))
                self.assertEqual(run_payload["parallel"]["pipeline_id"], pipeline.pipeline_id)
                self.assertEqual(run_payload["parallel"]["stage_id"], "scout")
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": 0.8},
                    output_text="private scout output",
                )

            first_advance = advance_agent_pipeline(vault, pipeline_id=pipeline.pipeline_id)
            first_payload = json.loads(first_advance.path.read_text(encoding="utf-8"))
            first_encoded = json.dumps(first_payload, sort_keys=True)
            self.assertEqual(first_payload["schema"], "griosai.agent-pipeline-advance.v1")
            self.assertEqual(first_payload["advance_status"], "advanced")
            self.assertEqual(first_payload["summary"]["planned_stages"], 2)
            self.assertEqual(len(first_advance.plans), 1)
            self.assertEqual(first_advance.plans[0].payload["pipeline"]["stage_id"], "build")
            self.assertEqual(len(first_advance.plans[0].runs), 3)
            self.assertNotIn("private scout output", first_encoded)

            for run in first_advance.plans[0].runs:
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": 0.9},
                    output_text="private build output",
                )

            second_advance = advance_agent_pipeline(vault, pipeline_id=pipeline.pipeline_id)
            second_payload = json.loads(second_advance.path.read_text(encoding="utf-8"))
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)
            audit = audit_agent_harness(vault)
            dashboard = write_agent_dashboard(vault, experiment="cross-model-agent")
            self.assertEqual(second_payload["advance_status"], "advanced")
            self.assertEqual(second_payload["summary"]["planned_stages"], 3)
            self.assertEqual(len(second_advance.plans), 1)
            self.assertEqual(second_advance.plans[0].payload["pipeline"]["stage_id"], "review")
            self.assertEqual(status.payload["summary"]["pipelines"], 1)
            self.assertEqual(status.payload["summary"]["pipeline_advances"], 2)
            event_types = {event["event_type"] for event in timeline.payload["events"]}
            self.assertIn("pipeline-created", event_types)
            self.assertIn("pipeline-advanced", event_types)
            self.assertEqual(audit.payload["experiments"][0]["counts"]["pipelines"], 1)
            self.assertIn("Pipelines", dashboard.path.read_text(encoding="utf-8"))
            self.assertNotIn(
                "private build output",
                json.dumps(second_payload, sort_keys=True),
            )

    def test_parallel_merge_selects_best_completed_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="merge-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            log_agent_outcome(
                vault,
                run_id=plan.runs[0].run_id,
                status="succeeded",
                metrics={"quality": 0.72},
                output_text="private answer one",
            )
            log_agent_outcome(
                vault,
                run_id=plan.runs[1].run_id,
                status="succeeded",
                metrics={"quality": 0.93},
                output_text="private answer two",
            )

            merge = merge_agent_plan(vault, plan_id=plan.plan_id)
            payload = json.loads(merge.path.read_text(encoding="utf-8"))
            report = merge.report_path.read_text(encoding="utf-8")

            self.assertEqual(payload["schema"], "griosai.agent-merge.v1")
            self.assertEqual(payload["merge_status"], "complete")
            self.assertEqual(payload["recommended_run_id"], plan.runs[1].run_id)
            self.assertEqual(len(payload["lane_summaries"]), 2)
            self.assertNotIn("private answer", json.dumps(payload, sort_keys=True))
            self.assertIn("Agent Harness Merge", report)

    def test_adjudication_creates_parallel_decision_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="adjudicate-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            log_agent_outcome(
                vault,
                run_id=plan.runs[0].run_id,
                status="succeeded",
                metrics={"quality": 0.81},
                output_text="private decision one",
            )
            log_agent_outcome(
                vault,
                run_id=plan.runs[1].run_id,
                status="succeeded",
                metrics={"quality": 0.91},
                output_text="private decision two",
            )
            merge_agent_plan(vault, plan_id=plan.plan_id)
            gate_agent_plan(vault, plan_id=plan.plan_id, metric_threshold=0.8)

            adjudication = adjudicate_agent_plan(
                vault,
                plan_id=plan.plan_id,
                min_consensus_ratio=0.0,
            )
            payload = json.loads(adjudication.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = adjudication.report_path.read_text(encoding="utf-8")

            self.assertTrue(adjudication.accepted)
            self.assertEqual(payload["schema"], "griosai.agent-adjudication.v1")
            self.assertEqual(payload["decision_status"], "accepted")
            self.assertEqual(payload["recommended_run_id"], plan.runs[1].run_id)
            self.assertEqual(len(payload["lane_decisions"]), 2)
            self.assertIn("adjudication-accepted", encoded)
            self.assertNotIn("private decision", encoded)
            self.assertIn("Agent Harness Adjudication", report)

    def test_quorum_detects_split_brain_lane_votes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="quorum-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            for run in plan.runs:
                lane = str(run.payload["parallel"]["lane_id"])
                if lane == "scout":
                    quality = 0.96 if run.variant_id == "openai-backup" else 0.55
                else:
                    quality = 0.97 if run.variant_id == "claude-primary" else 0.5
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": quality},
                    output_text="private quorum output",
                )

            quorum = quorum_agent_plan(
                vault,
                plan_id=plan.plan_id,
                min_agreement_ratio=0.75,
            )
            payload = json.loads(quorum.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = quorum.report_path.read_text(encoding="utf-8")
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)
            finding_codes = {item["code"] for item in payload["findings"]}

            self.assertFalse(quorum.passed)
            self.assertEqual(payload["schema"], "griosai.agent-quorum.v1")
            self.assertEqual(payload["quorum_status"], "split-brain")
            self.assertTrue(payload["consensus"]["split_brain"])
            self.assertEqual(payload["consensus"]["agreement_ratio"], 0.5)
            self.assertIn("split-brain-tie", finding_codes)
            self.assertEqual(status.payload["summary"]["quorums"], 1)
            self.assertIn(
                "quorum-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertIn("Agent Harness Quorum", report)
            self.assertNotIn("private quorum", encoded)

    def test_audit_passes_consistent_agent_graph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="audit-pass-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            for run in plan.runs:
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": 0.9},
                    output_text="private audit output",
                )
            merge_agent_plan(vault, plan_id=plan.plan_id)
            gate_agent_plan(vault, plan_id=plan.plan_id, metric_threshold=0.8)
            adjudicate_agent_plan(vault, plan_id=plan.plan_id, min_consensus_ratio=0)

            audit = audit_agent_harness(vault)
            payload = json.loads(audit.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = audit.report_path.read_text(encoding="utf-8")

            self.assertFalse(audit.failed)
            self.assertEqual(payload["schema"], "griosai.agent-audit.v1")
            self.assertEqual(payload["summary"]["fail"], 0)
            self.assertIn("artifact-graph-consistent", encoded)
            self.assertNotIn("private audit output", encoded)
            self.assertIn("Agent Harness Audit", report)

    def test_manifest_snapshots_and_verifies_agent_artifact_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="manifest-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            for run in plan.runs:
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": 0.9},
                    output_text="private manifest output",
                )

            manifest = write_agent_manifest(vault, experiment="cross-model-agent")
            payload = json.loads(manifest.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = manifest.report_path.read_text(encoding="utf-8")
            artifact_paths = {item["path"] for item in payload["artifacts"]}

            self.assertEqual(payload["schema"], "griosai.agent-manifest.v1")
            self.assertEqual(payload["scope"]["experiment"], "cross-model-agent")
            self.assertGreaterEqual(payload["summary"]["artifact_count"], 3)
            self.assertIn("runs", payload["summary"]["artifact_type_counts"])
            self.assertIn("plans", payload["summary"]["artifact_type_counts"])
            self.assertIn("Agent Harness Manifest", report)
            self.assertIn("agent-runs/cross-model-agent/plans/", "\n".join(artifact_paths))
            self.assertNotIn("private manifest output", encoded)
            self.assertNotIn("manifest-thread", encoded)

            verified = verify_agent_manifest(vault, manifest_id=manifest.manifest_id)
            self.assertTrue(verified.verified)
            self.assertEqual(verified.payload["verification_status"], "verified")

            first_run_path = plan.runs[0].path
            first_run_path.write_text(
                first_run_path.read_text(encoding="utf-8") + "\n",
                encoding="utf-8",
            )
            failed = verify_agent_manifest(vault, manifest_id=manifest.manifest_id)
            codes = {item["code"] for item in failed.payload["findings"]}

            self.assertFalse(failed.verified)
            self.assertEqual(failed.payload["verification_status"], "failed")
            self.assertIn("artifact-sha256", codes)

    def test_circuit_breaker_trips_and_quarantines_failing_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="circuit-thread",
                lanes=("scout",),
                replicas=2,
            )
            for run in plan.runs:
                if run.variant_id == "openai-backup":
                    log_agent_outcome(
                        vault,
                        run_id=run.run_id,
                        status="failed",
                        metrics={"quality": 0.1},
                        usage={"latency_ms": 2500, "cost_usd": 0.2},
                        failure_code="provider_error",
                        output_text="private circuit output",
                    )
                else:
                    log_agent_outcome(
                        vault,
                        run_id=run.run_id,
                        status="succeeded",
                        metrics={"quality": 0.92},
                        usage={"latency_ms": 700, "cost_usd": 0.01},
                        output_text="private circuit output",
                    )

            circuit = evaluate_agent_circuit(
                vault,
                experiment="cross-model-agent",
                group_by="provider",
                min_outcomes=2,
                max_failure_rate=0.25,
                quarantine_on_trip=True,
                operator="operator-a",
            )
            payload = json.loads(circuit.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = circuit.report_path.read_text(encoding="utf-8")
            findings = {item["code"] for item in payload["findings"]}
            actions = payload["actions"]

            self.assertTrue(circuit.tripped)
            self.assertEqual(payload["schema"], "griosai.agent-circuit.v1")
            self.assertEqual(payload["circuit_status"], "tripped")
            self.assertEqual(payload["summary"]["tripped_groups"], 1)
            self.assertIn("failure-rate", findings)
            self.assertEqual(actions[0]["status"], "written")
            self.assertEqual(actions[0]["group"], "openai")
            self.assertIn("Agent Harness Circuit Breaker", report)
            self.assertNotIn("private circuit output", encoded)
            self.assertNotIn("circuit-thread", encoded)

            status = summarize_agent_harness(vault, experiment="cross-model-agent")
            self.assertEqual(status.payload["summary"]["circuits"], 1)
            self.assertEqual(status.payload["summary"]["active_quarantines"], 1)
            self.assertEqual(status.payload["experiments"][0]["latest_circuit_status"], "tripped")

            timeline = timeline_agent_harness(vault, experiment="cross-model-agent")
            event_types = {item["event_type"] for item in timeline.payload["events"]}
            self.assertIn("circuit-evaluated", event_types)
            self.assertIn("agent-quarantine-written", event_types)

    def test_capacity_planner_recommends_batch_from_active_and_pending_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="capacity-thread",
                lanes=("scout",),
                replicas=2,
            )
            claim = claim_agent_run(
                vault,
                plan_id=plan.plan_id,
                client_id="capacity-worker",
                ttl_seconds=600,
            )
            completed = next(run for run in plan.runs if run.run_id != claim.run_id)
            log_agent_outcome(
                vault,
                run_id=completed.run_id,
                status="succeeded",
                metrics={"quality": 0.88},
                usage={"latency_ms": 900, "cost_usd": 0.01},
                output_text="private capacity output",
            )

            capacity = plan_agent_capacity(
                vault,
                plan_id=plan.plan_id,
                max_concurrency=3,
                target_utilization=1.0,
                latency_window=5,
            )
            payload = json.loads(capacity.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = capacity.report_path.read_text(encoding="utf-8")
            experiment = payload["experiments"][0]
            recommendation = experiment["recommendation"]

            self.assertEqual(payload["schema"], "griosai.agent-capacity.v1")
            self.assertEqual(payload["capacity_status"], "dispatch")
            self.assertEqual(payload["summary"]["pending_runs"], 4)
            self.assertEqual(payload["summary"]["active_claims"], 1)
            self.assertEqual(payload["summary"]["recommended_batch_size"], 2)
            self.assertEqual(recommendation["available_slots"], 2)
            self.assertEqual(recommendation["batch_size"], 2)
            self.assertEqual(recommendation["claim_strategy"], "variant-balanced")
            self.assertEqual(experiment["recent_latency"]["mean_latency_ms"], 900)
            self.assertIn("Agent Harness Capacity", report)
            self.assertNotIn("private capacity output", encoded)
            self.assertNotIn("capacity-thread", encoded)

            status = summarize_agent_harness(vault, experiment="cross-model-agent")
            self.assertEqual(status.payload["summary"]["capacity_reports"], 1)

    def test_slo_gate_fails_on_completion_failure_and_latency_regressions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="slo-thread",
                lanes=("scout",),
                replicas=1,
            )
            log_agent_outcome(
                vault,
                run_id=plan.runs[0].run_id,
                status="succeeded",
                metrics={"quality": 0.91},
                usage={"latency_ms": 2500, "cost_usd": 0.01},
                output_text="private slo output",
            )
            log_agent_outcome(
                vault,
                run_id=plan.runs[1].run_id,
                status="failed",
                metrics={"quality": 0.1},
                usage={"latency_ms": 3500, "cost_usd": 0.02},
                failure_code="adapter_error",
                output_text="private slo output",
            )

            slo = evaluate_agent_slo(
                vault,
                plan_id=plan.plan_id,
                min_completion_rate=1.0,
                max_failure_rate=0.2,
                max_mean_latency_ms=1000,
            )
            payload = json.loads(slo.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = slo.report_path.read_text(encoding="utf-8")
            codes = {item["code"] for item in payload["findings"]}

            self.assertFalse(slo.passed)
            self.assertEqual(payload["schema"], "griosai.agent-slo.v1")
            self.assertEqual(payload["slo_status"], "fail")
            self.assertIn("completion-rate", codes)
            self.assertIn("failure-rate", codes)
            self.assertIn("mean-latency", codes)
            self.assertEqual(payload["summary"]["scheduled_runs"], 3)
            self.assertEqual(payload["summary"]["completed_runs"], 2)
            self.assertEqual(payload["experiments"][0]["metrics"]["mean_latency_ms"], 3000)
            self.assertIn("Agent Harness SLO", report)
            self.assertNotIn("private slo output", encoded)
            self.assertNotIn("slo-thread", encoded)

            status = summarize_agent_harness(vault, experiment="cross-model-agent")
            self.assertEqual(status.payload["summary"]["slo_reports"], 1)

    def test_model_mix_gate_blocks_single_provider_and_tracks_diversity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            claude_only = dict(AGENT_CONFIG)
            claude_only["variants"] = [AGENT_CONFIG["variants"][0]]
            create_agent_run(
                vault,
                claude_only,
                subject_key="mix-private-single-provider",
                prompt_text="private mix prompt",
            )

            blocked = evaluate_agent_mix(
                vault,
                experiment="cross-model-agent",
                require_local_provider=True,
            )
            blocked_payload = json.loads(blocked.path.read_text(encoding="utf-8"))
            blocked_codes = {item["code"] for item in blocked_payload["findings"]}

            self.assertFalse(blocked.passed)
            self.assertEqual(blocked_payload["schema"], "griosai.agent-mix.v1")
            self.assertEqual(blocked_payload["mix_status"], "fail")
            self.assertIn("provider-count", blocked_codes)
            self.assertIn("variant-count", blocked_codes)
            self.assertIn("local-provider-missing", blocked_codes)

        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="mix-private-balanced",
                lanes=("scout",),
                replicas=1,
            )
            for run in plan.runs:
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": 0.8},
                    usage={"latency_ms": 600, "cost_usd": 0.01},
                    output_text="private mix output",
                )

            passed = evaluate_agent_mix(
                vault,
                experiment="cross-model-agent",
                require_local_provider=True,
            )
            payload = json.loads(passed.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            status = summarize_agent_harness(vault, experiment="cross-model-agent")
            audit = audit_agent_harness(vault, experiment="cross-model-agent")
            timeline = timeline_agent_harness(vault, experiment="cross-model-agent")

            self.assertTrue(passed.passed)
            self.assertEqual(payload["mix_status"], "pass")
            self.assertEqual(payload["summary"]["provider_count"], 3)
            self.assertEqual(payload["summary"]["variant_count"], 3)
            self.assertEqual(payload["summary"]["local_provider_count"], 1)
            self.assertAlmostEqual(payload["summary"]["max_scheduled_provider_share"], 1 / 3, places=5)
            self.assertIn("Agent Harness Model Mix", passed.report_path.read_text(encoding="utf-8"))
            self.assertNotIn("private mix output", encoded)
            self.assertNotIn("mix-private-balanced", encoded)
            self.assertEqual(status.payload["summary"]["mix_reports"], 1)
            self.assertEqual(status.payload["experiments"][0]["latest_mix_status"], "pass")
            self.assertEqual(audit.payload["experiments"][0]["counts"]["mix"], 1)
            self.assertIn(
                "mix-evaluated",
                {event["event_type"] for event in timeline.payload["events"]},
            )

    def test_snapshot_diffs_experiment_state_without_raw_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            first_plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="snapshot-private-thread",
                lanes=("scout",),
                replicas=1,
            )
            first = write_agent_snapshot(vault, experiment="cross-model-agent")
            first_payload = json.loads(first.path.read_text(encoding="utf-8"))
            first_encoded = json.dumps(first_payload, sort_keys=True)

            self.assertEqual(first_payload["schema"], "griosai.agent-snapshot.v1")
            self.assertEqual(first_payload["snapshot_status"], "baseline")
            self.assertFalse(first.changed)
            self.assertEqual(first_payload["summary"]["changed_sections"], 0)
            self.assertEqual(first_payload["summary"]["artifact_records"], 4)
            self.assertTrue(first.report_path.exists())
            self.assertNotIn("snapshot-private-thread", first_encoded)
            self.assertNotIn("map options", first_encoded)
            self.assertNotIn("metadata only logs", first_encoded)

            log_agent_outcome(
                vault,
                run_id=first_plan.runs[0].run_id,
                status="succeeded",
                metrics={"quality": 0.93},
                usage={"latency_ms": 800, "cost_usd": 0.01},
                output_text="private snapshot output",
            )
            second = write_agent_snapshot(
                vault,
                experiment="cross-model-agent",
                baseline_snapshot_id=first.snapshot_id,
            )
            payload = json.loads(second.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            changed_sections = {item["section"] for item in payload["changes"]}
            status = summarize_agent_harness(vault, experiment="cross-model-agent")
            audit = audit_agent_harness(vault, experiment="cross-model-agent")
            timeline = timeline_agent_harness(vault, experiment="cross-model-agent")

            self.assertTrue(second.changed)
            self.assertEqual(payload["snapshot_status"], "changed")
            self.assertEqual(payload["baseline_snapshot_id"], first.snapshot_id)
            self.assertIn("artifact_counts", changed_sections)
            self.assertIn("artifacts.outcomes", changed_sections)
            self.assertIn("outcomes", changed_sections)
            self.assertNotIn("private snapshot output", encoded)
            self.assertNotIn("snapshot-private-thread", encoded)
            self.assertEqual(status.payload["summary"]["snapshots"], 2)
            self.assertEqual(status.payload["experiments"][0]["latest_snapshot_status"], "changed")
            self.assertEqual(audit.payload["experiments"][0]["counts"]["snapshots"], 2)
            self.assertIn(
                "snapshot-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )

    def test_preflight_blocks_single_model_wave_and_passes_balanced_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            claude_only = dict(AGENT_CONFIG)
            claude_only["variants"] = [AGENT_CONFIG["variants"][0]]
            single = create_agent_plan(
                vault,
                claude_only,
                subject_key="preflight-single-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )

            blocked = preflight_agent_harness(
                vault,
                plan_id=single.plan_id,
                require_cross_model=True,
                require_lane_coverage=True,
                min_pending_runs=2,
            )
            blocked_payload = json.loads(blocked.path.read_text(encoding="utf-8"))
            blocked_codes = {item["code"] for item in blocked_payload["findings"]}

            self.assertFalse(blocked.ready)
            self.assertEqual(blocked_payload["schema"], "griosai.agent-preflight.v1")
            self.assertEqual(blocked_payload["preflight_status"], "blocked")
            self.assertIn("cross-model-coverage", blocked_codes)
            self.assertEqual(blocked_payload["summary"]["pending_runs"], 2)

            matrix = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="preflight-matrix-thread",
                lanes=("scout", "reviewer"),
            )
            ready = preflight_agent_harness(
                vault,
                plan_id=matrix.plan_id,
                require_cross_model=True,
                require_lane_coverage=True,
                require_variant_coverage=True,
                max_pending_skew=0,
            )
            payload = json.loads(ready.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = ready.report_path.read_text(encoding="utf-8")

            self.assertTrue(ready.ready)
            self.assertEqual(payload["preflight_status"], "ready")
            self.assertTrue(payload["coverage"]["cross_model"])
            self.assertEqual(payload["coverage"]["pending_sample_skew"], 0)
            self.assertEqual(set(payload["coverage"]["pending_variants"]), {"claude-primary", "ollama-local", "openai-backup"})
            self.assertIn("Agent Harness Preflight", report)
            self.assertNotIn("preflight-single-thread", encoded)

    def test_timeline_reports_chronological_metadata_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="timeline-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            claim = claim_agent_run(
                vault,
                plan_id=plan.plan_id,
                client_id="timeline-worker",
                ttl_seconds=120,
            )
            write_agent_work_packet(vault, claim_id=claim.claim_id)
            for run in plan.runs:
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": 0.9},
                    output_text="private timeline output",
                )
            merge_agent_plan(vault, plan_id=plan.plan_id)
            gate_agent_plan(vault, plan_id=plan.plan_id, metric_threshold=0.8)
            adjudicate_agent_plan(vault, plan_id=plan.plan_id, min_consensus_ratio=0)
            audit_agent_harness(vault)

            timeline = timeline_agent_harness(vault, limit=50)
            payload = json.loads(timeline.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = timeline.report_path.read_text(encoding="utf-8")
            event_types = {item["event_type"] for item in payload["events"]}
            timestamps = [item["timestamp"] for item in payload["events"]]

            self.assertEqual(payload["schema"], "griosai.agent-timeline.v1")
            self.assertGreaterEqual(payload["summary"]["events"], 9)
            self.assertEqual(timestamps, sorted(timestamps))
            self.assertIn("run-created", event_types)
            self.assertIn("plan-created", event_types)
            self.assertIn("run-claimed", event_types)
            self.assertIn("work-packet-written", event_types)
            self.assertIn("outcome-logged", event_types)
            self.assertIn("plan-merged", event_types)
            self.assertIn("gate-evaluated", event_types)
            self.assertIn("plan-adjudicated", event_types)
            self.assertIn("audit-written", event_types)
            self.assertIn("Agent Harness Timeline", report)
            self.assertNotIn("private timeline output", encoded)

    def test_audit_fails_broken_outcome_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            create_agent_run(vault, AGENT_CONFIG, subject_key="audit-fail-thread")
            outcome_dir = vault / "agent-runs" / "cross-model-agent" / "outcomes"
            outcome_dir.mkdir(parents=True, exist_ok=True)
            (outcome_dir / "outcome-broken.json").write_text(
                json.dumps(
                    {
                        "schema": "griosai.agent-outcome.v1",
                        "outcome_id": "outcome-broken",
                        "run_id": "run-missing",
                        "logged_at": "2026-05-30T00:00:00Z",
                        "experiment": {"name": "Cross Model Agent", "slug": "cross-model-agent"},
                        "variant": {"id": "claude-primary"},
                        "status": "succeeded",
                        "metrics": {"quality": 1.0},
                        "privacy": {"mode": "metadata-only"},
                    }
                ),
                encoding="utf-8",
            )

            audit = audit_agent_harness(vault)
            codes = {item["code"] for item in audit.payload["findings"]}

            self.assertTrue(audit.failed)
            self.assertIn("outcome-run-missing", codes)

    def test_status_scoreboard_reports_pending_and_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="status-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            log_agent_outcome(
                vault,
                run_id=plan.runs[0].run_id,
                status="failed",
                metrics={"quality": 0.1},
                failure_code="adapter_timeout",
                output_text="private failure output",
            )

            status = summarize_agent_harness(vault)
            payload = json.loads(status.path.read_text(encoding="utf-8"))
            report = status.report_path.read_text(encoding="utf-8")
            encoded = json.dumps(payload, sort_keys=True)

            self.assertEqual(payload["schema"], "griosai.agent-status.v1")
            self.assertEqual(payload["summary"]["experiments"], 1)
            self.assertEqual(payload["summary"]["pending_plan_runs"], 1)
            self.assertEqual(payload["summary"]["failed_outcomes"], 1)
            self.assertTrue(payload["recommendations"])
            self.assertIn("Agent Harness Status", report)
            self.assertNotIn("private failure output", encoded)

    def test_agent_dashboard_is_self_contained_and_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="dashboard-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            log_agent_outcome(
                vault,
                run_id=plan.runs[0].run_id,
                status="succeeded",
                metrics={"quality": 0.91},
                usage={"total_tokens": 120, "latency_ms": 800, "cost_usd": 0.02},
                output_text="private dashboard output <script>alert(1)</script>",
            )
            budget_agent_harness(vault, experiment="cross-model-agent", max_cost_usd=1)

            dashboard = write_agent_dashboard(
                vault,
                experiment="cross-model-agent",
                limit=20,
            )
            payload = json.loads(dashboard.report_path.read_text(encoding="utf-8"))
            html = dashboard.path.read_text(encoding="utf-8")
            timeline = timeline_agent_harness(vault, experiment="cross-model-agent")

            self.assertEqual(payload["schema"], "griosai.agent-dashboard.v1")
            self.assertEqual(payload["summary"]["experiments"], 1)
            self.assertEqual(payload["summary"]["runs"], 2)
            self.assertEqual(payload["summary"]["outcomes"], 1)
            self.assertEqual(payload["summary"]["budget_reports"], 1)
            self.assertTrue(dashboard.path.name.startswith("agent-dashboard-"))
            self.assertIn("Content-Security-Policy", html)
            self.assertIn("Agent Harness Dashboard", html)
            self.assertIn("cross-model-agent", html)
            self.assertNotIn("private dashboard output", html)
            self.assertNotIn("<script>alert(1)</script>", html)
            self.assertNotIn("private dashboard output", json.dumps(payload, sort_keys=True))
            self.assertIn(
                "dashboard-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )

    def test_claim_leases_next_uncompleted_plan_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="claim-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )

            first = claim_agent_run(
                vault,
                plan_id=plan.plan_id,
                client_id="worker-one",
                ttl_seconds=120,
            )
            second = claim_agent_run(
                vault,
                plan_id=plan.plan_id,
                client_id="worker-two",
                ttl_seconds=120,
            )
            status = summarize_agent_harness(vault)
            payload = json.loads(status.path.read_text(encoding="utf-8"))

            self.assertEqual(first.payload["schema"], "griosai.agent-claim.v1")
            self.assertNotEqual(first.run_id, second.run_id)
            self.assertEqual(payload["summary"]["claimed_plan_runs"], 2)
            self.assertEqual(payload["summary"]["pending_plan_runs"], 0)
            self.assertEqual(payload["summary"]["claims"], 2)
            with self.assertRaises(FileNotFoundError):
                claim_agent_run(vault, plan_id=plan.plan_id, client_id="worker-three")

    def test_dispatch_claims_batch_and_writes_work_packets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            secret = "sk-" + ("F" * 24)
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="dispatch-thread",
                prompt_text=f"Private dispatch prompt {secret}",
                lanes=("scout", "reviewer"),
                replicas=2,
            )

            dispatch = dispatch_agent_plan(
                vault,
                plan_id=plan.plan_id,
                client_prefix="dispatch-worker",
                count=3,
                ttl_seconds=120,
            )
            payload = json.loads(dispatch.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = dispatch.report_path.read_text(encoding="utf-8")
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)

            self.assertEqual(payload["schema"], "griosai.agent-dispatch.v1")
            self.assertEqual(payload["dispatch_status"], "complete")
            self.assertEqual(payload["claimed_count"], 3)
            self.assertEqual(payload["work_packet_count"], 3)
            self.assertEqual(len({item["run_id"] for item in payload["entries"]}), 3)
            self.assertEqual(status.payload["summary"]["dispatches"], 1)
            self.assertEqual(status.payload["summary"]["claimed_plan_runs"], 3)
            self.assertEqual(status.payload["summary"]["pending_plan_runs"], 1)
            self.assertIn("Agent Harness Dispatch", report)
            self.assertIn(
                "plan-dispatched",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertNotIn("Private dispatch prompt", encoded)
            self.assertNotIn(secret, encoded)
            for entry in payload["entries"]:
                self.assertTrue((vault / entry["work_packet_path"]).exists())

    def test_balanced_claim_strategy_spreads_batch_across_lanes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="balanced-claim-thread",
                lanes=("scout", "reviewer"),
                replicas=2,
            )

            dispatch = dispatch_agent_plan(
                vault,
                plan_id=plan.plan_id,
                client_prefix="balanced-worker",
                count=4,
                ttl_seconds=120,
                claim_strategy="lane-balanced",
            )
            payload = json.loads(dispatch.path.read_text(encoding="utf-8"))
            lane_counts: dict[str, int] = {}
            for entry in payload["entries"]:
                lane_id = str(entry["lane_id"])
                lane_counts[lane_id] = lane_counts.get(lane_id, 0) + 1

            self.assertEqual(payload["claim_strategy"], "lane-balanced")
            self.assertEqual(lane_counts, {"scout": 2, "reviewer": 2})
            self.assertTrue(
                all(claim.payload["scheduler"]["strategy"] == "lane-balanced" for claim in dispatch.claims)
            )

    def test_operator_hold_blocks_dispatch_until_released(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="hold-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )

            hold = hold_agent_experiment(
                vault,
                experiment="cross-model-agent",
                reason="pause worker wave",
                scopes=("dispatch",),
                operator="operator-a",
            )
            preflight = preflight_agent_harness(vault, plan_id=plan.plan_id)
            orchestration = orchestrate_agent_dispatch(
                vault,
                plan_id=plan.plan_id,
                client_prefix="held-worker",
                max_concurrency=2,
                batch_size=2,
            )
            timeline = timeline_agent_harness(vault, experiment="cross-model-agent")
            status = summarize_agent_harness(vault, experiment="cross-model-agent")
            preflight_codes = {item["code"] for item in preflight.payload["findings"]}

            self.assertEqual(hold.payload["schema"], "griosai.agent-hold.v1")
            self.assertEqual(hold.payload["hold_status"], "active")
            self.assertEqual(hold.payload["scopes"], ["dispatch"])
            self.assertEqual(status.payload["summary"]["active_holds"], 1)
            self.assertFalse(preflight.ready)
            self.assertIn("active-hold", preflight_codes)
            self.assertEqual(orchestration.payload["orchestration_status"], "blocked-by-hold")
            self.assertEqual(orchestration.payload["summary"]["claimed_count"], 0)
            self.assertEqual(orchestration.payload["summary"]["active_holds"], 1)
            with self.assertRaises(ValueError):
                dispatch_agent_plan(
                    vault,
                    plan_id=plan.plan_id,
                    client_prefix="held-dispatch",
                    count=1,
                )
            self.assertIn(
                "agent-hold-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )

            release = release_agent_hold(
                vault,
                experiment="cross-model-agent",
                hold_id=hold.hold_id,
                reason="resume worker wave",
            )
            dispatch = dispatch_agent_plan(
                vault,
                plan_id=plan.plan_id,
                client_prefix="released-worker",
                count=1,
            )

            self.assertEqual(release.payload["hold_status"], "released")
            self.assertFalse(release.active)
            self.assertEqual(dispatch.payload["claimed_count"], 1)

    def test_operator_hold_scopes_block_control_plane_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            create_agent_run(vault, AGENT_CONFIG, subject_key="hold-gates")

            promotion_hold = hold_agent_experiment(
                vault,
                experiment="cross-model-agent",
                reason="pause promotion",
                scopes=("promotion",),
            )
            with self.assertRaisesRegex(ValueError, "active agent hold blocks promotion"):
                promote_agent_experiment(
                    vault,
                    experiment="cross-model-agent",
                    min_trials_per_variant=1,
                )
            release_agent_hold(
                vault,
                experiment="cross-model-agent",
                hold_id=promotion_hold.hold_id,
                reason="resume promotion",
            )

            rollout = plan_agent_rollout(
                vault,
                experiment="cross-model-agent",
                candidate_variant_id="openai-backup",
                stages=(0.2, 1.0),
            )
            rollout_hold = hold_agent_experiment(
                vault,
                experiment="cross-model-agent",
                reason="pause rollout",
                scopes=("rollout",),
            )
            with self.assertRaisesRegex(ValueError, "active agent hold blocks rollout"):
                plan_agent_rollout(
                    vault,
                    experiment="cross-model-agent",
                    candidate_variant_id="openai-backup",
                )
            with self.assertRaisesRegex(ValueError, "active agent hold blocks rollout"):
                check_agent_rollout_stage(vault, rollout_id=rollout.rollout_id)
            release_agent_hold(
                vault,
                experiment="cross-model-agent",
                hold_id=rollout_hold.hold_id,
                reason="resume rollout",
            )

            evolve_hold = hold_agent_experiment(
                vault,
                experiment="cross-model-agent",
                reason="pause evolution",
                scopes=("evolve",),
            )
            with self.assertRaisesRegex(ValueError, "active agent hold blocks evolve"):
                evolve_agent_experiment(
                    vault,
                    experiment="cross-model-agent",
                    min_trials_per_variant=1,
                    min_samples_per_variant=1,
                )
            release_agent_hold(
                vault,
                experiment="cross-model-agent",
                hold_id=evolve_hold.hold_id,
                reason="resume evolution",
            )

            all_hold = hold_agent_experiment(
                vault,
                experiment="cross-model-agent",
                reason="global pause",
                scopes=("all",),
            )
            with self.assertRaisesRegex(ValueError, "active agent hold blocks promotion"):
                promote_agent_experiment(
                    vault,
                    experiment="cross-model-agent",
                    min_trials_per_variant=1,
                )
            release = release_agent_hold(
                vault,
                experiment="cross-model-agent",
                hold_id=all_hold.hold_id,
                reason="resume all",
            )

            self.assertFalse(release.active)

    def test_quarantine_filters_provider_from_claims_until_released(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="quarantine-thread",
                lanes=("scout",),
                replicas=1,
            )
            openai_run_ids = {run.run_id for run in plan.runs if run.variant_id == "openai-backup"}

            quarantine = quarantine_agent_slice(
                vault,
                experiment="cross-model-agent",
                reason="provider incident",
                providers=("openai",),
                operator="operator-a",
            )
            preflight = preflight_agent_harness(
                vault,
                plan_id=plan.plan_id,
                require_cross_model=True,
            )
            dispatch = dispatch_agent_plan(
                vault,
                plan_id=plan.plan_id,
                client_prefix="quarantine-worker",
                count=3,
                claim_strategy="variant-balanced",
            )
            status = summarize_agent_harness(vault, experiment="cross-model-agent")
            timeline = timeline_agent_harness(vault, experiment="cross-model-agent")
            codes = {item["code"] for item in preflight.payload["findings"]}

            self.assertEqual(quarantine.payload["schema"], "griosai.agent-quarantine.v1")
            self.assertEqual(quarantine.payload["quarantine_status"], "active")
            self.assertEqual(quarantine.payload["target"]["providers"], ["openai"])
            self.assertEqual(status.payload["summary"]["active_quarantines"], 1)
            self.assertIn("active-quarantine", codes)
            self.assertEqual(preflight.payload["summary"]["active_quarantines"], 1)
            self.assertEqual(preflight.payload["summary"]["quarantined_pending_runs"], 1)
            self.assertEqual(dispatch.payload["claimed_count"], 2)
            self.assertNotIn(
                "openai-backup",
                {entry.get("variant_id") for entry in dispatch.payload["entries"]},
            )
            self.assertTrue(
                all(claim.run_id not in openai_run_ids for claim in dispatch.claims)
            )
            self.assertIn(
                "agent-quarantine-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )

            release = release_agent_quarantine(
                vault,
                experiment="cross-model-agent",
                quarantine_id=quarantine.quarantine_id,
                reason="provider recovered",
            )
            claim = claim_agent_run(
                vault,
                plan_id=plan.plan_id,
                client_id="released-quarantine-worker",
            )

            self.assertEqual(release.payload["quarantine_status"], "released")
            self.assertFalse(release.active)
            self.assertIn(claim.run_id, openai_run_ids)

    def test_orchestrate_schedules_suite_under_concurrency_cap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            secret = "sk-" + ("G" * 24)
            suite = create_agent_suite_plan(
                vault,
                AGENT_CONFIG,
                {
                    "suite": "Orchestration Suite",
                    "cases": [
                        {"id": "orch-one", "prompt": f"Private orchestration prompt {secret}"},
                        {"id": "orch-two", "prompt": "Second private orchestration task"},
                    ],
                },
                subject_prefix="orchestration-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )

            orchestration = orchestrate_agent_dispatch(
                vault,
                suite_id=suite.suite_id,
                client_prefix="orch-worker",
                max_concurrency=3,
                batch_size=2,
                ttl_seconds=120,
                claim_strategy="lane-variant-balanced",
            )
            payload = json.loads(orchestration.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = orchestration.report_path.read_text(encoding="utf-8")
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)

            self.assertEqual(payload["schema"], "griosai.agent-orchestration.v1")
            self.assertEqual(payload["orchestration_status"], "dispatched-at-capacity")
            self.assertEqual(payload["summary"]["plan_count"], 2)
            self.assertEqual(payload["summary"]["claimed_count"], 3)
            self.assertEqual(payload["policy"]["claim_strategy"], "lane-variant-balanced")
            self.assertEqual(payload["summary"]["active_claims"], 3)
            self.assertEqual(payload["summary"]["pending_runs"], 9)
            self.assertEqual(len(payload["dispatches"]), 2)
            self.assertEqual(len(orchestration.dispatches), 2)
            self.assertEqual(status.payload["summary"]["orchestration_reports"], 1)
            self.assertEqual(status.payload["summary"]["claimed_plan_runs"], 3)
            self.assertIn("Agent Harness Orchestration", report)
            self.assertIn(
                "orchestration-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertNotIn("Private orchestration prompt", encoded)
            self.assertNotIn(secret, encoded)

            capped = orchestrate_agent_dispatch(
                vault,
                suite_id=suite.suite_id,
                client_prefix="orch-worker",
                max_concurrency=3,
                batch_size=2,
                ttl_seconds=120,
                claim_strategy="lane-variant-balanced",
            )
            self.assertEqual(capped.payload["orchestration_status"], "at-capacity")
            self.assertEqual(capped.payload["summary"]["claimed_count"], 0)

    def test_heartbeat_extends_claim_and_prevents_duplicate_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="heartbeat-thread",
                lanes=("scout",),
                replicas=1,
            )
            claim = claim_agent_run(
                vault,
                plan_id=plan.plan_id,
                client_id="worker-one",
                ttl_seconds=1,
            )
            heartbeat = heartbeat_agent_claim(
                vault,
                claim_id=claim.claim_id,
                client_id="worker-one",
                ttl_seconds=120,
            )
            claim_payload = json.loads(claim.path.read_text(encoding="utf-8"))
            claim_payload["claim"]["expires_at"] = "2000-01-01T00:00:00+00:00"
            claim.path.write_text(json.dumps(claim_payload), encoding="utf-8")

            status = summarize_agent_harness(vault)
            payload = json.loads(status.path.read_text(encoding="utf-8"))

            self.assertEqual(heartbeat.payload["schema"], "griosai.agent-heartbeat.v1")
            self.assertEqual(heartbeat.run_id, claim.run_id)
            self.assertEqual(payload["summary"]["heartbeats"], 1)
            self.assertEqual(payload["summary"]["claimed_plan_runs"], 1)
            self.assertEqual(payload["summary"]["expired_claims"], 0)
            with self.assertRaises(FileNotFoundError):
                claim_agent_run(vault, plan_id=plan.plan_id, client_id="worker-two")

    def test_parallel_claims_do_not_duplicate_pending_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="parallel-claim-race",
                lanes=("scout",),
                replicas=2,
            )
            original_write = agent_harness_module.write_unique_text
            results: list[tuple[str, str]] = []
            errors: list[BaseException] = []

            def delayed_write(path: Path, content: str, *, encoding: str = "utf-8") -> Path:
                if "/claims/" in str(path):
                    time.sleep(0.05)
                return original_write(path, content, encoding=encoding)

            def worker(client_id: str) -> None:
                try:
                    claim = claim_agent_run(
                        vault,
                        plan_id=plan.plan_id,
                        client_id=client_id,
                        ttl_seconds=120,
                    )
                    results.append((client_id, claim.run_id))
                except BaseException as exc:
                    errors.append(exc)

            with patch("griosai.agent_harness.write_unique_text", delayed_write):
                threads = [
                    threading.Thread(target=worker, args=("worker-one",)),
                    threading.Thread(target=worker, args=("worker-two",)),
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=5)

            self.assertEqual(errors, [])
            self.assertEqual(len(results), 2)
            self.assertEqual(len({run_id for _client_id, run_id in results}), 2)

    def test_work_packet_sanitizes_claimed_run_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            secret = "sk-" + ("E" * 24)
            prompt = f"Private work prompt {secret}"
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="work-packet-thread",
                prompt_text=prompt,
                prompt_source_name="/Users/gustavorios/private/work.md",
                lanes=("scout",),
                replicas=1,
            )
            claim = claim_agent_run(
                vault,
                plan_id=plan.plan_id,
                client_id="worker-one",
                ttl_seconds=120,
            )

            packet = write_agent_work_packet(vault, claim_id=claim.claim_id)
            payload = json.loads(packet.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = packet.report_path.read_text(encoding="utf-8")

            self.assertEqual(payload["schema"], "griosai.agent-work-packet.v1")
            self.assertEqual(payload["run_id"], claim.run_id)
            self.assertEqual(payload["claim"]["claim_id"], claim.claim_id)
            self.assertEqual(payload["parallel"]["lane_id"], "scout")
            self.assertEqual(payload["rubric"]["aggregate_metric"], "quality")
            self.assertTrue(payload["next_commands"])
            self.assertIn("Agent Harness Work Packet", report)
            self.assertNotIn(prompt, encoded)
            self.assertNotIn(secret, encoded)
            self.assertNotIn("/Users/gustavorios", encoded)

    def test_watchdog_reports_stale_claim_without_raw_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="watchdog-thread",
                lanes=("scout",),
                replicas=1,
            )
            claim = claim_agent_run(
                vault,
                plan_id=plan.plan_id,
                client_id="worker-one",
                ttl_seconds=3600,
            )
            claim_payload = json.loads(claim.path.read_text(encoding="utf-8"))
            claim_payload["claim"]["claimed_at"] = "2000-01-01T00:00:00+00:00"
            claim.path.write_text(json.dumps(claim_payload), encoding="utf-8")

            watchdog = watchdog_agent_harness(vault, stale_after_seconds=1)
            payload = json.loads(watchdog.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            codes = {item["code"] for item in payload["findings"]}
            report = watchdog.report_path.read_text(encoding="utf-8")

            self.assertTrue(watchdog.needs_attention)
            self.assertEqual(payload["schema"], "griosai.agent-watchdog.v1")
            self.assertEqual(payload["summary"]["stale_claims"], 1)
            self.assertIn("claim-stale", codes)
            self.assertIn("Agent Harness Watchdog", report)
            self.assertNotIn("Private", encoded)

    def test_expired_claim_can_be_reclaimed_and_status_reports_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="expired-claim-thread",
                lanes=("scout",),
                replicas=1,
            )
            first = claim_agent_run(
                vault,
                plan_id=plan.plan_id,
                client_id="worker-one",
                ttl_seconds=1,
            )
            claim_payload = json.loads(first.path.read_text(encoding="utf-8"))
            claim_payload["claim"]["expires_at"] = "2000-01-01T00:00:00+00:00"
            first.path.write_text(json.dumps(claim_payload), encoding="utf-8")

            reclaimed = claim_agent_run(
                vault,
                plan_id=plan.plan_id,
                client_id="worker-two",
                ttl_seconds=120,
            )
            status = summarize_agent_harness(vault)
            payload = json.loads(status.path.read_text(encoding="utf-8"))

            self.assertEqual(reclaimed.run_id, first.run_id)
            self.assertEqual(payload["summary"]["expired_claims"], 1)
            self.assertEqual(payload["summary"]["claimed_plan_runs"], 1)

    def test_gate_passes_complete_high_metric_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="gate-pass-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            for index, run in enumerate(plan.runs):
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": 0.91 + index * 0.01},
                    output_text=f"private output {index}",
                )

            gate = gate_agent_plan(
                vault,
                plan_id=plan.plan_id,
                metric_threshold=0.9,
                required_lanes=("scout", "reviewer"),
            )
            payload = json.loads(gate.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = gate.report_path.read_text(encoding="utf-8")

            self.assertTrue(gate.passed)
            self.assertEqual(payload["schema"], "griosai.agent-gate.v1")
            self.assertEqual(payload["gate_status"], "pass")
            self.assertEqual(payload["summary"]["completed_runs"], 2)
            self.assertIn("gate-passed", encoded)
            self.assertNotIn("private output", encoded)
            self.assertIn("Agent Harness Gate", report)

    def test_gate_fails_incomplete_or_low_metric_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="gate-fail-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            log_agent_outcome(
                vault,
                run_id=plan.runs[0].run_id,
                status="succeeded",
                metrics={"quality": 0.4},
            )

            gate = gate_agent_plan(
                vault,
                plan_id=plan.plan_id,
                min_completed_ratio=1.0,
                metric_threshold=0.9,
                required_lanes=("scout", "reviewer"),
            )
            codes = {item["code"] for item in gate.payload["findings"]}

            self.assertFalse(gate.passed)
            self.assertIn("completion-ratio", codes)
            self.assertIn("metric-threshold", codes)

    def test_promotion_can_require_suite_report_and_pareto_frontier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            suite = {
                "suite": "Promotion Suite",
                "cases": [
                    {"id": "promo-one", "prompt": "private promotion one"},
                    {"id": "promo-two", "prompt": "private promotion two"},
                ],
            }
            plan = create_agent_suite_plan(
                vault,
                AGENT_CONFIG,
                suite,
                subject_prefix="promotion-suite-thread",
                lanes=("scout",),
                mode="matrix",
            )
            scores = {
                "promo-one": {"claude-primary": 0.6, "openai-backup": 0.9, "ollama-local": 0.7},
                "promo-two": {"claude-primary": 0.61, "openai-backup": 0.91, "ollama-local": 0.71},
            }
            for case_plan in plan.plans:
                context = case_plan.payload["suite"]
                self.assertIsInstance(context, dict)
                case_id = str(context["case_id"])
                for run in case_plan.runs:
                    log_agent_outcome(
                        vault,
                        run_id=run.run_id,
                        status="succeeded",
                        metrics={"quality": scores[case_id][run.variant_id]},
                        usage={"total_tokens": 100, "latency_ms": 800, "cost_usd": 0.01},
                        output_text=f"private promotion output {case_id}",
                    )
            report = report_agent_suite(
                vault,
                suite_id=plan.suite_id,
                baseline_variant_id="claude-primary",
            )

            promotion = promote_agent_experiment(
                vault,
                experiment="cross-model-agent",
                champion_variant_id="claude-primary",
                min_trials_per_variant=1,
                min_delta=0.1,
                require_suite_report=True,
                require_pareto=True,
            )
            encoded = json.dumps(promotion.payload, sort_keys=True)

            self.assertTrue(promotion.ready)
            self.assertEqual(promotion.payload["promotion_status"], "ready")
            self.assertEqual(promotion.payload["candidate_variant_id"], "openai-backup")
            self.assertEqual(
                promotion.payload["evidence"]["latest_suite_report"]["report_id"],
                report.report_id,
            )
            self.assertIn("openai-backup", promotion.payload["evidence"]["pareto_variants"])
            self.assertTrue(promotion.payload["policy"]["require_suite_report"])
            self.assertTrue(promotion.payload["policy"]["require_pareto"])
            self.assertNotIn("private promotion", encoded)

    def test_retry_replaces_failed_plan_run_for_merge_and_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="retry-thread",
                lanes=("scout",),
                replicas=1,
            )
            log_agent_outcome(
                vault,
                run_id=plan.runs[0].run_id,
                status="failed",
                metrics={"quality": 0.1},
                failure_code="adapter_timeout",
                output_text="private retry failure",
            )

            retry = retry_agent_run(
                vault,
                run_id=plan.runs[0].run_id,
                reason="adapter_timeout",
            )
            log_agent_outcome(
                vault,
                run_id=retry.replacement_run_id,
                status="succeeded",
                metrics={"quality": 0.92},
                output_text="private retry success",
            )
            merge = merge_agent_plan(vault, plan_id=plan.plan_id)
            gate = gate_agent_plan(vault, plan_id=plan.plan_id, metric_threshold=0.9)
            audit = audit_agent_harness(vault)
            payload = json.loads(retry.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)

            self.assertEqual(payload["schema"], "griosai.agent-retry.v1")
            self.assertEqual(payload["original_run_id"], plan.runs[0].run_id)
            self.assertEqual(payload["replacement_run"]["run_id"], retry.replacement_run_id)
            self.assertEqual(merge.payload["merge_status"], "complete")
            self.assertEqual(merge.payload["recommended_run_id"], retry.replacement_run_id)
            self.assertTrue(gate.passed)
            self.assertEqual(gate.payload["summary"]["failed_runs"], 0)
            self.assertFalse(audit.failed)
            self.assertNotIn("private retry", encoded)

    def test_recover_batches_failed_and_expired_plan_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="recover-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            log_agent_outcome(
                vault,
                run_id=plan.runs[0].run_id,
                status="failed",
                metrics={"quality": 0.1},
                failure_code="adapter_timeout",
                output_text="private recovery failure",
            )
            claim = claim_agent_run(
                vault,
                plan_id=plan.plan_id,
                client_id="recover-worker",
                ttl_seconds=1,
            )
            claim_payload = json.loads(claim.path.read_text(encoding="utf-8"))
            claim_payload["claim"]["expires_at"] = "2000-01-01T00:00:00+00:00"
            claim.path.write_text(json.dumps(claim_payload), encoding="utf-8")

            recovery = recover_agent_harness(
                vault,
                experiment="cross-model-agent",
                max_retries=4,
                stale_after_seconds=1,
            )
            payload = json.loads(recovery.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = recovery.report_path.read_text(encoding="utf-8")
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)

            self.assertTrue(recovery.recovered)
            self.assertEqual(payload["schema"], "griosai.agent-recovery.v1")
            self.assertEqual(payload["recovery_status"], "recovered")
            self.assertEqual(payload["summary"]["candidate_count"], 2)
            self.assertEqual(payload["summary"]["retry_count"], 2)
            self.assertEqual(len(recovery.retries), 2)
            self.assertEqual(status.payload["summary"]["recovery_reports"], 1)
            self.assertIn("Agent Harness Recovery", report)
            self.assertIn(
                "recovery-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertNotIn("private recovery", encoded)

    def test_cycle_recovers_dispatches_and_writes_operator_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="cycle-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            log_agent_outcome(
                vault,
                run_id=plan.runs[0].run_id,
                status="failed",
                metrics={"quality": 0.1},
                failure_code="adapter_timeout",
                output_text="private cycle failure",
            )

            cycle = cycle_agent_harness(
                vault,
                experiment="cross-model-agent",
                plan_id=plan.plan_id,
                client_prefix="cycle-worker",
                max_concurrency=2,
                batch_size=2,
                stale_after_seconds=1,
                max_retries=2,
                dashboard_limit=30,
            )
            payload = json.loads(cycle.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)

            self.assertEqual(payload["schema"], "griosai.agent-cycle.v1")
            self.assertEqual(payload["cycle_status"], "acted")
            self.assertEqual(payload["summary"]["recovered_runs"], 1)
            self.assertEqual(payload["summary"]["dispatched_runs"], 2)
            self.assertIn("recovery", payload["artifacts"])
            self.assertIn("orchestration", payload["artifacts"])
            self.assertIn("dashboard", payload["artifacts"])
            self.assertEqual(status.payload["summary"]["cycle_reports"], 1)
            self.assertIn(
                "cycle-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertNotIn("private cycle", encoded)

    def test_loop_runs_bounded_cycles_until_idle_without_raw_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_plan(
                vault,
                AGENT_CONFIG,
                subject_key="loop-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )

            loop = loop_agent_harness(
                vault,
                experiment="cross-model-agent",
                plan_id=plan.plan_id,
                client_prefix="loop-worker",
                max_concurrency=2,
                batch_size=2,
                max_cycles=3,
                stop_after_idle_cycles=1,
                skip_recovery=True,
                dashboard_limit=30,
            )
            payload = json.loads(loop.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)

            self.assertEqual(payload["schema"], "griosai.agent-loop.v1")
            self.assertEqual(payload["loop_status"], "acted")
            self.assertEqual(payload["summary"]["requested_cycles"], 3)
            self.assertEqual(payload["summary"]["executed_cycles"], 2)
            self.assertEqual(payload["summary"]["acted_cycles"], 1)
            self.assertEqual(payload["summary"]["stop_reason"], "idle-threshold")
            self.assertEqual(payload["summary"]["dispatched_runs"], 2)
            self.assertEqual(len(payload["cycles"]), 2)
            self.assertEqual(status.payload["summary"]["loop_reports"], 1)
            self.assertEqual(status.payload["summary"]["cycle_reports"], 2)
            self.assertIn(
                "loop-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertNotIn("Private", encoded)

    def test_suite_plan_creates_case_matrix_without_raw_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            private_prompt = "Private case body with sk-" + ("D" * 24)
            suite = {
                "suite": "Regression Suite",
                "cases": [
                    {
                        "id": "case-one",
                        "prompt": private_prompt,
                        "tags": ["coding", "privacy"],
                    },
                    {
                        "id": "case-two",
                        "prompt": "Second private task",
                        "tags": ["review"],
                    },
                ],
            }

            result = create_agent_suite_plan(
                vault,
                AGENT_CONFIG,
                suite,
                subject_prefix="suite-thread",
                lanes=("scout", "reviewer"),
                mode="matrix",
            )
            payload = json.loads(result.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            first_plan = json.loads(result.plans[0].path.read_text(encoding="utf-8"))
            first_run = json.loads(result.plans[0].runs[0].path.read_text(encoding="utf-8"))
            audit = audit_agent_harness(vault)
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)

            self.assertEqual(payload["schema"], "griosai.agent-suite.v1")
            self.assertEqual(payload["case_count"], 2)
            self.assertEqual(payload["plan_count"], 2)
            self.assertEqual(payload["run_count"], 12)
            self.assertEqual(first_plan["suite"]["suite_id"], result.suite_id)
            self.assertEqual(first_run["parallel"]["suite_id"], result.suite_id)
            self.assertIn(first_run["parallel"]["case_id"], {"case-one", "case-two"})
            self.assertFalse(audit.failed)
            self.assertEqual(status.payload["summary"]["suites"], 1)
            self.assertIn(
                "suite-created",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertNotIn(private_prompt, encoded)
            self.assertNotIn("sk-" + ("D" * 24), encoded)
            self.assertNotIn("suite-thread", encoded)

    def test_suite_report_compares_paired_cases_without_raw_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            suite = {
                "suite": "Paired Suite",
                "cases": [
                    {"id": "case-one", "prompt": "private case one"},
                    {"id": "case-two", "prompt": "private case two"},
                    {"id": "case-three", "prompt": "private case three"},
                ],
            }
            result = create_agent_suite_plan(
                vault,
                AGENT_CONFIG,
                suite,
                subject_prefix="paired-suite-thread",
                lanes=("scout", "reviewer"),
                mode="matrix",
            )
            scores = {
                "case-one": {"claude-primary": 0.60, "openai-backup": 0.80, "ollama-local": 0.66},
                "case-two": {"claude-primary": 0.61, "openai-backup": 0.82, "ollama-local": 0.67},
                "case-three": {"claude-primary": 0.62, "openai-backup": 0.84, "ollama-local": 0.68},
            }
            for plan in result.plans:
                suite_context = plan.payload["suite"]
                self.assertIsInstance(suite_context, dict)
                case_id = str(suite_context["case_id"])
                for run in plan.runs:
                    log_agent_outcome(
                        vault,
                        run_id=run.run_id,
                        status="succeeded",
                        metrics={"quality": scores[case_id][run.variant_id]},
                        usage={"total_tokens": 100, "latency_ms": 700, "cost_usd": 0.01},
                        output_text=f"private paired output {case_id}",
                    )

            report = report_agent_suite(
                vault,
                suite_id=result.suite_id,
                baseline_variant_id="claude-primary",
            )
            payload = json.loads(report.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            by_candidate = {item["candidate_variant_id"]: item for item in payload["pairwise"]}
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)

            self.assertEqual(payload["schema"], "griosai.agent-suite-report.v1")
            self.assertEqual(payload["baseline_variant_id"], "claude-primary")
            self.assertEqual(payload["winner_variant_id"], "openai-backup")
            self.assertEqual(payload["summary"]["complete_cases"], 3)
            self.assertEqual(by_candidate["openai-backup"]["paired_cases"], 3)
            self.assertEqual(by_candidate["openai-backup"]["status"], "beats-baseline")
            self.assertEqual(payload["efficiency_frontier"][0]["variant_id"], "openai-backup")
            self.assertGreater(payload["efficiency_frontier"][0]["metric_per_usd"], 0)
            self.assertEqual(payload["variant_summaries"][0]["usage"]["total_tokens_mean"], 100.0)
            self.assertEqual(status.payload["summary"]["suite_reports"], 1)
            self.assertIn(
                "suite-reported",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertTrue(report.report_path.exists())
            self.assertNotIn("private case", encoded)
            self.assertNotIn("private paired output", encoded)
            self.assertNotIn("paired-suite-thread", encoded)

    def test_budget_report_gates_usage_without_raw_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            runs = [
                create_agent_run(vault, AGENT_CONFIG, subject_key=f"budget-thread-{index}")
                for index in range(2)
            ]
            for index, run in enumerate(runs):
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": 0.8 + (index * 0.01)},
                    usage={
                        "total_tokens": 100 + (index * 25),
                        "latency_ms": 700 + (index * 50),
                        "cost_usd": 0.01 + (index * 0.005),
                    },
                    output_text=f"private budget output {index}",
                )

            within = budget_agent_harness(
                vault,
                experiment="cross-model-agent",
                max_cost_usd=0.1,
                max_total_tokens=1000,
                max_mean_latency_ms=1000,
                max_run_cost_usd=0.02,
                max_run_tokens=200,
                max_run_latency_ms=1000,
            )
            payload = json.loads(within.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = within.report_path.read_text(encoding="utf-8")

            self.assertFalse(within.over_budget)
            self.assertEqual(payload["schema"], "griosai.agent-budget.v1")
            self.assertEqual(payload["budget_status"], "within-budget")
            self.assertEqual(payload["summary"]["outcome_count"], 2)
            self.assertEqual(payload["summary"]["usage_count"], 2)
            self.assertEqual(payload["summary"]["total_tokens"], 225)
            self.assertAlmostEqual(payload["summary"]["total_cost_usd"], 0.025)
            self.assertEqual(payload["summary"]["mean_latency_ms"], 725.0)
            self.assertIn("Agent Harness Budget", report)
            self.assertNotIn("private budget output", encoded)

            over = budget_agent_harness(
                vault,
                experiment="cross-model-agent",
                max_total_tokens=200,
                max_run_tokens=110,
            )
            codes = {item["code"] for item in over.payload["findings"]}
            timeline = timeline_agent_harness(vault, experiment="cross-model-agent")

            self.assertTrue(over.over_budget)
            self.assertEqual(over.payload["budget_status"], "over-budget")
            self.assertIn("token-budget-exceeded", codes)
            self.assertIn("run-token-budget-exceeded", codes)
            self.assertIn(
                "budget-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )

    def test_drift_report_flags_recent_metric_regression_without_raw_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            subjects = _subjects_by_variant_count(
                AGENT_CONFIG,
                {"openai-backup"},
                count=4,
            )["openai-backup"]
            scores = (0.95, 0.94, 0.70, 0.69)
            for index, subject in enumerate(subjects):
                run = create_agent_run(vault, AGENT_CONFIG, subject_key=subject)
                self.assertEqual(run.variant_id, "openai-backup")
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": scores[index]},
                    usage={
                        "total_tokens": 100,
                        "latency_ms": 700 + (index * 10),
                        "cost_usd": 0.01,
                    },
                    output_text=f"private drift output {index}",
                )

            drift = detect_agent_drift(
                vault,
                experiment="cross-model-agent",
                baseline_window=2,
                recent_window=2,
                min_samples=2,
                max_metric_drop=0.1,
                max_latency_increase_ratio=1.0,
            )
            payload = json.loads(drift.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            codes = {item["code"] for item in payload["findings"]}
            status = summarize_agent_harness(vault, experiment="cross-model-agent")
            timeline = timeline_agent_harness(vault, experiment="cross-model-agent")
            report = drift.report_path.read_text(encoding="utf-8")

            self.assertTrue(drift.drift_detected)
            self.assertEqual(payload["schema"], "griosai.agent-drift.v1")
            self.assertEqual(payload["drift_status"], "drift-detected")
            self.assertIn("metric-regression", codes)
            self.assertEqual(payload["windows"][0]["metric"]["baseline_mean"], 0.945)
            self.assertEqual(payload["windows"][0]["metric"]["recent_mean"], 0.695)
            self.assertEqual(status.payload["summary"]["drift_reports"], 1)
            self.assertEqual(status.payload["experiments"][0]["latest_drift_status"], "drift-detected")
            self.assertIn(
                "drift-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertIn("Agent Harness Drift", report)
            self.assertNotIn("private drift output", encoded)

    def test_drift_can_gate_promotion_and_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            subjects = _subjects_by_variant_count(
                AGENT_CONFIG,
                {"claude-primary", "openai-backup", "ollama-local"},
                count=4,
            )
            scores = {
                "claude-primary": (0.70, 0.70, 0.70, 0.70),
                "openai-backup": (0.95, 0.94, 0.70, 0.69),
                "ollama-local": (0.60, 0.60, 0.60, 0.60),
            }
            for variant_id, variant_subjects in subjects.items():
                for index, subject in enumerate(variant_subjects):
                    run = create_agent_run(vault, AGENT_CONFIG, subject_key=subject)
                    self.assertEqual(run.variant_id, variant_id)
                    log_agent_outcome(
                        vault,
                        run_id=run.run_id,
                        status="succeeded",
                        metrics={"quality": scores[variant_id][index]},
                        usage={"total_tokens": 100, "latency_ms": 700, "cost_usd": 0.01},
                        output_text=f"private drift gate output {variant_id}",
                    )

            detect_agent_drift(
                vault,
                experiment="cross-model-agent",
                baseline_window=2,
                recent_window=2,
                min_samples=2,
                max_metric_drop=0.1,
            )
            blocked = promote_agent_experiment(
                vault,
                experiment="cross-model-agent",
                champion_variant_id="claude-primary",
                min_trials_per_variant=1,
                min_delta=0.05,
                require_drift=True,
            )
            blocked_readiness = assess_agent_readiness(
                vault,
                experiment="cross-model-agent",
                min_outcomes=12,
                require_drift=True,
            )
            blocked_codes = {item["code"] for item in blocked_readiness.payload["findings"]}

            self.assertFalse(blocked.ready)
            self.assertEqual(blocked.payload["promotion_status"], "blocked-by-drift")
            self.assertEqual(blocked.payload["evidence"]["latest_drift"]["drift_status"], "drift-detected")
            self.assertFalse(blocked_readiness.ready)
            self.assertIn("drift-not-stable", blocked_codes)

            stable = detect_agent_drift(
                vault,
                experiment="cross-model-agent",
                baseline_window=2,
                recent_window=2,
                min_samples=2,
                max_metric_drop=1.0,
            )
            ready = promote_agent_experiment(
                vault,
                experiment="cross-model-agent",
                champion_variant_id="claude-primary",
                min_trials_per_variant=1,
                min_delta=0.05,
                require_drift=True,
            )
            ready_readiness = assess_agent_readiness(
                vault,
                experiment="cross-model-agent",
                min_outcomes=12,
                require_drift=True,
            )

            self.assertFalse(stable.drift_detected)
            self.assertEqual(stable.payload["drift_status"], "stable")
            self.assertTrue(ready.ready)
            self.assertEqual(ready.payload["promotion_status"], "ready")
            self.assertEqual(ready.payload["evidence"]["latest_drift"]["drift_status"], "stable")
            self.assertTrue(ready_readiness.ready)

    def test_promotion_can_require_budget_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            subjects = _subjects_by_variant(
                AGENT_CONFIG,
                {"claude-primary", "openai-backup", "ollama-local"},
            )
            scores = {
                "claude-primary": 0.72,
                "openai-backup": 0.94,
                "ollama-local": 0.80,
            }
            for variant_id, subject in subjects.items():
                run = create_agent_run(vault, AGENT_CONFIG, subject_key=subject)
                self.assertEqual(run.variant_id, variant_id)
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": scores[variant_id]},
                    usage={"total_tokens": 100, "latency_ms": 700, "cost_usd": 0.01},
                    output_text=f"private promotion budget output {variant_id}",
                )

            blocked = promote_agent_experiment(
                vault,
                experiment="cross-model-agent",
                champion_variant_id="claude-primary",
                min_trials_per_variant=1,
                require_budget=True,
            )
            budget_agent_harness(
                vault,
                experiment="cross-model-agent",
                max_cost_usd=1,
                max_total_tokens=1000,
                max_mean_latency_ms=1000,
            )
            ready = promote_agent_experiment(
                vault,
                experiment="cross-model-agent",
                champion_variant_id="claude-primary",
                min_trials_per_variant=1,
                require_budget=True,
            )

            self.assertFalse(blocked.ready)
            self.assertEqual(blocked.payload["promotion_status"], "blocked-by-budget")
            self.assertEqual(ready.payload["promotion_status"], "ready")
            self.assertTrue(ready.ready)
            self.assertEqual(ready.payload["candidate_variant_id"], "openai-backup")
            self.assertEqual(
                ready.payload["evidence"]["latest_budget"]["budget_status"],
                "within-budget",
            )

    def test_readiness_gate_rolls_up_required_experiment_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="readiness-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            scores = {
                "claude-primary": 0.78,
                "openai-backup": 0.95,
                "ollama-local": 0.66,
            }
            for run in plan.runs:
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": scores[run.variant_id]},
                    usage={"total_tokens": 100, "latency_ms": 700, "cost_usd": 0.01},
                    output_text="private readiness output",
                )

            compare_agent_experiment(
                vault,
                experiment="cross-model-agent",
                min_samples_per_variant=1,
            )
            budget_agent_harness(
                vault,
                experiment="cross-model-agent",
                max_cost_usd=1,
                max_total_tokens=1000,
                max_mean_latency_ms=1000,
            )
            remember_agent_experiment(
                vault,
                experiment="cross-model-agent",
                min_trials_per_variant=1,
            )
            route_agent_lanes(
                vault,
                experiment="cross-model-agent",
                min_trials_per_lane_variant=1,
            )
            quorum_agent_plan(
                vault,
                plan_id=plan.plan_id,
                min_agreement_ratio=1,
            )
            promote_agent_experiment(
                vault,
                experiment="cross-model-agent",
                champion_variant_id="claude-primary",
                min_trials_per_variant=1,
                require_budget=True,
            )

            readiness = assess_agent_readiness(
                vault,
                experiment="cross-model-agent",
                min_outcomes=len(plan.runs),
                max_failed_outcomes=0,
                require_comparison=True,
                require_budget=True,
                require_route=True,
                require_memory=True,
                require_quorum=True,
                require_promotion=True,
            )
            payload = json.loads(readiness.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = readiness.report_path.read_text(encoding="utf-8")
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)

            self.assertTrue(readiness.ready)
            self.assertEqual(payload["schema"], "griosai.agent-readiness.v1")
            self.assertEqual(payload["readiness_status"], "ready")
            self.assertEqual(payload["summary"]["failed_outcomes"], 0)
            self.assertEqual(payload["evidence"]["latest_budget"]["budget_status"], "within-budget")
            self.assertEqual(payload["evidence"]["latest_quorum"]["quorum_status"], "pass")
            self.assertEqual(payload["evidence"]["latest_promotion"]["promotion_status"], "ready")
            self.assertEqual(status.payload["summary"]["readiness"], 1)
            self.assertEqual(status.payload["experiments"][0]["latest_readiness_status"], "ready")
            self.assertIn(
                "readiness-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertIn("Agent Harness Readiness", report)
            self.assertNotIn("private readiness", encoded)
            self.assertNotIn("readiness-thread", encoded)

    def test_readiness_gate_blocks_missing_required_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            run = create_agent_run(vault, AGENT_CONFIG, subject_key="readiness-budget")
            log_agent_outcome(
                vault,
                run_id=run.run_id,
                status="succeeded",
                metrics={"quality": 0.82},
                usage={"total_tokens": 100, "latency_ms": 700, "cost_usd": 0.01},
            )

            readiness = assess_agent_readiness(
                vault,
                experiment="cross-model-agent",
                require_budget=True,
            )
            codes = {item["code"] for item in readiness.payload["findings"]}

            self.assertFalse(readiness.ready)
            self.assertEqual(readiness.payload["readiness_status"], "blocked")
            self.assertIn("budget-missing", codes)
            self.assertEqual(readiness.payload["summary"]["fail"], 1)

    def test_rollout_plan_stages_ready_challenger_with_rollback_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="rollout-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            scores = {
                "claude-primary": 0.75,
                "openai-backup": 0.96,
                "ollama-local": 0.7,
            }
            for run in plan.runs:
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": scores[run.variant_id]},
                    usage={"total_tokens": 100, "latency_ms": 700, "cost_usd": 0.01},
                    output_text="private rollout output",
                )
            compare_agent_experiment(
                vault,
                experiment="cross-model-agent",
                min_samples_per_variant=1,
            )
            budget_agent_harness(
                vault,
                experiment="cross-model-agent",
                max_cost_usd=1,
                max_total_tokens=1000,
                max_mean_latency_ms=1000,
            )
            remember_agent_experiment(vault, experiment="cross-model-agent", min_trials_per_variant=1)
            route_agent_lanes(vault, experiment="cross-model-agent", min_trials_per_lane_variant=1)
            quorum_agent_plan(vault, plan_id=plan.plan_id, min_agreement_ratio=1)
            promote_agent_experiment(
                vault,
                experiment="cross-model-agent",
                champion_variant_id="claude-primary",
                min_trials_per_variant=1,
                require_budget=True,
            )
            assess_agent_readiness(
                vault,
                experiment="cross-model-agent",
                min_outcomes=len(plan.runs),
                require_comparison=True,
                require_budget=True,
                require_route=True,
                require_memory=True,
                require_quorum=True,
                require_promotion=True,
            )

            rollout = plan_agent_rollout(
                vault,
                experiment="cross-model-agent",
                stages=(0.1, 0.5, 1.0),
                min_observation_runs=2,
                require_readiness=True,
                require_promotion=True,
                require_budget=True,
            )
            payload = json.loads(rollout.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = rollout.report_path.read_text(encoding="utf-8")
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)

            self.assertTrue(rollout.ready)
            self.assertEqual(payload["schema"], "griosai.agent-rollout.v1")
            self.assertEqual(payload["rollout_status"], "ready")
            self.assertEqual(payload["candidate_variant_id"], "openai-backup")
            self.assertEqual(payload["summary"]["stage_count"], 3)
            self.assertEqual(payload["stages"][0]["candidate_share"], 0.1)
            self.assertEqual(payload["stages"][-1]["candidate_share"], 1.0)
            self.assertEqual(payload["rollback_policy"]["fallback"], "return-to-champion")
            self.assertEqual(status.payload["summary"]["rollouts"], 1)
            self.assertEqual(status.payload["experiments"][0]["latest_rollout_status"], "ready")
            self.assertIn(
                "rollout-planned",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertIn("Agent Harness Rollout", report)
            self.assertNotIn("private rollout", encoded)
            self.assertNotIn("rollout-thread", encoded)

            for run in plan.runs:
                if run.variant_id not in {"openai-backup", "claude-primary"}:
                    continue
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": 0.97 if run.variant_id == "openai-backup" else 0.76},
                    usage={"total_tokens": 80, "latency_ms": 650, "cost_usd": 0.01},
                    output_text="private rollout stage output",
                )
            budget_agent_harness(
                vault,
                experiment="cross-model-agent",
                max_cost_usd=1,
                max_total_tokens=2000,
                max_mean_latency_ms=1000,
            )
            stage_check = check_agent_rollout_stage(
                vault,
                rollout_id=rollout.rollout_id,
                stage_index=1,
                min_stage_outcomes=2,
                require_budget=True,
                require_readiness=True,
                min_metric_delta=0.05,
            )
            check_payload = json.loads(stage_check.path.read_text(encoding="utf-8"))
            check_report = stage_check.report_path.read_text(encoding="utf-8")
            timeline = timeline_agent_harness(vault)

            self.assertEqual(stage_check.decision, "advance")
            self.assertEqual(check_payload["schema"], "griosai.agent-rollout-check.v1")
            self.assertEqual(check_payload["summary"]["candidate_outcome_count"], 2)
            self.assertGreater(check_payload["summary"]["metric_gap"], 0.05)
            self.assertIn("Agent Harness Rollout Check", check_report)
            self.assertIn(
                "rollout-checked",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertNotIn("private rollout stage", json.dumps(check_payload, sort_keys=True))

    def test_evolve_runs_full_metadata_loop_with_optional_rollout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="evolve-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            scores = {
                "claude-primary": 0.74,
                "openai-backup": 0.96,
                "ollama-local": 0.68,
            }
            for run in plan.runs:
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": scores[run.variant_id]},
                    usage={"total_tokens": 100, "latency_ms": 700, "cost_usd": 0.01},
                    output_text="private evolve output",
                )

            evolve = evolve_agent_experiment(
                vault,
                experiment="cross-model-agent",
                min_trials_per_variant=1,
                min_samples_per_variant=1,
                max_cost_usd=1,
                max_total_tokens=2000,
                max_mean_latency_ms=1000,
                require_budget=True,
                require_route=True,
                champion_variant_id="claude-primary",
                min_delta=0.05,
                plan_rollout=True,
                rollout_stages=(0.2, 1.0),
            )
            payload = json.loads(evolve.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = evolve.report_path.read_text(encoding="utf-8")
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)
            step_names = {step["step"] for step in payload["steps"]}

            self.assertFalse(evolve.failed)
            self.assertEqual(payload["schema"], "griosai.agent-evolve.v1")
            self.assertEqual(payload["evolve_status"], "complete")
            self.assertEqual(
                step_names,
                {
                    "compare",
                    "improve",
                    "memory",
                    "allocate",
                    "route",
                    "budget",
                    "promote",
                    "readiness",
                    "rollout",
                },
            )
            self.assertEqual(payload["summary"]["failed_steps"], 0)
            self.assertEqual(status.payload["summary"]["evolutions"], 1)
            self.assertEqual(status.payload["experiments"][0]["latest_evolve_status"], "complete")
            self.assertIn(
                "evolve-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertIn("Agent Harness Evolve", report)
            self.assertNotIn("private evolve", encoded)
            self.assertNotIn("evolve-thread", encoded)

    def test_power_plan_sizes_next_ab_experiment_without_private_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="power-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            scores = {
                ("claude-primary", "scout"): 0.70,
                ("claude-primary", "reviewer"): 0.72,
                ("openai-backup", "scout"): 0.92,
                ("openai-backup", "reviewer"): 0.95,
                ("ollama-local", "scout"): 0.64,
                ("ollama-local", "reviewer"): 0.66,
            }
            for run in plan.runs:
                lane = str(run.payload["parallel"]["lane_id"])
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": scores[(run.variant_id, lane)]},
                    usage={"total_tokens": 100, "latency_ms": 700, "cost_usd": 0.01},
                    output_text="private power output",
                )

            power = plan_agent_power(
                vault,
                experiment="cross-model-agent",
                baseline_variant_id="claude-primary",
                min_detectable_effect=0.01,
                max_total_tokens=1,
            )
            payload = json.loads(power.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            report = power.report_path.read_text(encoding="utf-8")
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)

            self.assertEqual(payload["schema"], "griosai.agent-power.v1")
            self.assertEqual(payload["power_status"], "budget-limited")
            self.assertEqual(payload["baseline_variant_id"], "claude-primary")
            self.assertGreater(payload["summary"]["max_required_samples_per_variant"], 2)
            self.assertGreater(payload["summary"]["budget_limited_candidates"], 0)
            self.assertEqual(status.payload["summary"]["power_reports"], 1)
            self.assertEqual(status.payload["experiments"][0]["latest_power_status"], "budget-limited")
            self.assertIn(
                "power-planned",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertIn("Agent Harness Power", report)
            self.assertNotIn("private power", encoded)
            self.assertNotIn("power-thread", encoded)

    def test_schedule_creates_claimable_plan_from_power_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="schedule-pilot-thread",
                lanes=("scout", "reviewer"),
                replicas=1,
            )
            for run in plan.runs:
                lane = str(run.payload["parallel"]["lane_id"])
                quality = (
                    0.76
                    if run.variant_id == "claude-primary" and lane == "scout"
                    else 0.84
                    if run.variant_id == "claude-primary"
                    else 0.78
                    if lane == "scout"
                    else 0.88
                )
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": quality},
                    usage={"total_tokens": 100, "latency_ms": 700, "cost_usd": 0.01},
                    output_text="private schedule pilot output",
                )
            power = plan_agent_power(
                vault,
                experiment="cross-model-agent",
                baseline_variant_id="claude-primary",
                min_detectable_effect=0.01,
                fallback_stddev=0.1,
            )

            schedule = schedule_agent_batch(
                vault,
                experiment="cross-model-agent",
                subject_key="private-schedule-thread",
                lanes=("scout", "reviewer"),
                max_runs=6,
                power_id=power.power_id,
            )
            payload = json.loads(schedule.path.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, sort_keys=True)
            plan_payload = json.loads(
                (vault / str(payload["plan_path"])).read_text(encoding="utf-8")
            )
            status = summarize_agent_harness(vault)
            timeline = timeline_agent_harness(vault)
            claim = claim_agent_run(
                vault,
                plan_id=str(schedule.plan_id),
                client_id="schedule-worker",
            )
            for block in payload["blocks"]:
                for run_ref in block["runs"]:
                    role = str(run_ref["comparison_role"])
                    log_agent_outcome(
                        vault,
                        run_id=str(run_ref["run_id"]),
                        status="succeeded",
                        metrics={"quality": 0.72 if role == "baseline" else 0.92},
                        usage={"total_tokens": 90, "latency_ms": 650, "cost_usd": 0.008},
                        output_text="private schedule report output",
                    )
            report = report_agent_schedule(vault, schedule_id=schedule.schedule_id)
            report_payload = json.loads(report.path.read_text(encoding="utf-8"))
            report_encoded = json.dumps(report_payload, sort_keys=True)
            leaderboard = write_agent_leaderboard(
                vault,
                experiment="cross-model-agent",
                baseline_variant_id="claude-primary",
            )
            leaderboard_payload = json.loads(leaderboard.path.read_text(encoding="utf-8"))
            leaderboard_encoded = json.dumps(leaderboard_payload, sort_keys=True)
            config = propose_agent_config(
                vault,
                experiment="cross-model-agent",
                source="leaderboard",
            )
            config_payload = json.loads(config.path.read_text(encoding="utf-8"))
            proposed_config = json.loads(config.config_path.read_text(encoding="utf-8"))
            config_encoded = json.dumps(config_payload, sort_keys=True)
            status_after_report = summarize_agent_harness(vault)
            timeline_after_report = timeline_agent_harness(vault)

            self.assertEqual(payload["schema"], "griosai.agent-schedule.v1")
            self.assertEqual(payload["schedule_status"], "scheduled-partial")
            self.assertEqual(payload["summary"]["scheduled_runs"], 6)
            self.assertEqual(payload["summary"]["block_count"], 3)
            self.assertEqual(len(payload["blocks"]), 3)
            self.assertEqual(len(payload["runs"]), 6)
            self.assertTrue(all(len(block["runs"]) == 2 for block in payload["blocks"]))
            self.assertIsNotNone(schedule.plan_id)
            self.assertTrue(Path(str(payload["plan_path"])).exists() or payload["plan_path"])
            self.assertEqual(plan_payload["schedule"]["block_count"], 3)
            self.assertTrue(all("block_id" in run for run in plan_payload["runs"]))
            self.assertEqual(status.payload["summary"]["schedules"], 1)
            self.assertEqual(status.payload["experiments"][0]["latest_schedule_status"], "scheduled-partial")
            self.assertIn(
                "schedule-written",
                {event["event_type"] for event in timeline.payload["events"]},
            )
            self.assertEqual(claim.plan_id, schedule.plan_id)
            self.assertEqual(report_payload["schema"], "griosai.agent-schedule-report.v1")
            self.assertEqual(report_payload["report_status"], "complete")
            self.assertEqual(report_payload["summary"]["complete_blocks"], len(payload["blocks"]))
            self.assertEqual(report_payload["summary"]["paired_comparisons"], len(payload["blocks"]))
            self.assertGreaterEqual(report_payload["summary"]["beats_baseline"], 1)
            self.assertIn(
                "beats-baseline",
                {item["status"] for item in report_payload["pairwise"]},
            )
            self.assertEqual(leaderboard_payload["schema"], "griosai.agent-leaderboard.v1")
            self.assertIn(leaderboard_payload["leaderboard_status"], {"ready", "needs-samples"})
            self.assertIsNotNone(leaderboard_payload["winner_variant_id"])
            self.assertEqual(
                leaderboard_payload["leaderboard"][0]["variant_id"],
                leaderboard_payload["winner_variant_id"],
            )
            self.assertIn("schedule_report", leaderboard_payload["source_artifacts"])
            self.assertEqual(config_payload["schema"], "griosai.agent-config-proposal.v1")
            self.assertIn(config_payload["config_status"], {"ready", "needs-review"})
            self.assertEqual(config_payload["source"]["selected"], "leaderboard")
            self.assertGreater(config_payload["summary"]["operation_count"], 0)
            self.assertTrue(config_payload["patch"]["operations"])
            self.assertIn("leaderboard", proposed_config["traffic_salt"])
            ExperimentSpec.from_mapping(proposed_config)
            self.assertEqual(status_after_report.payload["summary"]["schedule_reports"], 1)
            self.assertEqual(status_after_report.payload["summary"]["leaderboards"], 1)
            self.assertEqual(status_after_report.payload["summary"]["config_proposals"], 1)
            self.assertEqual(
                status_after_report.payload["experiments"][0]["latest_schedule_report_status"],
                "complete",
            )
            self.assertEqual(
                status_after_report.payload["experiments"][0]["latest_leaderboard_winner"],
                leaderboard_payload["winner_variant_id"],
            )
            self.assertIn(
                status_after_report.payload["experiments"][0]["latest_config_status"],
                {"ready", "needs-review"},
            )
            self.assertIn(
                "schedule-reported",
                {event["event_type"] for event in timeline_after_report.payload["events"]},
            )
            self.assertIn(
                "leaderboard-written",
                {event["event_type"] for event in timeline_after_report.payload["events"]},
            )
            self.assertIn(
                "config-proposed",
                {event["event_type"] for event in timeline_after_report.payload["events"]},
            )
            self.assertNotIn("private-schedule-thread", encoded)
            self.assertNotIn("private schedule pilot", encoded)
            self.assertNotIn("private schedule report output", report_encoded)
            self.assertNotIn("private schedule report output", leaderboard_encoded)
            self.assertNotIn("private schedule report output", config_encoded)

    def test_rollout_plan_blocks_missing_required_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            run = create_agent_run(vault, AGENT_CONFIG, subject_key="rollout-blocked")
            log_agent_outcome(
                vault,
                run_id=run.run_id,
                status="succeeded",
                metrics={"quality": 0.82},
                usage={"total_tokens": 100, "latency_ms": 700, "cost_usd": 0.01},
            )

            rollout = plan_agent_rollout(
                vault,
                experiment="cross-model-agent",
                candidate_variant_id="openai-backup",
                require_readiness=True,
            )
            codes = {item["code"] for item in rollout.payload["findings"]}

            self.assertFalse(rollout.ready)
            self.assertEqual(rollout.payload["rollout_status"], "blocked")
            self.assertIn("readiness-missing", codes)

    def test_rollout_check_rolls_back_on_stage_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            plan = create_agent_matrix_plan(
                vault,
                AGENT_CONFIG,
                subject_key="rollout-failure",
                lanes=("scout",),
                replicas=1,
            )
            for run in plan.runs:
                log_agent_outcome(
                    vault,
                    run_id=run.run_id,
                    status="succeeded",
                    metrics={"quality": 0.9 if run.variant_id == "openai-backup" else 0.7},
                    usage={"total_tokens": 80, "latency_ms": 650, "cost_usd": 0.01},
                )
            rollout = plan_agent_rollout(
                vault,
                experiment="cross-model-agent",
                candidate_variant_id="openai-backup",
                stages=(0.5, 1.0),
            )
            candidate_runs = [run for run in plan.runs if run.variant_id == "openai-backup"]
            self.assertEqual(len(candidate_runs), 1)
            log_agent_outcome(
                vault,
                run_id=candidate_runs[0].run_id,
                status="failed",
                metrics={"quality": 0.1},
                usage={"total_tokens": 80, "latency_ms": 650, "cost_usd": 0.01},
                failure_code="stage_failure",
                output_text="private failed rollout stage output",
            )

            stage_check = check_agent_rollout_stage(
                vault,
                rollout_id=rollout.rollout_id,
                stage_index=1,
                min_stage_outcomes=1,
                max_stage_failed_outcomes=0,
            )
            payload = json.loads(stage_check.path.read_text(encoding="utf-8"))
            codes = {item["code"] for item in payload["findings"]}

            self.assertEqual(stage_check.decision, "rollback")
            self.assertIn("stage-failed-outcomes", codes)
            self.assertNotIn("private failed rollout", json.dumps(payload, sort_keys=True))

    def test_drift_can_gate_rollout_and_stage_advance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = ensure_vault(Path(tmp) / "vault")
            subjects = _subjects_by_variant_count(
                AGENT_CONFIG,
                {"claude-primary", "openai-backup"},
                count=4,
            )
            scores = {
                "claude-primary": (0.74, 0.74, 0.74, 0.74),
                "openai-backup": (0.95, 0.94, 0.70, 0.69),
            }
            for variant_id, variant_subjects in subjects.items():
                for index, subject in enumerate(variant_subjects):
                    run = create_agent_run(vault, AGENT_CONFIG, subject_key=subject)
                    self.assertEqual(run.variant_id, variant_id)
                    log_agent_outcome(
                        vault,
                        run_id=run.run_id,
                        status="succeeded",
                        metrics={"quality": scores[variant_id][index]},
                        usage={"total_tokens": 100, "latency_ms": 700, "cost_usd": 0.01},
                    )

            detect_agent_drift(
                vault,
                experiment="cross-model-agent",
                baseline_window=2,
                recent_window=2,
                min_samples=1,
                max_metric_drop=0.1,
            )
            blocked = plan_agent_rollout(
                vault,
                experiment="cross-model-agent",
                champion_variant_id="claude-primary",
                candidate_variant_id="openai-backup",
                require_drift=True,
            )
            blocked_codes = {item["code"] for item in blocked.payload["findings"]}

            self.assertFalse(blocked.ready)
            self.assertEqual(blocked.payload["rollout_status"], "blocked")
            self.assertIn("drift-not-stable", blocked_codes)
            self.assertTrue(blocked.payload["policy"]["require_drift"])

            detect_agent_drift(
                vault,
                experiment="cross-model-agent",
                baseline_window=2,
                recent_window=2,
                min_samples=1,
                max_metric_drop=1.0,
            )
            ready = plan_agent_rollout(
                vault,
                experiment="cross-model-agent",
                champion_variant_id="claude-primary",
                candidate_variant_id="openai-backup",
                require_drift=True,
            )
            self.assertTrue(ready.ready)
            self.assertEqual(ready.payload["evidence"]["latest_drift"]["drift_status"], "stable")

            detect_agent_drift(
                vault,
                experiment="cross-model-agent",
                baseline_window=2,
                recent_window=2,
                min_samples=1,
                max_metric_drop=0.1,
            )
            check = check_agent_rollout_stage(
                vault,
                rollout_id=ready.rollout_id,
                stage_index=1,
                min_stage_outcomes=1,
                require_drift=True,
            )
            check_codes = {item["code"] for item in check.payload["findings"]}

            self.assertEqual(check.decision, "rollback")
            self.assertIn("drift-not-stable", check_codes)
            self.assertTrue(check.payload["policy"]["require_drift"])

    def test_sensitive_variant_setting_is_rejected(self) -> None:
        config = json.loads(json.dumps(AGENT_CONFIG))
        config["variants"][0]["settings"]["api_key"] = "placeholder"

        with self.assertRaises(ValueError):
            ExperimentSpec.from_mapping(config)

    def test_cli_agent_run_outcome_and_improve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            config = Path(tmp) / "agent.json"
            config.write_text(json.dumps(AGENT_CONFIG), encoding="utf-8")
            prompt = Path(tmp) / "prompt.md"
            prompt.write_text("Private prompt body", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-run",
                            "--vault",
                            str(vault),
                            "--config-file",
                            str(config),
                            "--subject",
                            "cli-thread",
                            "--prompt-file",
                            str(prompt),
                            "--json",
                        ]
                    ),
                    0,
                )
            run_payload = json.loads(output.getvalue())
            self.assertTrue((vault / "agent-runs").is_dir())
            self.assertNotIn("Private prompt body", output.getvalue())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-score",
                            "--vault",
                            str(vault),
                            "--run-id",
                            run_payload["run_id"],
                            "--scores-json",
                            '{"correctness": 0.8, "safety": 1, "efficiency": 0.8}',
                            "--usage-json",
                            '{"prompt_tokens": 90, "completion_tokens": 10, "cost_usd": 0.01}',
                            "--json",
                        ]
                    ),
                    0,
                )
            score_payload = json.loads(output.getvalue())
            self.assertEqual(score_payload["metrics"]["quality"], 0.86)
            self.assertEqual(score_payload["outcome"]["usage"]["total_tokens"], 100)
            self.assertTrue(Path(score_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-outcome",
                            "--vault",
                            str(vault),
                            "--run-id",
                            run_payload["run_id"],
                            "--status",
                            "succeeded",
                            "--metrics-json",
                            '{"quality": 0.8}',
                            "--usage-json",
                            '{"total_tokens": 120, "latency_ms": 800}',
                            "--json",
                        ]
                    ),
                    0,
                )
            outcome_payload = json.loads(output.getvalue())
            self.assertEqual(outcome_payload["metrics"]["quality"], 0.8)
            self.assertEqual(outcome_payload["usage"]["latency_ms"], 800.0)

            results_file = Path(tmp) / "results.json"
            results_file.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "run_id": run_payload["run_id"],
                                "status": "succeeded",
                                "metrics": {"quality": 0.83},
                                "usage": {"total_tokens": 130, "latency_ms": 850},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-ingest",
                            "--vault",
                            str(vault),
                            "--results-file",
                            str(results_file),
                            "--json",
                        ]
                    ),
                    0,
                )
            ingest_payload = json.loads(output.getvalue())
            self.assertEqual(ingest_payload["summary"]["ingested_count"], 1)
            self.assertTrue(Path(ingest_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-budget",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--max-cost-usd",
                            "1",
                            "--max-total-tokens",
                            "1000",
                            "--max-mean-latency-ms",
                            "2000",
                            "--json",
                        ]
                    ),
                    0,
                )
            budget_payload = json.loads(output.getvalue())
            self.assertEqual(budget_payload["budget_status"], "within-budget")
            self.assertTrue(Path(budget_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-readiness",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--require-budget",
                            "--json",
                        ]
                    ),
                    0,
                )
            readiness_payload = json.loads(output.getvalue())
            self.assertTrue(readiness_payload["ready"])
            self.assertEqual(readiness_payload["readiness_status"], "ready-with-warnings")
            self.assertTrue(Path(readiness_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-rollout",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--candidate-variant",
                            "openai-backup",
                            "--stages",
                            "0.1,1",
                            "--require-budget",
                            "--json",
                        ]
                    ),
                    0,
                )
            rollout_payload = json.loads(output.getvalue())
            self.assertTrue(rollout_payload["ready"])
            self.assertEqual(rollout_payload["rollout_status"], "ready-with-warnings")
            self.assertEqual(rollout_payload["candidate_variant_id"], "openai-backup")
            self.assertTrue(Path(rollout_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-rollout-check",
                            "--vault",
                            str(vault),
                            "--rollout-id",
                            rollout_payload["rollout_id"],
                            "--min-stage-outcomes",
                            "1",
                            "--json",
                        ]
                    ),
                    1,
                )
            rollout_check_payload = json.loads(output.getvalue())
            self.assertEqual(rollout_check_payload["decision"], "hold")
            self.assertTrue(Path(rollout_check_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-budget",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--max-total-tokens",
                            "1",
                            "--json",
                        ]
                    ),
                    1,
                )
            over_budget_payload = json.loads(output.getvalue())
            self.assertEqual(over_budget_payload["budget_status"], "over-budget")

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-dashboard",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--limit",
                            "20",
                            "--json",
                        ]
                    ),
                    0,
                )
            dashboard_payload = json.loads(output.getvalue())
            self.assertEqual(dashboard_payload["scope"], "cross-model-agent")
            self.assertTrue(Path(dashboard_payload["path"]).exists())
            self.assertTrue(Path(dashboard_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-retry",
                            "--vault",
                            str(vault),
                            "--run-id",
                            run_payload["run_id"],
                            "--reason",
                            "cli_retry",
                            "--json",
                        ]
                    ),
                    0,
                )
            retry_payload = json.loads(output.getvalue())
            self.assertEqual(retry_payload["original_run_id"], run_payload["run_id"])
            self.assertTrue(Path(retry_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-compare",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--min-samples-per-variant",
                            "1",
                            "--json",
                        ]
                    ),
                    0,
                )
            compare_payload = json.loads(output.getvalue())
            self.assertEqual(compare_payload["experiment"], "cross-model-agent")
            self.assertTrue(Path(compare_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-decision",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--baseline-variant",
                            "claude-primary",
                            "--candidate-variant",
                            "openai-backup",
                            "--min-samples-per-variant",
                            "1",
                            "--confidence-threshold",
                            "0.5",
                            "--json",
                        ]
                    ),
                    0,
                )
            decision_payload = json.loads(output.getvalue())
            self.assertEqual(decision_payload["experiment"], "cross-model-agent")
            self.assertIn(decision_payload["decision"], {"continue", "stop-promote", "stop-baseline"})
            self.assertTrue(Path(decision_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-improve",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--min-trials-per-variant",
                            "1",
                            "--json",
                        ]
                    ),
                    0,
                )
            improve_payload = json.loads(output.getvalue())
            self.assertEqual(improve_payload["experiment"], "cross-model-agent")
            self.assertTrue(Path(improve_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-memory",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--min-trials-per-variant",
                            "1",
                            "--max-lessons",
                            "6",
                            "--json",
                        ]
                    ),
                    0,
                )
            memory_payload = json.loads(output.getvalue())
            self.assertEqual(memory_payload["experiment"], "cross-model-agent")
            self.assertTrue(Path(memory_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-curriculum",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--metric-threshold",
                            "0.8",
                            "--max-cases",
                            "4",
                            "--json",
                        ]
                    ),
                    0,
                )
            curriculum_payload = json.loads(output.getvalue())
            self.assertEqual(curriculum_payload["experiment"], "cross-model-agent")
            self.assertTrue(Path(curriculum_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-allocate",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--strategy",
                            "ucb1",
                            "--min-trials-per-variant",
                            "1",
                            "--json",
                        ]
                    ),
                    0,
                )
            allocation_payload = json.loads(output.getvalue())
            self.assertEqual(allocation_payload["experiment"], "cross-model-agent")
            self.assertTrue(Path(allocation_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-route",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--strategy",
                            "ucb1",
                            "--min-trials-per-lane-variant",
                            "1",
                            "--json",
                        ]
                    ),
                    0,
                )
            route_payload = json.loads(output.getvalue())
            self.assertEqual(route_payload["experiment"], "cross-model-agent")
            self.assertTrue(Path(route_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-promote",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--min-trials-per-variant",
                            "1",
                            "--json",
                        ]
                    ),
                    0,
                )
            promote_payload = json.loads(output.getvalue())
            self.assertEqual(promote_payload["experiment"], "cross-model-agent")
            self.assertTrue(Path(promote_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-evolve",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--min-trials-per-variant",
                            "1",
                            "--min-samples-per-variant",
                            "1",
                            "--max-lessons",
                            "4",
                            "--json",
                        ]
                    ),
                    0,
                )
            evolve_payload = json.loads(output.getvalue())
            self.assertEqual(evolve_payload["experiment"], "cross-model-agent")
            self.assertIn(evolve_payload["evolve_status"], {"complete", "needs-review"})
            self.assertTrue(Path(evolve_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-power",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--min-detectable-effect",
                            "0.05",
                            "--fallback-stddev",
                            "0.1",
                            "--json",
                        ]
                    ),
                    0,
                )
            power_payload = json.loads(output.getvalue())
            self.assertEqual(power_payload["experiment"], "cross-model-agent")
            self.assertIn(power_payload["power_status"], {"ready", "needs-samples"})
            self.assertTrue(Path(power_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-schedule",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--subject",
                            "cli-schedule-thread",
                            "--lanes",
                            "scout,reviewer",
                            "--max-runs",
                            "3",
                            "--json",
                        ]
                    ),
                    0,
                )
            schedule_payload = json.loads(output.getvalue())
            self.assertEqual(schedule_payload["experiment"], "cross-model-agent")
            self.assertIn(schedule_payload["schedule_status"], {"scheduled", "scheduled-partial", "no-runs"})
            self.assertTrue(Path(schedule_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-schedule-report",
                            "--vault",
                            str(vault),
                            "--schedule-id",
                            str(schedule_payload["schedule_id"]),
                            "--json",
                        ]
                    ),
                    0,
                )
            schedule_report_payload = json.loads(output.getvalue())
            self.assertEqual(schedule_report_payload["schedule_id"], schedule_payload["schedule_id"])
            self.assertIn(schedule_report_payload["report_status"], {"complete", "partial", "no-outcomes", "no-blocks"})
            self.assertTrue(Path(schedule_report_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-arena",
                            "--vault",
                            str(vault),
                            "--config-file",
                            str(config),
                            "--subject",
                            "cli-arena",
                            "--lanes",
                            "reviewer",
                            "--max-runs",
                            "6",
                            "--json",
                        ]
                    ),
                    0,
                )
            arena_payload = json.loads(output.getvalue())
            self.assertEqual(arena_payload["experiment"], "cross-model-agent")
            self.assertIn(arena_payload["arena_status"], {"scheduled", "scheduled-partial"})
            self.assertTrue(Path(arena_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-arena-report",
                            "--vault",
                            str(vault),
                            "--arena-id",
                            str(arena_payload["arena_id"]),
                            "--json",
                        ]
                    ),
                    0,
                )
            arena_report_payload = json.loads(output.getvalue())
            self.assertEqual(arena_report_payload["arena_id"], arena_payload["arena_id"])
            self.assertIn(arena_report_payload["report_status"], {"complete", "partial", "no-outcomes"})
            self.assertTrue(Path(arena_report_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-leaderboard",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--json",
                        ]
                    ),
                    0,
                )
            leaderboard_payload = json.loads(output.getvalue())
            self.assertEqual(leaderboard_payload["experiment"], "cross-model-agent")
            self.assertIn(leaderboard_payload["leaderboard_status"], {"ready", "needs-samples", "needs-evidence", "inconclusive"})
            self.assertTrue(Path(leaderboard_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-config",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--source",
                            "auto",
                            "--json",
                        ]
                    ),
                    0,
                )
            config_payload = json.loads(output.getvalue())
            self.assertEqual(config_payload["experiment"], "cross-model-agent")
            self.assertIn(config_payload["config_status"], {"ready", "needs-review", "no-change"})
            self.assertTrue(Path(config_payload["config_path"]).exists())
            self.assertTrue(Path(config_payload["report_path"]).exists())

    def test_cli_agent_plan_and_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "vault"
            config = Path(tmp) / "agent.json"
            config.write_text(json.dumps(AGENT_CONFIG), encoding="utf-8")
            suite_file = Path(tmp) / "suite.json"
            suite_file.write_text(
                json.dumps(
                    {
                        "suite": "CLI Suite",
                        "cases": [
                            {"id": "cli-case-one", "prompt": "Private CLI suite prompt"},
                            {"id": "cli-case-two", "prompt": "Second private CLI task"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            pipeline_file = Path(tmp) / "pipeline.json"
            pipeline_file.write_text(
                json.dumps(
                    {
                        "pipeline": "CLI Pipeline",
                        "stages": [
                            {"id": "scout", "lanes": ["scout"], "mode": "weighted"},
                            {
                                "id": "build",
                                "depends_on": ["scout"],
                                "lanes": ["builder"],
                                "mode": "weighted",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-matrix",
                            "--vault",
                            str(vault),
                            "--config-file",
                            str(config),
                            "--subject",
                            "cli-matrix-thread",
                            "--lanes",
                            "scout,reviewer",
                            "--json",
                        ]
                    ),
                    0,
                )
            matrix_payload = json.loads(output.getvalue())
            self.assertEqual(matrix_payload["run_count"], 6)
            self.assertTrue(Path(matrix_payload["report_path"]).exists())

            for run in matrix_payload["runs"]:
                quality = 0.95 if run["variant_id"] == "claude-primary" else 0.6
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        main(
                            [
                                "agent-outcome",
                                "--vault",
                                str(vault),
                                "--run-id",
                                run["run_id"],
                                "--status",
                                "succeeded",
                                "--metrics-json",
                                f'{{"quality": {quality}}}',
                                "--json",
                            ]
                        ),
                        0,
                    )

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-quorum",
                            "--vault",
                            str(vault),
                            "--plan-id",
                            matrix_payload["plan_id"],
                            "--min-agreement-ratio",
                            "1",
                            "--json",
                        ]
                    ),
                    0,
                )
            quorum_payload = json.loads(output.getvalue())
            self.assertEqual(quorum_payload["quorum_status"], "pass")
            self.assertTrue(Path(quorum_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-pipeline",
                            "--vault",
                            str(vault),
                            "--config-file",
                            str(config),
                            "--pipeline-file",
                            str(pipeline_file),
                            "--subject-prefix",
                            "cli-pipeline-thread",
                            "--json",
                        ]
                    ),
                    0,
                )
            pipeline_payload = json.loads(output.getvalue())
            self.assertEqual(pipeline_payload["experiment"], "cross-model-agent")
            self.assertEqual(pipeline_payload["pipeline_status"], "scheduled")
            self.assertTrue(Path(pipeline_payload["report_path"]).exists())

            for run in pipeline_payload["plans"][0]["runs"]:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        main(
                            [
                                "agent-outcome",
                                "--vault",
                                str(vault),
                                "--run-id",
                                run["run_id"],
                                "--status",
                                "succeeded",
                                "--metrics-json",
                                '{"quality": 0.8}',
                                "--json",
                            ]
                        ),
                        0,
                    )

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-pipeline-advance",
                            "--vault",
                            str(vault),
                            "--pipeline-id",
                            pipeline_payload["pipeline_id"],
                            "--json",
                        ]
                    ),
                    0,
                )
            pipeline_advance_payload = json.loads(output.getvalue())
            self.assertEqual(pipeline_advance_payload["pipeline_id"], pipeline_payload["pipeline_id"])
            self.assertEqual(pipeline_advance_payload["advance_status"], "advanced")
            self.assertTrue(Path(pipeline_advance_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-judge-panel",
                            "--vault",
                            str(vault),
                            "--config-file",
                            str(config),
                            "--plan-id",
                            matrix_payload["plan_id"],
                            "--judge-variants",
                            "claude-primary,openai-backup",
                            "--max-runs",
                            "4",
                            "--json",
                        ]
                    ),
                    0,
                )
            judge_panel_payload = json.loads(output.getvalue())
            self.assertEqual(judge_panel_payload["experiment"], "cross-model-agent")
            self.assertIn(judge_panel_payload["panel_status"], {"scheduled", "scheduled-partial"})
            self.assertTrue(Path(judge_panel_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-judge-report",
                            "--vault",
                            str(vault),
                            "--panel-id",
                            judge_panel_payload["panel_id"],
                            "--json",
                        ]
                    ),
                    0,
                )
            judge_report_payload = json.loads(output.getvalue())
            self.assertEqual(judge_report_payload["panel_id"], judge_panel_payload["panel_id"])
            self.assertIn(judge_report_payload["report_status"], {"complete", "partial", "no-outcomes"})
            self.assertTrue(Path(judge_report_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-suite",
                            "--vault",
                            str(vault),
                            "--config-file",
                            str(config),
                            "--suite-file",
                            str(suite_file),
                            "--subject-prefix",
                            "cli-suite-thread",
                            "--lanes",
                            "scout,reviewer",
                            "--json",
                        ]
                    ),
                    0,
                )
            suite_payload = json.loads(output.getvalue())
            self.assertEqual(suite_payload["case_count"], 2)
            self.assertEqual(suite_payload["run_count"], 12)
            self.assertNotIn("Private CLI suite prompt", output.getvalue())
            self.assertTrue(Path(suite_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-orchestrate",
                            "--vault",
                            str(vault),
                            "--suite-id",
                            suite_payload["suite_id"],
                            "--client-prefix",
                            "cli-orch",
                            "--max-concurrency",
                            "2",
                            "--batch-size",
                            "1",
                            "--ttl-seconds",
                            "120",
                            "--claim-strategy",
                            "lane-balanced",
                            "--json",
                        ]
                    ),
                    0,
                )
            orchestration_payload = json.loads(output.getvalue())
            self.assertEqual(orchestration_payload["summary"]["claimed_count"], 2)
            self.assertTrue(Path(orchestration_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-cycle",
                            "--vault",
                            str(vault),
                            "--suite-id",
                            suite_payload["suite_id"],
                            "--client-prefix",
                            "cli-cycle",
                            "--max-concurrency",
                            "3",
                            "--batch-size",
                            "1",
                            "--skip-recovery",
                            "--json",
                        ]
                    ),
                    0,
                )
            cycle_payload = json.loads(output.getvalue())
            self.assertEqual(cycle_payload["cycle_status"], "acted")
            self.assertTrue(Path(cycle_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-loop",
                            "--vault",
                            str(vault),
                            "--suite-id",
                            suite_payload["suite_id"],
                            "--client-prefix",
                            "cli-loop",
                            "--max-concurrency",
                            "3",
                            "--batch-size",
                            "1",
                            "--max-cycles",
                            "1",
                            "--stop-after-idle-cycles",
                            "1",
                            "--skip-recovery",
                            "--json",
                        ]
                    ),
                    0,
                )
            loop_payload = json.loads(output.getvalue())
            self.assertEqual(loop_payload["summary"]["executed_cycles"], 1)
            self.assertTrue(Path(loop_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-suite-report",
                            "--vault",
                            str(vault),
                            "--suite-id",
                            suite_payload["suite_id"],
                            "--min-completed-ratio",
                            "0",
                            "--json",
                        ]
                    ),
                    0,
                )
            suite_report_payload = json.loads(output.getvalue())
            self.assertEqual(suite_report_payload["suite_id"], suite_payload["suite_id"])
            self.assertTrue(Path(suite_report_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-plan",
                            "--vault",
                            str(vault),
                            "--config-file",
                            str(config),
                            "--subject",
                            "cli-parallel-thread",
                            "--lanes",
                            "scout,reviewer",
                            "--json",
                        ]
                    ),
                    0,
                )
            plan_payload = json.loads(output.getvalue())
            self.assertEqual(plan_payload["run_count"], 2)

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-claim",
                            "--vault",
                            str(vault),
                            "--plan-id",
                            plan_payload["plan_id"],
                            "--client-id",
                            "cli-worker",
                            "--lane",
                            "scout",
                            "--ttl-seconds",
                            "120",
                            "--claim-strategy",
                            "lane-balanced",
                            "--json",
                        ]
                    ),
                    0,
                )
            claim_payload = json.loads(output.getvalue())
            self.assertEqual(claim_payload["plan_id"], plan_payload["plan_id"])
            self.assertEqual(claim_payload["claim"]["client_id"], "cli-worker")
            self.assertEqual(claim_payload["scheduler"]["strategy"], "lane-balanced")

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-work",
                            "--vault",
                            str(vault),
                            "--claim-id",
                            claim_payload["claim_id"],
                            "--json",
                        ]
                    ),
                    0,
                )
            work_payload = json.loads(output.getvalue())
            self.assertEqual(work_payload["run_id"], claim_payload["run_id"])
            self.assertTrue(Path(work_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-heartbeat",
                            "--vault",
                            str(vault),
                            "--claim-id",
                            claim_payload["claim_id"],
                            "--client-id",
                            "cli-worker",
                            "--ttl-seconds",
                            "120",
                            "--json",
                        ]
                    ),
                    0,
                )
            heartbeat_payload = json.loads(output.getvalue())
            self.assertEqual(heartbeat_payload["claim_id"], claim_payload["claim_id"])

            for run in plan_payload["runs"]:
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        main(
                            [
                                "agent-outcome",
                                "--vault",
                                str(vault),
                                "--run-id",
                                run["run_id"],
                                "--status",
                                "succeeded",
                                "--metrics-json",
                                '{"quality": 0.95}',
                            ]
                        ),
                        0,
                    )

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-gate",
                            "--vault",
                            str(vault),
                            "--plan-id",
                            plan_payload["plan_id"],
                            "--metric-threshold",
                            "0.9",
                            "--require-lane",
                            "scout",
                            "--json",
                        ]
                    ),
                    0,
                )
            gate_payload = json.loads(output.getvalue())
            self.assertTrue(gate_payload["passed"])

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-merge",
                            "--vault",
                            str(vault),
                            "--plan-id",
                            plan_payload["plan_id"],
                            "--json",
                        ]
                    ),
                    0,
                )
            merge_payload = json.loads(output.getvalue())
            self.assertEqual(merge_payload["merge_status"], "complete")
            self.assertTrue(Path(merge_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-adjudicate",
                            "--vault",
                            str(vault),
                            "--plan-id",
                            plan_payload["plan_id"],
                            "--min-consensus-ratio",
                            "0",
                            "--json",
                        ]
                    ),
                    0,
                )
            adjudication_payload = json.loads(output.getvalue())
            self.assertTrue(adjudication_payload["accepted"])
            self.assertTrue(Path(adjudication_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-audit",
                            "--vault",
                            str(vault),
                            "--json",
                        ]
                    ),
                    0,
                )
            audit_payload = json.loads(output.getvalue())
            self.assertFalse(audit_payload["failed"])
            self.assertTrue(Path(audit_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-snapshot",
                            "--vault",
                            str(vault),
                            "--experiment",
                            "cross-model-agent",
                            "--json",
                        ]
                    ),
                    0,
                )
            snapshot_payload = json.loads(output.getvalue())
            self.assertEqual(snapshot_payload["snapshot_status"], "baseline")
            self.assertTrue(Path(snapshot_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-timeline",
                            "--vault",
                            str(vault),
                            "--limit",
                            "50",
                            "--json",
                        ]
                    ),
                    0,
                )
            timeline_payload = json.loads(output.getvalue())
            self.assertGreater(timeline_payload["summary"]["events"], 0)
            self.assertTrue(Path(timeline_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-watchdog",
                            "--vault",
                            str(vault),
                            "--stale-after-seconds",
                            "120",
                            "--json",
                        ]
                    ),
                    0,
                )
            watchdog_payload = json.loads(output.getvalue())
            self.assertTrue(Path(watchdog_payload["report_path"]).exists())

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    main(
                        [
                            "agent-status",
                            "--vault",
                            str(vault),
                            "--json",
                        ]
                    ),
                    0,
                )
            status_payload = json.loads(output.getvalue())
            self.assertEqual(status_payload["summary"]["experiments"], 1)
            self.assertTrue(Path(status_payload["report_path"]).exists())


def _subjects_by_variant(config: dict[str, object], variant_ids: set[str]) -> dict[str, str]:
    spec = ExperimentSpec.from_mapping(config)
    subjects: dict[str, str] = {}
    for index in range(1000):
        subject = f"subject-{index}"
        variant, _bucket = assign_variant(spec, subject)
        if variant.id in variant_ids and variant.id not in subjects:
            subjects[variant.id] = subject
        if set(subjects) == variant_ids:
            return subjects
    raise AssertionError(f"could not find subjects for variants: {variant_ids - set(subjects)}")


def _subjects_by_variant_count(
    config: dict[str, object],
    variant_ids: set[str],
    *,
    count: int,
) -> dict[str, list[str]]:
    spec = ExperimentSpec.from_mapping(config)
    subjects: dict[str, list[str]] = {variant_id: [] for variant_id in variant_ids}
    for index in range(5000):
        subject = f"counted-subject-{index}"
        variant, _bucket = assign_variant(spec, subject)
        if variant.id in subjects and len(subjects[variant.id]) < count:
            subjects[variant.id].append(subject)
        if all(len(items) == count for items in subjects.values()):
            return subjects
    missing = {
        variant_id: count - len(items)
        for variant_id, items in subjects.items()
        if len(items) < count
    }
    raise AssertionError(f"could not find enough subjects by variant: {missing}")


if __name__ == "__main__":
    unittest.main()
