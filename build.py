# Production Logging Center (GLC Edition)
# Copyright (C) 2026 Jamie Martin
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import importlib
import importlib.util
import os
import shlex
import shutil
import stat
import subprocess
import sys
import argparse
from pathlib import Path, PurePosixPath, PureWindowsPath

from app.app_identity import DEB_PACKAGE_NAME, LEGACY_DEB_NAME, LEGACY_EXE_NAME, format_versioned_deb_name, format_versioned_exe_name, load_version_from_main, normalize_version, parse_version, parse_versioned_exe_name
from symbol_index import DEFAULT_OUTPUT_DIR as SYMBOL_INDEX_OUTPUT_DIR, SymbolIndexError, generate_symbol_index
from ubuntu_deb_packager import InstalledFile, build_default_package_config, build_ubuntu_deb_package, resolve_debian_architecture

REPO_ROOT = Path(__file__).resolve().parent
VERSION_SOURCE_PATH = REPO_ROOT / "launcher.py"
APP_VERSION = load_version_from_main(str(VERSION_SOURCE_PATH))
EXE_NAME = format_versioned_exe_name(APP_VERSION)
EXE_STEM = os.path.splitext(EXE_NAME)[0]
PRESERVE_DIST = os.environ.get("MARTIN_KEEP_DIST", "1") != "0"
SKIP_TASKKILL = os.environ.get("MARTIN_SKIP_TASKKILL", "0") == "1"
MARTIN_BUILD_TARGET_ENV = "MARTIN_BUILD_TARGET"
MARTIN_WSL_DISTRO_ENV = "MARTIN_WSL_DISTRO"
MARTIN_BUILD_PYTHON_ENV = "MARTIN_BUILD_PYTHON"
MAX_OLD_EXE_ARCHIVE = 10
REQUIRED_BUILD_MODULES = [
    "PIL",
    "PyInstaller",
    "openpyxl",
    "ttkbootstrap",
    "tkinter",
]
WSL_VENV_CANDIDATE_PATHS = [
    ".venv-linux/bin/python",
    ".venv/bin/python",
]
SENSITIVE_RUNTIME_PATHS = [
    ".vault",
    os.path.join("data", "security"),
    os.path.join("data", "backups", "security"),
]
ICON_SOURCE_CANDIDATE_PATHS = [
    REPO_ROOT / "assets" / "icons" / "icon.png",
    REPO_ROOT / "assets" / "icons" / "icon.jpg",
]
ICON_RUNTIME_PNG_SIZES = [16, 24, 32, 48, 64, 512]
ICON_ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
BUILD_DATA_PATHS = [
    ("app", "app"),
    ("assets", "assets"),
    ("docs", "docs"),
    ("templates", "templates"),
    ("layout_config.json", "."),
    ("rates.json", "."),
    ("production_log_calculations.json", "."),
]
HIDDENIMPORTS = [
    "openpyxl",
    "openpyxl.cell.cell",
    "PIL._tkinter_finder",
    "PyInstaller",
    "tkinter.messagebox",
    "tkinter.filedialog",
]
COLLECT_SUBMODULE_PACKAGES = [
    "app",
    "openpyxl",
    "PyInstaller",
]
WINDOWS_TARGET = "windows"
UBUNTU_TARGET = "ubuntu"
WINDOWS_BUILD_ROOT = REPO_ROOT / "build" / WINDOWS_TARGET
UBUNTU_BUILD_ROOT = REPO_ROOT / "build" / UBUNTU_TARGET
WINDOWS_DIST_ROOT = REPO_ROOT / "dist"
UBUNTU_DIST_ROOT = WINDOWS_DIST_ROOT / UBUNTU_TARGET
UBUNTU_APP_DIST_ROOT = UBUNTU_DIST_ROOT / "app"
UBUNTU_PACKAGE_ROOT = UBUNTU_DIST_ROOT / "package-root"


class BuildError(RuntimeError):
    pass


def ensure_repo_root():
    os.chdir(REPO_ROOT)


def detect_host_platform():
    if os.name == "nt":
        return WINDOWS_TARGET
    if sys.platform.startswith("linux"):
        return UBUNTU_TARGET
    if sys.platform == "darwin":
        return "macos"
    return sys.platform or os.name


