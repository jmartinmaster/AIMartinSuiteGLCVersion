import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from symbol_index import DEFAULT_OUTPUT_DIR as SYMBOL_INDEX_OUTPUT_DIR, JSON_OUTPUT_NAME as SYMBOL_INDEX_JSON_NAME, SymbolIndexError, generate_symbol_index


DEFAULT_OUTPUT_DIR = Path("build") / "project-librarian"
SNAPSHOT_NAME = "librarian-snapshot.json"
HISTORY_NAME = "change-history.jsonl"
CORPUS_NAME = "search-corpus.json"
DRAFTS_DIR_NAME = "drafts"
AI_CONTEXT_DIR_NAME = "ai-context"
SNAPSHOT_VERSION = 2
DEFAULT_AI_MODEL = "qwen2.5-coder:14b"
README_TARGET_NAME = "README.md"
CHANGELOG_TARGET_NAME = "CHANGELOG.md"
DOC_BLOCK_START = "<!-- project-librarian:docs:start -->"
DOC_BLOCK_END = "<!-- project-librarian:docs:end -->"
SEARCHABLE_EXTENSIONS = {
    ".code-workspace",
    ".desktop",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".spec",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".idea",
    ".venv",
    ".vscode",
    "__pycache__",
    "build",
    "data",
    "dist",
    "env",
    "exports",
    "logs",
    "venv",
}
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./:-]+")
STATUS_TOKEN_PATTERN = re.compile(r"[A-Za-z?]+")
DIFF_HUNK_PATTERN = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
CHANGELOG_HEADING_PATTERN = re.compile(r"^## \[(?P<version>[^\]]+)\] - .+$", re.MULTILINE)
AREA_ORDER = ("app", "controllers", "models", "views", "docs", "scripts", "root")
DOC_SUGGESTIONS_BY_AREA = {
    "app": ["README.md", "CHANGELOG.md", "docs/help/"],
    "controllers": ["README.md", "CHANGELOG.md", "docs/help/"],
    "models": ["README.md", "CHANGELOG.md", "docs/production_log_json_architecture.md"],
    "views": ["README.md", "CHANGELOG.md", "docs/help/"],
    "docs": ["README.md", "CHANGELOG.md"],
    "scripts": ["README.md", "docs/ai-delegation/"],
    "root": ["README.md", "CHANGELOG.md"],
}


class ProjectLibrarianError(RuntimeError):
    pass


@dataclass
class LibrarianWorkspace:
    repo_root: Path
    output_dir: Path
    snapshot: dict
    corpus: dict
    history: list

    @classmethod
    def load(cls, repo_root=None, output_dir=None, refresh_if_missing=True, refresh_first=False):
        resolved_repo_root = Path(repo_root or _repo_root_from_here()).resolve()
        resolved_output_dir = _resolve_output_dir(resolved_repo_root, output_dir)
        if refresh_first:
            build_librarian_snapshot(repo_root=resolved_repo_root, output_dir=resolved_output_dir)
        snapshot = _load_snapshot(
            repo_root=resolved_repo_root,
            output_dir=resolved_output_dir,
            refresh_if_missing=refresh_if_missing,
        )
        corpus = _load_corpus(
            repo_root=resolved_repo_root,
            output_dir=resolved_output_dir,
            refresh_if_missing=refresh_if_missing,
        )
        history = _load_history(
            repo_root=resolved_repo_root,
            output_dir=resolved_output_dir,
        )
        return cls(
            repo_root=resolved_repo_root,
            output_dir=resolved_output_dir,
            snapshot=snapshot,
            corpus=corpus,
            history=history,
        )

    def refresh(self):
        result = build_librarian_snapshot(repo_root=self.repo_root, output_dir=self.output_dir)
        self.snapshot = result["snapshot"]
        self.corpus = _load_corpus(repo_root=self.repo_root, output_dir=self.output_dir, refresh_if_missing=False)
        self.history = _load_history(repo_root=self.repo_root, output_dir=self.output_dir)
        return result

    @property
    def changed_files(self):
        return self.snapshot.get("git", {}).get("changed_files", [])

    @property
    def changed_paths(self):
        return {item.get("path") for item in self.changed_files if item.get("path")}

    @property
    def file_records(self):
        return self.snapshot.get("files", [])

    @property
    def symbol_records(self):
        return self.snapshot.get("symbols", [])

    @property
    def file_lookup(self):
        return {record.get("path"): record for record in self.file_records if record.get("path")}


def _repo_root_from_here():
    return Path(__file__).resolve().parent


def _resolve_output_dir(repo_root, output_dir=None):
    resolved_repo_root = Path(repo_root or _repo_root_from_here()).resolve()
    candidate = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    if candidate.is_absolute():
        return candidate.resolve()
    return (resolved_repo_root / candidate).resolve()


def _utc_now_text():
    return datetime.now(timezone.utc).isoformat()


def _today_text():
    return datetime.now(timezone.utc).date().isoformat()


def _relative_path_text(path, repo_root):
    return path.relative_to(repo_root).as_posix()


def _file_area(relative_path):
    if relative_path.startswith("docs/"):
        return "docs"
    if relative_path.startswith("app/controllers/"):
        return "controllers"
    if relative_path.startswith("app/models/"):
        return "models"
    if relative_path.startswith("app/views/"):
        return "views"
    if relative_path.startswith("app/"):
        return "app"
    if relative_path.startswith("scripts/"):
        return "scripts"
    return "root"


def _iter_searchable_files(repo_root):
    files = []
    for root_path, dir_names, file_names in os.walk(repo_root, topdown=True):
        dir_names[:] = [
            dir_name
            for dir_name in dir_names
            if dir_name not in EXCLUDED_DIRECTORY_NAMES and not dir_name.startswith(".venv")
        ]
        for file_name in file_names:
            suffix = Path(file_name).suffix.lower()
            if suffix not in SEARCHABLE_EXTENSIONS:
                continue
            files.append(Path(root_path) / file_name)
    return sorted(files, key=lambda path: _relative_path_text(path, repo_root))


def _extract_title(relative_path, text):
    if relative_path.endswith(".md"):
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]
    return relative_path


def _token_count(text):
    return len(TOKEN_PATTERN.findall(text))


def _preview_for_query(text, query, limit=160):
    lowered_query = str(query or "").lower()
    for line_number, line in enumerate(text.splitlines(), start=1):
        if lowered_query in line.lower():
            snippet = line.strip()
            if len(snippet) > limit:
                snippet = f"{snippet[: limit - 3]}..."
            return {"line": line_number, "text": snippet}
    preview_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if len(preview_line) > limit:
        preview_line = f"{preview_line[: limit - 3]}..."
    return {"line": 1 if preview_line else None, "text": preview_line}


def _run_git_command(repo_root, *args):
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _run_shell_command(command, cwd=None, env=None):
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def _run_git_status(repo_root):
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return []

    entries = completed.stdout.split("\0")
    changed_files = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2].strip() or "??"
        path_text = entry[3:]
        change_record = {
            "status": status,
            "path": path_text,
            "area": _file_area(path_text),
        }
        if "R" in status or "C" in status:
            source_path = entries[index] if index < len(entries) else ""
            if source_path:
                change_record["source_path"] = source_path
                index += 1
        changed_files.append(change_record)
    return changed_files


