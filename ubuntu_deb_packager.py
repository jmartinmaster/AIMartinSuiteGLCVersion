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

from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET

from app.app_identity import APP_MAINTAINER, DEB_PACKAGE_NAME, LEGACY_DEB_NAME, format_versioned_deb_name, load_version_from_main


REPO_ROOT = Path(__file__).resolve().parent
VERSION_SOURCE_PATH = REPO_ROOT / "launcher.py"

# Core package metadata. These are the fields most people swap first.
APP_NAME = "Production Logging Center"
APP_VERSION = load_version_from_main(str(VERSION_SOURCE_PATH))
APP_ARCHITECTURE = "amd64"
SHORT_DESCRIPTION = "Desktop production support application for GLC operators"
LONG_DESCRIPTION = """
Production Logging Center packages a desktop GUI workflow for production logging,
shift review, and operator-facing exports.

Replace this placeholder copy with your own support details, release notes, and
Ubuntu-specific packaging guidance before publishing a production package.
"""

# Packaging knobs that make the generated files reusable for other GUI apps.
APP_IDENTIFIER = DEB_PACKAGE_NAME
EXECUTABLE_NAME = APP_IDENTIFIER
DESKTOP_CATEGORIES = ("Utility", "Office")
HOMEPAGE_URL = "https://example.com/production-logging-center"
APPSTREAM_SUMMARY = "Industrial production logging workflow for Ubuntu desktops"
APPSTREAM_DESCRIPTION = """
Production Logging Center gives operators a desktop-first workflow for tracking
production activity, reviewing downtime, and exporting completed logs.

Replace this placeholder AppStream description with release-ready marketing copy,
workflow details, and links to your own screenshots or documentation.
"""
APPSTREAM_SCREENSHOTS = (
    ("default", "Main application dashboard", "https://example.com/screenshots/main-dashboard.png"),
    ("secondary", "Downtime review workflow", "https://example.com/screenshots/downtime-review.png"),
)

SECTION = "utils"
PRIORITY = "optional"
ICON_SIZE = 512

DEFAULT_BUNDLE_SOURCE = REPO_ROOT / "dist" / "ubuntu" / "app" / APP_IDENTIFIER
DEFAULT_ICON_SOURCE = REPO_ROOT / "assets" / "icons" / "icon.png"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "dist" / "ubuntu" / format_versioned_deb_name(APP_VERSION, APP_ARCHITECTURE)
DEFAULT_LEGACY_OUTPUT_PATH = REPO_ROOT / "dist" / "ubuntu" / LEGACY_DEB_NAME
DEFAULT_STAGING_ROOT = REPO_ROOT / "dist" / "ubuntu" / "package-root"


@dataclass(frozen=True)
class AppStreamScreenshot:
    kind: str
    caption: str
    url: str


@dataclass(frozen=True)
class InstalledFile:
    source: Path
    destination: PurePosixPath
    mode: int = 0o644


@dataclass(frozen=True)
class DebianPackageConfig:
    app_name: str
    package_name: str
    version: str
    architecture: str
    maintainer: str
    short_description: str
    long_description: str
    executable_name: str
    bundle_source: Path
    icon_source: Path
    output_path: Path
    output_alias_paths: tuple[Path, ...]
    staging_root: Path
    homepage_url: str = HOMEPAGE_URL
    appstream_summary: str = APPSTREAM_SUMMARY
    appstream_description: str = APPSTREAM_DESCRIPTION
    screenshots: tuple[AppStreamScreenshot, ...] = field(default_factory=tuple)
    desktop_categories: tuple[str, ...] = field(default_factory=lambda: DESKTOP_CATEGORIES)
    section: str = SECTION
    priority: str = PRIORITY
    icon_size: int = ICON_SIZE
    startup_wm_class: str | None = None
    extra_files: tuple[InstalledFile, ...] = field(default_factory=tuple)

    @property
    def desktop_filename(self) -> str:
        return f"{self.package_name}.desktop"

    @property
    def launcher_name(self) -> str:
        return self.package_name

    @property
    def metainfo_filename(self) -> str:
        return f"{self.package_name}.metainfo.xml"


