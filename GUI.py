import os
from datetime import datetime
import json

import pyqtgraph as pg
import sqlite3 as sql



from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QMainWindow, QFileDialog, QDesktopWidget, QMessageBox,
    QGroupBox, QPushButton, QLabel, QScrollArea,
    QGridLayout, QVBoxLayout, QProgressBar,
)
from SerialCommunication import SerialCommunication
from ConfigManager import ConfigManager
from TestWorker import TestWorker


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # Try to Connect to Device
        self.serialCtrl = SerialCommunication()
        self.serialCtrl.connect()

        self.init_Root_UI()
        self.init_Connection_UI()
        self.plots = dict()
        self.init_Test_UI()
        self.layouts()

        self.__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
        self.config_file_name = 'config.cfg'
        self.spec_file_name = None
        self.log_dir_path = self.__location__
        self.log_dir_name = 'TEST_REPORTS'
        self.log_file_name = None
        self.config_manager = ConfigManager()
        self.spec_parser = ConfigManager()
        self.web_dir_name = 'WEB'
        self.db_dir_name = 'db'
        self.db_name = 'kampure.db'

        self.config_manager.load_config(os.path.join(self.__location__, self.config_file_name))

        if not self.config_manager.config:
            if self.config_manager.load_error:
                self.show_messagebox(self.config_manager.load_error, 2, 'Config loading ERROR')
                # config file doesn't exist, create a new config
                self.config_manager.config = {
                    'spec': {'file_path': ''},
                    'logs': {'dir_path': self.log_dir_path},
                }
        else:
            try:
                self.spec_file_name = self.config_manager.config['spec']['file_path']
            except KeyError:
                self.show_messagebox('Unable to get spec file path from config', _type=2, title='Error')

            try:
                if os.path.exists(self.config_manager.config['logs']['dir_path']):
                    self.log_dir_path = self.config_manager.config['logs']['dir_path']
            except KeyError:
                pass

        if self.spec_file_name:
            self.load_spec()

        self.screen_log_txt = ''
        self.file_log_txt = ''
        self.db_log_data = []

        self.setup_Connection_UI()
        self.setup_Test_UI()

    def init_Root_UI(self):
        screen = QDesktopWidget().screenGeometry()
        self.setGeometry(0, 0, screen.width() - 10, screen.height() - 100)
        self.setWindowTitle("Kampure Test")
        self.widget_root = QWidget()
        self.setCentralWidget(self.widget_root)
        self.layout_Root = QGridLayout()
        self.widget_root.setLayout(self.layout_Root)

    def init_Connection_UI(self):
        self.grbox_Connect = QGroupBox("Connection")

        self.btn_connect = QPushButton()
        self.btn_connect.setCheckable(True)
        self.btn_connect.clicked.connect(self.on_Connect)
        self.btn_connect.setChecked(self.serialCtrl.connected_to_device)

        self.lbl_connection_status = QLabel("...")

        self.btn_open_config_file = QPushButton("Load configuration")
        self.btn_open_config_file.clicked.connect(self.openSpecFileNameDialog)
        self.btn_open_config_file.setEnabled(False)

        self.lbl_config_file_status = QLabel("...")

    def init_Test_UI(self):
        self.grbox_Test = QGroupBox("Test")
        self.grbox_Test.setEnabled(False)

        self.lbl_title = QLabel('Test Title')
        self.lbl_title.setFont(QFont('Arial', 14))

        self.lbl_uniqueID = QLabel('')
        self.lbl_uniqueID.setFont(QFont('Arial', 28))

        self.btn_start_test = QPushButton("Start test")
        self.btn_start_test.setFont(QFont('Arial', 14))
        self.btn_start_test.setMinimumHeight(100)
        self.btn_start_test.setStyleSheet("background-color: #a3d6bc")
        self.btn_start_test.clicked.connect(self.startTest)

        self.btn_stop_test = QPushButton("Stop test")
        self.btn_stop_test.setFont(QFont('Arial', 14))
        self.btn_stop_test.setMinimumHeight(100)
        self.btn_stop_test.setStyleSheet("background-color: #ffffb5")
        self.btn_stop_test.clicked.connect(self.stopTest)
        self.btn_stop_test.setEnabled(False)

        self.progress_bar_test = QProgressBar(self)
        self.progress_bar_test.setValue(0)

        self.lbl_test_status = QLabel('N/A')
        self.lbl_test_status.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_test_status.setFont(QFont('Arial', 40))
        self.lbl_test_status.setMargin(20)
        self.set_test_status(0)

        self.grbox_Test_Plots = QGroupBox("")
        self.lbl_test_log = ScrollLabel(self)
        # self.grbox_Test_Plots.setStyleSheet("background-color: #ffffb5")
        self.lbl_test_log.setFont(QFont('Arial', 10))
        self.lbl_test_log.setGeometry(100, 100, 200, 80)
        self.graphics_layout_widget = pg.GraphicsLayoutWidget(parent=self.grbox_Test_Plots, show=True)
        self.graphics_layout_widget.setBackground('w')

    def layouts(self):
        self.layout_Root.addWidget(self.grbox_Connect, 0, 0)
        self.layout_Root.addWidget(self.grbox_Test, 1, 0)

        self.layout_Сonnect = QGridLayout()
        self.layout_Сonnect.addWidget(self.btn_connect, 0, 0)
        self.layout_Сonnect.addWidget(self.lbl_connection_status, 0, 1)
        self.layout_Сonnect.addWidget(self.btn_open_config_file, 1, 0)
        self.layout_Сonnect.addWidget(self.lbl_config_file_status, 1, 1)
        self.grbox_Connect.setLayout(self.layout_Сonnect)

        self.layout_Test = QGridLayout()
        self.layout_Test.addWidget(self.lbl_title, 0, 0, 1, 2)
        self.layout_Test.addWidget(self.lbl_uniqueID, 0, 2, 1, 2)
        self.layout_Test.addWidget(self.lbl_test_status, 0, 4, 3, 2)
        self.layout_Test.addWidget(self.btn_start_test, 1, 0, 1, 2)
        self.layout_Test.addWidget(self.btn_stop_test, 1, 2, 1, 2)
        self.layout_Test.addWidget(self.progress_bar_test, 2, 0, 1, 4)

        self.layout_Test.addWidget(self.lbl_test_log, 3, 0, 1, 3)
        self.layout_Test.addWidget(self.graphics_layout_widget, 3, 3, 1, 3)
        # self.layout_Test.addWidget(self.grbox_Test_Plots, 2, 3, 1, 3)
        self.grbox_Test.setLayout(self.layout_Test)

    def setup_Connection_UI(self):
        """
        Set/update widgets in Connect panel depending on current Serial Connection status
        """
        if self.serialCtrl.connected_to_device:
            self.btn_connect.setText("Disconnect")
            self.lbl_connection_status.setText(f"Connected to port {self.serialCtrl.comport}")
            self.btn_open_config_file.setEnabled(True)
            if self.spec_parser.file_path:
                self.lbl_config_file_status.setText(self.spec_parser.file_path)
        else:
            self.btn_connect.setText("Connect")
            self.lbl_connection_status.setText("is not connected")
            self.btn_open_config_file.setEnabled(False)
            self.lbl_config_file_status.setText("...")

    def on_Connect(self):
        """
        Connection Button Handler
        """
        if self.serialCtrl.connected_to_device:
            self.serialCtrl.disconnect()
        else:
            self.serialCtrl.connect()
            if not self.serialCtrl.connected_to_device:
                self.show_messagebox("Unable to establish serial connection", 3, "Serial connection error")
        # refresh UI
        self.setup_Connection_UI()

    def openSpecFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self, "QFileDialog.getOpenFileName()", "",
                                                  "All Files (*);;Python Files (*.py)", options=options)
        if fileName:
            self.spec_file_name = fileName
            try:
                self.config_manager.config['spec']['file_path'] = fileName
                self.config_manager.save_config(self.config_manager.config)
                self.load_spec()
            except Exception as e:
                self.show_messagebox(repr(e), 3, "Spec load error")

    def load_spec(self):
        if self.spec_file_name:
            self.spec_parser.load_config(self.spec_file_name)
            self.setup_Connection_UI()
            self.setup_Test_UI()

    def setup_Test_UI(self):
        if self.spec_parser.config:
            self.grbox_Test.setEnabled(True)
            self.lbl_title.setText(self.spec_parser.title)
            self.progress_bar_test.setMaximum(len(self.spec_parser.config['TEST']))
            self.init_Plots()

    def init_Plots(self):
            if 'ADC_PLOTS' in self.spec_parser.config:
                self.graphics_layout_widget.clear()
                adc_plots = self.spec_parser.config['ADC_PLOTS']
                cols = 1
                i = 0
                for name, title in adc_plots.items():
                    plot_widget = self.graphics_layout_widget.addPlot(
                        row=i // cols,
                        col=i % cols,
                        name=name,
                        title=title)
                    plot_widget.setObjectName(f"plot_{name}")
                    plot_widget.showGrid(x=True, y=True)
                    # plot_widget.setLabel('left', "Y Axis", units='A')
                    plot_widget.setMouseEnabled(x=False, y=False)
                    # plot_widget.showAxis('bottom', False)
                    i += 1

                    line = plot_widget.plot(
                        [],
                        [],
                        name=title,
                        pen=pg.mkPen(color=(255, 0, 0), width=5),
                        symbol="o",
                        symbolSize=15,
                        symbolBrush="b",
                    )

                    self.plots[name] = {'title': title,
                                        'plot': plot_widget,
                                        'line': line,
                                        'data': []
                                        }

    def startTest(self):
        # clean log screen
        self.screen_log_txt = ''
        self.file_log_txt = ''
        self.db_log_data = []
        self.init_Plots()
        MSG = {
            'test_begin': "[TEST BEGIN]",
            'test_end': "[TEST END]",
        }
        if "TEST" in self.spec_parser.config:
            # self.btn_stop_test.setEnabled(True)
            # self.btn_start_test.setEnabled(False)
            self.thread_Test = QThread()
            self.tester = TestWorker(self)
            self.tester.moveToThread(self.thread_Test)
            self.thread_Test.started.connect(self.tester.run)

            self.tester.started.connect(self.test_start_handler)

            self.tester.update.connect(self.update_screen_log)
            self.tester.update.connect(self.update_text_log)

            self.tester.getv_data.connect(self.update_plots)

            self.tester.finished.connect(self.thread_Test.quit)
            self.tester.finished.connect(self.test_finish_handler)
            # self.tester.finished.connect(self.tester.deleteLater)
            # self.tester.finished.connect(self.thread_Test.deleteLater)

            self.tester.spec_error.connect(lambda: self.set_test_status(2))
            self.tester.tester_error.connect(self.tester_error_handler)

            self.thread_Test.start()

    def test_start_handler(self):
        self.write_screen_log("[TEST BEGIN]")
        self.set_test_status(1)
        self.btn_start_test.setEnabled(False)
        self.btn_stop_test.setEnabled(True)

    def test_finish_handler(self):
        self.write_file_log()
        self.write_db_log()
        self.write_screen_log("<br >[TEST END]")
        self.progress_bar_test.setValue(self.progress_bar_test.maximum())
        self.show_test_result()
        self.btn_start_test.setEnabled(True)
        self.btn_stop_test.setEnabled(False)

    def stopTest(self):
        try:
            self.tester.abort_test = True
            self.set_test_status(4)
            self.btn_start_test.setEnabled(True)
            self.btn_stop_test.setEnabled(False)
        except Exception as e:
            self.show_messagebox(repr(e), _type=2, title='Unable to finish the test')

    def tester_error_handler(self, err_msg: str):
        self.show_messagebox(err_msg)
        self.btn_start_test.setEnabled(True)
        self.btn_stop_test.setEnabled(False)
        self.thread_Test.quit()

    def set_test_status(self, status):
        """
        :param status: 0 - N/A; 1: - PROCESSING; 2 - NG; 3 - OK; 4 - ABORTED
        """
        status_list = {
            0: {'name': 'N/A', 'style': "border: 1px solid gray; padding: 0px"},
            1: {'name': 'PROCESSING', 'style': "background-color: #ffb703"},
            2: {'name': 'NG', 'style': "background-color: red"},
            3: {'name': 'OK', 'style': "background-color: #00FF18"},
            4: {'name': 'ABORTED', 'style': "background-color: gray"},
        }
        if status in status_list:
            self.lbl_test_status.setText(status_list[status]['name'])
            self.lbl_test_status.setStyleSheet(status_list[status]['style'])

    def update_screen_log(self, data):
        """
        :param data: dict returned by TestWorker
        :return: str log line
        """
        self.progress_bar_test.setValue(data['number'])

        color_text = "<font color='{}'>{}</font>"
        send_prefix = color_text.format('gray', "PC to MPU")
        get_prefix = color_text.format('gray', "MPU to PC")
        res_prefix = color_text.format('gray', "RESULT")
        msg_ok = color_text.format('green', 'OK')

        timestamp = color_text.format('gray', datetime.fromtimestamp(int(data['ts_start'])))
        exec_time = color_text.format('gray', f"Execution time: {data['execution_time']:.3f} seconds")
        request = data['request']
        response = data['response']
        message = color_text.format('red', f"ERROR {data['error']}") if data['error'] else msg_ok
        details = f"<br>{'<br>'.join(data['details'])}" if 'details' in data else ""

        result = f"""
        <br><font size=2>{timestamp}
        <br>{exec_time}</font>
        <br>{send_prefix}:  {request}
        <br>{get_prefix}:   {response}
        <code>{details}</code>
        <br>{res_prefix}:   {message}
        <br>----------------------------
        """
        self.write_screen_log(result)

    def write_screen_log(self, line):
        self.screen_log_txt += '<br>' + line
        self.lbl_test_log.setText(self.screen_log_txt)

    def update_text_log(self, data):
        send_prefix = "PC to MPU"
        get_prefix = "MPU to PC"
        res_prefix = "RESULT"
        msg_ok = 'OK'

        request = data['request'].strip('\n').strip('\t').strip()
        response = data['response'].strip('\n').strip('\t').strip()
        message = f"ERROR {data['error']}" if data['error'] else msg_ok
        details = '\n\t\t\t\t'.join(data['details']) + '\n' if 'details' in data else ""
        timestamp = datetime.fromtimestamp(int(data['ts_start']))
        exec_time = f"Execution time: {data['execution_time']:.3f} seconds"

        self.file_log_txt += f"""
{timestamp}
{exec_time}
{send_prefix}:  \t{request}
{get_prefix}:   \t{response}
{res_prefix}:   \t\t{message}
\t\t\t\t{details}
        """

        self.db_log_data.append({'request': request,
                                 'response': response,
                                 'result': message,
                                 'status': "error" if data['error'] else 'ok',
                                 'details': data['details'] if 'details' in data else [],
                                 'timestamp': data['ts_start'],
                                 'exec_time': data['execution_time'],
                                 })

    def write_file_log(self):
        now = datetime.now()
        header = f"""
DATE: \t{now.strftime('%d/%m/%Y')}
TIME: \t{now.strftime("%H:%M:%S")}
        """

        errors = '\n\t'.join(self.tester.errors)
        footer = f"""
------------------------------------------------------------------
\n\n{len(self.tester.errors)} ERROR(S) 
\n\t{errors}
\n\n================================================================================================================\n\n
        """
        if self.serialCtrl.kambala_UniqueID:
            # self.lbl_uniqueID.setText(self.serialCtrl.kambala_UniqueID)
            log_dir_full_path = os.path.join(self.log_dir_path, self.log_dir_name)
            os.makedirs(log_dir_full_path, exist_ok=True)
            with open(os.path.join(log_dir_full_path, f'{self.serialCtrl.kambala_UniqueID}.txt'), 'a') as log_file:
                log_file.write(header + self.file_log_txt + footer)

    def write_db_log(self):
        db_path = os.path.join(self.web_dir_name, self.db_dir_name, self.db_name)
        if self.serialCtrl.kambala_UniqueID:
            with sql.connect(db_path) as con:
                cur = con.cursor()

                cur.execute("""CREATE TABLE IF NOT EXISTS reports (
                    kambala_id TEXT,
                    date_create INTEGER,
                    detail_text TEXT NOT NULL,
                    spec_name TEXT,
                    errors_cnt INTEGER DEFAULT 0,
                    errors_text TEXT,
                    PRIMARY KEY (kambala_id, date_create)
                )
                """)

                errors_cnt = len(self.tester.errors)
                errors_txt = json.dumps(self.tester.errors)
                detail_txt = json.dumps(self.db_log_data)
                cur.execute(f"""INSERT INTO reports 
                (kambala_id, date_create, detail_text, spec_name, errors_cnt, errors_text)
                VALUES(
                    '{self.serialCtrl.kambala_UniqueID}',
                    strftime ('%s', 'now'),
                    '{detail_txt}',
                    '{self.spec_parser.title}',
                    {errors_cnt},
                    '{errors_txt}'
                )""")

    def update_plots(self, data):
        for plot_name in self.spec_parser.config['ADC_PLOTS']:
            plot_obj = self.plots[plot_name]
            plot_obj['data'].append(data[plot_name])
            plot_obj['line'].setData(list(range(len(plot_obj['data']))), plot_obj['data'])

    def show_test_result(self):
        test_errors_list = self.tester.errors
        error_cnt = len(test_errors_list)
        if error_cnt:
            self.show_messagebox(
                f"<h3>{error_cnt} error(s) found:</h3>" + "<br>".join(test_errors_list),
                _type=1,
                title="Test Report")
        else:
            self.set_test_status(3)
            # self.show_messagebox("Test is finished. No errors found", 1, "SUCCESS!")

    def show_messagebox(self, msg_text: str, _type=3, title="Error"):
        """
        :param _type: 1 - Information, 2 - Warning, 3 - Critical, 4 - Question
        """
        msg = QMessageBox()
        msg.setIcon(_type)
        msg.setText(msg_text)
        msg.setWindowTitle(title)
        msg.setStandardButtons(QMessageBox.Ok)
        retval = msg.exec_()


class ScrollLabel(QScrollArea):

    # constructor
    def __init__(self, *args, **kwargs):
        QScrollArea.__init__(self, *args, **kwargs)

        # making widget resizable
        self.setWidgetResizable(True)

        # making qwidget object
        content = QWidget(self)
        self.setWidget(content)

        # vertical box layout
        lay = QVBoxLayout(content)

        # creating label
        self.label = QLabel(content)

        # setting alignment to the text
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # making label multi-line
        self.label.setWordWrap(True)

        # adding label to the layout
        lay.addWidget(self.label)

    # the setText method
    def setText(self, text):
        # setting text to the label
        self.label.setText(text)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
