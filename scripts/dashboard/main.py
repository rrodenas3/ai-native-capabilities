"""Entry point for the local ai-native-capabilities dashboard (FastAPI + uvicorn)."""

from __future__ import annotations

import argparse
import time
import webbrowser


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="Run the local ai-native-capabilities dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="Open the dashboard in your browser")
    parser.add_argument("--quiet", action="store_true", help="Suppress HTTP request logs")
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}"
    print(f"Local dashboard running at {url}")
    print(f"API docs at {url}/docs")

    if args.open:
        time.sleep(0.5)
        webbrowser.open(url)

    uvicorn.run(
        "scripts.dashboard.app:app",
        host=args.host,
        port=args.port,
        log_level="error" if args.quiet else "info",
    )


if __name__ == "__main__":
    main()
