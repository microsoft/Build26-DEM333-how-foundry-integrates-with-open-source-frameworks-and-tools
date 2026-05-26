from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from dem333_common.responses_client import extract_output_text

AGENTS = [
    ("policy", ROOT / "agents" / "policy_agent" / "main.py", 8011, {}),
    ("itinerary", ROOT / "agents" / "itinerary_agent" / "main.py", 8012, {}),
    (
        "coordinator",
        ROOT / "agents" / "coordinator_agent" / "main.py",
        8010,
        {
            "POLICY_AGENT_RESPONSES_URL": "http://127.0.0.1:8011/responses",
            "ITINERARY_AGENT_RESPONSES_URL": "http://127.0.0.1:8012/responses",
            "DEM333_COORDINATOR_TRANSPORT": "responses",
        },
    ),
]


def agent_env(port: int, extra: dict[str, str]) -> dict[str, str]:
    env = os.environ.copy()
    python_path = str(SRC)
    if env.get("PYTHONPATH"):
        python_path = f"{python_path}{os.pathsep}{env['PYTHONPATH']}"
    env.update(
        {
            "PYTHONPATH": python_path,
            "PORT": str(port),
            "DEM333_CONSOLE_TRACES": "true",
            "DEM333_TRACE_CONTENT": "true",
        }
    )
    env.update(extra)
    return env


def start_agent(name: str, path: Path, port: int, extra: dict[str, str]) -> subprocess.Popen:
    print(f"Starting {name} on http://127.0.0.1:{port}/responses")
    return subprocess.Popen(
        [sys.executable, str(path)],
        cwd=ROOT,
        env=agent_env(port, extra),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )


def request_agent(port: int, prompt: str) -> str:
    response = httpx.post(
        f"http://127.0.0.1:{port}/responses",
        json={"model": "dem333-local", "input": prompt, "stream": False},
        timeout=180,
    )
    response.raise_for_status()
    return extract_output_text(response.json())


def wait_for_agent(name: str, port: int) -> None:
    deadline = time.monotonic() + 120
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            request_agent(port, f"health check for {name}")
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.75)
    raise RuntimeError(f"{name} did not become ready: {last_error}")


def stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)


def dump_output(name: str, process: subprocess.Popen) -> None:
    if not process.stdout:
        return
    output = process.stdout.read()
    if output.strip():
        print(f"\n--- {name} logs ---")
        print(output.strip())


def main() -> int:
    processes: list[tuple[str, subprocess.Popen]] = []
    try:
        for name, path, port, extra in AGENTS:
            process = start_agent(name, path, port, extra)
            processes.append((name, process))
            wait_for_agent(name, port)

        prompt = (
            "Plan a 2-day customer visit to Seattle for a healthcare customer. "
            "Make it executive-friendly, keep it compliant, and go ahead with "
            "the safe prep actions needed for the briefing."
        )
        print("\n--- Coordinator request ---")
        print(prompt)
        print("\n--- Coordinator response ---")
        print(request_agent(8010, prompt))
        return 0
    finally:
        for _, process in reversed(processes):
            stop_process(process)
        for name, process in processes:
            dump_output(name, process)


if __name__ == "__main__":
    raise SystemExit(main())
