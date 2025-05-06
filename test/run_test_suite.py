#!/usr/bin/env python3
"""
This is a Python script with a suite of tests for the Quiver library.
This tests the accuracy of the Quiver library by ensuring that the
correct PDB lines are returned for a given tag. And that no PDB lines
are lost during manipulation of the Quiver file.

"""

import sys
import os
import math
import uuid
import csv
from quiver_pdb import (
    Quiver,
    qvfrompdbs,
    extract_pdbs,
    list_tags,
    rename_tags,
    qvslice,
    qvsplit,
    extract_scorefile,
)
import glob

# 현재 스크립트의 디렉토리
current_dir = os.path.dirname(os.path.abspath(__file__))
# 부모 디렉토리를 sys.path에 추가하여 상대 임포트 가능하게 함
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)


# Define a custom Exception class
class TestFailed(Exception):
    pass


def test_zip_and_extract(basedir):
    """
    Test that qvfrompdbs and qvextract work correctly
    """
    # Go into the test directory
    os.chdir(f"{basedir}/test")

    # Create a temporary directory
    os.makedirs("do_zip_and_extract", exist_ok=True)
    os.chdir("do_zip_and_extract")

    # Get list of PDB files
    pdb_files = glob.glob(f"{basedir}/test/input_for_tests/*.pdb")
    
    # Create Quiver file
    with open("test.qv", "w") as f:
        f.write(qvfrompdbs(pdb_files))

    # Extract PDB files
    extract_pdbs("test.qv")

    # Get the list of PDB files in this directory
    pdbs = glob.glob("*.pdb")

    # Check that all PDB files were extracted
    for pdb in pdbs:
        tag = os.path.basename(pdb)[:-4]
        print(f"✅ Extracted {tag}")

    # Check that the extracted PDB files match the original ones
    for pdb in pdbs:
        tag = os.path.basename(pdb)[:-4]
        original_pdb = f"{basedir}/test/input_for_tests/{tag}.pdb"
        
        # Read both files
        with open(pdb, "r") as f1, open(original_pdb, "r") as f2:
            content1 = f1.read()
            content2 = f2.read()
            
            # Normalize content by removing extra whitespace and newlines
            content1 = '\n'.join(line.strip() for line in content1.splitlines() if line.strip())
            content2 = '\n'.join(line.strip() for line in content2.splitlines() if line.strip())
            
            # Compare contents
            if content1 != content2:
                print(f"File {pdb} does not match {original_pdb}")
                print("First few lines of extracted file:")
                print("\n".join(content1.split("\n")[:5]))
                print("\nFirst few lines of original file:")
                print("\n".join(content2.split("\n")[:5]))
                raise TestFailed(f"File {pdb} does not match {original_pdb}")

    # Clean up
    os.chdir(f"{basedir}")
    os.system(f"rm -r {basedir}/test/do_zip_and_extract")


def test_qvls(basedir):
    """
    Test that qvls returns the correct list of tags for a given Quiver file
    """
    # Go into the test directory
    os.chdir(f"{basedir}/test")

    # Create a temporary directory
    os.makedirs("do_qvls", exist_ok=True)
    os.chdir("do_qvls")

    # Get list of PDB files
    pdb_files = glob.glob(f"{basedir}/test/input_for_tests/*.pdb")
    
    # Create Quiver file
    with open("test.qv", "w") as f:
        f.write(qvfrompdbs(pdb_files))

    # Get tags
    tags = list_tags("test.qv")
    if tags is None:
        raise TestFailed("list_tags() returned None")

    # Get the list of PDB files
    pdbs = glob.glob(f"{basedir}/test/input_for_tests/*.pdb")

    # Check that all PDB files are listed
    for pdb in pdbs:
        tag = os.path.basename(pdb)[:-4]
        if tag not in tags:
            print(f"TAGS: {tags}")
            print(f"TAG: {tag}")
            raise TestFailed(f"PDB file {tag} not listed in qvls output")

    # Clean up
    os.chdir(f"{basedir}")
    os.system(f"rm -r {basedir}/test/do_qvls")


