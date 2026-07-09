from __future__ import annotations

import zipfile

import pytest

from agent_forge.skills.installer import SkillInstaller
from agent_forge.skills.manifest import SkillManifestError


def test_safe_extract_zip_rejects_path_traversal(tmp_path):
    archive_path = tmp_path / "unsafe.whl"
    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("../escape.txt", "nope")

    with zipfile.ZipFile(archive_path) as zf, pytest.raises(SkillManifestError, match="unsafe"):
        SkillInstaller._safe_extract_zip(zf, tmp_path / "extract")
