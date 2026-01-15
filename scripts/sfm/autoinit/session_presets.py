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

import os
import sfm
import sfmApp
import json
import traceback
import _winreg as winreg
from PySide import QtGui, QtCore, shiboken

_session_presets_version = "0.1"

def _session_presets_msg(msg):
    sfm.Msg("[SESSION PRESETS] " + msg + "\n")

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
        self.presets = []
        self.added_separator_header = False
        self.registry_path = r"Software\Valve\SourceFilmmaker\NewSessionWizard"
        self.load_options()
        self.new_session_menu()
        #self.add_window_actions()
        #self.open_startup_session()
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
            "presets": [
                {
                    "name": "Custom Preset 1",
                    "order": 1,
                    "description": "A custom preset",
                    "framerate": "30",
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
                presets = data.get("presets", [])
                for preset in presets:
                    append_preset = {
                        "name": preset.get("name", ""),
                        "order": preset.get("order", 0),
                        "description": preset.get("description", ""),
                        "framerate": preset.get("framerate", ""),
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

            
    def open_session(self):
        # todo!
        pass
    def new_session_menu(self):
        self.custom_framerate_checkbox_state = False
        self.changing_preset = False
        # Create modal dialog
        dialog = QtGui.QDialog()
        dialog.setModal(True)
        dialog.setFixedSize(800, 260)
        dialog.setWindowTitle(" ")
        dialog.setObjectName("NewSessionWizard")
        dialog.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.MSWindowsFixedSizeDialogHint)
        
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
        preset_combo.setGeometry(360+3, 20, 220, 23)

        autoload_append = " (autoload)"
        item_index = 0
        preset_combo.insertItem(item_index, "Default Presets")
        preset_combo.model().item(item_index).setEnabled(False)
        item_index += 1
        # Add default presets
        for preset in self.default_presets:
            preset_name = preset.get("name", "")
            if self.autoload_preset_is_default and preset_name == self.autoload_preset:
                preset_name += autoload_append
            preset_combo.insertItem(item_index, preset_name)
            preset_combo.setCurrentIndex(item_index)
            item_index += 1
        preset_combo.setCurrentIndex(1)
        # Add separator if there are custom presets
        custom_presets = []
        for preset in self.presets:
            name = preset.get("name", "")
            if name:
                custom_presets.append(name)
        if custom_presets:
            preset_combo.insertSeparator(item_index)
            item_index += 1
            preset_combo.insertItem(item_index, "Custom Presets")
            preset_combo.model().item(item_index).setEnabled(False)
            item_index += 1
            for preset in custom_presets:
                preset_name = preset
                if not self.autoload_preset_is_default and preset_name == self.autoload_preset:
                    preset_name = preset_name + autoload_append
                preset_combo.insertItem(item_index, preset_name)
                preset_combo.setCurrentIndex(item_index)
                item_index += 1

        default_framerate_index = 7
        
        # Bottom button bar (PyCQEditorLowerBarWidget)
        lower_bar = PyCQEditorLowerBarWidget()
        lower_bar.setStatusText(self.descriptor)

        def preset_changed(index):
            self.changing_preset = True
            index = index - 1 # Adjust for header item

            # Reset framerate controls to enabled state
            framerate_combo.setCurrentIndex(default_framerate_index)
            framerate_combo.setEnabled(True)
            framerate_edit.setEnabled(True)
            custom_framerate_label.setEnabled(True)
            custom_framerate_checkbox.setEnabled(True)
            custom_framerate_checkbox.setChecked(self.custom_framerate_checkbox_state)
            description = ""
            
            # Check if it's a default preset (index < len(default_presets))
            if index < len(self.default_presets):
                description = self.default_presets[index].get("description", "")
            elif custom_presets:
                # It's a custom preset - calculate the actual custom preset index
                default_count = len(self.default_presets)
                custom_index = index - default_count - 2 # -2 for header and separator
                
                if 0 <= custom_index < len(self.presets):
                    preset = self.presets[custom_index]
                    framerate_value = preset.get("framerate", "")
                    if framerate_value:
                        # parse as float or use 24 as default
                        try:
                            framerate_value = float(framerate_value)
                        except:
                            framerate_value = 24.0
                        # Check if framerate_value is in combo
                        combo_index = framerate_combo.findText(str(framerate_value))
                        if combo_index != -1:
                            custom_framerate_checkbox.setChecked(False)
                            framerate_combo.setCurrentIndex(combo_index)
                        else:
                            custom_framerate_checkbox.setChecked(True)
                            framerate_edit.setValue(float(framerate_value))
                        # Disable framerate controls for custom presets
                        framerate_combo.setEnabled(False)
                        framerate_edit.setEnabled(False)
                        custom_framerate_label.setEnabled(False)
                        custom_framerate_checkbox.setEnabled(False)
                    description = preset.get("description", "")
            lower_bar.setStatusText(description)
            preset_combo.setToolTip(description)
            self.changing_preset = False
        preset_combo.currentIndexChanged.connect(preset_changed)
        
        # Browse button next to preset combo
        preset_edit_button = QtGui.QPushButton("Edit...", group_box)
        preset_edit_button.setGeometry(592+3, 20, 80, 23)
        
        # Directory text field and Browse... button
        dir_label = QtGui.QLabel("Directory:", group_box)
        dir_label.move(10, 53)
        dir_edit = QtGui.QLineEdit(group_box)
        dir_edit.setGeometry(70, 48, 620, 23)
        dir_edit.setText("c:\\program files (x86)\\steam\\steamapps\\common\\sourcefilmmaker\\game\\usermod\\elements\\sessions")
        browse_button = QtGui.QPushButton("Browse...", group_box)
        browse_button.setGeometry(702, 48, 80, 23)
        
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
                index = framerate_combo.findText(str(framerate_edit.value()))
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
        
        lower_bar.addButton(create_button)
        lower_bar.addButton(cancel_button)
        
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
            filename = os.path.join(dir_edit.text(), name_edit.text() + ".dmx")
            preset_index = preset_combo.currentIndex()
            preset_name = preset_combo.currentText()
            
            if custom_framerate_checkbox.isChecked():
                framerate = str(framerate_edit.value())
            else:
                framerate = framerate_combo.currentText()
            
            # Save values to registry
            self.set_registry_value("Directory", dir_edit.text())
            self.set_registry_value("Name", name_edit.text())
            self.set_registry_value("Framerate", framerate)
            self.set_registry_value("UseCustomFramerate", "1" if custom_framerate_checkbox.isChecked() else "0")
            
            self.create_session(filename, preset_index, preset_name, framerate)
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
    
    def create_session(self, filename, preset_index, preset_name, framerate):
        """Create a new SFM session with the specified parameters"""
        try:
            _session_presets_msg("Creating session: %s with preset '%s' (index %d) at %s fps" % 
                              (filename, preset_name, preset_index, framerate))
            
            # Determine if this is a default or custom preset
            if preset_index < len(self.default_presets):
                # Default preset
                default_preset = self.default_presets[preset_index]
                _session_presets_msg("Using default preset: %s" % default_preset["name"])
                # TODO: Implement default preset creation logic
            else:
                # Custom preset
                default_count = len(self.default_presets)
                separator_offset = 1 if len(self.presets) > 0 else 0
                custom_index = preset_index - default_count - separator_offset
                
                if 0 <= custom_index < len(self.presets):
                    custom_preset = self.presets[custom_index]
                    preset_path = custom_preset.get("path", "")
                    _session_presets_msg("Using custom preset: %s from %s" % (custom_preset["name"], preset_path))
                    # TODO: Load and apply custom preset from DMX file
                else:
                    _session_presets_msg("Error: Invalid custom preset index %d" % custom_index)
                    return
            
            # TODO: Implement actual session creation logic here
            # This would involve creating the DMX file and loading it into SFM
            
        except Exception as e:
            _session_presets_msg("Error creating session: %s" % e)
            import traceback
            traceback.print_exc()

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
        msgBox = QtGui.QMessageBox()
        msgBox.setWindowTitle("Session Presets")
        msgBox.setText("Error: %s" % e)
        msgBox.exec_()

# Attached default startup session in binary, saved to usermod\elements\default_startup_sessions.dmx on first run
startup_session = """
A
"""

_SessionPresets_FirstBoot()
