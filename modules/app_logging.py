import sys


def log_exception(context, exc):
    print(f"[{context}] {exc}", file=sys.stderr)
