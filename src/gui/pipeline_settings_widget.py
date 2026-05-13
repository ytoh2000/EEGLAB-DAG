from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QCheckBox, QComboBox, QSpinBox, QHBoxLayout, QLineEdit, QPushButton, QFileDialog, QGroupBox, QLabel
from PyQt6.QtCore import pyqtSignal

class PipelineSettingsWidget(QWidget):
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, initial_settings=None, parent=None):
        super().__init__(parent)
        
        self.settings = initial_settings or {
            "generate_report": True,
            "error_strategy": "halt",
            "test_mode": False,
            "test_sample_size": 1,
            "parallel_processing": False
        }
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # General Group
        general_group = QGroupBox("General Options")
        general_layout = QFormLayout(general_group)
        
        self.report_cb = QCheckBox("Generate Execution Report")
        self.report_cb.setChecked(self.settings.get("generate_report", True))
        self.report_cb.toggled.connect(self._emit_change)
        general_layout.addRow(self.report_cb)
        
        self.parallel_cb = QCheckBox("Use Parallel Processing (parfor)")
        self.parallel_cb.setChecked(self.settings.get("parallel_processing", False))
        self.parallel_cb.toggled.connect(self._emit_change)
        general_layout.addRow(self.parallel_cb)
        
        self.error_combo = QComboBox()
        self.error_combo.addItems(["Halt on Error", "Skip File and Continue"])
        if self.settings.get("error_strategy", "halt") == "skip":
            self.error_combo.setCurrentIndex(1)
        self.error_combo.currentIndexChanged.connect(self._emit_change)
        general_layout.addRow("Error Strategy:", self.error_combo)
        
        layout.addWidget(general_group)
        
        # Testing Group
        test_group = QGroupBox("Testing & Batch")
        test_layout = QVBoxLayout(test_group)
        
        self.test_cb = QCheckBox("Enable Testing Mode")
        self.test_cb.setChecked(self.settings.get("test_mode", False))
        
        test_size_layout = QHBoxLayout()
        test_size_layout.addWidget(QLabel("Sample Size:"))
        self.sample_spin = QSpinBox()
        self.sample_spin.setMinimum(1)
        self.sample_spin.setMaximum(100)
        self.sample_spin.setValue(self.settings.get("test_sample_size", 1))
        self.sample_spin.setEnabled(self.test_cb.isChecked())
        test_size_layout.addWidget(self.sample_spin)
        test_size_layout.addStretch()
        
        self.test_cb.toggled.connect(self.sample_spin.setEnabled)
        self.test_cb.toggled.connect(self._emit_change)
        self.sample_spin.valueChanged.connect(self._emit_change)
        
        test_layout.addWidget(self.test_cb)
        test_layout.addLayout(test_size_layout)
        
        layout.addWidget(test_group)
        
        layout.addStretch()
            
    def _emit_change(self):
        self.settings = {
            "generate_report": self.report_cb.isChecked(),
            "error_strategy": "skip" if self.error_combo.currentIndex() == 1 else "halt",
            "test_mode": self.test_cb.isChecked(),
            "test_sample_size": self.sample_spin.value(),
            "parallel_processing": self.parallel_cb.isChecked()
        }
        self.settings_changed.emit(self.settings)

    def set_settings(self, settings):
        """Update UI without emitting signals (e.g. when loading a file)."""
        self.settings = settings.copy()
        
        # Disconnect momentarily to prevent recursive loops
        self.report_cb.blockSignals(True)
        self.parallel_cb.blockSignals(True)
        self.error_combo.blockSignals(True)
        self.test_cb.blockSignals(True)
        self.sample_spin.blockSignals(True)
        
        self.report_cb.setChecked(settings.get("generate_report", True))
        self.parallel_cb.setChecked(settings.get("parallel_processing", False))
        
        if settings.get("error_strategy", "halt") == "skip":
            self.error_combo.setCurrentIndex(1)
        else:
            self.error_combo.setCurrentIndex(0)
            
        self.test_cb.setChecked(settings.get("test_mode", False))
        self.sample_spin.setValue(settings.get("test_sample_size", 1))
        self.sample_spin.setEnabled(self.test_cb.isChecked())
        
        self.report_cb.blockSignals(False)
        self.parallel_cb.blockSignals(False)
        self.error_combo.blockSignals(False)
        self.test_cb.blockSignals(False)
        self.sample_spin.blockSignals(False)
