#!/usr/bin/env python3
"""
One-time script: fetch MATLAB function documentation from GitHub and embed it
as a 'help_text' field in each node JSON definition.

Usage:
    python scripts/populate_help_text.py
"""

import json
import os
import re
import urllib.request
import glob


def github_blob_to_raw(url: str) -> str:
    """Convert a GitHub blob URL to a raw.githubusercontent.com URL."""
    # https://github.com/sccn/eeglab/blob/master/functions/popfunc/pop_epoch.m
    # -> https://raw.githubusercontent.com/sccn/eeglab/master/functions/popfunc/pop_epoch.m
    return url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")


def fetch_matlab_help(raw_url: str) -> str:
    """Fetch a .m file and extract the leading % comment block (help text)."""
    try:
        req = urllib.request.Request(raw_url, headers={"User-Agent": "EEGLAB-DAG"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ⚠ Fetch failed: {e}")
        return ""

    lines = content.splitlines()
    help_lines = []
    started = False

    for line in lines:
        stripped = line.strip()

        # Skip empty lines before the first comment
        if not started:
            if stripped.startswith("%"):
                started = True
            else:
                continue

        if not stripped.startswith("%"):
            break  # End of comment block

        # Stop at copyright / license boilerplate
        text = stripped.lstrip("% ").lower()
        if text.startswith("copyright") or text.startswith("this program is free"):
            break

        # Strip leading '% ' and keep the rest
        comment = line.lstrip()
        if comment.startswith("% "):
            comment = comment[2:]
        elif comment == "%":
            comment = ""
        elif comment.startswith("%"):
            comment = comment[1:]

        help_lines.append(comment)

    # Trim trailing blank lines
    while help_lines and not help_lines[-1].strip():
        help_lines.pop()

    return "\n".join(help_lines)


def main():
    nodes_dir = os.path.join(os.path.dirname(__file__), "..", "library", "nodes")
    nodes_dir = os.path.abspath(nodes_dir)

    json_files = sorted(glob.glob(os.path.join(nodes_dir, "*.json")))

    for path in json_files:
        basename = os.path.basename(path)
        with open(path, "r") as f:
            data = json.load(f)

        github_url = data.get("github_url", "")
        if not github_url:
            print(f"⏭ {basename}: no github_url, skipping")
            continue

        raw_url = github_blob_to_raw(github_url)
        print(f"⬇ {basename}: fetching from {raw_url}")

        help_text = fetch_matlab_help(raw_url)
        if help_text:
            data["help_text"] = help_text
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
                f.write("\n")
            print(f"  ✓ Embedded {len(help_text)} chars of help text")
        else:
            print(f"  ⚠ No help text extracted")


if __name__ == "__main__":
    main()
