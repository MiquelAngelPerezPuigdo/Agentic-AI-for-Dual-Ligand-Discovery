"""Small, reusable authentic-standard masters, separate from the SM/IS reaction stock."""
from __future__ import annotations

import math

from .io import finite


def preparation(config):
    """Budget the fixed 14 calibration injections and optional seven-mixture pilot.

    A minimum practical weighing overrides the 10% margin for very small masses.
    Check masters are weighed independently; no reaction SM/IS stock is used.
    """
    minimum = finite(config["stock_preparation"]["analytical_minimum_weigh_mg"], "minimum analytical weighing", 0.01)
    margin = finite(config["stock_preparation"]["analytical_margin_factor"], "analytical margin", 1)
    assays = config["stock_preparation"].get("assay_fractions", {})
    working_ul = max(200, math.ceil(60*margin/100)*100)
    result = []
    for analyte, mw, assay_key in (("substrate", config["chemistry"]["substrate_molecular_weight_g_mol"], "substrate_stock"),
                                   ("product", 97.09, "product_standard")):
        assay = finite(assays.get(assay_key, 1), assay_key+" assay", 1e-6, 1)
        # Fit consumes 15+35+80 uL of 10 mM master, plus the 1 mM working solution.
        # Independent check consumes 66.667 uL; optional pilot adds 200 uL/analyte.
        for role, required in (("fit", 130+working_ul/10), ("independent_check_and_optional_pilot", 2000/30+200)):
            volume = math.ceil(max(2000, required*margin, minimum*assay*1e6/(10*mw))/1000)*1000
            result.append({"analyte":analyte,"role":role,"stock_mM":10,"prepare_ul":volume,
                "mass_mg":10*volume*mw/1e6/assay,
                "required_master_ul":required,"solvent":"Matched analytical matrix; NO IS",
                "storage_container":("4 mL capped glass vial" if volume <= 3000 else "8 mL capped glass vial" if volume <= 6000 else "20 mL capped glass vial" if volume <= 16000 else "Compatible capped stock container larger than final volume"),
                "instruction":"Weigh independently for this master; record actual assay/mass and make to stated FINAL volume. Save unused stock."})
        result.append({"analyte":analyte,"role":"low_level_working","stock_mM":1,"prepare_ul":working_ul,
            "mass_mg":"","required_master_ul":working_ul/10,"solvent":"Matched analytical matrix; NO IS",
            "storage_container":"0.5 mL compatible microtube",
            "instruction":f"Take {working_ul/10:g} uL of the FIT 10 mM master and add {working_ul*0.9:g} uL matrix; manual pipetting."})
    return result