def default_target_for_host(host_platform):
    if host_platform == WINDOWS_TARGET:
        return WINDOWS_TARGET
    if host_platform == UBUNTU_TARGET:
        return UBUNTU_TARGET
    return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build Production Logging Center for Windows (.exe) or Ubuntu (.deb).",
    )
    parser.add_argument(
        "--index-only",
        action="store_true",
        help="Refresh the local Python symbol index without building an artifact.",
    )
    parser.add_argument(
        "--target",
        choices=(WINDOWS_TARGET, UBUNTU_TARGET),
        help="Artifact target to build. Defaults to a prompt in interactive shells and the host-native target otherwise.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip the target prompt and default to the host-native target when --target is omitted.",
    )
    parser.add_argument(
        "--wsl-distro",
        help="Optional WSL distro name to use for Ubuntu builds launched from Windows.",
    )
    return parser.parse_args()


def prompt_for_target(host_platform):
    if host_platform == WINDOWS_TARGET:
        options = [
            (WINDOWS_TARGET, "Windows (.exe)"),
            (UBUNTU_TARGET, "Ubuntu (.deb via WSL)"),
        ]
    elif host_platform == UBUNTU_TARGET:
        print("Linux host detected. Defaulting to the Ubuntu (.deb) target.")
        return UBUNTU_TARGET
    else:
        raise BuildError(f"Interactive target selection is not supported on host platform: {host_platform}")

    print("Select a build target:")
    for index, (_target, label) in enumerate(options, start=1):
        print(f"  {index}. {label}")

    while True:
        raw_choice = input("Enter choice [1]: ").strip().lower()
        if raw_choice in {"", "1", WINDOWS_TARGET, "windows", "exe"}:
            return WINDOWS_TARGET
        if raw_choice in {"2", UBUNTU_TARGET, "linux", "deb"}:
            return UBUNTU_TARGET
        if raw_choice in {"q", "quit", "exit"}:
            raise BuildError("Build cancelled.")
        print("Invalid selection. Choose 1 for Windows, 2 for Ubuntu, or q to cancel.")


def resolve_target(args, host_platform):
    env_target = os.environ.get(MARTIN_BUILD_TARGET_ENV, "").strip().lower() or None
    requested_target = args.target or env_target

    if requested_target:
        return requested_target

    if args.non_interactive or not sys.stdin.isatty():
        default_target = default_target_for_host(host_platform)
        if not default_target:
            raise BuildError(
                f"No --target was provided and build.py does not have a default target for host platform {host_platform}."
            )
        print(f"No build target was specified. Defaulting to {default_target} for this {host_platform} host.")
        return default_target

    return prompt_for_target(host_platform)


def resolve_wsl_distro(args):
    return args.wsl_distro or os.environ.get(MARTIN_WSL_DISTRO_ENV, "").strip() or None


def refresh_symbol_index():
    try:
        result = generate_symbol_index(repo_root=REPO_ROOT, output_dir=REPO_ROOT / SYMBOL_INDEX_OUTPUT_DIR)
    except SymbolIndexError as exc:
        raise BuildError(f"Symbol index generation failed: {exc}") from exc

    summary = result["summary"]
    print(
        "Refreshed symbol index: "
        f"{summary['files']} files, "
        f"{summary['classes']} classes, "
        f"{summary['methods']} methods, "
        f"{summary['functions']} functions."
    )
    print(f"- JSON: {result['json_path']}")
    print(f"- Markdown: {result['markdown_path']}")


def validate_target_for_host(target, host_platform):
    if target == WINDOWS_TARGET and host_platform != WINDOWS_TARGET:
        raise BuildError("Windows .exe builds are only supported when build.py is running on Windows.")
    if target == UBUNTU_TARGET and host_platform not in {WINDOWS_TARGET, UBUNTU_TARGET}:
        raise BuildError("Ubuntu .deb builds are only supported on Linux directly or on Windows through WSL.")


def run_command(command, *, capture_output=False, cwd=None, env=None):
    kwargs = {
        "check": False,
        "cwd": cwd,
        "env": env,
    }
    if capture_output:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(command, **kwargs)


