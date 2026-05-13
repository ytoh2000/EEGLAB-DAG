from PyQt6.QtWidgets import QMainWindow, QSplitter, QWidget, QVBoxLayout, QToolBar, QFileDialog, QMessageBox, QMenuBar, QMenu, QDockWidget
from PyQt6.QtGui import QAction, QColor, QKeySequence
from PyQt6.QtCore import Qt
from src.gui.canvas import CanvasView
from src.gui.sidebar import Sidebar
from src.gui.file_browser import FileBrowserWidget
from src.gui.pipeline_settings_widget import PipelineSettingsWidget
from src.gui.app_settings import AppSettingsManager, PreferencesDialog
from src.gui.execution_dialog import ExecutionDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EEGLAB-DAG Pipeline Editor")
        self.resize(1200, 800)
        
        self.current_file = None
        self.unsaved_changes = False
        self.pipeline_settings = {
            "generate_report": True,
            "error_strategy": "halt",
            "test_mode": False,
            "test_sample_size": 1,
            "parallel_processing": False,
            "output_folder": ""
        }
        
        self.app_settings = AppSettingsManager()
        
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, self._check_matlab_path)
        
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
        self._create_menus()
        self._create_main_toolbar()
        
        # Connect undo stack to unsaved changes tracking
        self.canvas.undo_stack.indexChanged.connect(self.on_pipeline_changed)
        
        self.update_title()
        
        # Initialize file browser path to current directory
        
        # Right Side File Browser Dock
        self.file_dock = QDockWidget("File Browser", self)
        self.file_browser = FileBrowserWidget()
        self.file_browser.cwd_requested.connect(self.set_cwd)
        self.file_dock.setWidget(self.file_browser)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.file_dock)
        
        # Right Side Pipeline Settings Dock
        self.settings_dock = QDockWidget("Pipeline Settings", self)
        self.settings_widget = PipelineSettingsWidget(self.pipeline_settings)
        self.settings_widget.settings_changed.connect(self.on_settings_changed)
        self.settings_dock.setWidget(self.settings_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.settings_dock)
        
        # Split docks vertically (File browser on top, settings below)
        self.splitDockWidget(self.file_dock, self.settings_dock, Qt.Orientation.Vertical)
        
        import os
        self.set_cwd(os.getcwd())

    def _check_matlab_path(self):
        matlab = self.app_settings.get_matlab_path()
        if not matlab:
            discovered = self.app_settings.auto_discover_matlab()
            if discovered:
                self.app_settings.set_matlab_path(discovered)
            else:
                QMessageBox.information(self, "MATLAB Not Found", 
                                        "MATLAB executable could not be found automatically.\n\n"
                                        "You can still use EEGLAB-DAG to construct, edit, and export pipelines, but MATLAB is required to execute them and process EEG data.\n\n"
                                        "If you have MATLAB installed, you can configure its path anytime in Preferences (File -> Preferences).")

    def _create_main_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(__import__('PyQt6.QtCore', fromlist=['QSize']).QSize(20, 20))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        
        from PyQt6.QtWidgets import QStyle
        style = self.style()
        
        # Open
        self.open_action.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        toolbar.addAction(self.open_action)
        
        # New from Template
        self.template_action.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        toolbar.addAction(self.template_action)
        
        # Save
        self.save_action.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        toolbar.addAction(self.save_action)
        

        # Export MATLAB Script
        self.export_m_action.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        toolbar.addAction(self.export_m_action)
        
        toolbar.addSeparator()
        
        # Undo
        self.undo_action.setIcon(self._create_undo_icon())
        toolbar.addAction(self.undo_action)
        
        # Redo
        self.redo_action.setIcon(self._create_redo_icon())
        toolbar.addAction(self.redo_action)
        
        toolbar.addSeparator()
        
        # Run Job
        self.run_action.setIcon(self._create_run_icon())
        toolbar.addAction(self.run_action)

        toolbar.addSeparator()

        # Fit to View
        self.fit_action.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
        toolbar.addAction(self.fit_action)
        
        # Reset Zoom
        self.reset_zoom_action.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        toolbar.addAction(self.reset_zoom_action)

        toolbar.addSeparator()
        toolbar.addSeparator()

        # Import from Paper (LLM)
        self.paper_action.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        toolbar.addAction(self.paper_action)

    def on_settings_changed(self, new_settings):
        self.pipeline_settings = new_settings
        self.unsaved_changes = True
        self.update_title()

    def import_from_paper(self):
        from src.llm.dialog import PaperImportDialog
        dialog = PaperImportDialog(self)
        dialog.pipeline_ready.connect(self._on_paper_pipeline_ready)
        dialog.exec()
    
    def _on_paper_pipeline_ready(self, pipeline, warnings, reasoning):
        self.canvas.from_pipeline(pipeline)
        self.pipeline_settings = pipeline.settings
        self.settings_widget.set_settings(self.pipeline_settings)
        self.current_file = None
        self.unsaved_changes = True
        self.update_title()


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
        
        filename, _ = QFileDialog.getOpenFileName(self, "Select Pipeline Template", template_dir, "Pipeline Files (*.eegpipe *.json)")
        if filename:
            try:
                from src.model.pipeline import Pipeline
                pipeline = Pipeline.load(filename)
                self.canvas.from_pipeline(pipeline)
                self.pipeline_settings = pipeline.settings
                self.settings_widget.set_settings(self.pipeline_settings)
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

    def set_cwd(self, new_dir):
        import os
        if os.path.isdir(new_dir):
            try:
                os.chdir(new_dir)
                self.cwd_edit.setText(new_dir)
                self.file_browser.set_path(new_dir)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not change directory: {e}")
                self.cwd_edit.setText(os.getcwd()) # Revert
        else:
             QMessageBox.warning(self, "Error", "Directory does not exist.")
             self.cwd_edit.setText(os.getcwd()) # Revert

    def browse_cwd(self):
        import os
        new_dir = QFileDialog.getExistingDirectory(self, "Select Working Directory", self.cwd_edit.text())
        if new_dir:
            self.set_cwd(new_dir)
            
    def change_cwd_from_edit(self):
        self.set_cwd(self.cwd_edit.text())

    def show_preferences(self):
        dialog = PreferencesDialog(self)
        dialog.exec()

    def _create_actions(self):
        self.save_action = QAction("Save", self)
        self.save_action.setToolTip("Save Pipeline (Ctrl+S)")
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save_file)
        
        self.open_action = QAction("Open", self)
        self.open_action.setToolTip("Open Pipeline (Ctrl+O)")
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_file)
        
        self.new_action = QAction("New", self)
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_action.triggered.connect(self.new_file)
        
        self.save_as_action = QAction("Save As...", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self.save_as_file)
        
        self.prefs_action = QAction("Preferences...", self)
        self.prefs_action.triggered.connect(self.show_preferences)
        
        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.exit_action.triggered.connect(self.close)
        
        self.undo_action = QAction("Undo", self)
        self.undo_action.setToolTip("Undo (Ctrl+Z)")
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.triggered.connect(lambda: self.canvas.undo_stack.undo())
        
        self.redo_action = QAction("Redo", self)
        self.redo_action.setToolTip("Redo (Ctrl+Shift+Z)")
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(lambda: self.canvas.undo_stack.redo())
        
        self.delete_action = QAction("Delete Selected", self)
        self.delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        self.delete_action.triggered.connect(self.canvas.remove_selected_items)
        
        self.clear_action = QAction("Clear Canvas", self)
        self.clear_action.triggered.connect(self.canvas.clear_canvas)
        
        self.template_action = QAction("New from Template", self)
        self.template_action.setToolTip("Start from a pipeline template")
        self.template_action.triggered.connect(self.new_from_template)
        

        self.export_m_action = QAction("Export MATLAB Script", self)
        self.export_m_action.setToolTip("Export Standalone MATLAB Script(s)")
        self.export_m_action.triggered.connect(self.export_matlab_script)
        
        self.run_action = QAction("Run Pipeline", self)
        self.run_action.setToolTip("Run Pipeline")
        self.run_action.triggered.connect(self.run_job)
        
        self.fit_action = QAction("Fit to View", self)
        self.fit_action.setToolTip("Fit to View (Ctrl+0)")
        self.fit_action.setShortcut("Ctrl+0")
        self.fit_action.triggered.connect(self.canvas.fit_to_view)
        
        self.reset_zoom_action = QAction("Reset Zoom", self)
        self.reset_zoom_action.setToolTip("Reset Zoom (Ctrl+=)")
        self.reset_zoom_action.setShortcut("Ctrl+=")
        self.reset_zoom_action.triggered.connect(self.canvas.reset_zoom)
        
        self.paper_action = QAction("📄 Import from Paper", self)
        self.paper_action.setToolTip("Build pipeline from a research paper using AI")
        self.paper_action.triggered.connect(self.import_from_paper)
        
        self.zoom_in_action = QAction("Zoom In", self)
        self.zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        self.zoom_in_action.triggered.connect(self.canvas.zoom_in)
        
        self.zoom_out_action = QAction("Zoom Out", self)
        self.zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self.zoom_out_action.triggered.connect(self.canvas.zoom_out)
        
        self.toggle_sidebar_action = QAction("Toggle Sidebar", self)
        self.toggle_sidebar_action.setCheckable(True)
        self.toggle_sidebar_action.setChecked(True)
        self.toggle_sidebar_action.triggered.connect(self.sidebar.setVisible)
        
        self.about_action = QAction("About EEGLAB-DAG", self)
        self.about_action.triggered.connect(self.show_about)

    def _create_menus(self):
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu("File")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.template_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.export_m_action)
        file_menu.addSeparator()
        file_menu.addAction(self.prefs_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        
        # Edit Menu
        edit_menu = menubar.addMenu("Edit")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.delete_action)
        edit_menu.addAction(self.clear_action)
        
        # View Menu
        view_menu = menubar.addMenu("View")
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)
        view_menu.addAction(self.reset_zoom_action)
        view_menu.addAction(self.fit_action)
        view_menu.addSeparator()
        view_menu.addAction(self.toggle_sidebar_action)
        
        # Pipeline Menu
        pipeline_menu = menubar.addMenu("Pipeline")
        pipeline_menu.addAction(self.run_action)
        
        # AI Assistant Menu
        ai_menu = menubar.addMenu("AI Assistant")
        ai_menu.addAction(self.paper_action)
        
        # Help Menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction(self.about_action)

    def new_file(self):
        if self.prompt_save_if_needed():
            self.canvas.clear_canvas()
            self.current_file = None
            self.unsaved_changes = False
            self.update_title()
            
    def save_as_file(self):
        old_file = self.current_file
        self.current_file = None
        if not self.save_file():
            self.current_file = old_file
            return False
        return True
            
    def show_about(self):
        QMessageBox.about(self, "About EEGLAB-DAG", 
                          "EEGLAB-DAG Pipeline Editor\nA graphical tool for creating and executing EEGLAB processing pipelines.")

    def run_job(self):
        if self.unsaved_changes:
            reply = QMessageBox.question(self, "Unsaved Changes", 
                                         "The pipeline has unsaved changes.\nDo you want to save the pipeline before running?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            
            if reply == QMessageBox.StandardButton.Yes:
                if not self.save_file():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return
                
        matlab_path = self.app_settings.get_matlab_path()
        if not matlab_path:
            QMessageBox.warning(self, "MATLAB Path Not Set", 
                                "Please configure the MATLAB executable path in Preferences (File -> Preferences).")
            return
            
        pipeline = self.canvas.to_pipeline()
        pipeline.settings = self.pipeline_settings
        is_valid, error_msg = pipeline.validate(check_files=True)
        if not is_valid:
            QMessageBox.critical(self, "Validation Error", error_msg)
            return
            
        import tempfile
        import os
        from src.model.job_exporter import JobExporter
        
        # Export temporary json
        fd, temp_path = tempfile.mkstemp(suffix='.eegpipe', text=True)
        os.close(fd)
        
        try:
            pipeline.save(temp_path)
            
            eeglab_path = self.app_settings.get_eeglab_path()
            
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
                src_matlab = os.path.abspath(os.path.join(base_dir, '..', '..', '..', 'src', 'matlab'))
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                src_matlab = os.path.abspath(os.path.join(base_dir, '..', 'matlab'))
            
            # Construct MATLAB command
            if eeglab_path:
                cmd_inner = f"addpath('{eeglab_path}'); eeglab nogui; addpath('{src_matlab}'); run_pipeline('{temp_path}'); exit;"
            else:
                cmd_inner = f"addpath('{src_matlab}'); run_pipeline('{temp_path}'); exit;"
                
            self.execution_dialog = ExecutionDialog(self)
            self.execution_dialog.start_execution(matlab_path, ["-batch", cmd_inner])
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start MATLAB execution: {e}")


    def export_matlab_script(self):
        pipeline = self.canvas.to_pipeline()
        pipeline.settings = self.pipeline_settings
        is_valid, error_msg = pipeline.validate(check_files=True)
        
        if not is_valid:
            QMessageBox.critical(self, "Validation Error", error_msg)
            return

        filename, _ = QFileDialog.getSaveFileName(self, "Export MATLAB Script", "", "MATLAB Files (*.m)")
        if not filename:
            return

        from src.matlab.codegen import CodeGenerator
        generator = CodeGenerator(pipeline)
        try:
            generated_files = generator.generate(filename)
            msg = "Generated MATLAB scripts:\n" + "\n".join(generated_files)
            QMessageBox.information(self, "Success", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate MATLAB script:\n{e}")

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
        pipeline.settings = self.pipeline_settings
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
                
            filename, _ = QFileDialog.getSaveFileName(self, "Save Pipeline", default_dir, "Pipeline Files (*.eegpipe);;JSON Files (*.json)")
            
        if filename:
            # Auto-append .json if user didn't type an extension
            if not os.path.splitext(filename)[1]:
                filename += '.eegpipe'
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

        filename, _ = QFileDialog.getOpenFileName(self, "Open Pipeline", default_dir, "Pipeline Files (*.eegpipe *.json)")
        if filename:
            try:
                from src.model.pipeline import Pipeline
                pipeline = Pipeline.load(filename)
                self.canvas.from_pipeline(pipeline)
                self.pipeline_settings = pipeline.settings
                self.settings_widget.set_settings(self.pipeline_settings)
                self.current_file = filename
                self.unsaved_changes = False
                self.update_title()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not load file: {e}")

    def _create_undo_icon(self):
        from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QPainterPath, QIcon, QPolygonF
        from PyQt6.QtCore import Qt, QRectF, QPointF
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor(50, 50, 50), 2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        path = QPainterPath()
        rect = QRectF(6, 6, 12, 12)
        # Start bottom-right (-30 deg), sweep to left (180 deg)
        path.arcMoveTo(rect, -30)
        path.arcTo(rect, -30, 210)
        painter.drawPath(path)
        
        # Draw solid arrowhead pointing down at the left end (180 deg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(50, 50, 50))
        # Triangle pointing down
        head = QPolygonF([QPointF(6, 17), QPointF(2, 10), QPointF(10, 10)])
        painter.drawPolygon(head)
        
        painter.end()
        return QIcon(pixmap)

    def _create_redo_icon(self):
        from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QPainterPath, QIcon, QPolygonF
        from PyQt6.QtCore import Qt, QRectF, QPointF
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor(50, 50, 50), 2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        path = QPainterPath()
        rect = QRectF(6, 6, 12, 12)
        # Start bottom-left (210 deg), sweep to right (0 deg)
        path.arcMoveTo(rect, 210)
        path.arcTo(rect, 210, -210)
        painter.drawPath(path)
        
        # Arrowhead pointing down at the right end (0 deg)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(50, 50, 50))
        # Triangle pointing down
        head = QPolygonF([QPointF(18, 17), QPointF(14, 10), QPointF(22, 10)])
        painter.drawPolygon(head)
        
        painter.end()
        return QIcon(pixmap)

    def _create_export_icon(self):
        from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QIcon, QPolygonF
        from PyQt6.QtCore import Qt, QPointF
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor(50, 50, 50), 2)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        painter.setPen(pen)
        # Box with top opening
        painter.drawPolyline(QPolygonF([QPointF(8, 8), QPointF(4, 8), QPointF(4, 20), QPointF(20, 20), QPointF(20, 8), QPointF(16, 8)]))
        
        # Arrow pointing UP
        painter.drawLine(12, 14, 12, 4)
        painter.setBrush(QColor(50, 50, 50))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([QPointF(12, 2), QPointF(8, 7), QPointF(16, 7)]))
        
        painter.end()
        return QIcon(pixmap)

    def _create_run_icon(self):
        from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor, QPolygonF, QIcon
        from PyQt6.QtCore import Qt, QPointF
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#2ecc71"))) # Green
        
        polygon = QPolygonF([QPointF(6, 4), QPointF(20, 12), QPointF(6, 20)])
        painter.drawPolygon(polygon)
        painter.end()
        return QIcon(pixmap)
