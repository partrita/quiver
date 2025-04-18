#!/usr/bin/env python3
"""
Rename the tags in a Quiver file using new tags from stdin or command-line arguments.

Usage examples:
    qvls.py my.qv | sed 's/$/_new/' | qvrename.py my.qv > renamed.qv
    qvrename.py my.qv tag1_new tag2_new ... > renamed.qv
"""

import sys
import os
import stat
import click
from quiver import Quiver


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

    # Filter out empty entries and deduplicate if necessary
    tags = [tag for tag in tag_buffers if tag.strip()]

    qv = Quiver(quiver_file, "r")
    present_tags = qv.get_tags()

    if len(present_tags) != len(tags):
        click.secho(
            f"❌ Number of tags in file ({len(present_tags)}) does not match number of tags provided ({len(tags)})",
            fg="red",
        )
        sys.exit(1)

    tag_idx = 0
    with open(quiver_file, "r") as f:
        while True:
            line = f.readline()
            if not line:
                break

            if line.startswith("QV_TAG"):
                line = f"QV_TAG {tags[tag_idx]}\n"

                # Read next line (could be QV_SCORE or structure)
                next_line = f.readline()
                if next_line.startswith("QV_TAG"):
                    click.secho(
                        f"❌ Error: Found two QV_TAG lines in a row. This is not supported. Line: {next_line}",
                        fg="red",
                    )
                    sys.exit(1)

                if next_line.startswith("QV_SCORE"):
                    parts = next_line.split(" ")
                    parts[1] = tags[tag_idx]
                    next_line = " ".join(parts)

                line += next_line
                tag_idx += 1

            sys.stdout.write(line)


if __name__ == "__main__":
    rename_tags()
