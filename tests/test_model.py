import unittest
import json
import os
from src.model.pipeline import Pipeline, NodeData, EdgeData

class TestPipeline(unittest.TestCase):
    def test_serialization(self):
        p = Pipeline()
        node1 = NodeData("1", "filter", "Filter", (100, 100), {"locutoff": "1"})
        node2 = NodeData("2", "ica", "ICA", (300, 100), {"algorithm": "runica"})
        p.add_node(node1)
        p.add_node(node2)
        
        edge = EdgeData("1", "2")
        p.add_edge(edge)
        
        # Test to_dict
        d = p.to_dict()
        self.assertEqual(len(d['nodes']), 2)
        self.assertEqual(len(d['edges']), 1)
        self.assertEqual(d['nodes'][0]['parameters']['locutoff'], "1")
        
        # Test save/load
        p.save("test_pipeline.json")
        try:
            p2 = Pipeline.load("test_pipeline.json")
            self.assertEqual(len(p2.nodes), 2)
            self.assertEqual(len(p2.edges), 1)
            self.assertEqual(p2.nodes[0].params['locutoff'], "1")
            self.assertEqual(p2.edges[0].source, "1")
            self.assertEqual(p2.edges[0].target, "2")
            print("Serialization and Deserialization successful.")
        finally:
            if os.path.exists("test_pipeline.json"):
                os.remove("test_pipeline.json")

if __name__ == '__main__':
    unittest.main()
