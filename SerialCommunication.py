import serial.tools.list_ports
import time
# import datetime


class SerialCommunication:

    def __init__(self) -> None:
        self.baudrate = 115200
        self.comport = None
        self.serial = None
        self.connected_to_device = False
        self.connected_to_kambala = False
        self.kambala_UniqueID = None

        self.MSG = {
            'HELLO': 'id',
            'HELLO_REPLY': "Kampela's testing fixture",
        }

    def get(self, exec_timeout=5):
        """
        Try to Get decoded data from com port (maximum execution time = exec_max_time sec)
        """
        start_time = time.time()
        continue_exec = True
        reply = ""
        while continue_exec and (time.time()-start_time) < exec_timeout:
            # sync_data = self.serial.readline().decode("utf-8").replace("\r", "").replace("\n", "")
            sync_data = self.serial.readline().decode("utf-8")
            if "***" in sync_data:
                continue_exec = False
            else:
                reply += sync_data
                time.sleep(0.001)
        print("MPU to PS: <<", reply)
        return reply

    def request(self, msg_txt, exec_timeout=5):
        self.send(msg_txt)
        return self.get(exec_timeout=exec_timeout)

    def connect(self):
        """
        Search for device: try to connect to each com port and send hello-message
        """
        if not self.connected_to_device:
            # get list of all ports
            com_ports = [port.device for port in serial.tools.list_ports.comports()]
            # try to connect to each port
            for port in com_ports:

                print(f"Serial port {port}")

                if self.connected_to_device:
                    return
                try:
                    self.serial.is_open
                except Exception:
                    self.serial = serial.Serial(port=port, baudrate=self.baudrate, timeout=1.0)

                try:
                    if not self.serial.is_open:
                        self.serial = serial.Serial(port=port, baudrate=self.baudrate, timeout=1.0)
                        # self.serial.open()
                    self.serial.reset_input_buffer()
                    self.serial.reset_output_buffer()
                    self.comport = port
                    self.serial.status = True

                    print(f"Start Serial Connection with {port}")
                    print(f"Connection status = {self.serial.is_open}")
                    self.hello()

                except Exception as e:
                    self.serial.status = False

        print(f"Device connected: {self.connected_to_device} \tPort: {self.comport}")

    def hello(self):
        """
        Send hello-message to initialize the connection
        """
        if self.serial and self.serial.status:
            self.send(self.MSG["HELLO"])
            reply = self.get(exec_timeout=1)
            self.connected_to_device = True if self.MSG['HELLO_REPLY'].lower() in reply.lower() else False

    def disconnect(self):
        """
        Close Serial Connection
        """
        try:
            if self.serial.is_open:
                self.serial.close()
                self.serial.status = False
                self.connected_to_device = False
                self.comport = None
        except Exception as e:
            print(e)

    def send(self, msg_txt):
        """
        Send encoded text message to com port
        """
        if self.serial and self.serial.status:
            self.serial.write((msg_txt + '\n').encode())
            print("PC to MPU: >>", msg_txt)



if __name__ == "__main__":
    print("Serial Communication module")
    sc = SerialCommunication()
    sc.connect()
    sc.request('getadc')
    time.sleep(1)
    # sc.request('nfccheck')
    # sc.request('beep 10')
    # sc.request('dis')
    # sc.request('allinput')
    # sc.request('field 3400')
    # sc.request('field kukuG')
    # time.sleep(2)
    # sc.request('getrgb')
    # sc.request('field 0')
    # sc.request('led 0 100 255')
    # time.sleep(5.0)
    sc.disconnect()



