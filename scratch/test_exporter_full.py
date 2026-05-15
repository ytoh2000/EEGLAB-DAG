
from src.model.job_exporter import JobExporter

class DummyNode:
    def __init__(self, function, params, label="Test", type="process"):
        self.id = "test-id"
        self.function = function
        self.params = params
        self.label = label
        self.type = type
        self.save_output = False
        self.transfer_inputs = {}

class DummyPipeline:
    def __init__(self, node):
        self.nodes = [node]
        self.edges = []
        self.settings = {}

node = DummyNode("pop_select", {"rmchannel": "E17 E125 E127 E128 ECG"})
pipeline = DummyPipeline(node)
exporter = JobExporter(pipeline)

# Test the value formatter directly
val = "E17 E125 E127 E128 ECG"
res = exporter._format_value("rmchannel", val, {"type": "string"})
print(f"Direct Format Result: {res}")

# Test the full build_job_dict
job = exporter.build_job_dict()
print("Job Step Arguments:")
print(job['steps'][0]['arguments'])
