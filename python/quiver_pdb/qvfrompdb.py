#!/usr/bin/env python3
"""
This tool combines multiple PDB files into a Quiver-compatible stream.

Usage:
    qvfrompdbs.py <pdb1> <pdb2> ... <pdbN> > output.qv
"""

import sys
import click
from quiver_pdb import rs_qvfrompdbs


@click.command()
@click.argument("pdb_files", nargs=-1, required=True)
def qvfrompdbs(pdb_files):
    """
    Converts one or more PDB files into a Quiver-formatted stream.
    Output is printed to stdout.
    """
    if not pdb_files:
        click.secho("No PDB files provided.", fg="red", err=True)
        # Show help and exit, as pdb_files is a required argument.
        # Depending on click's behavior with `required=True`, this might be redundant,
        # but it's a good explicit check.
        ctx = click.get_current_context()
        click.echo(ctx.get_help(), err=True)
        ctx.exit(1)
        return

    try:
        # rs_qvfrompdbs expects a List[str] and returns a String.
        quiver_data = rs_qvfrompdbs(list(pdb_files))
        click.echo(quiver_data, nl=False) # nl=False because Rust output likely includes final newline
    except Exception as e:
        click.secho(f"❌ Error converting PDBs to Quiver format: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    qvfrompdbs()
