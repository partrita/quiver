#!/usr/bin/env python3
"""
This is a Python script using pytest for testing the Quiver library.
This tests the accuracy of the Quiver library by ensuring that the
correct PDB lines are returned for a given tag, and that no PDB lines
are lost during manipulation of the Quiver file.
"""

import sys
import os
import math
import uuid
import pandas as pd
import glob
import subprocess  # For running external scripts
import filecmp  # For comparing files more directly
import random  # For selecting random tags
import pathlib  # For Path object manipulation

# pytest 모듈 임포트
import pytest

# 현재 스크립트의 디렉토리 (pytest 실행 위치에 따라 달라질 수 있음)
# basedir fixture에서 프로젝트 루트를 결정하도록 변경

# quiver 모듈 임포트 - 프로젝트 구조에 따라 조정 필요
# 예: src 디렉토리가 루트에 있다면 pytest 실행 시 자동으로 인식될 수 있음
try:
    from quiver import Quiver
except ImportError:
    # 프로젝트 루트를 sys.path에 추가 (pytest 실행 위치에 따라 필요할 수 있음)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)  # test 디렉토리의 부모 (프로젝트 루트)
    # src 디렉토리가 있다면 해당 경로 추가
    src_dir = os.path.join(parent_dir, "src")
    if os.path.isdir(src_dir):
        sys.path.insert(0, src_dir)
    else:  # src가 없다면 부모 디렉토리를 시도
        sys.path.insert(0, parent_dir)
    from quiver import Quiver


# --- Pytest Fixtures ---


@pytest.fixture(scope="session")
def basedir():
    """Return the base directory of the project (one level up from tests)."""
    # __file__은 현재 테스트 파일의 경로
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


@pytest.fixture(
    scope="session"
)  # 세션 범위로 변경하여 여러 테스트에서 재사용 효율 높임
def input_pdb_files(basedir):
    """Return the list of input PDB files for tests."""
    pdb_dir = os.path.join(basedir, "test", "input_for_tests")
    files = glob.glob(os.path.join(pdb_dir, "*.pdb"))
    # 절대 경로를 반환하는지 확인
    return [os.path.abspath(f) for f in files]


@pytest.fixture
def input_qv_file(basedir, tmp_path, input_pdb_files):
    """Creates a test Quiver file from input PDBs in a temporary location."""
    if not input_pdb_files:
        pytest.skip("No input PDB files found for creating test Quiver file.")

    qv_path = tmp_path / "test.qv"
    # input_pdb_files 리스트를 공백으로 구분하고 각 파일을 따옴표로 감싼 문자열로 변환
    pdb_files_list_str = " ".join(f'"{f}"' for f in input_pdb_files)
    script_path = os.path.join(basedir, "src", "quiver", "qvfrompdbs.sh")

    # 스크립트 존재 여부 확인
    if not os.path.exists(script_path):
        pytest.fail(f"Script not found: {script_path}")
    if not os.access(script_path, os.X_OK):
        pytest.fail(f"Script is not executable: {script_path}")

    cmd = f"{script_path} {pdb_files_list_str}"
    # 표준 출력을 파일로 리디렉션
    try:
        with open(qv_path, "w") as f_out:
            # shell=True는 보안 위험이 있을 수 있으나, 여기서는 쉘 스크립트 실행 및 파일 목록 전달을 위해 사용
            # check=True는 명령 실패 시 예외 발생
            # stderr=subprocess.PIPE 추가하여 오류 메시지 캡처
            subprocess.run(
                cmd,
                shell=True,
                check=True,
                stdout=f_out,
                stderr=subprocess.PIPE,
                cwd=tmp_path,
                text=True,
                encoding="utf-8",
            )
    except subprocess.CalledProcessError as e:
        # 실패 시 stderr 출력
        print(f"Error running qvfrompdbs.sh: {e}")
        print(f"Stderr:\n{e.stderr}")
        pytest.fail(f"qvfrompdbs.sh failed: {e}")
    except FileNotFoundError as e:
        pytest.fail(
            f"Failed to run command. Is the script path correct and executable? {e}"
        )

    # 생성된 파일이 비어있지 않은지 간단히 확인
    assert qv_path.exists() and qv_path.stat().st_size > 0, (
        f"Created Quiver file is empty or does not exist: {qv_path}"
    )
    return qv_path


@pytest.fixture(scope="session")  # 세션 범위로 변경
def scored_qv_file(basedir):
    """Returns the path to the pre-scored input Quiver file."""
    file_path = os.path.join(basedir, "test", "input_for_tests", "designs_scored.qv")
    if not os.path.exists(file_path):
        pytest.skip(f"Scored Quiver file not found: {file_path}")
    return file_path


# --- Test Functions ---


