# Art contracts

## Purpose

An art contract converts direction such as “chunky,” “mobile-friendly,” or “hand-painted” into constraints that a builder, validator, and reviewer can apply consistently. Keep the rationale in design documentation and the binding values in one short contract.

## Contract layers

Use three layers:

1. **Project conventions:** units, axes, facing, origin, camera, lighting, naming, animation authority, export format.
2. **Category limits:** size ranges, triangle ranges, part expectations, texture limits, material limits, texel density, rig complexity, animation and LOD policy.
3. **Asset brief:** identity, silhouette, approved features, contact relationships, joints or bones, motion ranges, clips, exceptions, and acceptance views.

Build the asset brief from the [reference intake protocol](reference-intake.md). Reference interpretation is an input to the contract, not a substitute for measurable requirements.

Do not promote one project's aesthetic preference into a universal modeling rule. A “no visible primitives” rule may be correct for a handcrafted hero set and wrong for a geometric game.

## Make constraints measurable

Replace vague directions with observable tests:

| Direction | Measurable form |
|---|---|
| Reads clearly on a phone | silhouette remains identifiable at the chosen pixel size |
| Not too detailed | triangles, materials, texture memory, and frame cost stay inside category limits |
| Attachments feel connected | named contact pairs have a maximum allowed gap or seating depth |
| Consistent style | comparison set, palette roles, bevel range, camera, and texture treatment are named |
| Correct size | bounding-box range and origin/facing conventions are recorded |
| Animation-ready | joint names, pivots, axes, parents, and expected motions are listed |

## Budgets are evidence, not folklore

Set budgets from approved assets and target-device measurements. Record both floors and ceilings when too little geometry is also a quality failure. If a hero asset needs more geometry, measure its real cost and consider LODs before flattening its design.

Express texture density in pixels per project unit and include tolerance. Texture dimensions alone do not guarantee consistent sharpness.

## Exceptions

An exception should include:

- the two named parts or exact rule it affects;
- the maximum permitted deviation;
- the construction reason;
- the asset(s) it applies to;
- reviewer confirmation that it is not hiding a visible defect.

Avoid blanket allowlists and uncapped overlap exemptions.

Use [templates/asset-brief.md](../templates/asset-brief.md) for per-asset values.
