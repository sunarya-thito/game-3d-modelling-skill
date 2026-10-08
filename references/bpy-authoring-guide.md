# Blender Python authoring guide

Use this guide when the agent must create or change an asset builder and cannot rely on an established project toolkit. It explains the Blender-specific implementation boundary; the asset brief and quality bar still decide what to build.

## The production loop

Do not attempt a finished asset in one uninspected script run. Use the same deterministic builder in progressively more expensive passes:

1. reset Blender and build primary geometry;
2. export metrics and render six clay views plus a small silhouette;
3. revise proportions, profiles, negative spaces, contacts, and bevel widths;
4. pass topology and contact gates;
5. unwrap and create the surface treatment;
6. build the rig and representative poses;
7. export GLB, import that GLB into a clean scene, and render it again;
8. inspect in the target engine.

The AI must look at the rendered evidence after each visual pass. A script completing without an exception proves execution, not quality.

## Start deterministically

Parse only arguments after `--`, resolve paths from `Path(__file__)`, and start from an empty factory scene:

```python
from pathlib import Path
import argparse, sys
import bpy

root = Path(__file__).resolve().parents[1]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--out", type=Path, required=True)
args = parser.parse_args(argv)
bpy.ops.wm.read_factory_settings(use_empty=True)
```

Set units, frame rate, color management, render engine, and random seeds explicitly when they affect output. Never depend on a user's startup file, current selection, active mode, or viewport state.

## Keep authored coordinates outside Blender

Represent profiles, paths, pivots, bounds, and joint axes in the game's declared coordinate frame. Convert once when creating Blender data. Apply the same conversion to mesh points, normals when authored, joint positions, camera directions, collision, and reported bounds.

Do not scatter axis swaps through builders. A mismatch that appears harmless on a static mesh often breaks animation, root motion, or engine-facing direction.

## Choose the right construction method

- **Loft:** primary bodies whose silhouette changes along an axis. Author at least a few meaningful cross-sections; varying only scale usually looks inflated or generic.
- **Sweep:** beams, handles, ropes, branches, horns, trim, and pipes. Carry a section along an authored path and control twist with a stable transported frame.
- **Revolve:** vessels, knobs, wheels, posts, and turned parts. Collapse a zero-radius station to one pole vertex; never create a ring of coincident vertices.
- **Extruded outline:** signs, blades, panels, leaves, brackets, and graphic shapes. Triangulate concave caps deliberately.
- **Surface or shell:** roofs, cloth, body panels, terrain, and fitted attachments. Sample the dependent trim and attachments from the same surface function.
- **Implicit or sculpted skin:** organic continuous bodies. Use only with a planned polygonization, reduction, normals, UV, and deformation strategy; do not treat overlapping spheres as a finished mesh.

The supplied [`meshkit.py`](../scripts/blender/meshkit.py) implements the first four starter operations. Build project-specific higher-level forms from those primitives rather than placing untouched Blender primitives until the outline happens to resemble the brief.

## Create mesh data without fragile UI state

Prefer `bpy.data.meshes.new`, `mesh.from_pydata`, and `bpy.data.objects.new`. Link the object to a known collection, validate polygon indices before creation, then use `bmesh` for normal recalculation and triangulation. Assign material indices only after material slots exist.

For every authored part, retain semantic metadata long enough to support:

- part-level cost reports;
- material or paint zones;
- rig ownership and weight rules;
- allowed contact pairs;
- review notes that can name the defective part.

Joining geometry must not erase its meaning. Store integer face attributes or maintain explicit face ranges before joining.

## Transforms, origins, and parenting

Build geometry at its contract location. Do not auto-center or lift it to make a gate pass. Apply scale before operations whose width is measured in object space. Set origins and joint pivots from authored values, not from the current bounding-box center unless the contract says so.

When parenting while preserving world placement:

```python
child.parent = parent
child.matrix_parent_inverse = parent.matrix_world.inverted()
```

For a rigid moving part, a useful hierarchy is `joint object -> visible mesh -> nested joint`. Put the joint object at the pivot, express the mesh transform relative to it, and test the declared minimum and maximum rotation.

## Bevels, normals, and readable highlights

Stylized hard-surface quality depends on intentional highlight bands. Select bevel widths from the gameplay camera and asset scale, not from a universal constant. Keep widths coherent within a material family, but let hero edges differ from minor seams.

Use a bevel modifier or authored chamfer only after scale is correct. Limit it by angle, weight, or vertex group so contact seams and thin parts are not destroyed. Set enough segments for the target camera, then inspect triangle cost. Recalculate normals after topology changes. Use smooth shading selectively and preserve intended hard transitions with sharp edges, split normals, or smoothing-by-angle appropriate to the pinned Blender version.

Reject bevels that cause self-intersection, erase a designed corner, or create a highlight wider than the form it describes.

## Contacts and negative space

Build contact-critical pairs from shared inputs. A handle and its brackets should use the same endpoints; a frame and opening should use the same outline; an accessory should be gated on a neutral host proxy.

