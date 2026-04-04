# AIMartinSuiteGLCVersion

The Martin Suite is a desktop production support application for GLC operators. It is built with Python, Tkinter, and ttkbootstrap and is packaged for Windows with PyInstaller.

## Two Working Modes

The project currently operates in two different forms:

- Source / Python mode: the app is run from the Python files in the repository.
- Packaged EXE mode: the app is run from the built standalone Windows executable.

These two forms do not have identical behavior. The Python version has access to the repository files and build tooling, while the EXE version is a packaged release with a more limited update path.

## Shared Capabilities

- Production Log workflow with draft save and reopen support.
- Excel export and import support for production sheet work.
- Layout Manager and Rate Manager tools.
- Settings management for export paths, theme selection, and production defaults.
- In-app help viewer and About screen.
- Bundled GPL license access from Help Center and About.
- Theme support with readability overrides.

## Source / Python Mode

- Runs directly from the repository source files.
- Can use the local project structure, docs, templates, and module files directly.
- Can be rebuilt locally with `build.py` and PyInstaller.
- Can be used to develop, test, and package new EXE releases.
- The Update Manager can check repository versions, but source-mode executable updates are still expected to be handled by rebuilding manually.

## Packaged EXE Mode

- Runs as a standalone Windows executable built by PyInstaller.
- Intended for normal operator use outside the Python development environment.
- Does not have the same direct access to repository source files or local build tooling that the Python version has.
- Bundles the help documentation and `LICENSE.txt` for in-app access.
- Uses the Update Manager only for executable-release checks, not for source-file maintenance.
- Automatic self-replacement of the running EXE is still not dependable and may require manual EXE replacement during testing.

## Update Manager Status

- The updater checks the Dispatcher Core version in `main.py` as the master version.
- Two-part versions such as `1.07` trigger an executable update when greater than the local version.
- Three-part versions only trigger an executable update when the third number is even, such as `1.07.2`.
- Odd patch versions such as `1.07.1` are ignored.
- In Python/source mode, new releases are still best handled by rebuilding manually.
- In packaged EXE mode, automatic self-replacement is still experimental and may require manual EXE replacement during testing.
