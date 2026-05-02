import subprocess
import os
import shlex

shell_cmd = "echo hello world"
workspace = os.getcwd()
docker_cmd = f'docker run --rm -v "{workspace}:/workspace" -w /workspace python:3.11-slim bash -c {shlex.quote(shell_cmd)}'
print(docker_cmd)
result = subprocess.run(docker_cmd, shell=True, text=True, capture_output=True)
print("OUT:", result.stdout)
print("ERR:", result.stderr)
print("CODE:", result.returncode)
