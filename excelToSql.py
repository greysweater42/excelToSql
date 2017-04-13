#!/usr/bin/env python

import sys
import csv
import pandas as pd
import os
import pymysql.cursors
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QThread
from functools import partial


class MainWidget(QWidget):

    popups = []

    def __init__(self):
        super(MainWidget, self).__init__()
        self.resize(800, 600)
        self.fileData = FileData()

        self.cbxODBCName = QComboBox()
        self.btnGetTablesList = QPushButton("Pobierz listę tabel")
        self.btnGetTablesList.clicked.connect(self.get_tables_list)
        self.twTables = QTreeWidget()
        self.twTables.setColumnCount(2)
        self.twTables.setHeaderLabels(["tabele", "typ danych"])

        path = "/home/tomek/Documents/nauka/python/excelToSql/file.xlsx"
        self.leFileName = QLineEditUrl("lokalizacja pliku", path)
        self.btnOpenFile = QPushButton("...")
        self.btnOpenFile.clicked.connect(self.show_file_dialog)
        self.btnReadFileData = QPushButton("Wczytaj plik")
        self.btnReadFileData.clicked.connect(self.read_file_data)
        self.cbxSheet = QComboBox()
        self.cbxSheet.currentIndexChanged.connect(self.change_sheet)
        self.cbxSheet.hide()
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
        gbFileLayout.addWidget(self.cbxSheet)
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
        self.fileData = FileData()  # wczytanie drugiego pliku
        path = self.leFileName.text()
        _, file_extension = os.path.splitext(path)
        try:
            if file_extension in (".xls", ".xlsx"):
                self.cbxSheet.show()
                f = pd.ExcelFile(path)
                for sheet in f.sheet_names:
                    f_data = f.parse(sheet)
                    self.fileData.header[sheet] = f_data.columns.values
                    self.fileData.data[sheet] = {tuple(row) for row in
                                                 f_data.to_records(index=False)}
                    self.fileData.ncol[sheet] = len(f_data.columns.values)
                    self.fileData.nrow[sheet] = len(self.fileData.data[sheet])
                self.cbxSheet.addItems(f.sheet_names)
                self.twTable.set_file_data(self.fileData, f.sheet_names[0])
            elif file_extension == ".csv":
                self.cbxSheet.hide()
                file_data = set()
                with open(path, "r") as file:
                    rdr = csv.reader(file, delimiter=',')
                    self.fileData.header["csv"] = next(rdr)
                    for row in rdr:
                        file_data.add(tuple(row))
                self.fileData.data["csv"] = file_data
                self.fileData.ncol["csv"] = len(self.fileData.header["csv"])
                self.fileData.nrow["csv"] = len(self.fileData.data["csv"])
                self.twTable.set_file_data(self.fileData, "csv")
            else:
                error_message = "Otwierane są tylko pliki z rozszerzeniem "
                error_message += ".xlsx, .xls. lub .csv"
                self.popups.append(PopupError(error_message=error_message))
                self.popups[-1].show()
        except FileNotFoundError as err:
            error_message = "Nie znaleziono pliku.\n" + str(err)
            self.popups.append(PopupError(error_message=error_message))
            self.popups[-1].show()

    def send_file_data(self):
        db = self.cbxODBCName.currentText()
        dbtable = self.twTables.selectedIndexes()[0].data()
        if self.cbxSheet.isHidden():
            sheet = "csv"
        else:
            sheet = self.cbxSheet.currentText()
        self.popups.append(PopupSendData(db, dbtable, self.fileData, sheet))
        self.popups[-1].show()
        self.popups[-1].dataSender.start()

    def change_sheet(self):
        sheet = self.cbxSheet.currentText()
        self.twTable.set_file_data(self.fileData, sheet)


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


