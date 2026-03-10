import pytest
import os
import sys

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from quiver.quiver import Quiver

@pytest.fixture
def temp_qv_file(tmp_path):
    qv_path = tmp_path / "test.qv"
    with open(qv_path, "w") as f:
        f.write("QV_TAG tag1\n")
        f.write("ATOM      1  N   ALA A   1      11.104  13.203  10.000  1.00 20.00           N\n")
        f.write("QV_TAG tag2\n")
        f.write("ATOM      1  N   ALA A   1      12.104  14.203  11.000  1.00 21.00           N\n")
    return qv_path

def test_get_pdblines_invalid_mode(temp_qv_file):
    """Verify RuntimeError is raised when calling get_pdblines in write mode."""
    # Open in 'w' mode (although it's actually 'a' inside add_pdb, the check is on self.mode)
    q = Quiver(str(temp_qv_file), "w")
    with pytest.raises(RuntimeError, match="Quiver file must be opened in read mode to allow for reading."):
        q.get_pdblines("tag1")

def test_get_pdblines_nonexistent_tag(temp_qv_file):
    """Verify KeyError is raised when requesting a non-existent tag."""
    q = Quiver(str(temp_qv_file), "r")
    with pytest.raises(KeyError, match="Requested tag: non_existent_tag does not exist"):
        q.get_pdblines("non_existent_tag")

def test_get_pdblines_happy_path(temp_qv_file):
    """Verify get_pdblines works correctly for an existing tag (sanity check)."""
    q = Quiver(str(temp_qv_file), "r")
    lines = q.get_pdblines("tag1")
    assert len(lines) == 1
    assert "tag1" not in lines[0]
    assert "ALA" in lines[0]
