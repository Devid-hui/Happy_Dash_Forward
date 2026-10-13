# Hand study resources

These are reference/source assets, not an accepted game hand. Godot import is disabled here.

- Blender Human Base Meshes v1.4.1, official https://www.blender.org/download/demo-files/ ; ZIP SHA256 811f43accbb31a88266d932f8f5563b2d13586fca0ba2693aad1f5fe582b3515. Hand-specific metadata: CC0; realistic hand by Dan Ulrich, stylized hand by Julien Kaspar. The bundled README says all provided assets are CC0. Full inspected metadata, including an unrelated Rain Rig text block, is retained in blender-bundle-metadata.json. The extracted .blend keeps the two hand objects and their native metadata, UV and modifiers, without adding a rig or textures.
- MakeHuman Hands 01, official https://static.makehumancommunity.org/assets/assetpacks/hands01.html ; four targets by jujube and Mindfront, each marked CC0 in hands01/packs/hands01.json. Original ZIP SHA256 b874210dc3a9a179b73a3dd04976bc27521f47f985d106ce46fb45a480ee1701. Indices were checked against the current 19,158-vertex MakeHuman source. No target has yet been applied to the game.

Do not infer that a low-resolution base mesh plus subdivision is a finished high-detail commercial asset. Use the anatomical volume, topology and documented source data as authoring references; verify new poses and source/export parity in the actual engine.
