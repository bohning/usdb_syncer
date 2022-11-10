# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MetaTagsDialog.ui'
##
## Created by: Qt User Interface Compiler version 6.3.2
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QDoubleSpinBox, QFormLayout, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSizePolicy, QSpacerItem,
    QSpinBox, QVBoxLayout, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(852, 777)
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Dialog.sizePolicy().hasHeightForWidth())
        Dialog.setSizePolicy(sizePolicy)
        Dialog.setMinimumSize(QSize(0, 0))
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.scrollArea = QScrollArea(Dialog)
        self.scrollArea.setObjectName(u"scrollArea")
        self.scrollArea.setFrameShape(QFrame.NoFrame)
        self.scrollArea.setFrameShadow(QFrame.Plain)
        self.scrollArea.setLineWidth(0)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea.setWidgetResizable(False)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName(u"scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, -153, 817, 912))
        self.verticalLayout_3 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.groupBox = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox.setObjectName(u"groupBox")
        self.formLayout_2 = QFormLayout(self.groupBox)
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.label = QLabel(self.groupBox)
        self.label.setObjectName(u"label")

        self.formLayout_2.setWidget(0, QFormLayout.LabelRole, self.label)

        self.groupBox_2 = QGroupBox(self.groupBox)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.horizontalLayout = QHBoxLayout(self.groupBox_2)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label_2 = QLabel(self.groupBox_2)
        self.label_2.setObjectName(u"label_2")
        sizePolicy1 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.label_2)

        self.video_crop_left = QSpinBox(self.groupBox_2)
        self.video_crop_left.setObjectName(u"video_crop_left")
        self.video_crop_left.setMaximum(9999)

        self.horizontalLayout.addWidget(self.video_crop_left)

        self.label_3 = QLabel(self.groupBox_2)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout.addWidget(self.label_3)

        self.video_crop_right = QSpinBox(self.groupBox_2)
        self.video_crop_right.setObjectName(u"video_crop_right")
        self.video_crop_right.setMaximum(9999)

        self.horizontalLayout.addWidget(self.video_crop_right)

        self.label_4 = QLabel(self.groupBox_2)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout.addWidget(self.label_4)

        self.video_crop_top = QSpinBox(self.groupBox_2)
        self.video_crop_top.setObjectName(u"video_crop_top")
        self.video_crop_top.setMaximum(999)

        self.horizontalLayout.addWidget(self.video_crop_top)

        self.label_5 = QLabel(self.groupBox_2)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout.addWidget(self.label_5)

        self.video_crop_bottom = QSpinBox(self.groupBox_2)
        self.video_crop_bottom.setObjectName(u"video_crop_bottom")
        self.video_crop_bottom.setMaximum(9999)

        self.horizontalLayout.addWidget(self.video_crop_bottom)

        self.horizontalSpacer = QSpacerItem(391, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.formLayout_2.setWidget(2, QFormLayout.SpanningRole, self.groupBox_2)

        self.video_url = QLineEdit(self.groupBox)
        self.video_url.setObjectName(u"video_url")

        self.formLayout_2.setWidget(0, QFormLayout.FieldRole, self.video_url)

        self.groupBox_3 = QGroupBox(self.groupBox)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox_3)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.groupBox_8 = QGroupBox(self.groupBox_3)
        self.groupBox_8.setObjectName(u"groupBox_8")
        self.horizontalLayout_8 = QHBoxLayout(self.groupBox_8)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.label_19 = QLabel(self.groupBox_8)
        self.label_19.setObjectName(u"label_19")

        self.horizontalLayout_8.addWidget(self.label_19)

        self.video_trim_start_mins = QSpinBox(self.groupBox_8)
        self.video_trim_start_mins.setObjectName(u"video_trim_start_mins")
        self.video_trim_start_mins.setMaximum(999)

        self.horizontalLayout_8.addWidget(self.video_trim_start_mins)

        self.label_20 = QLabel(self.groupBox_8)
        self.label_20.setObjectName(u"label_20")

        self.horizontalLayout_8.addWidget(self.label_20)

        self.video_trim_start_secs = QDoubleSpinBox(self.groupBox_8)
        self.video_trim_start_secs.setObjectName(u"video_trim_start_secs")
        self.video_trim_start_secs.setMaximum(59.990000000000002)

        self.horizontalLayout_8.addWidget(self.video_trim_start_secs)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_6)

        self.video_trim_use_start_frames = QCheckBox(self.groupBox_8)
        self.video_trim_use_start_frames.setObjectName(u"video_trim_use_start_frames")

        self.horizontalLayout_8.addWidget(self.video_trim_use_start_frames)

        self.video_trim_start_frames = QSpinBox(self.groupBox_8)
        self.video_trim_start_frames.setObjectName(u"video_trim_start_frames")
        self.video_trim_start_frames.setEnabled(False)

        self.horizontalLayout_8.addWidget(self.video_trim_start_frames)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_2)


        self.verticalLayout_2.addWidget(self.groupBox_8)

        self.groupBox_7 = QGroupBox(self.groupBox_3)
        self.groupBox_7.setObjectName(u"groupBox_7")
        self.horizontalLayout_7 = QHBoxLayout(self.groupBox_7)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.label_6 = QLabel(self.groupBox_7)
        self.label_6.setObjectName(u"label_6")

        self.horizontalLayout_7.addWidget(self.label_6)

        self.video_trim_end_mins = QSpinBox(self.groupBox_7)
        self.video_trim_end_mins.setObjectName(u"video_trim_end_mins")
        self.video_trim_end_mins.setMaximum(999)

        self.horizontalLayout_7.addWidget(self.video_trim_end_mins)

        self.label_7 = QLabel(self.groupBox_7)
        self.label_7.setObjectName(u"label_7")

        self.horizontalLayout_7.addWidget(self.label_7)

        self.video_trim_end_secs = QDoubleSpinBox(self.groupBox_7)
        self.video_trim_end_secs.setObjectName(u"video_trim_end_secs")
        self.video_trim_end_secs.setMaximum(59.990000000000002)

        self.horizontalLayout_7.addWidget(self.video_trim_end_secs)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_7)

        self.video_trim_use_end_frames = QCheckBox(self.groupBox_7)
        self.video_trim_use_end_frames.setObjectName(u"video_trim_use_end_frames")

        self.horizontalLayout_7.addWidget(self.video_trim_use_end_frames)

        self.video_trim_end_frames = QSpinBox(self.groupBox_7)
        self.video_trim_end_frames.setObjectName(u"video_trim_end_frames")
        self.video_trim_end_frames.setEnabled(False)

        self.horizontalLayout_7.addWidget(self.video_trim_end_frames)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_5)


        self.verticalLayout_2.addWidget(self.groupBox_7)


        self.formLayout_2.setWidget(1, QFormLayout.SpanningRole, self.groupBox_3)


        self.verticalLayout_3.addWidget(self.groupBox)

        self.groupBox_4 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.formLayout_3 = QFormLayout(self.groupBox_4)
        self.formLayout_3.setObjectName(u"formLayout_3")
        self.label_8 = QLabel(self.groupBox_4)
        self.label_8.setObjectName(u"label_8")

        self.formLayout_3.setWidget(0, QFormLayout.LabelRole, self.label_8)

        self.audio_url = QLineEdit(self.groupBox_4)
        self.audio_url.setObjectName(u"audio_url")

        self.formLayout_3.setWidget(0, QFormLayout.FieldRole, self.audio_url)


        self.verticalLayout_3.addWidget(self.groupBox_4)

        self.groupBox_5 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.formLayout = QFormLayout(self.groupBox_5)
        self.formLayout.setObjectName(u"formLayout")
        self.label_10 = QLabel(self.groupBox_5)
        self.label_10.setObjectName(u"label_10")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label_10)

        self.label_16 = QLabel(self.groupBox_5)
        self.label_16.setObjectName(u"label_16")

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_16)

        self.cover_rotation = QDoubleSpinBox(self.groupBox_5)
        self.cover_rotation.setObjectName(u"cover_rotation")
        self.cover_rotation.setMinimum(-360.000000000000000)
        self.cover_rotation.setMaximum(360.000000000000000)

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.cover_rotation)

        self.label_17 = QLabel(self.groupBox_5)
        self.label_17.setObjectName(u"label_17")

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.label_17)

        self.label_18 = QLabel(self.groupBox_5)
        self.label_18.setObjectName(u"label_18")

        self.formLayout.setWidget(3, QFormLayout.LabelRole, self.label_18)

        self.cover_resize = QSpinBox(self.groupBox_5)
        self.cover_resize.setObjectName(u"cover_resize")
        self.cover_resize.setMinimum(0)
        self.cover_resize.setMaximum(1920)
        self.cover_resize.setValue(0)

        self.formLayout.setWidget(3, QFormLayout.FieldRole, self.cover_resize)

        self.groupBox_6 = QGroupBox(self.groupBox_5)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox_6)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_11 = QLabel(self.groupBox_6)
        self.label_11.setObjectName(u"label_11")
        sizePolicy1.setHeightForWidth(self.label_11.sizePolicy().hasHeightForWidth())
        self.label_11.setSizePolicy(sizePolicy1)

        self.horizontalLayout_2.addWidget(self.label_11)

        self.cover_crop_left = QSpinBox(self.groupBox_6)
        self.cover_crop_left.setObjectName(u"cover_crop_left")
        self.cover_crop_left.setMaximum(9999)

        self.horizontalLayout_2.addWidget(self.cover_crop_left)

        self.label_12 = QLabel(self.groupBox_6)
        self.label_12.setObjectName(u"label_12")

        self.horizontalLayout_2.addWidget(self.label_12)

        self.cover_crop_top = QSpinBox(self.groupBox_6)
        self.cover_crop_top.setObjectName(u"cover_crop_top")
        self.cover_crop_top.setMaximum(9999)

        self.horizontalLayout_2.addWidget(self.cover_crop_top)

        self.label_13 = QLabel(self.groupBox_6)
        self.label_13.setObjectName(u"label_13")

        self.horizontalLayout_2.addWidget(self.label_13)

        self.cover_crop_width = QSpinBox(self.groupBox_6)
        self.cover_crop_width.setObjectName(u"cover_crop_width")
        self.cover_crop_width.setMaximum(9999)

        self.horizontalLayout_2.addWidget(self.cover_crop_width)

        self.label_14 = QLabel(self.groupBox_6)
        self.label_14.setObjectName(u"label_14")

        self.horizontalLayout_2.addWidget(self.label_14)

        self.cover_crop_height = QSpinBox(self.groupBox_6)
        self.cover_crop_height.setObjectName(u"cover_crop_height")
        self.cover_crop_height.setMaximum(9999)

        self.horizontalLayout_2.addWidget(self.cover_crop_height)

        self.horizontalSpacer_4 = QSpacerItem(0, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_4)


        self.formLayout.setWidget(4, QFormLayout.SpanningRole, self.groupBox_6)

        self.cover_url = QLineEdit(self.groupBox_5)
        self.cover_url.setObjectName(u"cover_url")

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.cover_url)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.cover_contrast_auto = QCheckBox(self.groupBox_5)
        self.cover_contrast_auto.setObjectName(u"cover_contrast_auto")

        self.horizontalLayout_3.addWidget(self.cover_contrast_auto)

        self.cover_contrast = QDoubleSpinBox(self.groupBox_5)
        self.cover_contrast.setObjectName(u"cover_contrast")
        self.cover_contrast.setSingleStep(0.100000000000000)
        self.cover_contrast.setValue(1.000000000000000)

        self.horizontalLayout_3.addWidget(self.cover_contrast)


        self.formLayout.setLayout(2, QFormLayout.FieldRole, self.horizontalLayout_3)


        self.verticalLayout_3.addWidget(self.groupBox_5)

        self.groupBox_9 = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_9.setObjectName(u"groupBox_9")
        self.formLayout_4 = QFormLayout(self.groupBox_9)
        self.formLayout_4.setObjectName(u"formLayout_4")
        self.label_21 = QLabel(self.groupBox_9)
        self.label_21.setObjectName(u"label_21")

        self.formLayout_4.setWidget(0, QFormLayout.LabelRole, self.label_21)

        self.background_url = QLineEdit(self.groupBox_9)
        self.background_url.setObjectName(u"background_url")

        self.formLayout_4.setWidget(0, QFormLayout.FieldRole, self.background_url)

        self.groupBox_11 = QGroupBox(self.groupBox_9)
        self.groupBox_11.setObjectName(u"groupBox_11")
        self.horizontalLayout_9 = QHBoxLayout(self.groupBox_11)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.label_23 = QLabel(self.groupBox_11)
        self.label_23.setObjectName(u"label_23")

        self.horizontalLayout_9.addWidget(self.label_23)

        self.background_resize_width = QSpinBox(self.groupBox_11)
        self.background_resize_width.setObjectName(u"background_resize_width")
        self.background_resize_width.setMaximum(9999)

        self.horizontalLayout_9.addWidget(self.background_resize_width)

        self.label_22 = QLabel(self.groupBox_11)
        self.label_22.setObjectName(u"label_22")

        self.horizontalLayout_9.addWidget(self.label_22)

        self.background_resize_height = QSpinBox(self.groupBox_11)
        self.background_resize_height.setObjectName(u"background_resize_height")
        self.background_resize_height.setMaximum(9999)

        self.horizontalLayout_9.addWidget(self.background_resize_height)

        self.horizontalSpacer_9 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_9)


        self.formLayout_4.setWidget(1, QFormLayout.SpanningRole, self.groupBox_11)

        self.groupBox_10 = QGroupBox(self.groupBox_9)
        self.groupBox_10.setObjectName(u"groupBox_10")
        self.horizontalLayout_4 = QHBoxLayout(self.groupBox_10)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_25 = QLabel(self.groupBox_10)
        self.label_25.setObjectName(u"label_25")
        sizePolicy1.setHeightForWidth(self.label_25.sizePolicy().hasHeightForWidth())
        self.label_25.setSizePolicy(sizePolicy1)

        self.horizontalLayout_4.addWidget(self.label_25)

        self.background_crop_left = QSpinBox(self.groupBox_10)
        self.background_crop_left.setObjectName(u"background_crop_left")
        self.background_crop_left.setMaximum(9999)

        self.horizontalLayout_4.addWidget(self.background_crop_left)

        self.label_26 = QLabel(self.groupBox_10)
        self.label_26.setObjectName(u"label_26")

        self.horizontalLayout_4.addWidget(self.label_26)

        self.background_crop_top = QSpinBox(self.groupBox_10)
        self.background_crop_top.setObjectName(u"background_crop_top")
        self.background_crop_top.setMaximum(9999)

        self.horizontalLayout_4.addWidget(self.background_crop_top)

        self.label_27 = QLabel(self.groupBox_10)
        self.label_27.setObjectName(u"label_27")

        self.horizontalLayout_4.addWidget(self.label_27)

        self.background_crop_width = QSpinBox(self.groupBox_10)
        self.background_crop_width.setObjectName(u"background_crop_width")
        self.background_crop_width.setMaximum(9999)

        self.horizontalLayout_4.addWidget(self.background_crop_width)

        self.label_28 = QLabel(self.groupBox_10)
        self.label_28.setObjectName(u"label_28")

        self.horizontalLayout_4.addWidget(self.label_28)

        self.background_crop_height = QSpinBox(self.groupBox_10)
        self.background_crop_height.setObjectName(u"background_crop_height")
        self.background_crop_height.setMaximum(9999)

        self.horizontalLayout_4.addWidget(self.background_crop_height)

        self.horizontalSpacer_8 = QSpacerItem(385, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_8)


        self.formLayout_4.setWidget(2, QFormLayout.SpanningRole, self.groupBox_10)


        self.verticalLayout_3.addWidget(self.groupBox_9)

        self.duet = QGroupBox(self.scrollAreaWidgetContents)
        self.duet.setObjectName(u"duet")
        sizePolicy1.setHeightForWidth(self.duet.sizePolicy().hasHeightForWidth())
        self.duet.setSizePolicy(sizePolicy1)
        self.duet.setCheckable(True)
        self.duet.setChecked(False)
        self.horizontalLayout_6 = QHBoxLayout(self.duet)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.label_15 = QLabel(self.duet)
        self.label_15.setObjectName(u"label_15")
        sizePolicy1.setHeightForWidth(self.label_15.sizePolicy().hasHeightForWidth())
        self.label_15.setSizePolicy(sizePolicy1)
        self.label_15.setMaximumSize(QSize(16777215, 26))

        self.horizontalLayout_6.addWidget(self.label_15)

        self.duet_p1 = QLineEdit(self.duet)
        self.duet_p1.setObjectName(u"duet_p1")

        self.horizontalLayout_6.addWidget(self.duet_p1)

        self.label_9 = QLabel(self.duet)
        self.label_9.setObjectName(u"label_9")
        sizePolicy1.setHeightForWidth(self.label_9.sizePolicy().hasHeightForWidth())
        self.label_9.setSizePolicy(sizePolicy1)
        self.label_9.setMaximumSize(QSize(16777215, 26))

        self.horizontalLayout_6.addWidget(self.label_9)

        self.duet_p2 = QLineEdit(self.duet)
        self.duet_p2.setObjectName(u"duet_p2")

        self.horizontalLayout_6.addWidget(self.duet_p2)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer_3)


        self.verticalLayout_3.addWidget(self.duet)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.output = QLineEdit(self.scrollAreaWidgetContents)
        self.output.setObjectName(u"output")
        self.output.setReadOnly(True)

        self.horizontalLayout_5.addWidget(self.output)

        self.button_copy_to_clipboard = QPushButton(self.scrollAreaWidgetContents)
        self.button_copy_to_clipboard.setObjectName(u"button_copy_to_clipboard")

        self.horizontalLayout_5.addWidget(self.button_copy_to_clipboard)


        self.verticalLayout_3.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.char_count = QLabel(self.scrollAreaWidgetContents)
        self.char_count.setObjectName(u"char_count")

        self.horizontalLayout_10.addWidget(self.char_count)


        self.verticalLayout_3.addLayout(self.horizontalLayout_10)

        self.buttonBox = QDialogButtonBox(self.scrollAreaWidgetContents)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok)

        self.verticalLayout_3.addWidget(self.buttonBox)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout.addWidget(self.scrollArea)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Meta Tags", None))
        self.groupBox.setTitle(QCoreApplication.translate("Dialog", u"Video", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"URL:", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("Dialog", u"Cropping", None))
        self.label_2.setText(QCoreApplication.translate("Dialog", u"Left:", None))
        self.video_crop_left.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.label_3.setText(QCoreApplication.translate("Dialog", u"Right:", None))
        self.video_crop_right.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.label_4.setText(QCoreApplication.translate("Dialog", u"Top:", None))
        self.video_crop_top.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.label_5.setText(QCoreApplication.translate("Dialog", u"Bottom:", None))
        self.video_crop_bottom.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("Dialog", u"Trimming", None))
        self.groupBox_8.setTitle(QCoreApplication.translate("Dialog", u"Start", None))
        self.label_19.setText(QCoreApplication.translate("Dialog", u"Minutes:", None))
        self.label_20.setText(QCoreApplication.translate("Dialog", u"Seconds:", None))
        self.video_trim_use_start_frames.setText(QCoreApplication.translate("Dialog", u"Use Frames", None))
        self.groupBox_7.setTitle(QCoreApplication.translate("Dialog", u"End", None))
        self.label_6.setText(QCoreApplication.translate("Dialog", u"Minutes:", None))
        self.label_7.setText(QCoreApplication.translate("Dialog", u"Seconds:", None))
        self.video_trim_use_end_frames.setText(QCoreApplication.translate("Dialog", u"Use Frames", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("Dialog", u"Audio", None))
        self.label_8.setText(QCoreApplication.translate("Dialog", u"URL:", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("Dialog", u"Cover", None))
        self.label_10.setText(QCoreApplication.translate("Dialog", u"URL:", None))
        self.label_16.setText(QCoreApplication.translate("Dialog", u"Rotation:", None))
        self.cover_rotation.setSuffix(QCoreApplication.translate("Dialog", u"\u00b0", None))
        self.label_17.setText(QCoreApplication.translate("Dialog", u"Contrast:", None))
        self.label_18.setText(QCoreApplication.translate("Dialog", u"Resize:", None))
        self.cover_resize.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.groupBox_6.setTitle(QCoreApplication.translate("Dialog", u"Cropping", None))
        self.label_11.setText(QCoreApplication.translate("Dialog", u"Left:", None))
        self.cover_crop_left.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.label_12.setText(QCoreApplication.translate("Dialog", u"Top:", None))
        self.cover_crop_top.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.label_13.setText(QCoreApplication.translate("Dialog", u"Width:", None))
        self.cover_crop_width.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.label_14.setText(QCoreApplication.translate("Dialog", u"Height:", None))
        self.cover_crop_height.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.cover_contrast_auto.setText(QCoreApplication.translate("Dialog", u"Auto", None))
        self.groupBox_9.setTitle(QCoreApplication.translate("Dialog", u"Background", None))
        self.label_21.setText(QCoreApplication.translate("Dialog", u"URL:", None))
        self.groupBox_11.setTitle(QCoreApplication.translate("Dialog", u"Resize", None))
        self.label_23.setText(QCoreApplication.translate("Dialog", u"Width:", None))
        self.background_resize_width.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.label_22.setText(QCoreApplication.translate("Dialog", u"Height:", None))
        self.background_resize_height.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.groupBox_10.setTitle(QCoreApplication.translate("Dialog", u"Cropping", None))
        self.label_25.setText(QCoreApplication.translate("Dialog", u"Left:", None))
        self.background_crop_left.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.label_26.setText(QCoreApplication.translate("Dialog", u"Top:", None))
        self.background_crop_top.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.label_27.setText(QCoreApplication.translate("Dialog", u"Width:", None))
        self.background_crop_width.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.label_28.setText(QCoreApplication.translate("Dialog", u"Height:", None))
        self.background_crop_height.setSuffix(QCoreApplication.translate("Dialog", u" px", None))
        self.duet.setTitle(QCoreApplication.translate("Dialog", u"Duet", None))
        self.label_15.setText(QCoreApplication.translate("Dialog", u"Player 1:", None))
        self.duet_p1.setText(QCoreApplication.translate("Dialog", u"P1", None))
        self.label_9.setText(QCoreApplication.translate("Dialog", u"Player 2:", None))
        self.duet_p2.setText(QCoreApplication.translate("Dialog", u"P2", None))
        self.output.setText(QCoreApplication.translate("Dialog", u"#VIDEO:", None))
        self.button_copy_to_clipboard.setText(QCoreApplication.translate("Dialog", u"Copy to Clipboard", None))
        self.char_count.setText(QCoreApplication.translate("Dialog", u"7 / 170 characters", None))
    # retranslateUi

