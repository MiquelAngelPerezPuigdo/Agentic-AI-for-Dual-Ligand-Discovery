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
    result = []
    for analyte, mw, assay_key in (("substrate", config["chemistry"]["substrate_molecular_weight_g_mol"], "substrate_stock"),
                                   ("product", 97.09, "product_standard")):
        assay = finite(assays.get(assay_key, 1), assay_key+" assay", 1e-6, 1)
        # Robot makes 0.5 mM and 5 mM FIT working stocks from 20 +400 uL master.
        # Independent check consumes 66.667 uL; optional robot pilot dilutions add 420 uL/analyte.
        for role, required in (("fit", 420), ("independent_check_and_optional_pilot", 2000/30+420)):
            volume = math.ceil(max(2000, required*margin, minimum*assay*1e6/(10*mw))/1000)*1000
            result.append({"analyte":analyte,"role":role,"stock_mM":10,"prepare_ul":volume,
                "mass_mg":10*volume*mw/1e6/assay,
                "required_master_ul":required,"solvent":"Matched analytical matrix; NO IS",
                "storage_container":"Labeled channel of the configured Axygen bulk reservoir",
                "instruction":"Weigh independently; record actual mass/assay in the charges CSV. Robot adds nominal matrix volume and makes working dilutions. Save unused stock."})
    return result
