# Left hand source repair

The production source and all three equipment GLBs are frozen at the hashes in `production-sha256.json`. This source task does not mark the full four-stage game goal complete. Godot native verification and the final independent whole-hand/tool audit are owned by the parent task.

The hand continues to use the actual CC0 MakeHuman hm08 mesh and original weights. Public-source study is recorded in `../left-hand-reset-research`: original joint markers match the MakeHuman skeleton, the Blender Studio base hand was read, and Rain's actual rig/mesh/deformation settings were inspected with autoexec disabled. The repair follows neutral skin bindings and source-derived joint planes rather than additional global smoothing.

## Actual changes

- Removed the left thenar 18-pass weight smoothing, metacarpal-affinity clipping, and 36-pass ordinary skin smoothing. The right path remains as it was.
- Turned the entire supporting palm into a diagonal cradle. The current forward-thumb reference is retained, while the whole palm takes part in the change instead of forcing the CMC to absorb a large isolated turn. The final palm is inclined by 8 degrees and yawed by 50 degrees in equipment coordinates. These are this authored grip's choices, not claimed anatomical standards.
- Kept the original upper/forearm lengths and shoulder source anchor, and selected an authored elbow plane that leaves the elbow at least 25 mm below the wrist and brings the authored wrist angle to about 13.48 degrees. The parent owns the final runtime shoulder/elbow solution.
- Fixed `fit_loc`: the four fingers now fit at the final actual palm location, including the axial shift. The old fitter used the location before the extra 20 mm shift and then corrected the resulting intersections by moving individual skin points.
- Left skin is no longer baked into the main grip and then bent back for tools. Its real neutral mesh and inverse binds are retained. The supported Blender glTF option `export_rest_position_armature=False` writes the current main pose as default joint transforms. The parent has already verified this convention in Godot 4.7.2.
- Each tool is fitted from neutral joint frames, with natural contact arcs for the four fingers and actual LBS pad/nail evaluation for the thumb. Relative tool quaternions are derived from the default main joint transforms for every finger, not just the thumb. Both relative and absolute-neutral metadata are retained as xyzw arrays.
- Tool sockets were moved into a reachable grip region, rather than forcing different-length fingertips toward an unreachable shared target. No left contact compression is used.
- Left nail pigmentation now crosses material-polygon boundaries continuously through standard glTF `COLOR_0` multiplied with a linearly compensated copy of the existing 4K diffuse map. The original nail polygons, geometry, side, and normals remain intact. The right materials and diffuse map are untouched. The cached derivative map regenerates through the already installed ffmpeg only when missing.
- In current-pose export mode, LOD decimation temporarily sets armatures to REST and restores their previous pose-position state in `finally`, before export. Other assets retain the existing default rest-position export mode.

## Evidence and limits

`production-verified.json` proves that the right source neutral and evaluated vertices, root transform, full weight stream, bone rest matrices, and bone pose matrices are unchanged from the preserved source. Their numerical deltas are zero.

The actual default poses of all three GLBs were reconstructed from their own joint transforms, neutral inverse binds, and vertex weights. Every vertex was checked finite; every fifth deformed vertex was compared to the actual evaluated high source surface. Maximum sampled distances for the left hand were 0.131, 0.156, and 0.277 mm. These results support the absence of the proposed low-LOD double-deformation issue; they are not an exhaustive per-triangle visual acceptance claim. All three GLBs retain `neutral_bind_skin=true` and standard `COLOR_0` on the left, with no `COLOR_0` added to the right.

The independent frozen-main audit at source SHA `560a239a9ca2f49a28a3ee5cbb2d3beb40fc886840ab7db8f777f8ba1f0e7405` inspected the actual evaluated whole hand with the prop removed. It found no strict self-crossings across 210,816 triangles, and confirmed that the old isolated thenar sphere and pointed wrist crease had disappeared. The final production source must still be compared against that accepted main shape; the only subsequent intended main change was nail pigmentation.

The latest isolated tool skin samples used actual neutral skin deformation, actual tool surfaces placed at their grip sockets, and closed-component signed distances. Maximum sampled thumb penetration was below 1 mm. Not every finger needs to press against the object; forcing all fingers to zero distance would alter the accepted natural grasp. The final independent audit owns the full-point and self-intersection checks on the production source.

The tool object roots are parked in `SkillTools` in the source. For source inspection, set `Tool*.matrix_world` to the corresponding grip socket's world matrix, then apply `tool_absolute_neutral_poses_json` directly to source pose bones after converting xyzw to Blender wxyz. The runtime uses `tool_grip_poses_json` relative to the imported default main bone transforms.

## Scope and recovery

The nine previous source/recipe/GLB/manifest files and exact hashes are preserved in `production-before`. This task changed the hand recipe, its small skin-fitting helper, left-only nail shading, the equipment driver export call, and the optional exporter/neutral-LOD branch. It did not edit `scripts/player/field_equipment.gd`, tests, gameplay rules, the right hand geometry, or other model assets.

Useful primary references include [Blender Studio rigging pipeline](https://studio.blender.org/tools/pipeline-overview/rigging/), [Rain](https://studio.blender.org/characters/rain/v3/), and the installed Blender 4.5 official glTF exporter `skins.py`, `tree.py`, and `search_node_tree.py`. The public hand sources, joint correspondence, and actual rig inspection receipts are preserved in the research output directory.
