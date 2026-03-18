from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from offagent.app.services import discover_documents


class DiscoveryTests(unittest.TestCase):
    def test_discovers_only_supported_office_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "proposal.docx").write_text("word")
            (root / "deck.pptx").write_text("slides")
            (root / "budget.xlsx").write_text("sheet")
            (root / "notes.txt").write_text("ignore")
            nested = root / "nested"
            nested.mkdir()
            (nested / "appendix.docx").write_text("nested")

            documents = discover_documents([root])

            self.assertEqual(
                [document.path.name for document in documents],
                ["budget.xlsx", "deck.pptx", "appendix.docx", "proposal.docx"],
            )
            self.assertTrue(all(document.modified_time > 0 for document in documents))
            self.assertEqual({document.file_type for document in documents}, {"docx", "pptx", "xlsx"})


if __name__ == "__main__":
    unittest.main()
