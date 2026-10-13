# V9 codebase-memory Verify preflight

Actual supported CLI 0.11.0, not direct MCP. Final generation 2026-10-13T05:22:50Z, ready. All 13 requested code paths report metadata_match and no recorded issue; this remains a best-effort coverage signal. The previous stale-source ranges were read before refresh. Binary assets and image fidelity are checked by separate native/source receipts.

Files graph-0 through graph-5 record index_status, complete hunter_visual search (13/13), complete naifrog_model_contract search (20/20), both-direction _prepare_asset trace, exact _prepare_asset source, and the initial seven-path coverage. coverage-13-paths.json adds the inspector and changed runtime text paths.

Trace limitation: graph-3 resolves the bare GDScript builtin load name to a same-name historical Python archive function. The actual source in graph-4 loads MODEL_PATH as a Godot PackedScene, and the native tests confirm that runtime path. We do not treat the archive edge as a production dependency or claim a complete engine call graph. Global parse-partial entries outside this bounded scope remain; no whole-repository completeness claim is made.
