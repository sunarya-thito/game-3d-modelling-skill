"""Build and audit a small game prop with the bundled Blender helper.

Run from the repository root:
  blender --background --factory-startup --python-exit-code 1 \
    --python examples/stylized-crate.py -- --out build/stylized-crate.glb
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "blender"))

from meshkit import (
    MeshDraft,
    Y_UP_FRAME,
    add_profile_loft,
    create_mesh_object,
    inspect_topology,
    make_preview_material,
    start_empty_scene,
    write_glb,
)


def upright_plank(name, centre_x, centre_z, width, height, depth, lean=0.0):
    half_width = width * 0.5
    half_depth = depth * 0.5
    sections = []
    for y, width_scale, depth_scale, bow in (
        (0.0, 0.96, 0.88, 0.000),
        (height * 0.52, 1.03, 1.08, 0.018),
        (height, 0.94, 0.92, -0.010),
    ):
        x = centre_x + lean * (y / height - 0.5) + bow
        z = centre_z
        across = half_width * width_scale
        deep = half_depth * depth_scale
        corner = min(across, deep) * 0.28
        sections.append(
            [
                (x - across + corner, y, z - deep),
                (x + across - corner, y, z - deep),
                (x + across, y, z - deep + corner),
                (x + across, y, z + deep - corner),
                (x + across - corner, y, z + deep),
                (x - across + corner, y, z + deep),
                (x - across, y, z + deep - corner),
                (x - across, y, z - deep + corner),
            ]
        )
    draft = MeshDraft(name)
    add_profile_loft(draft, sections)
    return draft


def cross_plank(name, centre_y, centre_z, width, height, depth):
    half_width = width * 0.5
    half_height = height * 0.5
    sections = []
    for x, height_scale, depth_scale in (
        (-half_width, 0.92, 0.94),
        (0.0, 1.06, 1.08),
        (half_width, 0.95, 0.90),
    ):
        tall = half_height * height_scale
        deep = depth * 0.5 * depth_scale
        sections.append(
            [
                (x, centre_y - tall, centre_z - deep),
                (x, centre_y + tall, centre_z - deep),
                (x, centre_y + tall, centre_z + deep),
                (x, centre_y - tall, centre_z + deep),
            ]
        )
    draft = MeshDraft(name)
    add_profile_loft(draft, sections)
    return draft


def arguments():
    values = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "build" / "stylized-crate.glb")
    return parser.parse_args(values)


def main():
    options = arguments()
    start_empty_scene()
    timber = make_preview_material("Timber", (0.43, 0.22, 0.08, 1.0), roughness=0.78)

    drafts = []
    for index, x in enumerate((-0.70, -0.35, 0.0, 0.35, 0.70)):
        drafts.append(
            upright_plank(
                f"FrontPlank{index}",
                x,
                -0.38,
                0.30,
                1.25,
                0.13,
                lean=(index - 2) * 0.012,
            )
        )
        drafts.append(
            upright_plank(
                f"BackPlank{index}",
                x,
                0.38,
                0.30,
                1.25,
                0.13,
                lean=(2 - index) * 0.010,
            )
        )
    drafts.extend(
        [
            cross_plank("FrontRailLow", 0.28, -0.47, 1.75, 0.19, 0.12),
            cross_plank("FrontRailHigh", 0.98, -0.47, 1.75, 0.19, 0.12),
            cross_plank("BackRailLow", 0.28, 0.47, 1.75, 0.19, 0.12),
            cross_plank("BackRailHigh", 0.98, 0.47, 1.75, 0.19, 0.12),
        ]
    )
    for index, z in enumerate((-0.31, 0.0, 0.31)):
        drafts.append(cross_plank(f"FloorPlank{index}", 0.10, z, 1.62, 0.13, 0.26))

    objects = [create_mesh_object(draft, (timber,), basis=Y_UP_FRAME) for draft in drafts]
    report = {obj.name: inspect_topology(obj) for obj in objects}
    failures = {
        name: result
        for name, result in report.items()
        if result["boundary_edges"] or result["nonmanifold_edges"] or result["degenerate_faces"]
    }
    if failures:
        raise SystemExit("topology audit failed:\n" + json.dumps(failures, indent=2))
    output = write_glb(objects, options.out)
    print(json.dumps({"output": str(output), "parts": len(objects), "topology": report}, indent=2))


if __name__ == "__main__":
    main()