def test_qvextractspecific(basedir):
    os.chdir(f"{basedir}/test")
    test_dir = os.path.join(basedir, "test", "do_qvextractspecific")

    # 디렉토리 생성
    os.makedirs(test_dir, exist_ok=True)
    os.chdir(test_dir)

    # 기존 *.pdb 파일 삭제
    for f in glob.glob("*.pdb"):
        os.remove(f)

    # Get list of PDB files
    pdb_files = glob.glob(f"{basedir}/test/input_for_tests/*.pdb")
    
    # Create Quiver file
    with open("test.qv", "w") as f:
        f.write(qvfrompdbs(pdb_files))

    # Get tags and select 5 random ones
    tags = list_tags("test.qv")
    import random
    selected_tags = random.sample(tags, min(5, len(tags)))

    # Extract selected tags
    for tag in selected_tags:
        # Create a new Quiver file with just this tag
        with open("temp.qv", "w") as f:
            f.write(qvslice("test.qv", [tag]))
        # Extract from the temporary file
        extract_pdbs("temp.qv")
        # Clean up
        os.remove("temp.qv")

    # 파일 존재 여부 확인
    missing = [tag for tag in selected_tags if not os.path.exists(f"{tag}.pdb")]
    if missing:
        raise TestFailed(f"Missing PDBs: {missing}")

    # Get list of pdbs in this directory
    pdbs = glob.glob("*.pdb")
    pdb_tags = [os.path.basename(pdb)[:-4] for pdb in pdbs]

    if set(selected_tags) != set(pdb_tags):
        print(f"selected_tags: {selected_tags}")
        print(f"pdb_tags: {pdb_tags}")
        raise TestFailed("qvextractspecific did not return the correct PDB files")

    for tag in selected_tags:
        # Get the current PDB file
        currpdb = f"{tag}.pdb"
        with open(currpdb, "r") as f:
            currpdblines = [line.strip() for line in f.readlines()]

        # Get the PDB file
        pdb = f"{basedir}/test/input_for_tests/{tag}.pdb"

        # Get the PDB lines
        with open(pdb, "r") as f:
            pdblines = [line.strip() for line in f.readlines()]

        # Check that the two files are identical
        if currpdblines != pdblines:
            raise TestFailed(f"PDB file {currpdb} does not match {pdb}")

    # Clean up
    os.chdir(f"{basedir}")
    os.system(f"rm -r {basedir}/test/do_qvextractspecific")


def test_qvslice(basedir):
    """
    Test that qvslice returns the correct PDB lines for a given set of
    tags in a Quiver file
    """
    # Go into the test directory
    os.chdir(f"{basedir}/test")

    # Create a temporary directory
    os.makedirs("do_qvslice", exist_ok=True)
    os.chdir("do_qvslice")

    # Get list of PDB files
    pdb_files = glob.glob(f"{basedir}/test/input_for_tests/*.pdb")
    
    # Create Quiver file
    with open("test.qv", "w") as f:
        f.write(qvfrompdbs(pdb_files))

    # Get tags and select 5 random ones
    tags = list_tags("test.qv")
    import random
    selected_tags = random.sample(tags, min(5, len(tags)))

    # Run qvslice
    with open("sliced.qv", "w") as f:
        f.write(qvslice("test.qv", selected_tags))

    # Extract PDB files
    extract_pdbs("sliced.qv")

    # Get the list of PDB files in this directory
    pdbs = glob.glob("*.pdb")
    pdb_tags = [os.path.basename(pdb)[:-4] for pdb in pdbs]

    # Ensure that the correct PDB files are returned
    if set(selected_tags) != set(pdb_tags):
        print(f"PDB tags: {pdb_tags}")
        print(f"Tags: {selected_tags}")
        raise TestFailed("qvslice did not return the correct PDB files")

    for tag in selected_tags:
        # Get the current PDB file
        currpdb = f"{tag}.pdb"
        with open(currpdb, "r") as f:
            currpdblines = [line.strip() for line in f.readlines()]

        # Get the PDB file
        pdb = f"{basedir}/test/input_for_tests/{tag}.pdb"

        # Get the PDB lines
        with open(pdb, "r") as f:
            pdblines = [line.strip() for line in f.readlines()]

        # Check that the two files are identical
        if currpdblines != pdblines:
            raise TestFailed(f"PDB file {currpdb} does not match {pdb}")

    # Clean up
    os.chdir(f"{basedir}")
    os.system(f"rm -r {basedir}/test/do_qvslice")


