"""Dialog to create a report."""

import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QListWidgetItem,
    QMessageBox,
    QWidget,
)

from usdb_syncer import SongId, db, settings, utils
from usdb_syncer.gui import gui_utils
from usdb_syncer.gui.forms.ReportDialog import Ui_Dialog
from usdb_syncer.gui.pdf import generate_report_pdf
from usdb_syncer.gui.progress import run_with_progress
from usdb_syncer.gui.song_table.column import Column
from usdb_syncer.gui.song_table.song_table import SongTable
from usdb_syncer.json_export import generate_report_json
from usdb_syncer.logger import logger

optional_columns = [
    Column.LANGUAGE,
    Column.EDITION,
    Column.GENRE,
    Column.YEAR,
    Column.CREATOR,
    Column.SONG_ID,
]

if TYPE_CHECKING:
    from collections.abc import Iterable


class ReportDialog(Ui_Dialog, QDialog):
    """Dialog to create a report."""

    def __init__(self, parent: QWidget, song_table: SongTable) -> None:
        super().__init__(parent=parent)
        gui_utils.cleanup_on_close(self)
        self.song_table = song_table
        self.setupUi(self)
        self._populate_comboboxes()
        self._populate_optional_columns()
        self._load_settings()

    def _populate_optional_columns(self) -> None:
        theme = settings.get_theme()
        for column in optional_columns:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, column)
            if icon := column.decoration_data(theme):
                item.setIcon(icon)
            if name := column.display_data():
                item.setText(name)
            item.setCheckState(Qt.CheckState.Unchecked)
            if column in [Column.ARTIST, Column.TITLE]:
                item.setCheckState(Qt.CheckState.Checked)
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
            )
            self.optional_columns.addItem(item)
        self.optional_columns.setDragEnabled(True)
        self.optional_columns.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )

    def _populate_comboboxes(self) -> None:
        combobox_settings = (
            (self.comboBox_pdf_pagesize, settings.ReportPDFPagesize),
            (self.comboBox_pdf_orientation, settings.ReportPDFOrientation),
        )
        for combobox, setting in combobox_settings:
            for item in setting:
                combobox.addItem(str(item), item)

    def _load_settings(self) -> None:
        self.comboBox_pdf_pagesize.setCurrentIndex(
            self.comboBox_pdf_pagesize.findData(settings.get_report_pdf_pagesize())
        )
        self.comboBox_pdf_orientation.setCurrentIndex(
            self.comboBox_pdf_orientation.findData(
                settings.get_report_pdf_orientation()
            )
        )
        self.spinBox_pdf_margin.setValue(settings.get_report_pdf_margin())
        self.spinBox_pdf_columns.setValue(settings.get_report_pdf_columns())
        self.spinBox_pdf_font_size.setValue(settings.get_report_pdf_fontsize())
        self.spinBox_json_indent.setValue(settings.get_report_json_indent())

    def accept(self) -> None:
        self._save_settings()
        if (
            self.tabWidget_report_type.currentIndex() == 0
            and self._generate_report_pdf()
        ) or (
            self.tabWidget_report_type.currentIndex() == 1
            and self._generate_report_json()
        ):
            super().accept()

    def reject(self) -> None:
        self._save_settings()
        super().reject()

    def _save_settings(self) -> None:
        settings.set_report_pdf_pagesize(self.comboBox_pdf_pagesize.currentData())
        settings.set_report_pdf_orientation(self.comboBox_pdf_orientation.currentData())
        settings.set_report_pdf_margin(self.spinBox_pdf_margin.value())
        settings.set_report_pdf_columns(self.spinBox_pdf_columns.value())
        settings.set_report_pdf_fontsize(self.spinBox_pdf_font_size.value())
        settings.set_report_json_indent(self.spinBox_json_indent.value())

    def _generate_report_pdf(self) -> bool:
        def on_done(path: str) -> None:
            logger.info(f"PDF report created at {path}.")
            utils.open_path_or_file(Path(path))

        songs: Iterable[SongId] = []
        if self.radioButton_locally_available_songs.isChecked():
            songs = db.all_local_usdb_songs()
        if self.radioButton_selected_songs.isChecked():
            songs = []
            for song in self.song_table.selected_songs():
                songs.append(song.song_id)
        elif self.radioButton_all_songs.isChecked():
            songs = db.all_song_ids()
        if not songs:
            msg = "Skipping PDF report creation: no songs match the selection."
            QMessageBox.information(self, "Empty song list", msg)
            logger.info(msg)
            return False
        fname = f"{datetime.datetime.now():%Y-%m-%d}_songlist.pdf"
        path = str(Path(settings.get_song_dir()) / fname)
        path = QFileDialog.getSaveFileName(self, dir=path, filter="PDF (*.pdf)")[0]
        if path:
            pagesize = self.comboBox_pdf_pagesize.currentData()
            orientation = self.comboBox_pdf_orientation.currentData()
            margin = self.spinBox_pdf_margin.value()
            column_count = self.spinBox_pdf_columns.value()
            base_font_size = self.spinBox_pdf_font_size.value()
            optional_info = []
            for index in range(self.optional_columns.count()):
                item: QListWidgetItem = self.optional_columns.item(index)
                if item.checkState() == Qt.CheckState.Checked:
                    optional_info.append(item.data(Qt.ItemDataRole.UserRole))
            run_with_progress(
                lambda progress: generate_report_pdf(
                    songs=songs,
                    path=path,
                    size=pagesize,
                    orientation=orientation,
                    margin=margin,
                    column_count=column_count,
                    base_font_size=base_font_size,
                    optional_info=optional_info,
                    progress=progress,
                ),
                on_done=on_done,
            )
            return True
        # dialog is hidden by main window on macOS if file picker was cancelled
        self.raise_()
        return False

    def _generate_report_json(self) -> bool:
        def on_done(result: tuple[Path, int]) -> None:
            path, num_of_songs = result
            logger.info(f"JSON report created at {path} ({num_of_songs} songs).")

        songs: Iterable[SongId] = []
        if self.radioButton_locally_available_songs.isChecked():
            songs = db.all_local_usdb_songs()
        if self.radioButton_selected_songs.isChecked():
            songs = []
            for song in self.song_table.selected_songs():
                songs.append(song.song_id)
        elif self.radioButton_all_songs.isChecked():
            songs = db.all_song_ids()
        songs = db.all_local_usdb_songs()
        if not songs:
            msg = "Skipping JSON report creation: no songs match the selection."
            QMessageBox.information(self, "Empty song list", msg)
            logger.info(msg)
            return False
        fname = f"{datetime.datetime.now():%Y-%m-%d}_songlist.json"
        path = str(Path(settings.get_song_dir()) / fname)
        path = QFileDialog.getSaveFileName(self, dir=path, filter="JSON (*.json)")[0]
        indent = self.spinBox_json_indent.value()
        if path:
            run_with_progress(
                lambda progress: generate_report_json(
                    songs=songs, path=Path(path), indent=indent, progress=progress
                ),
                on_done=on_done,
            )
            return True
        # dialog is hidden by main window on macOS if file picker was cancelled
        self.raise_()
        return False