def build_default_package_config(
    *,
    bundle_source: Path,
    icon_source: Path,
    output_path: Path,
    staging_root: Path,
    output_alias_paths: tuple[Path, ...] | None = None,
    version: str = APP_VERSION,
    architecture: str = APP_ARCHITECTURE,
    app_name: str = APP_NAME,
    package_name: str = APP_IDENTIFIER,
    maintainer: str = APP_MAINTAINER,
    short_description: str = SHORT_DESCRIPTION,
    long_description: str = LONG_DESCRIPTION,
    executable_name: str = EXECUTABLE_NAME,
    homepage_url: str = HOMEPAGE_URL,
    appstream_summary: str = APPSTREAM_SUMMARY,
    appstream_description: str = APPSTREAM_DESCRIPTION,
    extra_files: tuple[InstalledFile, ...] = (),
) -> DebianPackageConfig:
    resolved_output_path = Path(output_path)
    if output_alias_paths is None:
        legacy_alias = resolved_output_path.parent / f"{package_name}.deb"
        resolved_aliases = () if legacy_alias == resolved_output_path else (legacy_alias,)
    else:
        resolved_aliases = tuple(Path(alias_path) for alias_path in output_alias_paths)

    screenshots = tuple(
        AppStreamScreenshot(kind=kind, caption=caption, url=url)
        for kind, caption, url in APPSTREAM_SCREENSHOTS
    )
    return DebianPackageConfig(
        app_name=app_name,
        package_name=package_name,
        version=version,
        architecture=architecture,
        maintainer=maintainer,
        short_description=short_description,
        long_description=long_description,
        executable_name=executable_name,
        bundle_source=Path(bundle_source),
        icon_source=Path(icon_source),
        output_path=resolved_output_path,
        output_alias_paths=resolved_aliases,
        staging_root=Path(staging_root),
        homepage_url=homepage_url,
        appstream_summary=appstream_summary,
        appstream_description=appstream_description,
        screenshots=screenshots,
        startup_wm_class=package_name,
        extra_files=extra_files,
    )


def ensure_command_available(command_name: str) -> None:
    if shutil.which(command_name) is None:
        raise RuntimeError(f"Required build command was not found on PATH: {command_name}")


def run_command(command: list[str], *, capture_output: bool = False) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    kwargs = {
        "check": False,
    }
    if capture_output:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    return subprocess.run(command, **kwargs)


