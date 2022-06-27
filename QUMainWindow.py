# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'QUMainWindow.ui'
##
## Created by: Qt User Interface Compiler version 6.2.3
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox,
    QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMenuBar,
    QPushButton, QSizePolicy, QSpacerItem, QStatusBar,
    QTableView, QVBoxLayout, QWidget)
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1493, 816)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_2 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(4, 4, 4, 4)
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.groupBox = QGroupBox(self.centralwidget)
        self.groupBox.setObjectName(u"groupBox")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(4, 4, 4, 4)
        self.pushButton_get_songlist = QPushButton(self.groupBox)
        self.pushButton_get_songlist.setObjectName(u"pushButton_get_songlist")
        font = QFont()
        font.setPointSize(16)
        self.pushButton_get_songlist.setFont(font)
        icon = QIcon()
        icon.addFile(u":/icons/resources/faviconUSDB.ico", QSize(), QIcon.Normal, QIcon.Off)
        self.pushButton_get_songlist.setIcon(icon)

        self.horizontalLayout_2.addWidget(self.pushButton_get_songlist)


        self.horizontalLayout_3.addWidget(self.groupBox)

        self.horizontalSpacer = QSpacerItem(347, 17, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer)

        self.groupBox_2 = QGroupBox(self.centralwidget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setCheckable(True)
        self.horizontalLayout_4 = QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(4, 4, 4, 4)
        self.lineEdit_song_dir = QLineEdit(self.groupBox_2)
        self.lineEdit_song_dir.setObjectName(u"lineEdit_song_dir")

        self.horizontalLayout_4.addWidget(self.lineEdit_song_dir)

        self.pushButton_select_song_dir = QPushButton(self.groupBox_2)
        self.pushButton_select_song_dir.setObjectName(u"pushButton_select_song_dir")
        self.pushButton_select_song_dir.setEnabled(True)
        self.pushButton_select_song_dir.setFont(font)

        self.horizontalLayout_4.addWidget(self.pushButton_select_song_dir)


        self.horizontalLayout_3.addWidget(self.groupBox_2)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.groupBox_3 = QGroupBox(self.centralwidget)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.horizontalLayout_6 = QHBoxLayout(self.groupBox_3)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(4, 4, 4, 4)
        self.lineEdit_search = QLineEdit(self.groupBox_3)
        self.lineEdit_search.setObjectName(u"lineEdit_search")

        self.horizontalLayout_6.addWidget(self.lineEdit_search)

        self.comboBox_search_column = QComboBox(self.groupBox_3)
        self.comboBox_search_column.addItem("")
        icon1 = QIcon()
        icon1.addFile(u":/icons/resources/artist.png", QSize(), QIcon.Normal, QIcon.Off)
        self.comboBox_search_column.addItem(icon1, "")
        icon2 = QIcon()
        icon2.addFile(u":/icons/resources/title.png", QSize(), QIcon.Normal, QIcon.Off)
        self.comboBox_search_column.addItem(icon2, "")
        icon3 = QIcon()
        icon3.addFile(u":/icons/resources/language.png", QSize(), QIcon.Normal, QIcon.Off)
        self.comboBox_search_column.addItem(icon3, "")
        icon4 = QIcon()
        icon4.addFile(u":/icons/resources/edition.png", QSize(), QIcon.Normal, QIcon.Off)
        self.comboBox_search_column.addItem(icon4, "")
        self.comboBox_search_column.setObjectName(u"comboBox_search_column")

        self.horizontalLayout_6.addWidget(self.comboBox_search_column)

        self.checkBox_case_sensitive = QCheckBox(self.groupBox_3)
        self.checkBox_case_sensitive.setObjectName(u"checkBox_case_sensitive")

        self.horizontalLayout_6.addWidget(self.checkBox_case_sensitive)

        self.horizontalLayout_6.setStretch(0, 5)
        self.horizontalLayout_6.setStretch(1, 1)

        self.verticalLayout_2.addWidget(self.groupBox_3)

        self.groupBox_4 = QGroupBox(self.centralwidget)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.horizontalLayout_5 = QHBoxLayout(self.groupBox_4)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(4, 4, 4, 4)
        self.label_10 = QLabel(self.groupBox_4)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setPixmap(QPixmap(u":/icons/resources/artist.png"))

        self.horizontalLayout_5.addWidget(self.label_10)

        self.comboBox_artist = QComboBox(self.groupBox_4)
        self.comboBox_artist.setObjectName(u"comboBox_artist")
        self.comboBox_artist.setEditable(True)

        self.horizontalLayout_5.addWidget(self.comboBox_artist)

        self.label_11 = QLabel(self.groupBox_4)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setPixmap(QPixmap(u":/icons/resources/title.png"))

        self.horizontalLayout_5.addWidget(self.label_11)

        self.comboBox_title = QComboBox(self.groupBox_4)
        self.comboBox_title.setObjectName(u"comboBox_title")
        self.comboBox_title.setEditable(True)

        self.horizontalLayout_5.addWidget(self.comboBox_title)

        self.label_12 = QLabel(self.groupBox_4)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setPixmap(QPixmap(u":/icons/resources/language.png"))

        self.horizontalLayout_5.addWidget(self.label_12)

        self.comboBox_language = QComboBox(self.groupBox_4)
        self.comboBox_language.setObjectName(u"comboBox_language")
        self.comboBox_language.setEditable(True)

        self.horizontalLayout_5.addWidget(self.comboBox_language)

        self.label_13 = QLabel(self.groupBox_4)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setPixmap(QPixmap(u":/icons/resources/edition.png"))

        self.horizontalLayout_5.addWidget(self.label_13)

        self.comboBox_edition = QComboBox(self.groupBox_4)
        self.comboBox_edition.setObjectName(u"comboBox_edition")
        self.comboBox_edition.setEditable(True)

        self.horizontalLayout_5.addWidget(self.comboBox_edition)

        self.label_14 = QLabel(self.groupBox_4)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setPixmap(QPixmap(u":/icons/resources/golden_notes.png"))

        self.horizontalLayout_5.addWidget(self.label_14)

        self.comboBox_goldennotes = QComboBox(self.groupBox_4)
        self.comboBox_goldennotes.addItem("")
        self.comboBox_goldennotes.addItem("")
        self.comboBox_goldennotes.addItem("")
        self.comboBox_goldennotes.setObjectName(u"comboBox_goldennotes")

        self.horizontalLayout_5.addWidget(self.comboBox_goldennotes)

        self.label_15 = QLabel(self.groupBox_4)
        self.label_15.setObjectName(u"label_15")
        self.label_15.setPixmap(QPixmap(u":/icons/resources/rating.png"))

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
        self.comboBox_rating.setObjectName(u"comboBox_rating")

        self.horizontalLayout_5.addWidget(self.comboBox_rating)

        self.label_16 = QLabel(self.groupBox_4)
        self.label_16.setObjectName(u"label_16")
        self.label_16.setPixmap(QPixmap(u":/icons/resources/views.png"))

        self.horizontalLayout_5.addWidget(self.label_16)

        self.comboBox_views = QComboBox(self.groupBox_4)
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.setObjectName(u"comboBox_views")

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
        self.tableView_availableSongs.setObjectName(u"tableView_availableSongs")
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
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.groupBox_songfile = QGroupBox(self.centralwidget)
        self.groupBox_songfile.setObjectName(u"groupBox_songfile")
        self.groupBox_songfile.setCheckable(True)
        self.formLayout = QFormLayout(self.groupBox_songfile)
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setVerticalSpacing(2)
        self.formLayout.setContentsMargins(4, 4, 4, 4)
        self.label = QLabel(self.groupBox_songfile)
        self.label.setObjectName(u"label")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label)

        self.comboBox_encoding = QComboBox(self.groupBox_songfile)
        self.comboBox_encoding.addItem("")
        self.comboBox_encoding.addItem("")
        self.comboBox_encoding.addItem("")
        self.comboBox_encoding.setObjectName(u"comboBox_encoding")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.comboBox_encoding)

        self.label_8 = QLabel(self.groupBox_songfile)
        self.label_8.setObjectName(u"label_8")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_8)

        self.comboBox_line_endings = QComboBox(self.groupBox_songfile)
        self.comboBox_line_endings.addItem("")
        self.comboBox_line_endings.addItem("")
        self.comboBox_line_endings.setObjectName(u"comboBox_line_endings")

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.comboBox_line_endings)


        self.horizontalLayout_7.addWidget(self.groupBox_songfile)

        self.groupBox_audio = QGroupBox(self.centralwidget)
        self.groupBox_audio.setObjectName(u"groupBox_audio")
        self.groupBox_audio.setCheckable(True)
        self.formLayout_2 = QFormLayout(self.groupBox_audio)
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.formLayout_2.setVerticalSpacing(2)
        self.formLayout_2.setContentsMargins(4, 4, 4, 4)
        self.label_7 = QLabel(self.groupBox_audio)
        self.label_7.setObjectName(u"label_7")

        self.formLayout_2.setWidget(0, QFormLayout.LabelRole, self.label_7)

        self.comboBox_audio_format = QComboBox(self.groupBox_audio)
        self.comboBox_audio_format.addItem("")
        self.comboBox_audio_format.addItem("")
        self.comboBox_audio_format.addItem("")
        self.comboBox_audio_format.setObjectName(u"comboBox_audio_format")

        self.formLayout_2.setWidget(0, QFormLayout.FieldRole, self.comboBox_audio_format)


        self.horizontalLayout_7.addWidget(self.groupBox_audio)

        self.groupBox_reencode_audio = QGroupBox(self.centralwidget)
        self.groupBox_reencode_audio.setObjectName(u"groupBox_reencode_audio")
        self.groupBox_reencode_audio.setCheckable(True)
        self.groupBox_reencode_audio.setChecked(False)
        self.formLayout_6 = QFormLayout(self.groupBox_reencode_audio)
        self.formLayout_6.setObjectName(u"formLayout_6")
        self.formLayout_6.setContentsMargins(4, 4, 4, 4)
        self.label_19 = QLabel(self.groupBox_reencode_audio)
        self.label_19.setObjectName(u"label_19")

        self.formLayout_6.setWidget(0, QFormLayout.LabelRole, self.label_19)

        self.comboBox_audio_conversion_format = QComboBox(self.groupBox_reencode_audio)
        self.comboBox_audio_conversion_format.addItem("")
        self.comboBox_audio_conversion_format.addItem("")
        self.comboBox_audio_conversion_format.addItem("")
        self.comboBox_audio_conversion_format.setObjectName(u"comboBox_audio_conversion_format")

        self.formLayout_6.setWidget(0, QFormLayout.FieldRole, self.comboBox_audio_conversion_format)


        self.horizontalLayout_7.addWidget(self.groupBox_reencode_audio)

        self.groupBox_video = QGroupBox(self.centralwidget)
        self.groupBox_video.setObjectName(u"groupBox_video")
        self.groupBox_video.setCheckable(True)
        self.formLayout_3 = QFormLayout(self.groupBox_video)
        self.formLayout_3.setObjectName(u"formLayout_3")
        self.formLayout_3.setVerticalSpacing(2)
        self.formLayout_3.setContentsMargins(4, 4, 4, 4)
        self.label_4 = QLabel(self.groupBox_video)
        self.label_4.setObjectName(u"label_4")

        self.formLayout_3.setWidget(0, QFormLayout.LabelRole, self.label_4)

        self.comboBox_videocontainer = QComboBox(self.groupBox_video)
        self.comboBox_videocontainer.addItem("")
        self.comboBox_videocontainer.addItem("")
        self.comboBox_videocontainer.addItem("")
        self.comboBox_videocontainer.setObjectName(u"comboBox_videocontainer")

        self.formLayout_3.setWidget(0, QFormLayout.FieldRole, self.comboBox_videocontainer)

        self.label_5 = QLabel(self.groupBox_video)
        self.label_5.setObjectName(u"label_5")

        self.formLayout_3.setWidget(1, QFormLayout.LabelRole, self.label_5)

        self.comboBox_videoresolution = QComboBox(self.groupBox_video)
        self.comboBox_videoresolution.addItem("")
        self.comboBox_videoresolution.addItem("")
        self.comboBox_videoresolution.setObjectName(u"comboBox_videoresolution")

        self.formLayout_3.setWidget(1, QFormLayout.FieldRole, self.comboBox_videoresolution)

        self.label_3 = QLabel(self.groupBox_video)
        self.label_3.setObjectName(u"label_3")

        self.formLayout_3.setWidget(2, QFormLayout.LabelRole, self.label_3)

        self.comboBox_fps = QComboBox(self.groupBox_video)
        self.comboBox_fps.addItem("")
        self.comboBox_fps.addItem("")
        self.comboBox_fps.setObjectName(u"comboBox_fps")

        self.formLayout_3.setWidget(2, QFormLayout.FieldRole, self.comboBox_fps)


        self.horizontalLayout_7.addWidget(self.groupBox_video)

        self.groupBox_reencode_video = QGroupBox(self.centralwidget)
        self.groupBox_reencode_video.setObjectName(u"groupBox_reencode_video")
        self.groupBox_reencode_video.setCheckable(True)
        self.groupBox_reencode_video.setChecked(False)
        self.label_18 = QLabel(self.groupBox_reencode_video)
        self.label_18.setObjectName(u"label_18")
        self.label_18.setGeometry(QRect(15, 25, 80, 16))
        self.comboBox_videoencoder = QComboBox(self.groupBox_reencode_video)
        self.comboBox_videoencoder.addItem("")
        self.comboBox_videoencoder.addItem("")
        self.comboBox_videoencoder.addItem("")
        self.comboBox_videoencoder.addItem("")
        self.comboBox_videoencoder.setObjectName(u"comboBox_videoencoder")
        self.comboBox_videoencoder.setGeometry(QRect(100, 23, 118, 32))

        self.horizontalLayout_7.addWidget(self.groupBox_reencode_video)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox_cover = QGroupBox(self.centralwidget)
        self.groupBox_cover.setObjectName(u"groupBox_cover")
        self.groupBox_cover.setCheckable(True)
        self.formLayout_4 = QFormLayout(self.groupBox_cover)
        self.formLayout_4.setObjectName(u"formLayout_4")
        self.formLayout_4.setVerticalSpacing(2)
        self.formLayout_4.setContentsMargins(4, 4, 4, 4)

        self.verticalLayout.addWidget(self.groupBox_cover)

        self.groupBox_background = QGroupBox(self.centralwidget)
        self.groupBox_background.setObjectName(u"groupBox_background")
        self.groupBox_background.setCheckable(True)
        self.formLayout_5 = QFormLayout(self.groupBox_background)
        self.formLayout_5.setObjectName(u"formLayout_5")
        self.formLayout_5.setVerticalSpacing(2)
        self.formLayout_5.setContentsMargins(4, 4, 4, 4)
        self.label_6 = QLabel(self.groupBox_background)
        self.label_6.setObjectName(u"label_6")

        self.formLayout_5.setWidget(0, QFormLayout.LabelRole, self.label_6)

        self.comboBox_background = QComboBox(self.groupBox_background)
        self.comboBox_background.addItem("")
        self.comboBox_background.addItem("")
        self.comboBox_background.setObjectName(u"comboBox_background")

        self.formLayout_5.setWidget(0, QFormLayout.FieldRole, self.comboBox_background)


        self.verticalLayout.addWidget(self.groupBox_background)


        self.horizontalLayout_7.addLayout(self.verticalLayout)


        self.verticalLayout_2.addLayout(self.horizontalLayout_7)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_2 = QSpacerItem(559, 46, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.pushButton_downloadSelectedSongs = QPushButton(self.centralwidget)
        self.pushButton_downloadSelectedSongs.setObjectName(u"pushButton_downloadSelectedSongs")
        self.pushButton_downloadSelectedSongs.setEnabled(True)
        self.pushButton_downloadSelectedSongs.setFont(font)

        self.horizontalLayout.addWidget(self.pushButton_downloadSelectedSongs)


        self.verticalLayout_2.addLayout(self.horizontalLayout)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1493, 24))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"USDB Syncer", None))
        self.groupBox.setTitle(QCoreApplication.translate("MainWindow", u"UltraStar Song Database (usdb)", None))
        self.pushButton_get_songlist.setText(QCoreApplication.translate("MainWindow", u"Refresh song list", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("MainWindow", u"Synchronize to local song directory", None))
        self.lineEdit_song_dir.setText(QCoreApplication.translate("MainWindow", u"./songs", None))
        self.pushButton_select_song_dir.setText(QCoreApplication.translate("MainWindow", u"Select song folder", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("MainWindow", u"Search (RexExp)", None))
        self.comboBox_search_column.setItemText(0, QCoreApplication.translate("MainWindow", u"any", None))
        self.comboBox_search_column.setItemText(1, QCoreApplication.translate("MainWindow", u"Artist", None))
        self.comboBox_search_column.setItemText(2, QCoreApplication.translate("MainWindow", u"Title", None))
        self.comboBox_search_column.setItemText(3, QCoreApplication.translate("MainWindow", u"Language", None))
        self.comboBox_search_column.setItemText(4, QCoreApplication.translate("MainWindow", u"Edition", None))

        self.checkBox_case_sensitive.setText(QCoreApplication.translate("MainWindow", u"Case sensitive", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("MainWindow", u"Filter", None))
        self.label_10.setText("")
        self.label_11.setText("")
        self.label_12.setText("")
        self.label_13.setText("")
        self.label_14.setText("")
        self.comboBox_goldennotes.setItemText(0, QCoreApplication.translate("MainWindow", u"any", None))
        self.comboBox_goldennotes.setItemText(1, QCoreApplication.translate("MainWindow", u"yes", None))
        self.comboBox_goldennotes.setItemText(2, QCoreApplication.translate("MainWindow", u"no", None))

        self.label_15.setText("")
        self.comboBox_rating.setItemText(0, QCoreApplication.translate("MainWindow", u"any", None))
        self.comboBox_rating.setItemText(1, QCoreApplication.translate("MainWindow", u"\u2605", None))
        self.comboBox_rating.setItemText(2, QCoreApplication.translate("MainWindow", u"\u2605\u2605", None))
        self.comboBox_rating.setItemText(3, QCoreApplication.translate("MainWindow", u"\u2605\u2605\u2605", None))
        self.comboBox_rating.setItemText(4, QCoreApplication.translate("MainWindow", u"\u2605\u2605\u2605\u2605", None))
        self.comboBox_rating.setItemText(5, QCoreApplication.translate("MainWindow", u"\u2605\u2605\u2605\u2605\u2605", None))
        self.comboBox_rating.setItemText(6, QCoreApplication.translate("MainWindow", u"\u2605 or more", None))
        self.comboBox_rating.setItemText(7, QCoreApplication.translate("MainWindow", u"\u2605\u2605 or more", None))
        self.comboBox_rating.setItemText(8, QCoreApplication.translate("MainWindow", u"\u2605\u2605\u2605 or more", None))
        self.comboBox_rating.setItemText(9, QCoreApplication.translate("MainWindow", u"\u2605\u2605\u2605\u2605 or more", None))

        self.label_16.setText("")
        self.comboBox_views.setItemText(0, QCoreApplication.translate("MainWindow", u"any", None))
        self.comboBox_views.setItemText(1, QCoreApplication.translate("MainWindow", u"100+", None))
        self.comboBox_views.setItemText(2, QCoreApplication.translate("MainWindow", u"200+", None))
        self.comboBox_views.setItemText(3, QCoreApplication.translate("MainWindow", u"300+", None))
        self.comboBox_views.setItemText(4, QCoreApplication.translate("MainWindow", u"400+", None))
        self.comboBox_views.setItemText(5, QCoreApplication.translate("MainWindow", u"500+", None))

        self.groupBox_songfile.setTitle(QCoreApplication.translate("MainWindow", u"Download song file", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Encoding", None))
        self.comboBox_encoding.setItemText(0, QCoreApplication.translate("MainWindow", u"UTF-8", None))
        self.comboBox_encoding.setItemText(1, QCoreApplication.translate("MainWindow", u"UTF-8 BOM", None))
        self.comboBox_encoding.setItemText(2, QCoreApplication.translate("MainWindow", u"CP1252", None))

        self.label_8.setText(QCoreApplication.translate("MainWindow", u"Line Endings", None))
        self.comboBox_line_endings.setItemText(0, QCoreApplication.translate("MainWindow", u"Windows (CRLF)", None))
        self.comboBox_line_endings.setItemText(1, QCoreApplication.translate("MainWindow", u"Mac/Linux (LF)", None))

        self.groupBox_audio.setTitle(QCoreApplication.translate("MainWindow", u"Download audio", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"Audio Format", None))
        self.comboBox_audio_format.setItemText(0, QCoreApplication.translate("MainWindow", u".m4a (mp4a)", None))
        self.comboBox_audio_format.setItemText(1, QCoreApplication.translate("MainWindow", u".webm (opus)", u"mp3"))
        self.comboBox_audio_format.setItemText(2, QCoreApplication.translate("MainWindow", u"bestaudio", None))

        self.groupBox_reencode_audio.setTitle(QCoreApplication.translate("MainWindow", u"Reencode audio", None))
        self.label_19.setText(QCoreApplication.translate("MainWindow", u"Audio Format", None))
        self.comboBox_audio_conversion_format.setItemText(0, QCoreApplication.translate("MainWindow", u".mp3 (MPEG)", None))
        self.comboBox_audio_conversion_format.setItemText(1, QCoreApplication.translate("MainWindow", u".ogg (Vorbis)", None))
        self.comboBox_audio_conversion_format.setItemText(2, QCoreApplication.translate("MainWindow", u".opus (Opus)", None))

        self.groupBox_video.setTitle(QCoreApplication.translate("MainWindow", u"Download video", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Video container", None))
        self.comboBox_videocontainer.setItemText(0, QCoreApplication.translate("MainWindow", u".mp4", None))
        self.comboBox_videocontainer.setItemText(1, QCoreApplication.translate("MainWindow", u".webm", None))
        self.comboBox_videocontainer.setItemText(2, QCoreApplication.translate("MainWindow", u"bestvideo", None))

        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Max. resolution", None))
        self.comboBox_videoresolution.setItemText(0, QCoreApplication.translate("MainWindow", u"1080p", None))
        self.comboBox_videoresolution.setItemText(1, QCoreApplication.translate("MainWindow", u"720p", None))

        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Max. fps", None))
        self.comboBox_fps.setItemText(0, QCoreApplication.translate("MainWindow", u"30", None))
        self.comboBox_fps.setItemText(1, QCoreApplication.translate("MainWindow", u"60", None))

        self.groupBox_reencode_video.setTitle(QCoreApplication.translate("MainWindow", u"Reencode video", None))
        self.label_18.setText(QCoreApplication.translate("MainWindow", u"Video Format", None))
        self.comboBox_videoencoder.setItemText(0, QCoreApplication.translate("MainWindow", u"h264", None))
        self.comboBox_videoencoder.setItemText(1, QCoreApplication.translate("MainWindow", u"h265", None))
        self.comboBox_videoencoder.setItemText(2, QCoreApplication.translate("MainWindow", u"libvpx-vp9", None))
        self.comboBox_videoencoder.setItemText(3, QCoreApplication.translate("MainWindow", u"libaom-av1", None))

        self.groupBox_cover.setTitle(QCoreApplication.translate("MainWindow", u"Download cover \u2013 settings:", None))
        self.groupBox_background.setTitle(QCoreApplication.translate("MainWindow", u"Download background \u2013 settings:", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Download", None))
        self.comboBox_background.setItemText(0, QCoreApplication.translate("MainWindow", u"always", None))
        self.comboBox_background.setItemText(1, QCoreApplication.translate("MainWindow", u"only if no video", None))

        self.pushButton_downloadSelectedSongs.setText(QCoreApplication.translate("MainWindow", u"Download selected songs!", None))
    # retranslateUi

