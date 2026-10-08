# Capability status

This table separates executable repository support from production checks that
still require a target game project. A written instruction is not counted as an
implemented validator.

| Capability | Repository support | What still requires the target project |
|---|---|---|
| Text, image, or combined intake | Structured brief and review routing | A vision-capable model or human must inspect image references |
| Procedural modeling | Executable loft, sweep, revolve, outline, material, and export helpers | Asset-specific form design and art direction |
| Geometry and contacts | Executable evaluated-mesh, bounds, budget, topology, volume, self-intersection, gap, penetration, and support gates | Visual plausibility, physics stability, and gameplay context |
| UVs and surfaces | Executable UV, density/stretch, guttered texture, color-space, Principled material, export, and re-import checks | Art-directed painting, production bakes, and target-engine shader parity |
| Rigid and skinned rigs | Executable hierarchy, armature, weight, action, export, and re-import examples | Asset-specific deformation review and engine retargeting |
| Animation channels | Executable object, bone, and morph authoring helpers plus a runtime sidecar schema | Engine adapters for material, atlas/UV, visibility, and effects channels |
| Review evidence | Deterministic multi-view and silhouette renderer with capability routing | Final visual approval by a capable reviewer |
| GLB audit | Clean-scene imported inventory and channel evidence | Comparison with target-engine import behavior |
| Collision and LOD | Contract fields and engine-stage guidance | Authoring and validation depend on the selected engine and project rules |
| Engine acceptance | Explicit checklist and stop conditions | Import, playback, shader, collision, LOD, and performance tests in the selected engine |

Blender integration checks are pinned to the version in
[`blender-version.txt`](../blender-version.txt). A green Blender test suite does
not replace target-engine verification.
