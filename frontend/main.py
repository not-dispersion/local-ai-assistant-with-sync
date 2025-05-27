import sys
from PySide6.QtWidgets import QApplication
from chat_interface import ChatInterface

def main():
    app = QApplication(sys.argv)
    window = ChatInterface()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()