def ensure_python_modules(module_names):
    missing_modules = [module_name for module_name in module_names if importlib.util.find_spec(module_name) is None]
    if missing_modules:
        joined = ", ".join(missing_modules)
        raise BuildError(f"The active Python runtime is missing required build modules: {joined}.")


def resolve_wsl_invocation_cwd():
    if os.name != "nt":
        return None
    anchor = REPO_ROOT.anchor or f"{Path.cwd().drive}\\"
    return anchor if anchor else None


def get_icon_source_path():
    for path in ICON_SOURCE_CANDIDATE_PATHS:
        if path.exists():
            return path
    raise FileNotFoundError("No icon source artwork found. Expected assets/icons/icon.png or assets/icons/icon.jpg.")


def sync_icon_assets():
    from PIL import Image

    source_path = get_icon_source_path()
    output_directory = source_path.parent

    with Image.open(source_path) as source_image:
        working_image = source_image.convert("RGBA")

        available_ico_sizes = []
        for size in ICON_RUNTIME_PNG_SIZES:
            output_path = output_directory / f"icon-{size}.png"
            resized_image = working_image.resize((size, size), Image.Resampling.LANCZOS)
            resized_image.save(output_path, format="PNG")
            available_ico_sizes.append((size, size))

        if working_image.width >= 128 and working_image.height >= 128:
            available_ico_sizes.append((128, 128))
        if working_image.width >= 256 and working_image.height >= 256:
            available_ico_sizes.append((256, 256))

        icon_ico_path = output_directory / "icon.ico"
        working_image.save(icon_ico_path, format="ICO", sizes=available_ico_sizes or ICON_ICO_SIZES)


def get_existing_build_data_paths():
    build_paths = []
    for source_path, destination_path in BUILD_DATA_PATHS:
        absolute_source_path = REPO_ROOT / source_path
        if absolute_source_path.exists():
            build_paths.append((str(absolute_source_path), destination_path))
    return build_paths


def build_pyinstaller_args(target):
    if target == WINDOWS_TARGET:
        artifact_name = EXE_STEM
        work_path = WINDOWS_BUILD_ROOT / "work"
        spec_path = WINDOWS_BUILD_ROOT / "spec"
        dist_path = WINDOWS_DIST_ROOT
    elif target == UBUNTU_TARGET:
        artifact_name = DEB_PACKAGE_NAME
        work_path = UBUNTU_BUILD_ROOT / "work"
        spec_path = UBUNTU_BUILD_ROOT / "spec"
        dist_path = UBUNTU_APP_DIST_ROOT
    else:
        raise BuildError(f"Unsupported PyInstaller target: {target}")

    args = [
        str(REPO_ROOT / "main.py"),
        "--noconfirm",
        "--clean",
        "--name",
        artifact_name,
        "--workpath",
        str(work_path),
        "--specpath",
        str(spec_path),
        "--distpath",
        str(dist_path),
    ]

    if target == WINDOWS_TARGET:
        args.extend([
            "--onefile",
            "--windowed",
            "--icon",
            str(REPO_ROOT / "assets" / "icons" / "icon.ico"),
        ])
    elif target == UBUNTU_TARGET:
        args.extend(["--windowed"])

    for hiddenimport in HIDDENIMPORTS:
        args.extend(["--hidden-import", hiddenimport])

    for package_name in COLLECT_SUBMODULE_PACKAGES:
        args.extend(["--collect-submodules", package_name])

    for source_path, destination_path in get_existing_build_data_paths():
        args.extend(["--add-data", f"{source_path}{os.pathsep}{destination_path}"])

    return args


def remove_path(path, remove_readonly):
    if not os.path.exists(path):
        return
    if os.path.isdir(path):
        shutil.rmtree(path, onexc=remove_readonly)
        return
    os.chmod(path, stat.S_IWRITE)
    os.remove(path)


def scrub_preserved_runtime_state(base_dir, remove_readonly):
    removable_relative_paths = [
        "the_golden_standard",
        "app",
        *SENSITIVE_RUNTIME_PATHS,
    ]
    for relative_path in removable_relative_paths:
        remove_path(os.path.join(base_dir, relative_path), remove_readonly)


