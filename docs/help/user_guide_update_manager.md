# Update Manager

Use Update Manager to compare the local Dispatcher Core version with the repository release version.

- Check Repository compares the local Dispatcher version against the configured repository release source.
- The top release section still evaluates Dispatcher Core as the packaged EXE update boundary.
- The repository URL, packaged Advanced Dev Updates toggle, and external override trust toggle are now controlled from the admin-only Developer & Admin tools in Settings Manager.
- Source-build runtime discovery prefers the suite's own `.venv` before trying environment-variable or system Python fallbacks.
- Downloaded module payloads are stored in the external `the_golden_standard` folder.
- Two-part versions such as `1.07` can trigger an executable update when greater than the local version.
- Three-part versions only trigger updates when the third number is even, such as `1.07.2`.
- Odd patch versions such as `1.07.1` are ignored.
- In the Python/source workflow on Windows, stable updates can download the published EXE into local `dist` and launch it for handoff testing.
- In the packaged Windows EXE workflow, the newer EXE downloads beside the current one, launches separately, and the app can later offer cleanup of older local EXEs.
- On Ubuntu, stable updates download the published `.deb` package and open the system package installer while the current app stays open.
- Advanced Dev Updates are only available from packaged Windows builds when the privileged setting is enabled.

## Payload Notes

- Module payload installs target the external `the_golden_standard` folder.
- Installed module payloads stay inactive until override trust is enabled; this lets admins stage override files without executing them immediately.
- JSON payload restores can replace tracked local configuration files while keeping backups first.
- Documentation restores refresh the bundled Help Center markdown files and `LICENSE.txt` as one grouped update instead of individual per-document choices.
- Dispatcher Core EXE updates still follow the packaged release path.
