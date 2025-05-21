#!/usr/bin/env python3
"""
This is a command-line tool to extract specific PDB files from a Quiver file
using the Rust-based `quiver_pdb` module for faster execution.

Usage:
    qvextractspecific.py [OPTIONS] <quiver_file> [tag1 tag2 ...]
    cat tags.txt | qvextractspecific.py [OPTIONS] <quiver_file>
"""

import os
import sys
import stat
import click
from quiver_pdb import rs_extract_selected_pdbs


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
    This version utilizes a Rust-based function for faster processing.
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

    # Call the Rust-based function
    try:
        result = rs_extract_selected_pdbs(quiver_file, unique_tags, output_dir)
        
        # Process results
        for file_path in result.extracted_files:
            click.secho(f"✅ Extracted {file_path}", fg="green")
        
        for tag_name in result.missing_tags:
            click.secho(f"⚠️  Could not find tag '{tag_name}' in Quiver file, skipping.", fg="yellow")

        # Provide a summary
        summary_message = f"\n🎉 Successfully extracted {len(result.extracted_files)} PDB file(s) to '{output_dir}'."
        if result.missing_tags:
            summary_message += f" {len(result.missing_tags)} tag(s) not found."
        
        click.secho(summary_message, fg="blue" if not result.missing_tags else "yellow")

        # Check if any files were skipped due to already existing (if this info is added to result)
        # For now, the Rust function extract_pdb_for_tag returns Ok(None) for skipped files,
        # and rs_extract_selected_pdbs does not explicitly list them in the PyResult.
        # If it did, we could print them here. e.g. result.skipped_files
        # Example:
        # if hasattr(result, 'skipped_files') and result.skipped_files:
        #     click.secho("\nℹ️ Skipped files (already existed):", fg="cyan")
        #     for file_info in result.skipped_files:
        #         click.secho(f"  - {file_info}", fg="cyan")

    except Exception as e:
        click.secho(f"❌ Error during extraction: {e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    extract_selected_pdbs()
