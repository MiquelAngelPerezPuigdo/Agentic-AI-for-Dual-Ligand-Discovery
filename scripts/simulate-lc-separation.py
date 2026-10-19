#!/usr/bin/env python3
"""Assumption-driven RP-LC scenarios, not calibrated retention predictions or robot methods."""
from __future__ import annotations

import argparse
import copy
from html import escape
import itertools
import json
from pathlib import Path
from string import Template
import sys

import numpy as np
from rdkit import Chem
from rdkit.Chem import Crippen, Descriptors

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hte.io import atomic_text, digest, new_output, read_json, write_csv, write_json

SOURCES = {
    "column_format": "https://documents.thermofisher.com/TFS-Assets/CMD/brochures/TG-20762-LC-Hypersil-GOLD-TG20762-EN.pdf",
    "LSS_equation": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9543774/",
    "computed_logP": "https://www.rdkit.org/docs/source/rdkit.Chem.Crippen.html",
}
COLORS = ["#31678a", "#29856d", "#a16d30", "#995d91"]
METHOD = {
    "column": "ASSUMED C18, e.g. Hypersil GOLD Vanquish format; not confirmed HTEL column",
    "length_mm": 50, "id_mm": 2.1, "particle_um": 1.9, "temperature_C": 40,
    "mobile_phase_A": "Water + 0.1% v/v formic acid",
    "mobile_phase_B": "Acetonitrile + 0.1% v/v formic acid",
    "flow_ml_min": 0.6, "total_mobile_porosity": 0.68,
    "dwell_ml": 0.05, "postcolumn_ml": 0.01, "injection_ul": 2,
    "effective_plates": 7000, "extra_sigma_min": 0.005,
    "acquisition_min": 1.7, "tail_fraction": 0.03, "tail_tau_min": 0.02,
    "toluene_density_g_ml_assumed": 0.867,
}
GRADIENTS = {
    "broad": {"name": "5–95% B ramp", "time": [0, .10, 1.10, 1.50, 1.51, 1.70],
              "phi": [.05, .05, .95, .95, .05, .05]},
    "gentler": {"name": "5–60% B, then wash", "time": [0, .10, 1.10, 1.30, 1.50, 1.51, 1.70],
                "phi": [.05, .05, .60, .95, .95, .05, .05]},
    "strong_start": {"name": "35–95% B ramp", "time": [0, .10, 1.10, 1.50, 1.51, 1.70],
                     "phi": [.35, .35, .95, .95, .35, .35]},
}
SCENARIOS = {
    "heuristic": "Uncalibrated logP-based starting guess",
    "early_overlap": "Stress: SM and product have similar retention",
    "aromatic_overlap": "Stress: toluene and the internal standard have similar retention",
}


def dead_time(method):
    volume_ml = np.pi * (method["id_mm"] / 2) ** 2 * method["length_mm"] / 1000
    return volume_ml * method["total_mobile_porosity"] / method["flow_ml_min"]


def retention_times(method, gradient, logk40, slopes, dt=0.0005):
    """Midpoint integration of local equilibrium migration through a moving gradient.

    log10(k)=log10(k at 40% B)-S*(phi-0.40).
    x is fractional column position; gradient travels at unretained mobile velocity.
    dx/dt=1/[t0*(1+k(phi_pump(t-dwell-x*t0)))]. Detector delay is added after elution.
    """
    logk40, slopes = np.broadcast_arrays(np.asarray(logk40, float), np.asarray(slopes, float))
    if (not np.isfinite(logk40).all() or not np.isfinite(slopes).all() or (slopes <= 0).any()
            or dt <= 0 or method["flow_ml_min"] <= 0):
        raise ValueError("Finite model parameters, positive S, flow and time step are required")
    t0 = dead_time(method)
    dwell = method["dwell_ml"] / method["flow_ml_min"]
    post = method["postcolumn_ml"] / method["flow_ml_min"]
    x = np.zeros_like(logk40)
    times = np.full_like(logk40, np.nan)
    def velocity(t, position):
        phi = np.interp(t - dwell - position * t0, gradient["time"], gradient["phi"])
        k = 10 ** np.clip(logk40 - slopes * (phi - .40), -12, 12)
        return 1 / (t0 * (1 + k))
    for t in np.arange(0, method["acquisition_min"], dt):
        if np.isfinite(times).all():
            break
        h = min(dt, method["acquisition_min"] - t)
        new = x + h * velocity(t + h / 2, x + h / 2 * velocity(t, x))
        crossed = (x < 1) & (new >= 1)
        times[crossed] = t + h * (1 - x[crossed]) / (new[crossed] - x[crossed]) + post
        x = np.minimum(new, 1)
    times[times > method["acquisition_min"]] = np.nan
    return times