def resolve_debian_architecture() -> str:
    result = run_command(["dpkg", "--print-architecture"], capture_output=True)
    if result.returncode == 0 and result.stdout:
        return result.stdout.strip()
    return {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(platform.machine().lower(), "amd64")


def should_stage_in_native_temp(staging_root: Path) -> bool:
    normalized = str(staging_root).replace("\\", "/")
    return normalized.startswith("/mnt/")


def remove_existing_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
        return
    path.unlink()


def set_mode(path: Path, mode: int) -> None:
    os.chmod(path, mode)


def ensure_directory(path: Path, mode: int = 0o755) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    set_mode(path, mode)
    return path


def ensure_parent_directories(path: Path, mode: int = 0o755) -> None:
    current = path.parent
    pending = []
    while current and not current.exists():
        pending.append(current)
        current = current.parent
    for directory in reversed(pending):
        ensure_directory(directory, mode=mode)


def write_text_file(path: Path, contents: str, mode: int) -> None:
    ensure_parent_directories(path)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(contents)
    set_mode(path, mode)


def apply_directory_modes(root_path: Path) -> None:
    for current_root, directory_names, _file_names in os.walk(root_path):
        root_directory = Path(current_root)
        set_mode(root_directory, 0o755)
        for directory_name in directory_names:
            set_mode(root_directory / directory_name, 0o755)


def split_paragraphs(text: str) -> list[str]:
    dedented = textwrap.dedent(str(text or "")).strip()
    if not dedented:
        return []
    paragraphs = []
    for paragraph in dedented.split("\n\n"):
        compact = " ".join(line.strip() for line in paragraph.splitlines() if line.strip())
        if compact:
            paragraphs.append(compact)
    return paragraphs


def format_debian_long_description(text: str, width: int = 74) -> str:
    lines = []
    for paragraph in split_paragraphs(text):
        wrapped = textwrap.wrap(paragraph, width=width) or [""]
        lines.extend(f" {line}" for line in wrapped)
        lines.append(" .")
    if lines and lines[-1] == " .":
        lines.pop()
    return "\n".join(lines) if lines else " ."


def build_launcher_script(config: DebianPackageConfig) -> str:
    app_root = f"/opt/{config.package_name}"
    return textwrap.dedent(
        f"""\
        #!/bin/sh
        set -eu

        APP_ROOT=\"{app_root}\"
        exec \"$APP_ROOT/{config.executable_name}\" \"$@\"
        """
    )


def render_control_file(config: DebianPackageConfig, installed_size_kib: int) -> str:
    return (
        f"Package: {config.package_name}\n"
        f"Version: {config.version}\n"
        f"Section: {config.section}\n"
        f"Priority: {config.priority}\n"
        f"Architecture: {config.architecture}\n"
        f"Maintainer: {config.maintainer}\n"
        f"Installed-Size: {installed_size_kib}\n"
        f"Description: {config.short_description}\n"
        f"{format_debian_long_description(config.long_description)}\n"
    )


def render_desktop_file(config: DebianPackageConfig) -> str:
    categories = "".join(f"{category};" for category in config.desktop_categories)
    startup_wm_class = config.startup_wm_class or config.package_name
    return textwrap.dedent(
        f"""\
        [Desktop Entry]
        Version=1.0
        Type=Application
        Name={config.app_name}
        Comment={config.short_description}
        Exec=/usr/bin/{config.launcher_name}
        Icon={config.package_name}
        Terminal=false
        Categories={categories}
        StartupWMClass={startup_wm_class}
        """
    )


def render_metainfo_xml(config: DebianPackageConfig) -> str:
    component = ET.Element("component", {"type": "desktop-application"})
    ET.SubElement(component, "id").text = config.desktop_filename
    ET.SubElement(component, "metadata_license").text = "CC0-1.0"
    ET.SubElement(component, "project_license").text = "GPL-3.0-or-later"
    ET.SubElement(component, "name").text = config.app_name
    ET.SubElement(component, "summary").text = config.appstream_summary
    ET.SubElement(component, "developer_name").text = config.maintainer.split("<", 1)[0].strip()
    description = ET.SubElement(component, "description")
    for paragraph in split_paragraphs(config.appstream_description):
        ET.SubElement(description, "p").text = paragraph

    if config.screenshots:
        screenshots_element = ET.SubElement(component, "screenshots")
        for screenshot in config.screenshots:
            screenshot_element = ET.SubElement(screenshots_element, "screenshot", {"type": screenshot.kind})
            ET.SubElement(screenshot_element, "caption").text = screenshot.caption
            ET.SubElement(screenshot_element, "image").text = screenshot.url

    ET.SubElement(component, "launchable", {"type": "desktop-id"}).text = config.desktop_filename
    ET.SubElement(component, "url", {"type": "homepage"}).text = config.homepage_url
    ET.SubElement(component, "content_rating", {"type": "oars-1.1"})

    tree = ET.ElementTree(component)
    ET.indent(tree, space="  ")
    xml_body = ET.tostring(component, encoding="unicode")
    return f"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n{xml_body}\n"


def estimate_installed_size_kib(root_path: Path) -> int:
    total_bytes = 0
    for directory_path, _directory_names, file_names in os.walk(root_path):
        for file_name in file_names:
            file_path = Path(directory_path) / file_name
            if file_path.is_symlink():
                continue
            total_bytes += file_path.stat().st_size
    return max(1, (total_bytes + 1023) // 1024)


def resolve_install_path(package_root: Path, destination: PurePosixPath) -> Path:
    relative_parts = destination.parts[1:] if destination.is_absolute() else destination.parts
    return package_root.joinpath(*relative_parts)


def copy_extra_installed_files(package_root: Path, extra_files: tuple[InstalledFile, ...]) -> None:
    for installed_file in extra_files:
        source = Path(installed_file.source)
        if not source.exists():
            continue
        target = resolve_install_path(package_root, installed_file.destination)
        ensure_parent_directories(target)
        shutil.copy2(source, target)
        set_mode(target, installed_file.mode)


def copy_icon_asset(config: DebianPackageConfig, icon_dir: Path) -> None:
    if not config.icon_source.exists():
        raise FileNotFoundError(f"Icon source was not found: {config.icon_source}")
    icon_suffix = config.icon_source.suffix.lower() or ".png"
    icon_target = icon_dir / f"{config.package_name}{icon_suffix}"
    shutil.copy2(config.icon_source, icon_target)
    set_mode(icon_target, 0o644)


def copy_application_payload(config: DebianPackageConfig, package_root: Path, bin_dir: Path) -> tuple[Path, ...]:
    if not config.bundle_source.exists():
        raise FileNotFoundError(f"Application bundle was not found: {config.bundle_source}")

    if config.bundle_source.is_dir():
        app_install_dir = ensure_directory(package_root / "opt" / config.package_name)
        shutil.copytree(config.bundle_source, app_install_dir, dirs_exist_ok=True)
        apply_directory_modes(app_install_dir)

        bundle_executable = app_install_dir / config.executable_name
        if not bundle_executable.exists():
            raise FileNotFoundError(
                f"Expected executable '{config.executable_name}' inside the app bundle at {bundle_executable}."
            )
        set_mode(bundle_executable, 0o755)

        launcher_path = bin_dir / config.launcher_name
        write_text_file(launcher_path, build_launcher_script(config), 0o755)
        return bundle_executable, launcher_path

    launcher_path = bin_dir / config.launcher_name
    shutil.copy2(config.bundle_source, launcher_path)
    set_mode(launcher_path, 0o755)
    return (launcher_path,)


def build_dpkg_command(package_root: Path, output_path: Path, include_root_owner_group: bool = True) -> list[str]:
    command = ["dpkg-deb", "--build"]
    if include_root_owner_group:
        command.append("--root-owner-group")
    command.extend([str(package_root), str(output_path)])
    return command


def run_dpkg_build(package_root: Path, output_path: Path) -> None:
    ensure_command_available("dpkg-deb")
    remove_existing_path(output_path)

    primary_result = run_command(build_dpkg_command(package_root, output_path, include_root_owner_group=True), capture_output=True)
    if primary_result.returncode == 0:
        return

    stderr_text = (primary_result.stderr or primary_result.stdout or "").strip()
    if "--root-owner-group" in stderr_text:
        fallback_result = run_command(build_dpkg_command(package_root, output_path, include_root_owner_group=False), capture_output=True)
        if fallback_result.returncode == 0:
            return
        stderr_text = (fallback_result.stderr or fallback_result.stdout or "").strip()

    raise RuntimeError(f"dpkg-deb failed while building the Ubuntu package: {stderr_text}")


def stage_package_root(config: DebianPackageConfig, package_root: Path) -> Path:
    remove_existing_path(package_root)

    control_dir = ensure_directory(package_root / "DEBIAN")
    bin_dir = ensure_directory(package_root / "usr" / "bin")
    desktop_dir = ensure_directory(package_root / "usr" / "share" / "applications")
    icon_dir = ensure_directory(package_root / "usr" / "share" / "icons" / "hicolor" / f"{config.icon_size}x{config.icon_size}" / "apps")
    metainfo_dir = ensure_directory(package_root / "usr" / "share" / "metainfo")

    copy_application_payload(config, package_root, bin_dir)
    copy_icon_asset(config, icon_dir)
    copy_extra_installed_files(package_root, config.extra_files)

    desktop_path = desktop_dir / config.desktop_filename
    metainfo_path = metainfo_dir / config.metainfo_filename
    write_text_file(desktop_path, render_desktop_file(config), 0o644)
    write_text_file(metainfo_path, render_metainfo_xml(config), 0o644)

    control_path = control_dir / "control"
    installed_size_kib = estimate_installed_size_kib(package_root)
    write_text_file(control_path, render_control_file(config, installed_size_kib), 0o644)
    set_mode(control_dir, 0o755)
    set_mode(package_root, 0o755)
    return package_root


def build_ubuntu_deb_package(config: DebianPackageConfig) -> Path:
    output_path = Path(config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    staging_root = Path(config.staging_root)
    if should_stage_in_native_temp(staging_root):
        with tempfile.TemporaryDirectory(prefix=f"{config.package_name}-pkg-") as temp_dir:
            package_root = stage_package_root(config, Path(temp_dir) / "package-root")
            run_dpkg_build(package_root, output_path)
            write_output_aliases(output_path, config.output_alias_paths)
            return output_path

    package_root = stage_package_root(config, staging_root)
    run_dpkg_build(package_root, output_path)
    write_output_aliases(output_path, config.output_alias_paths)
    return output_path


def write_output_aliases(primary_output_path: Path, alias_paths: tuple[Path, ...]) -> None:
    for alias_path in alias_paths:
        if not alias_path or alias_path == primary_output_path:
            continue
        alias_path.parent.mkdir(parents=True, exist_ok=True)
        remove_existing_path(alias_path)
        shutil.copy2(primary_output_path, alias_path)
        try:
            set_mode(alias_path, 0o644)
        except OSError:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage and build a Debian package for a GUI application.")
    parser.add_argument("--bundle-source", default=str(DEFAULT_BUNDLE_SOURCE), help="Path to the built app bundle or executable.")
    parser.add_argument("--icon-source", default=str(DEFAULT_ICON_SOURCE), help="Path to the application icon asset.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Destination .deb file path.")
    parser.add_argument("--legacy-output", default=str(DEFAULT_LEGACY_OUTPUT_PATH), help="Optional stable alias written alongside the versioned .deb.")
    parser.add_argument("--staging-root", default=str(DEFAULT_STAGING_ROOT), help="Working staging directory used before dpkg-deb runs.")
    parser.add_argument("--app-name", default=APP_NAME, help="User-facing application name.")
    parser.add_argument("--package-name", default=APP_IDENTIFIER, help="Debian package identifier used for file names and launcher paths.")
    parser.add_argument("--version", default=APP_VERSION, help="Debian package version string.")
    parser.add_argument("--architecture", default=APP_ARCHITECTURE, help="Debian package architecture. Use 'auto' to query dpkg.")
    parser.add_argument("--maintainer", default=APP_MAINTAINER, help="Maintainer string written into DEBIAN/control.")
    parser.add_argument("--short-description", default=SHORT_DESCRIPTION, help="One-line package description.")
    parser.add_argument("--long-description", default=LONG_DESCRIPTION, help="Multi-line package description.")
    parser.add_argument("--executable-name", default=EXECUTABLE_NAME, help="Executable name inside the bundle directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    architecture = resolve_debian_architecture() if str(args.architecture).strip().lower() == "auto" else args.architecture
    config = build_default_package_config(
        bundle_source=Path(args.bundle_source),
        icon_source=Path(args.icon_source),
        output_path=Path(args.output),
        output_alias_paths=(Path(args.legacy_output),),
        staging_root=Path(args.staging_root),
        version=args.version,
        architecture=str(architecture),
        app_name=args.app_name,
        package_name=args.package_name,
        maintainer=args.maintainer,
        short_description=args.short_description,
        long_description=args.long_description,
        executable_name=args.executable_name,
    )
    output_path = build_ubuntu_deb_package(config)
    print(f"Built Debian package: {output_path}")


if __name__ == "__main__":
    main()