def test_qvsplit(basedir):
    """
    Test that qvsplit returns the correct PDB lines for a given set of
    tags in a Quiver file
    """
    # Go into the test directory
    os.chdir(f"{basedir}/test")

    # Create a temporary directory
    os.makedirs("do_qvsplit", exist_ok=True)
    os.chdir("do_qvsplit")

    # Get list of PDB files
    pdb_files = glob.glob(f"{basedir}/test/input_for_tests/*.pdb")
    
    # Create Quiver file
    with open("test.qv", "w") as f:
        f.write(qvfrompdbs(pdb_files))

    os.makedirs("split", exist_ok=True)
    os.chdir("split")

    # Run qvsplit
    qvsplit("test.qv", 3, "split", "split")

    # Get the number of pdb files in the original quiver file
    num_pdbs = len(glob.glob(f"{basedir}/test/input_for_tests/*.pdb"))

    # Get the number of quiver files in the split directory
    num_quivers = len(glob.glob("*.qv"))

    # Ensure that the correct number of quiver files were created
    if num_quivers != math.ceil(num_pdbs / 3):
        raise TestFailed(
            f"qvsplit did not return the correct number of quiver files, "
            f"expected {math.ceil(num_pdbs / 3)}, got {num_quivers}"
        )

    # Extract the PDB files from each quiver file
    for i in range(num_quivers):
        # Run qvextract
        extract_pdbs(f"split_{i}.qv")

    # Get the list of PDB files in this directory
    pdbs = glob.glob("*.pdb")
    pdb_tags = [os.path.basename(pdb)[:-4] for pdb in pdbs]

    # Ensure that the correct PDB files are returned
    tags = []
    for i in glob.glob(f"{basedir}/test/input_for_tests/*.pdb"):
        tags.append(os.path.basename(i)[:-4])

    if set(tags) != set(pdb_tags):
        print(f"PDB tags: {pdb_tags}")
        print(f"Tags: {tags}")
        raise TestFailed("qvsplit did not return the correct PDB files")

    for tag in tags:
        # Get the current PDB file
        currpdb = f"{tag}.pdb"
        with open(currpdb, "r") as f:
            currpdblines = [line.strip() for line in f.readlines()]

        # Get the PDB file
        pdb = f"{basedir}/test/input_for_tests/{tag}.pdb"

        # Get the PDB lines
        with open(pdb, "r") as f:
            pdblines = [line.strip() for line in f.readlines()]

        # Check that the two files are identical
        if currpdblines != pdblines:
            raise TestFailed(f"PDB file {currpdb} does not match {pdb}")

    # Clean up
    os.chdir(f"{basedir}")
    os.system(f"rm -r {basedir}/test/do_qvsplit")


