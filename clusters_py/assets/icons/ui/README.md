# Prepared display icons

These transparent PNGs are derived from the original artwork in the parent folder.
The originals are retained unchanged. Play loads these images at native pixel size;
it does not use Tk's pixel-skipping subsample or integer zoom operations.

Regenerate on macOS from the repository root:

```sh
swift -module-cache-path /tmp/hui-pu-swift-cache clusters_py/tools/prepare_ui_icons.swift clusters_py/assets/icons
```

The generator uses CoreGraphics high-quality interpolation with premultiplied alpha.
Wordmarks are trimmed to their artwork bounds and scaled so the lowercase “u”
bodies have the same width and height, using Hui as the reference and excluding
Pu's macron. Source alpha-component bounds are recorded in the generator. Status
images occupy 176px square canvases. All five playing frames share the same crop
around their original common center, preserving leaf positions across frames.
