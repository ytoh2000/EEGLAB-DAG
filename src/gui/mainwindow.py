from PyQt6.QtWidgets import QMainWindow, QSplitter, QWidget, QVBoxLayout, QToolBar, QFileDialog, QMessageBox
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtCore import Qt
from src.gui.canvas import CanvasView
from src.gui.sidebar import Sidebar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EEGLAB-DAG Pipeline Editor")
        self.resize(1200, 800)
        
        self.current_file = None
        self.unsaved_changes = False
        
        # Central Widget and Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter to hold Sidebar and (CWD + Canvas)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.layout.addWidget(self.splitter)
        
        # Sidebar (Left)
        self.sidebar = Sidebar()
        self.sidebar.setStyleSheet("background-color: #f0f0f0; min-width: 200px;")
        self.splitter.addWidget(self.sidebar)
        
        # Right Side Container (CWD Bar + Canvas)
        self.right_container = QWidget()
        self.right_layout = QVBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        
        # CWD Bar
        self.cwd_widget = self._create_cwd_widget()
        self.right_layout.addWidget(self.cwd_widget)
        
        # Canvas
        self.canvas = CanvasView()
        self.canvas.pipeline_changed.connect(self.on_pipeline_changed)
        self.right_layout.addWidget(self.canvas)
        
        # Connect Sidebar to Canvas
        self.sidebar.node_requested.connect(self.canvas.add_node_from_def)
        
        self.splitter.addWidget(self.right_container)
        
        # Set splitter sizes (20% sidebar, 80% canvas)
        self.splitter.setSizes([200, 1000])

        # Toolbar for Working Directory (as widget)
        # (Already created in previous step inside right_container)

        self._create_actions()
        self._create_main_toolbar()
        
        # Connect undo stack to unsaved changes tracking
        self.canvas.undo_stack.indexChanged.connect(self.on_pipeline_changed)
        
        self.update_title()

    def _create_main_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        
        from PyQt6.QtWidgets import QStyle
        style = self.style()
        
        # Open
        self.open_action.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        toolbar.addAction(self.open_action)
        
        # New from Template
        template_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder)
        self.template_action = QAction(template_icon, "New from Template", self)
        self.template_action.setToolTip("Start from a pipeline template")
        self.template_action.triggered.connect(self.new_from_template)
        toolbar.addAction(self.template_action)
        
        # Save
        self.save_action.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        toolbar.addAction(self.save_action)
        
        toolbar.addSeparator()
        
        # Undo
        undo_icon = style.standardIcon(QStyle.StandardPixmap.SP_ArrowBack)
        self.undo_action.setIcon(undo_icon)
        toolbar.addAction(self.undo_action)
        
        # Redo
        redo_icon = style.standardIcon(QStyle.StandardPixmap.SP_ArrowForward)
        self.redo_action.setIcon(redo_icon)
        toolbar.addAction(self.redo_action)
        
        toolbar.addSeparator()
        
        # Run Job
        run_icon = style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        self.run_action = QAction(run_icon, "Run Job", self)
        self.run_action.setToolTip("Export and Run Pipeline Job")
        self.run_action.triggered.connect(self.run_job)
        toolbar.addAction(self.run_action)

        toolbar.addSeparator()

        # Export Job (Standalone)
        export_icon = style.standardIcon(QStyle.StandardPixmap.SP_ArrowRight)
        self.export_action = QAction(export_icon, "Export Job", self)
        self.export_action.setToolTip("Export Job File Only")
        self.export_action.triggered.connect(self.export_job)
        toolbar.addAction(self.export_action)

        toolbar.addSeparator()

        # Fit to View
        fit_icon = style.standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton)
        self.fit_action = QAction(fit_icon, "Fit to View", self)
        self.fit_action.setToolTip("Fit to View (Ctrl+0)")
        self.fit_action.setShortcut("Ctrl+0")
        self.fit_action.triggered.connect(self.canvas.fit_to_view)
        toolbar.addAction(self.fit_action)
        
        # Reset Zoom
        reset_icon = style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        self.reset_zoom_action = QAction(reset_icon, "Reset Zoom", self)
        self.reset_zoom_action.setToolTip("Reset Zoom (Ctrl+=)")
        self.reset_zoom_action.setShortcut("Ctrl+=")
        self.reset_zoom_action.triggered.connect(self.canvas.reset_zoom)
        toolbar.addAction(self.reset_zoom_action)

        toolbar.addSeparator()

        # Theme Toggle
        self.theme_action = QAction("🌙 Dark Mode", self)
        self.theme_action.setToolTip("Toggle Dark/Light Mode")
        self.theme_action.triggered.connect(self.toggle_theme)
        toolbar.addAction(self.theme_action)

        toolbar.addSeparator()

        # Import from Paper (LLM)
        paper_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView)
        self.paper_action = QAction(paper_icon, "📄 Import from Paper", self)
        self.paper_action.setToolTip("Build pipeline from a research paper using AI")
        self.paper_action.triggered.connect(self.import_from_paper)
        toolbar.addAction(self.paper_action)

    def import_from_paper(self):
        from src.llm.dialog import PaperImportDialog
        dialog = PaperImportDialog(self)
        dialog.pipeline_ready.connect(self._on_paper_pipeline_ready)
        dialog.exec()
    
    def _on_paper_pipeline_ready(self, pipeline, warnings, reasoning):
        self.canvas.from_pipeline(pipeline)
        self.current_file = None
        self.unsaved_changes = True
        self.update_title()

    def toggle_theme(self):
        from src.gui.theme import ThemeManager
        from PyQt6.QtWidgets import QApplication
        new_theme = ThemeManager.toggle(QApplication.instance())
        if new_theme == 'dark':
            self.theme_action.setText("☀️ Light Mode")
            self.canvas.setBackgroundBrush(QColor('#1e1e1e'))
        else:
            self.theme_action.setText("🌙 Dark Mode")
            self.canvas.setBackgroundBrush(Qt.GlobalColor.white)

    def new_from_template(self):
        if not self.prompt_save_if_needed():
            return
        import os, sys
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            template_dir = os.path.abspath(os.path.join(base_dir, '..', '..', '..', 'library', 'pipelines'))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            template_dir = os.path.abspath(os.path.join(base_dir, '..', '..', 'library', 'pipelines'))
        
        if not os.path.isdir(template_dir):
            QMessageBox.warning(self, "No Templates", f"Template directory not found:\n{template_dir}")
            return
        
        filename, _ = QFileDialog.getOpenFileName(self, "Select Pipeline Template", template_dir, "JSON Files (*.json)")
        if filename:
            try:
                from src.model.pipeline import Pipeline
                pipeline = Pipeline.load(filename)
                self.canvas.from_pipeline(pipeline)
                self.current_file = None  # Don't associate with template path
                self.unsaved_changes = True
                self.update_title()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load template: {e}")

    def _create_cwd_widget(self):
        from PyQt6.QtWidgets import QLabel, QLineEdit, QPushButton, QSizePolicy, QHBoxLayout
        import os
        
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5) # Small padding
        
        label = QLabel("Current Directory: ")
        layout.addWidget(label)
        
        self.cwd_edit = QLineEdit(os.getcwd())
        # Let's allowing proper functionality:
        self.cwd_edit.returnPressed.connect(self.change_cwd_from_edit)
        
        # Expand policy
        self.cwd_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        layout.addWidget(self.cwd_edit)
        
        btn_browse = QPushButton("...")
        btn_browse.setToolTip("Browse Working Directory")
        btn_browse.setFixedWidth(30)
        btn_browse.clicked.connect(self.browse_cwd)
        layout.addWidget(btn_browse)
        
        return widget

    def browse_cwd(self):
        import os
        new_dir = QFileDialog.getExistingDirectory(self, "Select Working Directory", self.cwd_edit.text())
        if new_dir:
            os.chdir(new_dir)
            self.cwd_edit.setText(new_dir)
            
    def change_cwd_from_edit(self):
        import os
        new_dir = self.cwd_edit.text()
        if os.path.isdir(new_dir):
            try:
                os.chdir(new_dir)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not change directory: {e}")
                self.cwd_edit.setText(os.getcwd()) # Revert
        else:
             QMessageBox.warning(self, "Error", "Directory does not exist.")
             self.cwd_edit.setText(os.getcwd()) # Revert

    def _create_actions(self):
        self.save_action = QAction("Save", self)
        self.save_action.setToolTip("Save Pipeline (Ctrl+S)")
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self.save_file)
        
        self.open_action = QAction("Open", self)
        self.open_action.setToolTip("Open Pipeline (Ctrl+O)")
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_file)
        
        self.undo_action = QAction("Undo", self)
        self.undo_action.setToolTip("Undo (Ctrl+Z)")
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(lambda: self.canvas.undo_stack.undo())
        
        self.redo_action = QAction("Redo", self)
        self.redo_action.setToolTip("Redo (Ctrl+Shift+Z)")
        self.redo_action.setShortcut("Ctrl+Shift+Z")
        self.redo_action.triggered.connect(lambda: self.canvas.undo_stack.redo())

    def run_job(self):
        # 1. Prompt Save if needed
        if self.unsaved_changes:
            reply = QMessageBox.question(self, "Unsaved Changes", 
                                         "The pipeline has unsaved changes.\nDo you want to save the pipeline before running?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            
            if reply == QMessageBox.StandardButton.Yes:
                if not self.save_file():
                    return # Cancelled save, stop run
            elif reply == QMessageBox.StandardButton.Cancel:
                return # Cancel run
        
        # 2. Export Job (Auto-prompt via common logic? Or distinct flow?)
        # For Run Job, we usually just want to get the file.
        self.export_job(run_after=True)

    def export_job(self, run_after=False):
        # 1. Validation (Structure + Files)
        pipeline = self.canvas.to_pipeline()
        is_valid, error_msg = pipeline.validate(check_files=True)
        
        if not is_valid:
            QMessageBox.critical(self, "Validation Error", error_msg)
            return

        filename, _ = QFileDialog.getSaveFileName(self, "Export Job File", "", "JSON Files (*.json)")
        if filename:
            try:
                from src.model.job_exporter import JobExporter
                exporter = JobExporter(pipeline)
                exporter.export(filename)
                
                if run_after:
                    # 3. Execution Hint
                    msg = f"Job successfully exported onto:\n{filename}\n\nTo execute in EEGLAB:\n1. Click 'Execute Job' in the DAG menu.\n2. Or run: run_pipeline('{filename}')"
                    QMessageBox.information(self, "Job Exported", msg)
                else:
                    QMessageBox.information(self, "Success", f"Job exported to:\n{filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "Validation Error", f"Could not export job:\n{e}")

    def on_pipeline_changed(self):
        self.unsaved_changes = True
        self.update_title()

    def update_title(self):
        title = "EEGLAB-DAG Pipeline Editor"
        if self.current_file:
            title += f" - {self.current_file}"
        else:
            title += " - Untitled"
            
        if self.unsaved_changes:
            title += " *"
            
        self.setWindowTitle(title)

    def closeEvent(self, event):
        if self.prompt_save_if_needed():
            event.accept()
        else:
            event.ignore()

    def prompt_save_if_needed(self):
        if not self.unsaved_changes:
            return True
            
        reply = QMessageBox.question(
            self, 
            "Unsaved Changes",
            "You have unsaved changes. Do you want to save them?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Save:
            return self.save_file()
        elif reply == QMessageBox.StandardButton.Discard:
            return True
        else: # Cancel
            return False

    def save_file(self):
        # 1. Validation (Structure Only)
        pipeline = self.canvas.to_pipeline()  
        is_valid, error_msg = pipeline.validate(check_files=False)
        
        if not is_valid:
            QMessageBox.critical(self, "Validation Error", error_msg)
            return False

        if self.current_file:
            filename = self.current_file
        else:
            # Default to library/pipelines
            import sys
            import os
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
                default_dir = os.path.abspath(os.path.join(base_dir, '..', '..', '..', 'library', 'pipelines'))
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                default_dir = os.path.abspath(os.path.join(base_dir, '..', '..', 'library', 'pipelines'))
                
            if not os.path.exists(default_dir):
                os.makedirs(default_dir, exist_ok=True)
                
            filename, _ = QFileDialog.getSaveFileName(self, "Save Pipeline", default_dir, "JSON Files (*.json)")
            
        if filename:
            # Auto-append .json if user didn't type an extension
            if not os.path.splitext(filename)[1]:
                filename += '.json'
            try:
                pipeline.save(filename)
                self.current_file = filename
                self.unsaved_changes = False
                self.update_title()
                QMessageBox.information(self, "Success", "Pipeline saved successfully.")
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {e}")
                return False
        return False

    def open_file(self):
        if not self.prompt_save_if_needed():
            return
            
        # Default to library/pipelines
        import sys
        import os
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
            default_dir = os.path.abspath(os.path.join(base_dir, '..', '..', '..', 'library', 'pipelines'))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            default_dir = os.path.abspath(os.path.join(base_dir, '..', '..', 'library', 'pipelines'))
            
        if not os.path.exists(default_dir):
            os.makedirs(default_dir, exist_ok=True)

        filename, _ = QFileDialog.getOpenFileName(self, "Open Pipeline", default_dir, "JSON Files (*.json)")
        if filename:
            try:
                from src.model.pipeline import Pipeline
                pipeline = Pipeline.load(filename)
                self.canvas.from_pipeline(pipeline)
                self.current_file = filename
                self.unsaved_changes = False
                self.update_title()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load file: {e}")
