# UV, baking, and surface pipeline

## Choose the shading model first

Identify what the target engine expects before painting:

- a conventional PBR set such as base color, normal, roughness, metallic, and occlusion;
- a hand-painted base color with lightweight runtime lighting;
- a largely baked or unlit stylized treatment;
- a project-specific hybrid.

Do not bake lighting into textures if the production shader will light the same information again. Conversely, do not leave form definition entirely to runtime lights when the approved style expects painted gradients and edge control.

## UV order

1. Finalize and validate geometry before unwrapping.
2. Mark seams based on construction, visibility, and deformation.
3. Scale visible charts toward the category's texel-density target.
4. Give hidden surfaces only the reduced allocation allowed by the art contract.
5. Pack with padding measured at the final texture resolution, including mip requirements.
6. Measure density and stretch after packing; do not trust the requested pack scale.
7. Re-run the geometry gate if an unwrap or modifier changed topology.

Use one texture sheet only when the engine and material plan benefit from it. Material-count limits and draw-call behavior belong in the art contract.

## Bake useful evidence

Depending on the shading model, bake maps that help a deterministic painter or texture author understand the form:

- ambient occlusion or cavity for contact and crevice information;
- world/object-space position for broad gradients and localized effects;
- normals for directional edge response;
- curvature or thickness when the style uses them;
- material/zone and part identifiers so intent survives mesh joining;
- visibility or coverage masks for allocation and gutter filling.

Use sufficient samples for stable output, record the render device and Blender version, and fail clearly when a required bake is missing. Supersample procedural paint when it materially improves line and edge quality, then downsample before export.

## Layered stylized paint

Build surface color from large to small:

1. **Material role:** a controlled base palette for timber, painted metal, stone, cloth, skin, foliage, glass, and other project roles.
2. **Large form:** deliberate top-to-bottom, inward-to-outward, or focal gradients that reinforce volume.
3. **Contact and cavity:** restrained darkening where parts meet and grime plausibly collects.
4. **Edge response:** highlights or wear on selected exposed edges, respecting the project's light direction or PBR model.
5. **Per-piece variation:** bounded value or hue differences across repeated planks, tiles, posts, scales, or panels.
6. **Localized history:** chips, rubbed handles, mud near the ground, rust around fasteners, moss on sheltered faces, or other story-specific marks.
7. **Fine detail:** grain, brushwork, pores, stitching, lettering, or patterns that remain useful at the target screen size.

Avoid global noise, uniform dirt washes, and random color variation. Each layer should have a visual purpose and a bounded strength.

## Texture quality checks

- Inspect the base level and multiple mip levels.
- Check UV gutters and chart bleed against high-contrast neighbors.
- View the asset at the gameplay camera, not only at texture-paint distance.
- Verify color space and channel packing after engine import.
- Compare repeated materials across the approved asset family.
- Check every visible side, underside, and animation-exposed surface.
- Test transparent and emissive materials against depth, fog, bloom, and sorting in the target renderer.

## Output report

Record texture dimensions, channel meaning, compression target, material count, visible texel-density statistics, stretch statistics, bake samples/device, color-space assignments, and exported filenames. The report makes surface regressions measurable across rebuilds.