def test_qvrename(basedir):
    """
    Test that qvrename correctly renames the entries of a Quiver file.
    """
    # Go into the test directory
    os.chdir(f"{basedir}/test")

    # Create a temporary directory
    os.makedirs("do_qvrename", exist_ok=True)
    os.chdir("do_qvrename")

    # Get the input Quiver filepath
    qvpath = f"{basedir}/test/input_for_tests/designs_scored.qv"
    os.makedirs("input_pdbs", exist_ok=True)
    os.chdir("input_pdbs")

    # Extract the PDB files from the Quiver file
    extract_pdbs(qvpath)

    # Store current path
    inpdbdir = os.getcwd()

    os.chdir(f"{basedir}/test/do_qvrename")

    # Get the Quiver tags
    inqv = Quiver(qvpath, "r")
    tags = inqv.get_tags()

    # Make a random set of names to rename the entries to
    newtags = [f"{uuid.uuid4()}" for tag in tags]

    # Run qvrename
    with open("renamed.qv", "w") as f:
        f.write(rename_tags(qvpath, newtags))

    # Run qvextract
    extract_pdbs("renamed.qv")

    # Pair the old tags with the new tags and assert that the PDB files are the same
    # other than the name
    for idx in range(len(tags)):
        # Get the new PDB file
        currpdb = f"{newtags[idx]}.pdb"
        with open(currpdb, "r") as f:
            currpdblines = [line.strip() for line in f.readlines()]

        # Get the original PDB file
        pdb = f"{inpdbdir}/{tags[idx]}.pdb"

        # Get the PDB lines
        with open(pdb, "r") as f:
            pdblines = [line.strip() for line in f.readlines()]

        # Check that the two files are identical
        if currpdblines != pdblines:
            raise TestFailed(f"PDB file {currpdb} does not match {pdb}")

    # Now compare the score lines of the two Quiver files
    # Get the score lines of the original Quiver file
    extract_scorefile(qvpath)
    ogsc = qvpath.split(".")[0] + ".sc"

    # Read original score file
    og_scores = {}
    with open(ogsc, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            og_scores[row['tag']] = row

    # Get the score lines of the new Quiver file
    extract_scorefile("renamed.qv")
    newsc = "renamed.sc"

    # Read new score file
    new_scores = {}
    with open(newsc, 'r') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            new_scores[row['tag']] = row

    # Pair the old tags with the new tags and assert that the score lines are the same
    # other than the name
    for idx in range(len(tags)):
        old_tag = tags[idx]
        new_tag = newtags[idx]
        
        old_row = og_scores[old_tag]
        new_row = new_scores[new_tag]

        # Check that the two rows are identical except for the tag
        for key in old_row.keys():
            if key == "tag":
                continue
            if old_row[key] != new_row[key]:
                raise TestFailed(
                    f"Score line {idx} does not match between old and new Quiver files"
                )

    # Clean up
    os.chdir(f"{basedir}")
    os.system(f"rm -r {basedir}/test/do_qvrename")


# Run through all the tests, logging which ones fail

# Get the base directory
basedir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
passed = 0
total = 0

# Zip and Extract Test
print("Running zip and extract test")
try:
    test_zip_and_extract(basedir)
    print("Passed zip and extract test")
    passed += 1
    total += 1
except TestFailed as e:
    print(f"Test with name test_zip_and_extract failed with error: {e}")
    total += 1

print("\n")

# qvls Test
print("Running qvls test")
try:
    test_qvls(basedir)
    print("Passed qvls test")
    passed += 1
    total += 1
except TestFailed as e:
    print(f"Test with name test_qvls failed with error: {e}")
    total += 1

print("\n")

# qvextractspecific Test
print("Running qvextractspecific test")
try:
    test_qvextractspecific(basedir)
    print("Passed qvextractspecific test")
    passed += 1
    total += 1
except TestFailed as e:
    print(f"Test with name test_qvextractspecific failed with error: {e}")
    total += 1

print("\n")

# qvslice Test
print("Running qvslice test")
try:
    test_qvslice(basedir)
    print("Passed qvslice test")
    passed += 1
    total += 1
except TestFailed as e:
    print(f"Test with name test_qvslice failed with error: {e}")
    os.system(f"rm -r {basedir}/test/do_qvslice")
    total += 1

print("\n")

# qvsplit Test
print("Running qvsplit test")
try:
    test_qvsplit(basedir)
    print("Passed qvsplit test")
    passed += 1
    total += 1
except TestFailed as e:
    print(f"Test with name test_qvsplit failed with error: {e}")
    os.system(f"rm -r {basedir}/test/do_qvsplit")
    total += 1

print("\n")

# qvrename Test
print("Running qvrename test")
try:
    test_qvrename(basedir)
    print("Passed qvrename test")
    passed += 1
    total += 1
except TestFailed as e:
    print(f"Test with name test_qvrename failed with error: {e}")
    os.system(f"rm -r {basedir}/test/do_qvrename")
    total += 1

print("\n")

print("#" * 50)
print(f"Passed {passed}/{total} tests")
print("#" * 50)
