"""
Paper Import Dialog — GUI for the LLM pipeline builder.

Provides:
- API key setup (first-run flow)
- PDF upload or URL input
- Methods text extraction and preview
- LLM pipeline generation with progress feedback
- Pipeline preview with warnings before accepting
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QTabWidget, QWidget, QFileDialog, QMessageBox,
    QProgressBar, QDialogButtonBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices

from src.llm.settings import get_api_key, save_api_key, has_api_key


class ApiKeyDialog(QDialog):
    """First-run dialog for configuring the Gemini API key."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gemini API Key Setup")
        self.resize(450, 280)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "To use the LLM pipeline builder, you need a free\n"
            "Google Gemini API key.\n\n"
            "1. Visit aistudio.google.com\n"
            "2. Sign in with your Google account\n"
            "3. Click 'Get API Key' then 'Create API Key'\n"
            "4. Copy and paste the key below:"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Link button
        link_btn = QPushButton("Open aistudio.google.com")
        link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://aistudio.google.com/apikey")))
        layout.addWidget(link_btn)
        
        # Key input
        form = QFormLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("Paste your API key here...")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.textChanged.connect(self._on_key_changed)
        form.addRow("API Key:", self.key_edit)
        layout.addLayout(form)
        
        # Show/hide toggle
        self.show_key_btn = QPushButton("Show Key")
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.toggled.connect(self._toggle_visibility)
        layout.addWidget(self.show_key_btn)
        
        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._save)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
        layout.addWidget(self.button_box)
        
        # Pre-fill if key exists
        existing = get_api_key()
        if existing:
            self.key_edit.setText(existing)
    
    def _on_key_changed(self, text):
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setEnabled(len(text.strip()) > 10)
    
    def _toggle_visibility(self, checked):
        if checked:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_btn.setText("Hide Key")
        else:
            self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_btn.setText("Show Key")
    
    def _save(self):
        key = self.key_edit.text().strip()
        save_api_key(key)
        self.accept()


