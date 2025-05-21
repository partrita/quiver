#!/usr/bin/env python3
"""
This is a command-line tool to list all the tags in a Quiver file.

Usage:
    qvls.py <quiver_file>
"""

import click
from quiver_pdb import rs_list_tags


@click.command()
@click.argument("quiver_file", type=click.Path(exists=True, dir_okay=False))
def list_tags(quiver_file):
    """
    List all tags in the given Quiver file.
    """
    try:
        tags = rs_list_tags(quiver_file)
        if not tags:
            click.secho(f"ℹ️ No tags found in {quiver_file}.", fg="yellow")
        else:
            for tag in tags:
                click.echo(tag)
    except Exception as e:
        click.secho(f"❌ Error listing tags: {e}", fg="red", err=True)
        sys.exit(1) # Use sys.exit(1) for errors


if __name__ == "__main__":
    list_tags()
