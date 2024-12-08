import sys
from PyQt5.QtWidgets import QApplication
# from WEB.site import
from GUI import MainWindow


app = QApplication(sys.argv)
main_window = MainWindow()
main_window.show()
app.exec_()

