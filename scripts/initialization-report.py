#!/usr/bin/env python3
"""Map the frozen initialization and compare cached-score previews; no API calls."""
from __future__ import annotations

import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hte.design import (consensus_select, rank_percentiles, ranked_ids,
                        round1_required_ligands, validate_design)
from hte.embeddings import load_embeddings
from hte.inventory import campaign_inventory, candidates
from hte.io import digest, new_output, read_csv, read_json, write_csv, write_json


def components(pairs, ligands):
    adjacent = {key: set() for key in ligands}
    for pair in pairs:
        a, b = pair.split("__")
        adjacent[a].add(b)
        adjacent[b].add(a)
    unseen, result = set(ligands), []
    while unseen:
        stack, group = [min(unseen)], set()
        while stack:
            key = stack.pop()
            if key in group:
                continue
            group.add(key)
            stack.extend(adjacent[key] - group)
        unseen -= group
        result.append(sorted(group))
    return sorted(result, key=lambda group: (-len(group), group))


def statistics(selected, ids, inventory, ranking, distances, trace, known):
    index = {key: i for i, key in enumerate(ids)}
    scores = {r["pair_id"]: float(r["mean_score"]) for r in ranking}
    sd = {r["pair_id"]: float(r["score_sd"]) for r in ranking}
    count = Counter(ligand for pair in selected for ligand in pair.split("__"))
    counts = np.array([count[key] for key in inventory], dtype=float)
    probabilities = counts[counts > 0] / counts.sum()
    selected_indices = [index[key] for key in selected]
    nearest = distances[:, selected_indices].min(axis=1)
    within = distances[np.ix_(selected_indices, selected_indices)].copy()
    np.fill_diagonal(within, np.inf)
    prior_types = Counter(sum(ligand in known for ligand in key.split("__")) for key in selected)
    utilities = rank_percentiles(scores)
    return {
        "pairs": len(selected), "ligands_covered": int((counts > 0).sum()),
        "missing_ligands": [key for key in inventory if not count[key]],
        "min_uses": int(counts.min()), "max_uses": int(counts.max()),
        "mean_uses": float(counts.mean()), "median_uses": float(np.median(counts)),
        "used_once": [key for key in inventory if count[key] == 1],
        "most_used": [key for key in inventory if count[key] == counts.max()],
        "usage_gini": float(np.abs(counts[:, None] - counts[None, :]).sum() /
                            (2 * len(counts) * counts.sum())),
        "normalized_usage_entropy": float(-(probabilities * np.log(probabilities)).sum() /
                                         np.log(len(counts))),
        "mean_model_score": float(np.mean([scores[key] for key in selected])),
        "minimum_model_score": min(scores[key] for key in selected),
        "maximum_model_score": max(scores[key] for key in selected),
        "median_scoring_sd": float(np.median([sd[key] for key in selected])),
        "minimum_llm_percentile": min(utilities[key] for key in selected),
        "top_score_48_overlap": len(set(selected) & {r["pair_id"] for r in ranking[:len(selected)]}),
        "mean_nearest_selected_squared_distance_all_pairs": float(nearest.mean()),
        "maximum_nearest_selected_squared_distance_all_pairs": float(nearest.max()),
        "mean_nearest_neighbor_squared_distance_within_selection": float(within.min(axis=1).mean()),
        "coverage_completed_at_step": next((int(r["selection_step"]) for r in trace
                                           if int(r["uncovered_ligands_remaining"]) == 0), None),
        "coverage_floor_overrides": sum(str(r["llm_floor_override"]).lower() == "true" for r in trace),
        "network_components": components(selected, inventory),
        "prior_categories": {"both_reported": prior_types[2], "one_reported": prior_types[1],
                             "neither_reported": prior_types[0]},
        "ligand_uses": {key: int(count[key]) for key in inventory},
    }


