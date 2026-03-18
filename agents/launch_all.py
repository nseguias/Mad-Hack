"""
Launch all 9 provider agents + the consumer agent.
Usage: python3.11 launch_all.py
(reads ANTHROPIC_API_KEY from .env file)
"""

import subprocess
import sys
import signal
import os
from pathlib import Path
from config import SERVICES

processes = []

PYTHON = "/opt/homebrew/bin/python3.11"


def load_dotenv():
    """Load .env file into os.environ."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()


def cleanup(sig=None, frame=None):
    print("\n⏹  Shutting down all agents...")
    for p in processes:
        p.terminate()
    for p in processes:
        p.wait()
    print("Done.")
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def main():
    load_dotenv()

    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ No OPENAI_API_KEY found in .env or environment.")
        sys.exit(1)

    agents_dir = os.path.dirname(os.path.abspath(__file__))

    # Start all providers
    print("=== Starting 9 provider agents ===\n")
    for svc_id, svc in SERVICES.items():
        env = {**os.environ, "SERVICE_NAME": svc_id}
        p = subprocess.Popen(
            [PYTHON, os.path.join(agents_dir, "provider.py")],
            env=env,
            cwd=agents_dir,
        )
        processes.append(p)
        print(f"  ✓ {svc_id:20s} → http://localhost:{svc['port']}")

    # Start consumer
    print("\n=== Starting consumer agent ===\n")
    p = subprocess.Popen(
        [PYTHON, os.path.join(agents_dir, "consumer.py")],
        env=os.environ.copy(),
        cwd=agents_dir,
    )
    processes.append(p)
    print(f"  ✓ {'consumer':20s} → http://localhost:8001")

    print("\n=== All agents running ===")
    print("\nTest it:")
    print('  curl -X POST http://localhost:8001/chat \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"message": "Find museum tickets for 2 adults tomorrow"}\'')
    print("\nCtrl+C to stop all.\n")

    for p in processes:
        p.wait()


if __name__ == "__main__":
    main()
