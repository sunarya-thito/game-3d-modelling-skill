---
name: game-3d-modelling-skill
description: Plan, model, surface, rig, animate, validate, preview, and review reproducible stylized 3D game models made with Blender Python. Use for game-ready GLB pipelines, model contracts, procedural modeling, skeletal or rigid rigs, engine-driven animation, geometry gates, review packets, or auditing an existing 3D-model workflow. Do not use for UI, audio, ordinary image generation, or manual-only DCC tutorials.
---

# Procedural 3D game models

Build reproducible 3D game models as a measured pipeline, not as an untracked sequence of edits.

## Choose the mode

- **Establish or repair a pipeline:** read [references/pipeline.md](references/pipeline.md) and [references/art-contract.md](references/art-contract.md).
- **Check what is automated versus engine-dependent:** read [references/capability-status.md](references/capability-status.md).
- **Author an asset:** first read [references/reference-intake.md](references/reference-intake.md) and turn the supplied text, images, or both into an explicit brief. Then read [references/quality-bar.md](references/quality-bar.md), [references/modeling-principles.md](references/modeling-principles.md), [references/bpy-authoring-guide.md](references/bpy-authoring-guide.md), [references/geometry-gates.md](references/geometry-gates.md), [references/surface-pipeline.md](references/surface-pipeline.md), [references/surface-implementation.md](references/surface-implementation.md), and [references/animation-channels.md](references/animation-channels.md), and use [templates/asset-brief.md](templates/asset-brief.md). If Blender is missing or its command is unknown, read [references/blender-headless.md](references/blender-headless.md). If the project lacks a modeling toolkit, also read [references/blender-helper.md](references/blender-helper.md), inspect [scripts/blender/meshkit.py](scripts/blender/meshkit.py), [scripts/blender/surfacekit.py](scripts/blender/surfacekit.py), [scripts/blender/rigkit.py](scripts/blender/rigkit.py), [scripts/blender/animationkit.py](scripts/blender/animationkit.py), and [scripts/blender/auditkit.py](scripts/blender/auditkit.py), then choose the closest executable example under [examples/](examples/). Treat every bundled asset as a technique test, not a visual benchmark.
- **Review an asset:** first read [references/review-capabilities.md](references/review-capabilities.md), then follow [references/review-protocol.md](references/review-protocol.md). Use [templates/review-verdict.md](templates/review-verdict.md) only when the reviewer can actually inspect images; otherwise produce a review handoff and keep visual approval pending.

Only read the references needed for the current mode. Treat the project's own art direction and engine constraints as authoritative.

Before doing asset work, confirm every linked file for the selected mode is readable. If a link is missing, stop and report an incomplete installation; do not pretend to have read it or substitute an invented API.

## Workflow

Track this checklist for a new or substantially revised asset:

```text
Asset progress
- [ ] Brief and measurable contract agreed
- [ ] References have clear usage rights
- [ ] Silhouette and primary forms authored
- [ ] Fast geometry gate passes
- [ ] Rig hierarchy, pivots, and weights validated
- [ ] Animation clips or runtime motion validated in representative poses
- [ ] Review packet inspected from every required view
- [ ] UV, bake, paint, rig, and export pass
- [ ] Independent review passes without notes
- [ ] Engine import and target-device checks pass
```

### 1. Inspect before changing

Find the existing asset registry, builders, coordinate conventions, exporter, shader, budgets, naming rules, test commands, and approved comparison assets. Do not invent a second convention when the project already has one.

Classify the creative input as text, image reference, or combined. Record observable facts separately from interpretation, identify hidden or ambiguous views, and state which traits must match versus where invention is allowed. If the active agent cannot inspect supplied images, obtain a structured visual description from a vision-capable agent or human before modeling.

If no binding contract exists, create one from the supplied template before modeling. Record units, axes, origin, facing, camera distance, size, triangle and material budgets, texture density, joints, collision needs, export format, and the views used for approval.

### 2. Separate intent from implementation

Keep these concerns distinct:

- an asset brief states what must be recognizable and measurable;
- a registry maps an asset id to its builder, limits, palette, joints, and justified exceptions;
- modeling helpers provide reusable operations such as loft, sweep, lathe, slab, and shell;
- asset builders contain the authored form decisions;
- validators report defects but do not silently repair or reposition the asset;
- preview and full-build commands consume the same builder.

Avoid project-specific constants inside shared geometry helpers.

### 3. Author the form deliberately

Start with silhouette, proportions, and contact surfaces. For bespoke stylized work, prefer drawn profiles, varied sections, and shared curves over a visible pile of untouched primitives. Variation must be deterministic and explainable. If an attachment follows a curved anchor, derive both from the same curve or surface function.