def prepare(args):
    config = read_json(args.config)
    inventory = campaign_inventory(args.inventory, config, confirmed=True)
    design = read_csv(args.design)
    validate_design(config, inventory, design)
    if {row["kind"] for row in design} != {"pair"}:
        raise ValueError("This initialization review expects a pair-only first batch")
    library = candidates(inventory)
    ids = [row["pair_id"] for row in library]
    ranking = read_csv(args.ranking)
    order = ranked_ids(ranking, library)
    ranking = sorted(ranking, key=lambda row: order.index(row["pair_id"]))
    if any(int(row["scoring_calls"]) != config["llm"]["repeats"] for row in ranking):
        raise ValueError("Saved ranking repeat counts differ from the campaign")
    features = load_embeddings(args.embeddings, inventory, library).astype(float)
    centered = features - features.mean(axis=0)
    u, singular, vt = np.linalg.svd(centered, full_matrices=False)
    coordinates = u[:, :2] * singular[:2]
    for axis in range(2):
        if vt[axis, np.abs(vt[axis]).argmax()] < 0:
            coordinates[:, axis] *= -1
    variance = singular[:2] ** 2 / (singular ** 2).sum()
    norms = (features ** 2).sum(axis=1)
    distances = np.maximum(norms[:, None] + norms[None, :] - 2 * features @ features.T, 0)
    np.fill_diagonal(distances, 0)
    evidence = read_json(args.evidence)
    known = set()
    for row in evidence["yields"]:
        if row["ligand_id"] in inventory:
            if row["cas"] != inventory[row["ligand_id"]]["cas"]:
                raise ValueError("SI ligand ID/CAS mismatch")
            known.add(row["ligand_id"])
    count = len(design)
    required = round1_required_ligands(config, inventory)
    actual, trace = consensus_select(library, ranking, features, count,
        config["design"]["consensus_weight_llm"], config["design"]["minimum_llm_percentile"],
        required_ligands=required)
    if set(actual) != {row["pair_id"] for row in design}:
        raise ValueError("Frozen batch differs from the current selector/configuration")
    methods = [{"key": "frozen", "name": "Frozen batch: 50% LLM / 50% diversity",
                "weight": config["design"]["consensus_weight_llm"], "selected": actual, "trace": trace}]
    for weight in (0.25, 0.75, 1.0):
        selection, steps = consensus_select(library, ranking, features, count, weight,
            config["design"]["minimum_llm_percentile"], required_ligands=required)
        methods.append({"key": f"llm{int(weight*100)}",
                        "name": f"Preview: {int(weight*100)}% LLM, coverage enforced",
                        "weight": weight, "selected": selection, "trace": steps})
    methods.append({"key": "top_scores", "name": "Diagnostic: top 48 scores, no coverage rule",
                    "weight": None, "selected": order[:count], "trace": []})
    for method in methods:
        method["statistics"] = statistics(method["selected"], ids, inventory, ranking,
                                           distances, method["trace"], known)
    sources = {name: digest(getattr(args, name)) for name in
               ("config", "inventory", "design", "ranking", "embeddings", "evidence")}
    data = {"sources_sha256": sources, "no_api_calls": True, "frozen_design_modified": False,
            "candidate_pairs": len(ids), "available_ligands": len(inventory),
            "hard_minimum_uses": 1, "pca_explained_variance_ratio": variance.tolist(),
            "embedding_metric": "squared Euclidean distance in all 768 raw T5 dimensions",
            "mean_library_model_score": float(np.mean([float(r["mean_score"]) for r in ranking])),
            "known_single_ligand_priors": len(known),
            "methods": [{k: v for k, v in method.items() if k != "trace"} for method in methods]}
    return data, inventory, design, ranking, ids, coordinates, variance, methods


def positions(inventory):
    angles = np.linspace(np.pi / 2, np.pi / 2 - 2 * np.pi, len(inventory), endpoint=False)
    return {key: np.array([np.cos(a), np.sin(a)]) for key, a in zip(inventory, angles)}


