import time
from PyQt5.QtCore import QObject, pyqtSignal
import re


class TestWorker(QObject):

    started = pyqtSignal()
    finished = pyqtSignal()
    spec_error = pyqtSignal()
    tester_error = pyqtSignal(str)
    update = pyqtSignal(dict)
    getv_data = pyqtSignal(dict)

    CMD = {
        'SETV': 'power',
        'GETV': 'getv',
        'DISCH': 'dis',
        'CONNECT': 'con',
        'ALL_INPUT': 'allinput',
        'FIELD': 'field',
        'SETP': 'portset',
        'GETL': 'getrgb',
        'WAIT': 'wait',
        'BEEP': 'beep',
        'NFC': 'nfccheck'
    }

    def __init__(self, root):
        super().__init__()
        self.root = root
        self.config = self.root.spec_parser.config
        self.stop_test = False
        self.abort_test = False
        self.errors = []

    def run(self):
        test = self.config["TEST"]

        self.started.emit()
        try:
            for instruction_item in test.items():
            # for line_num, instruction in test.items():
                ts_start = time.time()
                instruction_result = self.handler(instruction_item)
                instruction_result['execution_time'] = time.time()-ts_start
                instruction_result['ts_start'] = ts_start
                if instruction_result['error']:
                    self.errors.append(instruction_result['error'])
                    self.root.serialCtrl.request('beep 200')
                    self.spec_error.emit()
                self.update.emit(instruction_result)
                if self.stop_test:
                    self.tester_error.emit(f"Unable to continue the test")
                    self.root.serialCtrl.request('power 0')
                    return
                if self.abort_test:
                    self.tester_error.emit(f"Test is aborted")
                    self.root.serialCtrl.request('power 0')
                    return
            # in the end of test
            if len(self.errors):
                for _ in range(3):
                    self.root.serialCtrl.request('beep 200')
                    time.sleep(0.2)
            # no errors
            else:
                for _ in range(2):
                    self.root.serialCtrl.request('beep 50')
                    time.sleep(0.100)
        except Exception as e:
            self.tester_error.emit(f"An error occurred: {repr(e)}")
        finally:
            try:
                self.root.serialCtrl.request('power 0')
            except Exception as final_e:
                self.tester_error.emit(f"Unable to safely finish communication. Error: {repr(e)}")
        self.finished.emit()

    @staticmethod
    def params_parcer(command):
        regexp = r"(.+),\s*MSG\s*\"(.+)\""
        match = re.search(regexp, command)
        if match:
            return {'conditions': match[1], 'err_msg': match[2]}
        else:
            return False

    def handler(self, instruction_item):
        """
        :param instruction: dictionary {'command': 'SETV', 'params': '0'}
        :return: text log line
        """
        instruction_number, instruction = instruction_item
        command, params = instruction.values()

        result = {
            'number': instruction_number,
            'command': command,
            'params': params,
            'request': self.CMD[command],
            'response': "",
            'error': False
        }
        msg_ok = 'OK'
        msg_error = 'ERROR'
        err_msg_formate = f'{msg_error}: invalid command formate: {command} = {params}'
        err_msg_handler_not_found = f"{msg_error} The handler for {command} is not found"

        if command == 'BEEP':
            result['request'] += f' {params}'
            result['response'] = self.root.serialCtrl.request(result['request'])

        elif command == 'SETV':
            result['request'] += f' {params}'
            result['response'] = self.root.serialCtrl.request(result['request'])
            if 'power' not in result['response']:
                result['error'] = 'Incorrect SETV response'

        elif command == 'DISCH':
            response = self.root.serialCtrl.request(result['request'])
            result['response'] = response
            if params == '1':
                capacity = int(response.replace("Cap size raw is ", "").strip())
                check = self.check_speck('CAPACITY', capacity)
                if not check['within']:
                    result['error'] = "Capacitance is not in spec"
                result['details'] = [check['details'], ]

        elif command == 'GETV':
            result['response'] = self.root.serialCtrl.request(result['request'])
            adc_values = list(map(float, result['response'].split(',')))
            adc_sorted = sorted(self.config["ADC"].items(), key=lambda x: int(x[1]))
            # adc_names = [x[0] for x in adc_sorted]
            adc_items = dict(zip([x[0] for x in adc_sorted], adc_values))
            self.getv_data.emit(adc_items)
            # formate: [VALUE_FROM_ADC] in range of [SPEC], ..., else MSG = [ERROR_MESSAGE]
            param_parts = self.params_parcer(params)
            if param_parts:
                conditions = list(map(str.strip, param_parts['conditions'].split(',')))
                details = []
                for cond in conditions:
                    cond_values = list(map(str.strip, cond.split('*')))
                    adc_number = int(self.config["ADC"][cond_values[0]])
                    check = self.check_speck(cond_values[1], adc_values[adc_number])
                    details.append(check['details'])
                    if not check['within']:
                        result['error'] = param_parts['err_msg']
                result['details'] = details
            else:
                result['error'] = err_msg_formate

        elif command == 'WAIT':
            result['request'] += f' {params}'
            time.sleep(int(params) / 1000)

        elif command == 'CONNECT':
            param_parts = self.params_parcer(params)
            if param_parts:
                result['response'] = self.root.serialCtrl.request(result['request'])
                if 'error' in result['response'].lower():
                    self.stop_test = True
                    result['error'] = param_parts['err_msg']
                    return result
                else:
                    # get kambala UniqueID
                    reg_uid = r"UniqueID\s*(\S*)\s"
                    uid_match = re.search(reg_uid, result['response'], re.MULTILINE)
                    if uid_match:
                        self.root.lbl_uniqueID.setText("ID: " + uid_match[1])
                        self.root.serialCtrl.connected_to_kambala = True
                        self.root.serialCtrl.kambala_UniqueID = uid_match[1]
                    else:
                        result['error'] = f"Unable to find UniqueID"
                        return result
            else:
                result['error'] = err_msg_formate

        elif command == 'ALL_INPUT':
            param_parts = self.params_parcer(params)
            if param_parts:
                result['response'] = self.root.serialCtrl.request(result['request'])
                if 'OK' not in result['response']:
                    self.stop_test = True
                    result['error'] = param_parts['err_msg']
                    return result
            else:
                result['error'] = err_msg_formate

        elif command == 'SETP':
            ports = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
            inouts = {'IN': 0, 'OUT': 1}
            port_pin, in_out, out_state = list(map(str.strip, params.split(',')))
            port, pin = self.config["KAMBALA"][port_pin].values()
            result['request'] += f' {ports[port]} {pin} {inouts[in_out]} {out_state}'
            result['response'] = self.root.serialCtrl.request(result['request'])
            if 'OK' not in result['response']:
                result['error'] = "Invalid SETP result"

        elif command == 'FIELD':
            if params in self.config["VARS"]:
                params = self.config["VARS"][params]
            result['request'] += f' {params}'
            result['response'] = self.root.serialCtrl.request(result['request'])
            if 'field' not in result['response']:
                result['error'] = "Something went wrong"

        elif command == 'GETL':
            result['response'] = self.root.serialCtrl.request(result['request'])
            if not result['response']:
                result['error'] = "No response"
                return result
            rgbcir_raw = list(map(str.strip, result['response'].split(',')))
            rgbcir = {value.split(':')[0].lower(): int(value.split(':')[1]) for value in rgbcir_raw}
            param_parts = self.params_parcer(params)
            if param_parts:
                spec = self.config["LED_SPEC"][param_parts['conditions']]
                is_spec = []
                details = []
                sign_to_str = {'>': 'more', '<': 'less'}
                for key, value in rgbcir.items():
                    if key in ['r', 'g', 'b']:
                        msg = f'{key}: '
                        msg_details = (f"\t ("
                                       f"value = {round(rgbcir[key] / rgbcir['c'], 3)} "
                                       f"must be {sign_to_str[spec[key]['sign']]} "
                                       f"than {spec[key]['value']})")
                        check_res = eval(f"{rgbcir[key] / rgbcir['c']} {spec[key]['sign']} {spec[key]['value']}")
                        is_spec.append(check_res)
                        msg += msg_ok if check_res else msg_error
                        details.append(msg + msg_details)
                result['details'] = details
                if not all(is_spec):
                    result['error'] = param_parts['err_msg']
            else:
                result['error'] = err_msg_formate

        elif command == 'NFC':
            result['response'] = self.root.serialCtrl.request(result['request'])
            reg_nfc = r"Nfc\s+Packs:\s+(\d+)\s+Nfc\s+Rate:\s+([\d.]+)"
            nfc_match = re.search(reg_nfc, result['response'], re.MULTILINE)
            if nfc_match:
                nfc_packs_check = self.check_speck('NFC_PACKS', nfc_match[1])
                nfc_rate_check = self.check_speck('NFC_RATE', nfc_match[2])
                if not (nfc_packs_check['within'] and nfc_rate_check['within']):
                    result['error'] = "NFC is not in spec"
                result['details'] = [nfc_packs_check['details'], nfc_rate_check['details']]
            else:
                result['error'] = f"Unable to get NFC packs and NFC rate"
            return result

        else:
            result['error'] = err_msg_handler_not_found

        return result

    def check_speck(self, param_name, param_value):
        param_value = float(param_value)
        if param_name in self.config['SPEC']:
            spec, tolerance = list(map(float, self.config["SPEC"][param_name].values()))
            within = spec - tolerance <= param_value <= spec + tolerance
            ok_msg = "OK" if within else "ERROR"
            result = {'spec': spec,
                      'tolerance': tolerance,
                      'within': within,
                      'details': f'{param_name}: {ok_msg}\t (value = {param_value}; spec = {spec}; tolerance = {tolerance})'
                      }
            return result
        else:
            return None

