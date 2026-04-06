"""Deploy commands — push and status."""

import json
import subprocess
import sys
import urllib.request
import urllib.error


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300, **kwargs)


def deploy_status(output_json: bool = False) -> None:
    result = {}

    # Railway status
    try:
        out = _run(["railway", "status", "--json"])
        if out.returncode == 0:
            result["railway"] = json.loads(out.stdout) if out.stdout.strip() else {"status": "ok"}
        else:
            result["railway"] = {"error": out.stderr.strip() or "not linked"}
    except FileNotFoundError:
        result["railway"] = {"error": "railway CLI not installed"}
    except Exception as e:
        result["railway"] = {"error": str(e)}

    # Wrangler status
    try:
        out = _run(["wrangler", "deployments", "list", "--json"])
        if out.returncode == 0 and out.stdout.strip():
            result["wrangler"] = json.loads(out.stdout)
        else:
            result["wrangler"] = {"error": out.stderr.strip() or "no deployments"}
    except FileNotFoundError:
        result["wrangler"] = {"error": "wrangler CLI not installed"}
    except Exception as e:
        result["wrangler"] = {"error": str(e)}

    if output_json:
        print(json.dumps(result, indent=2))
        return

    print("\nDeploy Status\n")
    for service, info in result.items():
        if "error" in info:
            print(f"  {service}: {info['error']}")
        else:
            print(f"  {service}: ok")
    print()


def deploy_push(output_json: bool = False) -> None:
    results = {}

    # Railway deploy
    print("Deploying backend (Railway)...")
    try:
        out = _run(["railway", "up", "--detach"])
        if out.returncode == 0:
            results["railway"] = {"status": "deployed", "output": out.stdout.strip()}
            print(f"  Railway: deployed")
        else:
            results["railway"] = {"status": "failed", "error": out.stderr.strip()}
            print(f"  Railway: FAILED — {out.stderr.strip()}", file=sys.stderr)
    except FileNotFoundError:
        results["railway"] = {"status": "failed", "error": "railway CLI not installed"}
        print("  Railway: not installed", file=sys.stderr)

    # Wrangler deploy
    print("Deploying frontend (Wrangler)...")
    try:
        out = _run(["wrangler", "deploy"])
        if out.returncode == 0:
            results["wrangler"] = {"status": "deployed", "output": out.stdout.strip()}
            print(f"  Wrangler: deployed")
        else:
            results["wrangler"] = {"status": "failed", "error": out.stderr.strip()}
            print(f"  Wrangler: FAILED — {out.stderr.strip()}", file=sys.stderr)
    except FileNotFoundError:
        results["wrangler"] = {"status": "failed", "error": "wrangler CLI not installed"}
        print("  Wrangler: not installed", file=sys.stderr)

    if output_json:
        print(json.dumps(results, indent=2))

    # Check if either failed
    if any(r.get("status") == "failed" for r in results.values()):
        sys.exit(1)

    print("\nDeploy complete.")
