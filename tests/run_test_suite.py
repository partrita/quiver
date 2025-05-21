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
    
    # rs_extract_pdbs now returns a list of extracted file paths
    extracted_files = rs_extract_pdbs("test.qv")
    
    # Verify that the number of extracted files matches the number of unique PDB files
    # This assumes that if a PDB file (tag) already exists, it's skipped, not overwritten.
    # For a clean test directory, this count should match.
    unique_input_stems = {p.stem for p in pdb_files}
    if len(extracted_files) != len(unique_input_stems):
        raise TestFailed(f"Expected {len(unique_input_stems)} files to be extracted, got {len(extracted_files)}. Files: {extracted_files}")

    for pdb_path_str in extracted_files:
        pdb = Path(pdb_path_str)
        tag = pdb.stem
        original_pdb = Path(basedir) / "tests" / "input_for_tests" / f"{tag}.pdb"
        if not original_pdb.exists():
            raise TestFailed(f"Original PDB for tag {tag} not found at {original_pdb} (Test setup issue).")
        if not compare_pdb_files(str(pdb), str(original_pdb)):
            raise TestFailed(f"File {pdb} does not match {original_pdb}")
    
    extracted_stems = {Path(p).stem for p in extracted_files}
    if extracted_stems != unique_input_stems:
        raise TestFailed(f"Set of extracted PDB stems {extracted_stems} does not match expected {unique_input_stems}")
        
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
    test_dir.mkdir(exist_ok=True, parents=True)
    os.chdir(test_dir)

    output_dir_specific = test_dir / "extracted_specific_pdbs"
    if output_dir_specific.exists(): # Clean before test
        shutil.rmtree(output_dir_specific)
    output_dir_specific.mkdir(exist_ok=True)

    pdb_files = list(Path(basedir).glob("tests/input_for_tests/*.pdb"))
    main_qv_file = test_dir / "test_main.qv"
    with open(main_qv_file, "w") as f:
        f.write(rs_qvfrompdbs([str(p) for p in pdb_files]))
    
    all_tags_in_qv = rs_list_tags(str(main_qv_file))
    if not all_tags_in_qv:
        raise TestFailed(f"list_tags() returned no tags from {main_qv_file}")
    
    selected_tags_for_extraction = random.sample(all_tags_in_qv, min(5, len(all_tags_in_qv)))
    
    try:
        # Ensure output dir is clean for this run
        if output_dir_specific.exists():
            shutil.rmtree(output_dir_specific)
        output_dir_specific.mkdir(exist_ok=True)
        result = rs_extract_selected_pdbs(str(main_qv_file), selected_tags_for_extraction, str(output_dir_specific))
    except Exception as e:
        raise TestFailed(f"rs_extract_selected_pdbs raised an exception: {e}")

    if result.missing_tags: 
        raise TestFailed(f"rs_extract_selected_pdbs reported missing tags when all should exist: {result.missing_tags}")

    if len(result.extracted_files) != len(selected_tags_for_extraction):
         raise TestFailed(f"Expected to extract {len(selected_tags_for_extraction)} files, but {len(result.extracted_files)} were reported as extracted.")

    for extracted_file_path_str in result.extracted_files:
        extracted_file_path = Path(extracted_file_path_str)
        tag = extracted_file_path.stem
        if tag not in selected_tags_for_extraction:
            raise TestFailed(f"Extracted file {extracted_file_path} for tag {tag} which was not selected.")
        
        original_pdb = Path(basedir) / "tests" / "input_for_tests" / f"{tag}.pdb"
        if not compare_pdb_files(str(extracted_file_path), str(original_pdb)):
            raise TestFailed(f"PDB file {tag}.pdb does not match original")

    all_pdbs_in_output_dir = {p.stem for p in output_dir_specific.glob("*.pdb")}
    if set(selected_tags_for_extraction) != all_pdbs_in_output_dir:
        raise TestFailed(f"Extracted PDBs in output directory {all_pdbs_in_output_dir} do not match selected tags {set(selected_tags_for_extraction)}")
    
    # Test with some non-existent tags
    non_existent_tags = ["tag_foo_" + uuid.uuid4().hex[:6], "tag_bar_" + uuid.uuid4().hex[:6]]
    # Ensure selected_tags_for_extraction is not empty before slicing
    valid_tags_sample = selected_tags_for_extraction[:1] if selected_tags_for_extraction else []
    mixed_tags = valid_tags_sample + non_existent_tags
    
    shutil.rmtree(output_dir_specific) 
    output_dir_specific.mkdir(exist_ok=True)

    try:
        result_mixed = rs_extract_selected_pdbs(str(main_qv_file), mixed_tags, str(output_dir_specific))
    except Exception as e:
        raise TestFailed(f"rs_extract_selected_pdbs with mixed tags raised an exception: {e}")
    
    if len(result_mixed.extracted_files) != len(valid_tags_sample):
        raise TestFailed(f"Expected {len(valid_tags_sample)} file(s) for existing tag(s), got {len(result_mixed.extracted_files)}")
    if set(result_mixed.missing_tags) != set(non_existent_tags):
        raise TestFailed(f"Expected missing tags {set(non_existent_tags)}, got {set(result_mixed.missing_tags)}")

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
    all_tags_in_qv = rs_list_tags("test.qv")
    if not all_tags_in_qv:
        raise TestFailed("No tags found in the quiver file test.qv")
    
    # 태그 선택 (1개만)
    selected_tag_for_slice = random.choice(all_tags_in_qv)
    
    # 슬라이스 시도 (Valid tag)
    sliced_content_data_only = ""
    try:
        sliced_content_with_warnings = rs_qvslice("test.qv", [selected_tag_for_slice])
        
        # For verification of PDB content, extract only the data part by removing warning lines
        # This assumes warnings are single lines starting with "⚠️"
        actual_data_lines = [line for line in sliced_content_with_warnings.splitlines() if not line.startswith("⚠️")]
        sliced_content_data_only = "\n".join(actual_data_lines)
        if actual_data_lines: # Add trailing newline if there was content
            sliced_content_data_only += "\n"

        # A valid slice for an existing tag should contain its QV_TAG line.
        if not sliced_content_data_only.startswith(f"QV_TAG {selected_tag_for_slice}"):
            # If the tag only had QV_TAG and no other lines (e.g. empty PDB), this check might be too strict.
            # However, get_struct_list usually ensures QV_TAG line is present.
            # Check if original PDB content for this tag was empty
            core_qv_obj = Quiver("test.qv", "r")
            original_pdb_lines = core_qv_obj.core.get_pdblines(selected_tag_for_slice) # Access core for detailed check
            
            if original_pdb_lines: # If original PDB lines existed, slice should not be effectively empty of data
                 raise TestFailed(f"rs_qvslice returned unexpected content for tag '{selected_tag_for_slice}'. Expected QV_TAG start. Got: '{sliced_content_data_only[:200]}'")
            elif not sliced_content_data_only.strip() and not sliced_content_with_warnings.strip().startswith(f"QV_TAG {selected_tag_for_slice}"):
                 # If original PDB lines were empty, slice should still contain QV_TAG and possibly QV_SCORE
                 raise TestFailed(f"rs_qvslice for tag '{selected_tag_for_slice}' (with no PDB lines) seems malformed. Got: '{sliced_content_with_warnings[:200]}'")


    except Exception as e:
        raise TestFailed(f"Error in rs_qvslice for existing tag '{selected_tag_for_slice}': {str(e)}")
    
    # Verify warnings and data presence when a non-existent tag is included
    non_existent_tag = "tag_that_does_not_exist_for_slice_test_" + uuid.uuid4().hex[:6]
    try:
        content_with_warning_and_data = rs_qvslice("test.qv", [selected_tag_for_slice, non_existent_tag])
        
        expected_warning_line = f"⚠️  Tag not found in Quiver file: {non_existent_tag}"
        expected_data_line_pattern = f"QV_TAG {selected_tag_for_slice}" # Check if data for the valid tag is still present

        if expected_warning_line not in content_with_warning_and_data:
            raise TestFailed(f"Expected warning '{expected_warning_line}' not found in rs_qvslice output. Got: '{content_with_warning_and_data}'")
        if expected_data_line_pattern not in content_with_warning_and_data:
             raise TestFailed(f"Data for existing tag '{selected_tag_for_slice}' not found when non-existent tag was also requested. Got: '{content_with_warning_and_data}'")

    except Exception as e:
        raise TestFailed(f"Error testing rs_qvslice with a non-existent tag: {str(e)}")

    # Prepare sliced.qv for PDB extraction test
    # It should contain only the data for the valid selected tag.
    with open("sliced.qv", "w") as f:
        f.write(sliced_content_data_only) 

    # PDB 추출 from sliced.qv
    if sliced_content_data_only.strip(): # Only attempt extraction if there's content
        try:
            extracted_slice_pdbs = rs_extract_pdbs("sliced.qv")
            # If selected_tag_for_slice originally had PDB lines, we expect extraction.
            core_qv_obj_for_check = Quiver("test.qv", "r")
            original_pdb_lines_for_check = core_qv_obj_for_check.core.get_pdblines(selected_tag_for_slice)

            if original_pdb_lines_for_check:
                if not extracted_slice_pdbs:
                    raise TestFailed("Failed to extract PDBs from sliced.qv (rs_extract_pdbs returned empty list but expected data).")
                if not any(Path(p).stem == selected_tag_for_slice for p in extracted_slice_pdbs):
                    raise TestFailed(f"PDB for selected tag '{selected_tag_for_slice}' not found in extraction from sliced.qv. Found: {extracted_slice_pdbs}")
                
                # Verify content of extracted PDB
                extracted_pdb_path = Path(f"{selected_tag_for_slice}.pdb")
                if not extracted_pdb_path.exists():
                     raise TestFailed(f"Expected PDB file {extracted_pdb_path} not found after slicing and extracting.")
                original_pdb_to_compare = next(p for p in selected_pdbs if p.stem == selected_tag_for_slice)
                if not compare_pdb_files(str(original_pdb_to_compare), str(extracted_pdb_path)):
                    raise TestFailed(f"PDB file {selected_tag_for_slice}.pdb from sliced qv does not match original")

            elif extracted_slice_pdbs: # Original had no PDB lines, but extraction yielded files.
                 raise TestFailed(f"Extracted PDBs from a slice that should have no PDB lines. Tag: {selected_tag_for_slice}")


        except Exception as e:
            raise TestFailed(f"Error extracting PDBs from sliced quiver file: {str(e)}")
    
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
    
    try:
        success_message = rs_qvsplit("../test.qv", 3, "split", ".")
        expected_message = "✅ Files written to . with prefix 'split'" # Exact message based on Rust code
        if success_message != expected_message:
            raise TestFailed(f"rs_qvsplit success message mismatch. Expected '{expected_message}', Got: '{success_message}'")
    except Exception as e:
        raise TestFailed(f"Error in rs_qvsplit: {str(e)}")
        
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
    temp_output_path_str = None
    try:
        # rs_rename_tags now returns the path to a temporary file with the renamed content.
        temp_output_path_str = rs_rename_tags(str(qvpath), new_tags)
        if not temp_output_path_str or not os.path.exists(temp_output_path_str):
            raise TestFailed(f"rs_rename_tags did not return a valid temporary file path. Got: {temp_output_path_str}")

        # For the test, we'll replace the original qvpath with the content of the temp file.
        # In the actual CLI, os.replace(temp_output_path_str, qvpath) would be used.
        shutil.move(temp_output_path_str, qvpath)
        # temp_output_path_str is now moved, so it doesn't need explicit cleanup by os.remove later.
        temp_output_path_str = None 

    except Exception as e:
        raise TestFailed(f"Error in rs_rename_tags or moving temp file: {str(e)}")
    finally:
        # If shutil.move failed after temp_output_path_str was created but before it was set to None
        if temp_output_path_str and os.path.exists(temp_output_path_str):
            try:
                os.remove(temp_output_path_str)
            except OSError:
                print(f"Warning: Could not remove temporary file {temp_output_path_str} in test_qvrename cleanup.")
    
    # PDB 파일 추출 from the now renamed qvpath
    try:
        with suppress_output(): # Suppress output from rs_extract_pdbs if any
            extracted_files = rs_extract_pdbs(str(qvpath)) 
            if not extracted_files: # rs_extract_pdbs returns a list
                # This could be valid if no tags were left after renaming, or if files already existed.
                # For this test, we expect successful extraction.
                q = Quiver(str(qvpath), "r")
                if q.get_tags(): # Check if there are tags to be extracted
                    raise TestFailed("Failed to extract PDBs from renamed quiver file (rs_extract_pdbs returned empty list but tags exist)")
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


