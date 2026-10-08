import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "scripts"))
from validate_repo import validate_repo  # noqa: E402


VALID_SKILL = """---
name: sample-skill
description: A focused sample skill used for validator tests.
---

# Sample

Read [guide]""" + "(guide.md).\n"


class ValidateRepoTests(unittest.TestCase):
    def make_repo(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "sample-skill"
        root.mkdir()
        (root / "SKILL.md").write_text(VALID_SKILL, encoding="utf-8")
        (root / "guide.md").write_text("# Guide\n", encoding="utf-8")
        return temp, root

    def test_clean_skill_passes(self):
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        errors, warnings = validate_repo(root)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_broken_local_link_fails(self):
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        (root / "guide.md").unlink()
        errors, _ = validate_repo(root)
        self.assertTrue(any("broken local link" in item for item in errors))

    def test_invalid_frontmatter_name_fails(self):
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        (root / "SKILL.md").write_text(
            VALID_SKILL.replace("name: sample-skill", "name: Invalid_Name"),
            encoding="utf-8",
        )
        errors, _ = validate_repo(root)
        self.assertTrue(any("name must be" in item for item in errors))

    def test_repository_root_may_have_a_different_name(self):
        temp, root = self.make_repo()
        self.addCleanup(temp.cleanup)
        source_root = root.with_name("public-repository-name")
        root.rename(source_root)
        errors, warnings = validate_repo(source_root, require_parent_name=False)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
