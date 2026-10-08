from pathlib import Path
import numpy as np
import pytest

from hte.adapters import gollum_acquisition, process_mocca
from hte.io import read_csv, read_json, write_json


def test_actual_gollum_optimizer_on_synthetic_priors(tmp_path):
    pytest.importorskip("botorch")
    pairs = [{"pair_id": f"synthetic_{i}"} for i in range(8)]
    features = np.random.default_rng(42).normal(size=(8,6))
    priors = [{"pair_id": pairs[i]["pair_id"], "yield_percent": float(i*10+20), "qc_pass": True,
               "conditions_digest": "SYNTHETIC", "kind": "pair"} for i in range(4)]
    path = tmp_path/"acquisition.csv"
    gollum_acquisition(features, pairs, priors, path, "SYNTHETIC")
    rows = read_csv(path)
    assert len(rows) == 8 and np.isfinite([float(r["exploration_score"]) for r in rows]).all()
    assert read_json(str(path)+".metadata.json")["language_model_weights_finetuned"] is False


def test_actual_mocca_raw_dad_integration(tmp_path):
    pytest.importorskip("mocca2")
    time = np.linspace(0,2,401)
    wavelengths = np.arange(210,401,2)
    data = np.outer(np.exp(-((time-0.8)/0.04)**2)*100, np.exp(-((wavelengths-260)/30)**2))
    raw = np.zeros((len(time)+1,len(wavelengths)+1))
    raw[0,1:]=wavelengths
    raw[1:,0]=time
    raw[1:,1:]=data
    with (tmp_path/"synthetic.csv").open("w",encoding="utf-16") as handle:
        np.savetxt(handle,raw,delimiter=",")
    write_json(tmp_path/"manifest.json",{"method_id":"SYNTHETIC", "samples":[{"sample_id":"SYNTHETIC", "raw_path":"synthetic.csv"}]})
    settings=read_json(Path(__file__).resolve().parents[2]/"hte_inputs/mocca_settings.json")
    process_mocca(tmp_path/"manifest.json",settings,tmp_path/"processed")
    peaks=read_csv(tmp_path/"processed/peaks.csv")
    assert len(peaks)==1
    assert float(peaks[0]["retention_time_min"]) == pytest.approx(0.8,abs=0.02)
    assert float(peaks[0]["area"]) == pytest.approx(np.trapezoid(data[:,list(wavelengths).index(254)],time) if hasattr(np,"trapezoid") else np.trapz(data[:,list(wavelengths).index(254)],time),rel=0.05)