def widths(method, times):
    """Assumed apparent efficiency plus extra-column/injection variance; not a full band model."""
    post = method["postcolumn_ml"] / method["flow_ml_min"]
    injection_sigma = method["injection_ul"] / 1000 / method["flow_ml_min"] / np.sqrt(12)
    return np.sqrt((times - post) ** 2 / method["effective_plates"]
                   + method["extra_sigma_min"] ** 2 + injection_sigma ** 2)


def pair_resolution(times, sigma):
    return {(a, b): np.abs(times[..., a] - times[..., b]) / (2 * (sigma[..., a] + sigma[..., b]))
            for a, b in itertools.combinations(range(4), 2)}


def compounds(config):
    liquid, chemistry = config["liquids"], config["chemistry"]
    dilution = liquid["aliquot_ul"] / (liquid["aliquot_ul"] + liquid["diluent_ul"])
    extract = chemistry["reaction_volume_ul"] + liquid["workup_ul"]
    max_uM = chemistry["reaction_volume_ul"] * chemistry["substrate_molarity_M"] * 1e6 / extract * dilution
    toluene_fraction = chemistry["reaction_volume_ul"] / extract * dilution
    records = []
    entries = [("SM", chemistry["substrate"], chemistry["substrate_smiles"], max_uM / 2),
               ("Product", chemistry["product"], chemistry["product_smiles"], max_uM / 2),
               ("Toluene", "Toluene", "Cc1ccccc1", None),
               ("IS", chemistry["preloaded_internal_standard"]["identity"], chemistry["preloaded_internal_standard"]["smiles"],
                config["analytics"]["internal_standard_final_uM"])]
    for key, name, smiles, concentration in entries:
        mol = Chem.MolFromSmiles(smiles)
        logp = float(Crippen.MolLogP(mol))
        mw = float(Descriptors.MolWt(mol))
        if concentration is None:
            concentration = toluene_fraction * 1000 * METHOD["toluene_density_g_ml_assumed"] / mw * 1e6
        records.append({"id": key, "name": name, "smiles": smiles, "computed_Crippen_logP": logp,
                        "MW_g_mol": mw, "concentration_uM": concentration,
                        "assumed_log10_k40": .6 * logp - .7, "assumed_S": 4.5})
    return records, toluene_fraction


def profiles(method, times, sigma, time):
    result = []
    step = time[1] - time[0]
    tail_time = np.arange(0, 12 * method["tail_tau_min"], step)
    kernel = np.exp(-tail_time / method["tail_tau_min"])
    kernel /= kernel.sum()
    for center, width in zip(times, sigma):
        gaussian = np.exp(-.5 * ((time - center) / width) ** 2) / (width * np.sqrt(2 * np.pi))
        tailed = np.convolve(gaussian, kernel, mode="full")[:len(time)]
        result.append((1 - method["tail_fraction"]) * gaussian + method["tail_fraction"] * tailed)
    return np.asarray(result)


