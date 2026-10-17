#!/usr/bin/env python3
"""Generate illustrative LC traces and HTEL-format peak tables; replay the real analyzer.

No raw-trace integrator or Chromeleon instance is invoked. Synthetic integration
decisions are imposed explicitly, including two deliberately invisible area biases.
"""
from __future__ import annotations

import argparse
import copy
from html import escape
import json
from pathlib import Path
from string import Template
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hte.analytics import analyze, calibration_from_peaks, normalize_export, observations
from hte.analytical_practice import prepare, verify
from hte.demo import synthetic_config
from hte.io import atomic_text, digest, new_output, read_csv, read_json, write_csv, write_json

HEADERS = ["inj_no", "injection_name", "type", "vial_position", "inj_volume(uL)",
           "channel_for_peak_detection", "number_of_det_peaks", "peak_no", "retention_time(min)",
           "area_uvvis1(AU*min)", "area_uvvis2(AU*min)", "area_uvvis3(AU*min)",
           "area_uvvis4(AU*min)", "area_tic(counts*min)"]
COLORS = {"substrate": "#31678a", "product": "#29856d", "internal_standard": "#9d6a37",
          "impurity": "#9962a2", "interferent": "#ba5366"}
# Pass expectations are declared before generating or observing any results.
CASES = [
    ("clean", "Clean 50% mixture", True, True, "Normal peaks; small simulated response noise."),
    ("low_yield", "10% product", True, True, "Low-product mixture, still above the mock LOQ."),
    ("high_yield", "90% product", True, True, "High-product mixture inside the calibration range."),
    ("rt_inside", "Small RT drift", True, True, "Product moves +0.025 min, inside its ±0.05-min window."),
    ("injection_scale", "20% less injected signal", True, True, "Every peak area falls 20%; mesitylene normalization should compensate."),
    ("extra_impurity", "Resolved extra impurity", True, True, "A large peak outside all reference windows must not become product."),
    ("rt_outside", "Product outside RT window", False, False, "Product moves +0.08 min; strict reaction QC must reject it."),
    ("split_product", "Two candidate product peaks", False, False, "Two resolved peaks lie inside the product window; assignment is ambiguous."),
    ("missing_is", "Missing mesitylene", False, False, "The internal-standard peak is absent."),
    ("is_outlier", "Mesitylene area outlier", False, False, "Only the mesitylene peak loses 50% area."),
    ("truncated_export", "Incomplete peak export", False, False, "The export declares four detected peaks but contains three."),
    ("missing_area", "Missing selected UV area", False, False, "A detected product peak has n.a. in the selected detector column."),
    ("coelution_bias", "Hidden product coelution", True, False, "An unresolved interferent adds 18% to product area; area-only QC can miss it."),
    ("integration_loss", "20% product integration loss", True, False, "A plausible single product peak has 20% of its area omitted from the export."),
]


def sample(config, key, sm, product, rng):
    """Independent forward response model, not the analyzer's inverse calibration."""
    is_area = 0.03 * rng.uniform(0.97, 1.03)
    refs = config["analytics"]["references"]
    components = []
    for name, concentration, factor in (("substrate", sm, 0.0012), ("product", product, 0.0009)):
        if concentration > 0:
            components.append({"name": name, "rt": refs[name]["retention_time_min"],
                               "area": concentration * factor * is_area * rng.normal(1, 0.003),
                               "sigma": 0.012})
    components.append({"name": "internal_standard", "rt": refs["internal_standard"]["retention_time_min"],
                       "area": is_area, "sigma": 0.012})
    return {"sample_id": key, "components": components, "peaks": copy.deepcopy(components)}


