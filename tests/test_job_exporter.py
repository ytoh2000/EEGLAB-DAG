"""Tests for the JobExporter class — validates export logic, topological sort, and error handling."""
import unittest
import json
import os
from src.model.pipeline import Pipeline, NodeData, EdgeData
from src.model.job_exporter import JobExporter


class TestJobExporter(unittest.TestCase):
    def _make_valid_pipeline(self):
        """Helper: creates a minimal valid pipeline (Files → Filter → Save)."""
        p = Pipeline()
        p.add_node(NodeData("1", "input", "Get File(s)", function="get_files",
                            params={"file_paths": ["/data/test.set"]}))
        p.add_node(NodeData("2", "process", "Filter", function="pop_eegfiltnew",
                            params={"locutoff": 1, "hicutoff": 30}))
        p.add_node(NodeData("3", "output", "Save", function="pop_saveset"))
        p.add_edge(EdgeData("1", "2"))
        p.add_edge(EdgeData("2", "3"))
        return p

    # --- Validation ---
    def test_validate_pass(self):
        p = self._make_valid_pipeline()
        exporter = JobExporter(p)
        valid, msg = exporter.validate()
        self.assertTrue(valid, msg)

    def test_validate_cycle(self):
        p = self._make_valid_pipeline()
        p.add_edge(EdgeData("3", "2"))  # cycle
        exporter = JobExporter(p)
        valid, msg = exporter.validate()
        self.assertFalse(valid)
        self.assertIn("cycle", msg.lower())

    def test_validate_no_source(self):
        """Pipeline with no file_paths param on source should fail."""
        p = Pipeline()
        p.add_node(NodeData("1", "process", "Filter", function="pop_eegfiltnew"))
        p.add_node(NodeData("2", "output", "Save", function="pop_saveset"))
        p.add_edge(EdgeData("1", "2"))
        exporter = JobExporter(p)
        valid, msg = exporter.validate()
        self.assertFalse(valid)

    def test_validate_no_files(self):
        """get_files node with empty file_paths should fail."""
        p = Pipeline()
        p.add_node(NodeData("1", "input", "Get File(s)", function="get_files",
                            params={"file_paths": []}))
        p.add_node(NodeData("2", "output", "Save", function="pop_saveset"))
        p.add_edge(EdgeData("1", "2"))
        exporter = JobExporter(p)
        valid, msg = exporter.validate()
        self.assertFalse(valid)
        self.assertIn("no files", msg.lower())

    # --- Export ---
    def test_export_topological_order(self):
        """Steps in the exported JSON should follow topological order."""
        p = self._make_valid_pipeline()
        exporter = JobExporter(p)
        out_path = "_test_export.json"
        try:
            job = exporter.export(out_path)
            self.assertEqual(len(job["files"]), 1)
            self.assertEqual(job["files"][0], "/data/test.set")
            # get_files is excluded from steps, so we expect 2 processing steps
            self.assertEqual(len(job["steps"]), 2)
            self.assertEqual(job["steps"][0]["function"], "pop_eegfiltnew")
            self.assertEqual(job["steps"][1]["function"], "pop_saveset")
            
            # Verify the file was written correctly
            with open(out_path) as f:
                loaded = json.load(f)
            self.assertEqual(loaded, job)
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    def test_export_uses_node_function(self):
        """Export should use node.function directly, not label-based lookup."""
        p = Pipeline()
        # Use a label that doesn't match any library name to prove we use node.function
        p.add_node(NodeData("1", "input", "My Custom Input", function="get_files",
                            params={"file_paths": ["/data/x.set"]}))
        p.add_node(NodeData("2", "process", "Custom Label That Matches Nothing",
                            function="pop_eegfiltnew", params={"locutoff": 0.5}))
        p.add_node(NodeData("3", "output", "Custom Save", function="pop_saveset"))
        p.add_edge(EdgeData("1", "2"))
        p.add_edge(EdgeData("2", "3"))
        exporter = JobExporter(p)
        out_path = "_test_export_func.json"
        try:
            job = exporter.export(out_path)
            # The function names should come from NodeData.function, not label
            self.assertEqual(job["steps"][0]["function"], "pop_eegfiltnew")
            self.assertEqual(job["steps"][1]["function"], "pop_saveset")
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)


if __name__ == '__main__':
    unittest.main()
