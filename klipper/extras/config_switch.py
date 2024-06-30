import os
import logging

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


    cmd_SAVE_CONFIG_MODE_help = "Save session variables, marked in printer.cfg"
    def cmd_SAVE_CONFIG_MODE(self, gcmd):
        ## Variables
        home_dir = os.path.expanduser("~")
        destination = ""
        record = False

        printer_config = os.path.join(home_dir, "printer_data/config/printer.cfg")
        config_dir = os.path.join(home_dir, "printer_data/config/config")
        config_wt_dock = os.path.join(config_dir, "config_wt_dock.cfg")
        config_no_dock = os.path.join(config_dir, "config_no_dock.cfg")

        ## Make the config folder, if it is not already there
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        ## Decide where it should be saved
        with open(printer_config) as file:
            for line in file:
                ## Set destination file
                if "variable_dock:" in line.strip():
                    if "True" in line.strip():
                        destination = config_wt_dock
                    elif "False" in line.strip():
                        destination = config_no_dock
                    else:
                        raise gcmd.error("[variable_dock: ] must be 'True' or 'False'")
        
        ## Save session variables
        with open(printer_config) as file:
            if destination != "":
                with open(destination, 'w'):
                    pass
                for line in file:
                    ## Record point begin / end
                    if "#;<" in line.strip():
                        record = True
                    if "#;>" in line.strip():
                        record = False
                    
                    ## Start / Stop record
                    if record is True:
                        with open(destination, 'a') as savefile:
                            savefile.write(line)
                
                if "config_wt_dock" in destination:
                    self.gcode.respond_info("Session variables saved to config/config_wt_dock.cfg")
                elif "config_no_dock" in destination:
                    self.gcode.respond_info("Session variables saved to config/config_no_dock.cfg")


    cmd_TOGGLE_CONFIG_MODE_help = "Toggle saved session variable in printer.cfg"
    def cmd_TOGGLE_CONFIG_MODE(self, gcmd):
        ## Variables
        home_dir = os.path.expanduser("~")
        source = ""
        record = True

        printer_config = os.path.join(home_dir, "printer_data/config/printer.cfg")
        config_dir = os.path.join(home_dir, "printer_data/config/config")
        config_wt_dock = os.path.join(config_dir, "config_wt_dock.cfg")
        config_no_dock = os.path.join(config_dir, "config_no_dock.cfg")
        config_temp = os.path.join(config_dir, "printer.temp")

        ## Detect and toggle current config
        with open(printer_config) as file:
            for line in file:
                if "variable_dock:" in line.strip():
                    if "True" in line.strip():
                        source = config_no_dock
                    elif "False" in line.strip():
                        source = config_wt_dock
                    else:
                        raise gcmd.error("[variable_dock: ] must be 'True' or 'False'")
        
        ## Compile new printer.cfg in printer.temp
        if source != "":
            if os.path.exists(source):
                self.gcode.respond_info("Toggle current session variables to:\n" + source)
                with open(source, 'r') as session_variable_source:
                    source_content = session_variable_source.read()

                with open(printer_config) as file:
                    self.gcode.respond_info("Compile config/printer.temp ...")
                    with open(config_temp, 'w'):
                                pass
                    
                    for line in file:
                        ## Record point begin / end
                        if "#;<" in line.strip():
                            record = False
                        if "#;>" in line.strip():
                            record = True

                        ## Start / Stop record
                        if record is True:
                            with open(config_temp, 'a') as tempfile:
                                tempfile.write(line)
                    
                with open(config_temp, 'a') as tempfile:
                    tempfile.write(source_content)

                with open(config_temp, 'r') as tempfile:
                    temp_config = tempfile.read()
                
                with open(printer_config, 'w') as configfile:
                    self.gcode.respond_info("Update printer.cfg ...")
                    configfile.write(temp_config)
                
                if os.path.exists(config_temp):
                    self.gcode.respond_info("Remove config/printer.temp ...")
                    os.remove(config_temp)
            else:
                raise gcmd.error("Missing file:\n" + source)


def load_config(config):
    return ConfigSwitch(config)
