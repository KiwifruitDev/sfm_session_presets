# SFM Session Presets Script by KiwifruitDev
# https://github.com/KiwifruitDev/sfm_session_presets
# This software is licensed under the MIT License.
# MIT License
# 
# Copyright (c) 2026 KiwifruitDev
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import subprocess
import os
import sfm
import sfmApp
import json
import traceback
import _winreg as winreg
from vs import g_pDataModel as dm
from PySide import QtGui, QtCore, shiboken

_session_presets_version = "0.1"

def _session_presets_msg(msg):
    sfm.Msg("[SESSION PRESETS] " + msg + "\n")

def _session_presets_msg_box(msg, prefix, icon):
    _session_presets_msg(prefix + ": " + msg)
    msgBox = QtGui.QMessageBox()
    msgBox.setWindowTitle("Session Presets: " + prefix)
    msgBox.setText(msg)
    msgBox.setIcon(icon)
    msgBox.exec_()

def _session_presets_info_msg(msg):
    _session_presets_msg_box(msg, "Info", QtGui.QMessageBox.Information)

def _session_presets_error_msg(msg):
    _session_presets_msg_box(msg, "Error", QtGui.QMessageBox.Critical)

def _session_presets_warning_msg(msg):
    _session_presets_msg_box(msg, "Warning", QtGui.QMessageBox.Warning)

class PyCQEditorLowerBarWidget(QtGui.QWidget):
    # python implementation of CQEditorLowerBarWidget
    # modified to add a status label on the left side
    def __init__(self, parent=None):
        super(PyCQEditorLowerBarWidget, self).__init__(parent)
        self.setObjectName("PyCQEditorLowerBarWidget")
        self.setFixedHeight(48)
        # grow to fit width without padding, attach to bottom of parent
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        # layout should make buttons align to right
        self.layout = QtGui.QHBoxLayout(self)
        self.layout.setContentsMargins(16, 8, 6, 0)
        self.status_label = QtGui.QLabel(" ")
        self.layout.addWidget(self.status_label)
        # buttons appear 7 pixels from left or right edge with 8 pixel spacing between buttons
        # with top and bottom padding of 10 pixels
        #self.layout.setSpacing(8)
        self.layout.addStretch()
    def setStatusText(self, text):
        self.status_label.setText(text)
    def addButton(self, button):
        # set button size
        self.layout.addWidget(button)
        button.setFixedSize(80, 23)
    def paintEvent(self, event):
        super(PyCQEditorLowerBarWidget, self).paintEvent(event)
        painter = QtGui.QPainter(self)
        rect = self.rect()
        try:
            # Implementation of decompiled function FUN_1069d970
            x = rect.x()
            y = rect.y()
            width = rect.width()
            height = rect.height()
            
            iVar1 = 6 
            
            # Set pen and brush (equivalent of setPen and setBrush calls)
            painter.setPen(QtGui.QColor(104, 104, 104))  # Light gray for lines
            painter.setBrush(QtCore.Qt.NoBrush)
            
            # Draw line (equivalent of drawLines call)
            line_y = y + iVar1
            line = QtCore.QLine(x, line_y, x + width - 1, line_y)
            painter.drawLine(line)
            
            iVar1 += 1
            
            # Create linear gradient (equivalent of QLinearGradient constructor)
            gradient = QtGui.QLinearGradient(x, y + iVar1, x, height + 1)
            gradient.setColorAt(0.0, QtGui.QColor(54, 54, 54))   # Top color - lighter gray
            gradient.setColorAt(1.0, QtGui.QColor(40, 40, 40))   # Bottom color - darker gray
            
            # Create brush from gradient and fill rectangle
            gradient_brush = QtGui.QBrush(gradient)
            gradient_rect = QtCore.QRect(x, y + iVar1, width, height - iVar1)
            painter.fillRect(gradient_rect, gradient_brush)
            
        except Exception as e:
            # Fallback: draw a simple background
            painter.fillRect(rect, QtGui.QColor(64, 64, 64))