def export_vendor(config, samples, output, mapping):
    """Exact example headers, peak-major padding, repeated names and ignored channels."""
    rows = []
    ordered = [sorted(s["peaks"], key=lambda p: p["rt"]) for s in samples]
    for peak_index in range(max(len(s["peaks"]) for s in samples)):
        for inj, s in enumerate(samples, 1):
            row = dict(zip(HEADERS, ["n.a."] * len(HEADERS)))
            row.update(inj_no=inj, injection_name="MOCK_SM_PRODUCT_IS", type="Unknown",
                       vial_position=f"B:A{inj}", channel_for_peak_detection="UV_VIS_1",
                       number_of_det_peaks=s.get("reported_count", len(s["peaks"])))
            row["inj_volume(uL)"] = 5  # Example-format metadata, not an injection recommendation.
            if peak_index < len(ordered[inj - 1]):
                p = ordered[inj - 1][peak_index]
                area = p["area"]
                row.update(peak_no=peak_index + 1)
                row["retention_time(min)"] = p["rt"]
                row["area_uvvis1(AU*min)"] = area
                # Assumed alternate responses; no summing across wavelengths or TIC.
                row["area_uvvis2(AU*min)"] = float(area) * 2.3 if area != "n.a." else 999
                row["area_uvvis3(AU*min)"] = float(area) * 0.065 if area != "n.a." else 777
                row["area_tic(counts*min)"] = 1234567
            rows.append(row)
    write_csv(output, rows, HEADERS)
    write_csv(mapping, [{"inj_no": i, "sample_id": s["sample_id"],
                         "method_id": config["analytics"]["method_id"]} for i, s in enumerate(samples, 1)])


def absence(config, sample_id, name):
    return {"sample_id": sample_id, "analyte": name, "method_id": config["analytics"]["method_id"],
            "reviewed_by": "SYNTHETIC_FIXTURE_ONLY",
            "note": "Known absent in simulation; no human/experimental review is claimed."}


def dose(config, key):
    return {"sample_id": key, "round": 0, "well": "", "kind": "analytical_pilot", "pair_id": "",
            "ligand_a": "", "ligand_b": "", "reaction_volume_ul": config["chemistry"]["reaction_volume_ul"],
            "workup_ul": config["liquids"]["workup_ul"], "aliquot_ul": config["liquids"]["aliquot_ul"],
            "diluent_ul": config["liquids"]["diluent_ul"],
            "substrate_umol": config["chemistry"]["reaction_volume_ul"] * config["chemistry"]["substrate_molarity_M"],
            "internal_standard_final_uM": config["analytics"]["internal_standard_final_uM"]}


def perturb(key, target):
    product = next(p for p in target["peaks"] if p["name"] == "product")
    physical_product = next(p for p in target["components"] if p["name"] == "product")
    if key in ("rt_inside", "rt_outside"):
        shift = 0.025 if key == "rt_inside" else 0.08
        product["rt"] += shift
        physical_product["rt"] += shift
    elif key == "injection_scale":
        for collection in (target["peaks"], target["components"]):
            for p in collection:
                p["area"] *= 0.8
    elif key == "extra_impurity":
        impurity = {"name": "impurity", "rt": 1.18, "area": 0.045, "sigma": 0.016}
        target["components"].append(impurity)
        target["peaks"].append(copy.deepcopy(impurity))
    elif key == "split_product":
        for collection in (target["peaks"], target["components"]):
            p = next(p for p in collection if p["name"] == "product")
            collection.remove(p)
            collection.extend([{**p, "rt": 0.88, "area": p["area"] * 0.6, "sigma": 0.004},
                               {**p, "rt": 0.92, "area": p["area"] * 0.4, "sigma": 0.004}])
    elif key == "missing_is":
        for field in ("peaks", "components"):
            target[field] = [p for p in target[field] if p["name"] != "internal_standard"]
    elif key == "is_outlier":
        for collection in (target["peaks"], target["components"]):
            next(p for p in collection if p["name"] == "internal_standard")["area"] *= 0.5
    elif key == "truncated_export":
        target["reported_count"] = 4
    elif key == "missing_area":
        product["area"] = "n.a."
    elif key == "coelution_bias":
        interferent = {**physical_product, "name": "interferent", "rt": physical_product["rt"] + 0.004,
                       "area": physical_product["area"] * 0.18}
        target["components"].append(interferent)
        product["rt"] = (product["rt"] + 0.18 * interferent["rt"]) / 1.18
        product["area"] *= 1.18
    elif key == "integration_loss":
        product["area"] *= 0.8


