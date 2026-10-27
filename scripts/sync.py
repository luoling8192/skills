#!/usr/bin/env python3
"""Copy the skills listed in sources.json from their source repositories.

    python3 scripts/sync.py          # overwrite skills/<dest> with upstream
    python3 scripts/sync.py --check  # exit 1 if any synced skill differs from upstream

Each dest directory is replaced wholesale, so edits made here are lost on the
next sync. Change the source repository instead.
"""
import filecmp
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Repository files that describe the source repo, not the skill.
SKIP = {".git", ".github", ".gitignore", "README.md", "README.zh-CN.md"}


def clone(repo, workdir):
    target = os.path.join(workdir, repo.replace("/", "__"))
    if not os.path.isdir(target):
        subprocess.run(
            ["git", "clone", "--quiet", "--depth", "1", f"https://github.com/{repo}.git", target],
            check=True,
        )
    return target


def stage(source, upstream_root, staging):
    src = os.path.normpath(os.path.join(upstream_root, source["path"]))
    if not os.path.isfile(os.path.join(src, "SKILL.md")):
        sys.exit(f"{source['repo']}:{source['path']} has no SKILL.md")
    shutil.copytree(src, staging, ignore=lambda _dir, names: [n for n in names if n in SKIP])
    license_path = os.path.join(staging, "LICENSE")
    if not os.path.exists(license_path) and os.path.exists(os.path.join(upstream_root, "LICENSE")):
        shutil.copy2(os.path.join(upstream_root, "LICENSE"), license_path)


def same_tree(a, b):
    if not os.path.isdir(a) or not os.path.isdir(b):
        return False
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.funny_files:
        return False
    _, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
    if mismatch or errors:
        return False
    return all(same_tree(os.path.join(a, d), os.path.join(b, d)) for d in cmp.common_dirs)


def main():
    check = "--check" in sys.argv[1:]
    with open(os.path.join(ROOT, "sources.json")) as handle:
        sources = json.load(handle)

    dests = [s["dest"] for s in sources]
    if len(dests) != len(set(dests)):
        sys.exit("sources.json: duplicate dest")

    stale = []
    with tempfile.TemporaryDirectory() as workdir:
        for source in sources:
            upstream_root = clone(source["repo"], workdir)
            staging = os.path.join(workdir, "staged", source["dest"])
            stage(source, upstream_root, staging)
            dest = os.path.join(ROOT, source["dest"])
            if same_tree(staging, dest):
                continue
            stale.append(source["dest"])
            if not check:
                shutil.rmtree(dest, ignore_errors=True)
                shutil.copytree(staging, dest)

    if stale:
        print(("out of date: " if check else "updated: ") + ", ".join(stale))
    if check and stale:
        sys.exit(1)


if __name__ == "__main__":
    main()