def _collect_recent_commits(repo_root, limit=5):
    completed = subprocess.run(
        [
            "git",
            "log",
            f"--max-count={max(1, int(limit))}",
            "--date=short",
            "--pretty=format:%H%x1f%h%x1f%ad%x1f%an%x1f%s",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return []

    commits = []
    for line in completed.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) != 5:
            continue
        commits.append(
            {
                "commit": parts[0],
                "short_commit": parts[1],
                "date": parts[2],
                "author": parts[3],
                "subject": parts[4],
            }
        )
    return commits


def _counts_from_items(items, key_name):
    counts = {}
    for item in items:
        key_value = str(item.get(key_name) or "unknown")
        counts[key_value] = counts.get(key_value, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


def _get_change_record(workspace, path_text):
    for item in workspace.changed_files:
        if item.get("path") == path_text:
            return item
    return {}


def _symbols_for_path(workspace, path_text):
    symbols = [record for record in workspace.symbol_records if record.get("path") == path_text]
    return sorted(symbols, key=lambda record: (record.get("line") or 0, record.get("qualified_name") or record.get("name") or ""))


def _parse_changed_line_numbers(diff_text):
    line_numbers = set()
    for line in str(diff_text or "").splitlines():
        match = DIFF_HUNK_PATTERN.match(line)
        if not match:
            continue
        start_line = max(1, int(match.group(1) or 1))
        line_count = int(match.group(2) or "1")
        if line_count <= 0:
            line_numbers.add(start_line)
            continue
        for line_number in range(start_line, start_line + line_count):
            line_numbers.add(line_number)
    return sorted(line_numbers)


def _collect_changed_line_numbers(repo_root, path_text):
    completed = _run_shell_command(["git", "diff", "--unified=0", "--", path_text], cwd=repo_root)
    if completed.returncode != 0:
        return []
    return _parse_changed_line_numbers(completed.stdout)


def _nearest_symbols(symbols, changed_lines, limit=4):
    if not symbols or not changed_lines:
        return []

    scored_symbols = []
    for symbol in symbols:
        try:
            symbol_line = int(symbol.get("line") or 0)
        except (TypeError, ValueError):
            symbol_line = 0
        if symbol_line <= 0:
            continue
        distance = min(abs(symbol_line - changed_line) for changed_line in changed_lines)
        scored_symbols.append((distance, symbol_line, symbol.get("qualified_name") or symbol.get("name") or "", symbol))

    scored_symbols.sort(key=lambda item: (item[0], item[1], item[2]))
    return [item[3] for item in scored_symbols[: max(1, int(limit))]]


def _collect_touched_symbols(workspace, records):
    touched_symbols = {}
    for record in records:
        path_text = record.get("path")
        if not path_text:
            continue
        symbols = _symbols_for_path(workspace, path_text)
        if not symbols:
            continue

        change_record = _get_change_record(workspace, path_text)
        status_text = str(change_record.get("status") or "")
        if "?" in status_text or "A" in status_text:
            touched_symbols[path_text] = symbols[:8]
            continue

        changed_lines = _collect_changed_line_numbers(workspace.repo_root, path_text)
        if not changed_lines:
            touched_symbols[path_text] = symbols[:4]
            continue

        matches = []
        for symbol in symbols:
            try:
                symbol_line = int(symbol.get("line") or 0)
            except (TypeError, ValueError):
                symbol_line = 0
            if symbol_line <= 0:
                continue
            if any(abs(symbol_line - changed_line) <= 3 for changed_line in changed_lines):
                matches.append(symbol)

        touched_symbols[path_text] = matches[:8] if matches else _nearest_symbols(symbols, changed_lines)
    return touched_symbols


def _format_symbol_label(symbol_record):
    symbol_name = symbol_record.get("qualified_name") or symbol_record.get("name") or "(unknown)"
    symbol_kind = symbol_record.get("kind")
    if symbol_kind:
        return f"{symbol_name} ({symbol_kind})"
    return str(symbol_name)


def _summarize_symbol_labels(symbol_records, limit=4):
    labels = []
    seen = set()
    for symbol_record in symbol_records:
        label = _format_symbol_label(symbol_record)
        if label in seen:
            continue
        labels.append(label)
        seen.add(label)
        if len(labels) >= max(1, int(limit)):
            break
    remaining = max(0, len({ _format_symbol_label(symbol_record) for symbol_record in symbol_records }) - len(labels))
    if remaining > 0:
        labels.append(f"and {remaining} more")
    return ", ".join(labels)


def _collect_area_symbol_summary(records, touched_symbols):
    area_symbols = {}
    for record in records:
        path_text = record.get("path")
        area_name = record.get("area") or _file_area(path_text or "")
        symbols = touched_symbols.get(path_text, [])
        if not symbols:
            continue
        area_symbols.setdefault(area_name, []).extend(symbols)
    return area_symbols


def _recent_commit_subjects(workspace, limit=5):
    return [
        str(commit.get("subject") or "").strip()
        for commit in workspace.snapshot.get("git", {}).get("recent_commits", [])[: max(1, int(limit))]
        if str(commit.get("subject") or "").strip()
    ]


def _collect_git_snapshot(repo_root):
    branch_name = _run_git_command(repo_root, "rev-parse", "--abbrev-ref", "HEAD") or "unknown"
    changed_files = _run_git_status(repo_root)
    return {
        "branch": branch_name,
        "changed_files": changed_files,
        "changed_count": len(changed_files),
        "status_counts": _counts_from_items(changed_files, "status"),
        "area_counts": _counts_from_items(changed_files, "area"),
        "recent_commits": _collect_recent_commits(repo_root, limit=5),
    }


def _load_symbol_payload(repo_root):
    symbol_output_dir = (repo_root / SYMBOL_INDEX_OUTPUT_DIR).resolve()
    generate_symbol_index(repo_root=repo_root, output_dir=symbol_output_dir)
    symbol_json_path = symbol_output_dir / SYMBOL_INDEX_JSON_NAME
    try:
        return json.loads(symbol_json_path.read_text(encoding="utf-8")), symbol_json_path
    except OSError as exc:
        raise ProjectLibrarianError(f"Unable to read symbol index at {symbol_json_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProjectLibrarianError(f"Unable to parse symbol index at {symbol_json_path}: {exc}") from exc


def _flatten_symbol_payload(symbol_payload):
    symbol_records = []
    for file_entry in symbol_payload.get("files", []):
        file_path = file_entry.get("path", "")
        module_name = file_entry.get("module_name")

        for variable_entry in file_entry.get("variables", []):
            symbol_records.append(
                {
                    "path": file_path,
                    "line": variable_entry.get("line"),
                    "kind": variable_entry.get("kind"),
                    "name": variable_entry.get("name"),
                    "qualified_name": variable_entry.get("name"),
                    "signature": variable_entry.get("name"),
                    "doc_summary": None,
                    "context": module_name,
                }
            )

        for function_entry in file_entry.get("functions", []):
            symbol_records.append(
                {
                    "path": file_path,
                    "line": function_entry.get("line"),
                    "kind": function_entry.get("kind"),
                    "name": function_entry.get("name"),
                    "qualified_name": function_entry.get("name"),
                    "signature": function_entry.get("signature"),
                    "doc_summary": function_entry.get("doc_summary"),
                    "context": module_name,
                }
            )

        for class_entry in file_entry.get("classes", []):
            class_name = class_entry.get("name")
            symbol_records.append(
                {
                    "path": file_path,
                    "line": class_entry.get("line"),
                    "kind": class_entry.get("kind"),
                    "name": class_name,
                    "qualified_name": class_name,
                    "signature": class_name,
                    "doc_summary": class_entry.get("doc_summary"),
                    "context": module_name,
                }
            )
            for attribute_entry in class_entry.get("attributes", []):
                symbol_records.append(
                    {
                        "path": file_path,
                        "line": attribute_entry.get("line"),
                        "kind": attribute_entry.get("kind"),
                        "name": attribute_entry.get("name"),
                        "qualified_name": f"{class_name}.{attribute_entry.get('name')}",
                        "signature": attribute_entry.get("name"),
                        "doc_summary": None,
                        "context": class_name,
                    }
                )
            for method_entry in class_entry.get("methods", []):
                symbol_records.append(
                    {
                        "path": file_path,
                        "line": method_entry.get("line"),
                        "kind": method_entry.get("kind"),
                        "name": method_entry.get("name"),
                        "qualified_name": f"{class_name}.{method_entry.get('name')}",
                        "signature": method_entry.get("signature"),
                        "doc_summary": method_entry.get("doc_summary"),
                        "context": class_name,
                    }
                )
    return symbol_records


def _build_file_records(repo_root):
    file_records = []
    corpus_records = {}
    total_bytes = 0
    for path in _iter_searchable_files(repo_root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            raise ProjectLibrarianError(f"Unable to read {path}: {exc}") from exc

        stat_result = path.stat()
        relative_path = _relative_path_text(path, repo_root)
        total_bytes += stat_result.st_size
        corpus_records[relative_path] = text
        file_records.append(
            {
                "path": relative_path,
                "area": _file_area(relative_path),
                "title": _extract_title(relative_path, text),
                "line_count": len(text.splitlines()),
                "size_bytes": stat_result.st_size,
                "modified_at": datetime.fromtimestamp(stat_result.st_mtime, tz=timezone.utc).isoformat(),
                "token_count": _token_count(text),
            }
        )
    return file_records, corpus_records, total_bytes


def _path_score_adjustment(path_text):
    if path_text.startswith("docs/ai-delegation/archive/"):
        return -30
    if path_text.startswith("app/"):
        return 20
    if path_text.startswith("docs/help/") or path_text == "README.md":
        return 15
    if path_text.startswith("docs/"):
        return 5
    return 0


def build_librarian_snapshot(repo_root=None, output_dir=None):
    repo_root = Path(repo_root or _repo_root_from_here()).resolve()
    output_dir = _resolve_output_dir(repo_root, output_dir)

    try:
        symbol_payload, symbol_json_path = _load_symbol_payload(repo_root)
    except SymbolIndexError as exc:
        raise ProjectLibrarianError(f"Unable to refresh symbol index for librarian: {exc}") from exc

    symbol_records = _flatten_symbol_payload(symbol_payload)
    file_records, corpus_records, total_bytes = _build_file_records(repo_root)
    git_snapshot = _collect_git_snapshot(repo_root)

    snapshot = {
        "snapshot_version": SNAPSHOT_VERSION,
        "generated_at": _utc_now_text(),
        "repo_root": str(repo_root),
        "summary": {
            "files": len(file_records),
            "symbols": len(symbol_records),
            "bytes": total_bytes,
            "changed_files": git_snapshot["changed_count"],
            "history_entries": 0,
        },
        "symbol_index_path": str(symbol_json_path),
        "corpus_path": str(output_dir / CORPUS_NAME),
        "git": git_snapshot,
        "files": file_records,
        "symbols": symbol_records,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = output_dir / SNAPSHOT_NAME
    history_path = output_dir / HISTORY_NAME
    corpus_path = output_dir / CORPUS_NAME
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    corpus_path.write_text(json.dumps(corpus_records), encoding="utf-8")

    history_record = {
        "generated_at": snapshot["generated_at"],
        "branch": git_snapshot["branch"],
        "changed_count": git_snapshot["changed_count"],
        "changed_files": git_snapshot["changed_files"],
        "status_counts": git_snapshot.get("status_counts", {}),
        "area_counts": git_snapshot.get("area_counts", {}),
        "recent_commits": git_snapshot.get("recent_commits", []),
        "summary": snapshot["summary"],
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(history_record) + "\n")

    history_entries = len(_load_history(repo_root=repo_root, output_dir=output_dir))
    snapshot["summary"]["history_entries"] = history_entries
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    return {
        "snapshot": snapshot,
        "snapshot_path": snapshot_path,
        "history_path": history_path,
        "corpus_path": corpus_path,
    }


def refresh_librarian_snapshot(repo_root=None, output_dir=None):
    return build_librarian_snapshot(repo_root=repo_root, output_dir=output_dir)


def _load_snapshot(repo_root=None, output_dir=None, refresh_if_missing=False):
    repo_root = Path(repo_root or _repo_root_from_here()).resolve()
    output_dir = _resolve_output_dir(repo_root, output_dir)
    snapshot_path = output_dir / SNAPSHOT_NAME
    if not snapshot_path.exists():
        if refresh_if_missing:
            return build_librarian_snapshot(repo_root=repo_root, output_dir=output_dir)["snapshot"]
        raise ProjectLibrarianError(f"Snapshot not found at {snapshot_path}. Run refresh first.")
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProjectLibrarianError(f"Unable to read librarian snapshot: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProjectLibrarianError(f"Unable to parse librarian snapshot: {exc}") from exc
    snapshot.setdefault("summary", {})
    snapshot["summary"].setdefault("history_entries", len(_load_history(repo_root=repo_root, output_dir=output_dir)))
    snapshot.setdefault("git", {})
    snapshot["git"].setdefault("changed_files", [])
    snapshot["git"].setdefault("status_counts", _counts_from_items(snapshot["git"].get("changed_files", []), "status"))
    snapshot["git"].setdefault("area_counts", _counts_from_items(snapshot["git"].get("changed_files", []), "area"))
    snapshot["git"].setdefault("recent_commits", [])
    return snapshot


def _load_corpus(repo_root=None, output_dir=None, refresh_if_missing=False):
    repo_root = Path(repo_root or _repo_root_from_here()).resolve()
    output_dir = _resolve_output_dir(repo_root, output_dir)
    corpus_path = output_dir / CORPUS_NAME
    if not corpus_path.exists():
        if refresh_if_missing:
            build_librarian_snapshot(repo_root=repo_root, output_dir=output_dir)
            return _load_corpus(repo_root=repo_root, output_dir=output_dir, refresh_if_missing=False)
        raise ProjectLibrarianError(f"Search corpus not found at {corpus_path}. Run refresh first.")
    try:
        return json.loads(corpus_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ProjectLibrarianError(f"Unable to read search corpus: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ProjectLibrarianError(f"Unable to parse search corpus: {exc}") from exc


def _load_history(repo_root=None, output_dir=None):
    repo_root = Path(repo_root or _repo_root_from_here()).resolve()
    output_dir = _resolve_output_dir(repo_root, output_dir)
    history_path = output_dir / HISTORY_NAME
    if not history_path.exists():
        return []

    records = []
    try:
        with history_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                raw_line = line.strip()
                if not raw_line:
                    continue
                try:
                    records.append(json.loads(raw_line))
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        raise ProjectLibrarianError(f"Unable to read change history at {history_path}: {exc}") from exc
    return records


def _normalize_status_filter(status_filter):
    if not status_filter:
        return set()
    tokens = STATUS_TOKEN_PATTERN.findall(str(status_filter).upper())
    return {token for token in tokens if token}


def _matches_common_filters(path_text, area=None, path_filter=None, changed_only=False, changed_paths=None):
    candidate_path = str(path_text or "")
    if area and _file_area(candidate_path) != area:
        return False
    if path_filter and path_filter.lower() not in candidate_path.lower():
        return False
    if changed_only and candidate_path not in (changed_paths or set()):
        return False
    return True


def _score_text_record(record, file_text, query_tokens, query_text, changed_paths=None):
    searchable_parts = [record.get("path", ""), record.get("title", ""), file_text]
    searchable_text = "\n".join(searchable_parts).lower()
    if query_text not in searchable_text and not all(token in searchable_text for token in query_tokens):
        return None

    score = 0
    path_text = record.get("path", "").lower()
    title_text = record.get("title", "").lower()
    if query_text in path_text:
        score += 80
    if query_text in title_text:
        score += 50
    if query_text in file_text.lower():
        score += 20
    for token in query_tokens:
        if token in path_text:
            score += 15
        elif token in title_text:
            score += 10
        elif token in searchable_text:
            score += 5
    score += _path_score_adjustment(record.get("path", ""))
    preview = _preview_for_query(file_text, query_text)
    return {
        "type": "file",
        "score": score,
        "path": record.get("path"),
        "line": preview.get("line"),
        "title": record.get("title"),
        "preview": preview.get("text"),
        "area": record.get("area"),
        "changed": record.get("path") in (changed_paths or set()),
    }


def _score_symbol_record(record, query_tokens, query_text, changed_paths=None):
    searchable_text = " ".join(
        str(part or "")
        for part in (
            record.get("name"),
            record.get("qualified_name"),
            record.get("signature"),
            record.get("doc_summary"),
            record.get("path"),
        )
    ).lower()
    if query_text not in searchable_text and not all(token in searchable_text for token in query_tokens):
        return None

    score = 0
    if query_text in str(record.get("qualified_name", "")).lower():
        score += 90
    if query_text in str(record.get("name", "")).lower():
        score += 60
    if query_text in str(record.get("signature", "")).lower():
        score += 30
    for token in query_tokens:
        if token in searchable_text:
            score += 10
    score += _path_score_adjustment(record.get("path", ""))
    return {
        "type": "symbol",
        "score": score,
        "path": record.get("path"),
        "line": record.get("line"),
        "title": record.get("qualified_name"),
        "preview": record.get("signature") or record.get("doc_summary") or record.get("kind"),
        "kind": record.get("kind"),
        "area": _file_area(record.get("path", "")),
        "changed": record.get("path") in (changed_paths or set()),
    }


def search_snapshot(snapshot, corpus, query, scope="all", limit=20, area=None, changed_only=False, path_filter=None):
    query_text = str(query or "").strip().lower()
    if not query_text:
        return []
    query_tokens = [token.lower() for token in TOKEN_PATTERN.findall(query_text)] or [query_text]
    changed_paths = {item.get("path") for item in snapshot.get("git", {}).get("changed_files", []) if item.get("path")}
    results = []

    if scope in {"all", "files"}:
        for record in snapshot.get("files", []):
            path_text = record.get("path", "")
            if not _matches_common_filters(path_text, area=area, path_filter=path_filter, changed_only=changed_only, changed_paths=changed_paths):
                continue
            file_text = corpus.get(path_text, "")
            scored = _score_text_record(record, file_text, query_tokens, query_text, changed_paths=changed_paths)
            if scored is not None:
                results.append(scored)

    if scope in {"all", "symbols"}:
        for record in snapshot.get("symbols", []):
            path_text = record.get("path", "")
            if not _matches_common_filters(path_text, area=area, path_filter=path_filter, changed_only=changed_only, changed_paths=changed_paths):
                continue
            scored = _score_symbol_record(record, query_tokens, query_text, changed_paths=changed_paths)
            if scored is not None:
                results.append(scored)

    results.sort(key=lambda item: (-item["score"], item.get("path") or "", item.get("line") or 0))
    return results[: max(1, int(limit))]


def format_search_results(results):
    if not results:
        return "No results found."
    lines = []
    for index, result in enumerate(results, start=1):
        location = result.get("path") or "(unknown)"
        if result.get("line"):
            location = f"{location}:{result['line']}"
        title = result.get("title") or "(untitled)"
        preview = result.get("preview") or ""
        kind = result.get("type")
        if result.get("kind"):
            kind = f"{kind}/{result['kind']}"
        changed_marker = " [changed]" if result.get("changed") else ""
        lines.append(f"{index}. [{kind}] {title}{changed_marker} -> {location}")
        if preview:
            lines.append(f"   {preview}")
    return "\n".join(lines)


def _filter_changed_files(snapshot, status_filter=None, area=None, path_filter=None):
    status_tokens = _normalize_status_filter(status_filter)
    filtered = []
    for item in snapshot.get("git", {}).get("changed_files", []):
        path_text = item.get("path", "")
        if area and item.get("area") != area:
            continue
        if path_filter and path_filter.lower() not in path_text.lower():
            continue
        if status_tokens and not any(token in str(item.get("status", "")).upper() for token in status_tokens):
            continue
        filtered.append(item)
    return filtered


def format_change_report(snapshot, limit=20, status_filter=None, area=None, path_filter=None, include_commits=True):
    git_snapshot = snapshot.get("git", {})
    changed_files = _filter_changed_files(snapshot, status_filter=status_filter, area=area, path_filter=path_filter)
    if not changed_files:
        return "No tracked git changes in the current snapshot for the selected filters."

    lines = [
        f"Branch: {git_snapshot.get('branch', 'unknown')}",
        f"Changed Files: {len(changed_files)} of {git_snapshot.get('changed_count', len(changed_files))}",
    ]

    status_counts = _counts_from_items(changed_files, "status")
    if status_counts:
        lines.append("Statuses: " + ", ".join(f"{status}={count}" for status, count in status_counts.items()))
    area_counts = _counts_from_items(changed_files, "area")
    if area_counts:
        lines.append("Areas: " + ", ".join(f"{area_name}={count}" for area_name, count in area_counts.items()))

    for item in changed_files[: max(1, int(limit))]:
        source_path = item.get("source_path")
        if source_path:
            lines.append(f"- {item.get('status', '??')} [{item.get('area', 'root')}]: {source_path} -> {item.get('path', '')}")
        else:
            lines.append(f"- {item.get('status', '??')} [{item.get('area', 'root')}]: {item.get('path', '')}")
    remaining = len(changed_files) - min(len(changed_files), max(1, int(limit)))
    if remaining > 0:
        lines.append(f"- ... {remaining} more")

    if include_commits:
        commits = git_snapshot.get("recent_commits", [])
        if commits:
            lines.append("Recent Commits:")
            for commit in commits[:3]:
                lines.append(
                    f"- {commit.get('short_commit', '')} {commit.get('date', '')} {commit.get('subject', '')} ({commit.get('author', '')})"
                )
    return "\n".join(lines)


def format_history_report(history_records, limit=10):
    if not history_records:
        return "No recorded librarian history yet. Run refresh first."

    lines = []
    for index, record in enumerate(reversed(history_records[-max(1, int(limit)):]), start=1):
        generated_at = str(record.get("generated_at", ""))
        branch = record.get("branch", "unknown")
        changed_count = record.get("changed_count", 0)
        area_counts = record.get("area_counts", {})
        areas_text = ", ".join(f"{area_name}={count}" for area_name, count in list(area_counts.items())[:3]) or "none"
        lines.append(f"{index}. {generated_at} | branch={branch} | changed={changed_count} | areas={areas_text}")
    return "\n".join(lines)


def format_workspace_stats(workspace):
    summary = workspace.snapshot.get("summary", {})
    git_snapshot = workspace.snapshot.get("git", {})
    lines = [
        f"Repo Root: {workspace.repo_root}",
        f"Files: {summary.get('files', 0)}",
        f"Symbols: {summary.get('symbols', 0)}",
        f"Bytes Indexed: {summary.get('bytes', 0)}",
        f"Branch: {git_snapshot.get('branch', 'unknown')}",
        f"Changed Files: {summary.get('changed_files', 0)}",
        f"History Entries: {summary.get('history_entries', len(workspace.history))}",
    ]
    if git_snapshot.get("status_counts"):
        lines.append(
            "Status Counts: "
            + ", ".join(f"{status}={count}" for status, count in git_snapshot.get("status_counts", {}).items())
        )
    if git_snapshot.get("area_counts"):
        lines.append(
            "Area Counts: "
            + ", ".join(f"{area_name}={count}" for area_name, count in git_snapshot.get("area_counts", {}).items())
        )
    return "\n".join(lines)


def _format_repl_welcome(workspace):
    summary = workspace.snapshot.get("summary", {})
    branch_name = workspace.snapshot.get("git", {}).get("branch", "unknown")
    changed_files = summary.get("changed_files", 0)
    lines = [
        "Project Librarian loaded in memory.",
        f"Repo: {workspace.repo_root.name} | Branch: {branch_name} | Files: {summary.get('files', 0)} | Symbols: {summary.get('symbols', 0)} | Changed: {changed_files}",
        "",
        "Examples:",
        "- search layout manager",
        "- symbols LayoutManagerController",
        "- changes",
        "- history",
        "- show README.md",
        "- docs-draft",
        "- changelog-draft",
        "- ai-models",
        "- ai-doctor",
        "- refresh",
        "- stats",
        "- help",
        "- quit",
        "",
        "Tip: use explicit CLI subcommands outside the REPL when you need filters like --changed-only, --area, or --status.",
        "",
        "Commands: search <query> | symbols <query> | files <query> | changes | history | show <path> | docs-draft | changelog-draft | ai-models | ai-doctor | refresh | stats | quit",
    ]
    return "\n".join(lines)


def _resolve_workspace_path(workspace, path_text):
    normalized = str(path_text or "").strip().replace("\\", "/")
    if not normalized:
        raise ProjectLibrarianError("A file path is required.")

    all_paths = sorted(workspace.corpus.keys())
    if normalized in workspace.corpus:
        return normalized

    suffix_matches = [candidate for candidate in all_paths if candidate.endswith(normalized)]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    if len(suffix_matches) > 1:
        raise ProjectLibrarianError(
            "Path is ambiguous. Matches: " + ", ".join(suffix_matches[:10])
        )

    contains_matches = [candidate for candidate in all_paths if normalized.lower() in candidate.lower()]
    if len(contains_matches) == 1:
        return contains_matches[0]
    if len(contains_matches) > 1:
        raise ProjectLibrarianError(
            "Path is ambiguous. Matches: " + ", ".join(contains_matches[:10])
        )
    raise ProjectLibrarianError(f"No indexed file matched '{normalized}'.")


def show_file_excerpt(workspace, path_text, query=None, line=None, context=3):
    resolved_path = _resolve_workspace_path(workspace, path_text)
    text = workspace.corpus.get(resolved_path, "")
    all_lines = text.splitlines()
    if not all_lines:
        return f"{resolved_path}\n(empty file)"

    if query:
        preview = _preview_for_query(text, query, limit=500)
        target_line = preview.get("line") or 1
    else:
        target_line = max(1, int(line or 1))

    start_line = max(1, target_line - max(0, int(context)))
    end_line = min(len(all_lines), target_line + max(0, int(context)))
    excerpt_lines = [f"{resolved_path}"]
    for line_number in range(start_line, end_line + 1):
        marker = ">" if line_number == target_line else " "
        excerpt_lines.append(f"{marker} {line_number:>4}: {all_lines[line_number - 1]}")
    return "\n".join(excerpt_lines)


def _changed_file_records(workspace, changed_only=True):
    if changed_only:
        return [workspace.file_lookup[path_text] for path_text in sorted(workspace.changed_paths) if path_text in workspace.file_lookup]
    return list(workspace.file_records)


def _records_grouped_by_area(records):
    grouped = {}
    for record in records:
        area = record.get("area") or _file_area(record.get("path", ""))
        grouped.setdefault(area, []).append(record)
    return grouped


def _summarize_record_names(records, limit=4):
    labels = []
    for record in records[:limit]:
        labels.append(record.get("path") or record.get("title") or "(unknown)")
    summary = ", ".join(labels)
    remaining = len(records) - min(len(records), limit)
    if remaining > 0:
        summary += f", and {remaining} more"
    return summary


def _draft_bullet_for_area(area_name, records, symbol_records=None):
    summary = _summarize_record_names(records)
    if area_name == "controllers":
        message = f"Updated controller workflows in {summary}."
    elif area_name == "models":
        message = f"Updated model and data-handling logic in {summary}."
    elif area_name == "views":
        message = f"Updated view and interaction behavior in {summary}."
    elif area_name == "app":
        message = f"Updated app-level services and module entry points in {summary}."
    elif area_name == "docs":
        message = f"Refreshed documentation sources in {summary}."
    elif area_name == "scripts":
        message = f"Updated project automation scripts in {summary}."
    else:
        message = f"Updated project-level files in {summary}."

    symbol_summary = _summarize_symbol_labels(symbol_records or [])
    if symbol_summary:
        return f"{message[:-1]} Key symbols touched: {symbol_summary}."
    return message


def _suggest_docs(records):
    suggestions = []
    seen = set()
    for area_name in _records_grouped_by_area(records):
        for candidate in DOC_SUGGESTIONS_BY_AREA.get(area_name, []):
            if candidate not in seen:
                suggestions.append(candidate)
                seen.add(candidate)
    return suggestions


def _ensure_output_subdir(output_dir, directory_name):
    target_dir = output_dir / directory_name
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def _write_generated_output(output_dir, directory_name, prefix, content, output_path=None, output_base_dir=None):
    if output_path:
        target_path = Path(output_path)
        if not target_path.is_absolute():
            base_dir = Path(output_base_dir or output_dir)
            target_path = (base_dir / target_path).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = _ensure_output_subdir(output_dir, directory_name)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        target_path = target_dir / f"{prefix}_{stamp}.md"
    target_path.write_text(content, encoding="utf-8")
    return target_path


def _resolve_repo_path(repo_root, target_path):
    candidate = Path(target_path)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    return candidate


def _upsert_markdown_block(existing_text, content, start_marker, end_marker):
    managed_block = f"{start_marker}\n{content.rstrip()}\n{end_marker}"
    if start_marker in existing_text and end_marker in existing_text:
        pattern = re.compile(rf"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL)
        updated_text = pattern.sub(managed_block, existing_text, count=1)
        return updated_text.rstrip() + "\n"

    if not existing_text.strip():
        return managed_block + "\n"
    return existing_text.rstrip() + "\n\n" + managed_block + "\n"


def apply_docs_update(repo_root, content, target_path=README_TARGET_NAME):
    resolved_target = _resolve_repo_path(repo_root, target_path)
    existing_text = resolved_target.read_text(encoding="utf-8") if resolved_target.exists() else ""
    updated_text = _upsert_markdown_block(existing_text, content, DOC_BLOCK_START, DOC_BLOCK_END)
    resolved_target.write_text(updated_text, encoding="utf-8")
    return resolved_target


def _upsert_changelog_entry(existing_text, entry_text, version_label):
    headings = list(CHANGELOG_HEADING_PATTERN.finditer(existing_text))
    normalized_entry = entry_text.rstrip() + "\n\n"
    for index, match in enumerate(headings):
        if match.group("version") != str(version_label):
            continue
        start_index = match.start()
        end_index = headings[index + 1].start() if index + 1 < len(headings) else len(existing_text)
        updated_text = existing_text[:start_index] + normalized_entry + existing_text[end_index:].lstrip("\n")
        return updated_text.rstrip() + "\n"

    if headings:
        insertion_index = headings[0].start()
        prefix = existing_text[:insertion_index].rstrip() + "\n\n"
        suffix = existing_text[insertion_index:].lstrip("\n")
        return (prefix + normalized_entry + suffix).rstrip() + "\n"

    if not existing_text.strip():
        return normalized_entry.rstrip() + "\n"
    return existing_text.rstrip() + "\n\n" + normalized_entry.rstrip() + "\n"


def apply_changelog_update(repo_root, content, version_label, target_path=CHANGELOG_TARGET_NAME):
    resolved_target = _resolve_repo_path(repo_root, target_path)
    existing_text = resolved_target.read_text(encoding="utf-8") if resolved_target.exists() else ""
    updated_text = _upsert_changelog_entry(existing_text, content, version_label)
    resolved_target.write_text(updated_text, encoding="utf-8")
    return resolved_target


def _parse_ollama_models(raw_output):
    model_names = []
    for line in str(raw_output or "").splitlines()[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        model_name = stripped.split()[0]
        if model_name and model_name not in model_names:
            model_names.append(model_name)
    return model_names


def _select_recommended_model(models, preferred_model=None):
    preferred = str(preferred_model or "").strip()
    if preferred and preferred in models:
        return preferred

    ranked_groups = [
        [model for model in models if "qwen" in model.lower() and "coder" in model.lower()],
        [model for model in models if "qwen" in model.lower()],
        list(models),
    ]
    for group in ranked_groups:
        if group:
            return group[0]
    return None


def collect_ai_runtime_status(repo_root, preferred_model=DEFAULT_AI_MODEL, ollama_host=None):
    status = {
        "repo_root": str(repo_root),
        "ollama_host": str(ollama_host or os.environ.get("OLLAMA_HOST") or "default"),
        "preferred_model": preferred_model,
        "ollama_path": shutil.which("ollama"),
        "delegate_script": str(repo_root / "scripts" / "qwen_delegate.sh"),
        "smoke_script": str(repo_root / "scripts" / "local_ai_smoke_test.sh"),
        "models": [],
        "ollama_reachable": False,
        "preferred_model_available": False,
        "recommended_model": None,
        "issues": [],
    }

    delegate_path = Path(status["delegate_script"])
    smoke_path = Path(status["smoke_script"])
    status["delegate_script_exists"] = delegate_path.exists()
    status["delegate_script_executable"] = os.access(delegate_path, os.X_OK) if delegate_path.exists() else False
    status["smoke_script_exists"] = smoke_path.exists()

    if not status["ollama_path"]:
        status["issues"].append("ollama is not installed or is not on PATH.")
        return status

    env = os.environ.copy()
    if ollama_host:
        env["OLLAMA_HOST"] = str(ollama_host)

    completed = _run_shell_command(["ollama", "list"], cwd=repo_root, env=env)
    if completed.returncode != 0:
        error_text = (completed.stderr or completed.stdout or "Unable to query ollama.").strip()
        status["issues"].append(error_text)
        return status

    status["ollama_reachable"] = True
    status["models"] = _parse_ollama_models(completed.stdout)
    status["preferred_model_available"] = preferred_model in status["models"]
    status["recommended_model"] = _select_recommended_model(status["models"], preferred_model=preferred_model)
    if not status["models"]:
        status["issues"].append("Ollama is reachable but no local models were listed.")
    if not status["delegate_script_exists"]:
        status["issues"].append(f"AI delegate script is missing: {delegate_path}")
    elif not status["delegate_script_executable"]:
        status["issues"].append(f"AI delegate script is not executable: {delegate_path}")
    if preferred_model and not status["preferred_model_available"]:
        status["issues"].append(f"Preferred model is not available locally: {preferred_model}")
    return status


def format_ai_model_list(ai_status):
    models = ai_status.get("models", [])
    if not models:
        return "No local Ollama models were found for the selected host."
    lines = [f"Ollama Host: {ai_status.get('ollama_host', 'default')}", "Models:"]
    recommended_model = ai_status.get("recommended_model")
    preferred_model = ai_status.get("preferred_model")
    for model_name in models:
        suffix_bits = []
        if model_name == preferred_model:
            suffix_bits.append("preferred")
        if model_name == recommended_model:
            suffix_bits.append("recommended")
        suffix = f" [{' | '.join(suffix_bits)}]" if suffix_bits else ""
        lines.append(f"- {model_name}{suffix}")
    return "\n".join(lines)


def format_ai_status_report(ai_status):
    lines = [
        f"Repo Root: {ai_status.get('repo_root')}",
        f"Ollama Host: {ai_status.get('ollama_host')}",
        f"Ollama Installed: {'yes' if ai_status.get('ollama_path') else 'no'}",
        f"Ollama Reachable: {'yes' if ai_status.get('ollama_reachable') else 'no'}",
        f"Delegate Script: {ai_status.get('delegate_script')}",
        f"Delegate Executable: {'yes' if ai_status.get('delegate_script_executable') else 'no'}",
        f"Smoke Helper Present: {'yes' if ai_status.get('smoke_script_exists') else 'no'}",
        f"Preferred Model: {ai_status.get('preferred_model')}",
        f"Recommended Model: {ai_status.get('recommended_model') or '(none)'}",
    ]
    models = ai_status.get("models", [])
    if models:
        lines.append("Available Models: " + ", ".join(models))
    else:
        lines.append("Available Models: none")
    if ai_status.get("issues"):
        lines.append("Issues:")
        for issue_text in ai_status.get("issues", []):
            lines.append(f"- {issue_text}")
    else:
        lines.append("Issues: none")
    return "\n".join(lines)


def _resolve_ai_model(ai_status, requested_model):
    requested = str(requested_model or "").strip()
    if requested and requested.lower() != "auto":
        if ai_status.get("models") and requested not in ai_status.get("models", []):
            recommended_model = ai_status.get("recommended_model") or "(none)"
            available_models = ", ".join(ai_status.get("models", [])) or "none"
            raise ProjectLibrarianError(
                f"Requested Ollama model is not available locally: {requested}. Available models: {available_models}. Recommended: {recommended_model}."
            )
        return requested

    recommended_model = ai_status.get("recommended_model")
    if recommended_model:
        return recommended_model
    raise ProjectLibrarianError("No local Ollama model is available. Run 'project_librarian.py ai-models' or 'project_librarian.py ai-doctor' first.")


def generate_docs_draft(workspace, title=None, changed_only=True):
    records = _changed_file_records(workspace, changed_only=changed_only)
    grouped = _records_grouped_by_area(records)
    touched_symbols = _collect_touched_symbols(workspace, records)
    area_symbols = _collect_area_symbol_summary(records, touched_symbols)
    commit_subjects = _recent_commit_subjects(workspace)
    branch_name = workspace.snapshot.get("git", {}).get("branch", "unknown")
    lines = [
        f"# {title or 'Project Documentation Update Draft'}",
        "",
        f"- Generated: {workspace.snapshot.get('generated_at', _utc_now_text())}",
        f"- Branch: {branch_name}",
        f"- Scope: {'changed files only' if changed_only else 'full indexed workspace'}",
        "",
        "## Summary",
        "",
        f"- Indexed files: {workspace.snapshot.get('summary', {}).get('files', 0)}",
        f"- Indexed symbols: {workspace.snapshot.get('summary', {}).get('symbols', 0)}",
        f"- Changed files in snapshot: {workspace.snapshot.get('summary', {}).get('changed_files', 0)}",
        "",
        "## Documentation Targets",
        "",
    ]

    suggestions = _suggest_docs(records)
    if suggestions:
        for suggestion in suggestions:
            lines.append(f"- Review or update {suggestion}")
    else:
        lines.append("- No targeted documentation candidates were inferred from the current scope.")

    lines.extend(["", "## Draft Notes", ""])
    if grouped:
        for area_name in AREA_ORDER:
            area_records = grouped.get(area_name, [])
            if not area_records:
                continue
            lines.append(f"- {_draft_bullet_for_area(area_name, area_records, symbol_records=area_symbols.get(area_name, []))}")
    else:
        lines.append("- No tracked files were selected for the documentation draft.")

    lines.extend(["", "## Touched Symbols", ""])
    if touched_symbols:
        for path_text in sorted(touched_symbols):
            symbol_summary = _summarize_symbol_labels(touched_symbols.get(path_text, []), limit=5)
            if symbol_summary:
                lines.append(f"- {path_text}: {symbol_summary}")
    else:
        lines.append("- No symbol-level context was inferred from the current scope.")

    lines.extend(["", "## Recent Commit Context", ""])
    if commit_subjects:
        for subject_text in commit_subjects:
            lines.append(f"- {subject_text}")
    else:
        lines.append("- No recent commit subjects were available.")

    lines.extend(["", "## Files Considered", ""])
    if records:
        for record in records:
            lines.append(f"- [{record.get('area', 'root')}] {record.get('path', '(unknown)')}")
    else:
        lines.append("- No files selected.")
    lines.append("")
    return "\n".join(lines)


def generate_changelog_draft(workspace, version_text=None, release_date=None, changed_only=True):
    records = _changed_file_records(workspace, changed_only=changed_only)
    grouped = _records_grouped_by_area(records)
    touched_symbols = _collect_touched_symbols(workspace, records)
    area_symbols = _collect_area_symbol_summary(records, touched_symbols)
    commit_subjects = _recent_commit_subjects(workspace, limit=4)
    version_label = version_text or "Unreleased"
    date_label = release_date or _today_text()
    lines = [
        f"## [{version_label}] - {date_label}",
        "",
        "### Changed",
        "",
    ]

    if grouped:
        for area_name in AREA_ORDER:
            area_records = grouped.get(area_name, [])
            if not area_records:
                continue
            lines.append(f"- {_draft_bullet_for_area(area_name, area_records, symbol_records=area_symbols.get(area_name, []))}")
    else:
        lines.append("- No tracked changes were available for a changelog draft.")

    lines.extend(["", "### Notes", "", f"- Branch at draft time: {workspace.snapshot.get('git', {}).get('branch', 'unknown')}"])
    lines.append(f"- Snapshot generated at: {workspace.snapshot.get('generated_at', _utc_now_text())}")
    lines.append(f"- Files considered: {len(records)}")
    if commit_subjects:
        lines.append(f"- Recent commit context: {' | '.join(commit_subjects)}")
    lines.append("")
    return "\n".join(lines)


def _build_ai_context(workspace, task, changed_only=True):
    records = _changed_file_records(workspace, changed_only=changed_only)
    lines = [
        "# Project Librarian AI Context",
        "",
        f"Task: {task}",
        f"Generated: {workspace.snapshot.get('generated_at', _utc_now_text())}",
        f"Branch: {workspace.snapshot.get('git', {}).get('branch', 'unknown')}",
        "",
        "## Workspace Summary",
        "",
        format_workspace_stats(workspace),
        "",
        "## Current Changes",
        "",
        format_change_report(workspace.snapshot, limit=50, include_commits=True),
        "",
        "## Files In Scope",
        "",
    ]
    if records:
        for record in records:
            lines.append(f"- [{record.get('area', 'root')}] {record.get('path', '(unknown)')} | {record.get('title', '')}")
    else:
        lines.append("- No files selected.")
    lines.append("")
    return "\n".join(lines)


def run_ai_summary(workspace, task, mode="analysis", model=DEFAULT_AI_MODEL, changed_only=True, ollama_host=None):
    ai_status = collect_ai_runtime_status(workspace.repo_root, preferred_model=model, ollama_host=ollama_host)
    script_path = Path(ai_status.get("delegate_script"))
    if not ai_status.get("delegate_script_exists"):
        raise ProjectLibrarianError(f"AI delegate script not found at {script_path}")
    if not ai_status.get("delegate_script_executable"):
        raise ProjectLibrarianError(f"AI delegate script is not executable: {script_path}")
    if not ai_status.get("ollama_path"):
        raise ProjectLibrarianError("ollama is not installed or is not on PATH.")
    if not ai_status.get("ollama_reachable"):
        issue_text = ai_status.get("issues", ["Unable to query ollama."])[0]
        raise ProjectLibrarianError(
            f"Ollama is not reachable at {ai_status.get('ollama_host')}. {issue_text} Run 'project_librarian.py ai-doctor' for full diagnostics."
        )
    resolved_model = _resolve_ai_model(ai_status, model)

    context_text = _build_ai_context(workspace, task=task, changed_only=changed_only)
    context_path = _write_generated_output(
        workspace.output_dir,
        AI_CONTEXT_DIR_NAME,
        "ai_context",
        context_text,
    )

    command = [
        "bash",
        str(script_path),
        "--task",
        task,
        "--mode",
        mode,
        "--context",
        str(context_path),
        "--model",
        resolved_model,
    ]
    env = os.environ.copy()
    if ollama_host:
        env["OLLAMA_HOST"] = str(ollama_host)

    completed = subprocess.run(
        command,
        cwd=workspace.repo_root,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.returncode != 0:
        error_text = (completed.stderr or completed.stdout or "AI summary failed.").strip()
        raise ProjectLibrarianError(error_text)

    report_path = None
    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("Saved:"):
            report_path = stripped.split(":", 1)[1].strip()
            break
    return {
        "context_path": context_path,
        "report_path": report_path,
        "model": resolved_model,
        "stdout": completed.stdout.strip(),
    }


def run_repl(repo_root=None, output_dir=None, refresh_first=False):
    workspace = LibrarianWorkspace.load(
        repo_root=repo_root,
        output_dir=output_dir,
        refresh_if_missing=True,
        refresh_first=refresh_first,
    )

    print(_format_repl_welcome(workspace))
    while True:
        try:
            raw_command = input("librarian> ").strip()
        except EOFError:
            print()
            return 0
        if not raw_command:
            continue
        try:
            parts = shlex.split(raw_command)
        except ValueError as exc:
            print(f"Command parse error: {exc}")
            continue
        if not parts:
            continue
        command_name = parts[0].lower()
        command_args = parts[1:]

        if command_name in {"quit", "exit"}:
            return 0
        if command_name == "help":
            print(
                "Commands: search <query> | symbols <query> | files <query> | changes | history | show <path> | docs-draft | changelog-draft | ai-models | ai-doctor | refresh | stats | quit"
            )
            continue
        if command_name == "refresh":
            result = workspace.refresh()
            snapshot = result["snapshot"]
            print(
                f"Refreshed snapshot: {snapshot['summary']['files']} files, "
                f"{snapshot['summary']['symbols']} symbols, "
                f"{snapshot['summary']['changed_files']} changed files."
            )
            continue
        if command_name == "stats":
            print(format_workspace_stats(workspace))
            continue
        if command_name == "changes":
            print(format_change_report(workspace.snapshot))
            continue
        if command_name == "history":
            print(format_history_report(workspace.history))
            continue
        if command_name == "show" and command_args:
            print(show_file_excerpt(workspace, command_args[0]))
            continue
        if command_name == "docs-draft":
            draft_path = _write_generated_output(
                workspace.output_dir,
                DRAFTS_DIR_NAME,
                "docs_draft",
                generate_docs_draft(workspace),
            )
            print(f"Saved docs draft: {draft_path}")
            continue
        if command_name == "changelog-draft":
            draft_path = _write_generated_output(
                workspace.output_dir,
                DRAFTS_DIR_NAME,
                "changelog_draft",
                generate_changelog_draft(workspace),
            )
            print(f"Saved changelog draft: {draft_path}")
            continue
        if command_name == "ai-models":
            print(format_ai_model_list(collect_ai_runtime_status(workspace.repo_root)))
            continue
        if command_name == "ai-doctor":
            print(format_ai_status_report(collect_ai_runtime_status(workspace.repo_root)))
            continue
        if command_name in {"search", "symbols", "files"} and command_args:
            query = " ".join(command_args)
            scope = "all" if command_name == "search" else command_name
            print(format_search_results(search_snapshot(workspace.snapshot, workspace.corpus, query, scope=scope)))
            continue
        print("Unknown command. Type 'help' for usage.")


def parse_args():
    parser = argparse.ArgumentParser(description="Refresh and query a local in-memory project librarian.")
    parser.add_argument(
        "--repo-root",
        default=str(_repo_root_from_here()),
        help="Repository root to catalog. Defaults to the current repository.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Directory that receives {SNAPSHOT_NAME}, {CORPUS_NAME}, and {HISTORY_NAME}.",
    )

    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("refresh", help="Refresh the librarian snapshot, corpus, and change history.")

    search_parser = subparsers.add_parser("search", help="Search files and symbols from the current snapshot.")
    search_parser.add_argument("query", help="Query string to search for.")
    search_parser.add_argument("--scope", choices=("all", "files", "symbols"), default="all")
    search_parser.add_argument("--limit", type=int, default=20)
    search_parser.add_argument("--area", choices=AREA_ORDER)
    search_parser.add_argument("--path", dest="path_filter")
    search_parser.add_argument("--changed-only", action="store_true")

    changes_parser = subparsers.add_parser("changes", help="Show changed files recorded in the current snapshot.")
    changes_parser.add_argument("--limit", type=int, default=20)
    changes_parser.add_argument("--status")
    changes_parser.add_argument("--area", choices=AREA_ORDER)
    changes_parser.add_argument("--path", dest="path_filter")
    changes_parser.add_argument("--no-commits", action="store_true", help="Hide recent commit context.")

    history_parser = subparsers.add_parser("history", help="Show recent librarian refresh history.")
    history_parser.add_argument("--limit", type=int, default=10)

    show_parser = subparsers.add_parser("show", help="Show a file excerpt from the RAM-loaded corpus.")
    show_parser.add_argument("path", help="Indexed file path, suffix, or unique substring.")
    show_parser.add_argument("--query", help="Anchor the excerpt around the first matching line.")
    show_parser.add_argument("--line", type=int, help="1-based line to center the excerpt on.")
    show_parser.add_argument("--context", type=int, default=3)

    docs_parser = subparsers.add_parser("docs-draft", help="Generate a documentation update draft from the current snapshot.")
    docs_parser.add_argument("--title")
    docs_parser.add_argument("--all-files", action="store_true", help="Draft from the full indexed workspace instead of only changed files.")
    docs_parser.add_argument("--output")
    docs_parser.add_argument("--apply", action="store_true", help="Write the generated documentation block into a target markdown file.")
    docs_parser.add_argument("--target", default=README_TARGET_NAME, help="Markdown file to update when --apply is used.")

    changelog_parser = subparsers.add_parser("changelog-draft", help="Generate a changelog draft from the current snapshot.")
    changelog_parser.add_argument("--version")
    changelog_parser.add_argument("--date")
    changelog_parser.add_argument("--all-files", action="store_true", help="Draft from the full indexed workspace instead of only changed files.")
    changelog_parser.add_argument("--output")
    changelog_parser.add_argument("--apply", action="store_true", help="Write or replace the release entry in a changelog file.")
    changelog_parser.add_argument("--target", default=CHANGELOG_TARGET_NAME, help="Changelog file to update when --apply is used.")

    ai_parser = subparsers.add_parser("ai-summary", help="Ask the local AI helper to summarize the current workspace and changes.")
    ai_parser.add_argument("--task", default="Summarize the current repository changes and likely next actions.")
    ai_parser.add_argument("--mode", choices=("analysis", "review"), default="analysis")
    ai_parser.add_argument("--model", default=DEFAULT_AI_MODEL)
    ai_parser.add_argument("--all-files", action="store_true", help="Include the full indexed workspace context instead of only changed files.")
    ai_parser.add_argument("--ollama-host", help="Optional OLLAMA_HOST override for local AI calls.")

    ai_models_parser = subparsers.add_parser("ai-models", help="List locally available Ollama models for the selected host.")
    ai_models_parser.add_argument("--model", default=DEFAULT_AI_MODEL, help="Preferred model to compare against the local list.")
    ai_models_parser.add_argument("--ollama-host", help="Optional OLLAMA_HOST override for local AI calls.")

    ai_doctor_parser = subparsers.add_parser("ai-doctor", help="Show Ollama and delegate-script diagnostics for local AI usage.")
    ai_doctor_parser.add_argument("--model", default=DEFAULT_AI_MODEL, help="Preferred model to validate against the local list.")
    ai_doctor_parser.add_argument("--ollama-host", help="Optional OLLAMA_HOST override for local AI calls.")

    repl_parser = subparsers.add_parser("repl", help="Load the project into RAM and interactively search it.")
    repl_parser.add_argument("--refresh", action="store_true", help="Refresh the snapshot before entering the REPL.")

    subparsers.add_parser("stats", help="Show summary information for the current snapshot.")
    return parser.parse_args()


def main():
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = (repo_root / output_dir).resolve()

    if not args.command:
        return run_repl(repo_root=repo_root, output_dir=output_dir, refresh_first=False)

    if args.command == "refresh":
        result = build_librarian_snapshot(repo_root=repo_root, output_dir=output_dir)
        summary = result["snapshot"]["summary"]
        print(
            f"Refreshed project librarian: {summary['files']} files, "
            f"{summary['symbols']} symbols, {summary['changed_files']} changed files."
        )
        print(f"Snapshot: {result['snapshot_path']}")
        print(f"History: {result['history_path']}")
        print(f"Corpus: {result['corpus_path']}")
        return 0

    workspace = LibrarianWorkspace.load(repo_root=repo_root, output_dir=output_dir, refresh_if_missing=True)

    if args.command == "search":
        print(
            format_search_results(
                search_snapshot(
                    workspace.snapshot,
                    workspace.corpus,
                    args.query,
                    scope=args.scope,
                    limit=args.limit,
                    area=args.area,
                    changed_only=args.changed_only,
                    path_filter=args.path_filter,
                )
            )
        )
        return 0

    if args.command == "changes":
        print(
            format_change_report(
                workspace.snapshot,
                limit=args.limit,
                status_filter=args.status,
                area=args.area,
                path_filter=args.path_filter,
                include_commits=not args.no_commits,
            )
        )
        return 0

    if args.command == "history":
        print(format_history_report(workspace.history, limit=args.limit))
        return 0

    if args.command == "show":
        print(show_file_excerpt(workspace, args.path, query=args.query, line=args.line, context=args.context))
        return 0

    if args.command == "docs-draft":
        draft_content = generate_docs_draft(workspace, title=args.title, changed_only=not args.all_files)
        if args.apply:
            target_path = apply_docs_update(repo_root, draft_content, target_path=args.target)
            print(f"Updated docs target: {target_path}")
        else:
            draft_path = _write_generated_output(
                workspace.output_dir,
                DRAFTS_DIR_NAME,
                "docs_draft",
                draft_content,
                output_path=args.output,
                output_base_dir=repo_root,
            )
            print(f"Saved docs draft: {draft_path}")
        return 0

    if args.command == "changelog-draft":
        draft_content = generate_changelog_draft(
            workspace,
            version_text=args.version,
            release_date=args.date,
            changed_only=not args.all_files,
        )
        if args.apply:
            version_label = args.version or "Unreleased"
            target_path = apply_changelog_update(repo_root, draft_content, version_label=version_label, target_path=args.target)
            print(f"Updated changelog target: {target_path}")
        else:
            draft_path = _write_generated_output(
                workspace.output_dir,
                DRAFTS_DIR_NAME,
                "changelog_draft",
                draft_content,
                output_path=args.output,
                output_base_dir=repo_root,
            )
            print(f"Saved changelog draft: {draft_path}")
        return 0

    if args.command == "ai-summary":
        result = run_ai_summary(
            workspace,
            task=args.task,
            mode=args.mode,
            model=args.model,
            changed_only=not args.all_files,
            ollama_host=args.ollama_host,
        )
        print(f"AI context: {result['context_path']}")
        print(f"AI model: {result['model']}")
        if result.get("report_path"):
            print(f"AI report: {result['report_path']}")
        else:
            print(result.get("stdout") or "AI summary completed without a saved report path.")
        return 0

    if args.command == "ai-models":
        print(format_ai_model_list(collect_ai_runtime_status(repo_root, preferred_model=args.model, ollama_host=args.ollama_host)))
        return 0

    if args.command == "ai-doctor":
        print(format_ai_status_report(collect_ai_runtime_status(repo_root, preferred_model=args.model, ollama_host=args.ollama_host)))
        return 0

    if args.command == "stats":
        print(format_workspace_stats(workspace))
        return 0

    if args.command == "repl":
        return run_repl(repo_root=repo_root, output_dir=output_dir, refresh_first=args.refresh)

    raise ProjectLibrarianError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())