import unittest
import json
import os
from src.model.pipeline import Pipeline, NodeData, EdgeData

class TestPipeline(unittest.TestCase):
    def test_serialization(self):
        p = Pipeline()
        node1 = NodeData("1", "process", "Filter", (100, 100), {"locutoff": "1"}, function="pop_eegfiltnew")
        node2 = NodeData("2", "process", "ICA", (300, 100), {"algorithm": "runica"}, function="pop_runica")
        p.add_node(node1)
        p.add_node(node2)
        
        edge = EdgeData("1", "2")
        p.add_edge(edge)
        
        # Test to_dict includes function
        d = p.to_dict()
        self.assertEqual(len(d['nodes']), 2)
        self.assertEqual(len(d['edges']), 1)
        self.assertEqual(d['nodes'][0]['parameters']['locutoff'], "1")
        self.assertEqual(d['nodes'][0]['function'], "pop_eegfiltnew")
        self.assertEqual(d['nodes'][1]['function'], "pop_runica")
        
        # Test save/load
        p.save("test_pipeline.json")
        try:
            p2 = Pipeline.load("test_pipeline.json")
            self.assertEqual(len(p2.nodes), 2)
            self.assertEqual(len(p2.edges), 1)
            self.assertEqual(p2.nodes[0].params['locutoff'], "1")
            self.assertEqual(p2.nodes[0].function, "pop_eegfiltnew")
            self.assertEqual(p2.nodes[1].function, "pop_runica")
            self.assertEqual(p2.edges[0].source, "1")
            self.assertEqual(p2.edges[0].target, "2")
            print("Serialization and Deserialization successful.")
        finally:
            if os.path.exists("test_pipeline.json"):
                os.remove("test_pipeline.json")

    def test_backward_compatibility(self):
        """Pipeline files saved before the 'function' field was added should load with function=''."""
        old_format = {
            "nodes": [
                {"id": "1", "type": "process", "label": "Filter", "position": [100, 100], "parameters": {"locutoff": "1"}}
            ],
            "edges": []
        }
        p = Pipeline.from_dict(old_format)
        self.assertEqual(p.nodes[0].function, "")
        self.assertEqual(p.nodes[0].label, "Filter")

    def test_validate_empty(self):
        p = Pipeline()
        valid, msg = p.validate()
        self.assertFalse(valid)
        self.assertIn("empty", msg.lower())

    def test_validate_cycle(self):
        p = Pipeline()
        p.add_node(NodeData("1", "input", "Files", function="get_files", params={"file_paths": ["x.set"]}))
        p.add_node(NodeData("2", "process", "Filter", function="pop_eegfiltnew"))
        p.add_node(NodeData("3", "output", "Save", function="pop_saveset"))
        p.add_edge(EdgeData("1", "2"))
        p.add_edge(EdgeData("2", "3"))
        p.add_edge(EdgeData("3", "2"))  # cycle
        valid, msg = p.validate()
        self.assertFalse(valid)
        self.assertIn("cycle", msg.lower())

    def test_validate_disconnected(self):
        p = Pipeline()
        p.add_node(NodeData("1", "input", "Files", function="get_files", params={"file_paths": ["x.set"]}))
        p.add_node(NodeData("2", "process", "Filter", function="pop_eegfiltnew"))
        p.add_node(NodeData("3", "output", "Save", function="pop_saveset"))
        p.add_node(NodeData("4", "process", "ICA", function="pop_runica"))  # disconnected
        p.add_edge(EdgeData("1", "2"))
        p.add_edge(EdgeData("2", "3"))
        valid, msg = p.validate()
        self.assertFalse(valid)
        self.assertIn("disconnected", msg.lower())

    def test_validate_no_input(self):
        p = Pipeline()
        p.add_node(NodeData("1", "process", "Filter", function="pop_eegfiltnew"))
        p.add_node(NodeData("2", "output", "Save", function="pop_saveset"))
        p.add_edge(EdgeData("1", "2"))
        valid, msg = p.validate()
        self.assertFalse(valid)
        self.assertIn("input", msg.lower())

    def test_validate_valid(self):
        p = Pipeline()
        p.add_node(NodeData("1", "input", "Files", function="get_files", params={"file_paths": ["x.set"]}))
        p.add_node(NodeData("2", "process", "Filter", function="pop_eegfiltnew"))
        p.add_node(NodeData("3", "output", "Save", function="pop_saveset"))
        p.add_edge(EdgeData("1", "2"))
        p.add_edge(EdgeData("2", "3"))
        valid, msg = p.validate()
        self.assertTrue(valid)

if __name__ == '__main__':
    unittest.main()
