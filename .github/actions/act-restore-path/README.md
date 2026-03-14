# act-restore-path

Workaround for a [nektos/act](https://github.com/nektos/act) bug where `::add-path::` directives cause `node` to drop out of PATH for subsequent steps.

## Problem

When running workflows locally via `act`, JavaScript-based actions that emit `::add-path::` directives (e.g. `astral-sh/setup-uv@v4`, `aws-actions/setup-sam@v2`) cause `act` to rebuild PATH for subsequent `docker exec` calls. Instead of **prepending** the new entries to the existing container PATH (as GitHub Actions does), `act` appears to **replace** PATH with only the new entries. This drops the original container PATH, including `/opt/acttoolcache/node/.../bin` where the Node.js binary lives in `catthehacker/ubuntu:act-*` images.

The next Node-based action then fails with:

```
OCI runtime exec failed: exec failed: unable to start container process: exec: "node": executable file not found in $PATH
```

## Which steps trigger the issue

Any action that calls `core.addPath()` (or writes to `$GITHUB_PATH`) can trigger this. Common examples:

- `astral-sh/setup-uv` – adds uv and `~/.local/bin`
- `aws-actions/setup-sam` – adds SAM CLI paths
- Other setup actions that modify PATH

## How this workaround fixes it

This composite action, when `env.ACT` is set (i.e. running under `act`), globs for `/opt/acttoolcache/node/*/x64/bin` and appends any directory containing an executable `node` to `$GITHUB_PATH`. That causes `act` to prepend the node directory to PATH for the next step, restoring `node` visibility for subsequent Node-based actions.

The action is a no-op on real GitHub runners because of the `if: ${{ env.ACT }}` guard.

## Usage

Call this action after each step that modifies PATH when running under `act`:

```yaml
- name: Set up uv
  uses: astral-sh/setup-uv@v4
  with:
    python-version: '3.13'

- name: Restore PATH (act workaround)
  uses: ./.github/actions/act-restore-path

- name: Install SAM CLI
  uses: aws-actions/setup-sam@v2
  # ...
```

## References

- [nektos/act#973](https://github.com/nektos/act/issues/973) – exec: "node": executable file not found in $PATH
- [nektos/act#2637](https://github.com/nektos/act/issues/2637) – Paths to binaries put in GITHUB_PATH are not correctly set