def test_zip_and_extract(basedir, tmp_path, input_pdb_files):
    """
    Test creating a Quiver file and extracting identical PDB files.
    Uses pytest's tmp_path fixture for temporary directory.
    """
    if not input_pdb_files:
        pytest.skip("No input PDB files found for testing zip and extract.")

    print(f"\nRunning test in: {tmp_path}")
    qv_output_path = tmp_path / "test.qv"
    input_dir = os.path.join(basedir, "test", "input_for_tests")

    # 1. Zip PDB files into a Quiver file
    # 각 파일 경로를 따옴표로 감싸서 공백 등 문제 방지
    pdb_files_list_str = " ".join(f'"{f}"' for f in input_pdb_files)
    script_path = os.path.join(basedir, "src", "quiver", "qvfrompdbs.sh")

    # 스크립트 확인
    if not os.path.exists(script_path):
        pytest.fail(f"Script not found: {script_path}")
    if not os.access(script_path, os.X_OK):
        pytest.fail(f"Script is not executable: {script_path}")

    zip_cmd = f"{script_path} {pdb_files_list_str}"
    try:
        with open(qv_output_path, "w") as f_out:
            # shell=True로 실행, cwd는 tmp_path로 설정
            subprocess.run(
                zip_cmd,
                shell=True,
                check=True,
                stdout=f_out,
                stderr=subprocess.PIPE,
                cwd=tmp_path,
                text=True,
                encoding="utf-8",
            )
    except subprocess.CalledProcessError as e:
        print(f"Error running qvfrompdbs.sh: {e}")
        print(f"Command: {e.cmd}")
        print(f"Stderr:\n{e.stderr}")
        pytest.fail(f"qvfrompdbs.sh failed: {e}")
    except FileNotFoundError as e:
        pytest.fail(f"Failed to run command. Is the script path correct? {e}")

    assert qv_output_path.exists(), f"Quiver file was not created: {qv_output_path}"
    assert qv_output_path.stat().st_size > 0, (
        f"Created Quiver file is empty: {qv_output_path}"
    )

    # 2. Extract PDB files from the Quiver file
    extract_script = os.path.join(basedir, "src", "quiver", "qvextract.py")
    if not os.path.exists(extract_script):
        pytest.fail(f"Script not found: {extract_script}")

    extract_cmd = [
        sys.executable,  # 파이썬 인터프리터 사용
        extract_script,
        str(qv_output_path),  # Path 객체를 문자열로 변환
    ]
    try:
        subprocess.run(
            extract_cmd, check=True, cwd=tmp_path, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running qvextract.py: {e}")
        print(f"Command: {e.cmd}")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        pytest.fail(f"qvextract.py failed: {e}")

    # 3. Compare extracted PDB files to original PDB files
    extracted_files = list(tmp_path.glob("*.pdb"))
    assert len(extracted_files) == len(input_pdb_files), (
        f"Number of extracted files ({len(extracted_files)}) doesn't match input "
        f"({len(input_pdb_files)}). Extracted: {[f.name for f in extracted_files]}"
    )

    for extracted_file_path in extracted_files:
        # 원본 파일 이름 찾기 (input_dir에 있다고 가정)
        original_file_path = os.path.join(input_dir, extracted_file_path.name)
        assert os.path.exists(original_file_path), (
            f"Original file not found: {original_file_path}"
        )

        # Use filecmp for robust comparison
        assert filecmp.cmp(
            str(extracted_file_path), original_file_path, shallow=False
        ), (
            f"File {extracted_file_path.name} does not match original {original_file_path}"
        )

    print("Passed zip and extract test")


def test_qvls(basedir, tmp_path, input_pdb_files, input_qv_file):
    """Test that qvls returns the correct list of tags."""
    if not input_pdb_files:
        pytest.skip("No input PDB files for testing qvls.")

    print(f"\nRunning test in: {tmp_path}")
    qvls_output_path = tmp_path / "qvls_output.txt"

    # Run qvls
    qvls_script = os.path.join(basedir, "src", "quiver", "qvls.py")
    if not os.path.exists(qvls_script):
        pytest.fail(f"Script not found: {qvls_script}")

    qvls_cmd = [sys.executable, qvls_script, str(input_qv_file)]
    try:
        with open(qvls_output_path, "w") as f_out:
            subprocess.run(
                qvls_cmd,
                check=True,
                stdout=f_out,
                stderr=subprocess.PIPE,
                cwd=tmp_path,
                text=True,
            )
    except subprocess.CalledProcessError as e:
        print(f"Error running qvls.py: {e}")
        print(f"Stderr:\n{e.stderr}")
        pytest.fail(f"qvls.py failed: {e}")

    # Read the output tags
    with open(qvls_output_path, "r") as f:
        listed_tags = {
            line.strip() for line in f if line.strip()
        }  # Use a set for efficient lookup

    # Get the expected tags from input PDB filenames
    expected_tags = {pathlib.Path(pdb).stem for pdb in input_pdb_files}

    # Check that all expected tags are listed
    assert expected_tags == listed_tags, (
        f"qvls output mismatch. Expected: {expected_tags}, Got: {listed_tags}"
    )

    print("Passed qvls test")


def test_qvslice(basedir, tmp_path, input_pdb_files, input_qv_file):
    """Test slicing a Quiver file and extracting from the slice."""
    if not input_pdb_files:
        pytest.skip("No input PDB files for testing qvslice.")

    print(f"\nRunning test in: {tmp_path}")
    input_dir = os.path.join(basedir, "test", "input_for_tests")
    tags_to_slice_path = tmp_path / "tags.txt"
    sliced_qv_path = tmp_path / "sliced.qv"
    slice_script = os.path.join(basedir, "src", "quiver", "qvslice.py")
    extract_script = os.path.join(basedir, "src", "quiver", "qvextract.py")

    if not os.path.exists(slice_script):
        pytest.fail(f"Script not found: {slice_script}")
    if not os.path.exists(extract_script):
        pytest.fail(f"Script not found: {extract_script}")

    # Get all tags and select 5 random tags
    try:
        q = Quiver(str(input_qv_file), "r")
        all_tags = q.get_tags()
        # q.close() 제거됨
    except Exception as e:
        pytest.fail(f"Failed to read tags from Quiver file {input_qv_file}: {e}")

    assert len(all_tags) > 0, "No tags found in the input Quiver file."
    num_to_select = min(5, len(all_tags))
    selected_tags = random.sample(all_tags, num_to_select)

    # Write selected tags to file
    with open(tags_to_slice_path, "w") as f:
        for tag in selected_tags:
            f.write(f"{tag}\n")

    # Run qvslice using the tag file as input
    slice_cmd = (
        f"cat {tags_to_slice_path} | {sys.executable} {slice_script} {input_qv_file}"
    )
    try:
        with open(sliced_qv_path, "w") as f_out:
            subprocess.run(
                slice_cmd,
                shell=True,
                check=True,
                stdout=f_out,
                stderr=subprocess.PIPE,
                cwd=tmp_path,
                text=True,
            )
    except subprocess.CalledProcessError as e:
        print(f"Error running qvslice.py: {e}")
        print(f"Stderr:\n{e.stderr}")
        pytest.fail(f"qvslice.py failed: {e}")

    assert sliced_qv_path.exists(), "Sliced Quiver file was not created."
    assert sliced_qv_path.stat().st_size > 0, "Sliced Quiver file is empty."

    # Extract PDB files from the sliced Quiver file
    extract_cmd = [sys.executable, extract_script, str(sliced_qv_path)]
    try:
        subprocess.run(
            extract_cmd, check=True, cwd=tmp_path, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error extracting from sliced QV: {e}")
        print(f"Stderr:\n{e.stderr}")
        pytest.fail(f"qvextract.py failed on sliced file: {e}")

    # Verify extracted files
    extracted_files = list(tmp_path.glob("*.pdb"))
    extracted_tags = {file.stem for file in extracted_files}

    assert set(selected_tags) == extracted_tags, (
        f"Tags from sliced extract mismatch. Expected: {set(selected_tags)}, Got: {extracted_tags}"
    )

    # Compare content of extracted files with originals
    for tag in selected_tags:
        extracted_file_path = tmp_path / f"{tag}.pdb"
        original_file_path = os.path.join(input_dir, f"{tag}.pdb")
        assert extracted_file_path.exists(), (
            f"Sliced extracted file missing: {extracted_file_path}"
        )
        assert os.path.exists(original_file_path), (
            f"Original file missing: {original_file_path}"
        )
        assert filecmp.cmp(
            str(extracted_file_path), original_file_path, shallow=False
        ), f"Sliced extracted file {tag}.pdb does not match original."

    print("Passed qvslice test")


def test_qvsplit(basedir, tmp_path, input_pdb_files, input_qv_file):
    """Test splitting a Quiver file into multiple smaller files."""
    if not input_pdb_files:
        pytest.skip("No input PDB files for testing qvsplit.")

    print(f"\nRunning test in: {tmp_path}")
    input_dir = os.path.join(basedir, "test", "input_for_tests")
    split_output_dir = tmp_path / "split"
    split_output_dir.mkdir()
    split_size = 3
    split_script = os.path.join(basedir, "src", "quiver", "qvsplit.py")
    extract_script = os.path.join(basedir, "src", "quiver", "qvextract.py")

    if not os.path.exists(split_script):
        pytest.fail(f"Script not found: {split_script}")
    if not os.path.exists(extract_script):
        pytest.fail(f"Script not found: {extract_script}")

    # Run qvsplit
    split_cmd = [sys.executable, split_script, str(input_qv_file), str(split_size)]
    # qvsplit likely outputs files to the CWD, so run it in the target dir
    try:
        subprocess.run(
            split_cmd, check=True, cwd=split_output_dir, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error running qvsplit.py: {e}")
        print(f"Stderr:\n{e.stderr}")
        pytest.fail(f"qvsplit.py failed: {e}")

    # --- Verification ---
    original_tags = {pathlib.Path(pdb).stem for pdb in input_pdb_files}
    num_pdbs = len(original_tags)

    split_qv_files = list(split_output_dir.glob("split_*.qv"))
    expected_num_quivers = math.ceil(num_pdbs / split_size) if num_pdbs > 0 else 0

    # 1. Check number of created quiver files
    assert len(split_qv_files) == expected_num_quivers, (
        f"Incorrect number of split files. Expected {expected_num_quivers}, Got {len(split_qv_files)}"
    )

    all_extracted_tags_from_splits = set()
    # 2. Check content and number of tags in each split file
    for i, qv_split_file in enumerate(
        sorted(
            split_qv_files, key=lambda p: int(p.stem.split("_")[1])
        )  # Sort numerically
    ):
        try:
            q = Quiver(str(qv_split_file), "r")
            local_tags = q.get_tags()
            # q.close() 제거됨
        except Exception as e:
            pytest.fail(
                f"Failed to read tags from split Quiver file {qv_split_file}: {e}"
            )

        local_num_pdbs = len(local_tags)

        # Check number of PDBs in this split file
        if i < expected_num_quivers - 1:  # All files except possibly the last
            assert local_num_pdbs == split_size, (
                f"Split file {qv_split_file.name} has wrong number of entries. Expected {split_size}, Got {local_num_pdbs}"
            )
        else:  # Last file
            expected_last_size = num_pdbs % split_size
            if expected_last_size == 0 and num_pdbs > 0:
                expected_last_size = split_size  # If perfectly divisible
            assert local_num_pdbs == expected_last_size, (
                f"Last split file {qv_split_file.name} has wrong number of entries. "
                f"Expected {expected_last_size} (Total: {num_pdbs}, Size: {split_size}), Got {local_num_pdbs}"
            )

        # Extract PDBs from this split file to verify content and collect tags
        extract_cmd = [sys.executable, extract_script, str(qv_split_file)]
        # Extract into the same dir (split_output_dir)
        try:
            subprocess.run(
                extract_cmd,
                check=True,
                cwd=split_output_dir,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error extracting from split file {qv_split_file.name}: {e}")
            print(f"Stderr:\n{e.stderr}")
            pytest.fail(f"qvextract.py failed on split file: {e}")

        # Find newly extracted PDBs associated *only* with this split file's tags
        current_split_extracted_files = {
            f for f in split_output_dir.glob("*.pdb") if f.stem in local_tags
        }
        current_split_tags = {f.stem for f in current_split_extracted_files}
        all_extracted_tags_from_splits.update(current_split_tags)

        # Compare extracted files with originals for this split
        for tag in current_split_tags:
            extracted_file = split_output_dir / f"{tag}.pdb"
            original_file = os.path.join(input_dir, f"{tag}.pdb")
            assert extracted_file.exists()
            assert os.path.exists(original_file)
            assert filecmp.cmp(str(extracted_file), original_file, shallow=False), (
                f"Split extracted file {tag}.pdb does not match original."
            )
            # Remove the pdb file after checking to avoid counting it for the next split
            extracted_file.unlink()  # Clean up extracted file

    # 3. Check if all original tags are represented across all splits
    assert original_tags == all_extracted_tags_from_splits, (
        f"Tag mismatch after split. Expected: {original_tags}, Got: {all_extracted_tags_from_splits}"
    )

    print("Passed qvsplit test")


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
        assert currpdblines == pdblines, f"PDB file {currpdb} does not match {pdb}"

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
            assert oldrow[key].values[0] == newrow[key].values[0], (
                f"Score line {idx} does not match between old and new Quiver files"
            )

    # Clean up
    os.chdir(f"{basedir}")
    os.system(f"rm -r {basedir}/test/do_qvrename")


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
    assert not missing, f"Missing PDBs: {missing}"

    # Get list of pdbs in this directory
    pdbs = glob.glob("*.pdb")
    pdb_tags = [os.path.basename(pdb)[:-4] for pdb in pdbs]

    assert set(lines) == set(pdb_tags), (
        f"lines: {lines}\npdb_tags: {pdb_tags}\nqvextractspecific did not return the correct PDB files"
    )

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
        assert currpdblines == pdblines, f"PDB file {currpdb} does not match {pdb}"

    # Clean up
    os.chdir(f"{basedir}")
    os.system(f"rm -r {basedir}/test/do_qvextractspecific")
