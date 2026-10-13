# The Midnight Academy — The Rainfield

A first-person horror escape prototype built with **Godot 4.7.2 Standard (GDScript)** and Forward+. Collect three research books in a stormy forest, combine up to three discipline abilities, and reach the academy exit while five hunters pursue you.

See [中文说明](README_ZH.md) for controls, current rules, abilities, validation, export steps, and known limits. This repository contains source; it does not include a prebuilt `.app`.

The [2026-10-12 audit repair report](docs/updates/2026-10-12-audit-repair.md) records the changes, regression results, actual play attempts, export checks, and performance measurements. Asset attribution is listed in [README_ASSETS.md](README_ASSETS.md) and the corresponding `assets/*/ASSET_LICENSE.txt` files.

For a complete first checkout, follow [download and first-run instructions](docs/GETTING_STARTED.md). Models and textures use **Git LFS**. A default GitHub Source ZIP may contain only pointers, and running the game directly does not replace the editor's initial import. Download only the current runtime assets and explicitly import them with:

```bash
python3 tools/bootstrap_project.py --download --godot /path/to/godot
```

Then open `project.godot` in Godot 4.7.2 and press F5. To diagnose a map showing ground/rain/HUD but no trees, character or held equipment, run `python3 tools/bootstrap_project.py --check`; it distinguishes missing LFS binaries from missing/stale local imports. Blender is optional for source editing and is not required to play. See the linked guide for selective cloning, Windows/macOS commands and optional full Blender-source downloads.

Controls: WASD move, mouse look, Shift sprint, E interact, 1/2/3 abilities, Tab handbook, F rain-filter band, Esc pause. The handbook pauses gameplay and releases the mouse. Losing window focus pauses the game; returning focus requires an explicit resume.

Run the headless regression suite with Python 3 and the matching engine:

```bash
python3 tests/run_tests.py --godot /path/to/godot
```

The runner rejects engine/script errors, timeouts, nonzero exits, and missing success markers. CI runs the same suite. Headless results do not establish rendering quality or a completed human playthrough.

For serial graphical performance sampling at 640×360:

```bash
python3 tests/run_performance.py --godot /path/to/godot --output /path/to/results
```

The workload scripts a camera route and suppresses outcome/focus pauses only in its test scene. It retains all five hunter AI, rain, forest, lightning, and audio. It is a performance test, not gameplay acceptance; the report includes its configuration and limits.

Forest and rain-audio licenses are recorded with those assets. A root source-code license and provenance for the unused reference images remain unresolved; no project-wide license is implied by this README. The export preset excludes development tests, previews, documentation, and the unused reference images while retaining runtime resources.
