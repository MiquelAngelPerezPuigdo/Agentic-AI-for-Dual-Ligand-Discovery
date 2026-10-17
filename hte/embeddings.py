from __future__ import annotations

from pathlib import Path
import numpy as np

from .io import object_digest, write_json


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
    if x.ndim != 2 or len(x) != len(candidates) or not x.shape[1] or not np.isfinite(x).all():
        raise ValueError("Invalid embeddings")
    return x