def build_remove_readonly_callback():
    def remove_readonly(_func, path, _exc_info):
        os.chmod(path, stat.S_IWRITE)
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)

    return remove_readonly


def clean_previous_builds(target):
    remove_readonly = build_remove_readonly_callback()

    if target == WINDOWS_TARGET and os.name == "nt" and not SKIP_TASKKILL:
        for exe_name in {EXE_NAME, LEGACY_EXE_NAME}:
            run_command(["taskkill", "/F", "/IM", exe_name], capture_output=True)

    target_paths = []
    if target == WINDOWS_TARGET:
        target_paths.extend([
            REPO_ROOT / "build" / EXE_STEM,
            WINDOWS_BUILD_ROOT,
            WINDOWS_DIST_ROOT / EXE_NAME,
            WINDOWS_DIST_ROOT / EXE_STEM,
        ])
        if not PRESERVE_DIST:
            target_paths.append(WINDOWS_DIST_ROOT)
    elif target == UBUNTU_TARGET:
        target_paths.extend([
            UBUNTU_BUILD_ROOT,
            UBUNTU_DIST_ROOT,
        ])
    else:
        raise BuildError(f"Unsupported cleanup target: {target}")

    for path in target_paths:
        remove_path(path, remove_readonly)

    if target == WINDOWS_TARGET and PRESERVE_DIST:
        scrub_preserved_runtime_state(os.path.abspath(WINDOWS_DIST_ROOT), remove_readonly)


def archive_previous_builds():
    if not PRESERVE_DIST:
        return

    dist_dir = os.path.abspath(WINDOWS_DIST_ROOT)
    archive_dir = os.path.join(dist_dir, "Old_exe")
    os.makedirs(archive_dir, exist_ok=True)

    for file_name in os.listdir(dist_dir):
        source_path = os.path.join(dist_dir, file_name)
        if not os.path.isfile(source_path):
            continue
        if file_name == EXE_NAME:
            continue
        if parse_versioned_exe_name(file_name) is None:
            continue

        target_path = os.path.join(archive_dir, file_name)
        if os.path.abspath(source_path) == os.path.abspath(target_path):
            continue
        if os.path.exists(target_path):
            os.remove(target_path)
        shutil.move(source_path, target_path)

    archived_entries = []
    for file_name in os.listdir(archive_dir):
        archive_path = os.path.join(archive_dir, file_name)
        if not os.path.isfile(archive_path):
            continue
        version_text = parse_versioned_exe_name(file_name)
        version_key = normalize_version(parse_version(version_text)) if version_text else None
        if version_key is None:
            continue
        archived_entries.append((version_key, file_name, archive_path))

    archived_entries.sort(key=lambda entry: entry[0], reverse=True)
    for _version_key, _file_name, archive_path in archived_entries[MAX_OLD_EXE_ARCHIVE:]:
        os.remove(archive_path)


def resolve_desktop_icon_source_path():
    for candidate_name in ("icon-512.png", "icon.png", "icon-64.png", "icon.jpg"):
        candidate_path = REPO_ROOT / "assets" / "icons" / candidate_name
        if candidate_path.exists():
            return candidate_path
    raise BuildError("No desktop icon asset is available for the Ubuntu package.")


def build_ubuntu_extra_files():
    doc_root = PurePosixPath("usr") / "share" / "doc" / DEB_PACKAGE_NAME
    extra_files = []

    license_path = REPO_ROOT / "docs" / "legal" / "LICENSE.txt"
    if license_path.exists():
        extra_files.append(InstalledFile(license_path, doc_root / "LICENSE.txt"))

    readme_path = REPO_ROOT / "README.md"
    if readme_path.exists():
        extra_files.append(InstalledFile(readme_path, doc_root / "README.md"))

    return tuple(extra_files)


def ensure_command_available(command_name):
    if shutil.which(command_name) is None:
        raise BuildError(f"Required build command was not found on PATH: {command_name}")


