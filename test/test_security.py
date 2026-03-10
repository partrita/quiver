import os
import sys
import subprocess
import pytest
from quiver import Quiver

def test_extract_path_traversal_protection(tmp_path):
    """Test that qvextract.py is protected against path traversal."""
    qv_file = tmp_path / "test.qv"
    poison_tag = "../../poison_extract"

    with open(qv_file, "w") as f:
        f.write(f"QV_TAG {poison_tag}\n")
        f.write("ATOM      1  N   ASP A   1      -1.429  13.256 -13.011  1.00 46.54           N\n")

    # We'll run it from a subdirectory to see if it tries to go up
    extract_dir = tmp_path / "extract_dir"
    extract_dir.mkdir()

    script_path = os.path.abspath("src/quiver/qvextract.py")

    subprocess.run([sys.executable, script_path, str(qv_file)], cwd=extract_dir, check=True)

    # Should NOT exist in the parent of extract_dir (which is tmp_path)
    assert not (tmp_path / "poison_extract.pdb").exists()

    # SHOULD exist in extract_dir as poison_extract.pdb (basename of the tag)
    assert (extract_dir / "poison_extract.pdb").exists()

def test_extractspecific_path_traversal_protection(tmp_path):
    """Test that qvextractspecific.py is protected against path traversal."""
    qv_file = tmp_path / "test.qv"
    poison_tag = "../../poison_specific"

    with open(qv_file, "w") as f:
        f.write(f"QV_TAG {poison_tag}\n")
        f.write("ATOM      1  N   ASP A   1      -1.429  13.256 -13.011  1.00 46.54           N\n")

    extract_dir = tmp_path / "extract_dir"
    extract_dir.mkdir()

    script_path = os.path.abspath("src/quiver/qvextractspecific.py")

    # Test passing tag as argument
    subprocess.run([sys.executable, script_path, str(qv_file), poison_tag, "--output-dir", str(extract_dir)], check=True)

    # Should NOT exist in the grandparent of extract_dir
    # Based on the tag "../../poison_specific", it would try to go up twice from extract_dir if not sanitized.
    # tmp_path / .. / .. / poison_specific.pdb
    assert not (tmp_path.parent.parent / "poison_specific.pdb").exists()

    # SHOULD exist in extract_dir as poison_specific.pdb
    assert (extract_dir / "poison_specific.pdb").exists()
