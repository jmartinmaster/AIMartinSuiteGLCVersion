import os
import tempfile
import unittest
from app.models.internal_code_editor_model import InternalCodeEditorModel

class TestInternalCodeEditorModel(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.bundled_path = os.path.join(self.temp_dir.name, "bundled")
        self.external_path = os.path.join(self.temp_dir.name, "external")
        os.makedirs(self.bundled_path)
        os.makedirs(self.external_path)
        self.model = InternalCodeEditorModel(self.bundled_path, self.external_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_search_symbol_matches_executes_successfully(self):
        # Create a dummy python file in the bundled path
        file_path = os.path.join(self.bundled_path, "dummy.py")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("def my_test_function():\n    pass\n")

        # Manually populate file_entries to avoid scanning everything
        self.model.file_entries = [{
            "key": "workspace:dummy.py",
            "label": "Workspace | dummy.py",
            "relative_path": "dummy.py",
            "path": file_path,
            "source_name": "workspace",
        }]

        # Call search_symbol_matches - this should not crash
        results = self.model.search_symbol_matches("my_test_function")
        self.assertIn("results", results)
        self.assertEqual(len(results["results"]), 1)
        self.assertEqual(results["results"][0]["summary"], "my_test_function (function)")

    def test_build_definition_index(self):
        source = "class MyClass:\n    def my_method(self):\n        pass\n"
        definitions, semantic, err = self.model.build_definition_index(source)
        self.assertIsNone(err)
        self.assertEqual(len(definitions), 2)
        self.assertEqual(definitions[0]["name"], "MyClass")
        self.assertEqual(definitions[0]["kind"], "class")
        self.assertEqual(definitions[1]["name"], "my_method")
        self.assertEqual(definitions[1]["kind"], "method")
        self.assertEqual(len(semantic), 1)  # self parameter

if __name__ == "__main__":
    unittest.main()
