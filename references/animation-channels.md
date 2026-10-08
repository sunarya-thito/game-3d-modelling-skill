# Animation channels and authority

Use this reference when an asset animates anything beyond a single transform. Define every moving or changing property in `templates/animation-manifest.json` before creating keys or runtime code.

## Authority is per channel

Every channel has one authority:

- `blender_clip`: Blender owns the keys and the exporter must carry them into the selected interchange format.
- `runtime_engine`: the game owns the value. The GLB carries only the static owner when supported; a JSON sidecar carries the runtime parameter, timing intent, and fallback.

Do not key a runtime-owned property in Blender and also drive it in the engine. A hybrid asset is valid, but each property still has exactly one owner.

## Portability matrix

| Channel kind | Standard GLB expectation | Required evidence |
|---|---|---|
| Object translation, rotation, scale | Exportable as animation | Keys in Blender and after clean GLB re-import |
| Armature bone transforms | Exportable as skeletal animation | Bone action, skin, hierarchy, and re-imported clip |
| Shape-key weights / morph targets | Exportable as morph animation | Named target and animated weight after re-import |
| Arbitrary material or shader-node parameters | Not generally portable as standard GLB animation | Runtime sidecar and engine playback test |
| Emission strength or color animation | Treat as runtime-owned unless the exact exporter and importer extension is tested | Runtime parameter, fallback, and engine capture |
| UV offset, atlas frame, or image sequence | Not a standard portable GLB animation channel | Runtime sidecar and engine frame-selection test |
| Visibility | Not a standard portable GLB animation channel | Runtime sidecar; do not disguise it as zero scale without an explicit contract |
| Particles and effects | Engine/runtime behavior | Runtime sidecar, spawn contract, and engine capture |

GLB can store static materials and textures. That does not mean arbitrary Blender material, node, driver, UV, image-sequence, visibility, or particle animation survives export.

## Manifest requirements

Each channel records:

- stable channel id and kind;
- authority;
- property owner and property name;
- frame or time range;
- loop policy;
- root-motion policy;
- support level for the chosen export format;
- runtime parameter name for runtime-owned channels;
- safe fallback when animation is unavailable.

The validator rejects contradictory combinations. Standard transform and morph channels must use `blender_clip` with native format support. Material, texture-state, visibility, and effect channels must use `runtime_engine` and must not claim native GLB support.

`scripts/blender/animationkit.py` provides constructors for object, bone, morph, material, texture-state, visibility, and effect declarations. It also provides keying helpers for Blender-owned object, pose-bone, and morph properties. `tag_runtime_binding()` can add inspection metadata to a static Blender owner, but the JSON sidecar remains authoritative because custom-property export is not universally preserved.

## Blender implementation rules

Run animation scripts through Blender, not system Python. Start from a factory scene, set the frame range and frame rate explicitly, and create keys on the real property owner:

- object transforms live on the object;
- pose-bone transforms live on the armature object's action;
- morph weights live on the mesh's shape-key datablock, not on the object action.

Name actions deliberately. Use stable interpolation, avoid unintentional Euler wrapping, and record whether root motion belongs to the object, a bone, or the runtime controller.

For looping clips, inspect both the final sampled motion and the transition back to the first frame. Matching values alone may still produce a velocity discontinuity.

## Runtime implementation rules

The engine adapter should:

1. load the JSON sidecar that corresponds to the GLB;
2. resolve every `runtime_parameter` to one runtime property;
3. initialize the declared fallback before playback;
4. evaluate time and loop policy in one place;
5. apply values relative to the imported rest/static state;
6. fail clearly when an owner or parameter is missing;
7. capture representative and extreme states in the engine.

For texture atlases, the runtime contract should state atlas dimensions, frame ordering, filtering, and whether state is a discrete index or interpolated UV offset. For effects, state spawn ownership, local/world space, lifetime, and what happens when the effect system is unavailable.

## Executable example

From the repository root:

```bash
blender --background --factory-startup --python-exit-code 1 --python examples/animation-channels.py -- \
  --out-dir build/animation-channels
```

The example exports an object-transform clip and a morph-target clip to GLB. It then imports the GLB into a clean scene and verifies both animations. Emission and texture-atlas state remain runtime-owned and are written to `animation-manifest.json` beside the GLB.

Run the regression check with:

```bash
blender --background --factory-startup --python-exit-code 1 --python tests/blender_animation_checks.py
```

Passing this check proves that the tested Blender version round-trips the example object and morph channels. It does not prove that a target game engine imports them identically; engine verification remains required.
