# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'QUMainWindow.ui'
##
## Created by: Qt User Interface Compiler version 6.2.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
                            QMetaObject, QObject, QPoint, QRect, QSize, Qt,
                            QTime, QUrl)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor, QFont,
                           QFontDatabase, QGradient, QIcon, QImage,
                           QKeySequence, QLinearGradient, QPainter, QPalette,
                           QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox,
                               QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QHeaderView, QLabel, QLineEdit, QMainWindow,
                               QMenuBar, QPushButton, QSizePolicy, QSpacerItem,
                               QStatusBar, QTableView, QVBoxLayout, QWidget)

import resources_rc


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1493, 816)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(4, 4, 4, 4)
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.groupBox = QGroupBox(self.centralwidget)
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(4, 4, 4, 4)
        self.label_username = QLabel(self.groupBox)
        self.label_username.setObjectName("label_username")

        self.horizontalLayout_2.addWidget(self.label_username)

        self.lineEdit_user = QLineEdit(self.groupBox)
        self.lineEdit_user.setObjectName("lineEdit_user")

        self.horizontalLayout_2.addWidget(self.lineEdit_user)

        self.label_password = QLabel(self.groupBox)
        self.label_password.setObjectName("label_password")

        self.horizontalLayout_2.addWidget(self.label_password)

        self.lineEdit_password = QLineEdit(self.groupBox)
        self.lineEdit_password.setObjectName("lineEdit_password")
        self.lineEdit_password.setEchoMode(QLineEdit.Password)

        self.horizontalLayout_2.addWidget(self.lineEdit_password)

        self.pushButton_login = QPushButton(self.groupBox)
        self.pushButton_login.setObjectName("pushButton_login")
        font = QFont()
        font.setPointSize(16)
        self.pushButton_login.setFont(font)
        self.pushButton_login.setStyleSheet("background-color: rgb(0, 102, 0);")
        icon = QIcon()
        icon.addFile(
            ":/icons/resources/faviconUSDB.ico", QSize(), QIcon.Normal, QIcon.Off
        )
        self.pushButton_login.setIcon(icon)

        self.horizontalLayout_2.addWidget(self.pushButton_login)

        self.pushButton_refresh = QPushButton(self.groupBox)
        self.pushButton_refresh.setObjectName("pushButton_refresh")
        self.pushButton_refresh.setFont(font)
        self.pushButton_refresh.setStyleSheet("background-color: rgb(0, 102, 0);")
        self.pushButton_refresh.setIcon(icon)

        self.horizontalLayout_2.addWidget(self.pushButton_refresh)

        self.horizontalLayout_3.addWidget(self.groupBox)

        self.horizontalSpacer = QSpacerItem(
            347, 17, QSizePolicy.Expanding, QSizePolicy.Minimum
        )

        self.horizontalLayout_3.addItem(self.horizontalSpacer)

        self.groupBox_2 = QGroupBox(self.centralwidget)
        self.groupBox_2.setObjectName("groupBox_2")
        self.groupBox_2.setCheckable(True)
        self.horizontalLayout_4 = QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(4, 4, 4, 4)
        self.lineEdit_song_dir = QLineEdit(self.groupBox_2)
        self.lineEdit_song_dir.setObjectName("lineEdit_song_dir")

        self.horizontalLayout_4.addWidget(self.lineEdit_song_dir)

        self.pushButton_select_song_dir = QPushButton(self.groupBox_2)
        self.pushButton_select_song_dir.setObjectName("pushButton_select_song_dir")
        self.pushButton_select_song_dir.setEnabled(True)
        self.pushButton_select_song_dir.setFont(font)
        self.pushButton_select_song_dir.setStyleSheet(
            "background-color: rgb(0, 102, 0);"
        )

        self.horizontalLayout_4.addWidget(self.pushButton_select_song_dir)

        self.horizontalLayout_3.addWidget(self.groupBox_2)

        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.groupBox_3 = QGroupBox(self.centralwidget)
        self.groupBox_3.setObjectName("groupBox_3")
        self.horizontalLayout_6 = QHBoxLayout(self.groupBox_3)
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(4, 4, 4, 4)
        self.lineEdit_search = QLineEdit(self.groupBox_3)
        self.lineEdit_search.setObjectName("lineEdit_search")

        self.horizontalLayout_6.addWidget(self.lineEdit_search)

        self.comboBox_search_column = QComboBox(self.groupBox_3)
        self.comboBox_search_column.addItem("")
        icon1 = QIcon()
        icon1.addFile(":/icons/resources/artist.png", QSize(), QIcon.Normal, QIcon.Off)
        self.comboBox_search_column.addItem(icon1, "")
        icon2 = QIcon()
        icon2.addFile(":/icons/resources/title.png", QSize(), QIcon.Normal, QIcon.Off)
        self.comboBox_search_column.addItem(icon2, "")
        icon3 = QIcon()
        icon3.addFile(
            ":/icons/resources/language.png", QSize(), QIcon.Normal, QIcon.Off
        )
        self.comboBox_search_column.addItem(icon3, "")
        icon4 = QIcon()
        icon4.addFile(":/icons/resources/edition.png", QSize(), QIcon.Normal, QIcon.Off)
        self.comboBox_search_column.addItem(icon4, "")
        self.comboBox_search_column.setObjectName("comboBox_search_column")

        self.horizontalLayout_6.addWidget(self.comboBox_search_column)

        self.checkBox_case_sensitive = QCheckBox(self.groupBox_3)
        self.checkBox_case_sensitive.setObjectName("checkBox_case_sensitive")

        self.horizontalLayout_6.addWidget(self.checkBox_case_sensitive)

        self.horizontalLayout_6.setStretch(0, 5)
        self.horizontalLayout_6.setStretch(1, 1)

        self.verticalLayout_2.addWidget(self.groupBox_3)

        self.groupBox_4 = QGroupBox(self.centralwidget)
        self.groupBox_4.setObjectName("groupBox_4")
        self.horizontalLayout_5 = QHBoxLayout(self.groupBox_4)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(4, 4, 4, 4)
        self.label_10 = QLabel(self.groupBox_4)
        self.label_10.setObjectName("label_10")
        self.label_10.setPixmap(QPixmap(":/icons/resources/artist.png"))

        self.horizontalLayout_5.addWidget(self.label_10)

        self.comboBox_artist = QComboBox(self.groupBox_4)
        self.comboBox_artist.setObjectName("comboBox_artist")
        self.comboBox_artist.setEditable(True)

        self.horizontalLayout_5.addWidget(self.comboBox_artist)

        self.label_11 = QLabel(self.groupBox_4)
        self.label_11.setObjectName("label_11")
        self.label_11.setPixmap(QPixmap(":/icons/resources/title.png"))

        self.horizontalLayout_5.addWidget(self.label_11)

        self.comboBox_title = QComboBox(self.groupBox_4)
        self.comboBox_title.setObjectName("comboBox_title")
        self.comboBox_title.setEditable(True)

        self.horizontalLayout_5.addWidget(self.comboBox_title)

        self.label_12 = QLabel(self.groupBox_4)
        self.label_12.setObjectName("label_12")
        self.label_12.setPixmap(QPixmap(":/icons/resources/language.png"))

        self.horizontalLayout_5.addWidget(self.label_12)

        self.comboBox_language = QComboBox(self.groupBox_4)
        self.comboBox_language.setObjectName("comboBox_language")
        self.comboBox_language.setEditable(True)

        self.horizontalLayout_5.addWidget(self.comboBox_language)

        self.label_13 = QLabel(self.groupBox_4)
        self.label_13.setObjectName("label_13")
        self.label_13.setPixmap(QPixmap(":/icons/resources/edition.png"))

        self.horizontalLayout_5.addWidget(self.label_13)

        self.comboBox_edition = QComboBox(self.groupBox_4)
        self.comboBox_edition.setObjectName("comboBox_edition")
        self.comboBox_edition.setEditable(True)

        self.horizontalLayout_5.addWidget(self.comboBox_edition)

        self.label_14 = QLabel(self.groupBox_4)
        self.label_14.setObjectName("label_14")
        self.label_14.setPixmap(QPixmap(":/icons/resources/golden_notes.png"))

        self.horizontalLayout_5.addWidget(self.label_14)

        self.comboBox_goldennotes = QComboBox(self.groupBox_4)
        self.comboBox_goldennotes.addItem("")
        self.comboBox_goldennotes.addItem("")
        self.comboBox_goldennotes.addItem("")
        self.comboBox_goldennotes.setObjectName("comboBox_goldennotes")

        self.horizontalLayout_5.addWidget(self.comboBox_goldennotes)

        self.label_15 = QLabel(self.groupBox_4)
        self.label_15.setObjectName("label_15")
        self.label_15.setPixmap(QPixmap(":/icons/resources/rating.png"))

        self.horizontalLayout_5.addWidget(self.label_15)

        self.comboBox_rating = QComboBox(self.groupBox_4)
        self.comboBox_rating.addItem("")
        self.comboBox_rating.addItem("")
        self.comboBox_rating.addItem("")
        self.comboBox_rating.addItem("")
        self.comboBox_rating.addItem("")
        self.comboBox_rating.addItem("")
        self.comboBox_rating.addItem("")
        self.comboBox_rating.addItem("")
        self.comboBox_rating.addItem("")
        self.comboBox_rating.addItem("")
        self.comboBox_rating.setObjectName("comboBox_rating")

        self.horizontalLayout_5.addWidget(self.comboBox_rating)

        self.label_16 = QLabel(self.groupBox_4)
        self.label_16.setObjectName("label_16")
        self.label_16.setPixmap(QPixmap(":/icons/resources/views.png"))

        self.horizontalLayout_5.addWidget(self.label_16)

        self.comboBox_views = QComboBox(self.groupBox_4)
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.setObjectName("comboBox_views")

        self.horizontalLayout_5.addWidget(self.comboBox_views)

        self.horizontalLayout_5.setStretch(1, 2)
        self.horizontalLayout_5.setStretch(3, 2)
        self.horizontalLayout_5.setStretch(5, 2)
        self.horizontalLayout_5.setStretch(7, 2)
        self.horizontalLayout_5.setStretch(9, 1)
        self.horizontalLayout_5.setStretch(11, 1)
        self.horizontalLayout_5.setStretch(13, 1)

        self.verticalLayout_2.addWidget(self.groupBox_4)

        self.tableView_availableSongs = QTableView(self.centralwidget)
        self.tableView_availableSongs.setObjectName("tableView_availableSongs")
        self.tableView_availableSongs.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableView_availableSongs.setAlternatingRowColors(True)
        self.tableView_availableSongs.setSelectionMode(QAbstractItemView.MultiSelection)
        self.tableView_availableSongs.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableView_availableSongs.setSortingEnabled(True)
        self.tableView_availableSongs.verticalHeader().setVisible(False)
        self.tableView_availableSongs.verticalHeader().setMinimumSectionSize(24)
        self.tableView_availableSongs.verticalHeader().setDefaultSectionSize(24)

        self.verticalLayout_2.addWidget(self.tableView_availableSongs)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.groupBox_songfile = QGroupBox(self.centralwidget)
        self.groupBox_songfile.setObjectName("groupBox_songfile")
        self.groupBox_songfile.setCheckable(True)
        self.formLayout = QFormLayout(self.groupBox_songfile)
        self.formLayout.setObjectName("formLayout")
        self.formLayout.setVerticalSpacing(2)
        self.formLayout.setContentsMargins(4, 4, 4, 4)
        self.label = QLabel(self.groupBox_songfile)
        self.label.setObjectName("label")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label)

        self.comboBox_encoding = QComboBox(self.groupBox_songfile)
        self.comboBox_encoding.addItem("")
        self.comboBox_encoding.addItem("")
        self.comboBox_encoding.addItem("")
        self.comboBox_encoding.setObjectName("comboBox_encoding")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.comboBox_encoding)

        self.label_8 = QLabel(self.groupBox_songfile)
        self.label_8.setObjectName("label_8")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_8)

        self.comboBox_line_endings = QComboBox(self.groupBox_songfile)
        self.comboBox_line_endings.addItem("")
        self.comboBox_line_endings.addItem("")
        self.comboBox_line_endings.setObjectName("comboBox_line_endings")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.comboBox_line_endings)

        self.horizontalLayout_7.addWidget(self.groupBox_songfile)

        self.groupBox_audio = QGroupBox(self.centralwidget)
        self.groupBox_audio.setObjectName("groupBox_audio")
        self.groupBox_audio.setCheckable(True)
        self.formLayout_2 = QFormLayout(self.groupBox_audio)
        self.formLayout_2.setObjectName("formLayout_2")
        self.formLayout_2.setVerticalSpacing(2)
        self.formLayout_2.setContentsMargins(4, 4, 4, 4)
        self.label_7 = QLabel(self.groupBox_audio)
        self.label_7.setObjectName("label_7")

        self.formLayout_2.setWidget(0, QFormLayout.LabelRole, self.label_7)

        self.comboBox_audio_format = QComboBox(self.groupBox_audio)
        self.comboBox_audio_format.addItem("")
        self.comboBox_audio_format.addItem("")
        self.comboBox_audio_format.addItem("")
        self.comboBox_audio_format.setObjectName("comboBox_audio_format")

        self.formLayout_2.setWidget(
            0, QFormLayout.FieldRole, self.comboBox_audio_format
        )

        self.horizontalLayout_7.addWidget(self.groupBox_audio)

        self.groupBox_reencode_audio = QGroupBox(self.centralwidget)
        self.groupBox_reencode_audio.setObjectName("groupBox_reencode_audio")
        self.groupBox_reencode_audio.setCheckable(True)
        self.groupBox_reencode_audio.setChecked(False)
        self.formLayout_6 = QFormLayout(self.groupBox_reencode_audio)
        self.formLayout_6.setObjectName("formLayout_6")
        self.formLayout_6.setContentsMargins(4, 4, 4, 4)
        self.label_19 = QLabel(self.groupBox_reencode_audio)
        self.label_19.setObjectName("label_19")

        self.formLayout_6.setWidget(0, QFormLayout.LabelRole, self.label_19)

        self.comboBox_audio_conversion_format = QComboBox(self.groupBox_reencode_audio)
        self.comboBox_audio_conversion_format.addItem("")
        self.comboBox_audio_conversion_format.addItem("")
        self.comboBox_audio_conversion_format.addItem("")
        self.comboBox_audio_conversion_format.setObjectName(
            "comboBox_audio_conversion_format"
        )

        self.formLayout_6.setWidget(
            0, QFormLayout.FieldRole, self.comboBox_audio_conversion_format
        )

        self.horizontalLayout_7.addWidget(self.groupBox_reencode_audio)

        self.groupBox_video = QGroupBox(self.centralwidget)
        self.groupBox_video.setObjectName("groupBox_video")
        self.groupBox_video.setCheckable(True)
        self.formLayout_3 = QFormLayout(self.groupBox_video)
        self.formLayout_3.setObjectName("formLayout_3")
        self.formLayout_3.setVerticalSpacing(2)
        self.formLayout_3.setContentsMargins(4, 4, 4, 4)
        self.label_4 = QLabel(self.groupBox_video)
        self.label_4.setObjectName("label_4")

        self.formLayout_3.setWidget(0, QFormLayout.LabelRole, self.label_4)

        self.comboBox_videocontainer = QComboBox(self.groupBox_video)
        self.comboBox_videocontainer.addItem("")
        self.comboBox_videocontainer.addItem("")
        self.comboBox_videocontainer.addItem("")
        self.comboBox_videocontainer.setObjectName("comboBox_videocontainer")

        self.formLayout_3.setWidget(
            0, QFormLayout.FieldRole, self.comboBox_videocontainer
        )

        self.label_5 = QLabel(self.groupBox_video)
        self.label_5.setObjectName("label_5")

        self.formLayout_3.setWidget(1, QFormLayout.LabelRole, self.label_5)

        self.comboBox_videoresolution = QComboBox(self.groupBox_video)
        self.comboBox_videoresolution.addItem("")
        self.comboBox_videoresolution.addItem("")
        self.comboBox_videoresolution.setObjectName("comboBox_videoresolution")

        self.formLayout_3.setWidget(
            1, QFormLayout.FieldRole, self.comboBox_videoresolution
        )

        self.label_3 = QLabel(self.groupBox_video)
        self.label_3.setObjectName("label_3")

        self.formLayout_3.setWidget(2, QFormLayout.LabelRole, self.label_3)

        self.comboBox_fps = QComboBox(self.groupBox_video)
        self.comboBox_fps.addItem("")
        self.comboBox_fps.addItem("")
        self.comboBox_fps.setObjectName("comboBox_fps")

        self.formLayout_3.setWidget(2, QFormLayout.FieldRole, self.comboBox_fps)

        self.horizontalLayout_7.addWidget(self.groupBox_video)

        self.groupBox_reencode_video = QGroupBox(self.centralwidget)
        self.groupBox_reencode_video.setObjectName("groupBox_reencode_video")
        self.groupBox_reencode_video.setCheckable(True)
        self.groupBox_reencode_video.setChecked(False)
        self.label_18 = QLabel(self.groupBox_reencode_video)
        self.label_18.setObjectName("label_18")
        self.label_18.setGeometry(QRect(15, 25, 80, 16))
        self.comboBox_videoencoder = QComboBox(self.groupBox_reencode_video)
        self.comboBox_videoencoder.addItem("")
        self.comboBox_videoencoder.addItem("")
        self.comboBox_videoencoder.addItem("")
        self.comboBox_videoencoder.addItem("")
        self.comboBox_videoencoder.setObjectName("comboBox_videoencoder")
        self.comboBox_videoencoder.setGeometry(QRect(100, 23, 118, 32))

        self.horizontalLayout_7.addWidget(self.groupBox_reencode_video)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox_cover = QGroupBox(self.centralwidget)
        self.groupBox_cover.setObjectName("groupBox_cover")
        self.groupBox_cover.setCheckable(True)
        self.formLayout_4 = QFormLayout(self.groupBox_cover)
        self.formLayout_4.setObjectName("formLayout_4")
        self.formLayout_4.setVerticalSpacing(2)
        self.formLayout_4.setContentsMargins(4, 4, 4, 4)

        self.verticalLayout.addWidget(self.groupBox_cover)

        self.groupBox_background = QGroupBox(self.centralwidget)
        self.groupBox_background.setObjectName("groupBox_background")
        self.groupBox_background.setCheckable(True)
        self.formLayout_5 = QFormLayout(self.groupBox_background)
        self.formLayout_5.setObjectName("formLayout_5")
        self.formLayout_5.setVerticalSpacing(2)
        self.formLayout_5.setContentsMargins(4, 4, 4, 4)
        self.label_6 = QLabel(self.groupBox_background)
        self.label_6.setObjectName("label_6")

        self.formLayout_5.setWidget(0, QFormLayout.LabelRole, self.label_6)

        self.comboBox_background = QComboBox(self.groupBox_background)
        self.comboBox_background.addItem("")
        self.comboBox_background.addItem("")
        self.comboBox_background.setObjectName("comboBox_background")

        self.formLayout_5.setWidget(0, QFormLayout.FieldRole, self.comboBox_background)

        self.verticalLayout.addWidget(self.groupBox_background)

        self.horizontalLayout_7.addLayout(self.verticalLayout)

        self.verticalLayout_2.addLayout(self.horizontalLayout_7)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalSpacer_2 = QSpacerItem(
            559, 46, QSizePolicy.Expanding, QSizePolicy.Minimum
        )

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.pushButton_downloadSelectedSongs = QPushButton(self.centralwidget)
        self.pushButton_downloadSelectedSongs.setObjectName(
            "pushButton_downloadSelectedSongs"
        )
        self.pushButton_downloadSelectedSongs.setEnabled(True)
        self.pushButton_downloadSelectedSongs.setFont(font)
        self.pushButton_downloadSelectedSongs.setStyleSheet(
            "background-color: rgb(0, 102, 0);"
        )

        self.horizontalLayout.addWidget(self.pushButton_downloadSelectedSongs)

        self.verticalLayout_2.addLayout(self.horizontalLayout)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName("menubar")
        self.menubar.setGeometry(QRect(0, 0, 1493, 24))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)

    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(
            QCoreApplication.translate("MainWindow", "USDB Song Manager", None)
        )
        self.groupBox.setTitle(
            QCoreApplication.translate("MainWindow", "USDB connection", None)
        )
        self.label_username.setText(
            QCoreApplication.translate("MainWindow", "User", None)
        )
        self.label_password.setText(
            QCoreApplication.translate("MainWindow", "Password", None)
        )
        self.pushButton_login.setText(
            QCoreApplication.translate("MainWindow", " Login", None)
        )
        self.pushButton_refresh.setText(
            QCoreApplication.translate("MainWindow", " Refresh", None)
        )
        self.groupBox_2.setTitle(
            QCoreApplication.translate(
                "MainWindow", "Synchronize to local song directory", None
            )
        )
        self.lineEdit_song_dir.setText(
            QCoreApplication.translate("MainWindow", "./songs", None)
        )
        self.pushButton_select_song_dir.setText(
            QCoreApplication.translate("MainWindow", "Select song folder", None)
        )
        self.groupBox_3.setTitle(
            QCoreApplication.translate("MainWindow", "Search (RexExp)", None)
        )
        self.comboBox_search_column.setItemText(
            0, QCoreApplication.translate("MainWindow", "any", None)
        )
        self.comboBox_search_column.setItemText(
            1, QCoreApplication.translate("MainWindow", "Artist", None)
        )
        self.comboBox_search_column.setItemText(
            2, QCoreApplication.translate("MainWindow", "Title", None)
        )
        self.comboBox_search_column.setItemText(
            3, QCoreApplication.translate("MainWindow", "Language", None)
        )
        self.comboBox_search_column.setItemText(
            4, QCoreApplication.translate("MainWindow", "Edition", None)
        )

        self.checkBox_case_sensitive.setText(
            QCoreApplication.translate("MainWindow", "Case sensitive", None)
        )
        self.groupBox_4.setTitle(
            QCoreApplication.translate("MainWindow", "Filter", None)
        )
        self.label_10.setText("")
        self.label_11.setText("")
        self.label_12.setText("")
        self.label_13.setText("")
        self.label_14.setText("")
        self.comboBox_goldennotes.setItemText(
            0, QCoreApplication.translate("MainWindow", "any", None)
        )
        self.comboBox_goldennotes.setItemText(
            1, QCoreApplication.translate("MainWindow", "yes", None)
        )
        self.comboBox_goldennotes.setItemText(
            2, QCoreApplication.translate("MainWindow", "no", None)
        )

        self.label_15.setText("")
        self.comboBox_rating.setItemText(
            0, QCoreApplication.translate("MainWindow", "any", None)
        )
        self.comboBox_rating.setItemText(
            1, QCoreApplication.translate("MainWindow", "\u2605", None)
        )
        self.comboBox_rating.setItemText(
            2, QCoreApplication.translate("MainWindow", "\u2605\u2605", None)
        )
        self.comboBox_rating.setItemText(
            3, QCoreApplication.translate("MainWindow", "\u2605\u2605\u2605", None)
        )
        self.comboBox_rating.setItemText(
            4,
            QCoreApplication.translate("MainWindow", "\u2605\u2605\u2605\u2605", None),
        )
        self.comboBox_rating.setItemText(
            5,
            QCoreApplication.translate(
                "MainWindow", "\u2605\u2605\u2605\u2605\u2605", None
            ),
        )
        self.comboBox_rating.setItemText(
            6, QCoreApplication.translate("MainWindow", "\u2605 or more", None)
        )
        self.comboBox_rating.setItemText(
            7, QCoreApplication.translate("MainWindow", "\u2605\u2605 or more", None)
        )
        self.comboBox_rating.setItemText(
            8,
            QCoreApplication.translate(
                "MainWindow", "\u2605\u2605\u2605 or more", None
            ),
        )
        self.comboBox_rating.setItemText(
            9,
            QCoreApplication.translate(
                "MainWindow", "\u2605\u2605\u2605\u2605 or more", None
            ),
        )

        self.label_16.setText("")
        self.comboBox_views.setItemText(
            0, QCoreApplication.translate("MainWindow", "any", None)
        )
        self.comboBox_views.setItemText(
            1, QCoreApplication.translate("MainWindow", "100+", None)
        )
        self.comboBox_views.setItemText(
            2, QCoreApplication.translate("MainWindow", "200+", None)
        )
        self.comboBox_views.setItemText(
            3, QCoreApplication.translate("MainWindow", "300+", None)
        )
        self.comboBox_views.setItemText(
            4, QCoreApplication.translate("MainWindow", "400+", None)
        )
        self.comboBox_views.setItemText(
            5, QCoreApplication.translate("MainWindow", "500+", None)
        )

        self.groupBox_songfile.setTitle(
            QCoreApplication.translate("MainWindow", "Download song file", None)
        )
        self.label.setText(QCoreApplication.translate("MainWindow", "Encoding", None))
        self.comboBox_encoding.setItemText(
            0, QCoreApplication.translate("MainWindow", "UTF-8", None)
        )
        self.comboBox_encoding.setItemText(
            1, QCoreApplication.translate("MainWindow", "UTF-8 BOM", None)
        )
        self.comboBox_encoding.setItemText(
            2, QCoreApplication.translate("MainWindow", "CP1252", None)
        )

        self.label_8.setText(
            QCoreApplication.translate("MainWindow", "Line Endings", None)
        )
        self.comboBox_line_endings.setItemText(
            0, QCoreApplication.translate("MainWindow", "Windows (CRLF)", None)
        )
        self.comboBox_line_endings.setItemText(
            1, QCoreApplication.translate("MainWindow", "Mac/Linux (LF)", None)
        )

        self.groupBox_audio.setTitle(
            QCoreApplication.translate("MainWindow", "Download audio", None)
        )
        self.label_7.setText(
            QCoreApplication.translate("MainWindow", "Audio Format", None)
        )
        self.comboBox_audio_format.setItemText(
            0, QCoreApplication.translate("MainWindow", ".m4a (mp4a)", None)
        )
        self.comboBox_audio_format.setItemText(
            1, QCoreApplication.translate("MainWindow", ".webm (opus)", "mp3")
        )
        self.comboBox_audio_format.setItemText(
            2, QCoreApplication.translate("MainWindow", "bestaudio", None)
        )

        self.groupBox_reencode_audio.setTitle(
            QCoreApplication.translate("MainWindow", "Reencode audio", None)
        )
        self.label_19.setText(
            QCoreApplication.translate("MainWindow", "Audio Format", None)
        )
        self.comboBox_audio_conversion_format.setItemText(
            0, QCoreApplication.translate("MainWindow", ".mp3 (MPEG)", None)
        )
        self.comboBox_audio_conversion_format.setItemText(
            1, QCoreApplication.translate("MainWindow", ".ogg (Vorbis)", None)
        )
        self.comboBox_audio_conversion_format.setItemText(
            2, QCoreApplication.translate("MainWindow", ".opus (Opus)", None)
        )

        self.groupBox_video.setTitle(
            QCoreApplication.translate("MainWindow", "Download video", None)
        )
        self.label_4.setText(
            QCoreApplication.translate("MainWindow", "Video container", None)
        )
        self.comboBox_videocontainer.setItemText(
            0, QCoreApplication.translate("MainWindow", ".mp4", None)
        )
        self.comboBox_videocontainer.setItemText(
            1, QCoreApplication.translate("MainWindow", ".webm", None)
        )
        self.comboBox_videocontainer.setItemText(
            2, QCoreApplication.translate("MainWindow", "bestvideo", None)
        )

        self.label_5.setText(
            QCoreApplication.translate("MainWindow", "Max. resolution", None)
        )
        self.comboBox_videoresolution.setItemText(
            0, QCoreApplication.translate("MainWindow", "1080p", None)
        )
        self.comboBox_videoresolution.setItemText(
            1, QCoreApplication.translate("MainWindow", "720p", None)
        )

        self.label_3.setText(QCoreApplication.translate("MainWindow", "Max. fps", None))
        self.comboBox_fps.setItemText(
            0, QCoreApplication.translate("MainWindow", "30", None)
        )
        self.comboBox_fps.setItemText(
            1, QCoreApplication.translate("MainWindow", "60", None)
        )

        self.groupBox_reencode_video.setTitle(
            QCoreApplication.translate("MainWindow", "Reencode video", None)
        )
        self.label_18.setText(
            QCoreApplication.translate("MainWindow", "Video Format", None)
        )
        self.comboBox_videoencoder.setItemText(
            0, QCoreApplication.translate("MainWindow", "h264", None)
        )
        self.comboBox_videoencoder.setItemText(
            1, QCoreApplication.translate("MainWindow", "h265", None)
        )
        self.comboBox_videoencoder.setItemText(
            2, QCoreApplication.translate("MainWindow", "libvpx-vp9", None)
        )
        self.comboBox_videoencoder.setItemText(
            3, QCoreApplication.translate("MainWindow", "libaom-av1", None)
        )

        self.groupBox_cover.setTitle(
            QCoreApplication.translate(
                "MainWindow", "Download cover \u2013 settings:", None
            )
        )
        self.groupBox_background.setTitle(
            QCoreApplication.translate(
                "MainWindow", "Download background \u2013 settings:", None
            )
        )
        self.label_6.setText(QCoreApplication.translate("MainWindow", "Download", None))
        self.comboBox_background.setItemText(
            0, QCoreApplication.translate("MainWindow", "always", None)
        )
        self.comboBox_background.setItemText(
            1, QCoreApplication.translate("MainWindow", "only if no video", None)
        )

        self.pushButton_downloadSelectedSongs.setText(
            QCoreApplication.translate("MainWindow", "Download selected songs!", None)
        )

    # retranslateUi
