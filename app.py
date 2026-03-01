import sys

from PyQt5.QtWidgets import QApplication

from login import LoginWindow
from main import MainWindow


def main():
    app = QApplication(sys.argv)

    login = LoginWindow()
    main_window = MainWindow()

    def handle_login():
        if login.check_login():
            login.close()
            main_window.show()

    login.login_btn.clicked.connect(handle_login)

    login.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
