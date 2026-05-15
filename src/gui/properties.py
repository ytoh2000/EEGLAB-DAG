from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, 
                             QLabel, QComboBox, QCheckBox, QWidget, QHBoxLayout, QFileDialog, 
                             QTabWidget, QTextEdit, QSizePolicy, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QPushButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDoubleValidator, QIntValidator, QFont

class PropertiesDialog(QDialog):
    def __init__(self, node_type, current_params, step_def, parent=None, user_note='', readonly=False, disabled_params=None, save_output=False, transfer_inputs=None, pipeline_settings=None):
        super().__init__(parent)
        self.readonly = readonly
        self.disabled_params = disabled_params or []
        self.save_output = save_output
        self.transfer_inputs = transfer_inputs or {}
        self._canvas_parent = parent  # Keep reference to canvas to read live pipeline_settings
        self.pipeline_settings = pipeline_settings or {}
        self._initializing = True
        self.setWindowTitle(f"Properties: {node_type}")
        self.resize(450, 500)
        
        self.save_path_edit = None
        self.save_path_picker = None
        self.plot_filename_edit = None  # For visualization nodes: the filename QLineEdit
        self.use_pipeline_cb = None
        
        self.node_type = node_type
        self.params = current_params.copy()
        self.step_def = step_def or {}
        self.inputs = {}
        
        layout = QVBoxLayout(self)
        
        # dynamic form generation
        self._generate_form(layout)
        
        # Save output option (only if node has dataset output and isn't already a save node)
        self.save_cb = None
        outputs = self.step_def.get('outputs', [])
        has_dataset_output = any(o.get('type') == 'dataset' for o in outputs)
        is_already_save_node = self.step_def.get('function') == 'pop_saveset'
        
        if has_dataset_output and not is_already_save_node:
            self.save_cb = QCheckBox("Save output after this step")
            self.save_cb.setChecked(self.save_output)
            self.save_cb.setToolTip("Automatically save the EEG dataset to the output folder after this processing step.")
            self.save_cb.setStyleSheet("margin-left: 5px; margin-top: 5px; margin-bottom: 5px; font-weight: bold; color: #2E7D32;")
            layout.addWidget(self.save_cb)
        
        # Note field
        note_layout = QFormLayout()
        note_label = QLabel("Note")
        note_label.setToolTip("Add a personal annotation to this node")
        self.note_edit = QTextEdit()
        self.note_edit.setPlainText(user_note)
        self.note_edit.setPlaceholderText("Add a note…")
        self.note_edit.setMaximumHeight(70)
        note_layout.addRow(note_label, self.note_edit)
        layout.addLayout(note_layout)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        
        # Initial validation check
        self._validate_all()
        
    def _generate_form(self, layout):
        inputs_def = self.step_def.get('inputs', [])

        parameters = []

        for inp in inputs_def:
            # Skip implicit inputs like 'EEG'
            if inp.get('type') == 'dataset':
                continue
            parameters.append(inp)

        # Always use a tab widget so the Help tab is accessible
        tabs = QTabWidget()
        layout.addWidget(tabs)
        self._tabs = tabs

        # Parameters tab
        param_widget = QWidget()
        param_layout = QFormLayout(param_widget)
        param_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        param_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        param_layout.setContentsMargins(8, 8, 8, 8)

        if self.readonly:
            info_label = QLabel("These parameters are automatically managed by the connected source node.")
            info_label.setStyleSheet("color: #D32F2F; font-weight: bold; margin-bottom: 5px;")
            info_label.setWordWrap(True)
            param_layout.addRow(info_label)
            param_widget.setEnabled(False)

        is_importer = self.step_def.get('function') in ['pop_loadset', 'pop_mffimport', 'pop_fileio', 'pop_biosig']
        if is_importer:
            self.importer_files = self.params.get('file_paths', [])
            select_btn = QPushButton("Select File(s)...")
            select_btn.clicked.connect(self._on_select_importer_files)
            param_layout.addRow(select_btn)

        if parameters:
            for inp in parameters:
                self._create_input_widget(inp, param_layout)
        else:
            param_layout.addRow(QLabel("No parameters."))

        is_saver = self.step_def.get('function') == 'pop_saveset'
        if is_saver:
            self.auto_suffix_cb = QCheckBox("Use automatic suffix-based filename")
            self.auto_suffix_cb.setChecked(not bool(self.params.get('filename', '')))
            self.auto_suffix_cb.toggled.connect(self._on_auto_suffix_toggled)
            # Insert at the top of parameters
            if is_importer:
                param_layout.insertRow(1, self.auto_suffix_cb)
            else:
                param_layout.insertRow(0, self.auto_suffix_cb)
            self._on_auto_suffix_toggled(self.auto_suffix_cb.isChecked())
            
        if self.use_pipeline_cb and self.save_path_edit:
            self._on_use_global_savepath_toggled(self.use_pipeline_cb.isChecked())
            
        self._initializing = False
        tabs.addTab(param_widget, "Parameters")

        # Help tab
        help_widget = QWidget()
        help_layout = QVBoxLayout(help_widget)
        help_layout.setContentsMargins(8, 8, 8, 8)

        help_text = self.step_def.get('help_text', '')
        help_display = QTextEdit()
        help_display.setReadOnly(True)

        if help_text:
            help_display.setFont(QFont('Consolas', 12))
            help_display.setPlainText(help_text)
        else:
            help_display.setPlainText('Not available')

        help_layout.addWidget(help_display)
        tabs.addTab(help_widget, "Help")

    def _create_input_widget(self, inp, layout):
        name = inp.get('name')
        inp_type = inp.get('type', 'string')
        desc = inp.get('description', '')
        required = inp.get('required', False)
        default = inp.get('default')
        can_disable = inp.get('can_disable', False)
        accepts_transfer = inp.get('accepts_transfer', False)
        
        # Replace underscores with spaces and use title case for a cleaner UI
        label_text = name.replace('_', ' ').title() if name else ""
        
        label = QLabel(label_text)
        label.setToolTip(desc)
        
        val = self.params.get(name, default)

        # Special handling for use_global_savepath toggle
        if name == 'use_global_savepath':
            cb = QCheckBox()
            cb.setChecked(bool(val))
            cb.toggled.connect(self._on_use_global_savepath_toggled)
            self.use_pipeline_cb = cb
            layout.addRow(label, cb)
            self.inputs[name] = {'widget': cb, 'type': 'bool', 'can_disable': False, 'label': label}
            # Trigger path update — save_path_edit is already set (save_as/filepath comes first in JSON)
            if self.save_path_edit:
                self._on_use_global_savepath_toggled(bool(val))
            return
        
        # Check if this parameter is receiving a transfer connection
        if accepts_transfer and name in self.transfer_inputs:
            transfer_info = self.transfer_inputs[name]
            field = transfer_info.get('field', 'chanlocs')
            source_label = transfer_info.get('source_label', 'Transfer')
            
            # Render as a read-only styled label
            transfer_label = QLabel(f"\u2190 EEG.{field} from [{source_label}]")
            transfer_label.setStyleSheet(
                "QLabel { background-color: #E3F2FD; color: #1565C0; "
                "padding: 4px 8px; border: 1px solid #90CAF9; border-radius: 4px; "
                "font-weight: bold; }"
            )
            transfer_label.setToolTip(f"This parameter receives EEG.{field} from the connected Transfer node. Remove the transfer edge to edit manually.")
            
            # Store as a special transfer widget so get_params preserves the marker value
            self.inputs[name] = {'widget': transfer_label, 'type': 'transfer', 'can_disable': False, 'label': label}
            layout.addRow(label, transfer_label)
            return
        
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
            if name == 'save_as':
                self.save_path_edit = widget.line_edit
                self.save_path_picker = widget
        
        elif inp_type == 'directory':
             widget = FilePickerWidget(val if not is_off else "", "dir")
             if name == 'filepath':
                 self.save_path_edit = widget.line_edit
                 self.save_path_picker = widget

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

        elif inp_type == 'key_value_list':
            if not isinstance(val, list):
                val = []
            allowed_keys = inp.get('allowed_keys', {})
            widget = KeyValueListWidget(val, allowed_keys)

        else: # string, float, int
            display_val = val if not is_off else default
            widget = QLineEdit(str(display_val) if display_val is not None else "")
            widget.setPlaceholderText(str(default) if default is not None else "")
            
            # Track the filename field for visualization nodes
            if name == 'filename' and self.step_def.get('type') == 'visualization':
                self.plot_filename_edit = widget
            
            # Add validators for numeric types
            if inp_type == 'float':
                widget.setValidator(QDoubleValidator())
                widget.textChanged.connect(self._validate_all)
            elif inp_type in ['int', 'integer']:
                widget.setValidator(QIntValidator())
                widget.textChanged.connect(self._validate_all)
        
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
            self.inputs[name] = {'widget': widget, 'type': inp_type, 'checkbox': enable_cb, 'can_disable': True, 'label': label}
            final_widget = container
        else:
            self.inputs[name] = {'widget': widget, 'type': inp_type, 'can_disable': False, 'label': label}

        if name in self.disabled_params:
            final_widget.setEnabled(False)
            label.setEnabled(False)

        layout.addRow(label, final_widget)

    def _get_pipeline_settings(self):
        """Return live pipeline_settings from the parent canvas if available, else cached copy."""
        if self._canvas_parent and hasattr(self._canvas_parent, 'pipeline_settings'):
            return self._canvas_parent.pipeline_settings
        return self.pipeline_settings

    def _on_use_global_savepath_toggled(self, checked):
        if not self.save_path_edit:
            return

        settings = self._get_pipeline_settings()
        if checked:
            out_folder = settings.get('global_savepath', '')
            import os
            is_plot = self.step_def.get('type') == 'visualization'
            
            # For the UI, show a clean BIDS-aware relative path
            # The actual absolute path resolution happens in MATLAB/Codegen
            if is_plot:
                ui_path = "[Global]/derivatives/DAG/sub-XX/ses-YY/figures/"
            else:
                ui_path = "[Global]/derivatives/DAG/sub-XX/ses-YY/eeg/"
            
            self.save_path_edit.setText(ui_path)
            self.save_path_edit.setReadOnly(True)
            self.save_path_edit.setStyleSheet("background-color: #F5F5F5; color: #1565C0; border: 1px solid #90CAF9; font-weight: bold;")
            if self.save_path_picker:
                self.save_path_picker.btn.setEnabled(False)
            
            # Autofill filename using BIDS naming convention
            if self.plot_filename_edit:
                if is_plot:
                    # BIDS-like filename for plots
                    ext = ".png"
                    default_fname = "sub-XX_ses-YY_task-ZZ_plot" + ext
                else:
                    # BIDS derivative filename for EEG
                    ext = ".set"
                    # Try to get a suffix from the node definition (e.g., 'preproc', 'ica')
                    node_suffix = self.step_def.get('suffix', 'processed')
                    default_fname = f"sub-XX_ses-YY_task-ZZ_desc-{node_suffix}_eeg{ext}"
                
                self.plot_filename_edit.setText(default_fname)
                self.plot_filename_edit.setReadOnly(True)
                self.plot_filename_edit.setStyleSheet("background-color: #F5F5F5; color: #1565C0; border: 1px solid #90CAF9; font-weight: bold;")
            
            if not out_folder:
                self.save_path_edit.setPlaceholderText("Please set Global Savepath in Pipeline Settings first")
        else:
            self.save_path_edit.setReadOnly(False)
            self.save_path_edit.setStyleSheet("")
            if not self._initializing:
                self.save_path_edit.setText("")
            if self.save_path_picker:
                self.save_path_picker.btn.setEnabled(True)
            self.save_path_edit.setPlaceholderText("Select path…")
            
            if self.plot_filename_edit:
                self.plot_filename_edit.setReadOnly(False)
                self.plot_filename_edit.setStyleSheet("")
                if not self._initializing:
                    self.plot_filename_edit.setText("")

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
            
            # Preserve transfer marker value (read-only label, not editable)
            if w_type == 'transfer':
                new_params[name] = self.params.get(name, '')
                continue
            
            if isinstance(widget, QLineEdit):
                text_val = widget.text()
                if text_val == "":
                    new_params[name] = text_val
                elif w_type in ['int', 'integer']:
                    try:
                        new_params[name] = int(text_val)
                    except ValueError:
                        new_params[name] = text_val
                elif w_type == 'float':
                    try:
                        new_params[name] = float(text_val)
                    except ValueError:
                        new_params[name] = text_val
                else:
                    new_params[name] = text_val
            elif isinstance(widget, QComboBox):
                new_params[name] = widget.currentText()
            elif isinstance(widget, QCheckBox):
                 new_params[name] = widget.isChecked()
            elif isinstance(widget, FilePickerWidget):
                new_params[name] = widget.get_path()
            elif isinstance(widget, FileListWidget):
                new_params[name] = widget.get_files()
            elif isinstance(widget, KeyValueListWidget):
                new_params[name] = widget.get_data()
                
        if hasattr(self, 'importer_files') and self.importer_files:
            new_params['file_paths'] = self.importer_files
            
        return new_params

    def _on_auto_suffix_toggled(self, checked):
        if 'filename' in self.inputs:
            widget = self.inputs['filename']['widget']
            label = self.inputs['filename']['label']
            if isinstance(widget, QLineEdit):
                widget.setEnabled(not checked)
                label.setEnabled(not checked)
                if checked:
                    widget.setText("")

    def _on_select_importer_files(self):
        import os
        filter_str = "All Files (*)"
        func = self.step_def.get('function')
        if func == 'pop_loadset':
            filter_str = "EEGLAB Dataset (*.set);;All Files (*)"
        elif func == 'pop_mffimport':
            filter_str = "MFF Files (*.mff);;All Files (*)"
            
        paths, _ = QFileDialog.getOpenFileNames(self, "Select Data Files", filter=filter_str)
        if paths:
            self.importer_files = paths
            first_file = paths[0]
            if func == 'pop_loadset':
                if 'filename' in self.inputs:
                    picker = self.inputs['filename']['widget']
                    if hasattr(picker, 'line_edit'):
                        picker.line_edit.setText(os.path.basename(first_file))
                    else:
                        picker.setText(os.path.basename(first_file))
                if 'filepath' in self.inputs:
                    # widget is FilePickerWidget, which has line_edit
                    picker = self.inputs['filepath']['widget']
                    if hasattr(picker, 'line_edit'):
                        picker.line_edit.setText(os.path.dirname(first_file))
            elif func == 'pop_mffimport':
                if 'mffFile' in self.inputs:
                    picker = self.inputs['mffFile']['widget']
                    if hasattr(picker, 'line_edit'):
                        picker.line_edit.setText(first_file)
            elif func in ['pop_fileio', 'pop_biosig']:
                if 'filename' in self.inputs:
                    picker = self.inputs['filename']['widget']
                    if hasattr(picker, 'line_edit'):
                        picker.line_edit.setText(first_file)
            self._validate_all()

    def _validate_all(self):
        """Check all validated fields; disable OK and highlight invalid ones."""
        all_valid = True
        for name, data in self.inputs.items():
            widget = data['widget']
            if isinstance(widget, QLineEdit) and widget.validator():
                # Skip validation for disabled optional fields
                if data.get('can_disable') and data.get('checkbox') and not data['checkbox'].isChecked():
                    widget.setStyleSheet('')
                    continue
                text = widget.text()
                if text == '':
                    # Empty is ok (will use default)
                    widget.setStyleSheet('')
                    continue
                state = widget.validator().validate(text, 0)[0]
                if state != QDoubleValidator.State.Acceptable:
                    widget.setStyleSheet('QLineEdit { border: 2px solid #EF5350; }')
                    all_valid = False
                else:
                    widget.setStyleSheet('QLineEdit { border: 1px solid #66BB6A; }')
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(all_valid)