def resolve_wsl_command_prefix(wsl_distro=None):
    command = ["wsl.exe"]
    if wsl_distro:
        command.extend(["-d", wsl_distro])
    return command


def build_default_wsl_repo_path():
    windows_path = PureWindowsPath(str(REPO_ROOT))
    drive = windows_path.drive.rstrip(":").lower()
    if not drive:
        return None

    path_parts = [part for part in windows_path.parts[1:] if part not in {"\\", "/"}]
    suffix = "/".join(path_parts)
    return f"/mnt/{drive}/{suffix}" if suffix else f"/mnt/{drive}"


def resolve_wsl_drive_mount():
    windows_path = PureWindowsPath(str(REPO_ROOT))
    drive = windows_path.drive.rstrip(":").lower()
    if not drive:
        return None
    return f"/mnt/{drive}"


def resolve_wsl_path(wsl_distro=None):
    ensure_command_available("wsl.exe")
    result = run_command(
        resolve_wsl_command_prefix(wsl_distro) + ["wslpath", "-a", str(REPO_ROOT)],
        capture_output=True,
        cwd=resolve_wsl_invocation_cwd(),
    )
    resolved_path = (result.stdout or "").strip()
    if resolved_path.startswith("/"):
        return resolved_path

    fallback_path = build_default_wsl_repo_path()
    if fallback_path:
        probe_result = run_command(
            resolve_wsl_command_prefix(wsl_distro) + ["bash", "-lc", f"test -d {shlex.quote(fallback_path)}"],
            capture_output=True,
            cwd=resolve_wsl_invocation_cwd(),
        )
        if probe_result.returncode == 0:
            stderr_text = (result.stderr or "").strip()
            if stderr_text:
                print(f"WSL path translation fallback in use: {stderr_text}")
            return fallback_path

        drive_mount = resolve_wsl_drive_mount()
        if drive_mount:
            mount_probe = run_command(
                resolve_wsl_command_prefix(wsl_distro) + ["bash", "-lc", f"test -d {shlex.quote(drive_mount)}"],
                capture_output=True,
                cwd=resolve_wsl_invocation_cwd(),
            )
            if mount_probe.returncode != 0:
                raise BuildError(
                    f"WSL is available, but the distro cannot access the drive that contains this workspace. "
                    f"Expected a mounted path at {drive_mount} for {REPO_ROOT}. Mount that drive inside WSL or clone the repo into the distro filesystem before building Ubuntu packages."
                )

    stderr_text = (result.stderr or result.stdout or "").strip()
    raise BuildError(f"Could not resolve the repository path inside WSL. {stderr_text}")


def invoke_ubuntu_build_via_wsl(wsl_distro=None):
    linux_repo_root = resolve_wsl_path(wsl_distro)
    linux_venv_selection = " ".join(
        f"elif [ -x {shlex.quote(candidate_path)} ]; then BUILD_PYTHON={shlex.quote(candidate_path)}; "
        for candidate_path in WSL_VENV_CANDIDATE_PATHS
    )
    bash_script = (
        "set -euo pipefail; "
        f"cd {shlex.quote(linux_repo_root)}; "
        f"if [ -n \"${{{MARTIN_BUILD_PYTHON_ENV}:-}}\" ] && [ -x \"${{{MARTIN_BUILD_PYTHON_ENV}}}\" ]; then BUILD_PYTHON=\"${{{MARTIN_BUILD_PYTHON_ENV}}}\"; "
        f"{linux_venv_selection}"
        "elif command -v python3 >/dev/null 2>&1; then BUILD_PYTHON=$(command -v python3); "
        "else echo 'No python3 runtime was found in the selected WSL distribution.' >&2; exit 1; fi; "
        "if ! \"$BUILD_PYTHON\" -c 'import PIL, PyInstaller, openpyxl, ttkbootstrap, tkinter' >/dev/null 2>&1; then "
        "echo 'The selected WSL Python runtime is missing one or more required build modules: Pillow, PyInstaller, openpyxl, ttkbootstrap, tkinter.' >&2; "
        "echo 'Create .venv-linux inside WSL or install the modules into the selected WSL Python runtime before building.' >&2; exit 1; fi; "
        "if ! command -v dpkg-deb >/dev/null 2>&1; then "
        "echo 'dpkg-deb is required inside WSL to build the Ubuntu package.' >&2; exit 1; fi; "
        "exec \"$BUILD_PYTHON\" build.py --target ubuntu --non-interactive"
    )
    command = resolve_wsl_command_prefix(wsl_distro) + ["bash", "-lc", bash_script]
    result = run_command(command, capture_output=True, cwd=resolve_wsl_invocation_cwd())
    if result.returncode != 0:
        distro_suffix = f" in WSL distro '{wsl_distro}'" if wsl_distro else " in WSL"
        failure_detail = (result.stderr or result.stdout or "").strip()
        detail_suffix = f" Details: {failure_detail}" if failure_detail else ""
        raise BuildError(
            "The Ubuntu build failed"
            f"{distro_suffix}. Confirm that the distro can access this repo and has Python, Pillow, PyInstaller, openpyxl, ttkbootstrap, tkinter, and dpkg-deb installed.{detail_suffix}"
        )


