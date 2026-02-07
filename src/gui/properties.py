from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QLabel, QComboBox, QCheckBox, QWidget, QHBoxLayout, QFileDialog
from PyQt6.QtCore import Qt

class PropertiesDialog(QDialog):
    def __init__(self, node_type, current_params, step_def, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Properties: {node_type}")
        self.resize(400, 300)
        
        self.node_type = node_type
        self.params = current_params.copy()
        self.step_def = step_def or {}
        self.inputs = {}
        
        layout = QVBoxLayout(self)
        
        # Scrollable area could be added here if needed, but simple layout for now
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget) # Changed to VBox to stack Required / Button / Optional
        layout.addWidget(form_widget)
        
        # dynamic form generation
        self._generate_form(form_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def _generate_form(self, layout):
        inputs_def = self.step_def.get('inputs', [])
        
        if not inputs_def:
            layout.addWidget(QLabel("No parameters available."))
            return

        required_inputs = []
        optional_inputs = []

        for inp in inputs_def:
            # Skip implicit inputs like 'EEG'
            if inp.get('type') == 'dataset':
                continue
            if inp.get('required', False):
                required_inputs.append(inp)
            else:
                optional_inputs.append(inp)

        # 1. Required Parameters
        if required_inputs:
            req_group = QWidget()
            req_layout = QFormLayout(req_group)
            req_layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(req_group)
            
            for inp in required_inputs:
                self._create_input_widget(inp, req_layout)

        # 2. Optional Parameters (Collapsible)
        if optional_inputs:
            from PyQt6.QtWidgets import QPushButton, QFrame
            
            self.toggle_btn = QPushButton("Show Advanced Options")
            self.toggle_btn.setCheckable(True)
            self.toggle_btn.setChecked(False)
            self.toggle_btn.clicked.connect(self._toggle_optional)
            layout.addWidget(self.toggle_btn)
            
            self.optional_container = QWidget()
            self.optional_container.setVisible(False)
            opt_layout = QFormLayout(self.optional_container)
            opt_layout.setContentsMargins(0, 5, 0, 0)
            
            # Add a visual frame/border
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            frame_layout = QVBoxLayout(frame)
            frame_layout.addWidget(self.optional_container)
            layout.addWidget(frame)
            
            for inp in optional_inputs:
                self._create_input_widget(inp, opt_layout)

    def _toggle_optional(self):
        visible = self.toggle_btn.isChecked()
        self.optional_container.setVisible(visible)
        self.toggle_btn.setText("Hide Advanced Options" if visible else "Show Advanced Options")
        # Resize dialog to fit content
        # self.adjustSize() 

    def _create_input_widget(self, inp, layout):
        name = inp.get('name')
        inp_type = inp.get('type', 'string')
        desc = inp.get('description', '')
        required = inp.get('required', False)
        default = inp.get('default')
        can_disable = inp.get('can_disable', False)
        
        # Capitalize first letter only, preserve rest of the string
        label_text = name[0].upper() + name[1:] if name else ""
        
        label = QLabel(label_text)
        label.setToolTip(desc)
        
        val = self.params.get(name, default)
        
        # Helper to determine if the parameter is currently "off"
        is_off = False
        if can_disable:
            # Check if val indicates "off"
            if str(val).lower() in ['off', '-1']:
                is_off = True

        widget = None
        
        if inp_type == 'enum':
            widget = QComboBox()
            options = inp.get('options', [])
            widget.addItems(options)
            # If enabled, set value. If off, maybe set to default or keep index 0, but disable it.
            target_val = val if not is_off else default
            if target_val in options:
                widget.setCurrentText(str(target_val))
        
        elif inp_type == 'filepath':
            widget = FilePickerWidget(val if not is_off else "", "file")
        
        elif inp_type == 'directory':
             widget = FilePickerWidget(val if not is_off else "", "dir")

        elif inp_type == 'bool':
             widget = QCheckBox()
             # If off, what does it mean for a bool? Probably false.
             # But 'can_disable' is mostly for numeric/string params that can be 'off'.
             # Let's assume bool params don't have can_disable for now or handle gracefully.
             check_val = val if not is_off else default
             widget.setChecked(str(check_val).lower() in ('true', '1', 'on'))

        elif inp_type == 'filelist':
            # initial value should be a list
            if not isinstance(val, list):
                val = []
            widget = FileListWidget(val)

        else: # string, float, int
            display_val = val if not is_off else default
            widget = QLineEdit(str(display_val) if display_val is not None else "")
            widget.setPlaceholderText(str(default) if default is not None else "")
        
        widget.setToolTip(desc)

        final_widget = widget
        
        # If can_disable, wrap in a container with a checkbox
        if can_disable:
            container = QWidget()
            h_layout = QHBoxLayout(container)
            h_layout.setContentsMargins(0, 0, 0, 0)
            
            enable_cb = QCheckBox()
            enable_cb.setChecked(not is_off)
            enable_cb.setToolTip(f"Enable/Disable {name}")
            
            # Connect checkbox state to widget enablement
            widget.setEnabled(not is_off) # Initial state
            enable_cb.toggled.connect(widget.setEnabled)
            
            h_layout.addWidget(enable_cb)
            h_layout.addWidget(widget)
            
            # Store both in inputs so we can retrieve state later
            self.inputs[name] = {'widget': widget, 'type': inp_type, 'checkbox': enable_cb, 'can_disable': True}
            final_widget = container
        else:
            self.inputs[name] = {'widget': widget, 'type': inp_type, 'can_disable': False}

        layout.addRow(label, final_widget)

    def get_params(self):
        new_params = {}
        for name, data in self.inputs.items():
            widget = data['widget']
            w_type = data['type']
            can_disable = data.get('can_disable', False)
            checkbox = data.get('checkbox')
            
            # If modifiable and unchecked, return 'off'
            if can_disable and checkbox and not checkbox.isChecked():
                new_params[name] = 'off'
                continue # Skip value retrieval
            
            if isinstance(widget, QLineEdit):
                new_params[name] = widget.text()
            elif isinstance(widget, QComboBox):
                new_params[name] = widget.currentText()
            elif isinstance(widget, QCheckBox):
                 new_params[name] = widget.isChecked()
            elif isinstance(widget, FilePickerWidget):
                new_params[name] = widget.get_path()
            elif isinstance(widget, FileListWidget):
                new_params[name] = widget.get_files()
                
        return new_params

from PyQt6.QtWidgets import QPushButton, QTextEdit
import os
import glob

class FileListWidget(QWidget):
    def __init__(self, initial_files=None, parent=None):
        super().__init__(parent)
        self.files = initial_files if initial_files else []
        self.selected_folder = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        # Row 1: Add Files
        row1 = QHBoxLayout()
        self.btn_file = QPushButton("Add File(s)...")
        self.btn_file.clicked.connect(self.add_files)
        row1.addWidget(self.btn_file)
        layout.addLayout(row1)
        
        # Row 2: Add Folder, Ext, Search
        row2 = QHBoxLayout()
        self.btn_folder = QPushButton("Add Folder...")
        self.btn_folder.clicked.connect(self.pick_folder)
        row2.addWidget(self.btn_folder)
        
        self.ext_input = QLineEdit("*.set")
        self.ext_input.setPlaceholderText("Ext")
        self.ext_input.setFixedWidth(70)
        self.ext_input.setToolTip("Filter extension (e.g. *.set)")
        row2.addWidget(self.ext_input)
        
        self.btn_search = QPushButton("Search")
        self.btn_search.clicked.connect(self.search_files)
        self.btn_search.setEnabled(False)
        row2.addWidget(self.btn_search)
        
        layout.addLayout(row2)
        
        # Row 3: Count + Clear
        row3 = QHBoxLayout()
        self.info_label = QLabel("0 files selected")
        row3.addWidget(self.info_label)
        
        row3.addStretch()
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_files)
        self.btn_clear.setFixedWidth(60)
        row3.addWidget(self.btn_clear)
        
        layout.addLayout(row3)
        
        # Preview
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(80)
        layout.addWidget(self.preview)
        
        self.update_display()
        
    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", filter=self.ext_input.text())
        if paths:
            self.files.extend(paths)
            self.files = sorted(list(set(self.files))) # Dedup and sort
            self.update_display()
            
    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder:
            self.selected_folder = folder
            self.btn_folder.setText("Folder Selected")
            self.btn_folder.setToolTip(folder)
            self.btn_search.setEnabled(True)
            # Optional: auto-search? User requested separate Search button, so we wait.

    def search_files(self):
        if not self.selected_folder:
            return
            
        ext = self.ext_input.text()
        if not ext:
            ext = "*"
            
        search_pattern = os.path.join(self.selected_folder, "**", ext)
        found = glob.glob(search_pattern, recursive=True)
        
        if found:
            self.files.extend(found)
            self.files = sorted(list(set(self.files)))
            self.update_display()
                
    def clear_files(self):
        self.files = []
        self.selected_folder = None
        self.btn_folder.setText("Add Folder...")
        self.btn_folder.setToolTip("")
        self.btn_search.setEnabled(False)
        self.update_display()
        
    def update_display(self):
        count = len(self.files)
        self.info_label.setText(f"{count} files selected")
        
        preview_text = ""
        display_limit = 5
        for i, f in enumerate(self.files):
            if i >= display_limit:
                preview_text += f"... and {count - display_limit} more"
                break
            preview_text += f"{os.path.basename(f)}\n"
            
        self.preview.setText(preview_text)
        
    def get_files(self):
        return self.files

class FilePickerWidget(QWidget):
    def __init__(self, initial_path, mode="file", parent=None):
        super().__init__(parent)
        self.mode = mode
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.line_edit = QLineEdit(str(initial_path) if initial_path else "")
        layout.addWidget(self.line_edit)
        
        # Better to use button
        self.btn = QPushButton("...")
        self.btn.setFixedWidth(30)
        self.btn.clicked.connect(self.pick_file)
        layout.addWidget(self.btn)
        
    def pick_file(self):
        if self.mode == "file":
            path, _ = QFileDialog.getOpenFileName(self, "Select File")
        else:
            path = QFileDialog.getExistingDirectory(self, "Select Directory")
            
        if path:
            self.line_edit.setText(path)
            
    def get_path(self):
        return self.line_edit.text()
