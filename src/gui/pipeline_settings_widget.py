from PyQt6.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QCheckBox, QComboBox, QSpinBox, QHBoxLayout, QLineEdit, QPushButton, QFileDialog, QGroupBox, QLabel, QTabWidget, QGridLayout
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
            "pipeline_id": "DAG",
            "bids_dataset_name": "",
            "bids_authors": "",
            "bids_default_task": "",
            "bids_modality": "eeg"
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
        general_grid = QGridLayout(general_group)
        general_grid.setColumnStretch(0, 1) # 1/3 for labels
        general_grid.setColumnStretch(1, 2) # 2/3 for fields
        
        self.report_cb = QCheckBox("Generate Execution Report")
        self.report_cb.setChecked(self.settings.get("generate_report", True))
        self.report_cb.toggled.connect(self._emit_change)
        general_grid.addWidget(self.report_cb, 0, 0, 1, 2)
        
        self.parallel_cb = QCheckBox("Use Parallel Processing (parfor)")
        self.parallel_cb.setChecked(self.settings.get("parallel_processing", False))
        self.parallel_cb.toggled.connect(self._emit_change)
        general_grid.addWidget(self.parallel_cb, 1, 0, 1, 2)
        
        self.error_combo = QComboBox()
        self.error_combo.addItems(["Halt on Error", "Skip File and Continue"])
        if self.settings.get("error_strategy", "halt") == "skip":
            self.error_combo.setCurrentIndex(1)
        self.error_combo.currentIndexChanged.connect(self._emit_change)
        
        general_grid.addWidget(QLabel("Error Strategy:"), 2, 0)
        general_grid.addWidget(self.error_combo, 2, 1)
        
        exec_layout.addWidget(general_group)
        
        # Output Group (Global Save Path & BIDS ID)
        output_group = QGroupBox("Global Output Settings")
        output_v_layout = QVBoxLayout(output_group)
        
        self.use_global_cb = QCheckBox("Use Global Save Path")
        self.use_global_cb.setChecked(self.settings.get("use_global_savepath", False))
        self.use_global_cb.toggled.connect(self._emit_change)
        output_v_layout.addWidget(self.use_global_cb)
        
        # Path Selection Label (Separate row)
        self.save_path_label = QLabel("Save Path:")
        output_v_layout.addWidget(self.save_path_label)
        
        path_widget = QWidget()
        path_h_layout = QHBoxLayout(path_widget)
        path_h_layout.setContentsMargins(0, 0, 0, 0)
        
        self.output_edit = QLineEdit(self.settings.get("global_savepath", ""))
        self.output_edit.setPlaceholderText("Select global directory...")
        self.output_edit.textChanged.connect(self._emit_change)
        
        self.btn_browse = QPushButton("...")
        self.btn_browse.setFixedWidth(30)
        self.btn_browse.clicked.connect(self._browse_output)
        
        path_h_layout.addWidget(self.output_edit)
        path_h_layout.addWidget(self.btn_browse)
        output_v_layout.addWidget(path_widget)
        
        # Grid for Pipeline ID
        output_grid = QGridLayout()
        output_grid.setColumnStretch(0, 1)
        output_grid.setColumnStretch(1, 2)
        
        self.pipeline_id_edit = QLineEdit(self.settings.get("pipeline_id", "DAG"))
        self.pipeline_id_edit.setPlaceholderText("e.g. DAG, Preproc_V1, etc.")
        self.pipeline_id_edit.textChanged.connect(self._emit_change)
        
        output_grid.addWidget(QLabel("Pipeline Identifier:"), 0, 0)
        output_grid.addWidget(self.pipeline_id_edit, 0, 1)
        
        output_v_layout.addLayout(output_grid)
        exec_layout.addWidget(output_group)
        
        # Connect checkbox to enable/disable states
        self.use_global_cb.toggled.connect(self.save_path_label.setEnabled)
        self.use_global_cb.toggled.connect(self.output_edit.setEnabled)
        self.use_global_cb.toggled.connect(self.btn_browse.setEnabled)
        self.use_global_cb.toggled.connect(self.pipeline_id_edit.setEnabled)
        
        # Initial state
        self.save_path_label.setEnabled(self.use_global_cb.isChecked())
        self.output_edit.setEnabled(self.use_global_cb.isChecked())
        self.btn_browse.setEnabled(self.use_global_cb.isChecked())
        self.pipeline_id_edit.setEnabled(self.use_global_cb.isChecked())
        
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
        
        # --- TAB 2: Metadata Settings ---
        metadata_tab = QWidget()
        meta_layout = QVBoxLayout(metadata_tab)
        meta_layout.setContentsMargins(8, 8, 8, 8)
        
        # BIDS Description Group
        bids_desc_group = QGroupBox("BIDS Dataset Description")
        bids_desc_grid = QGridLayout(bids_desc_group)
        bids_desc_grid.setColumnStretch(0, 1)
        bids_desc_grid.setColumnStretch(1, 2)
        
        self.dataset_name_edit = QLineEdit(self.settings.get("bids_dataset_name", ""))
        self.dataset_name_edit.setPlaceholderText("e.g. My EEG Study")
        self.dataset_name_edit.textChanged.connect(self._emit_change)
        bids_desc_grid.addWidget(QLabel("Dataset Name:"), 0, 0)
        bids_desc_grid.addWidget(self.dataset_name_edit, 0, 1)
        
        self.authors_edit = QLineEdit(self.settings.get("bids_authors", ""))
        self.authors_edit.setPlaceholderText("Author A, Author B")
        self.authors_edit.textChanged.connect(self._emit_change)
        bids_desc_grid.addWidget(QLabel("Authors:"), 1, 0)
        bids_desc_grid.addWidget(self.authors_edit, 1, 1)
        
        meta_layout.addWidget(bids_desc_group)
        
        # BIDS Defaults Group
        bids_defaults_group = QGroupBox("BIDS Defaults & Modality")
        bids_defaults_grid = QGridLayout(bids_defaults_group)
        bids_defaults_grid.setColumnStretch(0, 1)
        bids_defaults_grid.setColumnStretch(1, 2)
        
        self.default_task_edit = QLineEdit(self.settings.get("bids_default_task", ""))
        self.default_task_edit.setPlaceholderText("e.g. task-rest")
        self.default_task_edit.textChanged.connect(self._emit_change)
        bids_defaults_grid.addWidget(QLabel("Default Task:"), 0, 0)
        bids_defaults_grid.addWidget(self.default_task_edit, 0, 1)
        
        self.modality_combo = QComboBox()
        self.modality_combo.addItems(["eeg", "ieeg", "meg"])
        self.modality_combo.setCurrentText(self.settings.get("bids_modality", "eeg"))
        self.modality_combo.currentTextChanged.connect(self._emit_change)
        bids_defaults_grid.addWidget(QLabel("Modality Identifier:"), 1, 0)
        bids_defaults_grid.addWidget(self.modality_combo, 1, 1)
        
        meta_layout.addWidget(bids_defaults_group)
        
        meta_layout.addStretch()
        
        self.tabs.addTab(metadata_tab, "Metadata")
        
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
            "pipeline_id": self.pipeline_id_edit.text(),
            "bids_dataset_name": self.dataset_name_edit.text(),
            "bids_authors": self.authors_edit.text(),
            "bids_default_task": self.default_task_edit.text(),
            "bids_modality": self.modality_combo.currentText()
        }
        self.settings_changed.emit(self.settings)

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Global Save Path", self.output_edit.text())
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
        
        # Metadata Tab
        self.dataset_name_edit.blockSignals(True)
        self.dataset_name_edit.setText(settings.get("bids_dataset_name", ""))
        self.dataset_name_edit.blockSignals(False)
        
        self.authors_edit.blockSignals(True)
        self.authors_edit.setText(settings.get("bids_authors", ""))
        self.authors_edit.blockSignals(False)
        
        self.default_task_edit.blockSignals(True)
        self.default_task_edit.setText(settings.get("bids_default_task", ""))
        self.default_task_edit.blockSignals(False)
        
        self.modality_combo.blockSignals(True)
        self.modality_combo.setCurrentText(settings.get("bids_modality", "eeg"))
        self.modality_combo.blockSignals(False)
        
        # Sync enablement
        self.save_path_label.setEnabled(self.use_global_cb.isChecked())
        self.output_edit.setEnabled(self.use_global_cb.isChecked())
        self.btn_browse.setEnabled(self.use_global_cb.isChecked())
        self.pipeline_id_edit.setEnabled(self.use_global_cb.isChecked())
        
        self.report_cb.blockSignals(False)
        self.parallel_cb.blockSignals(False)
        self.error_combo.blockSignals(False)
        self.test_cb.blockSignals(False)
        self.sample_spin.blockSignals(False)