def trace(sample_row, rng):
    time = np.linspace(0, 1.7, 1701)
    baseline = 0.005 + 0.003 * time / 1.7
    signal = baseline + rng.normal(0, 0.0004, len(time))
    components = []
    integrals = []
    for p in sample_row["components"]:
        def gaussian(center, sigma):
            return np.exp(-0.5 * ((time - center) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))
        values = p["area"] * (0.88 * gaussian(p["rt"], p["sigma"])
                              + 0.12 * gaussian(p["rt"] + 0.018, p["sigma"] * 1.8))
        numerical_area = float(np.trapz(values, time))
        if not np.isclose(numerical_area, p["area"], rtol=1e-6, atol=1e-12):
            raise ValueError("Synthetic trace is truncated or its area disagrees with the forward model")
        integrals.append({"name": p["name"], "imposed_area_AU_min": p["area"],
                          "numerical_area_AU_min": numerical_area})
        signal += values
        components.append({"name": p["name"], "y": np.round(values + baseline, 7).tolist()})
    return {"time": time.tolist(), "signal": np.round(signal, 7).tolist(),
            "baseline": np.round(baseline, 7).tolist(), "components": components,
            "exported_peaks": sample_row["peaks"], "area_verification": integrals}


def run(output, config_path=ROOT / "hte_inputs/campaign.json", example=None, seed=1707, render=True):
    out = new_output(output)
    config = synthetic_config(config_path)
    config["analytics"]["missing_analyte_policy"] = "reject"
    provenance = {"inspiration": "Wide integrated multi-UV peak-table format",
                  "source_contains_raw_traces": False, "historical_retention_times_reused": False}
    if example:
        rows = read_csv(example)
        if list(rows[0]) != HEADERS:
            raise ValueError("The example no longer matches the expected HTEL export schema")
        provenance.update(file=Path(example).name, sha256=digest(example), rows=len(rows))
    write_json(out / "SYNTHETIC_ONLY.json", {"synthetic_only": True, "api_calls": 0,
               "physical_execution_allowed": False, "optimizer_feedback": False})
    write_json(out / "campaign.json", config)
    plan = prepare(config, out)
    cal_plan_path = ROOT / "hte_inputs/calibration_template.csv"
    cal_plan = read_csv(cal_plan_path)
    rng = np.random.default_rng(seed)
    cal_folder = out / "calibration"
    cal_folder.mkdir()
    cal_samples, cal_absences = [], []
    for row in cal_plan:
        concentrations = {"substrate": 0, "product": 0}
        concentrations[row["analyte"]] = float(row["concentration_uM"])
        cal_samples.append(sample(config, row["sample_id"], concentrations["substrate"], concentrations["product"], rng))
        if float(row["concentration_uM"]) == 0:
            cal_absences.append(absence(config, row["sample_id"], row["analyte"]))
    export_vendor(config, cal_samples, cal_folder / "vendor.csv", cal_folder / "map.csv")
    write_csv(cal_folder / "reviewed-absences.csv", cal_absences)
    normalize_export(config, cal_folder / "vendor.csv", cal_folder / "peaks.csv", cal_folder / "map.csv")
    calibration_from_peaks(config, cal_folder / "peaks.csv", cal_plan_path, cal_folder / "calibration.csv",
                           cal_folder / "reviewed-absences.csv")
    calibration = read_csv(cal_folder / "calibration.csv")
    base = [sample(config, r["sample_id"], r["substrate_uM"], r["product_uM"], rng) for r in plan]
    absences = [absence(config, r["sample_id"], name) for r in plan for name in ("substrate", "product")
                if r[name + "_uM"] == 0]
    write_csv(out / "reviewed-absences.csv", absences)
    cases, visualizations = [], {}
    for key, title, expected_qc, expected_truth, description in CASES:
        folder = out / key
        folder.mkdir()
        truth = copy.deepcopy(plan)
        samples = copy.deepcopy(base)
        if key in ("low_yield", "high_yield"):
            fraction = 0.1 if key == "low_yield" else 0.9
            maximum = truth[2]["substrate_uM"] + truth[2]["product_uM"]
            truth[2].update(substrate_uM=maximum * (1 - fraction), product_uM=maximum * fraction)
            samples[2] = sample(config, truth[2]["sample_id"], truth[2]["substrate_uM"], truth[2]["product_uM"], rng)
        perturb(key, samples[2])
        write_csv(folder / "truth.csv", truth)
        export_vendor(config, samples, folder / "vendor.csv", folder / "map.csv")
        visual = trace(samples[2], np.random.default_rng(seed + len(cases)))
        visualizations[key] = visual
        write_csv(folder / "trace.csv", [{"time_min": t, "signal_AU": s, "baseline_AU": b}
                  for t, s, b in zip(visual["time"], visual["signal"], visual["baseline"])])
        write_json(folder / "trace_truth.json", {"components": samples[2]["components"],
                   "exported_peaks": samples[2]["peaks"], "area_verification": visual["area_verification"]})
        # Truth never goes into normalize/analyze. It is used only by the separate pilot audit.
        record = {"scenario": key, "title": title, "description": description,
                  "true_yield_percent": float(truth[2]["product_uM"]) / (
                      float(truth[2]["substrate_uM"]) + float(truth[2]["product_uM"])) * 100,
                  "expected_unknown_sample_qc_pass": expected_qc, "expected_known_mixture_pass": expected_truth}
        try:
            normalize_export(config, folder / "vendor.csv", folder / "peaks.csv", folder / "map.csv")
            # Compare the strict reaction policy on nonzero-analyte samples with known-truth pilot audit.
            keys = {r["sample_id"] for r in truth if r["substrate_uM"] > 0 and r["product_uM"] > 0}
            peaks = [r for r in read_csv(folder / "peaks.csv") if r["sample_id"] in keys]
            results, qc = analyze(config, [dose(config, r["sample_id"]) for r in truth if r["sample_id"] in keys],
                                  peaks, calibration, folder / "unknown-sample-analysis")
            target = next(r for r in results if r["sample_id"] == truth[2]["sample_id"])
            sanitized = next(r for r in observations(results) if r["sample_id"] == truth[2]["sample_id"])
            pilot = read_json(verify(config, [folder / "vendor.csv"], [folder / "map.csv"],
                cal_folder / "calibration.csv", folder / "truth.csv", folder / "known-mixture-replay",
                out / "reviewed-absences.csv"))
            record.update(import_pass=True, unknown_sample_qc_pass=qc["batch_qc_pass"],
                          known_mixture_pass=pilot["pilot_pass"], reported_yield_percent=target["yield_percent"],
                          usable_yield_percent=sanitized["yield_percent"], qc_flags=target["qc_flags"])
            if not qc["batch_qc_pass"] and any(r["yield_percent"] is not None for r in observations([target])):
                raise AssertionError("A rejected target retained a numeric feedback yield")
        except ValueError as error:
            # This one fixture deliberately has an invalid selected area; unexpected exceptions fail the run.
            if key != "missing_area" or "missing RT/number/selected-channel area" not in str(error):
                raise
            record.update(import_pass=False, unknown_sample_qc_pass=False, known_mixture_pass=False,
                          reported_yield_percent=None, usable_yield_percent=None, qc_flags=str(error))
        matched = (record["unknown_sample_qc_pass"] == expected_qc
                   and record["known_mixture_pass"] == expected_truth)
        record["matches_declared_expectation"] = matched
        record["outcome"] = ("Blocked" if not record["unknown_sample_qc_pass"] else
                             "Accepted" if record["known_mixture_pass"] else "Hidden bias")
        write_json(folder / "trial_report.json", record)
        cases.append(record)
    report = {"synthetic_only": True, "seed": seed, "api_calls": 0, "optimizer_feedback": False,
              "physical_execution_allowed": False, "real_method_validated": False,
              "raw_trace_integration_executed": False, "chromeleon_executed": False,
              "provenance": provenance, "generator_sha256": digest(__file__), "config_source_sha256": digest(config_path),
              "calibration_plan_sha256": digest(cal_plan_path), "calibration_injections": len(cal_samples),
              "pilot_injections_per_trial": len(plan), "trials": cases,
              "all_expected_outcomes_passed": all(r["matches_declared_expectation"] for r in cases),
              "trace_model": "Assumed Gaussian/tailing peaks, linear baseline and seeded additive noise. Areas numerically checked.",
              "scope": "Real importer, authentic-standard calibration logic, IS normalization, strict reaction QC and separate known-mixture audit. Exported integration decisions are simulated, not calculated from traces by Chromeleon.",
              "limitations": "RTs, peak widths, response factors, noise, LOQs and UV ratios are fictional. The historical example provides export format only. Known-mixture failure detects the two imposed biases, not every possible coelution or recovery error."}
    write_json(out / "trial_report.json", report)
    write_csv(out / "trial_summary.csv", cases)
    if render:
        render_report(out, report, visualizations, config)
    if not report["all_expected_outcomes_passed"]:
        raise AssertionError("Mock responses differed from the expectations declared in CASES; inspect trial_report.json")
    return report


