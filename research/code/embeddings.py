from __future__ import annotations

import json
from pathlib import Path
import numpy as np

from .io import digest, finite, object_digest, write_json


# This archive predates condition metadata inside the NPZ. Only its exact bytes
# may use the documented legacy profile; an arbitrary legacy file is not trusted.
LEGACY_ARCHIVE_SHA256 = "22d626dea637cb4aaf43fd56c94b05ecf602ba1a3272af675c20cc760d4a0caa"
LEGACY_CONDITIONS = {
    "substrate": "pyridine-2-sulfonyl fluoride",
    "substrate_smiles": "FS(C1=NC=CC=C1)(=O)=O",
    "solvent": "toluene", "temperature_C": 95.0, "substrate_molarity_M": 0.1,
    "ligand_a_mol_percent": 6.0, "ligand_b_mol_percent": 6.0, "pd_mol_percent": 12.0,
}


def embedding_conditions(config=None):
    """Capture the chemistry represented by the fixed desulfonylation template.

    Time, atmosphere, scale and precursor identity are not encoded by this
    template. Matching embeddings does not establish that a Claude ranking is
    appropriate after changes to those other conditions.
    """
    if config is None:
        return dict(LEGACY_CONDITIONS)
    chemistry = config["chemistry"]
    result = {key: finite(chemistry[key], key, 0) for key in
              ("temperature_C", "substrate_molarity_M", "ligand_a_mol_percent",
               "ligand_b_mol_percent", "pd_mol_percent")}
    result.update(substrate=str(chemistry["substrate"]).split(" /", 1)[0].strip(),
                  substrate_smiles=str(chemistry["substrate_smiles"]).strip(),
                  solvent=str(config["liquids"]["substrate_stock_solvent"]).strip())
    if not result["substrate"] or not result["substrate_smiles"] or not result["solvent"]:
        raise ValueError("Embedding conditions require substrate identity and solvent")
    if result["ligand_a_mol_percent"] != result["ligand_b_mol_percent"]:
        raise ValueError("Unordered-pair embeddings require equal ligand A/B loadings")
    return result


def pair_text(first, second, conditions):
    """Keep the current campaign's exact archived wording while parameterizing it."""
    c = conditions
    return (f"Pd desulfonylative fluorination in {c['solvent']} at {c['temperature_C']:g} C. "
            f"Ligand 1 {first['name']} {first['smiles']} {c['ligand_a_mol_percent']:g} mol%. "
            f"Ligand 2 {second['name']} {second['smiles']} {c['ligand_b_mol_percent']:g} mol%. "
            f"Pd {c['pd_mol_percent']:g} mol%. Substrate {c['substrate']} {c['substrate_molarity_M']:g} M.")


def build_embeddings(inventory, candidates, model_path, output, download=False, config=None):
    conditions = embedding_conditions(config)
    import torch
    from transformers import AutoTokenizer, T5EncoderModel
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=not download)
    encoder = T5EncoderModel.from_pretrained(model_path, local_files_only=not download).eval()
    texts = []
    for c in candidates:
        a, b = inventory[c["ligand_a"]], inventory[c["ligand_b"]]
        texts.extend([pair_text(a, b, conditions), pair_text(b, a, conditions)])
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
                        model_revision=np.asarray(str(getattr(encoder.config, "_commit_hash", None))),
                        template_conditions_json=np.asarray(json.dumps(conditions, sort_keys=True, allow_nan=False)))
    write_json(str(output)+".metadata.json", {"model": str(model_path), "revision": getattr(encoder.config, "_commit_hash", None),
                "pairs": len(candidates), "dimensions": x.shape[1], "inventory_digest": object_digest(inventory),
                "method": "mean masked token pooling; mean of both ligand orders; frozen T5 encoder",
                "template_conditions": conditions})


def load_embeddings(path, inventory, candidates, config=None):
    with np.load(path, allow_pickle=False) as saved:
        if str(saved["inventory_digest"]) != object_digest(inventory):
            raise ValueError("Embedding inventory digest mismatch; rebuild after structure changes")
        if list(saved["pair_ids"]) != [c["pair_id"] for c in candidates]:
            raise ValueError("Embedding candidate order mismatch")
        if config is not None:
            expected = embedding_conditions(config)
            if "template_conditions_json" in saved:
                actual = json.loads(str(saved["template_conditions_json"]))
            elif digest(path) == LEGACY_ARCHIVE_SHA256:
                actual = LEGACY_CONDITIONS
            else:
                raise ValueError("Embedding file has no verified condition provenance; rebuild for this campaign")
            if actual != expected:
                raise ValueError("Embedding conditions differ from the campaign; rebuild embeddings and review the Claude ranking")
        x = saved["features"].copy()
    if x.ndim != 2 or len(x) != len(candidates) or not x.shape[1] or not np.isfinite(x).all():
        raise ValueError("Invalid embeddings")
    return x
