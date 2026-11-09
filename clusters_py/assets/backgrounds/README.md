# Clusters tropical backgrounds

Eight saved PNG originals live in this folder. The game chooses one per new Play window, avoids the previous selection when possible, and keeps that choice while resizing.

`mobile/` contains 2160 × 3840 portrait exports for iOS and Android asset preparation. These are upscaled and center-cropped derivatives, not native 4K generations. Untouched source images are preserved here; see `manifest.json` for actual dimensions.

Rendering preserves aspect ratio using centered cover cropping. Keep the central puzzle area clear. Review cropping and sharpness on target devices; tablets and landscape screens may need wider artwork. These assets do not themselves port the current macOS Tk prototype to mobile.

Set `PLAY_NATURE_BACKGROUND = False` in `clusters_py/editor.py` to restore the plain cream Play screen.
