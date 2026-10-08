# Pipeline architecture

## Contents

- Design goals
- Suggested layout
- Asset registry
- Fast preview build
- Rigging and animation
- Full release build
- Engine verification
- Useful reports
- Failure policy

## Design goals

The pipeline should make the cheapest trustworthy failure happen as early as possible. The same deterministic asset builder feeds both preview and release builds, while validators observe without silently repairing.

Keep creative data near the asset and mechanical policy in shared code. A project should be able to answer: what created this mesh, which contract governed it, what was measured, what was reviewed, and which exact export entered the game?

## Suggested layout

Adapt names to the project instead of forcing this tree:

```text
art/
  contract.md
  registry.py
  builders/
    market_stall.py
  toolkit/
    mesh.py
    forms.py
    checks.py
    preview.py
    export.py
  build/
    reports/
    previews/
  reviews/
    market_stall/
      round_01/
```

Responsibilities:

- `contract.md`: global conventions and category budgets.
- `registry.py`: compact asset metadata and builder lookup; no modeling logic.
- `builders/`: authored proportions, profiles, curves, parts, and joints.
- `toolkit/`: reusable geometry and deterministic build operations.
- `build/`: generated, reproducible output.
- `reviews/`: immutable human/agent decisions and evidence.

Generated output may be gitignored while approved review images remain tracked. Choose deliberately; do not let large `.blend` files enter history accidentally.

## Asset registry

Store measurable intent in one entry per asset. Useful fields include:

```python
ASSETS = {
    "market_stall": {
        "builder": build_market_stall,
        "category": "building",
        "size": (3.2, 2.8, 2.1),
        "triangle_range": (2500, 7000),
        "part_range": (25, 70),
        "materials_max": 2,
        "texture_max": 1024,
        "texel_density": 96,
        "joints": {"Awning": (0.0, 2.1, 0.4)},
        "allowed_contacts": [
            ("hinge_strap", "door", 0.012, "strap is seated on the door")
        ],
    }
}
```

Numbers above illustrate shape only; replace them with the project's own measured values. An exception without a maximum depth and reason is not auditable.

## Fast preview build

Run from a clean Blender state and use the same builder as the release path.

1. Build geometry and required host context.
2. Measure bounds, origin, parts, triangles, materials, joints, and naming.
3. Run topology and contact checks before UV mutation.
4. Assign a cheap clay or lightweight preview material.
5. Render front, back, left, right, top, and three-quarter views.
6. Render a black 64 px silhouette on white.
7. Save a machine-readable report beside the images.

Use the project's real coordinate convention and representative camera. A review render lit from the wrong direction can lead to wrong texture and bevel decisions.

Contact checks should distinguish:

- a disconnected part touching nothing;
- a chain of parts that never connects to ground or the designated host;
- a surface pair expected to meet but separated by a visible gap;
- intentional seating versus deep burial;
- genuine overlap versus parts that are merely close;
- a thin member passing through a host even when no vertex lies inside it.

No automatic centering or lifting should hide a wrong origin or ground penetration. Report the defect at its authored location.

## Rigging and animation

Treat rig data as part of the asset contract, not as an afterthought added during export.

Use a skinned armature when one continuous surface must bend. Define bones parent-first, keep pivots in project coordinates, normalize vertex weights, and fail on unweighted vertices or missing parents. Weight decorative rigid parts wholly to one owner bone unless the design explicitly requires deformation. Inspect rest, representative, and extreme poses for collapsed volume, unwanted influence, clipping, and detached pieces.

Use named rigid joints when whole parts move without bending. Split or parent parts around authored pivots, preserve nested relationships, and export the hierarchy rather than the visible root mesh alone. This works well for doors, wheels, tailgates, sails, tools, mechanical parts, and modular building animation.

Choose and document one animation authority:

- **Exported clips:** verify action/clip names, frame ranges, sampling, loop flags, root motion, and that the exporter includes each required clip.
- **Runtime-driven motion:** export an unbaked rest hierarchy with stable names, axes, and pivots; verify that engine code discovers and poses every required joint.
- **Hybrid:** state which channels are baked and which the engine controls so they do not fight each other.

Add animation evidence to the review packet: bind/rest pose, one representative gameplay pose, relevant extreme poses, and a short in-engine playback capture when timing or transitions matter. A correct bind pose is not proof of a correct rig.

## Full release build

Only run after the fast geometry gate and rig checks are clean.

1. Compute visibility if hidden faces may use reduced UV area.
2. Unwrap with a chart margin expressed in final texture pixels.
3. Iterate packing to hit the target texel density within tolerance.
4. Bake the maps required by the art style.
5. Paint or assign materials deterministically.
6. Finalize joints, bones, animation clips, collision, LODs, and metadata.
7. Export the complete hierarchy and required animation—not only the visible mesh.
8. Save the source scene and a JSON report.
9. Re-import in the target engine.

The JSON report should record the asset id, category, sizes, counts, budgets, texture size, measured density, material count, joints, animation clips or runtime motion mode, gate state, build duration, tool versions, and a content hash when reproducibility matters.

## Engine verification

Automate import, then inspect the asset under the production shader and camera. Verify:

- axes, facing, scale, origin, and ground contact;
- material and texture assignment, filtering, and mip behavior;
- joint names, pivots, animation, and hierarchy;
- collision and interaction bounds;
- LOD transitions and shadow behavior;
- transparency/depth behavior;
- target-device memory and frame time.

For performance comparisons, pair baseline and candidate runs under the same device temperature, power state, camera path, and scene. Record distributions or stable medians rather than a single best frame.

## Useful reports

Keep reports machine-readable and concise. Useful artifacts are:

- `gate.json`: fast geometry state and defect list;
- `build.json`: final budgets, density, materials, joints, duration, versions;
- `contact-sheet.png`: consistent views with labels;
- `silhouette.png`: downsampled recognition test;
- `verdict.md`: independent decision and evidence;
- engine import log and device performance capture.

## Failure policy

- Fail closed on binding requirements.
- Fix the asset or its declared specification, not the evidence.
- Change a global threshold only with cross-asset measurements and an explanation.
- Preserve failed review rounds.
- Rebuild from a clean state after a builder or shared helper changes.
- Do not approve an asset whose report and visual evidence disagree.
