#!/usr/bin/env python3
"""
Slice a specific set of tags from a Quiver file into another Quiver file.

Usage:
    qvslice.py big.qv tag1 tag2 ... > sliced.qv
    echo "tag1 tag2" | qvslice.py big.qv > sliced.qv
"""

import sys
import click
from quiver_pdb import rs_qvslice


@click.command()
@click.argument("quiver_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("tags", nargs=-1)
def qvslice(quiver_file, tags):
    """
    Extract selected TAGS from QUIVER_FILE and output to stdout.
    If no TAGS are provided as arguments, they are read from stdin.
    """
    tag_list = list(tags)

    # ✅ Read tags from stdin if no arguments are provided
    if not tag_list and not sys.stdin.isatty():
        stdin_data = sys.stdin.read()
        tag_list.extend(stdin_data.strip().split())

    # ✅ Clean and validate tag list
    tag_list = [tag.strip() for tag in tag_list if tag.strip()]
    if not tag_list:
        click.secho(
            "❌ No tags provided. Provide tags as arguments or via stdin.",
            fg="red",
            err=True,
        )
        sys.exit(1)

    try:
        result = rs_qvslice(quiver_file, tag_list)
        # Print warnings to stderr
        for line in result.splitlines():
            if line.startswith("⚠️"):
                click.secho(line, fg="yellow", err=True)
            else:
                print(line)
    except Exception as e:
        click.secho(f"Error slicing Quiver file: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    qvslice()
