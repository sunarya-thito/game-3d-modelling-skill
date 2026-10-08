# Measurable geometry and contact gates

## Purpose

A geometry gate turns the binding parts of an asset brief into reproducible measurements. It catches structural defects before UV work, texturing, rigging, rendering, or engine import makes them more expensive to fix. The validator observes the evaluated scene at its authored transforms. It never centers, lifts, welds, closes, or repairs the model.

Use [`scripts/blender/auditkit.py`](../scripts/blender/auditkit.py) inside Blender. Start from [`templates/geometry-contract.json`](../templates/geometry-contract.json), replace every illustrative value with values derived from the asset brief, and keep the completed contract beside the asset builder.

## What the gate measures

For each named mesh, `audit_scene` records:

- finite local and evaluated world coordinates;
- evaluated world-space bounds and object origin;
- vertices, edges, faces, and triangulated face count;
- used material count and invalid material assignments;
- boundary, wire, non-manifold, degenerate faces, and degenerate triangles;
- closed-shell state and signed-volume winding signal;
- conservative BVH triangle-pair self-intersection candidates.

At asset level it checks triangle, material, and part budgets. All measurements use the dependency graph, so visible modifier output—not only the unevaluated source mesh—is gated.

## Contract rules

The contract is deliberately explicit and fails closed:

- `schema_version` must be `1`.
- `coordinate_system` declares the up axis and implicit ground-plane height.
- `geometry_epsilon` is expressed in project units and must be positive.
- every audited object must appear in `objects`;
- unlisted scene meshes fail unless `allow_unlisted_meshes` is explicitly `true`;
- each object must declare triangle, material, and topology policy;
- a requirement that cannot be evaluated fails instead of being treated as zero.

`require_positive_volume` is a winding signal for a closed shell, not a mass calculation. Mirrored transforms and inward face winding can make the signed volume negative. Fix the authored transform or winding; do not take an absolute value to hide the problem.

## Bounds, origin, and ground

`origin.expected_world` checks the actual world origin independently from the mesh bounds. `bounds.expected_min` and `bounds.expected_max` compare evaluated vertex bounds. Both use an explicit tolerance.

An object's `ground` declaration compares the lowest evaluated point on the configured up axis with the implicit ground plane:

- positive offset greater than `touch_tolerance` means the object floats;
- negative offset deeper than `max_penetration` means it penetrates the ground;
- the validator reports the authored offset and does not move the model.

Only objects with a passing `ground` declaration can become active ground nodes in the support graph.

## Named contact probes

Each contact declaration names two contract objects and sets:

- `max_gap`;
- `min_penetration`;
- `max_penetration`.

The closest-surface probe samples evaluated vertices and triangle centroids in both directions against Blender BVHs. If surfaces intersect or one sampled point is inside the other shell, gap is reported as zero. Otherwise the smallest sampled surface distance is reported with its two closest points.

Containment does not use the sign of the nearest face normal. That local half-space test is wrong for concave forms. Instead, each sample is handled in this order:

1. reject it as outside when it lies beyond the target's evaluated world AABB;
2. classify a sample within `geometry_epsilon` of the surface as boundary, not penetration;
3. calculate the signed generalized winding number over the target's evaluated triangles;
4. classify a non-zero integral winding as inside and zero winding as outside;
5. fail the penetration measurement closed if the winding is not sufficiently close to an integer.

This containment test requires a finite, closed, non-self-intersecting target shell. The report records the method plus outside-AABB, boundary, inside, and ambiguous sample counts for both directions.

Penetration remains a sampled lower-bound estimate: after a sample is proven inside, its nearest-surface distance contributes to the estimate. The report marks `penetration_is_sampled_lower_bound: true`. Thin crossings can occur entirely between vertices and triangle centroids, so pair this gate with self-intersection results and review renders. A contact requirement whose containment or depth cannot be measured fails closed.

The contact report exposes these semantics:

- `containment_method` identifies the classifier;
- `containment.a_in_b` and `b_in_a` report sample totals and classifications;
- `penetrating_samples` is the combined number of proven-inside samples;
- `penetration_depth_estimate` is the largest nearest-surface distance among those samples, or zero when both directions were evaluable and none were inside;
- `penetration_evaluable: false` means the declared penetration bounds cannot pass.

Generalized winding is robust for concavity, but it is not unlimited. It assumes orientable closed triangle shells and becomes intentionally unevaluable for open, self-intersecting, inconsistent-winding, or numerically ambiguous targets. Very large coordinate magnitudes relative to feature size can reduce numeric stability. It evaluates one dependency-graph state, not every frame of an animation. Most importantly, finite sampling can miss a thin face crossing with no sampled vertex or centroid inside the other object; BVH surface intersections and visual or engine review remain separate evidence.

`axis_aligned_bounds_overlap` is broad-phase evidence only. Positive overlap on all axes does not prove mesh penetration, while a negative component proves that the two closed objects do not contain or intersect each other at that evaluated state.

## Support reachability

`support.edges` forms a directed graph from `child` to `support`. An edge becomes active only when its named contact probe passes. A required node is supported only when it can follow active edges to an active ground node.

This catches:

- a floating attachment with no contact;
- a touching chain that never reaches the ground or designated host;
- a failed contact hidden behind a declared parent relationship.

The graph proves declared geometric reachability, not physical stability. It does not calculate center of mass, friction, torque, structural strength, or whether a tiny contact patch looks plausible.

## Self-intersection signal

The self-intersection check runs a BVH against the same evaluated mesh and removes pairs that share a triangle vertex. Remaining pairs are conservative candidates between non-neighbouring triangles. The count is deterministic for the pinned Blender version but is not a replacement for exact constructive-solid-geometry analysis. Coplanar overlays, duplicate disconnected surfaces, extreme scale, and epsilon choice deserve targeted inspection.

Use `max_self_intersections: 0` for an ordinary closed production mesh. Declare a narrow non-zero exception only when the construction method is intentional, measured, and visually reviewed.

## Running the example

From the repository root:

```sh
blender --background --factory-startup --python-exit-code 1 \
  --python examples/geometry-gate.py -- --out build/geometry-gate
```

The script creates two deterministic fixtures:

1. a grounded base and supported payload that pass all declared limits;
2. a lifted base, floating open payload, and crossing closed shells that must fail.

It writes `positive.json` and `negative.json`. The process exits non-zero if the positive fixture fails, the negative fixture passes, or expected negative failure classes disappear.

Call the reusable API from an asset builder after geometry and modifiers exist:

```python
import json
from auditkit import assert_audit_passed, audit_scene

contract = json.loads(open("path/to/geometry-contract.json", encoding="utf-8").read())
report = audit_scene(contract)
assert_audit_passed(report)
```

Save `report` even on failure so reviewers can compare rounds.

## What remains a visual or engine judgment

Do not infer artistic or gameplay approval from a green geometry report. Images or in-engine review must still decide whether:

- silhouette, proportions, negative spaces, and authored asymmetry match the brief;
- contacts look intentional rather than barely touching or deeply buried;
- thickness, bevels, shading, and material boundaries read at the target camera;
- a supported assembly looks stable under gravity and motion;
- deformed, animated, transparent, or displaced surfaces clip between sampled frames;
- collision, LODs, pivots, scale, and performance behave correctly in the target engine.

Numeric gates reject known structural failures. They do not replace capable image review, animation playback, or engine integration tests.
