import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication, QPushButton, QDialog, QListWidgetItem ,QMessageBox,QLineEdit, QTreeWidgetItem
from PyQt5.QtCore import pyqtSlot, QFile, QTextStream, QThread, pyqtSignal, QTimer
import time, os
from sidebar import Ui_MainWindow
from FOTA_readServerMessages import *
from FOTA_checkPackageServer import *
from newSWImageExist import Ui_FOTA_NewFWExist
from FOTA_Installation import install2TECU_Popup
import re
from datetime import datetime

# Server Message Flag - False: No message - True: New Server Message is available
# Base Server File List - List of files in Server - Azure Blob Storage
baseServerFileList = []
isGettingBaseList = False
connection_status = True
loadCentralStorage = False
update_log = False
# New Software available flag
isNewSwAvai = "NO"
latest_SwVer = ""
isRollbackTrigger = "NO"
# Installation status of new Sw
isNewSwInstalled = "YES"
isNewSwInstalling = "NO"
# Download file path - New Sw file will be downloaded into Central Storage folder
downloadFilePath = ""
rollback_currFilePath = ""
latestSwVer = ""
# TFTP file transfer flag
isFileTransferred = "NO"
# User confirmation on Popupwindow
userConfirm = False
userConfirm_rollback = False

# Sends a message to the server and receives the response over TCP.

        


# Thread definition 
class _rb_fota_listenServerReq_thread(QThread):
    # Định nghĩa các tín hiệu và slot của worker
    resultReady = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # Tạo một biến để lưu thời gian gửi kết quả cuối cùng
        self.lastResultTime = None
        # Khởi tạo biến stop
        self.stop = False
        self.isNewServerMsg = False

        self.SvrMsg_data = None
    def tcpToAdapter_API(self, server_address, message):
        bufferSize = 1024
        timeout = 5  # Set a timeout value of 5 seconds
        try:
            TCPClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create a TCP socket
            TCPClient.settimeout(timeout)  # Set socket timeout
            TCPClient.connect(server_address)
            TCPClient.sendall(message.encode('utf-8'))
            data = TCPClient.recv(bufferSize)
            data = data.decode('utf-8')
            self.isNewServerMsg = False
            return data
        except :
            print('Timeout occurred/No response from the server.')
            return None
        finally:
            TCPClient.close()
    def serverMessageHandler(self, message):
        # print data from both system and application (custom) properties
        print("MsgType: ",str(vars(message)['message_id']),"\n")  
        RECEIVED_MESSAGE_DATA = vars(message)['data']
        RECEIVED_DATA = RECEIVED_MESSAGE_DATA.decode('utf-8')
        self.SvrMsg_data = RECEIVED_DATA
        print("New Msg is :",self.SvrMsg_data)
        self.isNewServerMsg = True
    @pyqtSlot()
    def doWork(self):
        # Thực hiện công việc cần làm cyclic
        while True:
            if not self.stop:
                self.checkServerMsg()
                result = "Hello from worker"
                # Gửi tín hiệu kết quả
                self.resultReady.emit(result)
                # Ngủ một giây
                time.sleep(5)
    def checkServerMsg(self):
        global baseServerFileList
        global isGettingBaseList
        global connection_status
        print("Connection_status_newMsg:",connection_status)
            # Instantiate the client
        if connection_status == True:
            try:
                print("Thread 1 new still running !!")
                client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
                # Attach the handler to the client
                client.on_message_received = self.serverMessageHandler
                if self.isNewServerMsg == True:
                    serverAddress = ('192.168.0.123', 7)
                    print("New Msg from server !!!!!!")
                    # tcpToAdapter_API(serverAddress,RECEIVED_DATA)
            except :
                print("IoT Hub C2D Messaging device sample stopped")
                isGettingBaseList = False
                connection_status = False
            finally:
                # Graceful exit
                client.shutdown()

    @pyqtSlot()
    def stopWork(self):
        # Đặt biến cờ stop thành True để báo cho thread biết rằng nó cần dừng lại
        self.stop = True

    @pyqtSlot()  
    def restartWork(self):
        # Đặt biến cờ stop thành True để báo cho thread biết rằng nó cần dừng lại
        self.stop = False



