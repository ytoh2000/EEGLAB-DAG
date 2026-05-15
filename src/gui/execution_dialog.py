from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import QProcess, Qt

class ExecutionDialog(QDialog):
    """A dialog to display live console output from a running background process (like MATLAB)."""
    
    def __init__(self, global_savepath=None, parent=None, save_log=False):
        super().__init__(parent)
        self.global_savepath = global_savepath
        self.save_log = save_log
        self.log_file = None
        self.setWindowTitle("MATLAB Pipeline Execution")
        self.resize(700, 500)
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
        
        import os
        import platform
        
        self.btn_open_folder = QPushButton("Open Save Path")
        self.btn_open_folder.clicked.connect(self.open_savepath)
        if not self.global_savepath:
            import os
            self.global_savepath = os.getcwd()
        
        if not os.path.isdir(self.global_savepath):
            self.btn_open_folder.setToolTip(f"Path will be created on open: {self.global_savepath}")
        btn_layout.addWidget(self.btn_open_folder)
        
        self.btn_cancel = QPushButton("Cancel Execution")
        self.btn_cancel.clicked.connect(self.cancel_execution)
        btn_layout.addWidget(self.btn_cancel)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.setEnabled(False) # Disabled while running
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)
        
        if self.save_log and self.global_savepath:
            self._setup_logging()
        
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        
    def start_execution(self, program, arguments):
        """Starts the process and displays the dialog."""
        cmd_str = f"{program} " + " ".join([f'"{arg}"' if ' ' in arg else arg for arg in arguments])
        self.append_message(f"> Starting MATLAB Execution...\n> Command: {cmd_str}\n")
        
        self.process.start(program, arguments)
        self.show()

    def append_message(self, text):
        """Appends text to the output view and the log file if open."""
        self.output_view.appendPlainText(text)
        if self.log_file:
            # Ensure text ends with newline for file
            file_text = text if text.endswith('\n') else text + '\n'
            self.log_file.write(file_text)
            self.log_file.flush()
        # Scroll to bottom
        self.output_view.ensureCursorVisible()

    def _setup_logging(self):
        import os
        from datetime import datetime
        try:
            log_dir = os.path.join(self.global_savepath, "log")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"log_run_MATLAB_{timestamp}.log"
            log_path = os.path.join(log_dir, filename)
            
            self.log_file = open(log_path, "w", encoding="utf-8")
            self.output_view.appendPlainText(f"> Log file: {log_path}\n")
        except Exception as e:
            self.output_view.appendPlainText(f"> Warning: Could not create log file: {e}\n")
            self.log_file = None
        
    def _insert_text_handling_backspace(self, text):
        cursor = self.output_view.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        
        for char in text:
            if char == '\b':
                cursor.deletePreviousChar()
            elif char == '\r':
                pass # Usually we can just ignore standalone \r if \b does the backspacing, but let's ignore to avoid weird jumps
            else:
                cursor.insertText(char)
                
        self.output_view.setTextCursor(cursor)
        # Ensure scroll to bottom
        self.output_view.ensureCursorVisible()

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        text = bytes(data).decode('utf-8', errors='replace')
        self._insert_text_handling_backspace(text)
        if self.log_file:
            self.log_file.write(text)
            self.log_file.flush()

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        text = bytes(data).decode('utf-8', errors='replace')
        self._insert_text_handling_backspace(text)
        if self.log_file:
            self.log_file.write(text)
            self.log_file.flush()

    def open_savepath(self):
        import os
        import platform
        import subprocess
        
        folder = self.global_savepath
        if not folder:
            return
            
        # Create folder if it doesn't exist
        if not os.path.exists(folder):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                self.output_view.appendPlainText(f"\n> Error: Could not create directory {folder}: {e}")
                return
            
        if platform.system() == "Windows":
            os.startfile(folder)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    def process_finished(self, exit_code, exit_status):
        self.output_view.appendPlainText(f"\n> Execution Finished (Exit Code: {exit_code})")
        self.btn_cancel.setEnabled(False)
        self.btn_close.setEnabled(True)
        if self.log_file:
            self.log_file.close()
            self.log_file = None

    def cancel_execution(self):
        """Kills the running process."""
        if self.process.state() == QProcess.ProcessState.Running:
            self.output_view.appendPlainText("\n> Cancelling Execution... Terminating MATLAB process.")
            self.process.kill()
            
    def closeEvent(self, event):
        """Ensure process is killed and log is closed if user closes the window while it's running."""
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        super().closeEvent(event)