Test more than vertex distance. Useful checks include connected components, bounding-box overlap, closest-surface distance, ray tests for unintended burial, ground/host reachability, and sampled surface penetration. Keep exceptions pair-specific with a maximum amount and reason.

## UV workflow with `bpy`

Finish geometry first. Create or activate a UV layer with `mesh.uv_layers.new`. Mark seams from semantic boundaries and hidden edges. UV operators require explicit edit-mode context:

```python
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=margin_fraction)
bpy.ops.object.mode_set(mode="OBJECT")
```

Convert desired pixel padding to a UV fraction using the final texture size. After packing, measure visible texel density and stretch from actual UV and world-space triangle areas. Iterate the texture size or chart scale until the measured result falls within the brief; requesting a scale is not measurement.

Allocate less space to hidden faces only when visibility evidence and the contract permit it. Check overlaps unless intentional stacking is declared. Re-run topology checks if modifiers are applied during unwrap.

## Surface construction

Choose the target shader before baking. Create images at explicit dimensions and color spaces, make the intended image node active for baking, and save generated pixels to disk before export.

A deterministic stylized painter should consume baked or computed evidence rather than global noise. Useful inputs are normals, ambient occlusion, curvature, position, visibility, part id, and material-zone id. Compose broad palette and form gradients first, then restrained cavities and edge response, bounded per-piece variation, localized wear, and finally small details. Supersample thin painted marks and downsample once.

Inspect the texture at full size and through mip levels. Fill UV gutters, verify alpha handling and channel color spaces, and confirm the exported material points to the saved image.

## Rigid rigs

Use objects or bones for whole pieces that must not deform. For each joint, require `name`, `parent`, `pivot`, local rotation axis, and allowed range. Topologically sort parents and fail on cycles or missing names.

Create parent joints before children. Place every joint at its authored pivot, attach the owned mesh while preserving world placement, and attach nested joints to their parent joint. Rotate each joint through its extremes and check gaps, clipping, ground penetration, and whether descendants follow.

Stable names are part of the engine API. Do not let Blender append `.001`; detect name collisions before creating objects.

## Skinned armatures

Create an armature data block and object, make it active, enter Edit Mode, and create bones parent-first. Give each bone a non-zero tail and deliberate roll; parent relationships alone do not define a stable local axis. Return to Object Mode before creating vertex groups.

Create one vertex group per deform bone with the exact same name. Assign rigid accessories wholly to one owner bone. For bending regions, compute weights from explicit anatomical or mechanical regions and chain distance, then normalize each vertex. Fail when a deforming vertex has no influence, a sum differs materially from one, or influence crosses an implausible region.

Add an Armature modifier to the mesh and set the armature as parent. Test the rest pose, a representative gameplay pose, and joint extremes. Look for volume collapse, pinching, candy-wrapper twist, detached parts, and changing ground contact. Correct weight logic or topology; do not hide failures with a single flattering pose.

## Actions and animation

Create one `bpy.data.actions` entry per exported clip. Attach it through `animation_data_create()` and key pose-bone or joint-object transforms with explicit frames. Set interpolation intentionally on the action's F-curves. Record frame range, frames per second, loop policy, and root-motion authority in a clip manifest.

For a loop, compare the evaluated transforms and visible contacts at the first and last sample. For locomotion or machinery, inspect arcs, spacing, acceleration, contact locking, overlap, and parent-child phase—not only whether keys exist. Bake constraints when the target format or engine requires it, then verify the exported clips by name after re-import.

Runtime-driven rigs should export a clean rest hierarchy without competing baked keys. Test that the engine can discover every required name and rotate it about the expected local axis.

## Deterministic review rendering

Create the world, camera, lights, and materials in code. Frame from evaluated world-space bounds and keep lens, background, resolution, color management, and light directions constant across assets. Render front, back, left, right, top, and three-quarter views plus a small black-on-white silhouette. Add pose renders for rigged assets.

Match the game's shading model closely enough that preview decisions transfer. An unlit or custom-shaded game asset should not be approved only under an attractive Blender studio light.

Render with an engine that works in the actual headless environment. If GPU or viewport-dependent rendering is unreliable, use a deterministic CPU path and record the engine and Blender version.

## Export and re-import

Select only the intended export hierarchy and make its root active. Export GLB with explicit options for axes, materials, normals, UVs, animation, and modifier application. Save a machine-readable manifest beside it.

Then reset to an empty scene and import the emitted GLB. Re-measure bounds, triangle count, materials, hierarchy, bone/joint names, and actions from the imported data. Render at least the three-quarter view and required poses from this re-imported object. Source-scene evidence cannot detect data lost by the exporter.

The final gate remains the target engine: camera, shader, animation controller, collision, LOD, and target-device performance.

## Minimum build report

Write JSON containing asset id, builder version or content hash, Blender version, coordinate contract, bounds, origin, triangle/part/material counts, texture files and sizes, measured texel density, topology/contact defects, rig type, joint or bone names, weight defects, clip manifest, export path, re-import results, review image paths, and deferred engine checks.
