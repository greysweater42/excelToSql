#!/usr/bin/env python

import sys
import pymysql.cursors
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt


class MainWidget(QWidget):

    popups = []

    def __init__(self):
        super(MainWidget, self).__init__()
        self.resize(800, 600)

        self.cbxODBCName = QComboBox()
        self.btnReadData = QPushButton("Pobierz listę tabel")
        self.btnReadData.clicked.connect(self.get_data)
        self.twTables = QTreeWidget()
        self.twTables.setColumnCount(2)
        self.twTables.setHeaderLabels(["tabele", "typ danych"])

        self.leFileName = QLineEditUrl("lokalizacja pliku")

        gbDB = QGroupBox()
        gbDBLayout = QVBoxLayout()
        gbDBLayout.addWidget(self.cbxODBCName)
        gbDBLayout.addWidget(self.btnReadData)
        gbDBLayout.addWidget(self.twTables)
        gbDB.setLayout(gbDBLayout)

        gbFile = QGroupBox()
        gbFileLayout = QVBoxLayout()
        gbFileLayout.addWidget(self.leFileName)
        gbFile.setLayout(gbFileLayout)

        mainLayout = QHBoxLayout(self)
        mainLayout.addWidget(gbDB)
        mainLayout.addWidget(gbFile)

        self.read_settings()

    def read_settings(self):
        try:
            with open("settings", "r") as file:
                file_str = file.read()
            dbs = file_str.split("\n")
            dbs = [db for db in dbs if db != ""]
            self.cbxODBCName.addItems(dbs)
        except IOError as err:
            error_message = "Plik settings nie znajduje się w tej samej"
            " lokalizacji, co aplikacja. \n" + str(err)
            self.popups.append(PopupError(error_message=str(error_message)))
            self.popups[-1].show()

    def get_data(self):
        connection = pymysql.connect(host='localhost',
                                     user='tomek',
                                     password='haslo',
                                     db='MIS',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT table_name, column_name, data_type
                from information_schema.columns
                where table_schema='MIS';"""
                cursor.execute(sql)
                cur_result = cursor.fetchall()
                full_set = {tuple([item['table_name'], item['column_name'],
                                   item['data_type']]) for item in cur_result}
                result = AutoVivification()
                for item in full_set:
                    result[item[0]][item[1]] = item[2]
                for table in result:
                    table_item = QTreeWidgetItem([table])
                    for column in result[table]:
                        column_child = QTreeWidgetItem([column,
                                                        result[table][column]])
                        table_item.addChild(column_child)
                    self.twTables.addTopLevelItem(table_item)
        finally:
            connection.close()


class AutoVivification(dict):

    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value


class QLineEditUrl(QLineEdit):

    def __init__(self, placeholder_text="", text="", parent=None):
        super(QLineEditUrl, self).__init__(parent)
        self.setDragEnabled(True)
        self.setPlaceholderText(placeholder_text)
        self.setText(text)

    def dragEnterEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if urls and urls[0].scheme() == 'file':
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if urls and urls[0].scheme() == 'file':
            event.acceptProposedAction()

    def dropEvent(self, event):
        data = event.mimeData()
        urls = data.urls()
        if urls and urls[0].scheme() == 'file':
            url = str(urls[0].path())
            if url[0] == "/" and url[:5] != "/home":
                url = url[1:]
                self.setText(url)


class PopupError(QWidget):

    def __init__(self, error_message=""):
        QWidget.__init__(self)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.resize(300, 100)
        self.setWindowTitle(r"Błąd!")

        lbl = QLabel()
        lbl.setText(error_message)

        btn = QPushButton("OK")
        btn.clicked.connect(self.close)

        layout = QVBoxLayout(self)
        layout.addWidget(lbl)
        layout.addWidget(btn)

if __name__ == '__main__':

    app = QApplication(sys.argv)
    mw = MainWidget()
    mw.show()
    app.exec_()
