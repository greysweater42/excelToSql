#!/usr/bin/env python

import sys
import csv
import pymysql.cursors
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QThread
from functools import partial


class MainWidget(QWidget):

    popups = []
    file_data = set()
    file_data_header = []

    def __init__(self):
        super(MainWidget, self).__init__()
        self.resize(800, 600)

        self.cbxODBCName = QComboBox()
        self.btnGetTablesList = QPushButton("Pobierz listę tabel")
        self.btnGetTablesList.clicked.connect(self.get_tables_list)
        self.twTables = QTreeWidget()
        self.twTables.setColumnCount(2)
        self.twTables.setHeaderLabels(["tabele", "typ danych"])

        self.leFileName = QLineEditUrl("lokalizacja pliku",
                                       "/home/tomek/Documents/nauka/python/excelToSql/data.csv")
        self.btnOpenFile = QPushButton("...")
        self.btnOpenFile.clicked.connect(self.show_file_dialog)
        self.btnReadFileData = QPushButton("Wczytaj plik")
        self.btnReadFileData.clicked.connect(self.read_file_data)
        self.twTable = TableWidget()
        self.btnSendFileData = QPushButton("Wyślij dane")
        self.btnSendFileData .clicked.connect(self.send_file_data)

        gbDB = QGroupBox()
        gbDBLayout = QVBoxLayout()
        gbDBLayout.addWidget(self.cbxODBCName)
        gbDBLayout.addWidget(self.btnGetTablesList)
        gbDBLayout.addWidget(self.twTables)
        gbDB.setLayout(gbDBLayout)

        gbFile = QGroupBox()
        gbFileLayout = QVBoxLayout()
        gbFileUrlLayout = QHBoxLayout()
        gbFileUrlLayout.addWidget(self.leFileName)
        gbFileUrlLayout.addWidget(self.btnOpenFile)
        gbFileLayout.addLayout(gbFileUrlLayout)
        gbFileLayout.addWidget(self.btnReadFileData)
        gbFileLayout.addWidget(self.twTable)
        gbFileLayout.addWidget(self.btnSendFileData)
        gbFile.setLayout(gbFileLayout)

        mainLayout = QHBoxLayout(self)
        mainLayout.addWidget(gbDB)
        mainLayout.addWidget(gbFile)

        self.read_settings()
        self.dataSender = DataSender(self)

    def read_settings(self):
        try:
            with open("settings", "r") as file:
                file_str = file.read()
            dbs = file_str.split("\n")
            dbs = [db for db in dbs if db != ""]
            self.cbxODBCName.addItems(dbs)
        except IOError as err:
            error_message = "Plik settings nie znajduje się w tej samej"
            error_message += " lokalizacji, co aplikacja. \n" + str(err)
            self.popups.append(PopupError(error_message=str(error_message)))
            self.popups[-1].show()

    def get_tables_list(self):
        """
        pobiera listę tabel ze wskazanej bazy danych
        """
        self.twTables.clear()
        db = self.cbxODBCName.currentText()
        try:
            connection = pymysql.connect(host='localhost',
                                         user='tomek',
                                         password='haslo',
                                         db=db,
                                         charset='utf8mb4',
                                         cursorclass=pymysql.cursors.DictCursor)
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
                        column_child.setDisabled(True)
                        table_item.addChild(column_child)
                    self.twTables.addTopLevelItem(table_item)
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as err:
            self.popups.append(PopupError(error_message=str(err)))
            self.popups[-1].show()
        else:
            connection.close()

    def show_file_dialog(self):
        file_name = QFileDialog.getOpenFileName(self, 'Otwórz plik',
                                                '/home/tomek')
        self.leFileName.setText(file_name[0])

    def read_file_data(self):
        path = self.leFileName.text()
        try:
            with open(path, "r") as file:
                rdr = csv.reader(file, delimiter=',')
                self.file_data_header = next(rdr)
                for row in rdr:
                    self.file_data.add(tuple(row))
            self.twTable.add_data(self.file_data_header, self.file_data)
        except FileNotFoundError as err:
            error_message = "Nie znaleziono pliku.\n" + str(err)
            self.popups.append(PopupError(error_message=error_message))
            self.popups[-1].show()

    def send_file_data(self):
        self.dataSender.db = self.cbxODBCName.currentText()
        index = self.twTables.selectedIndexes()[0]
        self.dataSender.table = index.data()
        self.dataSender.file_data = self.file_data
        self.dataSender.file_data_header = self.file_data_header
        self.dataSender.start()


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


class DataSender(QThread):

    def __init__(self, parent=None):
        QThread.__init__(self)
        self.parent = parent
        self.db = ""
        self.table = ""
        self.file_data = ""
        self.file_data_header = []

    def __del__(self):
        self.wait()

    def run(self):
        # Connect to the database
        connection = pymysql.connect(host='localhost',
                                     user='tomek',
                                     password='haslo',
                                     db=self.db,
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)

        try:
            with connection.cursor() as cursor:
                sql = "insert into " + self.table + " values ("
                sql += "'%s'," * (len(self.file_data_header) - 1) + "'%s');"
                for row in self.file_data:
                    cursor.execute(sql % row)
                    connection.commit()
        finally:
            connection.close()


class TableWidget(QWidget):

    def __init__(self):
        super(TableWidget, self).__init__()
        self.tw = QTableWidget()
        self.tw.horizontalHeader().setSectionsMovable(True)
        self.btnRemove = QPushButton("Usuń kolumnę")
        self.btnRemove .clicked.connect(self.hide_column)
        self.btnUndelete = QPushButton("Przywróć kolumnę")
        self.btnUndelete.setEnabled(False)
        self.m = QMenu()
        self.btnUndelete.setMenu(self.m)
        lt = QVBoxLayout(self)
        lth = QHBoxLayout()
        lth.addWidget(self.btnRemove)
        lth.addWidget(self.btnUndelete)
        lt.addLayout(lth)
        lt.addWidget(self.tw)
        self.headerLabels = []
        self.nrow = 0
        self.ncol = 0

    def add_data(self, header, data):
        self.headerLabels = header
        self.ncol = len(header)
        self.nrow = len(data)
        self.tw.setColumnCount(self.ncol)
        self.tw.setRowCount(self.nrow)
        self.tw.setHorizontalHeaderLabels(self.headerLabels)
        for row, line in enumerate(data):
            for column, item in enumerate(line):
                qtwitem = QTableWidgetItem(str(item))
                self.tw.setItem(row, column, qtwitem)

    def hide_column(self):
        self.btnUndelete.setEnabled(True)
        index = self.tw.currentColumn()
        if index == -1:
            return
        self.tw.horizontalHeader().setSectionHidden(index, True)
        self.m.addAction(self.headerLabels[index],
                         partial(self.show_column, index))
        if self.tw.horizontalHeader().hiddenSectionCount() == self.ncol:
            self.btnRemove.setEnabled(False)

    def show_column(self, index):
        self.btnRemove.setEnabled(True)
        self.tw.horizontalHeader().setSectionHidden(index, False)
        self.m.clear()
        for i in range(self.ncol):
            if self.tw.horizontalHeader().isSectionHidden(i):
                self.m.addAction(self.headerLabels[i],
                                 partial(self.show_column, i))
        if not self.tw.horizontalHeader().hiddenSectionCount():
            self.btnUndelete.setEnabled(False)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = MainWidget()
    mw.show()
    app.exec_()
