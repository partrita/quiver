#!/usr/bin/env python3
"""
This is a command-line tool to extract specific PDB files from a Quiver file.

Usage:
    qvextractspecific.py [OPTIONS] <quiver_file> [tag1 tag2 ...]
    cat tags.txt | qvextractspecific.py [OPTIONS] <quiver_file>
"""

import os
import sys
import stat
import click
from quiver import Quiver


@click.command()
@click.argument("quiver_file", type=click.Path(exists=True, dir_okay=False))
@click.argument("tags", nargs=-1)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, writable=True),
    default=".",
    help="Directory to save extracted PDB files",
)
def extract_selected_pdbs(quiver_file, tags, output_dir):
    """
    Extract specific PDB files from a Quiver file.

    Tags can be passed as command-line arguments or via stdin (piped).
    """
    tag_buffers = list(tags)

    # Check if input is being piped via stdin
    if not sys.stdin.isatty() and stat.S_ISFIFO(os.fstat(0).st_mode):
        stdin_tags = [line.strip() for line in sys.stdin.readlines()]
        for line in stdin_tags:
            tag_buffers.extend(line.split())

    # Clean and deduplicate tags
    unique_tags = sorted(set(filter(None, tag_buffers)))

    if not unique_tags:
        click.secho("❗ No tags provided.", fg="red")
        sys.exit(1)

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    qv = Quiver(quiver_file, "r")
    extracted_count = 0

    for tag in unique_tags:
        outfn = os.path.join(output_dir, f"{tag}.pdb")

        if os.path.exists(outfn):
            click.echo(f"⚠️  File {outfn} already exists, skipping")
            continue

        try:
            lines = qv.get_pdblines(tag)
        except KeyError:
            click.secho(
                f"❌ Could not find tag {tag} in Quiver file, skipping", fg="yellow"
            )
            continue

        with open(outfn, "w") as f:
            f.writelines(lines)

        click.echo(f"✅ Extracted {outfn}")
        extracted_count += 1

    click.secho(
        f"\n🎉 Successfully extracted {extracted_count} PDB file(s) from {quiver_file} to {output_dir}",
        fg="green",
    )


if __name__ == "__main__":
    extract_selected_pdbs()
