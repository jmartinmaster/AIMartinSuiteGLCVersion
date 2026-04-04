# App Icon Reference

The Martin Suite uses a fixed icon pipeline so the app window, taskbar icon, and packaged EXE all stay aligned.

## Hard-Coded Icon Files

The runtime icon paths are defined in `main.py`.

- `icon.ico`
  - Primary Windows icon used by the executable and `iconbitmap`.

- `icon-16.png`
- `icon-24.png`
- `icon-32.png`
- `icon-48.png`
- `icon-64.png`
  - PNG sizes used by `iconphoto` in the Tk window at runtime.

- `icon.png`
- `icon.jpg`
  - Source artwork kept in the repository as the master visual reference for future icon updates.

## Where Packaging Uses Them

The packaged EXE includes the runtime icon assets through `TheMartinSuite_GLC.spec`, and packaged builds now use a versioned EXE name such as `TheMartinSuite_GLC_v1.2.4.exe`.

- `datas` bundles `icon.ico` and the size-specific PNG files.
- `icon=['icon.ico']` sets the Windows executable icon.

## How To Change The App Icons

1. Start from `icon.png` or `icon.jpg` as the source artwork.
2. Export a Windows-compatible `icon.ico` for the executable.
3. Export the PNG sizes used by the runtime window icon set:
   - `icon-16.png`
   - `icon-24.png`
   - `icon-32.png`
   - `icon-48.png`
   - `icon-64.png`
4. Replace the files in the repository root with the same names.
5. Rebuild with `build.py` so the updated icon set is embedded into the packaged EXE.

## Notes

- Keep the filenames unchanged unless you also update the icon constants in `main.py` and the `datas` plus `icon=` entries in `TheMartinSuite_GLC.spec`.
- If the EXE icon changes but the running app window does not, make sure the size-specific PNG files were also updated.
- If the window icon changes but the EXE icon does not, rebuild so PyInstaller picks up the new `icon.ico`.