class SessionPresets:
    def __init__(self):
        _session_presets_msg("Initializing Session Presets Script v%s" % _session_presets_version)
        self.cwd = os.getcwd()
        self.descriptor = "SFM Session Presets v%s by KiwifruitDev" % _session_presets_version
        self.options_file = "session_presets.json"
        self.autoload_preset = "Blank"
        self.autoload_enabled = False
        self.autoload_preset_is_default = True
        self.custom_framerate_checkbox_state = False
        self.changing_preset = False
        self.version_changed = False
        self.default_presets = [
            {
                "name": "Blank",
                "description": "An empty session without a map or camera.\nThis is what SFM uses by default.",
            },
            {
                "name": "Stage",
                "description": "Uses the stage map with a camera in the center and key, bounce, fill, and rim lights set up.",
            },
            {
                "name": "Dark Room",
                "description": "Uses the dark_room map with a camera set up in the corner.",
            }
        ]
        self.custom_presets = []
        self.windowFlags = QtCore.Qt.Dialog | QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.MSWindowsFixedSizeDialogHint
        self.cwd = os.getcwd()
        self.dmxConvert = self.cwd + r"\bin\dmxconvert.exe"
        self.presets = []
        self.added_separator_header = False
        self.registry_path = r"Software\Valve\SourceFilmmaker\NewSessionWizard"
        self.load_options()
        self.new_session_menu(True)
        #self.add_window_actions()
        #self.open_startup_session()
    def load_dmx_file(self, path):
        # run dmxconvert to load a dmx file
        out = self.cwd + r"\_temp.dmx"
        # Delete out if it currently exists
        if os.path.isfile(out):
            os.remove(out)
        # Run dmxconvert using system call
        args = ["-i", path, "-oe", "keyvalues2", "-o", out]
        subprocess.Popen([self.dmxConvert] + args, shell=True).wait()
        # Check if out was created
        if os.path.isfile(out):
            return out
        return None
    def get_session_from_dmx(self, dmx_path):
        # Read the dmx file and extract the framerate from the dmElement "sessionSettings"
        try:
            with open(dmx_path, "r") as f:
                lines = f.readlines()
                # Search for "renderSettings" "DmElement" and read until we match a line containing "frameRate" "float" "
                # If a match is found, read framerate until we see a " -> return the framerate value
                # If we read a } before finding frameRate, return None
                in_active_clip = False
                clip_id = None
                clip_name = None
                for line in lines:
                    line = line.strip()
                    if not clip_name and not clip_id and '"activeClip" "element" "' in line:
                        # Get the clip ID
                        parts = line.split('"')
                        for i in range(len(parts)):
                            if parts[i] == "element" and i + 2 < len(parts):
                                clip_id = parts[i + 2].strip()
                    elif not clip_name and clip_id and '"id" "elementid" "' + clip_id + '"' in line:
                        in_active_clip = True
                    elif not clip_name and in_active_clip:
                        if '}' in line:
                            # End of activeClip
                            in_active_clip = False
                            clip_id = None
                        elif '"name" "string" "' in line:
                            # Extract clip name
                            parts = line.split('"')
                            for i in range(len(parts)):
                                if parts[i] == "string" and i + 2 < len(parts):
                                    clip_name = parts[i + 2].strip()
                                    in_active_clip = False
                    if clip_name:
                        return {
                            "name": clip_name
                        }
        except Exception as e:
            _session_presets_msg("Error reading dmx file %s: %s" % (dmx_path, e))
        return None
    def load_options(self):
        # JSON file format
        """
        {
            "options": {
                "autoload_preset": "Stage",
                "autoload_enabled": true,
                "autoload_preset_is_default": true,
                "version": "0.0"
            },
            "default_presets": [
                {
                    "name": "Blank",
                    "description": "An empty session without a map or camera.\nThis is what SFM uses by default."
                },
            ],
            "presets": [
                {
                    "name": "Custom Preset 1",
                    "order": 1,
                    "description": "A custom preset",
                    "path": "C:\\path\\to\\custom\\preset1.dmx"
                }
            ]
        }
        
        """
        options_path = os.path.join(self.cwd, self.options_file)
        if not os.path.isfile(options_path):
            self.save_options() # create default options file
        if os.path.isfile(options_path):
            try:
                with open(options_path, "r") as f:
                    data = json.load(f)
                options = data.get("options", {})
                self.autoload_preset = options.get("autoload_preset", "")
                self.autoload_enabled = options.get("autoload_enabled", False)
                self.autoload_preset_is_default = options.get("autoload_preset_is_default", False)
                default_presets = data.get("default_presets", [])
                if default_presets:
                    self.default_presets = default_presets
                presets = data.get("presets", [])
                for preset in presets:
                    append_preset = {
                        "name": preset.get("name", ""),
                        "order": preset.get("order", 0),
                        "description": preset.get("description", ""),
                        "path": preset.get("path", "")
                    }
                    self.presets.append(append_preset)
                _session_presets_msg("Loaded options from %s" % options_path)
            except Exception as e:
                _session_presets_msg("Error loading options from %s: %s" % (options_path, e))
    def save_options(self):
        options_path = os.path.join(self.cwd, self.options_file)
        data = {
            "options": {
                "autoload_preset": self.autoload_preset,
                "autoload_enabled": self.autoload_enabled,
                "autoload_preset_is_default": self.autoload_preset_is_default,
                "version": _session_presets_version
            },
            "default_presets": self.default_presets,
            "presets": self.presets
        }
        try:
            with open(options_path, "w") as f:
                json.dump(data, f, indent=4)
            _session_presets_msg("Saved options to %s" % options_path)
        except Exception as e:
            _session_presets_msg("Error saving options to %s: %s" % (options_path, e))
    def add_window_actions(self):
        # Adds a window action to File menu, taken from https://steamcommunity.com/sharedfiles/filedetails/?id=562830725
        main_window = sfmApp.GetMainWindow()
        for widget in main_window.children():
            if isinstance(widget, QtGui.QMenuBar):
                menu_bar = widget
                break
        for menu_item in menu_bar.actions():
            if menu_item.text() == 'File':
                file_menu = menu_item.menu()
                break
        # Replace New button with our own (ctrl+N shortcut too)
        new_action = QtGui.QAction("New", main_window)
        new_action.setShortcut(QtGui.QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self.new_session_menu)
        file_menu.insertAction(file_menu.actions()[0], new_action)
        file_menu.insertSeparator(file_menu.actions()[-2])
        self.defaults_menu = menu_bar.addMenu("Defaults") 
    def create_session(self, preset_index, framerate, filename, directory):
        print("Creating session with preset index %d, framerate %f, filename %s, directory %s" % (preset_index, framerate, filename, directory))
        default_preset = False
        preset_path = ""
        # Determine if preset_index is a default preset or custom preset
        if preset_index > 0:
            preset_index -= 1 # Adjust for header item
            if preset_index < len(self.default_presets):
                default_preset = True
                preset_path = self.default_presets[preset_index].get("name", "")
                print("Using default preset: %s" % preset_path)
            else:
                # It's a custom preset - calculate the actual custom preset index
                default_count = len(self.default_presets)
                custom_index = preset_index - default_count - 2 # -2 for header and separator
                if 0 <= custom_index < len(self.presets):
                    preset = self.presets[custom_index]
                    preset_path = preset.get("path", "")
        if default_preset:
            dmx_path = os.path.join(self.cwd, "workshop\\scripts\\default_startup_sessions.dmx")
            if os.path.isfile(dmx_path):
                print("Loading default startup sessions from %s" % dmx_path)
                sfmApp.OpenDocument(dmx_path)
                sfmApp.ProcessEvents()
                # Document loaded! First we'll update self.default_presets
                document = sfmApp.GetDocumentRoot()
                if document:
                    dm.SetUndoEnabled(False)
                    clipbin = getattr(document, "clipBin", None)
                    if clipbin:
                        clips = []
                        clipbin_array = clipbin.GetValue()
                        count = clipbin_array.Count()
                        found_element = None
                        print("Found %d clips in clipBin" % count)
                        for i in range(count):
                            print("Reading clip %d" % i)
                            try:
                                clip_element = clipbin_array[i]
                                name = clip_element.name.GetValue()
                                description = clip_element.text.GetValue()
                                clips.append({
                                    "name": name,
                                    "description": description
                                })
                                if name == preset_path:
                                    print("Found clip: %s" % name)
                                    found_element = clip_element
                            except Exception as e:
                                _session_presets_msg("Error reading clip from clipBin: %s" % e)
                        #clipbin.SetCount(0)
                        #clipbin_array.AddToTail(document.activeClip)
                        self.default_presets = clips
                        if found_element:
                            document.activeClip = found_element
                            # convert filename to char const *
                            filenameConverted = filename
                            document.activeClip.SetName(filenameConverted)
                            document.activeClip.text.SetValue("")
                        document.name = filename
                        document.settings.renderSettings.frameRate.SetValue(framerate)
                        self.save_options()
                        return
                    else:
                        _session_presets_error_msg("Failed to find clipBin in default startup sessions document.")
                else:
                    _session_presets_error_msg("Failed to open default startup sessions document.")
            else:
                _session_presets_error_msg("Default startup sessions file not found: %s" % dmx_path)
        elif preset_path:
            # Find preset in self.presets
            if preset_path and os.path.isfile(preset_path):
               sfmApp.OpenDocument(preset_path, forceSilent=False)
               return
            else:
                _session_presets_error_msg("Preset file not found: %s" % preset_path)
        sfmApp.NewDocument(filename=directory + "/" + filename + ".dmx", name=filename, framerate=framerate, defaultContent=True, forceSilent=False)
    def new_session_menu(self, startupWizard=False):
        self.custom_framerate_checkbox_state = False
        self.changing_preset = False
        # Create modal dialog
        dialog = QtGui.QDialog()
        dialog.setModal(True)
        if startupWizard:
            dialog.setFixedSize(800, 430)
        else:
            dialog.setFixedSize(800, 260)
        dialog.setWindowTitle(" ")
        dialog.setObjectName("NewSessionWizard")
        dialog.setWindowFlags(self.windowFlags)
        
        # Main layout
        main_layout = QtGui.QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header image
        header_label = QtGui.QLabel()
        header_label.setFixedSize(800, 75)
        header_pixmap = QtGui.QPixmap("tools:images/sfm/sfm_wizardheader.png")
        if not header_pixmap.isNull():
            header_label.setPixmap(header_pixmap.scaled(800, 75, QtCore.Qt.KeepAspectRatio))
        header_label.setStyleSheet("background-color: white;")
        main_layout.addWidget(header_label)
        
        # Content area
        content_widget = QtGui.QWidget()
        content_layout = QtGui.QVBoxLayout(content_widget)
        content_layout.setContentsMargins(6, 19, 6, 19)
        
        # Group box for New Session
        group_box = QtGui.QGroupBox(" New Session ")
        group_box.setFixedSize(788, 105)
        
        # Name text field
        name_label = QtGui.QLabel("Name:", group_box)
        name_label.move(10, 25)
        name_edit = QtGui.QLineEdit(group_box)
        name_edit.setGeometry(70, 20, 220, 23)
        name_edit.setText("session")

        # Preset label right of name field
        preset_label = QtGui.QLabel("Preset:", group_box)
        preset_label.move(310-7, 25)
        
        # Preset combo box (populated with default presets, a separator if there are custom presets, and then custom presets)
        preset_combo = QtGui.QComboBox(group_box)
        preset_combo.setGeometry(363, 20, 227, 23)

        self.custom_presets = []
        def rebuild_preset_combo(combo, append):
            combo.clear()
            self.custom_presets = []
            item_index = 0
            combo.insertItem(item_index, "Default Presets")
            combo.model().item(item_index).setEnabled(False)
            item_index += 1
            # Add default presets
            for preset in self.default_presets:
                preset_name = preset.get("name", "")
                item_index += 1
                if self.autoload_preset_is_default and preset_name == self.autoload_preset:
                    preset_name += append
                combo.insertItem(item_index, preset_name)
            # Add separator if there are custom presets
            for preset in self.presets:
                name = preset.get("name", "")
                if name:
                    self.custom_presets.append(name)
            if self.custom_presets:
                combo.insertSeparator(item_index)
                item_index += 1
                combo.insertItem(item_index, "Custom Presets")
                combo.model().item(item_index).setEnabled(False)
                item_index += 1
                for preset in self.custom_presets:
                    preset_name = preset
                    item_index += 1
                    if not self.autoload_preset_is_default and preset_name == self.autoload_preset:
                        preset_name = preset_name + append
                    combo.insertItem(item_index, preset_name)
            # Set current index to autoload preset
            default_count = len(self.default_presets)
            if self.autoload_preset_is_default:
                for i in range(1, default_count + 1):
                    text = combo.itemText(i)
                    if text.replace(append, "") == self.autoload_preset:
                        combo.setCurrentIndex(i)
                        return
            else:
                for i in range(default_count + 2, combo.count()):
                    text = combo.itemText(i)
                    if text.replace(append, "") == self.autoload_preset:
                        combo.setCurrentIndex(i)
                        return

        default_framerate_index = 7
        
        # Bottom button bar (PyCQEditorLowerBarWidget)
        lower_bar = PyCQEditorLowerBarWidget()
        lower_bar.setStatusText(self.descriptor)
        if startupWizard:
            lower_bar.setVisible(False)

        def preset_changed(index):
            self.changing_preset = True
            index = index - 1 # Adjust for header item
            description = ""
            
            # Check if it's a default preset (index < len(default_presets))
            if index < len(self.default_presets):
                description = self.default_presets[index].get("description", "")
            elif self.custom_presets:
                # It's a custom preset - calculate the actual custom preset index
                default_count = len(self.default_presets)
                custom_index = index - default_count - 2 # -2 for header and separator
                
                if 0 <= custom_index < len(self.presets):
                    preset = self.presets[custom_index]
                    description = preset.get("description", "")
            lower_bar.setStatusText(description)
            preset_combo.setToolTip(description)
            self.changing_preset = False
        preset_combo.currentIndexChanged.connect(preset_changed)
        rebuild_preset_combo(preset_combo, " (autoload)")
        
        # Browse button next to preset combo
        preset_edit_button = QtGui.QPushButton("Edit...", group_box)
        preset_edit_button.setGeometry(592+3, 20, 80, 23)
        
        # Directory text field and Browse... button
        dir_label = QtGui.QLabel("Directory:", group_box)
        dir_label.move(10, 53)
        dir_edit = QtGui.QLineEdit(group_box)
        if not startupWizard:
            dir_edit.setGeometry(70, 48, 620, 23)
        else:
            dir_edit.setGeometry(70, 48, 520, 23)
        dir_edit.setText("c:\\program files (x86)\\steam\\steamapps\\common\\sourcefilmmaker\\game\\usermod\\elements\\sessions")
        browse_button = QtGui.QPushButton("Browse...", group_box)
        browse_button.setGeometry(702, 48, 80, 23)
        if startupWizard:
            browse_button.setGeometry(596, 48, 80, 23)
        
        # Framerate dropdown field
        framerate_label = QtGui.QLabel("Framerate:", group_box)
        framerate_label.move(10, 81)
        framerate_combo = QtGui.QComboBox(group_box)
        framerate_combo.setGeometry(70, 76, 100, 23)
        framerate_edit = QtGui.QDoubleSpinBox(group_box)
        framerate_edit.setGeometry(70, 76, 100, 23)
        framerate_edit.setVisible(False)
        framerate_edit.setMinimum(1)
        framerate_edit.setMaximum(1000)
        framerate_edit.setDecimals(3)
        framerate_edit.setSingleStep(1)
        
        # Add framerate options with separators
        framerate_combo.insertItem(0, "23.976")
        framerate_combo.insertItem(1, "29.97")
        framerate_combo.insertItem(2, "59.94")
        framerate_combo.insertSeparator(3)
        framerate_combo.insertItem(4, "3")
        framerate_combo.insertItem(5, "6")
        framerate_combo.insertItem(6, "12")
        framerate_combo.insertItem(default_framerate_index, "24")
        framerate_combo.insertItem(8, "48")
        framerate_combo.insertItem(9, "72")
        framerate_combo.insertSeparator(10)
        framerate_combo.insertItem(11, "15")
        framerate_combo.insertItem(12, "25")
        framerate_combo.insertItem(13, "30")
        framerate_combo.insertItem(14, "60")
        
        framerate_combo.setMaxVisibleItems(framerate_combo.count())

        # Custom checkbox next to framerate dropdown
        custom_framerate_label = QtGui.QLabel("Custom", group_box)
        custom_framerate_label.setGeometry(205, 78, 50, 20)
        custom_framerate_checkbox = QtGui.QCheckBox(" ", group_box)
        custom_framerate_checkbox.setGeometry(182, 79, 70, 20)
        def toggle_custom_framerate(checked):
            if checked:
                framerate_combo.setVisible(False)
                framerate_edit.setVisible(True)
                # Set text to current combo value
                framerate_edit.setValue(float(framerate_combo.currentText()))
            else:
                framerate_combo.setVisible(True)
                framerate_edit.setVisible(False)
                # If the text in framerate_edit matches a combo option, select it
                # get float value from framerate_edit (QDoubleSpinBox)
                framerate_value = framerate_edit.value()
                # Round to 3 decimal places, remove leading zeros and . if whole number
                rounded_str = str(round(framerate_value, 3)).rstrip('0').rstrip('.')
                index = framerate_combo.findText(rounded_str)
                if index != -1:
                    framerate_combo.setCurrentIndex(index)
                else:
                    # Default to 24
                    framerate_combo.setCurrentIndex(default_framerate_index)
            if not self.changing_preset:
                self.custom_framerate_checkbox_state = checked
        custom_framerate_checkbox.toggled.connect(toggle_custom_framerate)
        
        content_layout.addWidget(group_box)
        content_layout.addStretch()
        
        cancel_button = QtGui.QPushButton("Cancel")
        create_button = QtGui.QPushButton("Create")
        create_button.setDefault(True)
        create_button.setAutoDefault(True)
        
        if not startupWizard:
            lower_bar.addButton(create_button)
            lower_bar.addButton(cancel_button)
        else:
            cancel_button.setVisible(False)
            # reset create_button so we can create it as a child of group box
            create_button = QtGui.QPushButton("Create", group_box)
            create_button.setGeometry(682, 48, 100, 23)
        
        main_layout.addWidget(content_widget)
        main_layout.addWidget(lower_bar)

        def check_create_enabled():
            # Enable create button only if name and directory are not empty
            name = name_edit.text().strip()
            directory = dir_edit.text().strip()
            framerate_passed = not custom_framerate_checkbox.isChecked()
            if not framerate_passed:
                framerate_text = str(framerate_edit.value()).strip()
                try:
                    framerate_value = float(framerate_text)
                    if framerate_value > 0:
                        framerate_passed = True
                except:
                    framerate_passed = False
            if name and directory and framerate_passed:
                create_button.setEnabled(True)
            else:
                create_button.setEnabled(False)
        
        # Connect text change events
        name_edit.textChanged.connect(check_create_enabled)
        dir_edit.textChanged.connect(check_create_enabled)
        framerate_edit.valueChanged.connect(check_create_enabled)

        def browse_directory():
            # Open directory dialog
            directory = QtGui.QFileDialog.getExistingDirectory(dialog, "Open Directory", dir_edit.text())
            if directory:
                dir_edit.setText(directory)
        
        browse_button.clicked.connect(browse_directory)

        def open_preset_editor():
            # save current state so we can restore it if the user cancels
            saved_presets = [preset.copy() for preset in self.presets]
            saved_autoload_preset = self.autoload_preset
            saved_autoload_preset_is_default = self.autoload_preset_is_default
            preset_editor = QtGui.QDialog(dialog)
            preset_editor.setModal(True)
            preset_editor.setObjectName("SessionPresetEditor")
            preset_editor.setWindowFlags(self.windowFlags)
            preset_editor.setWindowTitle("Edit Session Presets")
            preset_editor.setFixedSize(600, 350)
            preset_editor_layout = QtGui.QVBoxLayout(preset_editor)
            preset_editor_layout.setContentsMargins(0, 0, 0, 0)
            preset_editor_layout.setSpacing(0)
            preset_editor.setLayout(preset_editor_layout)
            preset_editor_content = QtGui.QWidget()
            preset_editor_content_layout = QtGui.QVBoxLayout(preset_editor_content)
            preset_editor_content_layout.setContentsMargins(6, 6, 6, 6)
            preset_editor_content_layout.addStretch()
            preset_editor_layout.addWidget(preset_editor_content)
            # Select autoload preset dropdown
            autoload_group = QtGui.QGroupBox(" Options ")
            autoload_group.setFixedHeight(70)
            preset_editor_content_layout.addWidget(autoload_group)
            autoload_layout = QtGui.QHBoxLayout(autoload_group)
            autoload_label = QtGui.QLabel("Autoload Preset:")
            autoload_combo = QtGui.QComboBox()
            autoload_layout.addWidget(autoload_label)
            autoload_layout.addWidget(autoload_combo)
            # Populate autoload combo
            rebuild_preset_combo(autoload_combo, append="")
            def autoload_changed(index):
                index = index - 1 # Adjust for header item
                self.custom_presets = []
                for preset in self.presets:
                    name = preset.get("name", "")
                    if name:
                        self.custom_presets.append(name)
                if index < len(self.default_presets):
                    # Default preset selected
                    preset = self.default_presets[index]
                    self.autoload_preset = preset.get("name", "")
                    self.autoload_preset_is_default = True
                elif self.custom_presets:
                    # It's a custom preset - calculate the actual custom preset index
                    default_count = len(self.default_presets)
                    custom_index = index - default_count - 2 # -2 for header and separator
                    if 0 <= custom_index < len(self.presets):
                        preset = self.presets[custom_index]
                        self.autoload_preset = preset.get("name", "")
                        self.autoload_preset_is_default = False
            autoload_combo.currentIndexChanged.connect(autoload_changed)
            def find_autoload_index():
                # Find the index of the current autoload preset in the combo
                for i in range(autoload_combo.count()):
                    item_text = autoload_combo.itemText(i)
                    if self.autoload_preset_is_default:
                        if item_text == self.autoload_preset:
                            return i
                    else:
                        if item_text == self.autoload_preset:
                            return i
                self.autoload_preset = self.default_presets[0].get("name", "")
                self.autoload_preset_is_default = True
                return 1
            autoload_combo.setCurrentIndex(find_autoload_index())
            # Custom preset table
            preset_table = QtGui.QTableWidget()
            preset_table.setColumnCount(4)
            preset_table.setHorizontalHeaderLabels(["Order", "Name", "Path", "Description"])
            preset_table.setColumnHidden(0, True)
            # set framerate column to small and read-only
            preset_table.setColumnWidth(2, 128)
            preset_table.horizontalHeader().setStretchLastSection(True)
            preset_table.sortItems(0, QtCore.Qt.AscendingOrder)
            preset_table.setEditTriggers(QtGui.QAbstractItemView.DoubleClicked | QtGui.QAbstractItemView.SelectedClicked)
            # Populate table with current presets
            preset_table.setRowCount(len(self.presets))
            for row, preset in enumerate(self.presets):
                order_item = QtGui.QTableWidgetItem(str(preset.get("order", row)))
                name_item = QtGui.QTableWidgetItem(preset.get("name", ""))
                description_item = QtGui.QTableWidgetItem(preset.get("description", ""))
                path_item = QtGui.QTableWidgetItem(preset.get("path", ""))
                preset_table.setItem(row, 0, order_item)
                preset_table.setItem(row, 1, name_item)
                preset_table.setItem(row, 2, path_item)
                preset_table.setItem(row, 3, description_item)
            preset_editor_content_layout.addWidget(preset_table)
            # Add, Move Up, Move Down, Delete buttons
            preset_button_bar = QtGui.QWidget()
            preset_button_bar_layout = QtGui.QHBoxLayout(preset_button_bar)
            preset_button_bar_layout.addStretch()
            preset_button_bar_layout.setContentsMargins(0, 0, 0, 0)
            add_button = QtGui.QPushButton("Add")
            move_up_button = QtGui.QPushButton("Move Up")
            move_down_button = QtGui.QPushButton("Move Down")
            delete_button = QtGui.QPushButton("Delete")
            preset_button_bar_layout.addWidget(add_button)
            preset_button_bar_layout.addWidget(move_up_button)
            preset_button_bar_layout.addWidget(move_down_button)
            preset_button_bar_layout.addWidget(delete_button)
            preset_editor_content_layout.addWidget(preset_button_bar)
            def add_preset():
                # File picker dialog to select a .dmx file
                file_dialog = QtGui.QFileDialog(preset_editor, "Select Preset DMX File", "", "SFM Session (*.dmx)")
                file_dialog.setFileMode(QtGui.QFileDialog.ExistingFile)
                # Default to the directory in dir_edit
                start_dir = dir_edit.text().strip()
                if os.path.isdir(start_dir):
                    file_dialog.setDirectory(start_dir)
                else:
                    file_dialog.setDirectory(self.cwd + r"\usermod\elements\sessions")
                if file_dialog.exec_():
                    selected_files = file_dialog.selectedFiles()
                    if selected_files:
                        file_path = selected_files[0]
                        # Make sure we can access the file
                        if not os.path.isfile(file_path):
                            _session_presets_error_msg("The selected file does not exist:\n%s" % file_path)
                            return
                        # Try to get framerate from dmx file
                        session_name = ""
                        dmx_converted_path = self.load_dmx_file(file_path)
                        if dmx_converted_path:
                            session_data = self.get_session_from_dmx(dmx_converted_path)
                            if session_data:
                                session_name = session_data["name"]
                            # Delete temporary converted file
                            os.remove(dmx_converted_path)
                        if session_name == "":
                            # Convert file name to session name by removing extension, replacing underscores or dashes with spaces, and capitalizing words
                            base_name = os.path.basename(file_path)
                            name_without_ext = os.path.splitext(base_name)[0]
                            session_name = name_without_ext.replace("_", " ").replace("-", " ").title()
                        # Add new row to table
                        row = preset_table.rowCount()
                        preset_table.insertRow(row)
                        order_item = QtGui.QTableWidgetItem(str(row))
                        name_item = QtGui.QTableWidgetItem(session_name)
                        description_item = QtGui.QTableWidgetItem("")
                        path_item = QtGui.QTableWidgetItem(file_path)
                        preset_table.setItem(row, 0, order_item)
                        preset_table.setItem(row, 1, name_item)
                        preset_table.setItem(row, 2, path_item)
                        preset_table.setItem(row, 3, description_item)
                        rebuild_preset_combo(preset_combo, append="")
                        find_autoload_index()
            def move_up_preset():
                current_row = preset_table.currentRow()
                if current_row > 0:
                    preset_table.insertRow(current_row - 1)
                    for col in range(preset_table.columnCount()):
                        item = preset_table.takeItem(current_row + 1, col)
                        preset_table.setItem(current_row - 1, col, item)
                    preset_table.removeRow(current_row + 1)
                    preset_table.setCurrentCell(current_row - 1, 0)
                    rebuild_preset_combo(preset_combo, append="")
                    find_autoload_index()
            def move_down_preset():
                current_row = preset_table.currentRow()
                if current_row < preset_table.rowCount() - 1 and current_row != -1:
                    preset_table.insertRow(current_row + 2)
                    for col in range(preset_table.columnCount()):
                        item = preset_table.takeItem(current_row, col)
                        preset_table.setItem(current_row + 2, col, item)
                    preset_table.removeRow(current_row)
                    preset_table.setCurrentCell(current_row + 1, 0)
                    rebuild_preset_combo(preset_combo, append="")
                    find_autoload_index()
            def delete_preset():
                current_row = preset_table.currentRow()
                if current_row != -1:
                    preset_table.removeRow(current_row)
                    rebuild_preset_combo(preset_combo, append="")
                    find_autoload_index()
            add_button.clicked.connect(add_preset)
            move_up_button.clicked.connect(move_up_preset)
            move_down_button.clicked.connect(move_down_preset)
            delete_button.clicked.connect(delete_preset)
            # Lower bar with OK and Cancel buttons
            preset_lower_bar = PyCQEditorLowerBarWidget()
            preset_lower_bar.setStatusText("Session Presets v%s by KiwifruitDev" % _session_presets_version)
            preset_create_button = QtGui.QPushButton("OK")
            preset_create_button.setDefault(True)
            preset_create_button.setAutoDefault(True)
            preset_create_button.clicked.connect(preset_editor.accept)
            preset_cancel_button = QtGui.QPushButton("Cancel")
            preset_cancel_button.clicked.connect(preset_editor.reject)
            preset_lower_bar.addButton(preset_create_button)
            preset_lower_bar.addButton(preset_cancel_button)
            preset_editor_layout.addWidget(preset_lower_bar)
            result = preset_editor.exec_()
            if result == QtGui.QDialog.Accepted:
                # Reload presets after editing
                self.presets = []
                for row in range(preset_table.rowCount()):
                    order_item = preset_table.item(row, 0)
                    name_item = preset_table.item(row, 1)
                    path_item = preset_table.item(row, 2)
                    description_item = preset_table.item(row, 3)
                    preset = {
                        "order": int(order_item.text()) if order_item else row,
                        "name": name_item.text() if name_item else "",
                        "description": description_item.text() if description_item else "",
                        "path": path_item.text() if path_item else ""
                    }
                    self.presets.append(preset)
                self.save_options()
                rebuild_preset_combo(preset_combo, append=" (autoload)")
                preset_changed(preset_combo.currentIndex())
                check_create_enabled()
            else:
                # Restore saved presets
                self.presets = saved_presets
                self.autoload_preset = saved_autoload_preset
                self.autoload_preset_is_default = saved_autoload_preset_is_default

        preset_edit_button.clicked.connect(open_preset_editor)
        
        # Button connections
        create_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        # Populate fields from registry
        reg_directory = self.get_registry_value("Directory")
        if reg_directory is not None:
            dir_edit.setText(reg_directory)
        reg_framerate = self.get_registry_value("Framerate")
        if reg_framerate is not None:
            index = framerate_combo.findText(reg_framerate)
            if index != -1:
                framerate_combo.setCurrentIndex(index)
                default_framerate_index = index
        reg_name = self.get_registry_value("Name")
        if reg_name is not None:
            name_edit.setText(reg_name)
        reg_use_custom = self.get_registry_value("UseCustomFramerate")
        if reg_use_custom == "1":
            custom_framerate_checkbox.setChecked(True)
            self.custom_framerate_checkbox_state = True

        # Connect create button
        def accepted():
            filename = name_edit.text()
            preset_index = preset_combo.currentIndex()
            directory = dir_edit.text()
            framerate = 24.0
            
            if custom_framerate_checkbox.isChecked():
                framerate = float(framerate_edit.value())
            else:
                framerate = float(framerate_combo.currentText())
            
            # Save values to registry
            self.set_registry_value("Directory", dir_edit.text())
            self.set_registry_value("Name", name_edit.text())
            self.set_registry_value("Framerate", str(framerate))
            self.set_registry_value("UseCustomFramerate", "1" if custom_framerate_checkbox.isChecked() else "0")
            self.create_session(preset_index, framerate, filename, directory)
        dialog.accepted.connect(accepted)

        preset_changed(preset_combo.currentIndex())
        check_create_enabled()
        
        # Show dialog
        result = dialog.exec_()
        return result
    def get_registry_value(self, value_name):
        # SFM stores the following values:
        # - Directory REG_SZ D:/steamlibrary/steamapps/common/sourcefilmmaker/game/usermod/elements/sessions
        # - Framerate REG_SZ 24
        # - Name REG_SZ session
        # - UseCustomFramerate REG_SZ 0 or 1 (may not exist)
        # We will read from here and then write back when creating a new session
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_path, 0, winreg.KEY_READ) as key:
                value, regtype = winreg.QueryValueEx(key, value_name)
                return value
        except Exception as e:
            _session_presets_msg("Error reading registry value %s: %s" % (value_name, e))
            return None
    def set_registry_value(self, value_name, value):
        # Check if key exists, create if not
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_path, 0, winreg.KEY_SET_VALUE) as key:
                pass
        except FileNotFoundError:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.registry_path) as key:
                pass
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.registry_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, value)
        except Exception as e:
            _session_presets_msg("Error writing registry value %s: %s" % (value_name, e))

def _SessionPresets_FirstBoot():
    try:
        # Create window if it doesn't exist
        sessionpresets = globals().get("_session_presets")
        if sessionpresets is not None:
            # Delete existing instance
            del globals()["_session_presets"]
        sessionpresets = SessionPresets()
        globals()["_session_presets"] = sessionpresets
    except Exception  as e:
        traceback.print_exc()
        _session_presets_error_msg("Error: %s" % e)

# Attached default startup session in binary, saved to usermod\elements\default_startup_sessions.dmx on first run
startup_session = """
###
"""

_SessionPresets_FirstBoot()
