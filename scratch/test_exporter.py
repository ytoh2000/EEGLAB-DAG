
from src.model.job_exporter import JobExporter

# Create a dummy pipeline
class DummyPipeline:
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.settings = {}

exporter = JobExporter(DummyPipeline())

# Test 1: Channel labels
val1 = "E1 E56 E129"
result1 = exporter._format_value("rmchannel", val1, {"type": "string"})
print(f"Input: {val1}")
print(f"Output (JSON style): {result1}")

# Test 2: Numeric channels
val2 = "1 4 5 6"
result2 = exporter._format_value("rmchannel", val2, {"type": "string"})
print(f"Input: {val2}")
print(f"Output (JSON style): {result2}")

# Test 3: Mixed commas and spaces
val3 = "E1, E2 E3"
result3 = exporter._format_value("rmchannel", val3, {"type": "string"})
print(f"Input: {val3}")
print(f"Output (JSON style): {result3}")
