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
        # rs_qvslice now returns a single string which includes data and any warnings.
        # Warnings are already formatted with "⚠️" by the Rust function.
        # The Python script just needs to print the output.
        output_str = rs_qvslice(quiver_file, tag_list)
        if output_str: # Check if the string is not empty
            # Print the entire string. If it contains newlines, click.echo handles it.
            # If specific lines (like warnings) need to go to stderr, that logic
            # would need to be more complex here, or the Rust API would need to
            # return structured data (e.g., a dict with 'data' and 'warnings' keys).
            # Given the current Rust API returns a single string with embedded warnings,
            # we print it all to stdout. The user can redirect stderr if they only want data.
            click.echo(output_str)
        else:
            # This case might occur if Rust returns an empty string on success
            # (e.g. slice of no tags resulted in no data and no warnings).
            click.secho("ℹ️  The slice operation resulted in empty output.", fg="yellow")

    except Exception as e:
        click.secho(f"❌ Error slicing Quiver file: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    qvslice()
