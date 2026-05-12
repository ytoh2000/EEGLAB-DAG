import os
import shutil
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QDialogButtonBox, QMessageBox)
from PyQt6.QtCore import QSettings

class AppSettingsManager:
    """Manages application-level global preferences using QSettings."""
    
    def __init__(self):
        self.settings = QSettings("EEGLAB-DAG", "MainApp")
        
    def get_matlab_path(self):
        return self.settings.value("matlab_path", "")
        
    def set_matlab_path(self, path):
        self.settings.setValue("matlab_path", path)
        
    def get_eeglab_path(self):
        return self.settings.value("eeglab_path", "")
        
    def set_eeglab_path(self, path):
        self.settings.setValue("eeglab_path", path)

    def auto_discover_matlab(self):
        """Attempts to find the MATLAB executable on the system."""
        # 1. Check system PATH
        path = shutil.which("matlab")
        if path:
            return path
            
        # 2. Common OS-specific locations
        if os.name == 'posix': # macOS / Linux
            # Try to find /Applications/MATLAB_R202*.app/bin/matlab
            mac_apps = '/Applications'
            if os.path.exists(mac_apps):
                for item in os.listdir(mac_apps):
                    if item.startswith('MATLAB_R20') and item.endswith('.app'):
                        bin_path = os.path.join(mac_apps, item, 'bin', 'matlab')
                        if os.path.exists(bin_path):
                            return bin_path
        elif os.name == 'nt': # Windows
            # Try C:\Program Files\MATLAB\R202*\bin\matlab.exe
            win_prog = 'C:\\Program Files\\MATLAB'
            if os.path.exists(win_prog):
                for item in os.listdir(win_prog):
                    if item.startswith('R202'):
                        bin_path = os.path.join(win_prog, item, 'bin', 'matlab.exe')
                        if os.path.exists(bin_path):
                            return bin_path
        return ""


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Application Preferences")
        self.resize(500, 150)
        
        self.manager = AppSettingsManager()
        layout = QVBoxLayout(self)
        
        # MATLAB Path
        matlab_layout = QHBoxLayout()
        matlab_layout.addWidget(QLabel("MATLAB Executable Path:"))
        self.matlab_edit = QLineEdit(self.manager.get_matlab_path())
        matlab_layout.addWidget(self.matlab_edit)
        btn_browse_matlab = QPushButton("Browse...")
        btn_browse_matlab.clicked.connect(self.browse_matlab)
        matlab_layout.addWidget(btn_browse_matlab)
        layout.addLayout(matlab_layout)
        
        # EEGLAB Path
        eeglab_layout = QHBoxLayout()
        eeglab_layout.addWidget(QLabel("EEGLAB Folder Path:"))
        self.eeglab_edit = QLineEdit(self.manager.get_eeglab_path())
        eeglab_layout.addWidget(self.eeglab_edit)
        btn_browse_eeglab = QPushButton("Browse...")
        btn_browse_eeglab.clicked.connect(self.browse_eeglab)
        eeglab_layout.addWidget(btn_browse_eeglab)
        layout.addLayout(eeglab_layout)
        
        layout.addStretch()
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
    def browse_matlab(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select MATLAB Executable")
        if path:
            self.matlab_edit.setText(path)
            
    def browse_eeglab(self):
        folder = QFileDialog.getExistingDirectory(self, "Select EEGLAB Folder")
        if folder:
            self.eeglab_edit.setText(folder)
            
    def save_settings(self):
        m_path = self.matlab_edit.text()
        e_path = self.eeglab_edit.text()
        
        if m_path and not os.path.exists(m_path):
            QMessageBox.warning(self, "Warning", "MATLAB path does not exist.")
            return
            
        if e_path and not os.path.exists(e_path):
            QMessageBox.warning(self, "Warning", "EEGLAB path does not exist.")
            return
            
        self.manager.set_matlab_path(m_path)
        self.manager.set_eeglab_path(e_path)
        self.accept()
