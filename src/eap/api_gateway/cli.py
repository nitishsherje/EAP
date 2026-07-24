"""EAP command-line interface.

Commands:
    demo                 Register example contracts and run the auditor agent.
    catalog              List registered resources.
    resolve <ref>        Resolve a reference and print the ResolvedDefinition summary.
    run-agent <ref|file> Resolve and run an agent (file is parsed for its ref).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from eap.api_gateway.assembly import build_app_with_examples
from eap.specifications.envelope import ResourceKind
from eap.specifications.loader import load_file


def _print_result(result) -> None:  # noqa: ANN001
    print(f"\n=== Run {result.run_id} [{result.status}] ===")
    if result.error:
        print(f"error: {result.error}")
        return
    print(f"\ncontent:\n{result.content}\n")
    if result.output.get("structured"):
        print(f"structured: {result.output['structured']}")
    if result.citations:
        print(f"citations: {result.citations}")
    if result.tool_calls:
        print("tool calls:")
        for tc in result.tool_calls:
            print(f"  - {tc.capability}.{tc.operation} ok={tc.ok}")
    print(f"tokens: prompt={result.prompt_tokens} completion={result.completion_tokens}")
    if result.used_fallback:
        print("(model fallback was used)")


def _cmd_demo(_args: argparse.Namespace) -> int:
    app = build_app_with_examples()
    print("Registered example contracts. Running auditor-report-agent...\n")
    result = app.run_agent(
        "agent://auditor-report-agent/1.0.0",
        query="Analyze the auditor report and flag issues.",
        inputs={"document_id": "RPT-2026-042"},
    )
    _print_result(result)
    print(
        f"\nFinOps: total tokens={app.token_tracker.total_tokens()} "
        f"cost=${app.token_tracker.total_cost()}"
    )
    return 0


def _cmd_catalog(_args: argparse.Namespace) -> int:
    app = build_app_with_examples()
    print(f"{'KIND':<20}{'NAME':<28}{'VERSION':<10}{'STATUS':<12}DOMAIN")
    for entry in app.control_plane.catalog.list():
        print(
            f"{entry.kind:<20}{entry.name:<28}{entry.version:<10}{entry.status:<12}{entry.domain}"
        )
    return 0


def _cmd_resolve(args: argparse.Namespace) -> int:
    app = build_app_with_examples()
    rd = app.resolve(args.ref)
    print(f"target: {rd.target}")
    print(f"environment: {rd.environment}")
    print(f"hash: {rd.content_hash}")
    print(f"integrity ok: {rd.verify_integrity()}")
    print(f"agents: {list(rd.bundle.agents)}")
    print(f"skills: {list(rd.bundle.skills)}")
    print(f"capabilities: {list(rd.bundle.capabilities)}")
    print(f"knowledge: {list(rd.bundle.knowledge)}")
    print(f"models: {list(rd.bundle.models)}")
    print(f"bindings: {list(rd.bundle.bindings)}")
    print(f"effective policy: {rd.effective_policy.model_dump()}")
    return 0


def _cmd_run_agent(args: argparse.Namespace) -> int:
    app = build_app_with_examples()
    ref = args.target
    candidate = Path(ref)
    if candidate.exists():
        resources = load_file(candidate)
        agent = next((r for r in resources if r.kind == ResourceKind.AGENT), None)
        if agent is None:
            print(f"no Agent resource found in {ref}", file=sys.stderr)
            return 2
        ref = str(agent.ref)
    result = app.run_agent(ref, query=args.query, inputs={"document_id": args.document_id})
    _print_result(result)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eap", description="EAP control CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="run the end-to-end walking skeleton")
    sub.add_parser("catalog", help="list registered resources")

    p_resolve = sub.add_parser("resolve", help="resolve a reference")
    p_resolve.add_argument("ref")

    p_run = sub.add_parser("run-agent", help="resolve and run an agent")
    p_run.add_argument("target", help="agent:// reference or a YAML file path")
    p_run.add_argument("--query", default="Analyze the auditor report and flag issues.")
    p_run.add_argument("--document-id", default="RPT-2026-042")

    args = parser.parse_args(argv)
    handlers = {
        "demo": _cmd_demo,
        "catalog": _cmd_catalog,
        "resolve": _cmd_resolve,
        "run-agent": _cmd_run_agent,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
