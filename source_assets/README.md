# Refined editable assets

The current Blender masters and Godot GLBs are candidates under visual review. The user rejected the earlier medium-detail set and the first handmade hand prototypes. Geometry counts and contract results do not establish artistic acceptance. The rejected set is recoverable in the task's `work/stage2` archive.

`.gdignore` keeps authoring files outside Godot automatic import. The game uses GLBs directly and does not need Blender installed on the user machine.

| Master | Authoring recipe | Structure |
| --- | --- | --- |
| `field_equipment.blend` | `tools/build_anatomical_spectra.py`, `tools/makehuman_hand.py` | Compact balanced scientific optic, optical lens stack, enclosed battery, trigger and mode controls; two independently posed anatomical hands with 19 bones each; articulated rain-shell arms; reagent, salt and mud implements. |
| `abandoned_car.blend` | `tools/build_high_fidelity_assets.py -- --asset car` | Continuous stamped body, actual wheel arches, fitted roof and glazing, geometric tyre tread and split rims, four-seat interior, dashboard and controls, lamps, wipers and chassis. |
| `power_tower.blend` | `tools/build_research_landmarks.py` | L-section steel, structural connection plates and bolts, anchored concrete foundations, connected disc insulators, eight sagging conductors and inspection ladder. |
| `research_report.blend` | `tools/build_research_landmarks.py` | Individually curved thin paper sheets, cloth covers, sewn curved spine, embossed cover rules, tabs and fitted closure. |

The equipment hand geometry derives from the official MakeHuman hm08 base mesh, released under CC0 1.0 Universal. Only the hand and short wrist are extracted; the original quad topology and UVs are retained, then refined, skinned and posed for this game. The right hand grips the lamp pistol handle. The left hand has a separate underside support pose. `reference_cc0/` contains the unmodified OBJ, upstream license and CC0 legal statement. Its provenance and SHA-256 are recorded in `reference_cc0/PROVENANCE.json`. MakeHuman program code is not included or invoked. The original lamp, vehicle, tower, report and generated PBR maps use the included authoring scripts.

Current source and runtime density are recorded in `COMMERCIAL_MODEL_MANIFEST.json`; canonical exported counts and SHA-256 values are in `assets/refined/ASSET_MANIFEST.json`. Source/pre-export counts may differ from exported triangle counts after degenerate triangle removal.

For local rebuilding, use Blender 4.5 LTS bundled Python. Shared Godot editor imports and rendered previews must use the task `work/godot_exclusive.py` to avoid concurrent cache writes. Native candidate views, functional contracts, integrated gameplay inspection and performance measurement are distinct checks.
