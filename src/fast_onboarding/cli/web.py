"""CLI for serving the Fast Onboarding Web UI."""

from __future__ import annotations

import argparse

from fast_onboarding.web.server import WebAppConfig, normalize_base_path, run_server


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the Fast Onboarding Web UI.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind. Use 127.0.0.1 behind nginx.")
    parser.add_argument("--port", type=int, default=8787, help="Port to bind.")
    parser.add_argument("--base-path", default="", help="External URL prefix, e.g. /resume.")
    parser.add_argument("--output-dir", default="workspace/web-output", help="Directory for generated files.")
    parser.add_argument("--database", default="data/fast_onboarding.sqlite3", help="SQLite database path.")
    args = parser.parse_args()
    run_server(
        WebAppConfig(
            host=args.host,
            port=args.port,
            base_path=normalize_base_path(args.base_path),
            output_dir=args.output_dir,
            database_path=args.database,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