def run(output, config_path=ROOT / "hte_inputs/campaign.json", draws=512, seed=1707):
    if draws < 1:
        raise ValueError("At least one sensitivity draw is required")
    out = new_output(output)
    config = read_json(config_path)
    records, toluene_fraction = compounds(config)
    base = np.array([r["assumed_log10_k40"] for r in records])
    slopes = np.array([r["assumed_S"] for r in records])
    concentration = np.array([r["concentration_uM"] for r in records])
    time = np.linspace(0, METHOD["acquisition_min"], 3401)
    cases, visuals, peak_rows = [], {}, []
    for gkey, gradient in GRADIENTS.items():
        for skey, description in SCENARIOS.items():
            logk = base.copy()
            if skey == "early_overlap":
                logk[1] = logk[0] + .02
            elif skey == "aromatic_overlap":
                logk[3] = logk[2] + .04
            rt = retention_times(METHOD, gradient, logk, slopes)
            sigma = widths(METHOD, rt)
            if not np.isfinite(rt).all():
                raise ValueError("An illustrative case did not elute inside the acquisition window")
            p = profiles(METHOD, rt, sigma, time)
            gaussian_method = {**METHOD, "tail_fraction": 0}
            pure_gaussian = profiles(gaussian_method, rt, sigma, time)
            weighted = p * (concentration / concentration[3])[:, None]
            rs = pair_resolution(rt, sigma)
            minimum = min(rs, key=rs.get)
            window = abs(time - rt[3]) <= 2 * sigma[3]
            own = float(np.trapz(weighted[3, window], time[window]))
            other = float(np.trapz(weighted[:3, window].sum(axis=0), time[window]))
            tail_sensitivity = {}
            for fraction in (0, .01, .03, .1):
                changed = pure_gaussian + fraction / METHOD["tail_fraction"] * (p - pure_gaussian)
                changed *= (concentration / concentration[3])[:, None]
                own_signal = float(np.trapz(changed[3, window], time[window]))
                other_signal = float(np.trapz(changed[:3, window].sum(axis=0), time[window]))
                tail_sensitivity[str(fraction)] = other_signal / own_signal
            key = gkey + "__" + skey
            record = {"id": key, "gradient": gkey, "scenario": skey, "description": description,
                      "rt_min": rt.tolist(), "sigma_min": sigma.tolist(), "assumed_log10_k40": logk.tolist(),
                      "minimum_gaussian_Rs": float(rs[minimum]),
                      "closest_pair": records[minimum[0]]["id"] + " / " + records[minimum[1]]["id"],
                      "gaussian_Rs": {records[a]["id"] + " / " + records[b]["id"]: float(value)
                                      for (a, b), value in rs.items()},
                      "other_signal_over_IS_in_2sigma_window": other / own,
                      "tail_fraction_sensitivity_other_over_IS": tail_sensitivity,
                      "tail_and_response_assumptions_required": True}
            cases.append(record)
            visuals[key] = {"equal": np.round(p, 7).tolist(), "weighted": np.round(weighted, 7).tolist(),
                            "pure_gaussian": np.round(pure_gaussian, 7).tolist()}
            for i, compound in enumerate(records):
                peak_rows.append({"case": key, "compound": compound["id"], "retention_min": rt[i],
                                  "sigma_min": sigma[i], "assumed_log10_k40": logk[i], "assumed_S": slopes[i]})
            write_csv(out / (key + "-trace.csv"), [
                {"time_min": t, **{r["id"] + "_equal_area": p[i, j] for i, r in enumerate(records)},
                 "sum_concentration_weighted": weighted[:, j].sum()}
                for j, t in enumerate(time)])
    # A broad assumed parameter sweep is sensitivity analysis, never an empirical probability.
    rng = np.random.default_rng(seed)
    sampled_logk = base + rng.uniform(-.5, .5, (draws, 4))
    sampled_S = rng.uniform(3.5, 5.5, (draws, 4))
    sensitivity = []
    for key, gradient in GRADIENTS.items():
        rt = retention_times(METHOD, gradient, sampled_logk, sampled_S)
        rs = pair_resolution(rt, widths(METHOD, rt))
        for (a, b), values in rs.items():
            valid = np.isfinite(values)
            sensitivity.append({"gradient": key, "pair": records[a]["id"] + " / " + records[b]["id"],
                                "synthetic_draws": draws, "both_eluted": int(valid.sum()),
                                "draws_with_gaussian_Rs_below_1p5": int((values[valid] < 1.5).sum()),
                                "minimum_Rs_in_assumed_draws": float(values[valid].min()) if valid.any() else None,
                                "maximum_Rs_in_assumed_draws": float(values[valid].max()) if valid.any() else None})
    checks = numerical_checks()
    report = {"assumption_driven_only": True, "calibrated_retention_predictor": False,
              "manufacturer_software_executed": False, "physical_execution_allowed": False,
              "optimizer_feedback": False, "api_calls": 0, "seed": seed, "method": METHOD,
              "gradients": GRADIENTS, "compounds": records, "t0_min": dead_time(METHOD),
              "toluene_final_vv_fraction": toluene_fraction,
              "toluene_to_IS_molar_ratio": float(concentration[2] / concentration[3]),
              "retention_guess": "UNFITTED heuristic: log10(k at 40% B) = 0.6 * RDKit Crippen cLogP - 0.7; S=4.5. Coefficients chosen for illustration, not from measurements or a trained RT model.",
              "migration_model": "LSS equilibrium migration through a plug-flow moving gradient, including dwell and post-column delays; explicit midpoint time integration.",
              "peak_model": "Apparent N=7000 plus extra-column/injection variance; 3% exponential right-tail mixture, tau=0.02 min. No rigorous gradient-compression, saturation or strong-injection-solvent model.",
              "UV_response": "Concentration-weighted traces assume equal molar response for all four compounds. Relative units only, no wavelength-specific extinction coefficients or detector saturation model.",
              "sensitivity_assumptions": "Independent uniform +/-0.5 decades in log10(k40), S uniform 3.5–5.5. Counts are coverage of invented draws, not probabilities of real coelution.",
              "limitations": "Column, gradient, retention coefficients, efficiency, tailing and UV responses are unvalidated. No ionization/pKa model, temperature dependence, ligand/Pd matrix peaks, focusing, pressure, carryover or full injection/re-equilibration-cycle calculation. Acquisition is 1.7 min; operational throughput is not established.",
              "sources": SOURCES, "campaign_config_sha256": digest(config_path), "generator_sha256": digest(__file__),
              "cases": cases, "sensitivity": sensitivity, "numerical_checks": checks}
    write_json(out / "simulation.json", report)
    write_csv(out / "compound_assumptions.csv", records)
    write_csv(out / "simulated_retention_times.csv", peak_rows)
    write_csv(out / "sensitivity_counts.csv", sensitivity)
    render(out, report, visuals, time)
    return report


