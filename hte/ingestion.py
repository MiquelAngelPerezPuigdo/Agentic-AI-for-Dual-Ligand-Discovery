"""Join separately completed LC batches without confusing reset injection numbers."""
from pathlib import Path

from .analytics import complete_export, normalize_export
from .io import digest, new_output, read_csv, write_csv, write_json
from .transfer import copy_verified


def ingest_exports(config, exports, mappings, dosing_path, output):
    if not exports or len(exports) != len(mappings):
        raise ValueError("Supply one injection mapping for each LC export")
    if len({str(Path(p).resolve()) for p in exports}) != len(exports):
        raise ValueError("An LC export was supplied more than once")
    source_hashes = {str(path): digest(path) for path in [*exports, *mappings, dosing_path]}
    if len({source_hashes[str(path)] for path in exports}) != len(exports):
        raise ValueError("LC exports contain identical file content; do not count a copied export as another sequence")
    output = new_output(output)
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
    # Preserve the original all-channel tables, not only normalized selected peaks.
    archived = []
    for index, (source, mapping) in enumerate(zip(exports, mappings), 1):
        for role, path in (("export", source), ("injections", mapping)):
            saved = output / "sources" / f"part-{index:02d}-{role}{Path(path).suffix}"
            record = copy_verified(path, saved, source_hashes[str(path)])
            archived.append({**record, "archived": saved.relative_to(output).as_posix()})
    saved = output / "sources/dosing.csv"
    archived.append({**copy_verified(dosing_path, saved, source_hashes[str(dosing_path)]),
                     "archived": saved.relative_to(output).as_posix()})
    write_csv(combined, peaks)
    # Partial batches cannot release the optimizer, regardless of filenames/order.
    complete_export(config, combined, saved, ready)
    write_json(output / "ingestion.json", {"sources": provenance, "archived_inputs": archived,
               "dosing_sha256": source_hashes[str(dosing_path)], "peaks_sha256": digest(combined)})
    return combined, ready
