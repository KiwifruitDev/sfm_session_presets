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

import ctypes, shutil, subprocess, os, json, traceback
import sfm, sfmApp
import _winreg as winreg
from vs import g_pDataModel as dm
from PySide import QtGui, QtCore

virtual_protect = ctypes.windll.kernel32.VirtualProtect
write_process_memory = ctypes.windll.kernel32.WriteProcessMemory
get_current_process = ctypes.windll.kernel32.GetCurrentProcess
get_command_line = ctypes.windll.kernel32.GetCommandLineA

_session_presets_version = "0.2"

def _session_presets_msg(msg):
    sfm.Msg("[SESSION PRESETS] " + msg + "\n")

def _session_presets_msg_box(msg, prefix, icon):
    _session_presets_msg(prefix + ": " + msg)
    msgBox = QtGui.QMessageBox()
    msgBox.setWindowTitle("Session Presets: " + prefix)
    msgBox.setText(msg)
    msgBox.setIcon(icon)
    msgBox.exec_()

def _session_presets_error_msg(msg):
    _session_presets_msg_box(msg, "Error", QtGui.QMessageBox.Critical)

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
    def __init__(self, already_initialized=False):
        _session_presets_msg("Initializing Session Presets Script v%s" % _session_presets_version)
        self.cwd = os.getcwd()
        self.descriptor = "SFM Session Presets v%s by KiwifruitDev" % _session_presets_version
        self.options_file = "session_presets.json"
        self.autoload_preset = "Blank"
        self.autoload_enabled = False
        self.setting_autoload_enabled = False
        self.autoload_preset_is_default = True
        self.custom_framerate_checkbox_state = False
        self.attempting_to_rebuild_preset_combo = False
        self.changing_preset = False
        self.default_session_framerate = 24.0
        self.default_session_title = "Default Startup Sessions"
        default_presets = [
            {
                "name": "Blank",
                "description": "An empty session without a map or camera. This is what SFM uses by default.",
                "id": "91b71055-26fe-4b6f-bf6a-6afdc2a986ee"
            },
            {
                "name": "Stage",
                "description": "Uses the stage map with a camera in the center and key, bounce, fill, and rim lights set up.",
                "id": "94b17e1f-dd81-455a-b889-0e734a6845f9"
            },
            {
                "name": "Dark Room",
                "description": "Uses the dark_room map with a camera set up in the corner.",
                "id": "86157d42-842c-466c-b2ac-bc099a5d431c"
            }
        ]
        self.default_presets = default_presets
        self.custom_presets = []
        self.windowFlags = QtCore.Qt.Dialog | QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.MSWindowsFixedSizeDialogHint
        self.cwd = os.getcwd()
        self.dmxConvert = self.cwd + r"\bin\dmxconvert.exe"
        self.presets = []
        self.added_separator_header = False

        # Manipulate the function in memory that shows the startup wizard to prevent it from appearing
        if not already_initialized:
            self.disable_start_wizard_patch()
        
        # Load the options from file or set defaults if they are corrupt
        self.load_options()
        if len(self.default_presets) == 0 or type(self.default_presets[0]) is not dict or self.default_presets[0].get("name", "") == "":
            # Reset to default default settings
            _session_presets_msg("Resetting default presets to built-in defaults.")
            self.default_presets = default_presets
            self.autoload_preset = "Blank"
            self.autoload_enabled = False
            self.autoload_preset_is_default = True
            self.default_session_framerate = 24.0
            self.default_session_title = "Default Startup Sessions"
            self.save_options()

        # Replace New in the File menu with our own handler
        self.add_window_actions()

        # Show the startup wizard if needed
        if already_initialized or not self.autoload_enabled and self.should_show_start_wizard():
            self.new_session_menu(True)
        elif self.autoload_enabled:
            # Autoload the selected preset without showing the wizard
            # If this script is being run twice, don't autoload again
            reg_directory = self.get_registry_value("Directory")
            reg_filename = self.get_registry_value("Name")
            reg_framerate = self.get_registry_value("FrameRate")
            if reg_directory and reg_filename and reg_framerate:
                framerate = float(reg_framerate)
                preset_index = -1
                default_count = len(self.default_presets)
                for i in range(len(self.default_presets)):
                    if self.autoload_preset_is_default:
                        if self.default_presets[i].get("name", "") == self.autoload_preset:
                            preset_index = i
                            break
                if preset_index == -1:
                    for i in range(len(self.presets)):
                        if not self.autoload_preset_is_default:
                            if self.presets[i].get("name", "") == self.autoload_preset:
                                preset_index = default_count + 1 + i # +1 for separator
                                break
                # Ensure the name does not already exist in the selected directory
                while os.path.exists(os.path.join(reg_directory, reg_filename + ".dmx")):
                    # If the name ends in numbers, get the numbers and increment by 1
                    numbers = ""
                    for char in reversed(reg_filename):
                        if char.isdigit():
                            numbers = char + numbers
                        else:
                            break
                    if numbers:
                        new_number = str(int(numbers) + 1)
                        reg_filename = reg_filename[:-len(numbers)] + new_number
                    else:
                        # Append 1 to the name
                        reg_filename = reg_filename + "1"
                self.create_session(preset_index, framerate, reg_filename, reg_directory)
    def should_show_start_wizard(self):
        # Check if we should show the startup wizard
        if self.autoload_enabled:
            return False

        # Get command line for SFM process
        cmd_line_ptr = get_command_line()
        cmd_line = ctypes.c_char_p(cmd_line_ptr).value.decode('utf-8')

        # Check for -nostartwizard argument
        if "-nostartwizard" in cmd_line.lower():
            _session_presets_msg("Skipping startup wizard due to -nostartwizard command line argument.")
            return False

        return True
    def convert_dmx_file(self, path, out):
        # Run dmxconvert to convert a dmx file to keyvalues2 format in order to read and modify it

        # Convert paths to proper OS format
        dmxconvert = os.path.normpath(self.dmxConvert)
        if not os.path.isfile(dmxconvert):
            _session_presets_error_msg("dmxconvert executable not found: %s" % dmxconvert)
            return None
        path = os.path.normpath(path)
        if not os.path.isfile(path):
            _session_presets_error_msg("dmxconvert input file does not exist: %s" % path)
            return None
        out = os.path.normpath(out)

        # Delete the output file if it currently exists
        # We should've already prompted the user to save any unsaved changes before calling this function
        if os.path.isfile(out):
            os.remove(out)
        
        # Run dmxconvert using system call
        args = [dmxconvert, "-i", path, "-o", out, "-oe", "keyvalues2"]
        proc = subprocess.Popen(args, shell=True)
        return_code = proc.wait()
        if return_code != 0:
            _session_presets_error_msg("dmxconvert failed to convert file %s. Return code: %d" % (path, return_code))
            return None

        # Check if out was created
        if os.path.isfile(out):
            return out
        return None
    def replace_name_and_framerate_in_dmx(self, dmx_path, original_filename, filename, original_framerate, framerate, is_default):
        # Read the dmx file line-by-line and replace the session name and framerate
        # Also handles default session special cases, since the default session is formatted in a specific way
        search_filename = '"name" "string" "' + original_filename + '"'
        original_framerate_str = str(original_framerate).rstrip('0').rstrip('.')
        search_framerate = '"frameRate" "float" "' + original_framerate_str + '"'
        framerate_str = str(framerate).rstrip('0').rstrip('.')
        original_id = self.default_presets[0].get("id", "")
        search_id = '"activeClip" "element" "' + original_id + '"'

        # "clipBin" "element_array" [] is how the clipBin is defined in default sessions
        # This is not how SFM usually defines the clipBin, but it is formatted this way by hand in the default sessions dmx file
        # Simply makes it easier to parse and modify here
        search_clipbin = '"clipBin" "element_array" []'
        id = ""
        description = ""

        # Find the ID and description for the original filename if it's a default preset
        if is_default:
            for default_preset in self.default_presets:
                if default_preset.get("name", "") == original_filename:
                    description = default_preset.get("description", "")
                    id = default_preset.get("id", "")
                    break
        try:
            with open(dmx_path, "r") as f:
                lines = f.readlines()
            with open(dmx_path, "w") as f:
                for line in lines:
                    # Replace session name and framerate
                    if search_filename in line:
                        line = line.replace(original_filename, filename)
                    elif search_framerate in line:
                        line = line.replace(original_framerate_str, framerate_str)
                    
                    # Handle default session special cases
                    elif is_default and self.default_session_title in line:
                        line = line.replace(self.default_session_title, "session")
                    elif is_default and search_id in line:
                        line = line.replace(original_id, id)
                    elif is_default and description in line:
                        line = line.replace(description, "")
                    elif is_default and search_clipbin in line:
                        line = line.replace(" []", "\n\t[\n\t\t\"element\" \"" + id + "\"\n\t]")
                    
                    f.write(line)
            return True
        except Exception as e:
            _session_presets_msg("Error modifying dmx file %s: %s" % (dmx_path, e))
        return False
    def get_framerate_from_dmx(self, dmx_path):
        # Read the dmx file line-by-line to find the framerate
        try:
            with open(dmx_path, "r") as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()

                    # This line indicates any element with the framerate attribute
                    # Includes both clips and lights, but usually they are all set to the same framerate
                    if '"frameRate" "float" "' in line:
                        # Extract framerate
                        parts = line.split('"')
                        for i in range(len(parts)):
                            if parts[i] == "float" and i + 2 < len(parts):
                                framerate_str = parts[i + 2].strip()
                                try:
                                    # Make sure we found a valid float
                                    framerate = float(framerate_str)

                                    # Return the first valid framerate found
                                    return framerate
                                except ValueError:
                                    _session_presets_msg("Invalid framerate value in dmx file %s: %s" % (dmx_path, framerate_str))
        except Exception as e:
            _session_presets_msg("Error reading dmx file %s: %s" % (dmx_path, e))
        return None
    def get_name_from_dmx(self, dmx_path):
        # Read the dmx file line-by-line to find the active clip name
        try:
            with open(dmx_path, "r") as f:
                lines = f.readlines()
                in_active_clip = False
                clip_id = None
                clip_name = None
                for line in lines:
                    line = line.strip()

                    # This line indicates the start of the active clip attribute in the root document
                    if not clip_name and not clip_id and '"activeClip" "element" "' in line:
                        # Get the clip ID
                        parts = line.split('"')
                        for i in range(len(parts)):
                            if parts[i] == "element" and i + 2 < len(parts):
                                clip_id = parts[i + 2].strip()
                    
                    # Look for the active clip by its ID
                    elif not clip_name and clip_id and '"id" "elementid" "' + clip_id + '"' in line:
                        in_active_clip = True
                    elif not clip_name and in_active_clip:
                        if '}' in line:
                            # End of activeClip
                            in_active_clip = False
                            clip_id = None
                        elif '"name" "string" "' in line:
                            # Extract clip name from this line
                            parts = line.split('"')
                            for i in range(len(parts)):
                                if parts[i] == "string" and i + 2 < len(parts):
                                    clip_name = parts[i + 2].strip()
                                    in_active_clip = False
                    
                    # If we have found the clip name, return it
                    if clip_name:
                        return clip_name
        except Exception as e:
            _session_presets_msg("Error reading dmx file %s: %s" % (dmx_path, e))
        return None
    def disable_start_wizard_patch(self):
        # Apply a patch to prevent the startup wizard from appearing
        _session_presets_msg("Applying patches to stop startup wizard...")

        # This is just about where code stops executing when Python is loaded
        addr = ctypes.windll.ifm._handle + 0x2d1685 # game/bin/tools/ifm.dll -> 6a 28 PUSH 0x28, e8 f4 d3 f8 ff CALL FUN_1025ea80

        # We're jumping straight to the end of the function that sets up and shows the startup wizard
        # This is the same behavior as using the -nostartwizard command line argument
        data = [0x66, 0x90, 0xE9, 0x92, 0xF4, 0xFF, 0xFF] # 66 90 NOP, e9 92 f4 ff ff JMP LAB_102d0b1e
        data_len = len(data)
        data_bytes = (ctypes.c_char * data_len).from_buffer(bytearray(data))
        
        # Disable write protection
        old_protect = ctypes.c_ulong()
        virtual_protect(addr, data_len, 0x40, ctypes.byref(old_protect))

        # Write the patch
        bytes_written = ctypes.c_size_t(0)
        write_process_memory(get_current_process(), addr, ctypes.addressof(data_bytes), ctypes.sizeof(data_bytes), ctypes.byref(bytes_written))

        # Restore write protection, and we're done!
        virtual_protect(addr, data_len, old_protect, ctypes.byref(old_protect))
        _session_presets_msg("Patches applied to address 0x%X" % addr)
    def load_options(self):
        # JSON file format
        options_path = os.path.join(self.cwd, self.options_file)

        # Create options file with default values if it does not exist
        if not os.path.isfile(options_path):
            self.save_options()
            return # We already have default values set in __init__
        
        # Load options from file
        if os.path.isfile(options_path):
            try:
                with open(options_path, "r") as f:
                    data = json.load(f)
                options = data.get("options", {})

                # User-settable options
                self.autoload_preset = options.get("autoload_preset", "")
                self.autoload_enabled = options.get("autoload_enabled", False)
                self.autoload_preset_is_default = options.get("autoload_preset_is_default", False)

                # Populate default presets and settings
                self.default_session_framerate = data.get("default_session_framerate", 24.0)
                self.default_session_title = data.get("default_session_title", "Default Startup Sessions")
                default_presets = data.get("default_presets", [])
                if default_presets:
                    self.default_presets = default_presets

                # Populate custom presets
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
        # JSON file format
        # Saves the current options to the options file
        # This also populates default values if they do not exist in the current options file
        options_path = os.path.join(self.cwd, self.options_file)
        data = {
            "options": {
                "autoload_preset": self.autoload_preset,
                "autoload_enabled": self.autoload_enabled,
                "autoload_preset_is_default": self.autoload_preset_is_default
            },
            "default_presets": self.default_presets,
            "presets": self.presets,
            "default_session_framerate": self.default_session_framerate,
            "default_session_title": self.default_session_title,
            "version": _session_presets_version
        }
        try:
            with open(options_path, "w") as f:
                json.dump(data, f, indent=4)
            _session_presets_msg("Saved options to %s" % options_path)
        except Exception as e:
            _session_presets_msg("Error saving options to %s: %s" % (options_path, e))
    def add_window_actions(self):
        # Adds a window action to File menu, taken from SFM Python Module Pack
        # https://steamcommunity.com/sharedfiles/filedetails/?id=562830725
        # Credit to walropodes for the original code

        # Look for the File menu in the main window's menu bar
        main_window = sfmApp.GetMainWindow()
        for widget in main_window.children():
            if isinstance(widget, QtGui.QMenuBar):
                menu_bar = widget
                break
            
        # Find the File menu
        for menu_item in menu_bar.actions():
            if menu_item.text() == 'File':
                file_menu = menu_item.menu()
                break
        
        # The first action is the New button action
        # We're going to disconnect its event and connect our own
        new_action = file_menu.actions()[0]
        new_action.setShortcut(QtGui.QKeySequence("Ctrl+N"))
        try:
            new_action.triggered.disconnect() # SFM's original new session handler
        except Exception as e:
            pass

        # Connect our new session menu to the New action
        new_action.triggered.connect(self.new_session_menu)
    def create_session(self, preset_index, framerate, filename, directory):
        if sfmApp.HasDocument():
            sfmApp.CloseDocument(forceSilent=False)
        if sfmApp.HasDocument():
            # User cancelled close (unsaved changes)
            return False
        _session_presets_msg("Creating session with preset index %d, framerate %f, filename %s, directory %s" % (preset_index, framerate, filename, directory))
        full_filename = directory + "/" + filename + ".dmx"
        default_preset = False
        preset_path = ""
        # Determine if preset_index is a default preset or custom preset
        if preset_index > 0:
            if preset_index < len(self.default_presets):
                default_preset = True
                preset_path = self.default_presets[preset_index].get("name", "")
            else:
                # It's a custom preset - calculate the actual custom preset index
                default_count = len(self.default_presets)
                custom_index = preset_index - default_count - 1 # -1 for separator
                if 0 <= custom_index < len(self.presets):
                    preset = self.presets[custom_index]
                    preset_path = preset.get("path", "")
        try:
            if default_preset:
                dmx_path = os.path.join(self.cwd, "workshop\\scripts\\default_startup_sessions.dmx")
                
                if not os.path.isfile(dmx_path):
                    # Possibly cloned git repository as a mod
                    dmx_path = os.path.join(self.cwd, "sfm_session_presets\\scripts\\default_startup_sessions.dmx")
                if not os.path.isfile(dmx_path):
                    # Search each directory in cwd except known game directories
                    dmx_path = ""
                    ignore_dirs = [
                        "bin",
                        "hl2",
                        "left4dead2_movies",
                        "platform",
                        "sdktools",
                        "tf",
                        "tf_movies",
                        "workshop",
                        "dod",
                        "portal2",
                        "portal2_dlc1",
                        "portal2_dlc2",
                        "bladesymphony",
                        "blackmesa",
                        "left4dead2",
                        "left4dead2_dlc1",
                        "left4dead2_dlc2",
                        "dinodday",
                        "stanleyparable"
                    ]
                    for item in os.listdir(self.cwd):
                        item_path = os.path.join(self.cwd, item)
                        if os.path.isdir(item_path) and item.lower() not in ignore_dirs:
                            scripts_path = os.path.join(item_path, "scripts", "default_startup_sessions.dmx")
                            if os.path.isfile(scripts_path):
                                dmx_path = scripts_path
                                break
                    if not os.path.isfile(dmx_path):
                        raise Exception("Found a default startup sessions but could not read it: %s" % dmx_path)
                if not os.path.isfile(dmx_path):
                    raise Exception("Could not search and find default startup sessions file.")
                _session_presets_msg("Loading default startup sessions from %s" % dmx_path)

                # copy the default startup sessions to the new location
                shutil.copyfile(dmx_path, full_filename)
                if not os.path.isfile(full_filename):
                    raise Exception("Failed to copy default startup sessions file to: %s" % full_filename)
                if not self.replace_name_and_framerate_in_dmx(full_filename, preset_path, filename, self.default_session_framerate, framerate, True):
                    raise Exception("Failed to modify copied default startup sessions file: %s" % dmx_path)
                
                # Load the copied default startup sessions file
                sfmApp.OpenDocument(full_filename)
                sfmApp.ProcessEvents()
                os.remove(full_filename)
                document = sfmApp.GetDocumentRoot()
                if not document:
                    raise Exception("Failed to open copied default startup sessions document.")
                
                # Since we're reading from the default sessions, let's update our local default_presets list to match any changes
                # This allows the Workshop item to update the default presets without updating this script as well
                defaults = getattr(document, "defaults", None)
                ids = getattr(document, "ids", None)
                if not defaults or not ids:
                    raise Exception("Failed to find defaults in copied default startup sessions document.")
                clips = []
                defaults_array = defaults.GetValue()
                ids_array = ids.GetValue()
                count = defaults_array.Count()
                activeclip = None # We're also looking for the desired default session here
                for i in range(count):
                    try:
                        clip_element = defaults_array[i]
                        name = clip_element.name.GetValue()
                        id = ids_array[i]
                        description = clip_element.text.GetValue()
                        if name == filename:
                            # Found the active clip, keep our current preset info as it was previously changed when copying
                            clips.append({
                                "name": self.default_presets[preset_index].get("name", ""),
                                "description": self.default_presets[preset_index].get("description", ""),
                                "id": id
                            })
                            activeclip = clip_element
                        else:
                            # Populate this clip info into our default presets
                            clips.append({
                                "name": name,
                                "description": description,
                                "id": id
                            })
                    except Exception as e:
                        raise Exception("Error reading clip from defaults: %s" % e)
                if not activeclip:
                    raise Exception("Failed to find active clip in copied default startup sessions document.")

                # Update our default_presets list
                self.default_presets = clips

                # Set this session's active clip to the one we just created
                dm.SetUndoEnabled(False) # Making element changes...
                document.activeClip = activeclip

                # We can't add it to the clipBin without crashing SFM, instead we've done this in the dmx file modification
                #document.clipBin.SetCount(1)
                #document.clipBin[0] = activeclip

                # Remove defaults and ids attributes to clean up what's left of the default sessions
                document.RemoveAttribute("defaults")
                document.RemoveAttribute("ids")

                # Finished! Save what we've done and return
                dm.SetUndoEnabled(True) # Done making element changes
                self.save_options()
                return True
            elif preset_path:
                # User selected a custom preset, let's find it
                if not preset_path or not os.path.isfile(preset_path):
                    raise Exception("Preset file not found: %s" % preset_path)
                
                # Convert the preset dmx file to keyvalues2 format so we can read it line-by-line
                dmx_converted_path = self.convert_dmx_file(preset_path, full_filename)
                if not dmx_converted_path:
                    raise Exception("Failed to convert preset dmx file: %s" % preset_path)
                
                # Read the converted dmx file to get the session name and framerate
                session_name = self.get_name_from_dmx(dmx_converted_path)
                if session_name:
                    session_name = session_name
                framerate_in_dmx = self.get_framerate_from_dmx(dmx_converted_path)
                if not framerate_in_dmx:
                    framerate_in_dmx = self.default_session_framerate

                # Set the desired name and framerate in the copied dmx file
                if not self.replace_name_and_framerate_in_dmx(dmx_converted_path, session_name, filename, framerate_in_dmx, framerate, False):
                    raise Exception("Failed to modify copied preset dmx file: %s" % dmx_converted_path)
                
                # Just in case, close any open document forcefully (we already asked the user to save unsaved changes above)
                if sfmApp.HasDocument():
                    sfmApp.CloseDocument()

                # Open the modified preset dmx file as the new session
                # This also causes the map to load if there is one set
                sfmApp.OpenDocument(dmx_converted_path)
                sfmApp.ProcessEvents()

                # Delete this new session file
                # If the user makes any changes, SFM will ask them to save it before closing
                # This keeps behavior consistent with regular new session creation
                os.remove(dmx_converted_path)
                return True
        except Exception as e:
            _session_presets_msg("Error creating session from preset: %s" % e)
            traceback.print_exc()
        # Looks like we fell through - create a blank session as fallback
        if sfmApp.HasDocument():
            sfmApp.CloseDocument() # In case we have a lingering document still open
        sfmApp.NewDocument(filename=full_filename, name=filename, framerate=framerate, defaultContent=True, forceSilent=False)
        return True
    def new_session_menu(self, startupWizard=False):
        self.custom_framerate_checkbox_state = False
        self.changing_preset = False
        # Create modal dialog
        dialog = QtGui.QDialog()
        dialog.setModal(True)
        if startupWizard:
            dialog.setFixedSize(800, 430+48-6)
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
        
        # Group box for New Session
        group_box = QtGui.QGroupBox(" New Session ", content_widget)
        group_box.setGeometry(6, 19, 788, 105)
        
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
        self.attempting_to_rebuild_preset_combo = False
        def rebuild_preset_combo(combo, append):
            combo.clear()
            self.custom_presets = []
            item_index = 0
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
                for preset in self.custom_presets:
                    preset_name = preset
                    item_index += 1
                    if not self.autoload_preset_is_default and preset_name == self.autoload_preset:
                        preset_name = preset_name + append
                    combo.insertItem(item_index, preset_name)
            # Set current index to autoload preset
            default_count = len(self.default_presets)
            preset_index = -1
            if self.autoload_preset_is_default:
                for i in range(len(self.default_presets)):
                    if self.default_presets[i].get("name", "") == self.autoload_preset:
                        preset_index = i
                        break
            else:
                for i in range(len(self.presets)):
                    if self.presets[i].get("name", "") == self.autoload_preset:
                        preset_index = default_count + 1 + i # +1 for separator
                        break
            if preset_index != -1:
                combo.setCurrentIndex(preset_index)
            else:
                # Not found, set to first default preset
                _session_presets_msg("Autoload preset '%s' not found, defaulting to first default preset." % self.autoload_preset)
                self.autoload_preset = self.default_presets[0].get("name", "")
                self.autoload_preset_is_default = True
                self.save_options()
                if not self.attempting_to_rebuild_preset_combo:
                    self.attempting_to_rebuild_preset_combo = True
                    rebuild_preset_combo(preset_combo, " (default)")
                    self.attempting_to_rebuild_preset_combo = False
                else:
                    _session_presets_error_msg("Failed to find autoload preset after rebuilding preset combo.")
                    preset_combo.setEnabled(False)

        default_framerate_index = 7
        
        # Bottom button bar (PyCQEditorLowerBarWidget)
        lower_bar = PyCQEditorLowerBarWidget()
        lower_bar.setStatusText(self.descriptor)
        #if startupWizard:
            #lower_bar.setVisible(False)

        def preset_changed(index):
            self.changing_preset = True
            description = ""
            
            # Check if it's a default preset (index < len(default_presets))
            if index < len(self.default_presets):
                description = self.default_presets[index].get("description", "")
            elif self.custom_presets:
                # It's a custom preset - calculate the actual custom preset index
                default_count = len(self.default_presets)
                custom_index = index - default_count - 1 # -1 for separator
                
                if 0 <= custom_index < len(self.presets):
                    preset = self.presets[custom_index]
                    description = preset.get("description", "")
            lower_bar.setStatusText(description)
            preset_combo.setToolTip(description)
            self.changing_preset = False
        preset_combo.currentIndexChanged.connect(preset_changed)
        rebuild_preset_combo(preset_combo, " (default)")
        
        # Browse button next to preset combo
        preset_edit_button = QtGui.QPushButton("Edit...", group_box)
        preset_edit_button.setGeometry(596, 20, 80, 23)
        
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
            # filename in this directory must not already exist
            full_path = os.path.join(directory, name + ".dmx")
            if os.path.isfile(full_path):
                create_button.setEnabled(False)
        
        # Connect text change events
        name_edit.textChanged.connect(check_create_enabled)
        dir_edit.textChanged.connect(check_create_enabled)
        framerate_edit.valueChanged.connect(check_create_enabled)

        def browse_directory():
            # Open directory dialog starting in current dir_edit text
            directory = QtGui.QFileDialog(dialog, "Open Directory", "", "Directories")
            directory.setFileMode(QtGui.QFileDialog.Directory)
            # don't allow changing file type combo
            start_dir = dir_edit.text().strip()
            if os.path.isdir(start_dir):
                directory.setDirectory(start_dir)
            if directory.exec_():
                selected_dirs = directory.selectedFiles()
                if selected_dirs:
                    dir_edit.setText(selected_dirs[0])
        
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
            autoload_label = QtGui.QLabel("Default Preset:")
            autoload_combo = QtGui.QComboBox()
            autoload_combo.setFixedWidth(227)
            self.setting_autoload_enabled = self.autoload_enabled
            autoload_enabled_checkbox = QtGui.QCheckBox("Load automatically when SFM starts")
            autoload_enabled_checkbox.setChecked(self.autoload_enabled)
            autoload_layout.addWidget(autoload_label)
            autoload_layout.addWidget(autoload_combo)
            autoload_layout.addWidget(autoload_enabled_checkbox)
            autoload_layout.addStretch()
            # Populate autoload combo
            self.reloading = False
            rebuild_preset_combo(autoload_combo, append="")
            def autoload_changed(index):
                if self.reloading:
                    return
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
                    custom_index = index - default_count - 1 # -1 for separator
                    if 0 <= custom_index < len(self.presets):
                        preset = self.presets[custom_index]
                        self.autoload_preset = preset.get("name", "")
                        self.autoload_preset_is_default = False
            autoload_combo.currentIndexChanged.connect(autoload_changed)
            def find_autoload_index():
                # Find the index of the current autoload preset in the combo
                for i in range(autoload_combo.count()):
                    item_text = autoload_combo.itemText(i)
                    if item_text == self.autoload_preset:
                        return i
                # Reset to first default preset if not found
                _session_presets_msg("Autoload preset '%s' not found, resetting to first default preset." % self.autoload_preset)
                self.autoload_preset = self.default_presets[0].get("name", "")
                self.autoload_preset_is_default = True
                self.save_options()
                return 1
            autoload_combo.setCurrentIndex(find_autoload_index())
            autoload_enabled_checkbox.stateChanged.connect(lambda state: setattr(self, 'setting_autoload_enabled', state == QtCore.Qt.Checked))
            # Custom preset table
            preset_table = QtGui.QTableWidget()
            preset_table.setColumnCount(4)
            preset_table.setHorizontalHeaderLabels(["Order", "Name", "Path", "Description"])
            preset_table.setColumnHidden(0, True)
            preset_table.setColumnWidth(1, 128)
            preset_table.setColumnWidth(2, 256)
            preset_table.horizontalHeader().setStretchLastSection(True)
            preset_table.sortItems(0, QtCore.Qt.AscendingOrder)
            preset_table.setEditTriggers(QtGui.QAbstractItemView.DoubleClicked | QtGui.QAbstractItemView.SelectedClicked)
            # Populate table with current presets
            preset_table.setRowCount(len(self.presets))
            for row, preset in enumerate(self.presets):
                order_item = QtGui.QTableWidgetItem(str(preset.get("order", row)))
                name_item = QtGui.QTableWidgetItem(preset.get("name", ""))
                description_item = QtGui.QTableWidgetItem(preset.get("description", ""))
                preset_path = preset.get("path", "")
                path_item = QtGui.QTableWidgetItem(preset_path)
                # Set color of the text to red if the file does not exist
                if not os.path.isfile(preset_path):
                    path_item.setForeground(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
                path_item.setFlags(path_item.flags() ^ QtCore.Qt.ItemIsEditable)
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
            def reload_presets():
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
            def reload():
                self.reloading = True
                reload_presets()
                rebuild_preset_combo(autoload_combo, append="")
                autoload_combo.setCurrentIndex(find_autoload_index())
                self.reloading = False
            # on double click of an item in the Path column, open file dialog to select new .dmx file
            def edit_path_item(item):
                if item.column() == 2:
                    row = item.row()
                    file_dialog = QtGui.QFileDialog(preset_editor, "Select Preset Session", "", "SFM Session (*.dmx)")
                    file_dialog.setFileMode(QtGui.QFileDialog.ExistingFile)
                    # Default to the directory in dir_edit
                    start_dir = dir_edit.text().strip()
                    if os.path.isdir(start_dir):
                        file_dialog.setDirectory(start_dir)
                    else:
                        file_dialog.setDirectory(self.cwd + r"\usermod\elements\sessions")
                    # If the column currently has a path, set that as the starting file
                    current_path = item.text().strip()
                    if os.path.isfile(current_path):
                        file_dialog.setDirectory(os.path.dirname(current_path))
                        file_dialog.selectFile(current_path)

                    if file_dialog.exec_():
                        selected_files = file_dialog.selectedFiles()
                        if selected_files:
                            file_path = selected_files[0]
                            # Make sure we can access the file
                            if not os.path.isfile(file_path):
                                _session_presets_error_msg("The selected file does not exist:\n%s" % file_path)
                                return
                            # Update item text
                            item.setText(file_path)
                            reload()
            preset_table.itemDoubleClicked.connect(edit_path_item)
            def item_changed(item):
                # If this is the current autoload preset, set autoload_preset to the new name
                if not self.autoload_preset_is_default:
                    if item.column() == 1:
                        new_preset_name = item.text()
                        # Get old preset name based on order column
                        order_item = preset_table.item(item.row(), 0)
                        old_preset_name = ""
                        if order_item:
                            order = int(order_item.text())
                            if 0 <= order < len(self.presets):
                                old_preset_name = self.presets[order].get("name", "")
                        if old_preset_name == self.autoload_preset:
                            self.autoload_preset = new_preset_name
                reload()
            preset_table.itemChanged.connect(item_changed)
            def add_preset():
                # File picker dialog to select a .dmx file
                file_dialog = QtGui.QFileDialog(preset_editor, "Select Preset Session", "", "SFM Session (*.dmx)")
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
                        dmx_converted_path = self.convert_dmx_file(file_path, self.cwd + r"\_temp.dmx")
                        if dmx_converted_path:
                            session_name = self.get_name_from_dmx(dmx_converted_path)
                            if session_name:
                                session_name = session_name
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
                        # Set color of the text to red if the file does not exist
                        if not os.path.isfile(file_path):
                            path_item.setForeground(QtGui.QBrush(QtGui.QColor(255, 0, 0)))
                        path_item.setFlags(path_item.flags() ^ QtCore.Qt.ItemIsEditable)
                        preset_table.setItem(row, 0, order_item)
                        preset_table.setItem(row, 1, name_item)
                        preset_table.setItem(row, 2, path_item)
                        preset_table.setItem(row, 3, description_item)
                        reload()
            def move_up_preset():
                current_row = preset_table.currentRow()
                if current_row > 0:
                    preset_table.insertRow(current_row - 1)
                    for col in range(preset_table.columnCount()):
                        item = preset_table.takeItem(current_row + 1, col)
                        preset_table.setItem(current_row - 1, col, item)
                    preset_table.removeRow(current_row + 1)
                    preset_table.setCurrentCell(current_row - 1, 0)
                    reload()
            def move_down_preset():
                current_row = preset_table.currentRow()
                if current_row < preset_table.rowCount() - 1 and current_row != -1:
                    preset_table.insertRow(current_row + 2)
                    for col in range(preset_table.columnCount()):
                        item = preset_table.takeItem(current_row, col)
                        preset_table.setItem(current_row + 2, col, item)
                    preset_table.removeRow(current_row)
                    preset_table.setCurrentCell(current_row + 1, 0)
                    reload()
            def delete_preset():
                current_row = preset_table.currentRow()
                if current_row != -1:
                    preset_table.removeRow(current_row)
                    reload()
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
                reload_presets()
                self.autoload_enabled = self.setting_autoload_enabled
                self.save_options()
                rebuild_preset_combo(preset_combo, append=" (default)")
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
                
        reg_use_custom = self.get_registry_value("UseCustomFramerate")
        if reg_use_custom == "1":
            custom_framerate_checkbox.setChecked(True)
            self.custom_framerate_checkbox_state = True
        
        reg_framerate = self.get_registry_value("Framerate")
        if reg_framerate is not None:
            framerate_value = float(reg_framerate)
            framerate_edit.setValue(framerate_value)
            framerate_parsed = str(round(framerate_value, 3)).rstrip('0').rstrip('.')
            index = framerate_combo.findText(framerate_parsed)
            if index == -1:
                # Force showing custom framerate
                custom_framerate_checkbox.setChecked(True)
                framerate_edit.setVisible(True)
                framerate_combo.setVisible(False)
            else:
                framerate_combo.setCurrentIndex(index)
                default_framerate_index = index
        
        reg_name = self.get_registry_value("Name")
        if reg_name is not None:
            base_name = reg_name
            # Ensure the name does not already exist in the selected directory
            while os.path.exists(os.path.join(dir_edit.text(), base_name + ".dmx")):
                # If the name ends in numbers, get the numbers and increment by 1
                numbers = ""
                for char in reversed(base_name):
                    if char.isdigit():
                        numbers = char + numbers
                    else:
                        break
                if numbers:
                    new_number = str(int(numbers) + 1)
                    base_name = base_name[:-len(numbers)] + new_number
                else:
                    # Append 1 to the name
                    base_name = base_name + "1"
            name_edit.setText(base_name)
        
        # Startup wizard options
        if startupWizard:
            recent_files = []
            reg_recent_file_list = self.get_registry_value("recentFileList", path=r"Software\Valve\SourceFilmmaker\FileDialogs\SessionDocument")
            if reg_recent_file_list and type(reg_recent_file_list) == list:
                recent_files = reg_recent_file_list
            # Recent sessions group box
            recent_group_box = QtGui.QGroupBox(" Recent Session ", content_widget)
            recent_group_box.setFixedHeight(55)
            recent_group_box.setGeometry(6, 143, 788, 55)
            recent_combo = QtGui.QComboBox(recent_group_box)
            recent_combo.setGeometry(10, 20, 666, 23)
            recent_open_button = QtGui.QPushButton("Open Recent", recent_group_box)
            recent_open_button.setGeometry(682, 20, 100, 23)
            # Populate recent sessions
            for recent_file in recent_files:
                # Make sure file exists
                if os.path.isfile(recent_file):
                    recent_combo.addItem(recent_file)
            # Add starter sessions
            starter_sessions = [
                {
                    "name": "Meet the Heavy",
                    "file": "tf_movies\\elements\\sessions\\mtt_heavy\\mtt_heavy.dmx"
                },
                {
                    "name": "Meet the Engineer",
                    "file": "tf_movies\\elements\\sessions\\mtt_engineer\\mtt_engineer.dmx"
                },
                {
                    "name": "Meet the Soldier",
                    "file": "tf_movies\\elements\\sessions\\mtt_soldier\\mtt_soldier.dmx"
                }
            ]
            if recent_combo.count() > 0:
                recent_combo.insertSeparator(recent_combo.count())
            for session in starter_sessions:
                recent_combo.addItem(session["name"])
            def open_recent_session():
                selected_text = recent_combo.currentText()
                if selected_text == "":
                    return
                # Check if it's one of the starter sessions
                for session in starter_sessions:
                    if selected_text == session["name"]:
                        session_path = os.path.join(self.cwd, session["file"])
                        if self.open_session_file(session_path):
                            # close dialog without creating new session
                            dialog.done(QtGui.QDialog.Rejected)
                            return
                # Otherwise, try to open the selected file
                if self.open_session_file(selected_text):
                    # close dialog without creating new session
                    dialog.done(QtGui.QDialog.Rejected)
            recent_open_button.clicked.connect(open_recent_session)
            # Open session group box
            open_group_box = QtGui.QGroupBox(" Open Session ", content_widget)
            open_group_box.setFixedHeight(55)
            open_group_box.setGeometry(6, 217, 788, 55)
            open_label = QtGui.QLabel("Open an existing session through a file dialog", open_group_box)
            open_label.setGeometry(10, 22, 400, 20)
            open_button = QtGui.QPushButton("Open...", open_group_box)
            open_button.setGeometry(682, 20, 100, 23)
            def open_session():
                file_dialog = QtGui.QFileDialog(dialog, "Open Document", "", "SFM Session (*.dmx)")
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
                        if self.open_session_file(file_path):
                            # close dialog without creating new session
                            dialog.done(QtGui.QDialog.Rejected)
            open_button.clicked.connect(open_session)
            # More (links) group box
            more_group_box = QtGui.QGroupBox(" More... ", content_widget)
            more_group_box.setFixedHeight(46)
            more_group_box.setGeometry(6, 291, 788, 46)
            # <a style="color: #9C8F62" href="http://www.youtube.com/SourceFilmmaker">YouTube</a> <a href="http://www.reddit.com/r/sfm">Reddit</a> <a href="http://www.facebook.com/SourceFilmmaker">Facebook</a> <a href="http://www.twitter.com/#!SourceFilmmaker" <a href="http://www.sourcefilmmaker.com/faq">FAQ</a> <a href="http://developer.valvesoftware.com/wiki/Source_Filmmaker">Wiki</a>
            link_color = "#9C8F62"
            links = [
                {
                    "name": "YouTube",
                    "url": "http://www.youtube.com/SourceFilmmaker"
                },
                {
                    "name": "Reddit",
                    "url": "http://www.reddit.com/r/sfm"
                },
                {
                    "name": "Facebook",
                    "url": "http://www.facebook.com/SourceFilmmaker"
                },
                {
                    "name": "Twitter",
                    "url": "http://www.twitter.com/#!SourceFilmmaker"
                },
                {
                    "name": "FAQ",
                    "url": "http://www.sourcefilmmaker.com/faq"
                },
                {
                    "name": "Wiki",
                    "url": "http://developer.valvesoftware.com/wiki/Source_Filmmaker"
                }
            ]
            links_html = "Additional information can be found on the internet: "
            for i in range(len(links)):
                link = links[i]
                links_html += '<a style="color: %s" href="%s">%s</a>' % (link_color, link["url"], link["name"])
                if i < len(links) - 1:
                    links_html += " | "
            more_label = QtGui.QLabel(links_html, more_group_box)
            more_label.setTextFormat(QtCore.Qt.RichText)
            more_label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
            more_label.setOpenExternalLinks(True)
            more_label.setGeometry(12, 17, 770, 20)
        
        main_layout.addWidget(content_widget)
        main_layout.addWidget(lower_bar)

        # Connect create button
        preset_changed(preset_combo.currentIndex())
        check_create_enabled()
        
        # Show dialog
        result = dialog.exec_()
        if result == QtGui.QDialog.Accepted:
            filename = name_edit.text()
            preset_index = preset_combo.currentIndex()
            directory = dir_edit.text()
            framerate = 24.0
            
            if custom_framerate_checkbox.isChecked():
                framerate = float(framerate_edit.value())
            else:
                framerate = float(framerate_combo.currentText())
            # make sure file does not already exist
            full_filename = os.path.join(directory, filename + ".dmx")
            if os.path.exists(full_filename):
                return
            if self.create_session(preset_index, framerate, filename, directory):
                # Save values to registry
                self.set_registry_value("Directory", directory)
                self.set_registry_value("Name", filename)
                self.set_registry_value("Framerate", str(round(framerate, 3)).rstrip('0').rstrip('.'))
                self.set_registry_value("UseCustomFramerate", "1" if custom_framerate_checkbox.isChecked() else "0")
        return result
    def open_session_file(self, file_path):
        if not os.path.isfile(file_path):
            _session_presets_error_msg("The selected session file does not exist:\n%s" % file_path)
            return False
        if sfmApp.HasDocument():
            sfmApp.CloseDocument(forceSilent=False)
        if sfmApp.HasDocument():
            # User cancelled close (unsaved changes)
            return False
        sfmApp.OpenDocument(file_path)
        return True
    def get_registry_value(self, value_name, path=r"Software\Valve\SourceFilmmaker\NewSessionWizard"):
        # SFM stores the following values:
        # - Directory REG_SZ D:/steamlibrary/steamapps/common/sourcefilmmaker/game/usermod/elements/sessions
        # - Framerate REG_SZ 24
        # - Name REG_SZ session
        # - UseCustomFramerate REG_SZ 0 or 1 (may not exist)
        # We will read from here and then write back when creating a new session
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as key:
                value, regtype = winreg.QueryValueEx(key, value_name)
                return value
        except Exception as e:
            _session_presets_msg("Error reading registry value %s: %s" % (value_name, e))
            return None
    def set_registry_value(self, value_name, value, path=r"Software\Valve\SourceFilmmaker\NewSessionWizard"):
        # Check if key exists, create if not
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
                pass
        except FileNotFoundError:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
                pass
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, value)
        except Exception as e:
            _session_presets_msg("Error writing registry value %s: %s" % (value_name, e))

def _SessionPresets_FirstBoot():
    try:
        # Create window if it doesn't exist
        already_initialized = False
        sessionpresets = globals().get("_session_presets")
        if sessionpresets is not None:
            already_initialized = True
            # Delete existing instance
            del globals()["_session_presets"]
        sessionpresets = SessionPresets(already_initialized=already_initialized)
        globals()["_session_presets"] = sessionpresets
    except Exception  as e:
        traceback.print_exc()
        _session_presets_error_msg("Error: %s" % e)

_SessionPresets_FirstBoot()
