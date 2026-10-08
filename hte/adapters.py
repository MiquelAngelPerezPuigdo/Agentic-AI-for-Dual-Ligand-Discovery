from __future__ import annotations

from pathlib import Path
import numpy as np

from .io import finite, object_digest, read_csv, write_csv, write_json


GOLLUM_COMMIT = "c418d7ed3c17e5995f503f6df7c26e9f7c58d09f"


def build_embeddings(inventory, candidates, model_path, output, download=False):
    import torch
    from transformers import AutoTokenizer, T5EncoderModel
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=not download)
    encoder = T5EncoderModel.from_pretrained(model_path, local_files_only=not download).eval()
    texts = []
    for c in candidates:
        a, b = inventory[c["ligand_a"]], inventory[c["ligand_b"]]
        def text(x, y):
            return f"Pd desulfonylative fluorination in toluene at 95 C. Ligand 1 {x['name']} {x['smiles']} 6 mol%. Ligand 2 {y['name']} {y['smiles']} 6 mol%. Pd 12 mol%. Substrate pyridine-2-sulfonyl fluoride 0.1 M."
        texts.extend([text(a, b), text(b, a)])
    vectors = []
    for start in range(0, len(texts), 8):
        tokens = tokenizer(texts[start:start+8], return_tensors="pt", padding=True, truncation=False)
        if tokens.input_ids.shape[1] > 512:
            raise ValueError("Embedding text exceeds 512 tokens; shorten the explicit template without truncating ligands")
        with torch.no_grad():
            hidden = encoder(**tokens).last_hidden_state
            mask = tokens.attention_mask.unsqueeze(-1)
            pooled = (hidden*mask).sum(1)/mask.sum(1)
        vectors.extend(pooled.numpy())
        if start % 80 == 0:
            print(f"Embedding ordered pair texts: {start+len(pooled)}/{len(texts)}", flush=True)
    # Order-invariant representation: mean of text embeddings for BOTH ligand orders.
    x = np.asarray(vectors).reshape(len(candidates), 2, -1).mean(axis=1)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, pair_ids=np.asarray([c["pair_id"] for c in candidates]), features=x,
                        inventory_digest=np.asarray(object_digest(inventory)), model=np.asarray(str(model_path)),
                        model_revision=np.asarray(str(getattr(encoder.config, "_commit_hash", None))))
    write_json(str(output)+".metadata.json", {"model": str(model_path), "revision": getattr(encoder.config, "_commit_hash", None),
                "pairs": len(candidates), "dimensions": x.shape[1], "inventory_digest": object_digest(inventory),
                "method": "mean masked token pooling; mean of both ligand orders; frozen T5 encoder",
                "template_conditions": "PyFluor 0.1 M, toluene, 95 C, 6+6 mol% ligands, 12 mol% Pd"})


def load_embeddings(path, inventory, candidates):
    with np.load(path, allow_pickle=False) as saved:
        if str(saved["inventory_digest"]) != object_digest(inventory):
            raise ValueError("Embedding inventory digest mismatch; rebuild after structure changes")
        if list(saved["pair_ids"]) != [c["pair_id"] for c in candidates]:
            raise ValueError("Embedding candidate order mismatch")
        x = saved["features"].copy()
    if x.ndim != 2 or not np.isfinite(x).all():
        raise ValueError("Invalid embeddings")
    return x


