#!/usr/bin/env python3
"""Tests for the Quiver library."""

import sys
import os
import math
import uuid
import csv
import glob
import shutil
import random
from pathlib import Path
from contextlib import contextmanager
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

parent_dir = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(parent_dir))


class TestFailed(Exception):
    pass


@contextmanager
def suppress_output():
    """컨텍스트 매니저: stdout과 stderr 출력을 억제합니다."""
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


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
    test_dir = Path(basedir) / "tests" / f"do_{test_name}"
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)
    for pattern in ["*.qv", "*.pdb", "*.sc", "*.csv"]:
        for file in test_dir.glob(pattern):
            file.unlink(missing_ok=True)
    for dir_name in ["split", "input_pdbs"]:
        dir_path = test_dir / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path, ignore_errors=True)


def test_zip_and_extract(basedir):
    test_dir = Path(basedir) / "tests" / "do_zip_and_extract"
    test_dir.mkdir(exist_ok=True)
    os.chdir(test_dir)
    pdb_files = list(Path(basedir).glob("tests/input_for_tests/*.pdb"))
    with open("test.qv", "w") as f:
        f.write(rs_qvfrompdbs([str(p) for p in pdb_files]))
    rs_extract_pdbs("test.qv")
    for pdb in Path(".").glob("*.pdb"):
        tag = pdb.stem
        # print(f"✅ Extracted {tag}")
        original_pdb = Path(basedir) / "tests" / "input_for_tests" / f"{tag}.pdb"
        if not compare_pdb_files(str(pdb), str(original_pdb)):
            raise TestFailed(f"File {pdb} does not match {original_pdb}")
    os.chdir(basedir)


def test_qvls(basedir):
    test_dir = Path(basedir) / "tests" / "do_qvls"
    test_dir.mkdir(exist_ok=True)
    os.chdir(test_dir)
    pdb_files = list(Path(basedir).glob("tests/input_for_tests/*.pdb"))
    with open("test.qv", "w") as f:
        f.write(rs_qvfrompdbs([str(p) for p in pdb_files]))
    tags = rs_list_tags("test.qv")
    if not tags:
        raise TestFailed("list_tags() returned None")
    expected_tags = [p.stem for p in pdb_files]
    if set(tags) != set(expected_tags):
        raise TestFailed(f"Expected tags: {expected_tags}, got: {tags}")
    os.chdir(basedir)


def test_qvextractspecific(basedir):
    test_dir = Path(basedir) / "tests" / "do_qvextractspecific"
    test_dir.mkdir(exist_ok=True)
    os.chdir(test_dir)
    for f in Path(".").glob("*.pdb"):
        f.unlink()
    pdb_files = list(Path(basedir).glob("tests/input_for_tests/*.pdb"))
    with open("test.qv", "w") as f:
        f.write(rs_qvfrompdbs([str(p) for p in pdb_files]))
    tags = rs_list_tags("test.qv")
    if not tags:
        raise TestFailed("list_tags() returned None")
    selected_tags = random.sample(tags, min(5, len(tags)))
    for tag in selected_tags:
        with open("temp.qv", "w") as f:
            sliced_qv = rs_qvslice("test.qv", [tag])
            if not sliced_qv:
                raise TestFailed(f"rs_qvslice returned None for tag {tag}")
            f.write(sliced_qv)
        rs_extract_pdbs("temp.qv")
        Path("temp.qv").unlink()
        pdb_path = Path(f"{tag}.pdb")
        if not pdb_path.exists():
            raise TestFailed(f"Missing PDB: {tag}.pdb")
        original_pdb = Path(basedir) / "tests" / "input_for_tests" / f"{tag}.pdb"
        if not compare_pdb_files(str(pdb_path), str(original_pdb)):
            raise TestFailed(f"PDB file {tag}.pdb does not match original")
    extracted_pdbs = [p.stem for p in Path(".").glob("*.pdb")]
    if set(selected_tags) != set(extracted_pdbs):
        raise TestFailed("Extracted PDBs do not match selected tags")
    os.chdir(basedir)


def test_qvslice(basedir):
    test_dir = Path(basedir) / "tests" / "do_qvslice"
    test_dir.mkdir(exist_ok=True, parents=True)
    os.chdir(test_dir)
    
    # 입력 파일 준비
    pdb_files = list(Path(basedir).glob("tests/input_for_tests/*.pdb"))
    if not pdb_files:
        raise TestFailed("No PDB files found in input directory")
    
    # 테스트용 PDB 파일 복사
    input_dir = test_dir / "input"
    input_dir.mkdir(exist_ok=True)
    selected_pdbs = random.sample(pdb_files, min(3, len(pdb_files)))
    for pdb in selected_pdbs:
        shutil.copy2(pdb, input_dir / pdb.name)
    
    # Quiver 파일 생성
    with suppress_output():
        qv_content = rs_qvfrompdbs([str(p) for p in selected_pdbs])
    if not qv_content:
        raise TestFailed("rs_qvfrompdbs returned None")
    
    with open("test.qv", "w") as f:
        f.write(qv_content)
    
    # 태그 확인
    with suppress_output():
        tags = rs_list_tags("test.qv")
    if not tags:
        raise TestFailed("No tags found in the quiver file")
    
    # 태그 선택 (1개만)
    selected_tag = random.choice(tags)
    
    # 슬라이스 시도
    try:
        with suppress_output():
            sliced_content = rs_qvslice("test.qv", [selected_tag])
        if not sliced_content:
            raise TestFailed(f"rs_qvslice returned None for tag {selected_tag}")
    except Exception as e:
        raise TestFailed(f"Error in rs_qvslice: {str(e)}")
    
    with open("sliced.qv", "w") as f:
        f.write(sliced_content)
    
    # PDB 추출
    try:
        with suppress_output():
            if not rs_extract_pdbs("sliced.qv"):
                raise TestFailed("Failed to extract PDBs from sliced quiver file")
    except Exception as e:
        raise TestFailed(f"Error extracting PDBs from sliced quiver file: {str(e)}")
    
    # 결과 검증
    extracted_pdb = Path(f"{selected_tag}.pdb")
    if not extracted_pdb.exists():
        raise TestFailed(f"Expected PDB file {extracted_pdb} not found")
    
    original_pdb = next(p for p in selected_pdbs if p.stem == selected_tag)
    if not compare_pdb_files(str(original_pdb), str(extracted_pdb)):
        raise TestFailed(f"PDB file {selected_tag}.pdb does not match original")
    
    os.chdir(basedir)