class PopupSendData(QWidget):

    def __init__(self, db, dbtable, fileData, sheet):
        super(PopupSendData, self).__init__()
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.resize(300, 100)
        self.setWindowTitle(r"Wysyłanie danych")
        self.dataSender = DataSender(self)
        self.dataSender.db = db
        self.dataSender.dbtable = dbtable
        self.dataSender.fileData = fileData
        self.dataSender.sheet = sheet
        self.lblCount = QLabel()
        lt = QVBoxLayout(self)
        lt.addWidget(self.lblCount)


class DataSender(QThread):

    def __init__(self, parent=None):
        super(DataSender, self).__init__(parent)
        self.parent = parent
        self.db = ""
        self.dbtable = ""
        self.fileData = FileData()
        self.sheet = ""

    def run(self):
        connection = pymysql.connect(host='localhost',
                                     user='tomek',
                                     password='haslo',
                                     db=self.db,
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        try:
            with connection.cursor() as cursor:
                sql = "insert into " + self.dbtable + " values "
                for count, row in enumerate(self.fileData.data[self.sheet]):
                    sql += "(" + "'%s'," * (self.fileData.ncol[self.sheet] - 1)
                    sql += "'%s'),"
                    sql = sql % row
                    if (not count % 50 or
                       count == self.fileData.nrow[self.sheet] - 1):
                        sql = sql[:-1] + ";"
                        cursor.execute(sql)
                        connection.commit()
                        sql = "insert into " + self.dbtable + " values "
                        text = "Wysłano " + str(count + 1) + " wierszy."
                        self.parent.lblCount.setText(text)
        except (pymysql.err.InternalError, pymysql.err.OperationalError) as err:
            self.popups.append(PopupError(error_message=str(err)))
            self.popups[-1].show()
        else:
            connection.close()


class TableWidget(QWidget):

    def __init__(self):
        super(TableWidget, self).__init__()
        self.fileData = FileData()
        self.sheet = ""
        self.tw = QTableWidget()
        self.tw.horizontalHeader().setSectionsMovable(True)
        self.btnRemove = QPushButton("Usuń kolumnę")
        self.btnRemove.clicked.connect(self.hide_column)
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

    def set_file_data(self, fileData, sheet):
        self.btnUndelete.setEnabled(False)
        self.btnRemove.setEnabled(True)
        self.tw.clear()
        self.fileData = fileData
        self.sheet = sheet  # potrzebne do hide_column
        for i in range(self.fileData.ncol[self.sheet]):
            self.tw.horizontalHeader().setSectionHidden(i, False)
        self.m.clear()
        self.tw.setColumnCount(self.fileData.ncol[sheet])
        self.tw.setRowCount(self.fileData.nrow[sheet])
        self.tw.setHorizontalHeaderLabels(self.fileData.header[sheet])
        for row, line in enumerate(self.fileData.data[sheet]):
            for column, item in enumerate(line):
                qtwitem = QTableWidgetItem(str(item))
                self.tw.setItem(row, column, qtwitem)

    def hide_column(self):
        self.btnUndelete.setEnabled(True)
        if not self.sheet:
            self.sheet = "csv"
        index = self.tw.currentColumn()
        if index == -1:
            return
        self.tw.horizontalHeader().setSectionHidden(index, True)
        self.m.addAction(self.fileData.header[self.sheet][index],
                         partial(self.show_column, index))
        ncol = self.fileData.ncol[self.sheet]
        if self.tw.horizontalHeader().hiddenSectionCount() == ncol:
            self.btnRemove.setEnabled(False)

    def show_column(self, index):
        self.btnRemove.setEnabled(True)
        self.tw.horizontalHeader().setSectionHidden(index, False)
        self.m.clear()
        for i in range(self.fileData.ncol[self.sheet]):
            if self.tw.horizontalHeader().isSectionHidden(i):
                self.m.addAction(self.fileData.header[self.sheet][i],
                                 partial(self.show_column, i))
        if not self.tw.horizontalHeader().hiddenSectionCount():
            self.btnUndelete.setEnabled(False)


class FileData:

    def __init__(self):
        self.data = dict()
        self.header = dict()
        self.ncol = dict()
        self.nrow = dict()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = MainWidget()
    mw.show()
    app.exec_()
