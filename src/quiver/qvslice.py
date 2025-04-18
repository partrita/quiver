#!/usr/bin/env python3
"""
Slice a specific set of tags from a Quiver file into another Quiver file.

Usage:
    qvslice.py big.qv tag1 tag2 ... > sliced.qv
    echo "tag1 tag2" | qvslice.py big.qv > sliced.qv
"""

import sys
import click
from quiver import Quiver


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

    qv = Quiver(quiver_file, "r")
    qv_lines, found_tags = qv.get_struct_list(tag_list)

    # Warn about missing tags
    missing_tags = [tag for tag in tag_list if tag not in found_tags]
    for tag in missing_tags:
        click.secho(f"⚠️  Tag not found in Quiver file: {tag}", fg="yellow", err=True)

    # Output sliced content
    click.echo(qv_lines, nl=False)


if __name__ == "__main__":
    qvslice()