def numerical_checks():
    method = copy.deepcopy(METHOD)
    method["acquisition_min"] = 4
    isocratic = {"time": [0, 4], "phi": [.4, .4]}
    k = np.array([0.01, .2, 1, 5])
    actual = retention_times(method, isocratic, np.log10(k), np.full(4, 4.5))
    expected = dead_time(method) * (1 + k) + method["postcolumn_ml"] / method["flow_ml_min"]
    if not np.allclose(actual, expected, atol=1e-9, rtol=1e-9):
        raise AssertionError("Isocratic analytic reference disagrees with numerical migration")
    guess = np.array([-.25, .03, .5, .87])
    coarse = retention_times(METHOD, GRADIENTS["broad"], guess, 4.5)
    fine = retention_times(METHOD, GRADIENTS["broad"], guess, 4.5, dt=.00025)
    error = float(np.max(abs(coarse - fine)))
    if error > .00005:
        raise AssertionError("Gradient solver failed half-step convergence check")
    return {"isocratic_analytic_reference_pass": True,
            "gradient_half_step_max_error_min": error, "gradient_half_step_convergence_pass": True}


def render(out, report, visuals, time):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go

    records = report["compounds"]
    fig, axes = plt.subplots(3, 2, figsize=(14, 11), layout="constrained")
    panels = [(0, 0, "broad__heuristic", "equal", "Starting guess: equal areas"),
              (0, 1, "broad__heuristic", "weighted", "Same guess: concentration-weighted UV assumption"),
              (1, 0, "broad__early_overlap", "equal", "Stress case: SM / product overlap"),
              (1, 1, "broad__aromatic_overlap", "weighted", "Stress case: toluene / IS overlap")]
    for row, col, key, mode, title in panels:
        ax = axes[row, col]
        values = np.asarray(visuals[key][mode])
        ax.plot(time, values.sum(axis=0) + 1e-4, color="#333333", lw=1, label="Sum")
        for i, record in enumerate(records):
            ax.plot(time, values[i] + 1e-4, color=COLORS[i], lw=1.3, label=record["id"])
        if mode == "weighted":
            ax.set_yscale("log")
            ax.set_ylim(.01, 1e5)
        ax.set(xlim=(.2, 1.4), title=title, xlabel="Time (min)", ylabel="Relative signal (assumed)")
        ax.spines[["top", "right"]].set_visible(False)
    axes[0, 0].legend(frameon=False, ncol=5, fontsize=8)
    for key, gradient in GRADIENTS.items():
        axes[2, 0].plot(gradient["time"], np.array(gradient["phi"]) * 100, label=gradient["name"])
    axes[2, 0].set(xlabel="Pump program time (min)", ylabel="Acetonitrile (% B)", title="Assumed 1.7-minute programs")
    axes[2, 0].legend(frameon=False, fontsize=8)
    keys = ["SM / Product", "Toluene / IS"]
    x = np.arange(3)
    for i, pair in enumerate(keys):
        values = [next(c for c in report["cases"] if c["id"] == g + "__heuristic")["gaussian_Rs"][pair] for g in GRADIENTS]
        axes[2, 1].bar(x + (i - .5) * .34, values, .34, label=pair)
    axes[2, 1].axhline(1.5, color="#9d6651", ls="--", label="Rs = 1.5 reference")
    axes[2, 1].set(xticks=x, xticklabels=["5–95%", "5–60%, wash", "35–95%"],
                   ylabel="Gaussian-width Rs (assumed)", title="Starting guess only; tailing assessed separately")
    axes[2, 1].legend(frameon=False, fontsize=8)
    fig.suptitle(f"Assumed C18 separation: SM, product, toluene and {records[3]['name']}\nUncalibrated scenarios — not manufacturer predictions", fontsize=15)
    fig.savefig(out / "separation-overview.png", dpi=150)
    plt.close(fig)

    chart = go.Figure()
    chart.update_layout(height=355, margin=dict(l=65, r=15, t=30, b=45))
    plot_html = chart.to_html(full_html=False, include_plotlyjs=True, div_id="trace")
    options = "".join(f'<option value="{c["id"]}">{escape(GRADIENTS[c["gradient"]]["name"] + " — " + c["description"])}</option>' for c in report["cases"])
    assumptions = "".join(f'<tr><td>{escape(r["name"])}</td><td>{r["computed_Crippen_logP"]:.2f}</td><td>{10**r["assumed_log10_k40"]:.2f}</td><td>{r["concentration_uM"]:.1f}</td></tr>' for r in records)
    sensitivity = "".join(f'<tr><td>{escape(GRADIENTS[r["gradient"]]["name"])}</td><td>{escape(r["pair"])}</td><td>{r["draws_with_gaussian_Rs_below_1p5"]} / {r["synthetic_draws"]}</td></tr>' for r in report["sensitivity"] if r["pair"] in keys)
    payload = json.dumps({"report": report, "visuals": visuals, "time": time.tolist(), "colors": COLORS}, allow_nan=False).replace("</", "<\\/")
    links = " · ".join(f'<a href="{url}">{escape(name)}</a>' for name, url in SOURCES.items())
    html = Template("""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Assumed LC separation</title><style>body{font:15px/1.5 system-ui,sans-serif;max-width:1100px;margin:32px auto;padding:0 22px;color:#263238}
h1{font:32px Georgia,serif}h2{font-size:21px;margin-top:30px}.note{padding:12px 16px;background:#f3f1e9;border-left:3px solid #aa8541}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:8px;border-bottom:1px solid #ddd}select{font:inherit;padding:8px;max-width:100%}
code{background:#f1f3f4;padding:2px 4px}.small{font-size:13px;color:#5b686e}.tables{overflow-x:auto}</style></head><body>
<h1>Assumed LC separation</h1><p class="note"><b>Illustrative, uncalibrated simulation.</b> We assume a standard-like C18 setup and explore consequences.
Retention coefficients are invented from a transparent logP heuristic. These are not ChromSword/Thermo predictions or measured HTEL retention times.</p>
<p>50 × 2.1 mm C18, 1.9 µm; 40 °C; 0.6 mL/min; water/ACN, both 0.1% formic acid; 2 µL injection;
50 µL dwell volume; assumed t₀ = $T0 min. The 1.7-minute acquisition program does not establish a 1.7-minute injection cycle or adequate re-equilibration.</p>
<select id="case">$OPTIONS</select><p><label>Display: <select id="mode"><option value="equal">Equal areas — separation only</option>
<option value="weighted">Concentration-weighted — assumed equal molar UV response</option></select></label></p>
<p><label>Assumed tail mixture: <select id="tail"><option value="0">0% (Gaussian)</option><option value="0.01">1%</option>
<option value="0.03" selected>3%</option><option value="0.1">10%</option></select></label></p>
$CHART<div id="gradient"></div><p id="result" class="note"></p><div class="tables"><table><thead><tr><th>Compound</th><th>Simulated RT (min)</th><th>Assumed k at 40% B</th></tr></thead><tbody id="retention"></tbody></table></div>
<p class="small">Concentration-weighted traces use a logarithmic signal axis. Molar UV responses are assumed equal, not measured.
Gaussian-width Rs ignores the added tail; it is a geometric reference, not a quantitative purity guarantee.</p>
<h2>Starting assumptions</h2><table><thead><tr><th>Compound</th><th>RDKit cLogP</th><th>Assumed k₄₀</th><th>Concentration (µM)</th></tr></thead><tbody>$ASSUMPTIONS</tbody></table>
<p>The sample represents a 50% yield mixture at the configured dilution: SM/product about $ANALYTE_CONC µM each, $IS_NAME $IS_CONC µM,
toluene about $TOLUENE_CONC µM ($TOLUENE_PERCENT% v/v). This is about $RATIO toluene molecules per IS molecule.</p>
<p><code>log10(k₄₀) = 0.6 × computed cLogP − 0.7</code>, with <code>log10(k) = log10(k₄₀) − S × (fraction B − 0.40)</code> and S=4.5.
The first equation is an <b>unfitted illustrative choice</b>; cLogP alone is not a validated retention model. Neither ionization nor column selectivity is learned here.
The two stress cases deliberately bring one pair's retention coefficients together; they are possible scenarios, not predictions.</p>
<h2>Sensitivity to unknown retention</h2><p>For each gradient, $DRAWS invented parameter sets perturb each log10(k₄₀) uniformly by ±0.5 and vary S independently from 3.5 to 5.5.
The table counts simulated draws with Gaussian-width Rs below 1.5. <b>These fractions are not probabilities of real coelution.</b></p>
<table><thead><tr><th>Gradient</th><th>Pair</th><th>Synthetic draws with Rs &lt;1.5</th></tr></thead><tbody>$SENSITIVITY</tbody></table>
<h2>What the model includes</h2><p>Numerical equilibrium migration through a moving gradient, dwell and post-column delays; assumed apparent efficiency,
extra-column/injection variance, and a 3% exponential tail with 0.02-min time constant. Isocratic analytic-reference and half-step numerical-convergence checks pass.</p>
<p>No measured retention coefficients, ionization/pKa, temperature dependence, ligand/Pd matrix peaks, solvent focusing, pressure, saturation, carryover or complete
cycle/re-equilibration model is included. A large simulated toluene peak is not proof of detector overload. Signal in an IS window is not a prediction of yield bias.</p>
<p>The actual column/method and standards must replace the guesses before these traces could guide a real separation decision. This report cannot release a robot
protocol or feed yields to the optimizer; the campaign configuration is unchanged. No API calls or external modelling software were used.</p>
<p><a href="simulation.json">Assumptions and results JSON</a> · <a href="simulated_retention_times.csv">RT table</a> · <a href="sensitivity_counts.csv">Sensitivity counts</a>
· <a href="separation-overview.png">Overview image</a></p><p class="small">Sources for column format, the general LSS equation and the cLogP calculator (not the invented coefficients): $SOURCES</p>
<script id="data" type="application/json">$PAYLOAD</script><script>
const d=JSON.parse(document.getElementById('data').textContent);
function update(){const id=document.getElementById('case').value,mode=document.getElementById('mode').value;
const tail=document.getElementById('tail').value,fraction=Number(tail);
const c=d.report.cases.find(c=>c.id===id),g=d.report.gradients[c.gradient];
const v=d.visuals[id].pure_gaussian.map((row,i)=>row.map((value,j)=>Math.max(0,value+fraction/0.03*(d.visuals[id].equal[i][j]-value))*
 (mode==='weighted'?d.report.compounds[i].concentration_uM/d.report.compounds[3].concentration_uM:1)));
const sum=d.time.map((_,j)=>v.reduce((s,row)=>s+row[j],0)+1e-4);
const traces=[{x:d.time,y:sum,name:'Sum',mode:'lines',line:{color:'#333',width:1.3}}];
v.forEach((y,i)=>traces.push({x:d.time,y:y.map(y=>y+1e-4),name:d.report.compounds[i].id,mode:'lines',line:{color:d.colors[i],width:1.6}}));
Plotly.react('trace',traces,{height:355,margin:{l:65,r:20,t:35,b:45},legend:{orientation:'h',y:1.15},
xaxis:{title:{text:'Time (min)'},range:[0,1.7]},yaxis:{title:{text:'Relative signal (assumed)'},type:mode==='weighted'?'log':'linear'},template:'plotly_white'},
{responsive:true,displaylogo:false});
Plotly.react('gradient',[{x:g.time,y:g.phi.map(p=>p*100),mode:'lines',name:'Pump %B',line:{color:'#6d797e'}}],
{height:190,margin:{l:65,r:20,t:15,b:45},xaxis:{title:{text:'Pump program (min)'},range:[0,1.7]},yaxis:{title:{text:'% ACN'},range:[0,100]},template:'plotly_white'},
{responsive:true,displaylogo:false});
document.getElementById('result').textContent='Closest Gaussian-width pair: '+c.closest_pair+'; Rs = '+c.minimum_gaussian_Rs.toFixed(2)+
'. Assumed non-IS / IS signal inside ±2σ of IS: '+(100*c.tail_fraction_sensitivity_other_over_IS[tail]).toFixed(1)+'% (depends on invented UV/tail assumptions).';
document.getElementById('retention').innerHTML=d.report.compounds.map((r,i)=>'<tr><td>'+r.name+'</td><td>'+c.rt_min[i].toFixed(3)+'</td><td>'+Math.pow(10,c.assumed_log10_k40[i]).toFixed(2)+'</td></tr>').join('');}
document.getElementById('case').addEventListener('change',update);document.getElementById('mode').addEventListener('change',update);
document.getElementById('tail').addEventListener('change',update);update();
</script></body></html>""").substitute(T0=f"{report['t0_min']:.3f}", OPTIONS=options, CHART=plot_html,
                      ASSUMPTIONS=assumptions, RATIO=f"{report['toluene_to_IS_molar_ratio']:.0f}",
                      IS_NAME=escape(records[3]["name"]), IS_CONC=f"{records[3]['concentration_uM']:.1f}",
                      ANALYTE_CONC=f"{records[0]['concentration_uM']:.1f}",
                      TOLUENE_CONC=f"{records[2]['concentration_uM']:,.0f}",
                      TOLUENE_PERCENT=f"{report['toluene_final_vv_fraction']*100:.3f}",
                      DRAWS=report["sensitivity"][0]["synthetic_draws"], SENSITIVITY=sensitivity,
                      SOURCES=links, PAYLOAD=payload)
    atomic_text(out / "separation-report.html", html)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "hte_inputs/campaign.json")
    parser.add_argument("--draws", type=int, default=512)
    parser.add_argument("--seed", type=int, default=1707)
    args = parser.parse_args()
    report = run(args.output, args.config, args.draws, args.seed)
    print(json.dumps({"cases": len(report["cases"]), "sensitivity_draws_per_gradient": args.draws,
                      "calibrated_retention_predictor": False, "api_calls": 0, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
