# SFM Session Presets Script: For a Faster Workflow

Pick from a list of presets to apply to new sessions and pick a preset to load when SFM starts.

Also adds the ability to set a custom framerate for new sessions.

Requires [Autoinit Manager](https://steamcommunity.com/sharedfiles/filedetails/?id=3400621327) to work.

View the changelog [here](https://steamcommunity.com/workshop/filedetails/discussion/3648643720/742664166129751165/).

[Workshop Link](https://steamcommunity.com/sharedfiles/filedetails/?id=3648643720)

## Usage

Perform the following steps to use this script:

- Install [Autoinit Manager](https://steamcommunity.com/sharedfiles/filedetails/?id=3400621327) and this script from the Steam Workshop.
- Once SFM has updated the Workshop items, restart SFM.
- You should see the startup wizard appear when SFM starts, now with new options. You can use File -> New to open the new session menu at any time.
- You can create and manage presets by clicking "Edit..." in the startup wizard.

## Autoload Preset

To set a preset to autoload when SFM starts:

- Open the startup wizard when SFM starts or click File -> New to open the new session menu.
- Click "Edit..." to open the preset editor.
- Select a preset in the dropdown menu at the top.
- Select the "Load automatically when SFM starts" checkbox.
- Click "OK" to save the changes.
- Restart SFM, the selected preset should load automatically.

## Included Presets

The script comes with default presets for common use cases:

- Blank (automatically selected by default): An empty session without a map or camera. This is what SFM uses by default.
- Stage, Camera, Light: Uses the stage map with a camera in the center and key, bounce, fill, and rim lights set up.
- Dark Room: Uses the dark_room map with a camera set up in the corner.

## Custom Presets

You can create your own custom presets to show up in the preset list:

- Create a new session in SFM with the desired setup (map, camera, lights, etc).
- Save the session as a DMX file in a known location.
- Open the new session menu by clicking File -> New.
- Click "Edit..." to open the preset editor.
- Click "Add" and select the DMX file you saved earlier.
- The preset will be added to the list, you can rename it and set a description if desired.
- If you'd like this preset to be selected as default, select it in the dropdown menu at the top.
- To load this preset automatically when SFM starts, select the "Load automatically when SFM starts" checkbox.
- To remove a preset, select it in the list and click "Remove".
- Click "OK" to save the changes.

## Development

Please consider supporting my work through [Ko-fi](https://ko-fi.com/kiwifruitdev)! 💚

This script is available on [GitHub](https://github.com/KiwifruitDev/sfm_session_presets) and is licensed under the [MIT License](https://github.com/KiwifruitDev/sfm_session_presets/blob/main/LICENSE).

Feel free to credit me as KiwifruitDev if you use or modify this script, I'd really appreciate it!
