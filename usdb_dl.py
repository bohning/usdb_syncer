import argparse
import datetime
import logging
import os
import re
import sys
import time

from stringprep import map_table_b3
from PySide6.QtCore import Qt, QEvent, QSortFilterProxyModel, QThread, Signal, QRunnable, QThreadPool
from PySide6.QtGui import QPixmap, QStandardItemModel, QStandardItem, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QHeaderView, QMenu, QSplashScreen
#from pytube import extract

from pdfme import build_pdf # maybe reportlab is better suited?
from typing import Dict, List, Tuple
import filecmp
import usdb_scraper
import note_utils
import resource_dl

from QUMainWindow import Ui_MainWindow


class QPlainTextEditLogger(logging.Handler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.text_edit.setReadOnly(True)
 
    def emit(self, record):
        msg = self.format(record)
        self.text_edit.appendPlainText(msg)


class Worker(QRunnable):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs
 
 
    def run(self):
        # Your long-running task goes here ...
        
        logging.info(f"Downloading song #{self.kwargs['id']}")
        logging.info(f"\t- downloading usdb file #{self.kwargs['id']}")
        ###
        exists, details = usdb_scraper.get_usdb_details(self.kwargs['id'])
        if not exists:
            # song was deleted meanwhile, TODO: uncheck/remove from model
            return
        
        songtext = usdb_scraper.get_notes(self.kwargs['id'])
        
        #song = createsong(songtext)
        header, notes = note_utils.parse_notes(songtext)
        
        #self.statusbar.showMessage(f"Downloading '{header['#ARTIST']} - {header['#TITLE']}' ({num+1}/{len(ids)})") # TODO: this is not updated until after download all songs

        header["#TITLE"] = re.sub("[\[].*?[\]]", "", header["#TITLE"]).strip() # remove anything in "[]" from the title, e.g. "[duet]"
        resource_params = note_utils.get_params_from_video_tag(header)
        
        duet = note_utils.is_duet(header, resource_params)
        if duet:
            if p1 := resource_params.get("p1"):
                header["#P1"] = p1
            else:
                header["#P1"] = "P1"
            if p2 := resource_params.get("p2"):
                header["#P2"] = p2
            else:
                header["#P2"] = "P2"
            
            notes.insert(0, "P1\n")
            prev_start = 0
            for i, line in enumerate(notes):
                if line.startswith((":", "*", "F", "R", "G")):
                    type, start, duration, pitch, *syllable = line.split(" ", maxsplit = 4)
                    if int(start) < prev_start:
                        notes.insert(i, "P2\n")
                    prev_start = int(start)
        
        logging.info(f"\t- Song: {header['#ARTIST']} - {header['#TITLE']}")
        
        dirname = note_utils.generate_dirname(header, resource_params)
        pathname = os.path.join(os.path.join(self.kwargs['songdir'], dirname), self.kwargs['idp'])
        
        if not os.path.exists(pathname):
            os.makedirs(pathname)
        
        # write .usdb file for synchronization
        with open(os.path.join(pathname, "temp.usdb"), 'w', encoding="utf_8") as f:
            f.write(songtext)
        if os.path.exists(os.path.join(pathname, f"{self.kwargs['idp']}.usdb")):
            if filecmp.cmp(os.path.join(pathname, "temp.usdb"), os.path.join(pathname, f"{self.kwargs['idp']}.usdb")):
                logging.info("\t FILES ARE IDENTICAL - SKIPPING SONG")
                os.remove(os.path.join(pathname, "temp.usdb"))
                return
            else:
                logging.info("\t USDB file has been updated, re-downloading...")
                # TODO: check if resources in #VIDEO tag have changed and if so, re-download new resources only
                os.remove(os.path.join(pathname, f"{self.kwargs['idp']}.usdb"))
                os.rename(os.path.join(pathname, "temp.usdb"), os.path.join(pathname, f"{self.kwargs['idp']}.usdb"))
        else:
            os.rename(os.path.join(pathname, "temp.usdb"), os.path.join(pathname, f"{self.kwargs['idp']}.usdb"))
        ###
        logging.info(f"\t- downloading audio file for #{self.kwargs['id']}")
        ###
        has_audio = False
        if self.kwargs['dl_audio']:
            if audio_resource := resource_params.get("a"):
                pass
            elif audio_resource := resource_params.get("v"):
                pass
            else:
                video_params = details.get("video_params")
                if video_params:
                    audio_resource = video_params.get("v")
                    if audio_resource:
                        logging.warning(f"Using Youtube ID {audio_resource} extracted from comments.")
            
            if audio_resource:
                #if "bestaudio" in self.comboBox_audio_format.currentText():
                #    audio_dl_format = "bestaudio"
                #elif "m4a" in self.comboBox_audio_format.currentText():
                audio_dl_format = "m4a"
                #elif "webm" in self.comboBox_audio_format.currentText():
                #    audio_dl_format = "webm"
                    
                audio_target_format = ""
                audio_target_codec = ""
                """ if self.groupBox_reencode_audio.isChecked():
                    if "mp3" in self.comboBox_audio_conversion_format.currentText():
                        audio_target_format = "mp3"
                        audio_target_codec = "mp3"
                    elif "ogg" in self.comboBox_audio_conversion_format.currentText():
                        audio_target_format = "ogg"
                        audio_target_codec = "vorbis"
                    elif "opus" in self.comboBox_audio_conversion_format.currentText():
                        audio_target_format = "opus"
                        audio_target_codec = "opus" """
                    
                has_audio, ext = resource_dl.download_and_process_audio(header, audio_resource, audio_dl_format, audio_target_codec, self.kwargs['dl_browser'], pathname)
                
                header["#MP3"] = f"{note_utils.generate_filename(header)}.{ext}" 
                
                # delete #VIDEO tag used for resources
                if header.get("#VIDEO"):
                    header.pop("#VIDEO")
                    
                #if has_audio:
                    #self.model.setItem(self.model.findItems(self.kwargs['id'], flags=Qt.MatchExactly, column=0)[0].row(), 9, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
        ###
        logging.info(f"\t- downloading video file for #{self.kwargs['id']}")
        ###
        has_video = False
        if self.kwargs['dl_video']:
            if video_resource := resource_params.get("v"):
                pass
            elif not resource_params.get("a"):
                video_params = details.get("video_params")
                if video_params:
                    video_resource = video_params.get("v")
                    if video_resource:
                        logging.warning(f"Using Youtube ID {audio_resource} extracted from comments.")
            
            if video_resource:
                """video_params = {
                        "container": self.comboBox_videocontainer.currentText(),
                        "resolution": self.comboBox_videoresolution.currentText(),
                        "fps": self.comboBox_fps.currentText(),
                        "allow_reencode": self.groupBox_reencode_video.isChecked(),
                        "encoder": self.comboBox_videoencoder.currentText()
                    }"""
                video_params = {
                        "container": ".mp4",
                        "resolution": "1080p",
                        "fps": "30",
                        "allow_reencode": False,
                        "encoder": "h264"
                    }
                has_video = resource_dl.download_and_process_video(header, video_resource, video_params, resource_params, self.kwargs['dl_browser'], pathname)
                
                header["#VIDEO"] = f"{note_utils.generate_filename(header)}{video_params['container']}" 
                #if has_video:
                #    self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 10, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
            else:
                logging.warning("\t- no video resource in #VIDEO tag")
        ###
        logging.info(f"\t- downloading cover file for #{self.kwargs['id']}")
        ###
        has_cover = False
        if self.kwargs['dl_cover']:
            has_cover = resource_dl.download_and_process_cover(header, resource_params, details, pathname)
            header["#COVER"] = f"{note_utils.generate_filename(header)} [CO].jpg"
            #if has_cover:
            #    self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 11, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
        ###
        logging.info(f"\t- downloading background file for #{self.kwargs['id']}")
        ###
        has_background = False
        if self.kwargs['dl_background']:
            #if self.comboBox_background.currentText() == "always" or (not has_video and self.comboBox_background.currentText() == "only if no video"):
            has_background = resource_dl.download_and_process_background(header, resource_params, pathname)
            header["#BACKGROUND"] = f"{note_utils.generate_filename(header)} [BG].jpg"
                
                #if has_background:
                #    self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 12, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
        ###
        logging.info(f"\t- downloading text file for #{self.kwargs['id']}")
        ###
        bom = False
        #if self.comboBox_encoding.currentText() == "UTF-8":
        encoding = "utf_8"
        #elif self.comboBox_encoding.currentText() == "UTF-8 BOM":
        #    encoding = "utf_8_sig"
        #elif self.comboBox_encoding.currentText() == "CP1252":
        #    encoding = "cp1252"
        #newline = self.comboBox_line_endings.currentText()
        #if newline == "Windows (CRLF)":
            #newline = '\r\n'
        #elif newline == "Mac/Linux (LF)":
        newline = '\n'
        note_utils.dump_notes(header, notes, duet, encoding, newline, pathname)
        #self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 8, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
        ###


class QUMainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        
        self.threadpool = QThreadPool(self)
        
        self.lineEdit_song_dir.setText(os.path.join(os.getcwd(), "songs"))
        
        self.handler = QPlainTextEditLogger(self.plainTextEdit)
        self.handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S'))
        
        self.pushButton_get_songlist.clicked.connect(self.refresh)
        self.pushButton_downloadSelectedSongs.clicked.connect(self.download_selected_songs)
        self.pushButton_select_song_dir.clicked.connect(self.select_song_dir)   
        
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderItem(0, QStandardItem(QIcon(":/icons/resources/id.png"), "ID"))
        self.model.setHorizontalHeaderItem(1, QStandardItem(QIcon(":/icons/resources/artist.png"), "Artist"))
        self.model.setHorizontalHeaderItem(2, QStandardItem(QIcon(":/icons/resources/title.png"), "Title"))
        self.model.setHorizontalHeaderItem(3, QStandardItem(QIcon(":/icons/resources/language.png"), "Language"))
        self.model.setHorizontalHeaderItem(4, QStandardItem(QIcon(":/icons/resources/edition.png"), "Edition"))
        self.model.setHorizontalHeaderItem(5, QStandardItem(QIcon(":/icons/resources/golden_notes.png"), ""))
        self.model.setHorizontalHeaderItem(6, QStandardItem(QIcon(":/icons/resources/rating.png"), ""))
        self.model.setHorizontalHeaderItem(7, QStandardItem(QIcon(":/icons/resources/views.png"), ""))
        self.model.setHorizontalHeaderItem(8, QStandardItem(QIcon(":/icons/resources/text.png"), ""))
        self.model.setHorizontalHeaderItem(9, QStandardItem(QIcon(":/icons/resources/audio.png"), ""))
        self.model.setHorizontalHeaderItem(10, QStandardItem(QIcon(":/icons/resources/video.png"), ""))
        self.model.setHorizontalHeaderItem(11, QStandardItem(QIcon(":/icons/resources/cover.png"), ""))
        self.model.setHorizontalHeaderItem(12, QStandardItem(QIcon(":/icons/resources/background.png"), ""))
        
        self.filter_proxy_model = QSortFilterProxyModel()
        self.filter_proxy_model.setSourceModel(self.model)
        self.filter_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.filter_proxy_model.setFilterKeyColumn(-1)
        
        self.lineEdit_search.textChanged.connect(self.set_filter_regular_expression)
        self.tableView_availableSongs.setModel(self.filter_proxy_model)
        self.tableView_availableSongs.installEventFilter(self)
        
        self.comboBox_search_column.currentIndexChanged.connect(self.set_filter_key_column)
        self.checkBox_case_sensitive.stateChanged.connect(self.set_case_sensitivity)


    def set_filter_regular_expression(self, regexp):
        self.filter_proxy_model.setFilterRegularExpression(regexp)
        self.statusbar.showMessage(f"{self.filter_proxy_model.rowCount()} songs found.")
    
        
    def set_filter_key_column(self, index):
        if index == 0:
            self.filter_proxy_model.setFilterKeyColumn(-1)
        else:
            self.filter_proxy_model.setFilterKeyColumn(index)
        self.statusbar.showMessage(f"{self.filter_proxy_model.rowCount()} songs found.")

            
    def set_case_sensitivity(self, state):
        if state == 0:
            self.filter_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        else:
            self.filter_proxy_model.setFilterCaseSensitivity(Qt.CaseSensitive)
        self.statusbar.showMessage(f"{self.filter_proxy_model.rowCount()} songs found.")
    

    def refresh(self):
        #TODO: remove all existing items in the model!
        available_songs = usdb_scraper.get_usdb_available_songs()
        artists = set()
        titles = []
        languages = set()
        editions = set()
        self.model.removeRows(0, self.model.rowCount())
        
        root = self.model.invisibleRootItem()
        for song in available_songs:
            if song["language"]:
                lang = song["language"]
            else:
                lang = "language_not_set"
            
            rating = int(song["rating"])
            rating_string = rating * "★" #+ (5-rating) * "☆"
            
            id_zero_padded = song["id"].zfill(5)

            id_item = QStandardItem()
            id_item.setData(id_zero_padded, Qt.DisplayRole)
            id_item.setCheckable(True)
            artist_item = QStandardItem()
            artist_item.setData(song['artist'], Qt.DisplayRole)
            title_item = QStandardItem()
            title_item.setData(song['title'], Qt.DisplayRole)
            language_item = QStandardItem()
            language_item.setData(song['language'], Qt.DisplayRole)
            edition_item = QStandardItem()
            edition_item.setData(song['edition'], Qt.DisplayRole)
            goldennotes_item = QStandardItem()
            goldennotes_item.setData("Yes" if song["goldennotes"] else "No", Qt.DisplayRole)
            rating_item = QStandardItem()
            rating_item.setData(rating_string, Qt.DisplayRole)
            views_item = QStandardItem()
            views_item.setData(int(song["views"]), Qt.DisplayRole)
            row = [
                id_item,
                artist_item,
                title_item,
                language_item,
                edition_item,
                goldennotes_item,
                rating_item,
                views_item
            ]
            root.appendRow(row)
            
            artists.add(song['artist'])
            titles.append(song['title'])
            languages.add(song['language'])
            editions.add(song['edition'])
            
        self.statusbar.showMessage(f"{self.filter_proxy_model.rowCount()} songs found.")
        
        self.comboBox_artist.addItems(list(sorted(set(artists))))
        self.comboBox_title.addItems(list(sorted(set(titles))))
        self.comboBox_language.addItems(list(sorted(set(languages))))
        self.comboBox_edition.addItems(list(sorted(set(editions))))
        
        header = self.tableView_availableSongs.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0,QHeaderView.Fixed)
        header.resizeSection(0,84)
        header.setSectionResizeMode(1,QHeaderView.Interactive)
        header.setSectionResizeMode(2,QHeaderView.Interactive)
        header.setSectionResizeMode(3,QHeaderView.Interactive)
        header.setSectionResizeMode(4,QHeaderView.Interactive)
        header.setSectionResizeMode(5,QHeaderView.Fixed)
        header.resizeSection(5,header.sectionSize(5))
        header.setSectionResizeMode(6,QHeaderView.Fixed)
        header.resizeSection(6,header.sectionSize(6))
        header.setSectionResizeMode(7,QHeaderView.Fixed)
        header.resizeSection(7,header.sectionSize(7))
        header.setSectionResizeMode(8,QHeaderView.Fixed)
        header.resizeSection(8,24)
        header.setSectionResizeMode(9,QHeaderView.Fixed)
        header.resizeSection(9,24)
        header.setSectionResizeMode(10,QHeaderView.Fixed)
        header.resizeSection(10,24)
        header.setSectionResizeMode(11,QHeaderView.Fixed)
        header.resizeSection(11,24)
        header.setSectionResizeMode(12,QHeaderView.Fixed)
        header.resizeSection(12,24)
        
        return len(available_songs)
        
        
    def select_song_dir(self):
        song_dir = str(QFileDialog.getExistingDirectory(self, "Select Song Directory"))
        self.lineEdit_song_dir.setText(song_dir)
        for path, dirs, files in os.walk(song_dir):
            dirs.sort()
            idp = ""
            item = ""
            for file in files:
                if file.endswith(".usdb"):
                    idp = file.replace(".usdb", "")
                    items = self.model.findItems(idp, flags=Qt.MatchExactly, column=0)
                    if items:
                        item = items[0]
                        item.setCheckState(Qt.CheckState.Checked)
            
                        if idp:
                            for file in files:
                                if file.endswith(".txt"):
                                    self.model.setItem(item.row(), 8, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
                                    
                                if file.endswith(".mp3") or file.endswith(".ogg") or file.endswith("m4a") or file.endswith("opus") or file.endswith("ogg"):
                                    self.model.setItem(item.row(), 9, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
                                
                                if file.endswith(".mp4") or file.endswith(".webm"):
                                    self.model.setItem(item.row(), 10, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
                                    
                                if file.endswith("[CO].jpg"):
                                    self.model.setItem(item.row(), 11, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
                                    
                                if file.endswith("[BG].jpg"):
                                    self.model.setItem(item.row(), 12, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
        
                
    def download_selected_songs(self):
        ids = []
        for row in range(self.model.rowCount(self.tableView_availableSongs.rootIndex())):
            item = self.model.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                ids.append(int(item.data(0)))
            else:
                pass
                #self.treeView_availableSongs.setRowHidden(row, QModelIndex(), True)
        self.download_songs(ids)
        self.generate_songlist_pdf()
        
        
    def generate_songlist_pdf(self):
        ### generate song list PDF
        document = {}
        document['style'] = {
            'margin_bottom': 15,
            'text_align': 'j'
        }
        document['formats'] = {
            'url': {'c': 'blue', 'u': 1},
            'title': {'b': 1, 's': 13}
        }
        document['sections'] = []
        section1 = {}
        document['sections'].append(section1)
        section1['content'] = content1 = []
        date = datetime.datetime.now()
        content1.append({
            '.': f'Songlist ({date:%Y-%m-%d})', 'style': 'title', 'label': 'title1',
            'outline': {'level': 1, 'text': 'A different title 1'}
        })

        for row in range(self.model.rowCount(self.tableView_availableSongs.rootIndex())):
            item = self.model.item(row, 0)
            if item.checkState() == Qt.CheckState.Checked:
                id = str(int(item.text()))
                artist = self.model.item(row, 1).text()
                title = self.model.item(row, 2).text()
                language = self.model.item(row, 3).text()
                edition = self.model.item(row, 4).text()
                content1.append([f"{id}\t\t{artist}\t\t{title}\t\t{language}".replace("’", "'")])
        
        with open(f'{date:%Y-%m-%d}_songlist.pdf', 'wb') as f:
            build_pdf(document, f)
        ####
    
    def download_songs(self, ids):
        dl_browser = self.comboBox_browser.currentText().lower()
        dl_video = self.groupBox_video.isChecked()
        dl_audio = self.groupBox_audio.isChecked()
        dl_cover = self.groupBox_cover.isChecked()
        dl_background = self.groupBox_background.isChecked()
        
        songdir = self.lineEdit_song_dir.text()
        
        #self.threadpool = QThreadPool.globalInstance()
        
        for num, id in enumerate(ids):
            idp = str(id).zfill(5)
            
            worker = Worker(id=id, idp=idp, ids=ids, songdir=songdir, dl_browser=dl_browser, dl_video=dl_video, dl_audio=dl_audio, dl_cover=dl_cover, dl_background=dl_background)
            self.threadpool.start(worker)
        
        # TODO: this sleep() only prevents the function from exiting, which otherwise leads to a crash (don’t know why)
        time.sleep(len(ids)*10)
        logging.info(f"DONE! (Downloaded {len(ids)} songs)")
        
        
    def eventFilter(self, source, event):
        if event.type() == QEvent.ContextMenu and source == self.tableView_availableSongs:
            menu = QMenu()
            menu.addAction("Check all selected songs")
            menu.addAction("Uncheck all selected songs")
            
            if(menu.exec(event.globalPos())):
                index = source.indexAt(event.pos())
                print(index)
            return True
        return super().eventFilter(source, event)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
        handlers=[
            logging.FileHandler("usdb_dl.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

    app = QApplication(sys.argv)
    quMainWindow = QUMainWindow()
    logger = logging.getLogger()
    logger.addHandler(quMainWindow.handler)
    pixmap = QPixmap(":/splash/resources/splash.png")
    splash = QSplashScreen(pixmap)
    splash.show()
    app.processEvents()
    splash.showMessage("Loading song database from usdb...", color=Qt.gray)
    num_songs = quMainWindow.refresh()
    splash.showMessage(f"Song database successfully loaded with {num_songs} songs.", color=Qt.gray)
    quMainWindow.show()
    logging.info("Application successfully loaded.")
    splash.finish(quMainWindow)
    app.exec()
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="UltraStar script.")

    args = parser.parse_args()

    # Call main
    main()