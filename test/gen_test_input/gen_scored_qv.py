#!/usr/bin/env python3

"""
Take 10 pdbs from the ../input_for_tests dir then assign them random scores and stash this in a Quiver file.
This scores quiver file will be used in testing later.

"""

import sys

sys.path.append("../../")
from quiver import Quiver
import os
import glob
import random

# Make a quiver file
qv = Quiver("test.qv", "w")

for i in range(10):
    # Get a random pdb from the input_for_tests dir
    pdbs = glob.glob("../input_for_tests/*.pdb")
    pdb = pdbs[i]
    # Get the pdb name
    pdb_name = os.path.basename(pdb)

    pdblines = open(pdb, "r").readlines()

    # Remove the .pdb extension
    tag = pdb_name[:-4]

    # Make up some random scores

    ddg = random.randint(-100, 100)
    charge = random.randint(-100, 100)
    cool = random.randint(-100, 100)
    scoreX = random.randint(-100, 100)

    score_str = f"ddg={ddg}|charge={charge}|cool={cool}|scoreX={scoreX}"

    # Add the pdb to the quiver file
    qv.add_pdb(pdblines, tag, score_str)