import os
import glob

class KeyValueListWidget(QWidget):
    def __init__(self, initial_data=None, allowed_keys=None, parent=None):
        super().__init__(parent)
        self.allowed_keys = allowed_keys or {} # key -> description
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setMaximumHeight(150)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Row")
        self.add_btn.setStyleSheet("background-color: #E8F5E9; color: #2E7D32; font-weight: bold;")
        self.add_btn.clicked.connect(lambda: self.add_row())
        btn_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton("- Remove Selected")
        self.remove_btn.setStyleSheet("background-color: #FFEBEE; color: #C62828;")
        self.remove_btn.clicked.connect(self.remove_row)
        btn_layout.addWidget(self.remove_btn)
        
        layout.addLayout(btn_layout)
        
        # Load initial data
        if initial_data and isinstance(initial_data, list):
            for pair in initial_data:
                if isinstance(pair, list) and len(pair) == 2:
                    self.add_row(pair[0], pair[1])

    def add_row(self, key="", value=""):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # Key widget: ComboBox if allowed_keys exists, else LineEdit
        if self.allowed_keys:
            key_widget = QComboBox()
            key_widget.setEditable(True)
            sorted_keys = sorted(self.allowed_keys.keys())
            key_widget.addItems(sorted_keys)
            if key:
                key_widget.setCurrentText(str(key))
            else:
                key_widget.setCurrentIndex(-1)
            
            # Show tooltip if a known key is selected
            def update_tooltip(idx):
                k = key_widget.currentText()
                if k in self.allowed_keys:
                    key_widget.setToolTip(self.allowed_keys[k])
            
            key_widget.currentIndexChanged.connect(update_tooltip)
            key_widget.editTextChanged.connect(lambda: update_tooltip(0))
            self.table.setCellWidget(row, 0, key_widget)
        else:
            self.table.setItem(row, 0, QTableWidgetItem(str(key)))
            
        val_item = QTableWidgetItem(str(value))
        if value == "" and self.allowed_keys and key in self.allowed_keys:
            # Maybe use a placeholder? items don't support placeholders well
            pass
        self.table.setItem(row, 1, val_item)

    def remove_row(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self.table.removeRow(current_row)

    def get_data(self):
        data = []
        for r in range(self.table.rowCount()):
            key_widget = self.table.cellWidget(r, 0)
            if isinstance(key_widget, QComboBox):
                k = key_widget.currentText().strip()
            else:
                k_item = self.table.item(r, 0)
                k = k_item.text().strip() if k_item else ""
                
            v_item = self.table.item(r, 1)
            v_str = v_item.text().strip() if v_item else ""
            
            if k:
                # Try to parse value as number if possible
                try:
                    if '.' in v_str:
                        v_parsed = float(v_str)
                    else:
                        v_parsed = int(v_str)
                except ValueError:
                    # Keep as string or bool
                    if v_str.lower() == 'true': v_parsed = True
                    elif v_str.lower() == 'false': v_parsed = False
                    elif v_str.lower() == 'on': v_parsed = True
                    elif v_str.lower() == 'off': v_parsed = False
                    else: v_parsed = v_str
                
                data.append([k, v_parsed])
        return data

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
        self.line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
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
