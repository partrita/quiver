#!/usr/bin/env python3
"""Tests for the Quiver library."""

import sys
import os
import math
import uuid
import csv
import glob
import shutil
from quiver_pdb import (
    Quiver,
    rs_qvfrompdbs,
    rs_extract_pdbs,
    rs_list_tags,
    rs_rename_tags,
    rs_qvslice,
    rs_qvsplit,
    rs_extract_scorefile,
)

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


class TestFailed(Exception):
    pass


def normalize_pdb_content(content):
    return "\n".join(line.strip() for line in content.splitlines() if line.strip())


def compare_pdb_files(file1, file2):
    with open(file1, "r") as f1, open(file2, "r") as f2:
        return normalize_pdb_content(f1.read()) == normalize_pdb_content(f2.read())


def run_test(test_func, basedir, test_name):
    print(f"Running {test_name} test")
    try:
        test_func(basedir)
        print(f"Passed {test_name} test")
        return True
    except TestFailed as e:
        print(f"Test {test_name} failed with error: {e}")
        return False
    finally:
        cleanup_test_directory(basedir, test_name)


def cleanup_test_directory(basedir, test_name):
    test_dir = os.path.join(basedir, "test", f"do_{test_name}")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)
    for file in glob.glob(os.path.join(basedir, "test", f"do_{test_name}", "*.qv")):
        os.remove(file)


def test_zip_and_extract(basedir):
    test_dir = os.path.join(basedir, "test", "do_zip_and_extract")
    os.makedirs(test_dir, exist_ok=True)
    os.chdir(test_dir)
    pdb_files = glob.glob(f"{basedir}/test/input_for_tests/*.pdb")
    with open("test.qv", "w") as f:
        f.write(rs_qvfrompdbs(pdb_files))
    rs_extract_pdbs("test.qv")
    for pdb in glob.glob("*.pdb"):
        tag = os.path.basename(pdb)[:-4]
        print(f"✅ Extracted {tag}")
        original_pdb = f"{basedir}/test/input_for_tests/{tag}.pdb"
        if not compare_pdb_files(pdb, original_pdb):
            raise TestFailed(f"File {pdb} does not match {original_pdb}")
    os.chdir(basedir)


def test_qvls(basedir):
    test_dir = os.path.join(basedir, "test", "do_qvls")
    os.makedirs(test_dir, exist_ok=True)
    os.chdir(test_dir)
    pdb_files = glob.glob(f"{basedir}/test/input_for_tests/*.pdb")
    with open("test.qv", "w") as f:
        f.write(rs_qvfrompdbs(pdb_files))
    tags = rs_list_tags("test.qv")
    if not tags:
        raise TestFailed("list_tags() returned None")
    expected_tags = [
        os.path.basename(pdb)[:-4]
        for pdb in glob.glob(f"{basedir}/test/input_for_tests/*.pdb")
    ]
    if set(tags) != set(expected_tags):
        raise TestFailed(f"Expected tags: {expected_tags}, got: {tags}")
    os.chdir(basedir)


def test_qvextractspecific(basedir):
    test_dir = os.path.join(basedir, "test", "do_qvextractspecific")
    os.makedirs(test_dir, exist_ok=True)
    os.chdir(test_dir)
    for f in glob.glob("*.pdb"):
        os.remove(f)
    pdb_files = glob.glob(f"{basedir}/test/input_for_tests/*.pdb")
    with open("test.qv", "w") as f:
        f.write(rs_qvfrompdbs(pdb_files))
    tags = rs_list_tags("test.qv")
    selected_tags = random.sample(tags, min(5, len(tags)))
    for tag in selected_tags:
        with open("temp.qv", "w") as f:
            sliced_qv = rs_qvslice("test.qv", [tag])
            if not sliced_qv:
                raise TestFailed("rs_qvslice returned None")
            f.write(sliced_qv)
        rs_extract_pdbs("temp.qv")
        os.remove("temp.qv")
        if not os.path.exists(f"{tag}.pdb"):
            raise TestFailed(f"Missing PDB: {tag}.pdb")
        original_pdb = f"{basedir}/test/input_for_tests/{tag}.pdb"
        if not compare_pdb_files(f"{tag}.pdb", original_pdb):
            raise TestFailed(f"PDB file {tag}.pdb does not match original")
    extracted_pdbs = [os.path.basename(pdb)[:-4] for pdb in glob.glob("*.pdb")]
    if set(selected_tags) != set(extracted_pdbs):
        raise TestFailed("Extracted PDBs do not match selected tags")
    os.chdir(basedir)


