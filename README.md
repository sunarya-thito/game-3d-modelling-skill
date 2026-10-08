# Game-Ready 3D Asset Pipeline

A provider-neutral [Agent Skill](https://agentskills.io/home) for creating stylized game assets with Blender Python.

The skill guides an AI through an explicit production loop:

```text
contract → model → geometry gate → surface → rig → animate
         → export → re-import → review → engine integration
```

It is intended for game development, not isolated beauty renders or manual-only Blender tutorials. It covers static props, buildings, rigid articulated assets, and skinned assets with exported or engine-driven animation.

## What the skill teaches

- turn art direction into a measurable asset contract;
- convert text prompts, image references, or combined input into a structured brief;
- build deliberate silhouettes from profiles, paths, sections, outlines, and shared surfaces;
- use Blender headlessly and reproducibly from Python;
- preserve semantic part and surface intent through modeling and export;
- stop geometry defects before expensive UV, bake, and paint work;
- construct rigid joint hierarchies or skinned armatures with deterministic weights;
- author exported actions or a stable rest rig for runtime-driven motion;
- create consistent multi-view, silhouette, and pose evidence;
- route visual approval safely when the current AI has weak or no image recognition;
- audit the emitted GLB after importing it into a clean Blender scene;
- verify scale, materials, hierarchy, animation, collision, LOD, and performance in the game engine.

The target is polished production art, not blockout geometry. The quality bar is defined in [references/quality-bar.md](references/quality-bar.md) and is carried through form, surfacing, rigging, animation, review, and engine acceptance.

The bundled example assets are executable technique tests. They are not the visual benchmark, and this README intentionally contains no prototype screenshots. Add screenshots only after a separately authored, finished example passes the full quality bar.

## Install the skill

Keep the entire repository together. `SKILL.md` depends on `references/`, `scripts/`, `templates/`, and `examples/`.

The GitHub repository is named `game-3d-modelling-skill`. The installed Agent Skill remains `3d-modelling-skill`; repository names and skill identifiers do not need to match.

### Claude Code

Claude's short installer does not require GitHub CLI:

```bash
npx skills add https://github.com/sunarya-thito/game-3d-modelling-skill --skill 3d-modelling-skill
```

For a project-local manual installation, clone or copy the repository to `.claude/skills/3d-modelling-skill/`. For a personal installation available across projects, use `~/.claude/skills/3d-modelling-skill/`.

### Claude.ai

Download the repository ZIP. In Claude.ai, open **Settings → Features**, find custom Skills, and upload the ZIP. The archive must keep `SKILL.md` and its supporting folders together.

### OpenAI Codex, Cursor, GitHub Copilot, and other coding agents

The [GitHub CLI skill installer](https://cli.github.com/manual/gh_skill_install) supports many coding agents. Install [GitHub CLI](https://cli.github.com/) once, then choose the matching command:

```bash
# OpenAI Codex
gh skill install sunarya-thito/game-3d-modelling-skill SKILL.md --agent codex --scope user

# Cursor
gh skill install sunarya-thito/game-3d-modelling-skill SKILL.md --agent cursor --scope user

# GitHub Copilot
gh skill install sunarya-thito/game-3d-modelling-skill SKILL.md --agent github-copilot --scope user

# Claude Code, if you prefer GitHub CLI
gh skill install sunarya-thito/game-3d-modelling-skill SKILL.md --agent claude-code --scope user
```

`--scope user` makes the skill available across projects. Run the command from a game repository with `--scope project` when the skill should be local to that project. Update GitHub CLI-managed skills with `gh skill update --all`.

### Gemini CLI

Gemini CLI has its own installer:

```bash
gemini skills install https://github.com/sunarya-thito/game-3d-modelling-skill
```

Use `--scope workspace` for the current project only. While developing a local checkout, use `gemini skills link /path/to/3d-modelling-skill`. Reload skills in an active session with `/skills reload`.

### Gemini Apps

Open the **Skills** page, choose **Upload**, select the repository ZIP or extracted folder, review it, and choose **Create**.

### Manual locations

If an installer is unavailable, place the complete `3d-modelling-skill` folder at the appropriate location:

| Client | Personal | Project-local |
|---|---|---|
| OpenAI Codex | `~/.codex/skills/3d-modelling-skill/` | `.codex/skills/3d-modelling-skill/` |
| Claude Code | `~/.claude/skills/3d-modelling-skill/` | `.claude/skills/3d-modelling-skill/` |
| Cursor | `~/.agents/skills/3d-modelling-skill/` | `.agents/skills/3d-modelling-skill/` |
| GitHub Copilot | `~/.agents/skills/3d-modelling-skill/` | `.agents/skills/3d-modelling-skill/` |
| Gemini CLI | `~/.agents/skills/3d-modelling-skill/` | `.agents/skills/3d-modelling-skill/` |

The destination folder must directly contain `SKILL.md`. Restart the client or reload its skills after copying.

### Any AI without Agent Skills support

Attach the full repository if the client accepts folders. Otherwise, attach `SKILL.md` and the files it selects for the current task:

- asset creation: `references/reference-intake.md`, `references/quality-bar.md`, `references/modeling-principles.md`, `references/bpy-authoring-guide.md`, `references/surface-pipeline.md`, and `templates/asset-brief.md`;
- Blender setup: `references/blender-headless.md`;
- Blender implementation: `references/blender-helper.md`, `scripts/blender/meshkit.py`, and `scripts/blender/rigkit.py`;
- asset review: `references/review-capabilities.md`, `references/review-protocol.md`, and `templates/review-verdict.md`;
- pipeline design or repair: `references/pipeline.md` and `references/art-contract.md`.

The instructions do not rely on a particular AI provider.

### Verify the skill installation

Ask the agent:

```text
Read the 3d-modelling-skill. List the files required for authoring an asset,
then explain which Blender Python guide and helper modules you would use.
```

A correct installation lets the agent open the linked references, [scripts/blender/meshkit.py](scripts/blender/meshkit.py), [scripts/blender/rigkit.py](scripts/blender/rigkit.py), and the files under [examples/](examples/). The skill tells the agent to stop and report an incomplete installation if a selected file is missing.

## Install Blender for headless work

Install a stable or Long-Term Support build from the official [Blender download page](https://www.blender.org/download/). The Windows installer or portable ZIP, macOS application bundle, and Linux archive/package are all suitable. Pin one tested Blender major/minor version for a production project.

Make the executable available as `blender` on `PATH`, or call it by its full path:

```text
Windows portable: tools/blender/blender.exe
macOS:            /Applications/Blender.app/Contents/MacOS/Blender
Linux/PATH:       blender
```

Verify it with `blender --version`.

Every repository command uses the same reliable flags:

```bash
blender --background --factory-startup --python-exit-code 1 --python SCRIPT.py -- SCRIPT_ARGUMENTS
```

- `--background` runs without the Blender UI;
- `--factory-startup` ignores personal startup-scene changes;
- `--python-exit-code 1` makes Python failures fail the process;
- arguments after `--` belong to the script.

For PowerShell syntax, executable discovery, version pinning, and troubleshooting, read [references/blender-headless.md](references/blender-headless.md).

## Run the executable examples

Run commands from the repository root. Generated files go under the gitignored `build/` directory.

### Geometry helper smoke test

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python examples/stylized-crate.py -- --out build/stylized-crate.glb
```

This exercises multi-part loft construction, topology checks, materials, coordinate conversion, and selected-hierarchy GLB export.

### Rigid joint hierarchy and action

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python examples/rigid-joint-animation.py -- --out build/rigid-joint-animation.glb
```

This creates named nested pivots, attaches rigid meshes without changing their world placement, authors an action, and exports the hierarchy.

### Skinned armature, weights, and action

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python examples/skinned-chain-animation.py -- --out build/skinned-chain-animation.glb
```

This creates bones parent-first, assigns normalized vertex weights, fails on weight defects, authors a loop, and exports the skinned mesh.

### Audit the emitted GLB

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python examples/audit-glb.py -- \
  --input build/skinned-chain-animation.glb \
  --report build/skinned-chain-audit.json
```

The audit starts from a clean scene and reports imported bounds, triangle count, materials, objects, armatures, bones, and actions. It measures the shipping artifact rather than trusting the source scene.

### Render review views from the emitted GLB

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python examples/render-review.py -- \
  --input build/rigid-joint-animation.glb \
  --out-dir build/rigid-review
```

The renderer writes consistent three-quarter, front, back, left, right, and top views plus a 64 px silhouette. These outputs are review evidence for the technical example, not approved portfolio screenshots.

## Production workflow

| Stage | Required result | Stop when |
|---|---|---|
| Intake and contract | Structured text/image observations, uncertainties, units, axes, budgets, surface roles, rig mode, animation authority, views, target platform | The reference is unseen or requirements are ambiguous |
| Form | Authored silhouette, primary masses, negative spaces, contacts, semantic parts | The asset still reads as undeveloped primitives |
| Fast gate | Bounds, counts, topology/contact report, clay views, small silhouette | Any binding geometry check fails |
| Surface | Measured UV density, padding, bake evidence, layered texture, material manifest | Geometry changed or texture checks fail |
| Rig | Named hierarchy, pivots, axes, weights, rigid attachments | Hierarchy, weights, or extreme poses fail |
| Animate | Exported clips or runtime motion contract with representative pose tests | Timing, loop, contact, clipping, or authority is wrong |
| Export | Source scene, GLB, textures, build report, content identity | Export is incomplete |
| Re-import | Shipping-artifact counts, hierarchy, materials, bones/joints, clips, review renders | Source and imported results disagree |
| Independent review | Immutable `PASS` or `REJECT` from a reviewer that opened the images | Images cannot be inspected or any useful defect note remains |
| Engine integration | Correct camera, shader, animation, collision, LOD, and target-device behavior | Production context differs from the contract |

The central optimization is a two-speed loop: shape and contact failures are found before unwrap, bake, paint, and final export. Preview and release builds must call the same asset builder.

## Modeling, rigging, and animation choices

Use a skinned armature when one continuous surface must bend. Use named rigid joints when whole pieces rotate or translate, such as lids, doors, wheels, machinery, tools, sails, or modular parts. Nested joints must carry their descendants.

Choose one animation authority for each channel:

- **exported action:** Blender owns the keys and the GLB contains the clip;
- **runtime-driven:** the GLB contains a stable rest hierarchy and the game owns motion;
- **hybrid:** the contract explicitly separates baked and runtime-controlled channels.

The asset brief must supply engine conventions, budgets, art direction, and motion authority.

## How the code is organized

The skill separates creative intent from reusable mechanics:

- an asset brief defines recognition, dimensions, budgets, surfaces, rig, motion, and evidence;
- a registry maps an asset id to its builder and measurable contract;
- geometry helpers implement reusable loft, sweep, revolve, outline, and conversion operations;
- rig helpers implement hierarchy ordering, pivots, armatures, and weight validation;
- asset builders contain the authored profiles, proportions, contacts, and semantic ownership;
- validators observe and report; they do not silently move or repair the asset;
- preview, full build, review, and export consume the same builder.

The concrete Blender Python boundary is documented in [references/bpy-authoring-guide.md](references/bpy-authoring-guide.md). It covers deterministic scene setup, data API versus operators, transforms, origins, bevels and normals, contacts, UV work, surfaces, rigid rigs, skinned rigs, actions, review rendering, export, and clean-scene re-import.

## Example requests

```text
Use the 3d-modelling-skill to create a production brief and a headless Blender
builder for a stylized game prop. Run the fast gate and show me the review views
before starting UV or texture work.
```

```text
Use the 3d-modelling-skill to add a rigid articulated hierarchy and one exported
animation clip to this asset. Audit the emitted GLB in a clean scene.
```

```text
Use the 3d-modelling-skill to diagnose this skinned character's weighting and
looping animation. Review rest, representative, and extreme poses.
```

```text
Use the 3d-modelling-skill to audit our existing asset pipeline. Do not change
files; report the earliest gate that should have caught each defect.
```

## Repository map

```text
SKILL.md                           Agent entry point and mode routing
references/art-contract.md        Measurable global and per-asset constraints
references/reference-intake.md   Text, image, and combined-reference analysis
references/pipeline.md            Production pipeline architecture
references/quality-bar.md         Production acceptance rubric
references/modeling-principles.md Form, construction, contact, and coordinates
references/bpy-authoring-guide.md Concrete Blender Python implementation guide
references/surface-pipeline.md     UV, bake, paint, and texture checks
references/blender-headless.md    Blender installation and headless commands
references/blender-helper.md      Geometry helper API
references/review-protocol.md     Independent visual and technical review
references/review-capabilities.md Vision, weak-vision, and text-only review routes
templates/asset-brief.md          Per-asset contract template
templates/review-verdict.md       Immutable PASS/REJECT record
scripts/blender/meshkit.py        Geometry, topology, material, and GLB helpers
scripts/blender/rigkit.py         Rigid hierarchy, armature, and weight helpers
scripts/validate_repo.py          Agent Skill structure and link validator
examples/stylized-crate.py        Multi-part geometry smoke test
examples/rigid-joint-animation.py Rigid hierarchy and exported action
examples/skinned-chain-animation.py Skinned rig, weights, and action
examples/audit-glb.py             Clean-scene GLB report
examples/render-review.py         Deterministic multi-view renderer
tests/blender_meshkit_checks.py   Blender geometry and GLB regression checks
tests/test_validate_repo.py       Repository validator tests
```

## Validate the repository

Python 3.10 or newer is sufficient for repository checks:

```bash
python scripts/validate_repo.py .
python -m unittest discover -s tests -v
```

Run the Blender integration checks with the production Blender version:

```bash
blender --background --factory-startup --python-exit-code 1 \
  --python tests/blender_meshkit_checks.py
```

The validator checks Agent Skill metadata, linked local files, unfinished placeholders, UTF-8 text, and portable paths. The Blender test exercises loft, sweep, pointed revolve, concave outline extrusion, material validation, topology inspection, GLB export, and clean-scene re-import.

## Requirements and boundaries

- Any AI that supports Agent Skills or can read the attached Markdown and Python files.
- Python 3.10+ for repository validation.
- Blender 4.x for the bundled scripts; pin the exact tested major/minor release in a real project.
- A target game engine for final integration acceptance.

The skill intentionally does not hardcode an AI provider, Blender executable, render engine, game engine, triangle budget, texture size, or art style. Those belong in the target project's contract.