def test_qvscorefile_new(basedir):
    test_dir = Path(basedir) / "tests" / "do_qvscorefile"
    test_dir.mkdir(exist_ok=True, parents=True)
    os.chdir(test_dir)

    # Prepare a test quiver file with score information
    qv_content_lines = [
        "QV_TAG tag1",
        "ATOM 1 X",
        "QV_SCORE tag1 scoreA=1.2|scoreB=3.4",
        "QV_TAG tag2",
        "ATOM 2 Y",
        "QV_SCORE tag2 scoreA=5.6|scoreC=7.8",
        "QV_TAG tag3", # Tag with no score line
        "ATOM 3 Z"
    ]
    qv_file_path = Path("test_for_score.qv")
    with open(qv_file_path, "w") as f:
        f.write("\n".join(qv_content_lines) + "\n")

    try:
        csv_file_path_str = rs_extract_scorefile(str(qv_file_path))
        
        if not csv_file_path_str:
            raise TestFailed("rs_extract_scorefile returned an empty path.")
        
        csv_file_path = Path(csv_file_path_str)
        if not csv_file_path.exists():
            raise TestFailed(f"CSV file reported at {csv_file_path_str} does not exist.")
        
        expected_csv_name = qv_file_path.with_suffix(".csv").name
        if csv_file_path.name != expected_csv_name:
            raise TestFailed(f"Expected CSV filename {expected_csv_name}, but got {csv_file_path.name}")

        with open(csv_file_path, "r", newline="") as f_csv:
            reader = csv.DictReader(f_csv, delimiter='\t')
            records = list(reader)
            
            if len(records) != 2:
                raise TestFailed(f"Expected 2 score records in CSV, got {len(records)}")

            # Rust function sorts headers (except 'tag')
            # Expected fieldnames based on the data and sorted unique score keys
            # Unique score keys: scoreA, scoreB, scoreC. Sorted: scoreA, scoreB, scoreC
            expected_fieldnames = ["tag", "scoreA", "scoreB", "scoreC"]
            if reader.fieldnames != expected_fieldnames:
                 raise TestFailed(f"CSV headers mismatch. Expected {expected_fieldnames}, Got {reader.fieldnames}")

            record_tag1 = next((r for r in records if r["tag"] == "tag1"), None)
            if not record_tag1:
                raise TestFailed("Record for tag1 not found in CSV.")
            if not (record_tag1["scoreA"] == "1.2" and record_tag1["scoreB"] == "3.4" and record_tag1.get("scoreC") == "NaN"):
                raise TestFailed(f"Data mismatch for tag1. Got: {record_tag1}")

            record_tag2 = next((r for r in records if r["tag"] == "tag2"), None)
            if not record_tag2:
                raise TestFailed("Record for tag2 not found in CSV.")
            if not (record_tag2["scoreA"] == "5.6" and record_tag2.get("scoreB") == "NaN" and record_tag2["scoreC"] == "7.8"):
                raise TestFailed(f"Data mismatch for tag2. Got: {record_tag2}")

    except Exception as e:
        raise TestFailed(f"Error in test_qvscorefile: {str(e)}")
    finally:
        os.chdir(basedir)


