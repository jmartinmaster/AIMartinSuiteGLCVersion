import sys

__module_name__ = "App Logging"
__version__ = "1.1.4"


def log_exception(context, exc):
    print(f"[{context}] {exc}", file=sys.stderr)