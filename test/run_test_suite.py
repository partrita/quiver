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
import pandas as pd
from quiver import Quiver
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
    Test that we can turn a directory of PDB files into a Quiver file and
    then extract the PDB files from the Quiver file. And that the extracted
    PDB files are identical to the original PDB files.
    """

    # Go into the test directory
    os.chdir(f"{basedir}/test")

    # Create a temporary directory
    os.system("mkdir -p zipextract")

    os.chdir("zipextract")

    # Zip the PDB files into a Quiver file
    os.system(
        f"{basedir}/src/quiver/qvfrompdbs.sh {basedir}/test/input_for_tests/*.pdb > test.qv"
    )

    # Extract the PDB files from the Quiver file
    os.chdir(f"{basedir}/test/zipextract")

    os.system(f"{basedir}/src/quiver/qvextract.py test.qv")

    # Compare the extracted PDB files to the original PDB files
    for file in glob.glob("*.pdb"):
        otherfile = f"{basedir}/test/input_for_tests/{file}"

        # Compare the two files
        with open(file, "r") as f:
            lines = f.readlines()
        with open(otherfile, "r") as f:
            otherlines = f.readlines()

        if lines != otherlines:
            raise TestFailed(f"File {file} does not match {otherfile}")

    # Remove the temporary directory
    os.chdir(f"{basedir}")
    os.system(f"rm -r {basedir}/test/zipextract")


def test_qvls(basedir):
    """
    Test that qvls returns the correct list of tags for a given Quiver file
    """

    # Go into the test directory
    os.chdir(f"{basedir}/test")

    # Create a temporary directory
    os.system("mkdir -p do_qvls")

    os.chdir("do_qvls")

    # Zip the PDB files into a Quiver file
    os.system(
        f"{basedir}/src/quiver/qvfrompdbs.sh {basedir}/test/input_for_tests/*.pdb > test.qv"
    )

    # Run qvls
    os.system(f"{basedir}/src/quiver/qvls.py test.qv > qvls_output.txt")

    # Ensure that all pdbs are listed
    with open("qvls_output.txt", "r") as f:
        lines = [line.strip() for line in f.readlines()]

    # Get the list of PDB files
    pdbs = glob.glob(f"{basedir}/test/input_for_tests/*.pdb")

    # Check that all PDB files are listed
    for pdb in pdbs:
        tag = os.path.basename(pdb)[:-4]
        if tag not in lines:
            print(f"LINES: {lines}")
            print(f"TAG: {tag}")
            raise TestFailed(f"PDB file {tag} not listed in qvls output")

    # Clean up
    os.chdir(f"{basedir}")
    os.system(f"rm -r {basedir}/test/do_qvls")


def test_qvextractspecific(basedir):
    os.chdir(f"{basedir}/test")
    test_dir = os.path.join(basedir, "test", "do_qvextractspecific")

    # 디렉토리 생성 방식 변경
    os.makedirs(test_dir, exist_ok=True)
    os.chdir(test_dir)

    # 기존 *.pdb 파일 삭제
    for f in glob.glob("*.pdb"):
        os.remove(f)

    # Quiver 파일 생성
    os.system(
        f"{basedir}/src/quiver/qvfrompdbs.sh {basedir}/test/input_for_tests/*.pdb > test.qv"
    )

    # 태그 추출
    os.system(f"{basedir}/src/quiver/qvls.py test.qv | shuf | head -n 5 > tags.txt")

    # Extraction 명령어 수정 (--output-dir 추가)
    os.system(
        f"cat tags.txt | {basedir}/src/quiver/qvextractspecific.py test.qv --output-dir {test_dir}"
    )

    with open("tags.txt", "r") as f:
        lines = [line.strip() for line in f.readlines()]

    # 파일 존재 여부 확인
    missing = [tag for tag in lines if not os.path.exists(f"{tag}.pdb")]
    if missing:
        raise TestFailed(f"Missing PDBs: {missing}")

    # Get list of pdbs in this directory
    pdbs = glob.glob("*.pdb")
    pdb_tags = [os.path.basename(pdb)[:-4] for pdb in pdbs]

    if set(lines) != set(pdb_tags):
        print(f"lines: {lines}")
        print(f"pdb_tags: {pdb_tags}")
        raise TestFailed("qvextractspecific did not return the correct PDB files")

    for tag in lines:
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

    We are testing the following:

    1) qvslice is slicing the requested tags

    2) qvslice is correctly zipping the requested tags, this is tested
       by running qvextract on the output of qvslice and comparing the
       extracted PDB files to the original PDB files
    """

    # Go into the test directory
    os.chdir(f"{basedir}/test")

    # Create a temporary directory
    os.system("mkdir -p do_qvslice")

    os.chdir("do_qvslice")

    # Zip the PDB files into a Quiver file
    os.system(
        f"{basedir}/src/quiver/qvfrompdbs.sh {basedir}/test/input_for_tests/*.pdb > test.qv"
    )

    # Get 5 random tags
    os.system(f"{basedir}/src/quiver/qvls.py test.qv | shuf | head -n 5 > tags.txt")

    # Run qvslice
    os.system(f"cat tags.txt | {basedir}/src/quiver/qvslice.py test.qv > sliced.qv")

    # Run qvextract
    os.system(f"{basedir}/src/quiver/qvextract.py sliced.qv")

    # Get the list of PDB files in this directory
    pdbs = glob.glob("*.pdb")
    pdb_tags = [os.path.basename(pdb)[:-4] for pdb in pdbs]

    # Ensure that the correct PDB files are returned
    with open("tags.txt", "r") as f:
        tags = [line.strip() for line in f.readlines()]

    if set(tags) != set(pdb_tags):
        print(f"PDB tags: {pdb_tags}")
        print(f"Tags: {tags}")
        raise TestFailed("qvslice did not return the correct PDB files")

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
    os.system(f"rm -r {basedir}/test/do_qvslice")