def static_map(output, inventory, ids, coordinates, variance, method, sources):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    matplotlib.rcParams.update({"svg.fonttype": "none", "svg.hashsalt": sources["design"],
                                 "font.size": 10})
    selected = method["selected"]
    s = method["statistics"]
    index = {key: i for i, key in enumerate(ids)}
    chosen = [index[key] for key in selected]
    fig = plt.figure(figsize=(19, 11.5), layout="constrained")
    grid = fig.add_gridspec(2, 2, width_ratios=(1.25, 1), wspace=0.18, hspace=0.14)
    ax = fig.add_subplot(grid[0, 0])
    ax.scatter(*coordinates.T, s=13, c="#d5dce2", label="All 435 pairs", rasterized=False)
    ax.scatter(*coordinates[chosen].T, s=42, c="#166b96", edgecolor="white", linewidth=0.4,
               label="Selected 48")
    ax.set(xlabel=f"PC1 ({variance[0]:.1%} variance)", ylabel=f"PC2 ({variance[1]:.1%} variance)",
           title="Pair embedding map — projection of the full T5 space")
    ax.legend(frameon=False, loc="best", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    graph = fig.add_subplot(grid[1, 0])
    xy = positions(inventory)
    edges = [[xy[a], xy[b]] for a, b in (key.split("__") for key in selected)]
    graph.add_collection(LineCollection(edges, colors="#a6b3be", linewidths=0.85, alpha=0.75))
    points = np.array(list(xy.values()))
    graph.scatter(*points.T, s=110, color="#166b96", zorder=3)
    for key, point in xy.items():
        graph.text(*(point * 1.14), key, ha="center", va="center", fontsize=9)
    graph.set(xlim=(-1.28, 1.28), ylim=(-1.28, 1.28), aspect="equal",
              title="Ligand pairing network — each edge is one experiment")
    graph.axis("off")
    bars = fig.add_subplot(grid[:, 1])
    names = [f"{key}  {row['name']}" for key, row in inventory.items()]
    counts = list(s["ligand_uses"].values())
    bars.barh(range(len(names)), counts, color="#166b96", height=0.7)
    bars.set_yticks(range(len(names)), names, fontsize=9)
    bars.invert_yaxis()
    bars.set(xlabel="Pair experiments containing the ligand", xlim=(0, max(counts)+1),
             title="All 30 ligands are covered; frequencies are unequal")
    bars.axvline(1, color="#b05c29", linewidth=1, linestyle="--", label="Required minimum = 1")
    for i, value in enumerate(counts):
        bars.text(value+0.12, i, str(value), va="center", fontsize=9)
    bars.spines[["top", "right"]].set_visible(False)
    bars.legend(frameon=False, loc="lower right", fontsize=9)
    fig.suptitle(f"Frozen initialization: 48 pairs · 30/30 ligands · use counts 1–7 · "
                 f"11.0% of pair space", fontsize=17)
    fig.supxlabel(f"PCA displays {variance.sum():.1%} of embedding variance. Network uses a circular layout. "
                  "No experimental pair yields are available.", fontsize=10)
    metadata = {"Title": "Frozen ligand initialization", "Description": "Design SHA256 "+sources["design"],
                "Date": None}
    svg = output/"initialization-map.svg"
    fig.savefig(svg, metadata=metadata)
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines())+"\n")
    fig.savefig(output/"initialization-map.png", dpi=180)
    plt.close(fig)


def comparison_rows(methods):
    rows = []
    for method in methods:
        s = method["statistics"]
        rows.append({"method": method["name"], "all_ligands_covered": not s["missing_ligands"],
                     "ligands_covered": s["ligands_covered"], "minimum_uses": s["min_uses"],
                     "maximum_uses": s["max_uses"], "mean_model_score": s["mean_model_score"],
                     "mean_nearest_squared_distance": s["mean_nearest_selected_squared_distance_all_pairs"],
                     "usage_gini": s["usage_gini"], "same_pairs_as_frozen": len(
                         set(method["selected"]) & set(methods[0]["selected"]))})
    return rows


