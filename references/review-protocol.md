# Independent review protocol

## Reviewer role

Review should be adversarial but evidence-based. The reviewer did not author the asset, cannot edit it, and has no incentive to make it pass. The only verdicts are `PASS` and `REJECT`.

“Pass with notes” hides priority: if a note describes a defect worth fixing, reject the round.

Read [review-capabilities.md](review-capabilities.md) first. Only an image-capable reviewer that actually opens the evidence may issue the final verdict. A text-only agent may independently verify machine-readable gates, but it prepares a handoff rather than a visual verdict.

## Inputs

Read in this order:

1. project art contract;
2. asset brief and declared exceptions;
3. approved comparison assets in the same category;
4. all earlier verdicts for this asset;
5. current geometry and build reports;
6. current multi-view images and silhouette;
7. host-context or in-engine views when applicable.

Do not count an image as evidence unless it was actually opened and inspected.

## Re-run checks

Do not blindly trust the builder's report. Re-run affordable measurements from a clean state and investigate mismatches. At minimum check dimensions, origin/ground, triangles, parts, materials, joints, and validator status.

Understand validator blind spots. A graph-based floating check can pass a roof that touches only its trim while hovering above the wall. A vertex-inside test can miss a thin member passing through another mesh. Visual and targeted geometric probes remain necessary.

## Visual gates

Reject on any binding failure:

1. **Identity and silhouette:** wrong proportions, missing defining feature, unreadable 64 px silhouette.
2. **Construction:** undeveloped forms where the contract expects authored detail, implausible thickness, or featureless surfaces visible to the player.
3. **Contact:** gaps, clipping, burial, unsupported elements, attachments that do not follow anchors.
4. **Surface:** UV bleed, inconsistent density, flat or repetitive treatment, unintended seams, broken normals.
5. **Consistency:** scale, palette, edge treatment, detail frequency, or animation behavior differs from the approved family without justification.
6. **Integration:** wrong axis, origin, joint, material, transparency, collision, or LOD behavior in the target engine.

## Review packets

A useful packet includes consistent front, back, left, right, top, and three-quarter views; a 64 px silhouette; the machine reports; and context views. Add closeups only for a specific question. More images are not automatically better.

For worn, held, mounted, or embedded pieces, review the piece on its host and in a representative pose. For animated assets, include rest and stressed poses.

## Rounds

Write each verdict to a new immutable directory:

```text
reviews/<asset>/round_01/verdict.md
reviews/<asset>/round_01/contact-sheet.png
reviews/<asset>/round_01/silhouette.png
reviews/<asset>/round_01/report.json
```

Later rounds must re-check every gate, not only the last defect. Regressions and recurring defects are explicit rejection reasons.

Use [templates/review-verdict.md](../templates/review-verdict.md) for the decision record.
