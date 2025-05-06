#!/usr/bin/env python3
"""
This is a command-line tool to list all the tags in a Quiver file.

Usage:
    qvls.py <quiver_file>
"""

import click
from quiver_pdb import list_tags

@click.command()
@click.argument("quiver_file", type=click.Path(exists=True, dir_okay=False))
def main(quiver_file):
    """
    List all tags in the given Quiver file.
    """
    try:
        tags = list_tags(quiver_file)
        for tag in tags:
            click.echo(tag)
    except Exception as e:
        click.echo(f"Error listing tags: {e}", err=True)
        raise click.Abort()

if __name__ == "__main__":
    main()