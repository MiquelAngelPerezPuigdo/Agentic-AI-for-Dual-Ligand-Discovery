"""Saved representations must not silently follow a changed reaction target."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from hte.embeddings import (build_embeddings, embedding_conditions, load_embeddings,
                            pair_text)
from hte.inventory import campaign_inventory, candidates
from hte.io import object_digest, read_json


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "hte_inputs/pair_embeddings_t5-base.npz"


@pytest.fixture
def inputs():
    config = read_json(ROOT / "hte_inputs/campaign.json")
    inventory = campaign_inventory(ROOT / "hte_inputs/ligands.csv", config)
    return config, inventory, candidates(inventory)


def test_exact_archived_campaign_and_prompt_remain_compatible(inputs):
    config, inventory, pairs = inputs
    assert embedding_conditions(config) == embedding_conditions()
    assert np.array_equal(load_embeddings(ARCHIVE, inventory, pairs, config=config),
                          load_embeddings(ARCHIVE, inventory, pairs))
    a, b = inventory["L01"], inventory["L02"]
    assert pair_text(a, b, embedding_conditions(config)) == (
        f"Pd desulfonylative fluorination in toluene at 95 C. Ligand 1 {a['name']} {a['smiles']} 6 mol%. "
        f"Ligand 2 {b['name']} {b['smiles']} 6 mol%. Pd 12 mol%. Substrate pyridine-2-sulfonyl fluoride 0.1 M.")


@pytest.mark.parametrize("section,key,value", [
    ("chemistry", "temperature_C", 100),
    ("chemistry", "substrate_molarity_M", 0.05),
    ("chemistry", "pd_mol_percent", 6),
    ("chemistry", "substrate", "another substrate"),
    ("chemistry", "substrate_smiles", "CC"),
    ("liquids", "substrate_stock_solvent", "acetonitrile"),
])
def test_changed_target_cannot_reuse_archived_features(inputs, section, key, value):
    config, inventory, pairs = inputs
    config[section][key] = value
    with pytest.raises(ValueError, match="conditions differ"):
        load_embeddings(ARCHIVE, inventory, pairs, config=config)


def test_arbitrary_legacy_file_cannot_claim_archived_conditions(inputs, tmp_path):
    config, inventory, pairs = inputs
    path = tmp_path / "unknown.npz"
    with np.load(ARCHIVE, allow_pickle=False) as archive:
        contents = {key: archive[key].copy() for key in archive}
    contents["features"][0, 0] += 1
    np.savez_compressed(path, **contents)
    with pytest.raises(ValueError, match="no verified condition provenance"):
        load_embeddings(path, inventory, pairs, config=config)


def test_new_condition_metadata_is_checked_inside_archive(inputs, tmp_path):
    config, inventory, pairs = inputs
    revised = copy.deepcopy(config)
    revised["chemistry"]["temperature_C"] = 100
    path = tmp_path / "new.npz"
    # Synthetic vectors verify metadata compatibility only; no model inference.
    features = np.arange(len(pairs)*2).reshape(len(pairs), 2)
    np.savez_compressed(path, pair_ids=np.array([p["pair_id"] for p in pairs]),
                        features=features, inventory_digest=np.array(object_digest(inventory)),
                        template_conditions_json=np.array(json.dumps(embedding_conditions(revised))))
    assert np.array_equal(load_embeddings(path, inventory, pairs, config=revised), features)
    with pytest.raises(ValueError, match="conditions differ"):
        load_embeddings(path, inventory, pairs, config=config)


def test_unequal_loading_stops_before_model_access(inputs, tmp_path):
    config, inventory, pairs = inputs
    config["chemistry"]["ligand_b_mol_percent"] = 12
    with pytest.raises(ValueError, match="equal ligand A/B loadings"):
        build_embeddings(inventory, pairs, "must-not-be-loaded", tmp_path / "new.npz", config=config)
    assert not (tmp_path / "new.npz").exists()
