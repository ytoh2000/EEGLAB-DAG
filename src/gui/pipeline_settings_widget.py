from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QCheckBox, QComboBox, QSpinBox, QHBoxLayout, QLineEdit, QPushButton, QFileDialog, QGroupBox, QLabel, QTabWidget
from PyQt6.QtCore import pyqtSignal, Qt

class PipelineSettingsWidget(QWidget):
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, initial_settings=None, parent=None):
        super().__init__(parent)
        
        self.settings = initial_settings or {
            "generate_report": True,
            "error_strategy": "halt",
            "test_mode": False,
            "test_sample_size": 1,
            "parallel_processing": False,
            "use_global_savepath": False,
            "global_savepath": "",
            "pipeline_id": "DAG"
        }
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        
        # --- TAB 1: Execution Settings ---
        execution_tab = QWidget()
        exec_layout = QVBoxLayout(execution_tab)
        exec_layout.setContentsMargins(8, 8, 8, 8)
        
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
        
        exec_layout.addWidget(general_group)
        
        # Output Group (Global Savepath & BIDS ID)
        output_group = QGroupBox("Global Output Settings")
        output_v_layout = QVBoxLayout(output_group)
        
        self.use_global_cb = QCheckBox("Use Global Savepath for Results")
        self.use_global_cb.setChecked(self.settings.get("use_global_savepath", False))
        self.use_global_cb.toggled.connect(self._emit_change)
        output_v_layout.addWidget(self.use_global_cb)
        
        # Path Selection
        path_layout = QHBoxLayout()
        self.output_edit = QLineEdit(self.settings.get("global_savepath", ""))
        self.output_edit.setPlaceholderText("Select global directory for saving...")
        self.output_edit.textChanged.connect(self._emit_change)
        
        self.btn_browse = QPushButton("...")
        self.btn_browse.setFixedWidth(30)
        self.btn_browse.clicked.connect(self._browse_output)
        
        path_layout.addWidget(self.output_edit)
        path_layout.addWidget(self.btn_browse)
        output_v_layout.addLayout(path_layout)
        
        # BIDS ID Options
        self.bids_id_group = QGroupBox("BIDS Identifier")
        bids_id_layout = QFormLayout(self.bids_id_group)
        bids_id_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.pipeline_id_edit = QLineEdit(self.settings.get("pipeline_id", "DAG"))
        self.pipeline_id_edit.setPlaceholderText("e.g. DAG, Preproc_V1, etc.")
        self.pipeline_id_edit.setFixedWidth(200)
        self.pipeline_id_edit.textChanged.connect(self._emit_change)
        bids_id_layout.addRow("Pipeline Identifier:", self.pipeline_id_edit)
        
        output_v_layout.addWidget(self.bids_id_group)
        exec_layout.addWidget(output_group)
        
        # Connect checkbox to enable/disable states
        self.use_global_cb.toggled.connect(self.output_edit.setEnabled)
        self.use_global_cb.toggled.connect(self.btn_browse.setEnabled)
        self.use_global_cb.toggled.connect(self.bids_id_group.setEnabled)
        
        # Initial state
        self.output_edit.setEnabled(self.use_global_cb.isChecked())
        self.btn_browse.setEnabled(self.use_global_cb.isChecked())
        self.bids_id_group.setEnabled(self.use_global_cb.isChecked())
        
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
        
        exec_layout.addWidget(test_group)
        exec_layout.addStretch()
        
        self.tabs.addTab(execution_tab, "Execution")
        
        main_layout.addWidget(self.tabs)
            
    def _emit_change(self):
        self.settings = {
            "generate_report": self.report_cb.isChecked(),
            "error_strategy": "skip" if self.error_combo.currentIndex() == 1 else "halt",
            "test_mode": self.test_cb.isChecked(),
            "test_sample_size": self.sample_spin.value(),
            "parallel_processing": self.parallel_cb.isChecked(),
            "use_global_savepath": self.use_global_cb.isChecked(),
            "global_savepath": self.output_edit.text(),
            "pipeline_id": self.pipeline_id_edit.text()
        }
        self.settings_changed.emit(self.settings)

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Global Savepath Folder", self.output_edit.text())
        if folder:
            self.output_edit.setText(folder)

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
        
        self.use_global_cb.blockSignals(True)
        self.use_global_cb.setChecked(settings.get("use_global_savepath", False))
        self.use_global_cb.blockSignals(False)
        
        self.output_edit.blockSignals(True)
        self.output_edit.setText(settings.get("global_savepath", ""))
        self.output_edit.blockSignals(False)
        
        self.pipeline_id_edit.blockSignals(True)
        self.pipeline_id_edit.setText(settings.get("pipeline_id", "DAG"))
        self.pipeline_id_edit.blockSignals(False)
        
        # Sync enablement
        self.output_edit.setEnabled(self.use_global_cb.isChecked())
        self.btn_browse.setEnabled(self.use_global_cb.isChecked())
        self.bids_group.setEnabled(self.use_global_cb.isChecked())
        
        self.report_cb.blockSignals(False)
        self.parallel_cb.blockSignals(False)
        self.error_combo.blockSignals(False)
        self.test_cb.blockSignals(False)
        self.sample_spin.blockSignals(False)
