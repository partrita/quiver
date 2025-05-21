#!/usr/bin/env python3
"""
Rename the tags in a Quiver file using new tags from stdin or command-line arguments.
The Quiver file is modified in-place.

Usage examples:
    qvrename.py my.qv new_tag1 new_tag2 ...
    echo -e "new_tag1\\nnew_tag2" | qvrename.py my.qv
"""

import sys
import os
import stat
import click
from quiver_pdb import rs_rename_tags


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

    # Filter out empty entries
    tags = [tag.strip() for tag in tag_buffers if tag.strip()]

    try:
        temp_file_path = rs_rename_tags(quiver_file, tags)
        if temp_file_path:
            # Atomically replace the original file with the temporary file
            # os.replace is generally atomic, especially if src and dst are on the same filesystem.
            os.replace(temp_file_path, quiver_file)
            click.secho(f"✅ Successfully renamed tags in {quiver_file}", fg="green")
        else:
            # This case should ideally not be reached if rs_rename_tags errors out
            # or returns a valid path. But as a fallback.
            click.secho("Rename operation did not return a new file path.", fg="yellow", err=True)
            sys.exit(1)
            
    except Exception as e:
        # If rs_rename_tags raises an exception, it will be caught here.
        # This includes PyIOError, PyValueError from Rust.
        # Also includes potential errors from os.replace if the temp_file_path was returned
        # but replacement failed (e.g. permission issues, different filesystems for temp_file_path).
        # The temp file created by Rust's NamedTempFile will be automatically cleaned up
        # when `temp_file_path` (if it's a `tempfile.TempPath`) goes out of scope or on error,
        # unless it was persisted and its path returned as a simple String.
        # Given rs_rename_tags returns Result<String>, the temp file is persisted until os.replace.
        # If os.replace fails, we should try to clean up the temp file.
        click.secho(f"Error renaming tags: {e}", fg="red", err=True)
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                click.secho(f"Cleaned up temporary file: {temp_file_path}", fg="yellow", err=True)
            except OSError as rm_e:
                click.secho(f"Error cleaning up temporary file {temp_file_path}: {rm_e}", fg="red", err=True)
        sys.exit(1)


if __name__ == "__main__":
    rename_tags()
