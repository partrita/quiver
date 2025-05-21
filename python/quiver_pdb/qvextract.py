#!/usr/bin/env python3
"""
This is a command-line tool to extract all PDB files from a Quiver file.

Usage:
    qvextract.py <quiver_file>
"""

import click
from quiver_pdb import rs_extract_pdbs


@click.command()
@click.argument("quiver_file", type=click.Path(exists=True, dir_okay=False))
def extract_pdbs(quiver_file):
    """
    Extract all PDB files from a Quiver file.
    Each PDB structure is saved as a separate .pdb file named after its tag.
    Files that already exist will be skipped.
    """
    try:
        extracted_files = rs_extract_pdbs(quiver_file)
        if not extracted_files:
            click.secho("ℹ️ No PDB files were extracted. This might be because all target PDB files already exist or the Quiver file is empty/contains no PDB data.", fg="yellow")
        else:
            for file_path in extracted_files:
                click.secho(f"✅ Extracted {file_path}", fg="green")
            click.secho(f"\n🎉 Successfully extracted {len(extracted_files)} PDB file(s).", fg="blue")
    except Exception as e:
        click.secho(f"❌ Error during extraction: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    extract_pdbs()
