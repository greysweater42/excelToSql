#!/usr/bin/env python

import pymysql.cursors
from PyQt5.QtWidgets import QDialog, QPushButton, QLineEdit, QHBoxLayout, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QApplication, QGroupBox


class MainWindow(QDialog):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.resize(800, 600)

        self.leDBName = QLineEditUrl("nazwa połączenia ODBC", "MIS")
        self.btnReadData = QPushButton("Pobierz listę tabel")
        self.btnReadData.clicked.connect(self.get_data)
        self.twTables = QTreeWidget()
        self.twTables.setColumnCount(2)
        self.twTables.setHeaderLabels(["tabele", "typ danych"])

        self.leFileName = QLineEditUrl("lokalizacja pliku")

        gbDB = QGroupBox()
        gbDBLayout = QVBoxLayout()
        gbDBLayout.addWidget(self.leDBName)
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


if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)
    mw = MainWindow()
    sys.exit(mw.exec_())
