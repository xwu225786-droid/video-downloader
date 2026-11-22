#!/usr/bin/env python3
"""Keep the existing double-click entries aligned with the selected runtime."""
import json
import subprocess
import sys

import docker_app

state = {}
if docker_app.REGISTRY.is_file():
    state = json.loads(docker_app.REGISTRY.read_text())
action = sys.argv[1]
if state.get("mode") == "docker":
    result = subprocess.run([str(docker_app.PYTHON), str(docker_app.ROOT/"scripts/docker_app.py"), action])
else:
    result = subprocess.run([str(docker_app.PYTHON), "-m", "voxpull.cli", action], env=docker_app.native_env())
raise SystemExit(result.returncode)
