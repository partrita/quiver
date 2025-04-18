#!/usr/bin/env python3
"""
This is a command-line tool to extract all PDB files from a Quiver file.

Usage:
    qvextract.py <quiver_file>
"""

import os
import click
from quiver import Quiver


@click.command()
@click.argument("quiver_file", type=click.Path(exists=True, dir_okay=False))
def extract_pdbs(quiver_file):
    """
    Extract all PDB files from a Quiver file.
    """
    qv = Quiver(quiver_file, "r")

    for tag in qv.get_tags():
        outfn = f"{tag}.pdb"

        if os.path.exists(outfn):
            click.echo(f"⚠️  File {outfn} already exists, skipping")
            continue

        lines = qv.get_pdblines(tag)
        with open(outfn, "w") as f:
            f.writelines(lines)

        click.echo(f"✅ Extracted {outfn}")

    click.secho(
        f"\n🎉 Successfully extracted {qv.size()} PDB files from {quiver_file}",
        fg="green",
    )


if __name__ == "__main__":
    extract_pdbs()