def run_windows_build():
    refresh_symbol_index()
    ensure_python_modules(REQUIRED_BUILD_MODULES)
    pyinstaller_main = importlib.import_module("PyInstaller.__main__")

    clean_previous_builds(WINDOWS_TARGET)
    sync_icon_assets()
    pyinstaller_main.run(build_pyinstaller_args(WINDOWS_TARGET))

    built_executable_path = WINDOWS_DIST_ROOT / EXE_NAME
    if not built_executable_path.exists():
        raise BuildError(f"PyInstaller completed, but the Windows executable was not created at {built_executable_path}.")

    archive_previous_builds()

    print(f"\n--- Windows build complete. Check {built_executable_path} ---")


def run_ubuntu_build_direct():
    refresh_symbol_index()
    ensure_command_available("dpkg-deb")
    ensure_python_modules(REQUIRED_BUILD_MODULES)

    pyinstaller_main = importlib.import_module("PyInstaller.__main__")
    architecture = resolve_debian_architecture()
    deb_name = format_versioned_deb_name(APP_VERSION, architecture)

    clean_previous_builds(UBUNTU_TARGET)
    sync_icon_assets()
    pyinstaller_main.run(build_pyinstaller_args(UBUNTU_TARGET))

    bundle_root = UBUNTU_APP_DIST_ROOT / DEB_PACKAGE_NAME
    if not bundle_root.exists():
        raise BuildError(f"PyInstaller completed, but the Ubuntu app bundle was not created at {bundle_root}.")

    output_path = UBUNTU_DIST_ROOT / deb_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    package_config = build_default_package_config(
        bundle_source=bundle_root,
        icon_source=resolve_desktop_icon_source_path(),
        output_path=output_path,
        output_alias_paths=(UBUNTU_DIST_ROOT / LEGACY_DEB_NAME,),
        staging_root=UBUNTU_PACKAGE_ROOT,
        version=APP_VERSION,
        architecture=architecture,
        extra_files=build_ubuntu_extra_files(),
    )
    try:
        build_ubuntu_deb_package(package_config)
    except Exception as exc:
        raise BuildError(str(exc)) from exc

    print(f"\n--- Ubuntu package complete. Check {output_path} ---")


def run_target_build(target, host_platform, args):
    validate_target_for_host(target, host_platform)

    if target == WINDOWS_TARGET:
        run_windows_build()
        return

    if target == UBUNTU_TARGET and host_platform == WINDOWS_TARGET:
        invoke_ubuntu_build_via_wsl(resolve_wsl_distro(args))
        return

    if target == UBUNTU_TARGET:
        run_ubuntu_build_direct()
        return

    raise BuildError(f"Unsupported build target: {target}")


def main():
    ensure_repo_root()
    args = parse_args()
    if args.index_only:
        refresh_symbol_index()
        return

    host_platform = detect_host_platform()
    selected_target = resolve_target(args, host_platform)

    print(f"Host platform: {host_platform}")
    print(f"Selected target: {selected_target}")
    run_target_build(selected_target, host_platform, args)


if __name__ == "__main__":
    try:
        main()
    except BuildError as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc