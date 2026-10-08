# Text and image reference intake

Asset creation may begin from text, one or more images, or both. Convert every input into a structured brief before writing geometry code.

## Text-only input

Extract:

- player-facing purpose and one-sentence identity;
- category, scale, target camera, and platform;
- silhouette-defining features and important negative spaces;
- construction logic, materials, palette roles, and wear story;
- rigid or deforming motion requirements;
- explicit budgets and engine conventions;
- words that express taste but need a measurable interpretation.

Turn subjective phrases into observable tests. For example, “chunky” may imply a width-to-height range, broad bevel bands, few thin appendages, and recognition at a small pixel footprint. Mark interpretations as assumptions rather than facts.

When no visual reference exists, propose a small number of silhouette directions in words or quick review renders. Do not commit to surface detail before the user approves the primary form.

## Image-only input

An image is evidence, not a complete 3D specification. Record only what is visible:

- camera angle, likely projection, crop, and possible lens distortion;
- outer contour and major internal negative spaces;
- relative landmarks using normalized ratios rather than guessed real units;
- overlap and depth-order clues;
- repeated construction rhythm and symmetry/asymmetry;
- material classes, value groups, color roles, edge treatment, and detail frequency;
- visible contacts, pivots, seams, openings, and thickness clues;
- lighting and shadows that may be presentation rather than surface color.

Separate three columns mentally or in notes:

1. **Observed:** directly visible in the reference.
2. **Inferred:** plausible 3D interpretation supported by the image.
3. **Invented:** necessary design for unseen sides or missing mechanics.

Never present an inference as an observed fact. A single view cannot establish the back, underside, exact depth, topology, rig, or physical scale.

## Multiple images

Determine whether the images show the same design, variants, or only style references. Match landmarks across views and note conflicts caused by perspective, animation, or inconsistent source art. Give orthographic drawings priority for proportion measurements and photographs or renders priority for material response, unless the user says otherwise.

Create a view coverage table:

| Region | Directly shown | Inferred from | Confidence | Decision needed |
|---|---|---|---|
| Front | | | | |
| Back | | | | |
| Left/right | | | | |
| Top/bottom | | | | |
| Interior/occluded parts | | | | |

## Combined text and images

Treat the user's text as the authority for intended function and requested changes. Use images for observable form and style. List conflicts explicitly—for example, text requests an opening part while the image shows no hinge, or text requests a different palette from the reference.

Write two lists in the asset brief:

- **Must match:** identity, proportion landmarks, silhouette features, palette relationships, or mechanisms the result must preserve.
- **May change:** unseen construction, topology, exact micro-detail, or user-requested departures.

This prevents accidental literal copying when the user wanted only a style or shape cue, and prevents excessive invention when a specific design must be reproduced.

## When the active AI cannot see images

Do not model from filenames or alt text alone. Ask a vision-capable model or human to fill the reference-intake section of the asset brief with observations, uncertainties, and normalized measurements. The text-only modeling agent can then execute that brief and generate review evidence, but final visual approval still follows [review-capabilities.md](review-capabilities.md).

## Reference-to-model iteration

1. Normalize the brief and identify uncertainty.
2. Build only primary masses and silhouette.
3. Render the required reference-matching cameras plus standard review views.
4. Compare landmarks, contour, negative space, and contact—not surface decoration.
5. Correct the form before adding secondary construction.
6. Add surfaces, rig, and animation only after primary-form approval.
7. Review the exported GLB against both the brief and the permitted reference use.

Save the exact reference set or stable identifiers used for each review round so later changes are evaluated against the same target.