def interactive_report(output, inventory, design, ranking, ids, coordinates, variance, methods, data):
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    index = {key: i for i, key in enumerate(ids)}
    ranked = {row["pair_id"]: row for row in ranking}
    actual = {row["pair_id"]: row for row in design}
    xy = positions(inventory)
    fig = make_subplots(rows=2, cols=2, specs=[[{}, {"rowspan": 2}], [{}, None]],
                        column_widths=[0.58, 0.42], horizontal_spacing=0.23, vertical_spacing=0.22,
                        subplot_titles=("Pair embedding map", "Ligand use counts", "Tested ligand pairs"))
    fig.add_trace(go.Scatter(x=coordinates[:, 0], y=coordinates[:, 1], mode="markers",
        marker={"size": 5, "color": "#d5dce2"}, text=ids, name="All 435 pairs",
        hovertemplate="%{text}<extra>Library pair</extra>"), row=1, col=1)
    groups = []
    for method in methods:
        selected = method["selected"]
        s = method["statistics"]
        group = []
        chosen = [index[key] for key in selected]
        custom = []
        for key in selected:
            a, b = key.split("__")
            frozen = actual.get(key, {})
            custom.append([key, inventory[a]["name"], inventory[b]["name"],
                           float(ranked[key]["mean_score"]), float(ranked[key]["score_sd"]),
                           frozen.get("well", "Unassigned"), frozen.get("sample_id", "Preview only")])
        group.append(len(fig.data))
        fig.add_trace(go.Scatter(x=coordinates[chosen, 0], y=coordinates[chosen, 1], mode="markers",
            marker={"size": 9, "color": [r[3] for r in custom], "coloraxis": "coloraxis",
                    "line": {"width": 0.5, "color": "white"}}, name="Selected pairs", customdata=custom,
            hovertemplate=("%{customdata[0]}<br>%{customdata[1]} + %{customdata[2]}"
                "<br>Mean score %{customdata[3]:.1f}; scoring SD %{customdata[4]:.1f}"
                "<br>Frozen assignment: %{customdata[6]} / %{customdata[5]}<extra></extra>")),
            row=1, col=1)
        ex, ey = [], []
        for key in selected:
            a, b = key.split("__")
            ex.extend([xy[a][0], xy[b][0], None]); ey.extend([xy[a][1], xy[b][1], None])
        group.append(len(fig.data))
        fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line={"color": "#a6b3be", "width": 1},
                                hoverinfo="skip", showlegend=False), row=2, col=1)
        group.append(len(fig.data))
        points = np.array(list(xy.values()))
        fig.add_trace(go.Scatter(x=points[:, 0], y=points[:, 1], mode="markers",
            customdata=[[key, row["name"], s["ligand_uses"][key]] for key, row in inventory.items()],
            marker={"size": 11, "color": ["#166b96" if s["ligand_uses"][key] else "#e3e7eb"
                                         for key in inventory]}, showlegend=False,
            hovertemplate="%{customdata[0]} %{customdata[1]}<br>Uses: %{customdata[2]}<extra></extra>"),
            row=2, col=1)
        group.append(len(fig.data))
        fig.add_trace(go.Scatter(x=points[:, 0]*1.14, y=points[:, 1]*1.14, mode="text",
            text=list(inventory), textposition="middle center", textfont={"size": 10},
            hoverinfo="skip", showlegend=False), row=2, col=1)
        group.append(len(fig.data))
        labels = [key+" "+(row["name"] if len(row["name"]) < 25 else row["name"][:22]+"…")
                  for key, row in inventory.items()]
        values = list(s["ligand_uses"].values())
        fig.add_trace(go.Bar(x=values, y=labels, orientation="h", text=values, textposition="outside",
            marker_color="#166b96", showlegend=False,
            customdata=[[key, row["name"]] for key, row in inventory.items()],
            hovertemplate="%{customdata[0]} %{customdata[1]}<br>Pair experiments: %{x}<extra></extra>"),
            row=1, col=2)
        groups.append(group)
    def visibility(i):
        return [True]+[j in groups[i] for j in range(1, len(fig.data))]
    def heading(method):
        s = method["statistics"]
        return (method["name"]+f"<br><sup>{s['ligands_covered']}/30 ligands; uses "
                f"{s['min_uses']}–{s['max_uses']}; mean model score {s['mean_model_score']:.2f}"
                +(" · COVERAGE RULE FAILED" if s["missing_ligands"] else "")+"</sup>")
    for i, trace in enumerate(fig.data):
        trace.visible = visibility(0)[i]
    fig.update_layout(template="plotly_white", height=1120,
        title={"text": heading(methods[0]), "y": 0.97, "yanchor": "top"},
        margin={"l": 60, "r": 35, "t": 220, "b": 55}, font={"size": 12},
        coloraxis={"colorscale": "Viridis", "cmin": 0, "cmax": 100,
                   "colorbar": {"orientation": "h", "x": 0.22, "y": 0.47, "len": 0.42,
                                "thickness": 10, "title": "Mean Claude score (ranking units)"}},
        legend={"orientation": "h", "y": 1.06, "x": 0},
        updatemenus=[{"buttons": [{"label": m["name"], "method": "update",
                                  "args": [{"visible": visibility(i)},
                                           {"title.text": heading(m)}]}
                                 for i, m in enumerate(methods)],
                      "x": 0, "y": 1.14, "xanchor": "left", "yanchor": "top"}])
    fig.update_xaxes(title_text=f"PC1 ({variance[0]:.1%})", row=1, col=1)
    fig.update_yaxes(title_text=f"PC2 ({variance[1]:.1%})", row=1, col=1)
    maximum = max(m["statistics"]["max_uses"] for m in methods)
    fig.update_xaxes(title_text="Pair experiments", range=[0, maximum+1], dtick=1, row=1, col=2)
    fig.update_yaxes(autorange="reversed", tickfont={"size": 11}, row=1, col=2)
    fig.update_xaxes(visible=False, range=[-1.25, 1.25], row=2, col=1)
    fig.update_yaxes(visible=False, range=[-1.25, 1.25], scaleanchor="x3", scaleratio=1, row=2, col=1)
    plot = fig.to_html(full_html=False, include_plotlyjs=True,
                       config={"displaylogo": False, "responsive": True})
    s = methods[0]["statistics"]
    rows = "".join("<tr>"+f"<td>{escape(r['method'])}</td><td>{r['ligands_covered']}/30</td>"
        f"<td>{r['minimum_uses']}–{r['maximum_uses']}</td><td>{r['mean_model_score']:.2f}</td>"
        f"<td>{r['mean_nearest_squared_distance']:.4f}</td><td>{r['usage_gini']:.3f}</td>"
        f"<td>{r['same_pairs_as_frozen']}/48</td></tr>" for r in comparison_rows(methods))
    assignments = "".join("<tr>"+"".join(f"<td>{escape(str(v))}</td>" for v in
        [r["sample_id"], r["well"], r["pair_id"], inventory[r["ligand_a"]]["name"],
         inventory[r["ligand_b"]]["name"], f"{float(ranked[r['pair_id']]['mean_score']):.1f}"])+"</tr>"
        for r in design)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Ligand initialization review</title>