def test_qvslice(basedir):
    test_dir = os.path.join(basedir, "test", "do_qvslice")
    os.makedirs(test_dir, exist_ok=True)
    os.chdir(test_dir)
    pdb_files = glob.glob(f"{basedir}/test/input_for_tests/*.pdb")
    with open("test.qv", "w") as f:
        f.write(rs_qvfrompdbs(pdb_files))
    tags = rs_list_tags("test.qv")
    selected_tags = random.sample(tags, min(5, len(tags)))
    sliced_content = rs_qvslice("test.qv", selected_tags)
    if not sliced_content:
        raise TestFailed("rs_qvslice returned None")
    with open("sliced.qv", "w") as f:
        f.write(sliced_content)
    rs_extract_pdbs("sliced.qv")
    extracted_pdbs = [os.path.basename(pdb)[:-4] for pdb in glob.glob("*.pdb")]
    if set(selected_tags) != set(extracted_pdbs):
        raise TestFailed("Extracted PDBs from slice do not match selected tags")
    for tag in selected_tags:
        original_pdb = f"{basedir}/test/input_for_tests/{tag}.pdb"
        if not compare_pdb_files(f"{tag}.pdb", original_pdb):
            raise TestFailed(f"PDB file {tag}.pdb from slice does not match original")
    os.chdir(basedir)


def test_qvsplit(basedir):
    test_dir = os.path.join(basedir, "test", "do_qvsplit")
    os.makedirs(test_dir, exist_ok=True)
    os.chdir(test_dir)
    pdb_files = glob.glob(f"{basedir}/test/input_for_tests/*.pdb")
    with open("test.qv", "w") as f:
        f.write(rs_qvfrompdbs(pdb_files))
    os.makedirs("split", exist_ok=True)
    os.chdir("split")
    rs_qvsplit("../test.qv", 3, "split", ".")
    num_pdbs = len(glob.glob(f"{basedir}/test/input_for_tests/*.pdb"))
    num_quivers = len(glob.glob("*.qv"))
    if num_quivers != math.ceil(num_pdbs / 3):
        raise TestFailed(
            f"Expected {math.ceil(num_pdbs / 3)} quiver files, got {num_quivers}"
        )
    all_extracted_tags = set()
    for qv_file in glob.glob("*.qv"):
        rs_extract_pdbs(qv_file)
        all_extracted_tags.update(
            os.path.basename(pdb)[:-4] for pdb in glob.glob("*.pdb")
        )
    expected_tags = {
        os.path.basename(pdb)[:-4]
        for pdb in glob.glob(f"{basedir}/test/input_for_tests/*.pdb")
    }
    if all_extracted_tags != expected_tags:
        raise TestFailed("Extracted PDBs after split do not match original set")
    for tag in expected_tags:
        original_pdb = f"{basedir}/test/input_for_tests/{tag}.pdb"
        if not compare_pdb_files(f"{tag}.pdb", original_pdb):
            raise TestFailed(f"PDB file {tag}.pdb after split does not match original")
    os.chdir(basedir)


def test_qvrename(basedir):
    test_dir = os.path.join(basedir, "test", "do_qvrename")
    os.makedirs(test_dir, exist_ok=True)
    os.chdir(test_dir)
    qvpath = f"{basedir}/test/input_for_tests/designs_scored.qv"
    os.makedirs("input_pdbs", exist_ok=True)
    os.chdir("input_pdbs")
    rs_extract_pdbs(qvpath)
    input_pdb_dir = os.getcwd()
    os.chdir(test_dir)
    inqv = Quiver(qvpath, "r")
    tags = inqv.get_tags()
    new_tags = [f"{uuid.uuid4()}" for _ in tags]
    renamed_qv_content = rs_rename_tags(qvpath, new_tags)
    if not renamed_qv_content:
        raise TestFailed("rs_rename_tags returned None")
    with open("renamed.qv", "w") as f:
        f.write(renamed_qv_content)
    rs_extract_pdbs("renamed.qv")
    original_scores = {}
    rs_extract_scorefile(qvpath)
    with open(qvpath.replace(".qv", ".sc"), "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            original_scores[row["tag"]] = row
    rs_extract_scorefile("renamed.qv")
    with open("renamed.csv", "r") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            new_scores = {row["tag"]: row}
            original_tag = tags[new_tags.index(row["tag"])]
            if not compare_pdb_files(
                os.path.join(input_pdb_dir, f"{original_tag}.pdb"), f"{row['tag']}.pdb"
            ):
                raise TestFailed(
                    f"Renamed PDB {row['tag']}.pdb does not match original {original_tag}.pdb"
                )
            if original_tag not in original_scores:
                raise TestFailed(f"Original tag {original_tag} not found in scores")
            for key, value in original_scores[original_tag].items():
                if key == "tag":
                    continue
                if new_scores[row["tag"]].get(key) != value:
                    raise TestFailed(f"Score mismatch for {row['tag']}")
    os.chdir(basedir)


if __name__ == "__main__":
    basedir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    passed_tests = [
        run_test(test_zip_and_extract, basedir, "zip_and_extract"),
        run_test(test_qvls, basedir, "qvls"),
        run_test(test_qvextractspecific, basedir, "qvextractspecific"),
        run_test(test_qvslice, basedir, "qvslice"),
        run_test(test_qvsplit, basedir, "qvsplit"),
        run_test(test_qvrename, basedir, "qvrename"),
    ]
    passed_count = sum(passed_tests)
    total_count = len(passed_tests)
    print("\n" + "#" * 50)
    print(f"Passed {passed_count}/{total_count} tests")
    print("#" * 50)
