from __future__ import annotations

import argparse
from pathlib import Path

from .io import object_digest, read_csv, read_json, write_csv, write_json
from .inventory import candidates, import_workbook, load_inventory


def main():
    parser = argparse.ArgumentParser(description="Local OT-2 catalyst HTE pipeline")
    parser.add_argument("--config", default="hte_inputs/campaign.json")
    parser.add_argument("--inventory", default="hte_inputs/ligands.csv")
    parser.add_argument("--evidence", default="hte_inputs/literature.json")
    commands = parser.add_subparsers(dest="command", required=True)
    imp = commands.add_parser("import-inventory")
    imp.add_argument("workbook")
    imp.add_argument("--output", default="hte_inputs/ligands.csv")
    commands.add_parser("check")
    s = commands.add_parser("score")
    s.add_argument("--output", required=True)
    s.add_argument("--observations")
    d = commands.add_parser("design")
    d.add_argument("--ranking", required=True)
    d.add_argument("--embeddings")
    d.add_argument("--acquisition")
    d.add_argument("--output", required=True)
    e = commands.add_parser("export")
    e.add_argument("--design", required=True)
    e.add_argument("--output", required=True)
    e.add_argument("--live", action="store_true")
    a = commands.add_parser("analyze")
    for key in ["dosing", "peaks", "ready", "calibration", "output"]:
        a.add_argument("--"+key, required=True)
    n = commands.add_parser("normalize")
    n.add_argument("input")
    n.add_argument("--output", required=True)
    ready = commands.add_parser("complete-export", help="Invoke only after every expected LC injection completed")
    for key in ("peaks", "dosing", "output"):
        ready.add_argument("--"+key, required=True)
    for command in ["iterate", "watch"]:
        w = commands.add_parser(command)
        for key in ["dosing", "calibration", "output"]:
            w.add_argument("--"+key, required=True)
        if command == "iterate":
            w.add_argument("--peaks", required=True)
            w.add_argument("--ready", required=True)
        else:
            w.add_argument("--inbox", required=True)
            w.add_argument("--once", action="store_true")
    emb = commands.add_parser("embeddings")
    emb.add_argument("--model", required=True)
    emb.add_argument("--output", required=True)
    emb.add_argument("--download", action="store_true")
    g = commands.add_parser("gollum")
    g.add_argument("--embeddings", required=True)
    g.add_argument("--priors", required=True)
    g.add_argument("--output", required=True)
    m = commands.add_parser("mocca")
    m.add_argument("--manifest", required=True)
    m.add_argument("--settings", default="hte_inputs/mocca_settings.json")
    m.add_argument("--output", required=True)
    demo = commands.add_parser("demo")
    demo.add_argument("--output", required=True)
    rehearsal = commands.add_parser("rehearse-loop", help="Offline watcher/scoring rehearsal; no API key or paid calls")
    rehearsal.add_argument("--output", required=True)
    rehearsal.add_argument("--embeddings", default="hte_inputs/pair_embeddings_t5-base.npz")
    args = parser.parse_args()
    try:
        if args.command == "import-inventory":
            import_workbook(args.workbook, args.output)
            print(args.output)
            return
        if args.command == "demo":
            from .demo import run
            print(run(args.output, args.inventory, args.config))
            return
        if args.command == "rehearse-loop":
            from .rehearsal import run
            print(run(args.output, args.inventory, args.config, args.evidence, args.embeddings))
            return
        config = read_json(args.config)
        inv = load_inventory(args.inventory)
        pairs = candidates(inv)
        if args.command == "check":
            from .planning import schedule, validate_config, required_validations
            validate_config(config)
            print({"ligands": len(inv), "pairs": len(pairs), "unresolved_identities": [k for k,v in inv.items() if v["identity_confirmed"] != "true"],
                   "missing_bench_validation": [k for k in required_validations(config) if config["validation"].get(k) is not True],
                   "schedule": schedule(config)})
        elif args.command == "score":
            from .scoring import score_candidates
            from .analytics import observations
            feedback = observations(read_csv(args.observations)) if args.observations else []
            score_candidates(config, inv, pairs, read_json(args.evidence), feedback, args.output)
            print(Path(args.output)/"ranking.csv")
            cache = read_json(Path(args.output)/"cache_summary.json")
            print(f"Prompt cache: {cache['status']}; {cache['cache_hit_requests']}/{cache['requests']} "
                  f"requests reported hits, {cache['cache_read_input_tokens']} cached read tokens")
        elif args.command == "design":
            from .design import consensus_select, make_design, pair_features
            from .adapters import load_embeddings
            if config["design"].get("require_lm_embeddings") and not args.embeddings:
                raise ValueError("This campaign requires LM embeddings; pass --embeddings")
            features = load_embeddings(args.embeddings, inv, pairs) if args.embeddings else pair_features(inv, pairs)
            ranking = read_csv(args.ranking)
            controls = config["design"]["round1_controls"]
            if controls is None:
                raise ValueError("Decide first-round reference-well allocation before design")
            acq = {r["pair_id"]: r["exploration_score"] for r in read_csv(args.acquisition)} if args.acquisition else None
            backend = "gollum_acquisition" if acq else "lm_diversity_initialization" if args.embeddings else "fingerprint_diversity_initialization"
            config["design"]["exploration_backend"] = backend
            count = config["design"]["round1_total"]-len(controls)
            selection, trace = consensus_select(pairs, ranking, features, count,
                           config["design"]["consensus_weight_llm"], config["design"]["minimum_llm_percentile"], acq)
            design = make_design(config, inv, pairs, ranking, selection, 1)
            write_csv(args.output, design)
            write_csv(str(args.output)+".selection.csv", trace)
            write_json(str(args.output)+".metadata.json", {"config_digest": object_digest(config), "backend": backend, "pairs": count})
            print(args.output)
        elif args.command == "export":
            from .protocols import export
            export(config, inv, read_csv(args.design), args.output, live=args.live)
            print(args.output)
        elif args.command == "normalize":
            from .analytics import normalize_export
            normalize_export(config, args.input, args.output)
        elif args.command == "complete-export":
            from .analytics import complete_export
            complete_export(config, args.peaks, args.dosing, args.output)
        elif args.command == "analyze":
            from .analytics import analyze, validate_completion
            validate_completion(args.ready, args.peaks, args.dosing, config)
            _, report = analyze(config, read_csv(args.dosing), read_csv(args.peaks), read_csv(args.calibration), args.output)
            print(report)
        elif args.command == "iterate":
            from .workflow import iterate
            print(iterate(config, inv, read_json(args.evidence), args.dosing, args.peaks, args.ready, args.calibration, args.output))
        elif args.command == "watch":
            from .workflow import watch
            watch(config, inv, read_json(args.evidence), args.inbox, args.dosing, args.calibration, args.output, args.once)
        elif args.command == "embeddings":
            from .adapters import build_embeddings
            build_embeddings(inv, pairs, args.model, args.output, args.download)
        elif args.command == "gollum":
            from .adapters import load_embeddings, gollum_acquisition
            gollum_acquisition(load_embeddings(args.embeddings, inv, pairs), pairs, read_csv(args.priors), args.output,
                               object_digest(config["chemistry"]), config["design"]["seed"])
        elif args.command == "mocca":
            from .adapters import process_mocca
            process_mocca(args.manifest, read_json(args.settings), args.output)
    except (ValueError, KeyError, FileNotFoundError, ImportError) as error:
        parser.exit(2, f"HTE stopped: {error}\n")


if __name__ == "__main__":
    main()
