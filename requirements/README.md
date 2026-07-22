# Locked Python dependencies

`runtime.lock` contains the exact runtime dependency graph.

`ci.lock` contains the runtime graph plus test and wheel-build tooling.

Both lock files include SHA-256 hashes and are installed in CI with
`pip --require-hashes`.

Regenerate the locks from the repository root using Python 3.14:

```bash
lock_env=$(mktemp -d /tmp/5ibr-lock-env.XXXXXX)
python -m venv "$lock_env"
"$lock_env/bin/python" -m pip install "pip-tools==7.6.0"

(
  cd requirements
  "$lock_env/bin/pip-compile" \
    --generate-hashes \
    --resolver=backtracking \
    --output-file=runtime.lock \
    runtime.in

  "$lock_env/bin/pip-compile" \
    --generate-hashes \
    --resolver=backtracking \
    --allow-unsafe \
    --output-file=ci.lock \
    ci.in
)
```

Review every dependency and hash change before committing regenerated locks.
