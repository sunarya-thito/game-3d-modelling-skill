# Executable surface-production track

This clean-room implementation turns the surface guidance into a small runnable
path. It is tested with Blender 4.2.5 LTS and uses only Blender and Python's
standard library. It does not borrow assets, textures, code or constants from a
private game project.

The implementation is [surfacekit.py](../scripts/blender/surfacekit.py). The
[example](../examples/textured-surface-workflow.py) builds three authored paint
samples, paints an atlas, exports GLB, imports that GLB into an empty scene,
checks its surfaces, and renders the imported shader graph with CPU Cycles.
These are material technique samples, not an independently approved hero asset.

## Run

From the repository root, with Blender 4.2 available as `blender`:

```bash
blender --background --factory-startup --python-exit-code 1 --python examples/textured-surface-workflow.py -- --out-dir build/textured-surface
blender --background --factory-startup --python-exit-code 1 --python tests/blender_surface_checks.py
```

Use the documented explicit executable form on Windows when Blender is not on
PATH. No developer-specific executable path is embedded in this implementation.
The example accepts `--texture-size` (default 1024) and `--skip-render`.

Outputs include `albedo.png`, `roughness.png`, `textured-surface.blend`,
`textured-surface.glb`, `surface-report.json` and `imported-surface.png`.
The regression uses a temporary directory and removes its generated files.

## UV creation and measurable metrics

`triangle_atlas(objects, texture_size=512, gutter_px=8)` requires finalized,
triangulated Object-mode meshes with single-user mesh data and no active modifiers. It leaves geometry
unchanged and assigns one UV triangle to each rectangular atlas cell. It measures
world-space edge lengths, including object scale, and applies one common scale.
The resulting triangles have uniform texel density and no directional stretch.
Cells use deterministic height-sorted shelf packing and a common scale search;
short or narrow triangles receive correspondingly smaller cells. The generated
`SurfaceUV` layer is made active for editing and rendering. Use a single UV layer when relying
on this example's GLB surface gate, which requires `TEXCOORD_0`.

Every triangle is inset at least `gutter_px + 1` pixels from its cell boundary.
`paint_atlas` fills the whole cell using the nearest triangle-edge sample outside
the triangle. Thus gutters never borrow colors from another part. This is an
explicit margin guarantee for this construction, not a claim that arbitrary UV
maps have been checked for overlap or padding. Texture filtering whose footprint
exceeds the gutter can still cross a cell boundary; target-engine mipmaps and
anisotropic filtering remain separate acceptance checks.

`smart_unwrap` is an alternative wrapper around Blender Smart UV Project. It
establishes selection, active object, edit mode and selected faces explicitly,
then restores the prior Object-mode selection and active object. It requests a
margin in texture-pixel units but does not certify the achieved margin. It does
not restore mesh component selection, and callers must begin in Object mode.
The atlas painter consumes the deterministic atlas plan, not arbitrary smart UVs.

`uv_report(obj, width, height=None)` measures:

- total world-space and normalized UV triangle area;
- minimum, maximum and area-weighted mean density in pixels per world unit;
- directional stretch as the singular-value ratio of the world-to-pixel Jacobian;
- missing UVs, degenerate world/UV triangles, nonfinite UVs and out-of-range UVs.

Density is `sqrt(UV_area * width * height / world_area)`. Stretch 1 means no
directional distortion; it does not prove that density is suitable for a game.
`require_uv_metrics` enforces caller-supplied density and stretch limits and fails
on the listed defects. It never silently repairs UVs or changes the budget.

## Paint and image color spaces

`paint_atlas(plan, destination, painter, color_space="sRGB")` samples the callback
with `(world_position, world_normal, piece_index)`. The callback returns four
LINEAR color components for an sRGB image, or four unencoded data components for
a Non-Color image. Piece indices follow the caller's object order; keep that
order stable. Colors are extended per cell. The helper uses no random generator.

The example layers a broad vertical pigment gradient, restrained base contact
darkening, exposed-edge pigment, deterministic per-piece brush variation, and
localized cream insignia. These are authored pigment effects, not baked lighting
or measured ambient occlusion. A separate roughness map varies at the base and
across pieces. Position-aware painting stays coherent across triangle seams;
normal-dependent layers can intentionally differ across hard edges.

`save_rgba_png` writes deterministic RGBA8 PNG using `struct` and `zlib`, then
loads it into Blender. It explicitly converts linear RGB to sRGB for color maps;
alpha is always linear. Non-Color maps bypass that encoding. No display/view
transform is baked into either image. Values are clamped to [0, 1]; nonfinite
values fail. HDR, 16-bit maps and photographic texture synthesis are not supported.

## Principled material hookup

`principled_textured` creates an exporter-friendly Principled graph:

| Input | Image interpretation | Shader connection |
|---|---|---|
| Albedo | sRGB | Image Color to Base Color |
| Roughness | Non-Color | Separate Color green to Roughness |
| Metallic | Non-Color | Separate Color blue to Metallic |
| Tangent normal | Non-Color | Image RGB through Normal Map to Normal |

Roughness and metallic images can be grayscale, or can share a packed image with
green/blue channels. An albedo image cannot also serve a data role because an
image datablock has one color-space setting. The normal connection is supplied,
but the example does not generate or bake a normal map. AO, alpha blending,
transmission, material animation and custom engine shaders are outside this
helper's supported surface path.

## Export, re-import and tests

The example uses the existing `write_glb`, then `glb_surface_report` examines the
actual emitted JSON chunk. It requires a UV attribute and valid base-color texture
reference on every primitive, valid image references and embedded PNG/JPEG images.
With `require_data_texture=True`, it also requires a metallic/roughness texture.
This focused gate is not a complete glTF validator or an image-pixel equivalence
test.

After clean-scene import, `imported_surface_report` checks UV metrics and follows
links upstream from Principled Base Color and, when required, Roughness. The
referenced images must contain pixels, have the requested dimensions, and use the
correct color spaces. The example compares source and imported triangle counts,
world area and UV area. The render uses the imported material nodes, rather than
Workbench material swatches.

The regression checks deterministic UVs and PNG bytes, world-scale density,
stretch, declared atlas clearance, exact sRGB/data encoding for 18% gray, exported
and imported texture links, and the explicit-context unwrap path. Negative cases
must reject missing UVs, zero-area UVs, insufficient atlas space, density/stretch
violations, conflicting color/data image roles and missing albedo links.

## Deliberate limitations

- Triangle cells waste atlas area and create many seams. This is an understandable
  baseline with measurable gutters, not optimal chart packing or seam placement.
- UV reports operate on finalized mesh data. They do not evaluate deformation,
  arbitrary modifiers, stacked islands, overlap, or artist-defined visibility.
- The painter takes one sample per pixel. Very fine marks need supersampling or a
  larger texture; it does not promise anti-aliased subpixel paint.
- There is no AO/normal/curvature bake, automatic wear inference, texture baking
  from arbitrary Blender shader graphs, or image-reference interpretation.
- Source surfaces and their GLB import are checked. Shader equivalence, engine
  compression, mip behavior, platform performance and independent art approval
  remain outside this executable demonstration.
