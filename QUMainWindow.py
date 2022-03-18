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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMenuBar, QPushButton,
    QSizePolicy, QSpacerItem, QStatusBar, QTreeView,
    QVBoxLayout, QWidget)
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1426, 670)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.groupBox = QGroupBox(self.centralwidget)
        self.groupBox.setObjectName(u"groupBox")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_username = QLabel(self.groupBox)
        self.label_username.setObjectName(u"label_username")

        self.horizontalLayout_2.addWidget(self.label_username)

        self.lineEdit_user = QLineEdit(self.groupBox)
        self.lineEdit_user.setObjectName(u"lineEdit_user")

        self.horizontalLayout_2.addWidget(self.lineEdit_user)

        self.label_password = QLabel(self.groupBox)
        self.label_password.setObjectName(u"label_password")

        self.horizontalLayout_2.addWidget(self.label_password)

        self.lineEdit_password = QLineEdit(self.groupBox)
        self.lineEdit_password.setObjectName(u"lineEdit_password")
        self.lineEdit_password.setEchoMode(QLineEdit.Password)

        self.horizontalLayout_2.addWidget(self.lineEdit_password)

        self.pushButton_login = QPushButton(self.groupBox)
        self.pushButton_login.setObjectName(u"pushButton_login")
        font = QFont()
        font.setPointSize(16)
        self.pushButton_login.setFont(font)
        self.pushButton_login.setStyleSheet(u"background-color: rgb(0, 102, 0);")
        icon = QIcon()
        icon.addFile(u":/icons/resources/faviconUSDB.ico", QSize(), QIcon.Normal, QIcon.Off)
        self.pushButton_login.setIcon(icon)

        self.horizontalLayout_2.addWidget(self.pushButton_login)

        self.pushButton_refresh = QPushButton(self.groupBox)
        self.pushButton_refresh.setObjectName(u"pushButton_refresh")
        self.pushButton_refresh.setFont(font)
        self.pushButton_refresh.setStyleSheet(u"background-color: rgb(0, 102, 0);")
        self.pushButton_refresh.setIcon(icon)

        self.horizontalLayout_2.addWidget(self.pushButton_refresh)


        self.horizontalLayout_3.addWidget(self.groupBox)

        self.horizontalSpacer = QSpacerItem(358, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer)

        self.groupBox_2 = QGroupBox(self.centralwidget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.horizontalLayout_4 = QHBoxLayout(self.groupBox_2)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.lineEdit_song_dir = QLineEdit(self.groupBox_2)
        self.lineEdit_song_dir.setObjectName(u"lineEdit_song_dir")

        self.horizontalLayout_4.addWidget(self.lineEdit_song_dir)

        self.pushButton_select_song_dir = QPushButton(self.groupBox_2)
        self.pushButton_select_song_dir.setObjectName(u"pushButton_select_song_dir")
        self.pushButton_select_song_dir.setEnabled(True)
        self.pushButton_select_song_dir.setFont(font)
        self.pushButton_select_song_dir.setStyleSheet(u"background-color: rgb(0, 102, 0);")

        self.horizontalLayout_4.addWidget(self.pushButton_select_song_dir)


        self.horizontalLayout_3.addWidget(self.groupBox_2)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.comboBox_artist = QComboBox(self.centralwidget)
        self.comboBox_artist.setObjectName(u"comboBox_artist")
        self.comboBox_artist.setEditable(True)

        self.horizontalLayout_6.addWidget(self.comboBox_artist)

        self.comboBox_title = QComboBox(self.centralwidget)
        self.comboBox_title.setObjectName(u"comboBox_title")
        self.comboBox_title.setEditable(True)

        self.horizontalLayout_6.addWidget(self.comboBox_title)

        self.comboBox_language = QComboBox(self.centralwidget)
        self.comboBox_language.setObjectName(u"comboBox_language")
        self.comboBox_language.setEditable(True)

        self.horizontalLayout_6.addWidget(self.comboBox_language)

        self.comboBox_edition = QComboBox(self.centralwidget)
        self.comboBox_edition.setObjectName(u"comboBox_edition")
        self.comboBox_edition.setEditable(True)

        self.horizontalLayout_6.addWidget(self.comboBox_edition)

        self.comboBox_goldennotes = QComboBox(self.centralwidget)
        self.comboBox_goldennotes.addItem("")
        self.comboBox_goldennotes.addItem("")
        self.comboBox_goldennotes.addItem("")
        self.comboBox_goldennotes.setObjectName(u"comboBox_goldennotes")

        self.horizontalLayout_6.addWidget(self.comboBox_goldennotes)

        self.comboBox_rating = QComboBox(self.centralwidget)
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

        self.horizontalLayout_6.addWidget(self.comboBox_rating)

        self.comboBox_views = QComboBox(self.centralwidget)
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.addItem("")
        self.comboBox_views.setObjectName(u"comboBox_views")

        self.horizontalLayout_6.addWidget(self.comboBox_views)


        self.verticalLayout.addLayout(self.horizontalLayout_6)

        self.treeView_availableSongs = QTreeView(self.centralwidget)
        self.treeView_availableSongs.setObjectName(u"treeView_availableSongs")
        self.treeView_availableSongs.setAlternatingRowColors(True)
        self.treeView_availableSongs.setRootIsDecorated(False)
        self.treeView_availableSongs.setSortingEnabled(True)
        self.treeView_availableSongs.header().setHighlightSections(False)

        self.verticalLayout.addWidget(self.treeView_availableSongs)

        self.horizontalLayout_13 = QHBoxLayout()
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.groupBox_songfile = QGroupBox(self.centralwidget)
        self.groupBox_songfile.setObjectName(u"groupBox_songfile")
        self.groupBox_songfile.setCheckable(True)
        self.formLayout = QFormLayout(self.groupBox_songfile)
        self.formLayout.setObjectName(u"formLayout")
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


        self.horizontalLayout_13.addWidget(self.groupBox_songfile)

        self.groupBox_audio = QGroupBox(self.centralwidget)
        self.groupBox_audio.setObjectName(u"groupBox_audio")
        self.groupBox_audio.setCheckable(True)
        self.formLayout_2 = QFormLayout(self.groupBox_audio)
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.label_7 = QLabel(self.groupBox_audio)
        self.label_7.setObjectName(u"label_7")

        self.formLayout_2.setWidget(0, QFormLayout.LabelRole, self.label_7)

        self.comboBox_audio_format = QComboBox(self.groupBox_audio)
        self.comboBox_audio_format.addItem("")
        self.comboBox_audio_format.addItem("")
        self.comboBox_audio_format.addItem("")
        self.comboBox_audio_format.setObjectName(u"comboBox_audio_format")

        self.formLayout_2.setWidget(0, QFormLayout.FieldRole, self.comboBox_audio_format)

        self.checkBox_audio_convert = QCheckBox(self.groupBox_audio)
        self.checkBox_audio_convert.setObjectName(u"checkBox_audio_convert")

        self.formLayout_2.setWidget(1, QFormLayout.LabelRole, self.checkBox_audio_convert)

        self.comboBox_audio_conversion_format = QComboBox(self.groupBox_audio)
        self.comboBox_audio_conversion_format.addItem("")
        self.comboBox_audio_conversion_format.addItem("")
        self.comboBox_audio_conversion_format.addItem("")
        self.comboBox_audio_conversion_format.setObjectName(u"comboBox_audio_conversion_format")

        self.formLayout_2.setWidget(1, QFormLayout.FieldRole, self.comboBox_audio_conversion_format)


        self.horizontalLayout_13.addWidget(self.groupBox_audio)

        self.groupBox_video = QGroupBox(self.centralwidget)
        self.groupBox_video.setObjectName(u"groupBox_video")
        self.groupBox_video.setCheckable(True)
        self.formLayout_3 = QFormLayout(self.groupBox_video)
        self.formLayout_3.setObjectName(u"formLayout_3")
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

        self.comboBox_videoencoder = QComboBox(self.groupBox_video)
        self.comboBox_videoencoder.addItem("")
        self.comboBox_videoencoder.addItem("")
        self.comboBox_videoencoder.addItem("")
        self.comboBox_videoencoder.addItem("")
        self.comboBox_videoencoder.setObjectName(u"comboBox_videoencoder")

        self.formLayout_3.setWidget(3, QFormLayout.FieldRole, self.comboBox_videoencoder)

        self.checkBox_videoallowreencode = QCheckBox(self.groupBox_video)
        self.checkBox_videoallowreencode.setObjectName(u"checkBox_videoallowreencode")
        self.checkBox_videoallowreencode.setChecked(False)

        self.formLayout_3.setWidget(3, QFormLayout.LabelRole, self.checkBox_videoallowreencode)


        self.horizontalLayout_13.addWidget(self.groupBox_video)

        self.groupBox_cover = QGroupBox(self.centralwidget)
        self.groupBox_cover.setObjectName(u"groupBox_cover")
        self.groupBox_cover.setCheckable(True)
        self.formLayout_4 = QFormLayout(self.groupBox_cover)
        self.formLayout_4.setObjectName(u"formLayout_4")
        self.label_2 = QLabel(self.groupBox_cover)
        self.label_2.setObjectName(u"label_2")

        self.formLayout_4.setWidget(0, QFormLayout.LabelRole, self.label_2)

        self.comboBox_coverresolution = QComboBox(self.groupBox_cover)
        self.comboBox_coverresolution.addItem("")
        self.comboBox_coverresolution.addItem("")
        self.comboBox_coverresolution.addItem("")
        self.comboBox_coverresolution.addItem("")
        self.comboBox_coverresolution.addItem("")
        self.comboBox_coverresolution.setObjectName(u"comboBox_coverresolution")

        self.formLayout_4.setWidget(0, QFormLayout.FieldRole, self.comboBox_coverresolution)


        self.horizontalLayout_13.addWidget(self.groupBox_cover)

        self.groupBox_background = QGroupBox(self.centralwidget)
        self.groupBox_background.setObjectName(u"groupBox_background")
        self.groupBox_background.setCheckable(True)
        self.formLayout_5 = QFormLayout(self.groupBox_background)
        self.formLayout_5.setObjectName(u"formLayout_5")
        self.label_6 = QLabel(self.groupBox_background)
        self.label_6.setObjectName(u"label_6")

        self.formLayout_5.setWidget(0, QFormLayout.LabelRole, self.label_6)

        self.comboBox_background = QComboBox(self.groupBox_background)
        self.comboBox_background.addItem("")
        self.comboBox_background.addItem("")
        self.comboBox_background.setObjectName(u"comboBox_background")

        self.formLayout_5.setWidget(0, QFormLayout.FieldRole, self.comboBox_background)


        self.horizontalLayout_13.addWidget(self.groupBox_background)


        self.verticalLayout.addLayout(self.horizontalLayout_13)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_2 = QSpacerItem(1088, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)

        self.pushButton_downloadSelectedSongs = QPushButton(self.centralwidget)
        self.pushButton_downloadSelectedSongs.setObjectName(u"pushButton_downloadSelectedSongs")
        self.pushButton_downloadSelectedSongs.setEnabled(True)
        self.pushButton_downloadSelectedSongs.setFont(font)
        self.pushButton_downloadSelectedSongs.setStyleSheet(u"background-color: rgb(0, 102, 0);")

        self.horizontalLayout.addWidget(self.pushButton_downloadSelectedSongs)


        self.verticalLayout.addLayout(self.horizontalLayout)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1426, 24))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"USDB Song Manager", None))
        self.groupBox.setTitle(QCoreApplication.translate("MainWindow", u"USDB connection", None))
        self.label_username.setText(QCoreApplication.translate("MainWindow", u"User", None))
        self.label_password.setText(QCoreApplication.translate("MainWindow", u"Password", None))
        self.pushButton_login.setText(QCoreApplication.translate("MainWindow", u" Login", None))
        self.pushButton_refresh.setText(QCoreApplication.translate("MainWindow", u" Refresh", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("MainWindow", u"Local song directory to synchronize", None))
        self.lineEdit_song_dir.setText(QCoreApplication.translate("MainWindow", u"./usdb_songs", None))
        self.pushButton_select_song_dir.setText(QCoreApplication.translate("MainWindow", u"Select song folder", None))
        self.comboBox_goldennotes.setItemText(0, QCoreApplication.translate("MainWindow", u"any", None))
        self.comboBox_goldennotes.setItemText(1, QCoreApplication.translate("MainWindow", u"yes", None))
        self.comboBox_goldennotes.setItemText(2, QCoreApplication.translate("MainWindow", u"no", None))

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

        self.comboBox_views.setItemText(0, QCoreApplication.translate("MainWindow", u"any", None))
        self.comboBox_views.setItemText(1, QCoreApplication.translate("MainWindow", u"100+", None))
        self.comboBox_views.setItemText(2, QCoreApplication.translate("MainWindow", u"200+", None))
        self.comboBox_views.setItemText(3, QCoreApplication.translate("MainWindow", u"300+", None))
        self.comboBox_views.setItemText(4, QCoreApplication.translate("MainWindow", u"400+", None))
        self.comboBox_views.setItemText(5, QCoreApplication.translate("MainWindow", u"500+", None))

        self.groupBox_songfile.setTitle(QCoreApplication.translate("MainWindow", u"Download song file \u2013 settings:", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"File Encoding", None))
        self.comboBox_encoding.setItemText(0, QCoreApplication.translate("MainWindow", u"UTF-8", None))
        self.comboBox_encoding.setItemText(1, QCoreApplication.translate("MainWindow", u"UTF-8 BOM", None))
        self.comboBox_encoding.setItemText(2, QCoreApplication.translate("MainWindow", u"CP1252", None))

        self.label_8.setText(QCoreApplication.translate("MainWindow", u"Line Endings", None))
        self.comboBox_line_endings.setItemText(0, QCoreApplication.translate("MainWindow", u"Windows (CRLF)", None))
        self.comboBox_line_endings.setItemText(1, QCoreApplication.translate("MainWindow", u"Mac/Linux (LF)", None))

        self.groupBox_audio.setTitle(QCoreApplication.translate("MainWindow", u"Download audio \u2013 settings:", None))
        self.label_7.setText(QCoreApplication.translate("MainWindow", u"Audio Format", None))
        self.comboBox_audio_format.setItemText(0, QCoreApplication.translate("MainWindow", u".m4a (mp4a)", None))
        self.comboBox_audio_format.setItemText(1, QCoreApplication.translate("MainWindow", u".webm (opus)", u"mp3"))
        self.comboBox_audio_format.setItemText(2, QCoreApplication.translate("MainWindow", u"bestaudio", None))

        self.checkBox_audio_convert.setText(QCoreApplication.translate("MainWindow", u"convert to", None))
        self.comboBox_audio_conversion_format.setItemText(0, QCoreApplication.translate("MainWindow", u".mp3 (MPEG Audio Layer 3)", None))
        self.comboBox_audio_conversion_format.setItemText(1, QCoreApplication.translate("MainWindow", u".ogg (Vorbis)", None))
        self.comboBox_audio_conversion_format.setItemText(2, QCoreApplication.translate("MainWindow", u".opus (Opus)", None))

        self.groupBox_video.setTitle(QCoreApplication.translate("MainWindow", u"Download video \u2013 settings:", None))
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

        self.comboBox_videoencoder.setItemText(0, QCoreApplication.translate("MainWindow", u"h264", None))
        self.comboBox_videoencoder.setItemText(1, QCoreApplication.translate("MainWindow", u"h265", None))
        self.comboBox_videoencoder.setItemText(2, QCoreApplication.translate("MainWindow", u"libvpx-vp9", None))
        self.comboBox_videoencoder.setItemText(3, QCoreApplication.translate("MainWindow", u"libaom-av1", None))

        self.checkBox_videoallowreencode.setText(QCoreApplication.translate("MainWindow", u"reencode to", None))
        self.groupBox_cover.setTitle(QCoreApplication.translate("MainWindow", u"Download cover \u2013 settings:", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Max. resolution", None))
        self.comboBox_coverresolution.setItemText(0, QCoreApplication.translate("MainWindow", u"1920x1920", None))
        self.comboBox_coverresolution.setItemText(1, QCoreApplication.translate("MainWindow", u"1500x1500", None))
        self.comboBox_coverresolution.setItemText(2, QCoreApplication.translate("MainWindow", u"1000x1000", None))
        self.comboBox_coverresolution.setItemText(3, QCoreApplication.translate("MainWindow", u"800x800", None))
        self.comboBox_coverresolution.setItemText(4, QCoreApplication.translate("MainWindow", u"600x600", None))

        self.groupBox_background.setTitle(QCoreApplication.translate("MainWindow", u"Download background \u2013 settings:", None))
        self.label_6.setText(QCoreApplication.translate("MainWindow", u"Download bg", None))
        self.comboBox_background.setItemText(0, QCoreApplication.translate("MainWindow", u"always", None))
        self.comboBox_background.setItemText(1, QCoreApplication.translate("MainWindow", u"only if no video", None))

        self.pushButton_downloadSelectedSongs.setText(QCoreApplication.translate("MainWindow", u"Download selected songs!", None))
    # retranslateUi