def render_report(out, report, visuals, config):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go

    cases = report["trials"]
    palette = {"Accepted": "#29856d", "Blocked": "#9b6351", "Hidden bias": "#af6b19"}
    fig, ax = plt.subplots(figsize=(11, 8.2), layout="constrained")
    for i, r in enumerate(cases):
        ax.scatter(r["true_yield_percent"], i, marker="|", s=220, color="#abb0b3", linewidths=2,
                   label="Known truth" if i == 0 else None)
        if r["usable_yield_percent"] is not None:
            ax.plot([r["true_yield_percent"], r["usable_yield_percent"]], [i, i], color=palette[r["outcome"]])
            ax.scatter(r["usable_yield_percent"], i, s=40, color=palette[r["outcome"]])
            text = f"{r['usable_yield_percent']:.1f}%"
            ax.text(max(r["true_yield_percent"], r["usable_yield_percent"]) + 2, i, text, va="center", fontsize=9)
        else:
            ax.text(2, i, "REJECTED", va="center", color=palette["Blocked"], fontsize=9)
    ax.set(yticks=range(len(cases)), yticklabels=[r["title"] for r in cases], xlim=(-2, 105),
           xlabel="Product yield (%) — synthetic truth and usable reported result",
           title="Mock HTEL exports through the actual analytical pipeline")
    ax.invert_yaxis()
    ax.grid(axis="x", color="#e9e9e9")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    fig.savefig(out / "trial-results.png", dpi=160)
    plt.close(fig)

    chart = go.Figure()
    chart.update_layout(template="plotly_white", height=430, margin=dict(l=65, r=20, t=35, b=50),
                        xaxis_title="Retention time (min)", yaxis_title="Simulated signal (AU)",
                        xaxis=dict(range=[0, 1.7]), legend=dict(orientation="h", y=1.15))
    chart_html = chart.to_html(full_html=False, include_plotlyjs=True, div_id="chromatogram")
    rows = []
    for r in cases:
        measured = f"{r['usable_yield_percent']:.1f}%" if r["usable_yield_percent"] is not None else "—"
        rows.append(f"<tr><td>{escape(r['title'])}</td><td>{r['true_yield_percent']:.0f}%</td>"
                    f"<td>{measured}</td><td>{'Pass' if r['unknown_sample_qc_pass'] else 'Reject'}</td>"
                    f"<td>{'Pass' if r['known_mixture_pass'] else 'Fail'}</td>"
                    f"<td class='{r['outcome'].lower().replace(' ', '-')}'>{r['outcome']}</td></tr>")
    options = "".join(f"<option value='{r['scenario']}'>{escape(r['title'])}</option>" for r in cases)
    payload = json.dumps({"visuals": visuals, "cases": cases, "colors": COLORS,
                          "refs": config["analytics"]["references"]}, allow_nan=False).replace("</", "<\\/")
    html = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Mock HPLC trials</title>
