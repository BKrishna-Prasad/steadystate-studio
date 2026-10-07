"""Replay a saved synthetic file; pass additional CLI options after its path."""

import sys

from neurovision.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["replay", *sys.argv[1:]]))
