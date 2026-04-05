# Update Manager

Use Update Manager to compare the local Dispatcher Core version with the repository release version.

- Check Repository compares the local Dispatcher version against the current branch version.
- The top release section still evaluates Dispatcher Core as the packaged EXE update boundary.
- Source-build runtime discovery prefers the suite's own `.venv` before trying environment-variable or system Python fallbacks.
- Downloaded module payloads are stored in the external `modules` folder and become active automatically for that module once the module is reloaded.
- Two-part versions such as `1.07` can trigger an executable update when greater than the local version.
- Three-part versions only trigger updates when the third number is even, such as `1.07.2`.
- Odd patch versions such as `1.07.1` are ignored.
- In the Python/source workflow, updated EXEs are still best handled by rebuilding manually.
- In the packaged EXE workflow, automatic self-replacement is still experimental and may require manual EXE replacement.

## Payload Notes

- Module payload installs target the external `modules` folder.
- JSON payload restores can replace tracked local configuration files while keeping backups first.
- Documentation restores refresh the bundled Help Center markdown files and `LICENSE.txt` as one grouped update instead of individual per-document choices.
- Dispatcher Core EXE updates still follow the packaged release path.