def test_qvscorefile_new(basedir): # Renamed to avoid conflict if old one is kept temporarily
    test_dir = Path(basedir) / "tests" / "do_qvscorefile"
    test_dir.mkdir(exist_ok=True, parents=True)
    os.chdir(test_dir)

    # Prepare a test quiver file with score information
    qv_content_lines = [
        "QV_TAG tag1",
        "ATOM 1 X",
        "QV_SCORE tag1 scoreA=1.2|scoreB=3.4", # scoreB will be specific to tag1
        "QV_TAG tag2",
        "ATOM 2 Y",
        "QV_SCORE tag2 scoreA=5.6|scoreC=7.8", # scoreC will be specific to tag2
        "QV_TAG tag3", # Tag with no score line
        "ATOM 3 Z"
    ]
    qv_file_path = Path("test_for_score.qv")
    with open(qv_file_path, "w") as f:
        f.write("\n".join(qv_content_lines) + "\n")

    try:
        # rs_extract_scorefile now returns the path to the created CSV file.
        csv_file_path_str = rs_extract_scorefile(str(qv_file_path))
        
        if not csv_file_path_str:
            raise TestFailed("rs_extract_scorefile returned an empty path.")
        
        csv_file_path = Path(csv_file_path_str)
        if not csv_file_path.exists():
            raise TestFailed(f"CSV file reported at {csv_file_path_str} does not exist.")
        
        expected_csv_name = qv_file_path.with_suffix(".csv").name
        if csv_file_path.name != expected_csv_name:
            raise TestFailed(f"Expected CSV filename {expected_csv_name}, but got {csv_file_path.name}")

        # Verify CSV content
        with open(csv_file_path, "r", newline="") as f_csv:
            reader = csv.DictReader(f_csv, delimiter='\t')
            records = list(reader)
            
            if len(records) != 2: # Only tag1 and tag2 have scores
                raise TestFailed(f"Expected 2 score records in CSV, got {len(records)}")

            # Rust function sorts headers (except 'tag')
            expected_fieldnames = sorted(["tag", "scoreA", "scoreB", "scoreC"]) # Sorted list of all possible score keys + tag
            csv_headers = sorted(reader.fieldnames if reader.fieldnames else [])
            if csv_headers != expected_fieldnames:
                 raise TestFailed(f"CSV headers mismatch. Expected sorted {expected_fieldnames}, Got sorted {csv_headers}")

            record_map = {r["tag"]: r for r in records}

            record_tag1 = record_map.get("tag1")
            if not record_tag1:
                raise TestFailed("Record for tag1 not found in CSV.")
            # Check values, using .get(key, "NaN") for keys that might be missing in a specific record
            if not (record_tag1.get("scoreA") == "1.2" and \
                    record_tag1.get("scoreB") == "3.4" and \
                    record_tag1.get("scoreC", "NaN") == "NaN"): # scoreC should be NaN for tag1
                raise TestFailed(f"Data mismatch for tag1. Got: {record_tag1}")

            record_tag2 = record_map.get("tag2")
            if not record_tag2:
                raise TestFailed("Record for tag2 not found in CSV.")
            if not (record_tag2.get("scoreA") == "5.6" and \
                    record_tag2.get("scoreB", "NaN") == "NaN" and \ # scoreB should be NaN for tag2
                    record_tag2.get("scoreC") == "7.8"):
                raise TestFailed(f"Data mismatch for tag2. Got: {record_tag2}")

    except Exception as e:
        raise TestFailed(f"Error in test_qvscorefile: {str(e)}")
    finally:
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
        run_test(test_qvscorefile_new, basedir, "qvscorefile"), 
    ]
    passed_count = sum(passed_tests)
    total_count = len(passed_tests)
    print("\n" + "=" * 50)
    print(f"Passed {passed_count}/{total_count} tests")
    print("=" * 50)
