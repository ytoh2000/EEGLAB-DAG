from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import QProcess, Qt

class ExecutionDialog(QDialog):
    """A dialog to display live console output from a running background process (like MATLAB)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MATLAB Pipeline Execution")
        self.resize(600, 400)
        self.setModal(False) # Non-modal so user can interact with main window if needed
        
        layout = QVBoxLayout(self)
        
        self.output_view = QPlainTextEdit(self)
        self.output_view.setReadOnly(True)
        # Monospace font for better console formatting
        font = self.output_view.font()
        font.setFamily("Menlo") # Mac-specific monospace, but fallback is fine
        font.setStyleHint(font.StyleHint.Monospace)
        self.output_view.setFont(font)
        
        layout.addWidget(self.output_view)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel Execution")
        self.btn_cancel.clicked.connect(self.cancel_execution)
        btn_layout.addWidget(self.btn_cancel)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.setEnabled(False) # Disabled while running
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        
    def start_execution(self, program, arguments):
        """Starts the process and displays the dialog."""
        self.output_view.clear()
        cmd_str = f"{program} " + " ".join([f'"{arg}"' if ' ' in arg else arg for arg in arguments])
        self.output_view.appendPlainText(f"> Starting MATLAB Execution...\n> Command: {cmd_str}\n")
        
        self.process.start(program, arguments)
        self.show()
        
    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode('utf-8', errors='replace')
        self.output_view.moveCursor(self.output_view.textCursor().MoveOperation.End)
        self.output_view.insertPlainText(text)
        self.output_view.moveCursor(self.output_view.textCursor().MoveOperation.End)

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        text = bytes(data).decode('utf-8', errors='replace')
        self.output_view.moveCursor(self.output_view.textCursor().MoveOperation.End)
        self.output_view.insertPlainText(text)
        self.output_view.moveCursor(self.output_view.textCursor().MoveOperation.End)

    def process_finished(self, exit_code, exit_status):
        self.output_view.appendPlainText(f"\n> Execution Finished (Exit Code: {exit_code})")
        self.btn_cancel.setEnabled(False)
        self.btn_close.setEnabled(True)

    def cancel_execution(self):
        """Kills the running process."""
        if self.process.state() == QProcess.ProcessState.Running:
            self.output_view.appendPlainText("\n> Cancelling Execution... Terminating MATLAB process.")
            self.process.kill()
            
    def closeEvent(self, event):
        """Ensure process is killed if user closes the window while it's running."""
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
        super().closeEvent(event)
