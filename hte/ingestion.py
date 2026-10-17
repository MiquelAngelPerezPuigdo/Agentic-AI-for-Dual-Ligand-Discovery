"""Join separately completed LC batches without confusing reset injection numbers."""
from pathlib import Path

from .analytics import complete_export, normalize_export
from .io import digest, new_output, read_csv, write_csv, write_json


def ingest_exports(config, exports, mappings, dosing_path, output):
    if not exports or len(exports) != len(mappings):
        raise ValueError("Supply one injection mapping for each LC export")
    if len({str(Path(p).resolve()) for p in exports}) != len(exports):
        raise ValueError("An LC export was supplied more than once")
    output = new_output(output)
    source_hashes = {str(path): digest(path) for path in [*exports, *mappings, dosing_path]}
    peaks, seen, provenance = [], set(), []
    for index, (source, mapping) in enumerate(zip(exports, mappings), 1):
        normalized = output / f"part-{index:02d}.csv"
        normalize_export(config, source, normalized, injections_path=mapping)
        rows = read_csv(normalized)
        samples = {row["sample_id"] for row in rows}
        if samples & seen:
            raise ValueError("A sample occurs in multiple LC batches; select one accepted injection: " + ", ".join(sorted(samples & seen)))
        seen.update(samples)
        peaks.extend(rows)
        provenance.append({"source": str(source), "sha256": digest(source),
                           "mapping": str(mapping), "mapping_sha256": digest(mapping),
                           "samples": sorted(samples)})
    combined = output / "peaks.csv"
    ready = output / "peaks.ready.json"
    if any(digest(path) != checksum for path, checksum in source_hashes.items()):
        raise ValueError("LC source, mapping or dosing changed during ingestion; publish stable completed files")
    write_csv(combined, peaks)
    # Partial batches cannot release the optimizer, regardless of filenames/order.
    complete_export(config, combined, dosing_path, ready)
    write_json(output / "ingestion.json", {"sources": provenance,
               "dosing_sha256": digest(dosing_path), "peaks_sha256": digest(combined)})
    return combined, ready