def test_qvsplit(basedir):
    test_dir = Path(basedir) / "tests" / "do_qvsplit"
    test_dir.mkdir(exist_ok=True, parents=True)
    os.chdir(test_dir)
    
    pdb_files = list(Path(basedir).glob("tests/input_for_tests/*.pdb"))
    with suppress_output():
        qv_content = rs_qvfrompdbs([str(p) for p in pdb_files])
    if not qv_content:
        raise TestFailed("rs_qvfrompdbs returned None")
    
    with open("test.qv", "w") as f:
        f.write(qv_content)
    
    os.makedirs("split", exist_ok=True)
    os.chdir("split")
    with suppress_output():
        rs_qvsplit("../test.qv", 3, "split", ".")
    
    num_pdbs = len(pdb_files)
    num_quivers = len(list(Path(".").glob("*.qv")))
    if num_quivers != math.ceil(num_pdbs / 3):
        raise TestFailed(
            f"Expected {math.ceil(num_pdbs / 3)} quiver files, got {num_quivers}"
        )
    
    all_extracted_tags = set()
    for qv_file in Path(".").glob("*.qv"):
        with suppress_output():
            rs_extract_pdbs(str(qv_file))
            all_extracted_tags.update(p.stem for p in Path(".").glob("*.pdb"))
    
    expected_tags = {p.stem for p in pdb_files}
    if all_extracted_tags != expected_tags:
        raise TestFailed("Extracted PDBs after split do not match original set")
    
    for tag in expected_tags:
        original_pdb = next(p for p in pdb_files if p.stem == tag)
        if not compare_pdb_files(str(original_pdb), f"{tag}.pdb"):
            raise TestFailed(f"PDB file {tag}.pdb after split does not match original")
    
    os.chdir(basedir)


def test_qvrename(basedir):
    test_dir = Path(basedir) / "tests" / "do_qvrename"
    test_dir.mkdir(exist_ok=True, parents=True)
    os.chdir(test_dir)
    
    # 입력 파일 준비
    pdb_files = list(Path(basedir).glob("tests/input_for_tests/*.pdb"))
    if not pdb_files:
        raise TestFailed("No PDB files found in input directory")
    
    # 테스트용 PDB 파일 복사
    input_dir = test_dir / "input"
    input_dir.mkdir(exist_ok=True)
    selected_pdbs = random.sample(pdb_files, min(2, len(pdb_files)))
    for pdb in selected_pdbs:
        shutil.copy2(pdb, input_dir / pdb.name)
    
    # Quiver 파일 생성
    with suppress_output():
        qv_content = rs_qvfrompdbs([str(p) for p in selected_pdbs])
    if not qv_content:
        raise TestFailed("rs_qvfrompdbs returned None")
    
    qvpath = test_dir / "test.qv"
    with open(qvpath, "w") as f:
        f.write(qv_content)
    
    # 태그 확인
    with suppress_output():
        tags = rs_list_tags(str(qvpath))
    if not tags:
        raise TestFailed("No tags found in the quiver file")
    
    # 새 태그 생성 (매우 단순한 이름)
    new_tags = [f"test_{i:02d}" for i in range(len(tags))]
    
    # 태그 이름 변경
    try:
        with suppress_output():
            renamed_qv_content = rs_rename_tags(str(qvpath), new_tags)
        if not renamed_qv_content:
            raise TestFailed("rs_rename_tags returned None")
    except Exception as e:
        raise TestFailed(f"Error in rs_rename_tags: {str(e)}")
    
    renamed_qv_path = test_dir / "renamed.qv"
    with open(renamed_qv_path, "w") as f:
        f.write(renamed_qv_content)
    
    # PDB 파일 추출
    try:
        with suppress_output():
            if not rs_extract_pdbs(str(renamed_qv_path)):
                raise TestFailed("Failed to extract PDBs from renamed quiver file")
    except Exception as e:
        raise TestFailed(f"Error extracting PDBs from renamed quiver file: {str(e)}")
    
    # 결과 검증
    for i, (old_tag, new_tag) in enumerate(zip(tags, new_tags)):
        old_pdb = input_dir / f"{old_tag}.pdb"
        new_pdb = Path(f"{new_tag}.pdb")
        
        if not old_pdb.exists():
            raise TestFailed(f"Original PDB file not found: {old_pdb}")
        if not new_pdb.exists():
            raise TestFailed(f"Renamed PDB file not found: {new_pdb}")
        if not compare_pdb_files(str(old_pdb), str(new_pdb)):
            raise TestFailed(f"Renamed PDB {new_tag}.pdb does not match original {old_tag}.pdb")
    
    os.chdir(basedir)


if __name__ == "__main__":
    basedir = Path(__file__).parent.parent.absolute()
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
    print("\n" + "=" * 50)
    print(f"Passed {passed_count}/{total_count} tests")
    print("=" * 50)
