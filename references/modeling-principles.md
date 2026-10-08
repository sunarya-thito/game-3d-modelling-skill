# Modeling principles

## Form hierarchy

Work in this order:

1. silhouette and overall proportions;
2. primary masses and negative spaces;
3. contact and load-bearing relationships;
4. secondary forms that explain construction;
5. small geometry that survives the target camera;
6. painted detail for features too small to model reliably.

A detailed texture cannot rescue an anonymous silhouette. Conversely, tiny geometry that occupies less than a few screen pixels often becomes noise.

## Authored procedural form

Procedural does not mean random. Prefer deterministic inputs that a reviewer can name and adjust:

- cross-sections placed along a path;
- thickness curves with explicit control points;
- roof or panel surfaces sampled from one shared function;
- profiles revolved by a fixed segment count;
- outlines extruded into slabs;
- cages developed through inset, extrude, bevel, and limited booleans.

Use randomness only when the contract calls for it, seed it, and keep it out of contact-critical geometry. Never hide poor construction behind a global vertex-noise pass.

## Shared geometry relationships

When an attachment belongs to an anchor, derive them from the same geometry source. Examples:

- fascia and gable read the roof's top and underside curves;
- a strap samples the box surface it wraps;
- a window frame follows the wall opening and reveal;
- a worn item is built and reviewed against the host surface;
- debris is settled against measured support geometry.

This prevents the common procedural failure where individually plausible parts visibly separate when assembled.

## Parts and topology

Choose part boundaries that reflect construction, material, animation, damage, or review needs. Avoid both extremes: a heap of undeveloped primitives and one featureless continuous skin.

Closed hard-surface parts should have consistent outward winding, no accidental boundary edges, no zero-area faces, and stable triangulation. Use booleans for genuine cuts and openings, not as the only way to discover the silhouette.

## Contact and rest

Place contact from surfaces, not from guessed center heights. For loose objects, verify that the center of mass projects over the support region and that the object is not balanced on a visually implausible point. Build supports before objects that depend on them.

Treat “floating” broadly: any surfaces intended to meet but separated by a visible gap are floating even if each part touches something else.

## Coordinate discipline

Define project space once. Convert to Blender space at a narrow boundary. Keep builder inputs, asset briefs, joint pivots, and size reports in project coordinates so the meaning of “up,” “front,” and “ground” remains stable.