# Popup definition            
class rollbackPreviousSw(QtWidgets.QDialog):
    def __init__(self, isNewSwInstalled, filepath):
        
        super().__init__()
        uic.loadUi(r'rollback.ui', self)
        self.rollback_yes.clicked.connect(self.on_yes_clicked)
        self.rollback_no.clicked.connect(self.on_no_clicked)
        self.isNewSwInstalled = isNewSwInstalled
        self.filepath = filepath
        
        self.ecuversion.setText(filepath)
    def on_yes_clicked(self):
        rollback_filepath = "".join(['./FOTA_CentralStorage/',self.filepath])
        
        # Add your code here for when the "Yes" button is clicked
        dialog1 = install2TECU_Popup(rollback_filepath, self.isNewSwInstalled)
        dialog1.valueUpdated.connect(self.rollback_success)
        dialog1.exec_()
        self.accept()  # Close the dialog
        
    def rollback_success(self, value):
        if value == "YES":
            global isRollbackTrigger
            global userConfirm_rollback
            isRollbackTrigger = "NO"
            global update_log
            update_log = True
            userConfirm_rollback = False
            
    def on_no_clicked(self):
        # Add your code here for when the "No" button is clicked
        print("No button clicked")
        self.reject()  # Close the dialog

class newSwAvai_Popup(QtWidgets.QDialog):
    isNewSwInstalled_signal = pyqtSignal()
    def __init__(self, isNewSwInstalled):
        super().__init__()
        uic.loadUi(r'newSWImageExist.ui', self)
        self.FOTA_User_Yes.clicked.connect(self.on_yes_clicked)
        self.FOTA_User_No.clicked.connect(self.on_no_clicked)
        self.isNewSwInstalled = isNewSwInstalled

    def on_yes_clicked(self):
        global downloadFilePath
        # Add your code here for when the "Yes" button is clicked
        dialog = install2TECU_Popup(downloadFilePath, self.isNewSwInstalled)
        dialog.valueUpdated.connect(self.newSwInstallSuccess)      
        dialog.exec_()
        self.accept()  # Close the dialog
        
    def newSwInstallSuccess(self, value):
        if value == "YES":
            self.isNewSwInstalled_signal.emit()
            # global isNewSwInstalled
            # global userConfirm
            # isNewSwInstalled = "YES"
            # userConfirm = False
            
    def on_no_clicked(self):
        # Add your code here for when the "No" button is clicked
        self.reject()  # Close the dialog




class _CheckServerContainer(QThread):
    # Định nghĩa các tín hiệu và slot của worker
    newSw = pyqtSignal()
    resultReady = pyqtSignal(str)
    isNewSwInstalled_signal = pyqtSignal(str)
    def __init__(self, isNewSwInstalled):
        super().__init__()
        # Tạo một biến để lưu thời gian gửi kết quả cuối cùng
        self.lastResultTime = None
        # Khởi tạo biến stop
        self.stop = False
        self.isNewSwInstalled = isNewSwInstalled
    @pyqtSlot()
    def doWork(self):
        # Thực hiện công việc cần làm cyclic
        global baseServerFileList
        baseServerFileList = get_first_file_list()

        while True:
            if not self.stop:
                result = "Hello from worker"
                self.checkNewSwAvai()
                # Gửi tín hiệu kết quả
                self.resultReady.emit(result)

                # Cập nhật thời gian gửi kết quả cuối cùng
                self.lastResultTime = time.time()
                # Ngủ một giây
                time.sleep(3)
        
    @pyqtSlot()
    def stopWork(self):
        # Đặt biến cờ stop thành True để báo cho thread biết rằng nó cần dừng lại
        self.stop = True

    @pyqtSlot()  
    def restartWork(self):
        # Đặt biến cờ stop thành True để báo cho thread biết rằng nó cần dừng lại
        self.stop = False

    def checkNewSwAvai(self):
            global baseServerFileList
            global downloadFilePath
            global isNewSwAvai
            global isNewSwInstalling
            print("Thread 2 is running")
            if connection_status == True:
                if isNewSwInstalling == "NO" and self.isNewSwInstalled == "NO" and isNewSwAvai == "YES":
                    isNewSwInstalling = "YES"
                elif isNewSwInstalling == "YES" and self.isNewSwInstalled == "YES" and isNewSwAvai == "NO":
                    if downloadFilePath != "":
                        self.addSwListLog(downloadFilePath)
                        isNewSwInstalling = "NO"
                # self.loadListServerFile(baseServerFileList)
                checkServerContainerResult = get_file_from_cloud(baseServerFileList, self.isNewSwInstalled)
                print("Thread 2")
                if checkServerContainerResult[1] != "":
                    downloadFilePath = checkServerContainerResult[1]
                    latest_SwVer = downloadFilePath
                    self.isNewSwInstalled = checkServerContainerResult[2]
                    self.newSw.emit()
                    self.isNewSwInstalled_signal.emit(self.isNewSwInstalled)
                    # dialog = newSwAvai_Popup(isNewSwInstalled)
                    # dialog.exec_()
                isNewSwAvai = checkServerContainerResult[-1]
                if isNewSwAvai == "YES":
                    baseServerFileList = checkServerContainerResult[0]



