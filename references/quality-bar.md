# Production quality bar

## Purpose

Use this rubric to produce polished stylized game assets rather than prototypes. Quality is demonstrated by the asset, reports, review images, animation poses, and engine result—not by the amount of code or the number of parts.

The target project's art contract decides the style and budgets. This rubric defines the evidence needed to show that the result meets them.

## 1. Identity and silhouette

- The object is recognizable in a small solid-black silhouette at the gameplay camera's expected pixel footprint.
- Primary proportions and negative spaces carry the identity before texture is visible.
- Category-defining features from the brief are present from every gameplay-visible side.
- Thin details either remain readable at target resolution or become painted detail.

Reject a result whose identity depends on labels, color, or a close camera.

## 2. Authored form

- Bespoke parts use intentional profiles, outlines, cages, or sculpted surfaces rather than visibly untouched primitives.
- Long members have designed thickness and profile changes where the style calls for handcrafted form.
- Curvature is authored by stations or control functions, not added as undirected vertex noise.
- Bevels and chamfers are proportional to the final screen size and create controlled highlight bands.
- Secondary forms explain construction: reveals, lips, rebates, frames, seams, fasteners, supports, and transitions appear where visually useful.
- Geometry density is spent on silhouette, deformation, and highlight control before hidden flat areas.

Reject both a pile of primitive shapes and a single featureless surface.

## 3. Assembly, contact, and rest

- Every attachment that should touch an anchor derives its placement from that anchor's geometry.
- Curved anchors and their trim, lining, straps, or frames use the same curve or surface definition.
- Intended contact has neither a visible gap nor excessive burial.
- Loose objects have plausible support and do not balance on accidental points.
- Nothing penetrates the ground or floats after the asset is placed at its authored origin.
- Narrow overlap exceptions identify the exact parts, maximum depth, and construction reason.

Automated connectivity is necessary but not sufficient: a chain of parts can be connected to itself while the whole chain floats above its intended support.

## 4. Topology and export structure

- Required closed parts are manifold, consistently wound, and free of degenerates and accidental self-intersections.
- Triangulation is deterministic and does not change the visible silhouette or shading unexpectedly.
- Smoothing, split normals, and hard edges support the intended form.
- Object, material, bone, joint, socket, collision, and clip names match the engine contract exactly.
- The export contains the required hierarchy, not only the visible root mesh.
- Rebuilding from a clean Blender startup produces the same structure and materially equivalent output.

## 5. UVs and surface finish

- Visible surfaces meet the contract's texel-density target within its stated tolerance.
- Chart padding is measured in final texture pixels and survives mipmapping.
- Seams avoid focal areas unless the construction naturally hides them.
- Repeated pieces do not collapse into one uniform molded mass.
- Large-form color, cavity, edge response, material variation, and localized wear reinforce the geometry.
- Surface detail frequency remains legible under the gameplay camera and does not shimmer at distance.
- Glass, emissive, transparent, or double-sided materials are tested in the target engine's actual render path.

Read [references/surface-pipeline.md](surface-pipeline.md) for the build order.

## 6. Rigging and animation

- Bone and joint pivots sit on the intended mechanical or anatomical axes.
- Parent motion carries every required descendant without double transforms.
- Skin weights are normalized; there are no unintended unweighted vertices or distant influences.
- Rigid accessories remain rigid and attached to their owning bone or joint.
- Rest, representative, and extreme poses preserve volume where intended and avoid clipping, detached pieces, or ground penetration.
- Exported clips have correct names, frame ranges, loop behavior, sampling, and root-motion policy.
- Runtime-driven rigs expose every name and pivot expected by game code.

## 7. Review packet

Every candidate needs consistent evidence:

- three-quarter, front, back, left, right, and top views;
- small silhouette at the real or stricter gameplay footprint;
- closeups only for specific surface or contact questions;
- topology, bounds, materials, texture, rig, and animation metrics;
- host-context views for worn, held, mounted, or embedded pieces;
- rest, representative, and extreme animation poses;
- in-engine view under production camera, shader, lighting, and fog;
- prior verdicts and the exact fixes made since the last rejected round.

The reviewer opens the images, re-runs affordable measurements, and returns only `PASS` or `REJECT`. A meaningful note is a defect and therefore a rejection.

## 8. Runtime acceptance

- Scale, facing, origin, collision, materials, animation, and LODs behave correctly after import.
- The asset reads in motion and among neighboring approved assets, not only in an isolated render.
- Mipmaps, compression, shadows, transparency, and lighting are correct on the target renderer.
- Memory and frame cost are measured on representative target hardware.
- If performance requires simplification, create measured LODs before weakening the authored hero asset without evidence.

## Completion rule

An asset is complete only when it passes the contract, independent review, engine integration, and relevant target-device checks. A successful script run or GLB export is an intermediate result.