Primitives are acceptable only when the art contract calls for them or they are an intermediate construction step whose final silhouette is materially developed.

Do not assume Blender Python knowledge. When writing or modifying a builder, follow the concrete data-flow and `bpy` patterns in the authoring guide. Prefer data API operations over selection-dependent operators; when an operator is necessary, establish its mode, active object, selection, and scene context explicitly.

### 4. Run the fast gate first

Before UV work, baking, painting, or export:

1. Build the final geometry from a clean Blender startup.
2. Measure bounds, origin, triangle count, part count, material slots, and required joints.
3. Check open or non-manifold edges, degenerates, flipped normals, self-intersections, ground penetration, unintended deep overlaps, unsupported parts, and gaps between surfaces that should touch.
4. Render the standard review views plus a 64 px silhouette.
5. Stop and fix geometry if any binding check fails.

Never weaken a global threshold to make one asset pass. Declare a narrow exception by part pair, maximum depth, and reason. Review the exception itself.

Encode binding bounds, budgets, topology, contact probes, and support reachability
in a geometry contract. Run `scripts/blender/auditkit.py` against evaluated meshes
and preserve its report; do not substitute an eyeballed pass for a declared gate.

### 5. Rig and animate for the game

Choose the rig from the deformation need:

- use a skinned armature for a continuous surface that must bend;
- use named rigid joints for whole parts that rotate, translate, or carry child parts;
- support nested joints so parent motion carries its descendants;
- keep decorative rigid pieces wholly assigned to their owning bone or joint unless deformation is intentional.

Record every required joint or bone name, pivot, axis, parent, and expected range in the asset brief. Validate normalized weights, unweighted vertices, implausible cross-body influence, hierarchy cycles, and required engine names. Test rest, representative, and extreme poses for volume loss, collapsing joints, detached accessories, clipping, and ground penetration.

Declare authority per animation channel with `templates/animation-manifest.json`.
Object, bone, and morph channels may be Blender-owned clips when the chosen
export format carries them. Treat arbitrary shader parameters, emission, UV or
atlas state, visibility, and effects as runtime-owned unless an explicitly tested
exporter/importer extension proves otherwise. For exported clips, verify clip
names, frame ranges, loop behavior, root motion, sampling, and clean re-import.
For runtime motion, export a stable rest/static state and verify that engine code
resolves every declared owner and runtime parameter.

### 6. Run the full build

After the fast gate is clean, unwrap to the target texel density, measure density
and stretch, preserve sufficient chart padding for mipmaps, bake or generate the
required maps, assign correct color spaces, and connect them through Principled
BSDF materials. Use `scripts/blender/surfacekit.py` and
`examples/textured-surface-workflow.py` as executable patterns. Build the joint
hierarchy, export, and write machine-readable reports. Import the result into a
clean Blender scene and then the target engine; a successful export call is not
proof of a successful shipping asset.

Use one source of truth for the builder. Preview and release builds must not model different geometry.

### 7. Review independently

The reviewer must inspect the images and reports, re-run measurable checks when practical, compare against the brief and approved family, and issue only `PASS` or `REJECT`. A useful note is a defect, so do not use “pass with notes.” The reviewer must not edit the asset under review.

Detect review capability before claiming a verdict. A model with no image input may run machine gates and prepare evidence, but it cannot approve silhouette, proportions, contact appearance, surface finish, or pose quality. It must hand the packet to a vision-capable model or human and report visual review as pending.

Review mounted, worn, held, or embedded assets in their real host context. A clean isolated accessory can still float or clip in use. Review animated assets in rest, representative, and extreme poses—not only in the bind pose.

### 8. Verify in context

Check the imported asset under the actual camera, lighting, animation controller, collision, LOD, and device constraints. Confirm clip discovery or runtime joint lookup, playback speed, looping, root motion, transitions, attachment behavior, and deformation under gameplay poses. Compare performance against a paired baseline on the target hardware. Prefer an explicit lower LOD over degrading the authored hero asset without evidence.

### 9. Preserve evidence

Keep immutable review rounds such as `reviews/<asset>/round_01/`. Each round should contain the verdict, metrics, and the exact images reviewed. Do not overwrite failed rounds; they explain why the pipeline changed.

## Completion standard

Report what was built, the commands actually run, the observable results, remaining rejected assets or deferred checks, and any decision the user still needs to make. Do not call the pipeline complete because scripts ran; call it complete when the exported asset passes its contract and is verified in context.
