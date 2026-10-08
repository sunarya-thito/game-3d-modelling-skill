# Review capability protocol

Visual review is a required production gate, but not every AI can inspect images well enough to perform it. Determine the reviewer route before opening a round.

## Capability levels

### Native visual review

The agent can open the actual PNGs at useful resolution, zoom or crop when needed, compare multiple views, and reason about visible geometry and surfaces. It may issue `PASS` or `REJECT` after completing the full review protocol.

### Tool-assisted visual review

The agent can inspect images through an image-viewing or computer-use tool but may receive reduced resolution. Improve the packet before reviewing:

- render one asset per frame against a plain contrasting background;
- use identical camera framing across rounds;
- include a solid silhouette at the gameplay footprint;
- provide separate views rather than only a dense contact sheet;
- add targeted closeups for contacts, UV seams, deformation, or clipping;
- include rest, representative, and extreme poses as separate images;
- provide an approved comparison asset with the same camera when rights allow;
- use neutral filenames and a manifest that states which question each image answers.

The agent must say which images it actually opened. If resolution or tooling prevents a binding judgment, route that gate onward rather than guessing.

### No image input

A text-only agent cannot approve visual gates. It should still do useful work:

1. rebuild from a clean Blender state;
2. run topology, bounds, budget, UV, material, hierarchy, weight, action, and re-import checks;
3. generate deterministic multi-view images, a silhouette, pose views, and machine reports;
4. compare numeric results to the asset contract;
5. create a concise handoff listing passed machine gates and unresolved visual questions;
6. request review from a vision-capable agent or human.

Its status is `VISUAL REVIEW REQUIRED`, not `PASS`. Do not convert the absence of visible evidence into an approval.

## What automation can and cannot prove

Machine gates can prove facts such as file presence, topology counts, bounds, origin, triangle/material budgets, texture dimensions, UV density, hierarchy names, normalized weights, exported actions, and source-versus-GLB consistency.

They cannot by themselves prove that:

- the silhouette is appealing or recognizable;
- proportions and negative spaces match the art direction;
- bevels, highlights, and detail frequency feel intentional;
- contacts look plausible despite passing distance tests;
- paint, wear, or color hierarchy looks authored;
- deformation preserves appealing volume;
- animation timing, weight, arcs, overlap, and personality feel correct.

Those remain visual judgments.

## Handoff format

Use this structure when the current agent cannot finish visual review:

```text
STATUS: VISUAL REVIEW REQUIRED
Asset/build id:
Machine gates passed:
Machine gates failed:
Evidence files:
Views and poses rendered:
Visual questions to decide:
Approved comparison to use:
Engine-context evidence still needed:
```

The next reviewer reads the same immutable packet. It does not need to rerun expensive builds unless the report is incomplete or inconsistent.