class LLMWorker(QThread):
    """Background thread for LLM API calls."""
    finished = pyqtSignal(dict)      # pipeline data
    error = pyqtSignal(str)          # error message
    
    def __init__(self, methods_text):
        super().__init__()
        self.methods_text = methods_text
    
    def run(self):
        try:
            from src.llm.engine import generate_pipeline_json
            result = generate_pipeline_json(self.methods_text)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class PaperImportDialog(QDialog):
    """Main dialog for importing a paper and generating a pipeline."""
    
    pipeline_ready = pyqtSignal(object, list, dict)  # Pipeline, warnings, reasoning
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📄 Build Pipeline from Paper")
        self.resize(600, 500)
        self.setMaximumWidth(650)
        self._worker = None
        self._llm_result = None
        
        layout = QVBoxLayout(self)
        
        # API Key status
        key_bar = QHBoxLayout()
        self.key_status = QLabel()
        self._update_key_status()
        key_bar.addWidget(self.key_status)
        key_bar.addStretch()
        self.key_btn = QPushButton("⚙ API Key Settings")
        self.key_btn.clicked.connect(self._open_key_settings)
        key_bar.addWidget(self.key_btn)
        layout.addLayout(key_bar)
        
        # Input tabs: PDF or URL
        self.input_tabs = QTabWidget()
        
        # PDF tab
        pdf_widget = QWidget()
        pdf_layout = QVBoxLayout(pdf_widget)
        pdf_row = QHBoxLayout()
        self.pdf_path = QLineEdit()
        self.pdf_path.setPlaceholderText("Select a PDF file...")
        self.pdf_path.setReadOnly(True)
        pdf_row.addWidget(self.pdf_path)
        pdf_browse = QPushButton("Browse...")
        pdf_browse.clicked.connect(self._browse_pdf)
        pdf_row.addWidget(pdf_browse)
        pdf_layout.addLayout(pdf_row)
        self.input_tabs.addTab(pdf_widget, "📄 Upload PDF")
        
        # URL tab
        url_widget = QWidget()
        url_layout = QVBoxLayout(url_widget)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste article URL here...")
        url_layout.addWidget(self.url_input)
        self.input_tabs.addTab(url_widget, "🌐 Paste URL")
        
        # Paste text tab
        text_widget = QWidget()
        text_layout = QVBoxLayout(text_widget)
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Paste the Methods section text here...")
        text_layout.addWidget(self.text_input)
        self.input_tabs.addTab(text_widget, "📝 Paste Text")
        
        layout.addWidget(self.input_tabs)
        
        # Extract button
        self.extract_btn = QPushButton("1. Extract Methods Section")
        self.extract_btn.clicked.connect(self._extract)
        layout.addWidget(self.extract_btn)
        
        # Methods preview
        methods_group = QGroupBox("Extracted Methods Text (editable)")
        methods_layout = QVBoxLayout(methods_group)
        self.methods_preview = QTextEdit()
        self.methods_preview.setPlaceholderText("Methods text will appear here after extraction...")
        self.methods_preview.setMinimumHeight(100)
        methods_layout.addWidget(self.methods_preview)
        layout.addWidget(methods_group)
        
        # Build button
        self.build_btn = QPushButton("2. Build Pipeline with AI")
        self.build_btn.setEnabled(False)
        self.build_btn.clicked.connect(self._build_pipeline)
        layout.addWidget(self.build_btn)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.hide()
        layout.addWidget(self.progress)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Accept/Cancel
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.accept_btn = QPushButton("✓ Accept Pipeline")
        self.accept_btn.setEnabled(False)
        self.accept_btn.clicked.connect(self._accept_pipeline)
        btn_layout.addWidget(self.accept_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def _update_key_status(self):
        if has_api_key():
            self.key_status.setText("🟢 API Key configured")
            self.key_status.setStyleSheet("color: #4CAF50;")
        else:
            self.key_status.setText("🔴 API Key not set")
            self.key_status.setStyleSheet("color: #EF5350;")
    
    def _open_key_settings(self):
        dlg = ApiKeyDialog(self)
        if dlg.exec():
            self._update_key_status()
    
    def _browse_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Paper PDF", "", "PDF Files (*.pdf)")
        if path:
            self.pdf_path.setText(path)
    
    def _extract(self):
        """Extract text from the selected source."""
        tab = self.input_tabs.currentIndex()
        
        try:
            if tab == 0:  # PDF
                path = self.pdf_path.text()
                if not path:
                    QMessageBox.warning(self, "No File", "Please select a PDF file first.")
                    return
                from src.llm.extractor import extract_from_pdf, extract_methods_section
                self.status_label.setText("Extracting text from PDF...")
                full_text = extract_from_pdf(path)
                methods = extract_methods_section(full_text)
                
            elif tab == 1:  # URL
                url = self.url_input.text().strip()
                if not url:
                    QMessageBox.warning(self, "No URL", "Please enter an article URL first.")
                    return
                from src.llm.extractor import extract_from_url, extract_methods_section
                self.status_label.setText("Fetching article from URL...")
                full_text = extract_from_url(url)
                methods = extract_methods_section(full_text)
                
            else:  # Pasted text
                text = self.text_input.toPlainText().strip()
                if not text:
                    QMessageBox.warning(self, "No Text", "Please paste the methods text first.")
                    return
                methods = text
            
            self.methods_preview.setPlainText(methods)
            self.build_btn.setEnabled(True)
            char_count = len(methods)
            self.status_label.setText(f"✓ Extracted {char_count:,} characters. Review the text, then click 'Build Pipeline'.")
            
        except Exception as e:
            QMessageBox.critical(self, "Extraction Error", f"Could not extract text:\n\n{e}")
            self.status_label.setText("Extraction failed.")
    
    def _build_pipeline(self):
        """Send methods text to LLM."""
        if not has_api_key():
            self._open_key_settings()
            if not has_api_key():
                return
        
        methods = self.methods_preview.toPlainText().strip()
        if not methods:
            QMessageBox.warning(self, "No Text", "No methods text to analyze.")
            return
        
        # Disable buttons, show progress
        self.build_btn.setEnabled(False)
        self.extract_btn.setEnabled(False)
        self.progress.show()
        self.status_label.setText("🤖 Sending to Gemini AI... This may take 10-30 seconds.")
        
        # Run in background thread
        self._worker = LLMWorker(methods)
        self._worker.finished.connect(self._on_llm_success)
        self._worker.error.connect(self._on_llm_error)
        self._worker.start()
    
    def _on_llm_success(self, result):
        self.progress.hide()
        self._llm_result = result
        
        node_count = len(result.get('nodes', []))
        edge_count = len(result.get('edges', []))
        
        # Show summary
        node_names = [n.get('label', n.get('function', '?')) for n in result.get('nodes', [])]
        summary = ' → '.join(node_names)
        
        self.status_label.setText(
            f"✓ Generated pipeline: {node_count} nodes, {edge_count} edges\n"
            f"Pipeline: {summary}"
        )
        
        self.accept_btn.setEnabled(True)
        self.build_btn.setEnabled(True)
        self.build_btn.setText("2. Rebuild Pipeline")
        self.extract_btn.setEnabled(True)
    
    def _on_llm_error(self, error_msg):
        self.progress.hide()
        self.build_btn.setEnabled(True)
        self.extract_btn.setEnabled(True)
        self.status_label.setText("❌ Pipeline generation failed.")
        QMessageBox.critical(self, "LLM Error", f"Could not generate pipeline:\n\n{error_msg}")
    
    def _accept_pipeline(self):
        """Build Pipeline object and emit."""
        if not self._llm_result:
            return
        
        from src.llm.builder import build_pipeline_from_llm
        pipeline, warnings, reasoning = build_pipeline_from_llm(self._llm_result)
        
        if warnings:
            msg = "The AI generated the pipeline, but with some notes:\n\n"
            msg += '\n'.join(f"• {w}" for w in warnings)
            msg += "\n\nAccept anyway?"
            reply = QMessageBox.question(self, "Pipeline Warnings", msg,
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.pipeline_ready.emit(pipeline, warnings, reasoning)
        self.accept()
