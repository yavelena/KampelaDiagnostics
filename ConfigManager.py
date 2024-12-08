import os.path


class ConfigManager:

    def __init__(self) -> None:
        self.file_path = None
        self.title = None
        self.config = None
        self.load_error = None

    def load_config(self, filepath):
        self.file_path = filepath
        if os.path.isfile(self.file_path):
            with open(filepath, 'r') as config_file:
                lines = config_file.readlines()

                section = False
                data = {}
                test_line_num = 0

                try:
                    self.config = {}
                    for row_line in lines:
                        line = row_line.strip()

                        if not len(line) or line[0] == '#':
                            continue

                        if line[0] == '[' and line[-1] == ']':
                            if section:
                                self.config[section] = data
                            section = line[1: -1]
                            data = {}

                        elif '=' in line:
                            key, value = [x.strip() for x in line.split('=')]
                            if section == "NAME":
                                self.title = value.strip(" \'\"")
                            elif section == "KAMBALA":
                                port, pin = value.split('.')
                                value = {'port': port, 'pin': pin}
                            elif section == "SPEC":
                                spec, tolerance = [float(x.strip(" ")) for x in value.split(',')]
                                value = {'spec': spec, 'tolerance': tolerance}
                            elif section == "LED_SPEC":
                                r, g, b = [x.strip(" ") for x in value.split(',')]
                                value = {
                                    'r': {'sign': r[0], 'value': r[1:]},
                                    'g': {'sign': g[0], 'value': g[1:]},
                                    'b': {'sign': b[0], 'value': b[1:]}
                                }
                            elif section == "TEST":
                                value = {'command': key, 'params': value}
                                key = test_line_num
                                test_line_num += 1

                            data[key] = value
                    self.config[section] = data

                except Exception as e:
                    self.config = None
                    self.load_error = repr(e)

    def save_config(self, data: dict):
        with open(self.file_path, 'w+') as config_file:
            config = []
            for key, value in data.items():
                if type(value) == dict:
                    config.append(f'\n[{key}]')
                    for k, v in value.items():
                        config.append(f'\n{k} = {v}')
                else:
                    config.append(f'\n{key} = {value}')
            config_file.writelines(config)