def test_qvsplit(basedir):
    """
    Test that qvsplit returns the correct PDB lines for a given set of
    tags in a Quiver file

    We will test that:

    1) qvsplit returns the correct number of quiver files
    2) Each Quiver file contains the correct number of PDB files
    3) All pdbs which were zipped into the original quiver file are represented
       in the output quiver files

    These three conditions are sufficient to ensure that qvsplit is working
    """

    # Go into the test directory
    os.chdir(f"{basedir}/test")

    # Create a temporary directory
    os.system("mkdir -p do_qvsplit")

    os.chdir("do_qvsplit")

    # Zip the PDB files into a Quiver file
    os.system(
        f"{basedir}/src/quiver/qvfrompdbs.sh {basedir}/test/input_for_tests/*.pdb > test.qv"
    )

    os.mkdir("split")

    os.chdir("split")

    # Run qvsplit
    os.system(f"{basedir}/src/quiver/qvsplit.py ../test.qv 3")

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

    # Ensure that each quiver file contains the correct number of PDB files
    # Except for the last quiver file, which may contain fewer PDB files
    for i in range(num_quivers - 1):
        # Get the number of PDB files in this quiver file
        local_num_pdbs = 0

        with open(f"split_{i}.qv", "r") as f:
            for line in f.readlines():
                if line.startswith("QV_TAG"):
                    local_num_pdbs += 1

        # Ensure that the correct number of PDB files were created
        if local_num_pdbs != 3:
            raise TestFailed(
                f"qvsplit did not return the correct number of PDB files, "
                f"expected 3, got {local_num_pdbs}"
            )

    # Reset local_num_pdbs
    local_num_pdbs = 0

    with open(f"split_{num_quivers - 1}.qv", "r") as f:
        for line in f.readlines():
            if line.startswith("QV_TAG"):
                local_num_pdbs += 1

    # Ensure that the correct number of PDB files were created
    if local_num_pdbs != num_pdbs % 3:
        raise TestFailed(
            f"qvsplit did not return the correct number of PDB files, "
            f"expected {num_pdbs % 3}, got {local_num_pdbs}"
        )

    # Extract the PDB files from each quiver file
    for i in range(num_quivers):
        # Run qvextract
        os.system(f"{basedir}/src/quiver/qvextract.py split_{i}.qv")

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
    We are testing:

    1) qvrename assigns the correct names to the Quiver file entries

    2) The entries in the Quiver file are unchanged except for the names

    3) Checks that the score lines are also renamed
    """

    # Go into the test directory
    os.chdir(f"{basedir}/test")

    # Create a temporary directory
    os.system("mkdir -p do_qvrename")

    os.chdir("do_qvrename")

    # Get the input Quiver filepath
    qvpath = f"{basedir}/test/input_for_tests/designs_scored.qv"
    if not os.path.exists("input_pdbs"):
        os.mkdir("input_pdbs")
    os.chdir("input_pdbs")

    # Extract the PDB files from the Quiver file
    os.system(f"{basedir}/src/quiver/qvextract.py {qvpath}")

    # Store current path
    inpdbdir = os.getcwd()

    os.chdir(f"{basedir}/test/do_qvrename")

    # Get the Quiver tags
    inqv = Quiver(qvpath, "r")
    tags = inqv.get_tags()

    # Make a random set of names to rename the entries to
    newtags = [f"{uuid.uuid4()}" for tag in tags]

    # Write the new tags to a file
    with open("newtags.txt", "w") as f:
        for tag in newtags:
            f.write(f"{tag}\n")

    # Run qvrename
    os.system(
        f"cat newtags.txt | {basedir}/src/quiver/qvrename.py {qvpath} > renamed.qv"
    )

    # Run qvextract
    os.system(f"{basedir}/src/quiver/qvextract.py renamed.qv")

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
    os.system(f"{basedir}/src/quiver/qvscorefile.py {qvpath}")
    ogsc = qvpath.split(".")[0] + ".sc"

    ogdf = pd.read_csv(ogsc, sep="\t")

    # Get the score lines of the new Quiver file
    os.system(f"{basedir}/src/quiver/qvscorefile.py renamed.qv")
    newsc = "renamed.sc"

    newdf = pd.read_csv(newsc, sep="\t")

    # Pair the old tags with the new tags and assert that the score lines are the same
    # other than the name
    for idx in range(len(tags)):
        # Get the old score line with 'tag' column equal to the old tag
        oldrow = ogdf.loc[ogdf["tag"] == tags[idx]]

        # Get the new score line with 'tag' column equal to the new tag
        newrow = newdf.loc[newdf["tag"] == newtags[idx]]

        # Check that the two rows are identical except for the tag
        for key in oldrow.keys():
            if key == "tag":
                continue
            if oldrow[key].values[0] != newrow[key].values[0]:
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
