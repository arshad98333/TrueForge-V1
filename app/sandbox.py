"""Build a command for TrueForge's sandbox; never execute generated code on this host."""

import ast
import base64
import hashlib
from pathlib import Path

from domain.charge_rules import VERSION, canonical, digest, validate_evidence

from .store import PolicyError

RUNNER = """import json
from charge_rules import reconstruct
result = reconstruct(evidence)
print(json.dumps(result, sort_keys=True))
"""


def validate_runner(source):
    if not isinstance(source, str) or len(source) > 4096:
        raise PolicyError("Runner exceeds its supported size")
    try:
        valid = ast.dump(ast.parse(source)) == ast.dump(ast.parse(RUNNER))
    except (SyntaxError, ValueError) as exc:
        raise PolicyError("Runner is not valid Python") from exc
    if not valid:
        raise PolicyError(
            "Runner may only import the library, reconstruct evidence, and print JSON"
        )


def execution_spec(bundle, runner_source):
    validate_evidence(bundle)
    validate_runner(runner_source)
    library = (Path(__file__).resolve().parents[1] / "domain" / "charge_rules.py").read_text()
    library_hash = hashlib.sha256(library.encode()).hexdigest()
    # Serialize and base64 encode sources/data; never interpolate ticket text into the shell.
    bootstrap = f"""import contextlib, io, json, os, resource, signal, sys, types
os.environ.clear()
resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
resource.setrlimit(resource.RLIMIT_AS, (268435456, 268435456))
signal.alarm(20)
library = types.ModuleType('charge_rules')
exec({library!r}, library.__dict__)
sys.modules['charge_rules'] = library
evidence = json.loads({canonical(bundle)!r})
capture = io.StringIO()
with contextlib.redirect_stdout(capture):
    exec({runner_source!r}, {{'evidence': evidence}})
output = capture.getvalue()
if len(output.encode()) > 65536:
    raise ValueError('Output limit exceeded')
sys.stdout.write(output)
"""
    encoded = base64.b64encode(bootstrap.encode()).decode()
    command = (
        "env -i PATH=/usr/local/bin:/usr/bin:/bin timeout 20s python3 -I -S -c "
        f"'import base64;exec(base64.b64decode(\"{encoded}\"))'"
    )
    return {
        "command": command,
        "runner_source": runner_source,
        "library_hash": library_hash,
        "library_version": VERSION,
        "evidence_hash": digest(bundle),
    }
