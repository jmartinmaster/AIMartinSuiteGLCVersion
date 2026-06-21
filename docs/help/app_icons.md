# App Icon Reference

Production Logging Center uses a standardized icon pipeline so that the app
window, taskbar icon, and packaged executable (`.exe`) all display the same image.

---

## Icon Files

The app relies on the following files stored in the repository:

- `icon.ico`: The master icon file for Windows executables and taskbars.
- `icon-16.png`, `icon-24.png`, `icon-32.png`, `icon-48.png`, `icon-64.png`: PNG icon
  sizes used by the application window at runtime.
- `icon.png`: The master high-resolution source artwork. (Falls back to `icon.jpg`
  if the PNG version is missing).

---

## How to Change the App Icon

If you need to update the application's branding or icon design:

1. Replace `icon.png` in the repository with your new source artwork.
2. Run the `build.py` script.
3. The build script automatically regenerates `icon.ico` and all the smaller
   runtime PNG files so they stay in sync.
4. Package the application. The new icons will automatically embed in the
   output executable.

---

## Technical Notes

- Keep all filenames exactly as they are. Changing filenames requires updating
  path references in `app/app_platform.py` and `TheMartinSuite_GLC.spec`.
- Always update `icon.png` first and let the build script regenerate the rest,
  rather than editing the `.ico` or small PNGs manually.