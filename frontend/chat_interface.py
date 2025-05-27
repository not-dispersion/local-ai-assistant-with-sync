from PySide6.QtWidgets import (QMainWindow, QTextEdit, QLineEdit, QPushButton, 
                              QVBoxLayout, QWidget, QMessageBox, QFileDialog,
                              QInputDialog, QLabel, QApplication)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import (QFile, Qt)
from chat_logic import ChatLogic
from sync_handler import SyncHandler
from memory_handler import MemoryHandler
import os

class ChatInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat with Ai")
        self.resize(600, 650)

        self.data_folder = "data"
        os.makedirs(self.data_folder, exist_ok=True)

        ui_file = QFile("ui/chat_interface.ui")
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        self.ui = loader.load(ui_file)
        ui_file.close()
        self.setCentralWidget(self.ui)

        self.chat_logic = ChatLogic()
        self.sync_handler = SyncHandler()

        self.chat_display = self.ui.findChild(QTextEdit, "chatDisplay")
        self.user_input_entry = self.ui.findChild(QLineEdit, "userInputEntry")
        self.send_button = self.ui.findChild(QPushButton, "sendButton")
        self.exit_button = self.ui.findChild(QPushButton, "exitButton")
        self.file_mode_button = self.ui.findChild(QPushButton, "fileModeButton")
        self.change_folder_button = self.ui.findChild(QPushButton, "changeFolderButton")
        self.web_search_button = self.ui.findChild(QPushButton, "webSearchButton")
        self.login_button = self.ui.findChild(QPushButton, "loginButton")
        self.register_button = self.ui.findChild(QPushButton, "registerButton")
        self.upload_button = self.ui.findChild(QPushButton, "uploadButton")
        self.download_button = self.ui.findChild(QPushButton, "downloadButton")
        self.logout_button = self.ui.findChild(QPushButton, "logoutButton")
        self.username_label = self.ui.findChild(QLabel, "usernameLabel")

        self.send_button.clicked.connect(self.send_message)
        self.exit_button.clicked.connect(self.close)
        self.file_mode_button.clicked.connect(self.toggle_file_mode)
        self.change_folder_button.clicked.connect(self.prompt_local_folder)
        self.web_search_button.clicked.connect(self.toggle_web_search)
        self.login_button.clicked.connect(self.handle_login)
        self.register_button.clicked.connect(self.handle_register)
        self.upload_button.clicked.connect(self.handle_upload)
        self.download_button.clicked.connect(self.handle_download)
        self.logout_button.clicked.connect(self.handle_logout)

        self.file_mode_button.setCheckable(True)
        self.file_mode_button.setText("Enable File Mode")
        self.web_search_button.setCheckable(True)
        self.web_search_button.setText("Enable Web Search")
        self.update_auth_ui(False)
        self.username_label.clear()

        if not self.chat_logic.file_handler.local_folder:
            self.prompt_local_folder()

    def handle_login(self):
        username, ok1 = QInputDialog.getText(self, "Login", "Username:")
        if not ok1 or not username:
            return
            
        password, ok2 = QInputDialog.getText(self, "Login", "Password:", QLineEdit.Password)
        if not ok2:
            return
            
        result = self.sync_handler.login(username, password)
        if "error" in result:
            QMessageBox.warning(self, "Login Failed", result["error"])
        else:
            self.username_label.setText(f"User: {username}")
            self.update_auth_ui(True)
            QMessageBox.information(self, "Success", "Logged in successfully")

    def handle_logout(self):
        self.sync_handler.logout()
        self.update_auth_ui(False)
        self.username_label.clear()
        QMessageBox.information(self, "Success", "Logged out successfully")

    def update_auth_ui(self, logged_in):
        self.login_button.setEnabled(not logged_in)
        self.register_button.setEnabled(not logged_in)
        self.upload_button.setEnabled(logged_in)
        self.download_button.setEnabled(logged_in)
        self.logout_button.setEnabled(logged_in)

    def send_message(self):
        user_input = self.user_input_entry.text()
        if not user_input.strip():
            return

        self.chat_display.append(f"You: {user_input}")

        ai_reply = self.chat_logic.send_message(user_input)
        if ai_reply:
            self.chat_display.append(f"Ai: {ai_reply}\n")

        self.user_input_entry.clear()

    def toggle_file_mode(self):
        enabled = self.file_mode_button.isChecked()
        message = self.chat_logic.toggle_file_mode(enabled)
        if message:
            QMessageBox.information(self, "Information", message)
        self.file_mode_button.setText("Disable File Mode" if enabled else "Enable File Mode")

    def toggle_web_search(self):
        enabled = self.web_search_button.isChecked()
        self.chat_logic.web_search_handler.toggle_enabled(enabled)
        self.web_search_button.setText("Disable Web Search" if enabled else "Enable Web Search")

    def prompt_local_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Local Folder")
        if folder_path:
            self.chat_logic.file_handler.save_local_folder(folder_path)
            QMessageBox.information(self, "Success", f"Local folder set to: {folder_path}")
        else:
            QMessageBox.warning(self, "Warning", "Local folder is required for file mode.")

    def handle_register(self):
        username, ok1 = QInputDialog.getText(self, "Register", "Username:")
        if not ok1 or not username:
            return
            
        password, ok2 = QInputDialog.getText(self, "Register", "Password:", QLineEdit.Password)
        if not ok2:
            return
            
        confirm_password, ok3 = QInputDialog.getText(self, "Register", "Confirm Password:", QLineEdit.Password)
        if not ok3:
            return
            
        if password != confirm_password:
            QMessageBox.warning(self, "Error", "Passwords don't match")
            return
            
        result = self.sync_handler.register(username, password)
        if "error" in result:
            QMessageBox.warning(self, "Registration Failed", result["error"])
        else:
            QMessageBox.information(self, "Success", "Registration successful. You can now login.")

    def handle_upload(self):
        if not self.sync_handler.auth_token:
            QMessageBox.warning(self, "Error", "You need to login first")
            return
            
        result = self.sync_handler.upload_data()
        if "error" in result:
            QMessageBox.warning(self, "Upload Failed", result["error"])
        else:
            QMessageBox.information(self, "Success", "Data uploaded to cloud successfully")

    def handle_download(self):
        if not self.sync_handler.auth_token:
            QMessageBox.warning(self, "Error", "You need to login first")
            return
            
        result = self.sync_handler.download_data()
        if "error" in result:
            QMessageBox.warning(self, "Download Failed", result["error"])
        else:
            success = self.sync_handler.save_downloaded_data(result)
            if success:
                QMessageBox.information(self, "Success", "Data downloaded from cloud successfully")
                self.chat_logic.memory_handler = MemoryHandler()
            else:
                QMessageBox.warning(self, "Error", "Failed to save downloaded data")

    def closeEvent(self, event):
        try:
            self.chat_logic.finalize()
            event.accept()
        except Exception as e:
            print(f"Error on close: {str(e)}")
            event.accept()

    def handle_download(self):
        if not self.sync_handler.auth_token:
            QMessageBox.warning(self, "Error", "You need to login first")
            return
        
        self.setCursor(Qt.WaitCursor)
        try:
            result = self.sync_handler.download_data()
            
            if "error" in result:
                QMessageBox.warning(self, "Download Failed", 
                    f"{result['error']}\nDetails: {result.get('details', 'None')}")
            elif not result.get('data'):
                reply = QMessageBox.question(
                    self,
                    "Empty Cloud Storage",
                    "The cloud has no chat data. Do you want to clear local data?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    summary_path = os.path.join("data", "chat_summary.jsonl")
                    embeddings_path = os.path.join("data", "chat_embeddings.jsonl")
                    
                    with open(summary_path, "w", encoding="utf-8") as f:
                        f.write("")
                    with open(embeddings_path, "w", encoding="utf-8") as f:
                        f.write("")
                    
                    self.chat_logic.memory_handler = MemoryHandler()
                    QMessageBox.information(self, "Success", "Local data cleared")
            else:
                success = self.sync_handler.save_downloaded_data(result)
                if success:
                    self.chat_logic.memory_handler = MemoryHandler()
                    QMessageBox.information(self, "Success", 
                        f"Downloaded {len(result['data'])} conversation records")
                else:
                    QMessageBox.warning(self, "Error", "Failed to save downloaded data")
        finally:
            self.setCursor(Qt.ArrowCursor)

    def handle_upload(self):
        if not self.sync_handler.auth_token:
            QMessageBox.warning(self, "Error", "You need to login first")
            return
        
        self.setCursor(Qt.WaitCursor)
        QApplication.processEvents()
        
        try:
            if not self.chat_logic.memory_handler.force_summary():
                QMessageBox.warning(self, "Warning", "Failed to summarize pending messages")
                return
            
            result = self.sync_handler.upload_data()
            if "error" in result:
                QMessageBox.warning(self, "Upload Failed", result["error"])
            else:
                QMessageBox.information(self, "Success", "Data uploaded to cloud successfully")
        finally:
            self.setCursor(Qt.ArrowCursor)