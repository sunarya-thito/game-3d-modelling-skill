# Blender Python helper

## Purpose

[`scripts/blender/meshkit.py`](../scripts/blender/meshkit.py) is a small, portable implementation of the modeling vocabulary described by this skill. It leaves project paths, palettes, budgets, asset registries, rig policy, and engine integration to the consuming game project.

Use it when a project has no established modeling toolkit. If the project already has reliable equivalents, preserve those conventions instead of creating a parallel helper.

For articulated assets, [`scripts/blender/rigkit.py`](../scripts/blender/rigkit.py) adds parent-first hierarchy validation, rigid pivots, armature creation, normalized weight binding, and weight audits. The complete Blender workflow is explained in the [authoring guide](bpy-authoring-guide.md).

## Operations

- `CoordinateBasis`: keeps project coordinates explicit until Blender object creation.
- `MeshDraft`: stores one authored part as points, polygons, and material indices.
- `add_profile_loft`: bridges equal-sized authored cross-sections.
- `add_path_extrusion`: carries a 2D section along a path with optional per-station scale.
- `add_revolved_profile`: revolves an authored radius/height profile and collapses zero-radius stations to clean poles.
- `add_extruded_outline`: extrudes a concave or convex outline into a closed plate.
- `create_mesh_object`: validates indices, maps axes, recalculates normals, and triangulates.
- `inspect_topology`: reports boundary edges, non-manifold edges, degenerates, and counts without modifying the mesh.
- `write_glb`: exports only the supplied object hierarchy, including animation.

These helpers are construction primitives, not an art style. Asset builders remain responsible for meaningful proportions, varied sections, contact relationships, joints, and budgets.

## Example

[`examples/stylized-crate.py`](../examples/stylized-crate.py) builds a multi-part crate from varied loft sections, audits each part, and exports a GLB. Run it from the repository root:

```bash
blender --background --factory-startup --python-exit-code 1 --python examples/stylized-crate.py -- \
  --out build/stylized-crate.glb
```

On PowerShell the same command can be written on one line.

The example output is intentionally not a production art asset or visual benchmark. It demonstrates API use, clean topology, deterministic rebuilding, explicit output paths, and failure before export when the topology audit is dirty. Apply the full [production quality bar](quality-bar.md) and [surface pipeline](surface-pipeline.md) to real assets.

Additional executable examples cover [rigid joints and an exported action](../examples/rigid-joint-animation.py), [a skinned armature and normalized weights](../examples/skinned-chain-animation.py), [clean-scene GLB auditing](../examples/audit-glb.py), and [multi-view review rendering](../examples/render-review.py).

## Coordinate frames

The default `BLENDER_FRAME` basis treats input coordinates as Blender coordinates. `Y_UP_FRAME` is supplied as an example for a project that authors with +Y up and +Z forward. Define another `CoordinateBasis` for other engines instead of scattering axis swaps throughout asset builders.

Joint pivots, bounds, and briefs should remain in project coordinates. Convert only when constructing Blender objects or exporting engine data.

## Extension boundary

Keep this helper compact. Add a reusable operation only after more than one asset needs it. Put asset-specific curves and dimensions in the asset builder, and put project-specific exporters, texture baking, rigs, collision, and engine import code in their own modules.