def gollum_acquisition(features, candidates, observations, output, conditions_digest, seed=42):
    """Actual upstream BotorchOptimizer, with an explicit local projected-embedding GP adapter."""
    import torch
    from .vendor.gollum_optimizer import BotorchOptimizer
    torch.manual_seed(seed)
    np.random.seed(seed)
    ids = [c["pair_id"] for c in candidates]
    seen = {}
    for row in observations:
        if row.get("kind", "pair") != "pair" or row.get("qc_pass") not in (True, "True"):
            continue
        if row.get("yield_percent") in (None, ""):
            continue  # Censored bounds need a censored model; never fit them as zero.
        if row.get("conditions_digest") != conditions_digest:
            raise ValueError("GoLLuM prior conditions differ from this campaign. Published 150 C single-ligand yields cannot train this pair model.")
        key = row["pair_id"]
        if key not in ids or key in seen:
            raise ValueError("Prior pair IDs must be unique and in the candidate library")
        seen[key] = finite(row["yield_percent"], "measured prior yield", 0, 105)
    if len(seen) < 3:
        raise ValueError("A trained GoLLuM acquisition requires at least three valid same-condition pair measurements; use diversity initialization for a cold start")
    x = torch.as_tensor(features, dtype=torch.float64)
    training = [ids.index(key) for key in seen]
    y = torch.tensor([[seen[ids[i]]] for i in training], dtype=torch.float64)
    optimizer = BotorchOptimizer(surrogate_model_config={"class_path": "hte.gollum_surrogate.ProjectedGP",
                                                        "init_args": {"seed": seed}},
                                acq_function_config={"class_path": "botorch.acquisition.analytic.UpperConfidenceBound",
                                                     "init_args": {"beta": 2.0, "maximize": True}}, batch_size=1)
    optimizer.train_surrogate_model(x[training], y)
    from .vendor.gollum_config import instantiate_class
    acquisition = instantiate_class(optimizer.acq_function_config,
                                   **optimizer.update_acquisition_function_params(y))
    with torch.no_grad():
        values = acquisition(x.unsqueeze(-2)).flatten().numpy()
    if not np.isfinite(values).all():
        raise ValueError("GoLLuM acquisition returned nonfinite values")
    write_csv(output, [{"pair_id": key, "exploration_score": float(value)} for key, value in zip(ids, values)])
    write_json(str(output)+".metadata.json", {"upstream_commit": GOLLUM_COMMIT, "valid_measured_priors": len(seen),
               "variant": "Upstream GoLLuM optimizer; GP-trained projection over frozen, symmetric LM embeddings",
               "language_model_weights_finetuned": False})


def process_mocca(manifest_path, settings, output):
    """HPLC-DAD raw data only. Process standards with the same settings for calibration."""
    from mocca2 import Chromatogram
    from .io import read_json
    manifest = read_json(manifest_path)
    base = Path(manifest_path).resolve().parent
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    import re
    for sample in manifest["samples"]:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,80}", sample["sample_id"]):
            raise ValueError("Raw-data sample IDs must be safe single filenames")
        raw_path = (base/sample["raw_path"]).resolve()
        chromatogram = Chromatogram(str(raw_path))
        chromatogram.correct_baseline(method=settings["baseline_model"])
        chromatogram.extract_time(settings["minimum_time_min"], settings["maximum_time_min"], inplace=True)
        chromatogram.extract_wavelength(settings["minimum_wavelength_nm"], settings["maximum_wavelength_nm"], inplace=True)
        chromatogram.find_peaks(min_height=settings["minimum_peak_height"], min_rel_height=settings["minimum_relative_height"])
        chromatogram.deconvolve_peaks(model="FraserSuzuki", min_r2=settings["minimum_deconvolution_r2"],
                                     relaxe_concs=False, max_comps=settings["max_components"])
        index, actual_wavelength = chromatogram.closest_wavelength(settings["quantification_wavelength_nm"])
        if abs(actual_wavelength-settings["quantification_wavelength_nm"]) > 1:
            raise ValueError("Requested DAD quantification wavelength is not present in raw data")
        for peak in chromatogram.peaks:
            for component in getattr(peak, "components", []):
                # Physical integral corrects MOCCA's sample-count sum for the actual time grid.
                times = chromatogram.time[peak.left:peak.left+len(component.concentration)]
                area = float(np.trapz(component.concentration*component.spectrum[index], times))
                rows.append({"sample_id": sample["sample_id"], "retention_time_min": float(chromatogram.time[component.elution_time]),
                             "area": area, "channel": f"MOCCA_DAD_{actual_wavelength:g}nm", "method_id": manifest["method_id"],
                             "qc_flag": "ok" if peak.resolved else "unresolved_deconvolution"})
        write_json(output/(sample["sample_id"]+".chromatogram.json"), chromatogram.to_dict())
    write_csv(output/"peaks.csv", rows, ["sample_id", "retention_time_min", "area", "channel", "method_id", "qc_flag"])