# End New SW Available Popup
class MainWindow(QMainWindow):
    operate = pyqtSignal()
    newSw = pyqtSignal()
    def __init__(self):
        super(MainWindow, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.isNewSwInstalled = "YES"
        # self.rb_fota_listenServerReq_thread = rb_fota_listenServerReq_thread()
        # self.rb_fota_listenServerReq_thread.start()
        
        # Tạo một đối tượng QThread
        self.ListenServer_thread = QThread()
        # Tạo một đối tượng Worker
        self.listenWorker = _rb_fota_listenServerReq_thread()
        # Di chuyển worker vào thread
        self.listenWorker.moveToThread(self.ListenServer_thread)
        # Kết nối các tín hiệu và slot
        self.operate.connect(self.listenWorker.doWork)
        self.listenWorker.resultReady.connect(self.handleListenServerResults)
        self.ListenServer_thread.start()


        # Tạo một đối tượng QThread
        self.thread = QThread()
        # Tạo một đối tượng Worker
        self.worker = _CheckServerContainer(self.isNewSwInstalled)
        # Di chuyển worker vào thread
        self.worker.moveToThread(self.thread)
        # Kết nối các tín hiệu và slot
        self.operate.connect(self.worker.doWork)
        self.worker.newSw.connect(self.newSwPopUp)
        self.worker.isNewSwInstalled_signal.connect(self.Update_newSWStatus)
        self.worker.resultReady.connect(self.handleResults)
        # Bắt đầu thread
        self.thread.start()

        # Tạo một QTimer để kiểm tra trạng thái của thread
        # self.timer = QTimer(self)
        # self.timer.setInterval(15000) # Kiểm tra sau mỗi 5 giây
        # self.timer.timeout.connect(self.checkThreadStatus)
        # self.timer.start()
        
        self.thread_stuck_warning_shown = False  # Thêm biến kiểm soát 

        self.ui.icon_only_widget.hide()
        self.ui.stackedWidget.setCurrentIndex(0)
        self.ui.home_btn_2.setChecked(True)
        
        self.ui.sendDiag.clicked.connect(self.getManualDiagMsg)
        self.ui.manual_install.clicked.connect(self.manualInstalNewSw)
        
        self.ui.pushButton.clicked.connect(self.checkInternetConnection)
        self.ui.pushButton_3.clicked.connect(self.reloadCentralStorage)
        self.ui.pushButton_4.clicked.connect(self.rollbackTrigger)

        self._init_run()

    def _init_run (self):
        print("Running init function...")
        self.loadCentralStorage()
        self.checkInternetConnection()
        self.operate.emit()

    def tcpToAdapter_API(self, server_address, message):
            bufferSize = 1024
            timeout = 5  # Set a timeout value of 5 seconds
            try:
                TCPClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create a TCP socket
                TCPClient.settimeout(timeout)  # Set socket timeout
                TCPClient.connect(server_address)
                TCPClient.sendall(message.encode('utf-8'))
                data = TCPClient.recv(bufferSize)
                data = data.decode('utf-8')
                return data
            except :
                print('Timeout occurred/No response from the server.')
                return None
            finally:
                TCPClient.close()
    @pyqtSlot()
    def newSwPopUp(self):
        global latest_SwVer
        print(latest_SwVer)
        if latest_SwVer != "":
            latestVer = latest_SwVer[9:14]
            self.ui.latestSw.setText(latestVer)
        dialog = newSwAvai_Popup(self.isNewSwInstalled)
        dialog.isNewSwInstalled_signal.connect(self.Update_isNewSwInstalled)
        dialog.exec_()

    @pyqtSlot(str)
    def handleResults(self, result):
        # Xử lý kết quả từ worker
        pass
    @pyqtSlot(str)
    def handleListenServerResults(self, result):
        # Xử lý kết quả từ worker
        pass
    @pyqtSlot()
    def checkThreadStatus(self):
        # Kiểm tra trạng thái của thread
        if self.worker.lastResultTime is not None and not self.thread_stuck_warning_shown:
            # Nếu thời gian gửi kết quả cuối cùng lớn hơn 2 giây, coi như thread bị đứng
            if time.time() - self.worker.lastResultTime > 2: 
                self.thread_stuck_warning_shown = True
                # Yêu cầu dừng thread
                # Thông báo cho người dùng
                QMessageBox.warning(self, "Warning", "The thread is stuck and has been stopped.")
                self.worker.stopWork()

    def checkInternetConnection(self):
        global connection_status
        WAN_connection = get_file_list()
        if WAN_connection != []:
            connection_status = True
            self.ui.label.setText("E-Connected")
        else:
            self.ui.label.setText("E-Disconnected")
            connection_status = False
        serverAddress = ('192.168.0.123', 7)
        # ECUVersion_Req = tcpToAdapter_API(serverAddress,"UDS_22F195")
        # sleep(1)
        # ECUVersion_Res = tcpToAdapter_API(serverAddress,"UDS_GET")
        
        # if ECUVersion_Res is not None:
        #     ECU_Ver1 = ECUVersion_Res[17]
        #     ECU_Ver2 = ECUVersion_Res[25]
        #     ECU_Ver3 = ECUVersion_Res[33]
        #     ECU_Ver = "_".join([ECU_Ver1,ECU_Ver2,ECU_Ver3])
        #     self.ui.currentSw.setText(ECU_Ver)
        #     print(ECU_Ver)
            
        #     self.ui.latestSw.setText(ECU_Ver)
            
    # def firstLoad(self):
    #     global loadCentralStorage
    #     if loadCentralStorage == False:
    #         self.loadCentralStorage()
    #         self.checkInternetConnection()
    #         loadCentralStorage = True
    #     self.operate.emit()
    #     self.timerfirst.stop() 
        
    def addSwListLog(self, information):
        now = datetime.now()
        formatted = now.strftime("%d/%m/%Y %H:%M:%S")
        text = "{} - {}".format(information, formatted)
        icon_done = QIcon("done.png")
        new_item = QListWidgetItem(icon_done, text)
        self.ui.listSwLog.addItem(new_item)
        
    def loadCentralStorage(self):
        startpath = './FOTA_CentralStorage'
        for element in os.listdir(startpath):
            path_info = startpath + "/" + element
            parent_itm = QTreeWidgetItem(self.ui.central_storage, [os.path.basename(element)])
            if os.path.isdir(path_info):
                parent_itm.setIcon(0, QIcon('folder.png'))
            else:
                parent_itm.setIcon(0, QIcon('file.png'))
                
    def reloadCentralStorage(self):
        self.ui.central_storage.clear() # xóa tất cả các item
        startpath = './FOTA_CentralStorage'
        for element in os.listdir(startpath):
            path_info = startpath + "/" + element
            parent_itm = QTreeWidgetItem(self.ui.central_storage, [os.path.basename(element)])
            if os.path.isdir(path_info):
                # load_project_structure(path_info, parent_itm)
                parent_itm.setIcon(0, QIcon('folder.png'))
            else:
                parent_itm.setIcon(0, QIcon('file.png'))
        # self.ui.central_storage.addTopLevelItems(items)
    def rollbackTrigger_action(self):
        global rollback_currFilePath
        self.addSwListLog(rollback_currFilePath)
        serverAddress = ('192.168.0.123', 7)
        ECUVersion_Req = self.tcpToAdapter_API(serverAddress,"UDS_22F195")
        sleep(1)
        ECUVersion_Res = self.tcpToAdapter_API(serverAddress,"UDS_GET")
        
        if ECUVersion_Res is not None:
            ECU_Ver1 = ECUVersion_Res[17]
            ECU_Ver2 = ECUVersion_Res[25]
            ECU_Ver3 = ECUVersion_Res[33]
            ECU_Ver = "_".join([ECU_Ver1,ECU_Ver2,ECU_Ver3])
            self.ui.currentSw.setText(ECU_Ver)
        
    def rollbackTrigger(self):
        curr_file = self.ui.central_storage.currentItem()
        filepath = ""
        try:  
            if curr_file:
                # Lấy giá trị của phần tử
                filepath = curr_file.text(0)
                global rollback_currFilePath
                rollback_currFilePath = filepath

            if filepath != "":
                global isRollbackTrigger
                global update_log
                rollbackPopup = rollbackPreviousSw(isRollbackTrigger,filepath)
                rollbackPopup.exec_()
                if update_log == True:
                    self.rollbackTrigger_action()
                    update_log = False
            else:
                QMessageBox.information(self,'RESPONSE WINDOW',f'No New SW Available!!!')

        except Exception as e:
            
            QMessageBox.information(self,'ERROR',f'ERROR WHEN GETTING TO ROLLBACK ! ')
        
    def loadListServerFile(self, listServerFile):
        self.ui.listServerfile.clear()
        for value in listServerFile:
            file_icon = QIcon("file.png")
            new_item = QListWidgetItem(file_icon, value)
            self.ui.listServerfile.addItem(new_item)

    def manualInstalNewSw(self):
        try:
            if downloadFilePath != "":
                installPopUp = newSwAvai_Popup(self.isNewSwInstalled)
                installPopUp.isNewSwInstalled_signal.connect(self.Update_isNewSwInstalled)
                installPopUp.exec_()
            else:
                QMessageBox.information(self,'RESPONSE WINDOW',f'No New SW Available!!!')

        except Exception as e:
            print("Error")

    def Update_newSWStatus(self, value):
        if value =="NO":
            self.isNewSwInstalled = "NO"
        else:
            self.isNewSwInstalled = "YES"

    def Update_isNewSwInstalled(self):
        self.isNewSwInstalled = "YES"
    def getManualDiagMsg(self):
        selectedUDSMsg = self.ui.DiagServices.currentText()
        UDS_payload = ""
        serverAddress = ('192.168.0.123', 7)
        if "10" in selectedUDSMsg[0:2]:
            UDS_payload = selectedUDSMsg[0:5].replace(" ","")
            UDS_msg = "".join(["UDS_",UDS_payload])
            UDS_display = "".join(["Send UDS request: ",UDS_msg])
            new_text = QListWidgetItem(UDS_display)
            self.ui.DiagResponse.addItem(new_text)
        else:
            UDS_payload = selectedUDSMsg[0:8].replace(" ","")
            UDS_msg = "".join(["UDS_",UDS_payload])
            UDS_display = "".join(["Send UDS request: ",UDS_msg])
            new_text = QListWidgetItem(UDS_display)
            self.ui.DiagResponse.addItem(new_text)
        response1 = self.tcpToAdapter_API(serverAddress,UDS_msg)
        sleep(1)
        response = self.tcpToAdapter_API(serverAddress,"UDS_GET")
        UDS_display = "".join(["Reveive UDS Response: ",UDS_msg])
        if response == "UDS_FAIL":
            icon_neg = QIcon("error.png")
            new_text = QListWidgetItem(icon_neg,response)
            self.ui.DiagResponse.addItem(new_text)
        else:
            icon_pos = QIcon("done.png")
            new_text = QListWidgetItem(icon_pos, response)
            self.ui.DiagResponse.addItem(new_text)
    
    ## Function for searching
    def on_search_btn_clicked(self):
        self.worker.restartWork()
        self.ui.stackedWidget.setCurrentIndex(5)
        search_text = self.ui.search_input.text().strip()
        if search_text:
            self.ui.label_9.setText(search_text)
            
 
    ## Function for changing page to user page
    def on_user_btn_clicked(self):
        self.ui.stackedWidget.setCurrentIndex(6)
        self.worker.stopWork()

    ## Change QPushButton Checkable status when stackedWidget index changed
    def on_stackedWidget_currentChanged(self, index):
        btn_list = self.ui.icon_only_widget.findChildren(QPushButton) \
                    + self.ui.full_menu_widget.findChildren(QPushButton)
        for btn in btn_list:
            if index in [5, 6]:
                btn.setAutoExclusive(False)
                btn.setChecked(False)
            else:
                btn.setAutoExclusive(True)
                
    ## functions for changing menu page
    def on_home_btn_1_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(0)
    
    def on_home_btn_2_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(0)

    def on_dashborad_btn_1_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(1)

    def on_dashborad_btn_2_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(1)

    def on_orders_btn_1_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(2)

    def on_orders_btn_2_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(2)

    def on_products_btn_1_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(3)

    def on_products_btn_2_toggled(self, ):
        self.ui.stackedWidget.setCurrentIndex(3)

    def on_customers_btn_1_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(4)

    def on_customers_btn_2_toggled(self):
        self.ui.stackedWidget.setCurrentIndex(4)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    style_file = QFile("style.qss")
    style_file.open(QFile.ReadOnly | QFile.Text)
    style_stream = QTextStream(style_file)
    app.setStyleSheet(style_stream.readAll())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())





