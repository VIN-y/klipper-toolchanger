# Copyright (C) 2024 Chinh Nhan Vo <nhanvo29@proton.me>
# Improved 2026 by Frank Paynter / Grok – fix section replacement, marker handling,
# and prevent progressive corruption of printer.cfg
#
# This file may be distributed under the terms of the GNU GPLv3 license.
#
import os
import logging
import shutil
from datetime import datetime

class ConfigSwitch:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        ## Register Commands
        self.gcode.register_command('SAVE_CONFIG_MODE',
                                    self.cmd_SAVE_CONFIG_MODE,
                                    desc=self.cmd_SAVE_CONFIG_MODE_help)
        self.gcode.register_command('TOGGLE_CONFIG_MODE',
                                    self.cmd_TOGGLE_CONFIG_MODE,
                                    desc=self.cmd_TOGGLE_CONFIG_MODE_help)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_paths(self):
        home_dir = os.path.expanduser("~")
        printer_config = os.path.join(home_dir, "printer_data/config/printer.cfg")
        config_dir = os.path.join(home_dir, "printer_data/config/config")
        return {
            "printer": printer_config,
            "dir": config_dir,
            "wt": os.path.join(config_dir, "config_wt_dock.cfg"),
            "no": os.path.join(config_dir, "config_no_dock.cfg"),
            "temp": os.path.join(config_dir, "printer.temp"),
        }

    def _ensure_config_dir(self, config_dir):
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

    def _read_lines(self, path):
        with open(path, "r") as f:
            return f.readlines()

    def _write_lines(self, path, lines):
        with open(path, "w") as f:
            f.writelines(lines)

    def _find_markers(self, lines):
        """Return (start_idx, end_idx) inclusive, or raise."""
        start = end = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if "#;<" in stripped:
                if start is not None:
                    raise self.gcode.error("Multiple '#;<' markers found in printer.cfg")
                start = i
            if "#;>" in stripped:
                if end is not None:
                    raise self.gcode.error("Multiple '#;>' markers found in printer.cfg")
                end = i
        if start is None or end is None:
            raise self.gcode.error(
                "Missing '#;<' or '#;>' marker in printer.cfg – "
                "the swappable section is not defined"
            )
        if end <= start:
            raise self.gcode.error("'#;>' appears before '#;<' – markers are inverted")
        return start, end

    def _get_current_dock_state(self, lines):
        for line in lines:
            if "variable_dock:" in line.strip():
                if "True" in line:
                    return True
                if "False" in line:
                    return False
        raise self.gcode.error(
            "Could not find a valid 'variable_dock: True/False' line inside the marked section"
        )

    # ------------------------------------------------------------------
    # SAVE_CONFIG_MODE
    # ------------------------------------------------------------------
    cmd_SAVE_CONFIG_MODE_help = "Save the marked session-variable section to the appropriate config_*.cfg"
    def cmd_SAVE_CONFIG_MODE(self, gcmd):
        paths = self._get_paths()
        self._ensure_config_dir(paths["dir"])

        lines = self._read_lines(paths["printer"])
        start, end = self._find_markers(lines)
        dock = self._get_current_dock_state(lines[start:end+1])

        dest = paths["wt"] if dock else paths["no"]
        section = lines[start:end+1]          # inclusive – keeps both markers

        self._write_lines(dest, section)

        name = "config_wt_dock.cfg" if dock else "config_no_dock.cfg"
        self.gcode.respond_info(f"Session variables (incl. markers) saved to config/{name}")

    # ------------------------------------------------------------------
    # TOGGLE_CONFIG_MODE
    # ------------------------------------------------------------------
    cmd_TOGGLE_CONFIG_MODE_help = "Replace the marked section with the opposite config_*.cfg (in-place)"
    def cmd_TOGGLE_CONFIG_MODE(self, gcmd):
        paths = self._get_paths()
        self._ensure_config_dir(paths["dir"])

        lines = self._read_lines(paths["printer"])
        start, end = self._find_markers(lines)
        dock = self._get_current_dock_state(lines[start:end+1])

        # Choose the opposite file
        source = paths["no"] if dock else paths["wt"]
        if not os.path.exists(source):
            raise self.gcode.error(f"Missing source file: {source}")

        new_section = self._read_lines(source)
        # Sanity-check the incoming section has the markers
        if not any("#;<" in l for l in new_section) or not any("#;>" in l for l in new_section):
            raise self.gcode.error(
                f"{os.path.basename(source)} is missing '#;<' or '#;>' – "
                "run SAVE_CONFIG_MODE first on a clean printer.cfg"
            )

        # Optional safety backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = paths["printer"] + f".bak_{timestamp}"
        shutil.copy2(paths["printer"], backup)
        self.gcode.respond_info(f"Backup created: {os.path.basename(backup)}")

        # Build the new file: everything before start + new section + everything after end
        new_lines = lines[:start] + new_section + lines[end+1:]

        self._write_lines(paths["printer"], new_lines)
        self.gcode.respond_info(
            f"Toggled to {'no-dock' if dock else 'with-dock'} configuration "
            f"(section replaced in-place)"
        )


def load_config(config):
    return ConfigSwitch(config)