<style>body{font:15px/1.5 system-ui,sans-serif;color:#243238;max-width:1100px;margin:36px auto;padding:0 22px}
h1{font:34px Georgia,serif;margin-bottom:4px}h2{font-size:20px;margin-top:30px}p{max-width:950px}
.note{background:#f2f4f4;padding:14px 18px;border-left:3px solid #587380}.small{font-size:13px;color:#58656b}
select{font:inherit;padding:9px;max-width:100%}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid #dce2e4}th{font-weight:600}
.accepted{color:#20715d}.blocked{color:#8b503f}.hidden-bias{color:#9b5e11;font-weight:600}
code{background:#f1f3f4;padding:2px 4px}.tablewrap{overflow-x:auto}</style></head><body>
<h1>Mock HPLC trials</h1><p class="small">HTEL-format exports · real pipeline replay · synthetic concentrations</p>
<p class="note"><b>$CHECKS responses matched the declared expectations.</b> $ACCEPTED valid cases passed;
$BLOCKED faults were blocked; $HIDDEN hidden area biases passed unknown-sample QC but failed the known-mixture check.
No API calls, robot execution or real LC acquisition.</p>
<h2>Inspect a chromatogram</h2><select id="scenario">$OPTIONS</select><p id="description"></p>
$CHART<p id="response" class="note"></p>
<p class="small">Solid black: simulated measured trace. Dotted colors: known simulated components above baseline.
Diamonds: peaks in the mock integrated export (hover for area). Shaded bands: fictional reference RT windows.
Traces illustrate the imposed export decisions; the pipeline reads peak areas, not these traces.</p>
<h2>Pipeline responses</h2><div class="tablewrap"><table><thead><tr><th>Trial</th><th>Truth</th><th>Usable yield</th>
<th>Unknown-sample QC</th><th>Known-mixture check</th><th>Outcome</th></tr></thead><tbody>$ROWS</tbody></table></div>
<h2>What was exercised</h2><p>Fourteen simulated authentic-standard injections establish separate substrate/product
calibrations, including independent check levels. Each trial replays seven pilot injections through the real
Chromeleon-format importer, calibration, mesitylene normalization and concentration/yield calculations. Strict
reaction QC is evaluated on mixtures with both analytes above the mock LOQ. The separate pilot audit checks known
concentrations, including reviewed absent-analyte fixtures. Rejected numeric results are removed from feedback;
no optimizer is called here.</p>
<p><b>Hidden bias is a limitation, not a successful unknown-sample analysis.</b> The coelution case reports approximately
59% from a true 50% mixture. Lost product area reports approximately 40%. Both appear plausible in an area table.
Known pilot concentrations reveal these imposed errors; unknown reaction samples do not carry that truth.</p>
<h2>How the example was used</h2><p>The supplied historical CSV provides the 14-column, peak-major export layout,
repeated injection names, padding and nonselected detector fields. It contains no raw time–intensity trace.
These 1.7-minute RTs, response factors, widths, tailing, baseline and noise are invented; historical RTs and
wavelength assignments are not reused as method settings. Trace component areas are numerically checked against
their imposed areas. The example does not establish a real 1.7-minute separation.</p>
<p>No Chromeleon or MOCCA processing was executed. Integration errors and merged peaks are explicitly simulated
in the exported tables. Real acquisition, peak integration, separation and detector behavior remain outside this
offline test.</p><p class="small">Reproducible seed: $SEED. Machine-readable results: <a href="trial_report.json">JSON</a>
and <a href="trial_summary.csv">CSV</a>. Each trial folder contains the mock export, mapping, illustrative trace,
separate truth and pipeline outputs. All files are marked synthetic.</p>
<script id="trial-data" type="application/json">$PAYLOAD</script><script>
const payload=JSON.parse(document.getElementById('trial-data').textContent);
function showTrial(){
 const key=document.getElementById('scenario').value;
 const v=payload.visuals[key], r=payload.cases.find(c=>c.scenario===key);
 const data=[{x:v.time,y:v.signal,name:'Simulated trace',mode:'lines',line:{color:'#263238',width:1.7}}];
 v.components.forEach(c=>data.push({x:v.time,y:c.y,name:c.name.replaceAll('_',' '),mode:'lines',
   line:{color:payload.colors[c.name]||'#888',width:1.4,dash:'dot'}}));
 data.push({x:v.exported_peaks.map(p=>p.rt),y:v.exported_peaks.map(p=>v.signal[Math.round(p.rt*1000)]),
   mode:'markers',name:'Exported peaks',marker:{symbol:'diamond-open',size:10,color:'#263238'},
   text:v.exported_peaks.map(p=>p.name+': exported area '+(p.area==='n.a.'?'MISSING':Number(p.area).toPrecision(4))+' AU·min'),
   hovertemplate:'%{text}<extra></extra>'});
 const shapes=Object.entries(payload.refs).map(([name,ref])=>({type:'rect',xref:'x',yref:'paper',
   x0:ref.retention_time_min-ref.window_min,x1:ref.retention_time_min+ref.window_min,y0:0,y1:1,
   fillcolor:payload.colors[name],opacity:0.06,line:{width:0},layer:'below'}));
 const layout={template:'plotly_white',height:430,margin:{l:65,r:20,t:45,b:50},
   xaxis:{title:{text:'Retention time (min)'},range:[0,1.7]},yaxis:{title:{text:'Simulated signal (AU)'}},
   legend:{orientation:'h',y:1.15},shapes:shapes};
 Plotly.react('chromatogram',data,layout,{responsive:true,displaylogo:false});
 document.getElementById('description').textContent=r.description;
 const measured=r.usable_yield_percent==null?'no usable numeric yield':r.usable_yield_percent.toFixed(1)+'% usable yield';
 document.getElementById('response').textContent='Truth '+r.true_yield_percent.toFixed(0)+'% → '+measured+
   '. Unknown-sample QC: '+(r.unknown_sample_qc_pass?'PASS':'REJECT')+
   '. Known-mixture check: '+(r.known_mixture_pass?'PASS':'FAIL')+(r.qc_flags?'. Flags: '+r.qc_flags:'');
}
document.getElementById('scenario').addEventListener('change',showTrial);showTrial();
</script></body></html>"""
    html = Template(html).substitute(
        OPTIONS=options, CHART=chart_html, ROWS="".join(rows), PAYLOAD=payload, SEED=str(report["seed"]),
        CHECKS=f"{sum(r['matches_declared_expectation'] for r in cases)} of {len(cases)}",
        ACCEPTED=sum(r["outcome"] == "Accepted" for r in cases),
        BLOCKED=sum(r["outcome"] == "Blocked" for r in cases),
        HIDDEN=sum(r["outcome"] == "Hidden bias" for r in cases))
    atomic_text(out / "mock-hplc-report.html", html)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "hte_inputs/campaign.json")
    parser.add_argument("--example", type=Path, help="Optional original HTEL CSV: record hash and verify schema")
    parser.add_argument("--seed", type=int, default=1707)
    parser.add_argument("--no-report", action="store_true", help="Skip optional matplotlib/plotly reports")
    args = parser.parse_args()
    report = run(args.output, args.config, args.example, args.seed, not args.no_report)
    print(json.dumps({"trials": len(report["trials"]), "all_expected_outcomes_passed": report["all_expected_outcomes_passed"],
                      "api_calls": 0, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
