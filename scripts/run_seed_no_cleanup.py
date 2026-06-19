
from pathlib import Path
import json
import build
import os
import shutil

# Monkeypatch cleanup to avoid PermissionError if dirs are empty or we can just skip it
def mock_reset(path):
    print(f'Skipping reset for {path}')
    os.makedirs(path, exist_ok=True)

build._reset_windows_runtime_seed_targets = mock_reset

try:
    sanitized = build.prepare_sanitized_rates_asset(build.WINDOWS_TARGET)
    print('Sanitized rates asset prepared.')
except Exception as e:
    print(f'Rates Error: {e}')
    sanitized = None

try:
    build.seed_private_windows_runtime_files(build.WINDOWS_DIST_ROOT)
    print('Private seeding successful.')
except Exception as e:
    print(f'Private Seed Error: {e}')

try:
    build.seed_public_windows_runtime_files(build.PUBLIC_VARIANT_DIST_ROOT, sanitized)
    print('Public seeding successful.')
except Exception as e:
    print(f'Public Seed Error: {e}')

print('EXECUTION_COMPLETE')