<style>body{{font:16px system-ui,sans-serif;color:#18384d;background:#fff;margin:24px auto;padding:0 20px;max-width:1450px}}
h1,h2{{font-weight:600}}p{{line-height:1.5;max-width:1100px}}table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{padding:9px 10px;border-bottom:1px solid #d8e1e8;text-align:left}}th{{background:#f1f5f8}}
.table-wrap{{overflow-x:auto}}.note{{color:#425563}}code{{font-size:13px}}summary{{cursor:pointer;font-weight:600;padding:16px 0}}</style>
</head><body><h1>Ligand initialization review</h1>
<p><b>Frozen batch:</b> 48 unique pairs cover all 30 available ligands. Uses range from 1 to 7;
five ligands appear once and three appear seven times. Mean use is 3.2 experiments per ligand.
The minimum-once rule is satisfied; frequencies are not balanced.</p>
<p class="note">Choose a cached-score preview below. Previews do not modify the real batch.
The top-score-only diagnostic deliberately omits the coverage rule.
Scores are model ranking values, not measured yields. PCA retains {variance.sum():.1%} of embedding variance;
all distance statistics use the full 768 dimensions. Network positions are circular, not chemical coordinates.</p>
{plot}<h2>Comparison using the same saved Claude scores</h2><div class="table-wrap"><table><thead><tr>
<th>Method</th><th>Ligands</th><th>Uses</th><th>Mean score</th><th>Mean nearest squared distance</th>
<th>Usage Gini</th><th>Shared with frozen</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="note">The distance column averages, over all 435 library pairs, squared distance to the closest
selected pair in raw T5 space; smaller values indicate broader representation coverage.
Gini is 0 for equal ligand use and increases with imbalance. Neither statistic measures chemical performance.
All weighted previews retain minimum-once coverage and the existing LLM percentile floor.</p>
<details><summary>Frozen 48-well assignments (unchanged by preview selection)</summary>
<div class="table-wrap"><table><thead><tr><th>Sample</th><th>Reaction well</th><th>Pair</th>
<th>Ligand A</th><th>Ligand B</th><th>Mean score</th></tr></thead><tbody>{assignments}</tbody></table></div></details>
<p class="note">Single-use ligands: {", ".join(s["used_once"])}. Most used: {", ".join(s["most_used"])}.
Initial coverage was completed at selection step {s["coverage_completed_at_step"]}; floor overrides: {s["coverage_floor_overrides"]}.
No paid calls or experimental results were generated.</p>
<details><summary>Source integrity</summary><pre>{escape(json.dumps(data["sources_sha256"], indent=2))}</pre></details>
</body></html>"""
    (output/"initialization-review.html").write_text(html)


def markdown_report(data, inventory, methods):
    s = methods[0]["statistics"]
    variance = sum(data["pca_explained_variance_ratio"])
    lines = ["# Initial ligand-selection review", "",
        "**The minimum-once constraint is enabled and passed: all 30 available ligands occur in "
        "the 48 first-round pair experiments.** L07 is excluded because it is unavailable.", "",
        "![Frozen initialization: embedding map, pair network and ligand frequencies](initialization-map.svg)", "",
        "## Frozen-batch statistics", "",
        "| Measure | Value |", "|---|---:|",
        "| Unique pair experiments | 48 /435 (11.0%) |", "| Ligands covered | 30 /30 |",
        "| Uses per ligand | 1–7; mean 3.2; median 2.5 |",
        f"| Mean Claude score, selected /whole library | {s['mean_model_score']:.2f} /{data['mean_library_model_score']:.2f} |",
        f"| Median repeat-scoring SD, selected | {s['median_scoring_sd']:.2f} score units |",
        f"| Overlap with the unconstrained top 48 scores | {s['top_score_48_overlap']} /48 |",
        f"| All-ligand coverage completed | Selection step {s['coverage_completed_at_step']} |",
        f"| LLM-floor overrides | {s['coverage_floor_overrides']} |",
        f"| Pairing-network components | {len(s['network_components'])} |",
        f"| Ligand-usage Gini (0 = equal use) | {s['usage_gini']:.3f} |", "",
        "Five ligands appear only once: "+", ".join(f"**{key} {inventory[key]['name']}**" for key in s["used_once"])+".",
        "Three appear seven times: "+", ".join(f"**{key} {inventory[key]['name']}**" for key in s["most_used"])+".", "",
        f"The PCA map retains **{variance:.1%}** of embedding variance. Points are pairs, not individual ligands; "
        "the network displays the individual ligand IDs and tested pairings. Two-dimensional visual separation "
        "is an approximation. Diversity statistics below use all 768 raw T5 dimensions.", "",
        "## Weight previews from the same paid scores", "",
        "| Method | Ligands covered | Uses | Mean score | Mean nearest squared distance | Usage Gini | Shared pairs |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for r in comparison_rows(methods):
        lines.append(f"| {r['method']} | {r['ligands_covered']}/30 | {r['minimum_uses']}–{r['maximum_uses']} | "
            f"{r['mean_model_score']:.2f} | {r['mean_nearest_squared_distance']:.4f} | "
            f"{r['usage_gini']:.3f} | {r['same_pairs_as_frozen']}/48 |")
    lines += ["", "Lower mean nearest squared distance indicates broader embedding coverage: average squared "
        "distance from every library pair to its nearest selected pair. Mean scores quantify Claude's relative "
        "ranking, not expected experimental yield. Weighted previews all retain the existing coverage rule "
        "and LLM floor. The top-score-only diagnostic omits coverage deliberately.", "",
        "## Interpreting possible refinement", "",
        "Minimum-once coverage ensures inclusion, not balanced sampling. We can compare score/diversity "
        "weights with the existing cached scores; enforcing a larger minimum or maximum ligand frequency "
        "would be a separate selector change. No preview here changes the frozen batch, well assignments "
        "or stock plan. Experimental performance can only be assessed after measured yields.", "",
        "Generate the self-contained interactive report and machine-readable statistics locally:", "",
        "    python -m pip install -e '.[reports]'",
        "    python scripts/initialization-report.py --output output/initialization-review", "",
        "Open output/initialization-review/initialization-review.html. The folder also contains SVG/PNG, "
        "statistics.json, comparison.csv and ligand_counts.csv. No API key or paid calls are needed.", "",
        "[ML strategy](ml-strategy.md) · "
        "[Exact frozen ligand coverage](../campaigns/hackathon2026/round1_design.csv.ligand_coverage.csv)", "",
        "Design SHA-256: "+data["sources_sha256"]["design"], ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="hte_inputs/campaign.json")
    parser.add_argument("--inventory", default="hte_inputs/ligands.csv")
    parser.add_argument("--evidence", default="hte_inputs/literature.json")
    parser.add_argument("--design", default="campaigns/hackathon2026/round1_design.csv")
    parser.add_argument("--ranking", default="campaigns/hackathon2026/scoring/ranking.csv")
    parser.add_argument("--embeddings", default="hte_inputs/pair_embeddings_t5-base.npz")
    parser.add_argument("--output", required=True)
    parser.add_argument("--publish-docs", action="store_true", help="Refresh the compact versioned overview")
    args = parser.parse_args()
    data, inventory, design, ranking, ids, coords, variance, methods = prepare(args)
    output = new_output(args.output)
    write_json(output/"statistics.json", data)
    write_csv(output/"comparison.csv", comparison_rows(methods))
    write_csv(output/"ligand_counts.csv", [{"ligand_id": key, "name": row["name"],
        "uses": methods[0]["statistics"]["ligand_uses"][key]} for key, row in inventory.items()])
    static_map(output, inventory, ids, coords, variance, methods[0], data["sources_sha256"])
    interactive_report(output, inventory, design, ranking, ids, coords, variance, methods, data)
    (output/"initialization-review.md").write_text(markdown_report(data, inventory, methods))
    if args.publish_docs:
        for name in ("initialization-map.svg", "initialization-review.md"):
            shutil.copy2(output/name, ROOT/"docs"/name)
    print(json.dumps({"report": str(output/"initialization-review.html"), "paid_calls": 0,
                      "frozen_batch_modified": False, "covered_ligands": methods[0]["statistics"]["ligands_covered"],
                      "pca_variance_retained": float(variance.sum())}))


if __name__ == "__main__":
    main()
