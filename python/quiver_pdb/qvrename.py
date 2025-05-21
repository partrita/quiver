#!/usr/bin/env python3
"""
Rename the tags in a Quiver file using new tags from stdin or command-line arguments.

Usage examples:
    qvrename.py my.qv tag1_new tag2_new ... > renamed.qv
"""

import sys
import os
import stat
import click
from quiver_pdb import rs_rename_tags


@click.command()
@click.argument("quiver_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("new_tags", nargs=-1)
def rename_tags(quiver_file, new_tags):
    """
    Rename tags in a Quiver file. New tags are read from arguments or stdin.
    """
    tag_buffers = list(new_tags)

    # Read from stdin if piped
    if not sys.stdin.isatty() and stat.S_ISFIFO(os.fstat(0).st_mode):
        stdin_lines = sys.stdin.read().splitlines()
        for line in stdin_lines:
            tag_buffers.extend(line.strip().split())

    # Filter out empty entries
    tags = [tag.strip() for tag in tag_buffers if tag.strip()]

    try:
        rs_rename_tags(quiver_file, tags)
    except Exception as e:
        click.secho(f"Error renaming tags: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    rename_tags()
