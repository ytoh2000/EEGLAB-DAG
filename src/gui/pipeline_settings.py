from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QCheckBox, QFileDialog, QDialogButtonBox)

class PipelineSettingsDialog(QDialog):
    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Pipeline Settings")
        self.resize(400, 200)
        
        self.settings = current_settings or {
            "generate_report": True,
            "stop_on_error": True,
            "output_folder": ""
        }
        
        layout = QVBoxLayout(self)
        
        # Report generation
        self.report_cb = QCheckBox("Generate Pipeline Report")
        self.report_cb.setChecked(self.settings.get("generate_report", True))
        layout.addWidget(self.report_cb)
        
        # Stop on error
        self.stop_error_cb = QCheckBox("Stop Pipeline on Error")
        self.stop_error_cb.setChecked(self.settings.get("stop_on_error", True))
        layout.addWidget(self.stop_error_cb)
        
        # Output folder
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel("Output Folder:"))
        self.out_edit = QLineEdit(self.settings.get("output_folder", ""))
        out_layout.addWidget(self.out_edit)
        
        btn_browse = QPushButton("...")
        btn_browse.clicked.connect(self.browse_output)
        out_layout.addWidget(btn_browse)
        layout.addLayout(out_layout)
        
        layout.addStretch()
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.out_edit.text())
        if folder:
            self.out_edit.setText(folder)
            
    def get_settings(self):
        return {
            "generate_report": self.report_cb.isChecked(),
            "stop_on_error": self.stop_error_cb.isChecked(),
            "output_folder": self.out_edit.text()
        }
