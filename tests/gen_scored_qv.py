#!/usr/bin/env python3
"""
Take 10 pdbs from the ./input_for_tests dir then assign them random scores and stash this in a Quiver file
by concatenating text, without using the Quiver class.  Writes in QV_TAG/QV_SCORE format.
This scored quiver file will be used in testing later.
"""

import sys
from pathlib import Path
from typing import List
import random

# Define the input directory.  Now relative to the script's parent.
input_dir: Path = Path(Path(__file__).parent / "input_for_tests")
# Define the output quiver file path inside the tests directory
output_qv_path: Path = Path(Path(__file__).parent / "test.qv")

# Initialize an empty string to store the Quiver file content
quiver_content = ""

# Get a list of pdb files from the input directory
pdbs: List[Path] = list(input_dir.glob("*.pdb"))
num_pdbs = len(pdbs)  # Get the number of PDB files

if not pdbs:
    print(f"Error: No PDB files found in {input_dir}")
    sys.exit(1)  # Exit if no pdb files are found

for i in range(min(10, num_pdbs)):  # Iterate up to 10, or the number of files, whichever is smaller.
    # Select the i-th pdb file
    pdb_path: Path = pdbs[i]
    # Get the pdb name
    pdb_name: str = pdb_path.name

    try:
        with open(pdb_path, "r") as f:
            pdblines: List[str] = f.readlines()
    except Exception as e:
        print(f"Error reading file {pdb_path}: {e}")
        continue  # Skip to the next file if there's an error reading this one.

    # Remove the .pdb extension to create the tag
    tag: str = pdb_name[:-4]

    # Make up some random scores
    ddg: int = random.randint(-100, 100)
    charge: int = random.randint(-100, 100)
    cool: int = random.randint(-100, 100)
    scoreX: int = random.randint(-100, 100)
    score_str: str = f"ddg={ddg}|charge={charge}|cool={cool}|scoreX={scoreX}"

    # Construct the PDB block as a string
    pdb_block = "".join(pdblines)

    # Append to the quiver content in the specified format, with QV_SCORE on the next line
    quiver_content += f"QV_TAG {tag}\nQV_SCORE {tag} {score_str}\n{pdb_block}"

# Write the complete Quiver file content to the output file. Added error handling.
if not quiver_content:
    print("Error: No data to write to Quiver file.")
    sys.exit(1)  # Exit if no data was generated.

try:
    with open(output_qv_path, "w") as qv_file:
        qv_file.write(quiver_content)
    print(f"Quiver file successfully written to {output_qv_path}")
except Exception as e:
    print(f"Error writing to Quiver file: {e}")
    sys.exit(1)  # Exit on error
