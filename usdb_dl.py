import argparse
import datetime
from distutils.command.config import config
import logging
import os
import re
import sys

from stringprep import map_table_b3
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QHeaderView, QMenu, QSplashScreen
from PySide6 import QtCore
#from PySide6 import QtGui
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QPixmap, QStandardItemModel, QStandardItem, QIcon
from PySide6.QtUiTools import QUiLoader
from bs4 import BeautifulSoup # needs lxml
import urllib
from pytube import extract
import requests
#import Levenshtein
import yt_dlp
#from moviepy.editor import VideoFileClip
from PIL import Image, ImageEnhance, ImageOps
import subprocess
from pdfme import build_pdf # maybe reportlab is better suited?
from typing import Dict, List, Tuple
import filecmp
import web_scraper
import note_utils

from QUMainWindow import Ui_MainWindow


""" def _get_usdb_headers():
    return {
        'Connection': 'keep-alive',
        'Content-Type': 'text/html',
        'charset': 'utf-8',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en-DE;q=0.7,en;q=0.6',
        'Cookie': f'__utmz=7495734.1596286540.251.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); __utmc=7495734; ziparchiv=; counter=0; PHPSESSID={PHPSESSID}; __utma=7495734.1923417532.1586343016.1641505471.1641515336.1172; __utmt=1; __utmb=7495734.23.10.1641515336'
    } """
    
    
def getscinfo(header):
    sc_info = {}
    
    artist = header.get("#ARTIST").replace(" feat. ", " ")
    title = header.get("#TITLE")
    title = re.sub("\[.*?\]", "", title).strip()
    url = "http://swisscharts.com/search.asp"
    # TODO: remove anything non-essential from artist/title, e.g. "(duet)" or "(video version), maybe even anything including and after "feat."
    search = f"{artist} {title}"
    if len(search) > 50:
        last_space_index = search[:50].rfind(" ")
        search = search[:last_space_index]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
    }
    
    params = {
        "cat": "s",
        "search": search
    }
    
    params = urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus, encoding="cp1252")
    
    sc = requests.get(url, headers = headers, params = params, allow_redirects=True).text
    sc_soup = BeautifulSoup(sc, 'lxml')
    sc_tbody = sc_soup.find("tbody", id="items1")
    #TODO: check for many songs if the following works reliably
    if not sc_tbody:
        logging.info(f"\t- sc::song_url: no song url found!")
        return sc_info
    else:
        song_candidates = sc_tbody.find_all("tr")
        
    if not song_candidates:
        return sc_info
    else:
        index = 0
        if len(song_candidates) > 1:
            logging.warning("\t- sc::multiple entries in the database, selection needs to be refined!")
            l_dists = []
            for i, song_candidate in enumerate(song_candidates):
                a = song_candidate.find_all("a", href=lambda x: x != '#')
                if len(a) == 2:
                    candidate_artist = song_candidate.find_all("a", href=lambda x: x != '#')[0].text
                    candidate_title = song_candidate.find_all("a", href=lambda x: x != '#')[1].text
                    artist_ldist = Levenshtein.distance(artist.lower(), candidate_artist.lower())
                    title_ldist = Levenshtein.distance(title.lower(), candidate_title.lower())
                    l_dists.append(artist_ldist+title_ldist)
                    min_l_dist = min(l_dists)
                    min_indices = [i for i, ldist in enumerate(l_dists) if ldist == min_l_dist]
                    # TODO: what if several song candidates have the minimum Levenshtein distance?
                    index = min_indices[0]
                    if len(min_indices) > 1:
                        logging.warning(f"\t- sc:: multiple database entries have a minimum Levenshtein distance of {min_l_dist}, taking the first one (this might not be correct).")
                else:
                    logging.warning("DUDE, SOMETHING IS FISHY HERE! Website in browser is different than requests.get()!")
        
        sc_song_url = "http://swisscharts.com" + song_candidates[index].find("a").get("href")
        logging.info(f"\t- sc::song_url: {sc_song_url}")
        sc_song = requests.get(sc_song_url, headers = headers).text
        sc_song_soup = BeautifulSoup(sc_song, 'lxml')
        
        # get artist and title
        heading_item = sc_song_soup.find("div", class_ = "heading item").text
        
        if heading_item:
            artist, title = heading_item.split(" – ")
            sc_info["artist"] = artist
            sc_info["title"] = title
            artist_ldist = Levenshtein.distance(artist.lower(), artist.lower())
            title_ldist = Levenshtein.distance(title.lower(), title.lower())
            sc_info["artist_ldist"] = artist_ldist
            sc_info["title_ldist"] = title_ldist
            if artist_ldist > 0: 
                logging.warning(f"\t- sc::artist: {artist} (L-distance: {artist_ldist})")
            else:
                logging.info(f"\t- sc::artist: {artist} (lowercase match!)")
            if title_ldist > 0:
                logging.warning(f"\t- sc::title: {title} (L-distance: {title_ldist})")
            else:
                logging.info(f"\t- sc::title: {title} (lowercase match!)")
        else:
            return sc_info
        
        # get cover(s)
        #TODO: sometimes there are multiple covers - which one to select?
        cover_urls = []
        coversdots = sc_song_soup.find("div", id="coversdots")
        if coversdots:
            cover_links = coversdots.find_all("a")
            for cover_link in cover_links:
                onclick = cover_link.get("onclick")
                cover_path = re.findall("showCover\(\d+,\'([^\']+)", onclick)
                cover_url = "https://media.hitparade.ch/cover/big/" + cover_path[0]
                cover_urls.append(cover_url)
        else:
            coversquare = sc_song_soup.find("div", class_ ="coversquare")
            if coversquare:
                coversquare_style = coversquare.get("style")
                cover_url = re.findall('url\(\'([^\']+)\'', coversquare_style)[0]
                if cover_url:
                    cover_urls.append(cover_url)
                else:
                    logging.info(f"\t- sc::cover_urls: coversquare exists, but url could not be extracted. Check regex!")
            else:
                logging.info(f"\t- sc::cover_urls: song page does not contain any covers.")
        
        if cover_urls:
            sc_info["cover_urls"] = cover_urls
            logging.info(f"\t- sc::cover_urls: {len(cover_urls)} ({cover_urls[0]}, ...)")
            
        # get audio sample url
        audio = sc_song_soup.find("audio")
        if audio:
            sample_url = audio.get("src")
            if sample_url:
                sc_info["sample_url"] = sample_url
                logging.info(f"\t- sc::sample_url: {sample_url}")
            else:
                logging.info(f"\t- sc::sample_url: audio exists, burl url could not be extracted.")
        else:
            logging.info(f"\t- sc::sample_url: song page does not contain any audio samples.")
        
        # get year + additional infos
        item_info = sc_song_soup.find("div", {'class': 'item_info song'})
        if not item_info:
            item_info = sc_song_soup.find("div", {'class': 'item_info_nocover'})
        
        if item_info:
            display_rows = item_info.find_all(style="display:table-row;")
            for row in display_rows:
                names = []
                th = row.find("div", class_="th").text
                td = row.find("div", class_="td").text
                if th == "Jahr":
                    sc_info["year"] = td
                    logging.info(f"\t- sc::year: {td}")
                elif th == "Musik/Text":
                    entries = row.find("div", class_="td").find_all("a")
                    for entry in entries:
                        names.append(entry.text)
                    sc_info["music_lyrics_by"] = ", ".join(names)
                elif th == "Produzent":
                    entries = row.find("div", class_="td").find_all("a")
                    for entry in entries:
                        names.append(entry.text)
                    sc_info["produced_by"] = ", ".join(names)
                elif th == "Gecovert von":
                    entries = row.find("div", class_="td").find_all("a")
                    for entry in entries:
                        names.append(entry.text)
                    sc_info["covered_by"] = ", ".join(names)
                elif th == "Durchschnittliche Bewertung":
                    sc_info["average_rating"] = row.find("span").text + "/6" + " (" + row.find("span").next_sibling.next_sibling.split()[0] + " votes)"
            
            # get video url
            video_ids = re.findall('videoId: \'(.{11})\'', sc_song)
            if video_ids:
                video_url = video_ids[0]
                sc_info["video_params"] = {"v": video_url} 
                logging.info(f"\t- sc::video_url: {video_url}")
            else:
                logging.info(f"\t- sc::video_url: song page does not contain any video urls.")
    
    return sc_info

            
def download_and_process_audio(header, audio_resource, audio_dl_format, audio_target_codec):
    if not audio_resource:
        logging.warning("\t- no audio resource in #VIDEO tag")
        return False, ""
    
    if "/" in audio_resource:
        audio_url = f"https://{audio_resource}"
    else:
        audio_url = f"https://www.youtube.com/watch?v={audio_resource}"
    logging.info(f"\t- downloading audio: {audio_url}")
    
    audio_filename = note_utils.generate_filename(header)
    
    ydl_opts = {
            "format": "bestaudio",
            "outtmpl": f"{audio_filename}" + ".%(ext)s",
            "keepvideo": False,
            "verbose": True,
            "cookiesfrombrowser": ("chrome", )
        }
    
    ext = ""
    if audio_dl_format != "bestaudio":
        ext = audio_dl_format
        if not "/" in audio_resource:
            ydl_opts["format"] = f"bestaudio[ext={ext}]" # ext only seems to work for Youtube
        else:
            ydl_opts["format"] = f"bestaudio" # not for e.g. UM
            ydl_opts["outtmpl"] = f"{audio_filename}.m4a"
    
    if audio_target_codec:
        ydl_opts["postprocessors"] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': f'{audio_target_codec}',
                'preferredquality': '320',
            }]
        
        ext = audio_target_codec
        if audio_target_codec == "vorbis":
            ext = "ogg"
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            #ydl.download([video_url])
            filename = ydl.prepare_filename(ydl.extract_info(f"{audio_url}"))
        except:
            logging.error(f"\t#VIDEO: error downloading video url: {audio_url}")
            return False, ""
    
    if audio_dl_format == "bestaudio" and not audio_target_codec:
        ext = os.path.splitext(filename)[1][1:]
        
    return True, ext


def download_and_process_video(header, video_resource, video_params, resource_params):    
    if video_params["resolution"] == "1080p":
        video_max_width = 1920
        video_max_height = 1080
    else:
        video_max_width = 1280
        video_max_height = 720
    video_max_fps = video_params["fps"]
    video_target_container = video_params["container"]
    video_reencode_allow = video_params["allow_reencode"] #True # if False, ffmpeg will not be used to trim or crop and subsequently reencode videos (uses US #START/#END tags)
    video_reencode_encoder = video_params["encoder"] # "libx264" #"libvpx-vp9" #"libaom-av1" #"libx264"
    video_reencode_crf = 23 #0–51 (0=lossless/huge file size, 23=default, 51=worst quality possible)
    video_reencode_preset = "ultrafast" #ultrafast, superfast, veryfast, faster, fast, medium (default preset), slow, slower, veryslow
    
    if "/" in video_resource:
        video_url = f"https://{video_resource}"
    else:
        video_url = f"https://www.youtube.com/watch?v={video_resource}"
    logging.info(f"\t- downloading video: {video_url}")
    
    video_filename = note_utils.generate_filename(header)
    
    ydl_opts = {
        #"format":  f"bestvideo[ext=mp4][width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]+bestaudio[ext=m4a]/best[ext=mp4][width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]/best[width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]",
        "format":  f"bestvideo[ext=mp4][width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]",
        #"format":  f"bestvideo[width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]+bestaudio",
        #"format":  f"bestvideo[width<={video_max_width}][height<={video_max_height}][fps<={video_max_fps}]",
        #"outtmpl": os.path.join(dir, f"{artist} - {title}" + ".%(ext)s"),
        "outtmpl": f"{video_filename}" + ".%(ext)s",
        "keepvideo": False,
        "verbose": True,
        "cookiesfrombrowser": ("chrome", )
    }
    
    if "/" in video_resource: # not Youtube
        ydl_opts["format"] = f"bestvideo"
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([video_url])
            vfn = ydl.prepare_filename(ydl.extract_info("{}".format(video_url)))
        except:
            logging.error(f"\t#VIDEO: error downloading video url: {video_url}")
            pass
        
    ######
    
    # Trim
    """ trim = resource_params.get("v-trim")
    start_time = None
    end_time = None
    if trim:
        start_time, end_time = trim.split("-")
        framerate = VideoFileClip(vfn).subclip(0, 10).fps
        
        if ":" in start_time:
            hours, minutes, seconds = start_time.split(":")
            start_time = int(hours)*3600 + int(minutes)*60 + float(seconds)
        elif "." in start_time:
            pass
        elif start_time == "":
            pass
        else:
            start_time = round(float(start_time) / framerate, 3)
        
        if ":" in end_time:
            hours, minutes, seconds = end_time.split(":")
            end_time = int(hours)*3600 + int(minutes)*60 + float(seconds)
        elif "." in end_time:
            pass
        elif end_time == "":
            pass
        else:
            end_time = round(float(end_time) / framerate, 3)
            
        logging.info(f"\t- video: trimming video from {start_time} to {end_time}")

    # Crop
    crop = resource_params.get("v-crop")

    if trim or crop:
        if video_reencode_allow:
            dst = vfn
            src = vfn.replace(".", "_unprocessed.")
            os.rename(dst, src)
            
            logging.info("\t\tFFMPEG postprocessing required...")    
            
            ffmpeg_trim_crop_cmd = "ffmpeg"

            if trim:
                if start_time:
                    ffmpeg_trim_crop_cmd += " -ss " + str(start_time)
                if end_time:
                    ffmpeg_trim_crop_cmd += " -to " + str(end_time)

            ffmpeg_trim_crop_cmd += " -i \"" + src + "\""

            if crop:
                left, right, top, bottom = crop.split("-")
                ffmpeg_trim_crop_cmd += f" -vf \"crop=iw-{left}-{right}:ih-{top}-{bottom}:{left}:{top}\""

            #ffmpeg_trim_crop_cmd += f" -c:v {video_reencode_encoder} -crf {video_reencode_crf} -preset {video_reencode_preset} -c:a copy \"" + dst + "\""
            ffmpeg_trim_crop_cmd += f" -c:v {video_reencode_encoder} -threads 4 -crf {video_reencode_crf} -preset {video_reencode_preset} -c:a copy \"" + dst + "\""
            logging.info(ffmpeg_trim_crop_cmd)
            logging.info("\tprocessing video file...")
            subprocess.run(ffmpeg_trim_crop_cmd, shell=True, check=True)
            logging.info("\tprocessing video file finished!")
            os.remove(src)
            # reduce #GAP by trimmed part 
            header["#GAP"] = str(int(float(header["#GAP"]) - float(start_time) * 1000))
        else:
            logging.info("\t- video: trim/crop required, but disabled.")
            if trim:
                logging.info("\t- video: trimming required, but reencode is disabled. Using appropriate #START tag to fix this.")
                if start_time:
                    header["#START"] = str(start_time) # # START is in seconds!
            if crop:
                logging.info("\t- video: cropping required, but reencode is disabled. Black bars will not be cropped.") """
    
    ######
    
    #TODO: check if download was successful, only then return True
    return True


def download_image(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"}
        reply = requests.get(url, allow_redirects=True, headers=headers)
    except:
        logging.error(f"Failed to retrieve {url}. The server may be down or your internet connection is currently unavailable.")
        return False, False
    else:
        if reply.status_code in range(100, 199):
            #1xx informational response
            return True, reply.content
        elif reply.status_code in range(200, 299):
            #2xx success
            return True, reply.content
        elif reply.status_code in range(300, 399):
            #3xx redirection
            logging.warning(f"\tRedirection to {reply._next.url}. Please update the template file.")
            return True, reply.content
        elif reply.status_code in range(400, 499):
            #4xx client errors
            logging.error(f"\tClient error {reply.status_code}. Failed to download {reply.url}")
            return False, reply.content
        elif reply.status_code in range(500, 599):
            #5xx server errors
            logging.error(f"\tServer error {reply.status_code}. Failed to download {reply.url}")
            return False, reply.content


def download_and_process_cover(header, cover_params, details):
    if not cover_params.get("co") and not details.get("cover_url"):
        logging.warning("\t- no cover resource in #VIDEO tag and no cover in usdb")
        return

    logging.info("\t- downloading cover ...")
    
    cover_extension = ".jpg"
    cover_filename = note_utils.generate_filename(header) + f" [CO]{cover_extension}"
    
    if partial_url := cover_params.get("co"):
        protocol = "https://"
        if p := cover_params.get("co-protocol"):
            if p == "http":
                protocol = "http://"
        
        if "/" in cover_params['co']:
            cover_url = f"{protocol}{partial_url}"
        else:
            cover_url = f"{protocol}images.fanart.tv/fanart/{partial_url}"
        logging.info("\t- downloading cover from #VIDEO params")
    else:
        logging.warning(f"\t- no cover resource in #VIDEO tag, so fallback to small usdb cover!")
        cover_url = details.get("cover_url")
    
    success, cover = download_image(cover_url)
    
    if success:
        open(cover_filename, "wb").write(cover)
        
        if cover_params.get("co-rotate") or cover_params.get("co-crop") or cover_params.get("co-resize") or cover_params.get("co-contrast"):
            with Image.open(cover_filename).convert("RGB") as cover:
                # rotate (optional)
                angle = cover_params.get("co-rotate")
                if angle:
                    cover = cover.rotate(float(angle), resample=Image.BICUBIC, expand=True)

                # crop (optional)
                # TODO: ensure quadratic cover
                cover_crop = cover_params.get("co-crop")
                if cover_crop:
                    cover_crop_left, cover_crop_upper, cover_width, cover_height = cover_crop.split("-")
                    cover_crop_right = int(cover_crop_left) + int(cover_width)
                    cover_crop_lower = int(cover_crop_upper) + int(cover_height)
                    cover = cover.crop((int(cover_crop_left),int(cover_crop_upper),cover_crop_right,cover_crop_lower))

                # resize (optional)
                cover_resize = cover_params.get("co-resize")
                if cover_resize:
                    width, height = cover_resize.split("-")
                    cover = cover.resize((int(width), int(height)), resample=Image.LANCZOS)
                
                # increase contrast (optional)
                cover_contrast = cover_params.get("co-contrast")
                if cover_contrast:
                    if cover_contrast == "auto":
                        cover = ImageOps.autocontrast(cover, cutoff = 5)
                    else:
                        cover = ImageEnhance.Contrast(cover).enhance(float(cover_contrast))
                
                # save post-processed cover
                cover.save(cover_filename, "jpeg", quality=100, subsampling=0)
        return True
    else:
        logging.error(f"\t#COVER: file does not exist at url: {cover_url}")
        return False


def download_and_process_background(header, background_params):
    if not background_params.get("bg"):
        logging.warning("\t- no background resource in #VIDEO-tag")
        return
    
    logging.info("\t- downloading background ...")
    background_extension = ".jpg"
    
    background_filename = note_utils.generate_filename(header) + f" [BG]{background_extension}"
    
    protocol = "https://"
    if p := background_params.get("bg-protocol"):
        if p == "http":
            protocol = "http://"
    
    if "/" in background_params['bg']:
        background_url = f"{protocol}{background_params['bg']}"
    else:
        background_url = f"{protocol}images.fanart.tv/fanart/{background_params['bg']}"
        
    logging.info("\t- downloading background from #VIDEO params")
    
    success, background = download_image(background_url)
    
    if success:
        open(background_filename, "wb").write(background)
        
        if background_params.get("bg-crop") or background_params.get("bg-resize"):
            with Image.open(background_filename).convert("RGB") as background:
                # resize (optional)
                background_resize = background_params.get("bg-resize")
                if background_resize:
                    width, height = background_resize.split("-")
                    background = background.resize((int(width), int(height)), resample=Image.LANCZOS)
                
                # crop (optional)
                background_crop = background_params.get("bg-crop")
                if background_crop:
                    background_crop_left, background_crop_upper, background_width, background_height = background_crop.split("-")
                    background_crop_right = int(background_crop_left) + int(background_width)
                    background_crop_lower = int(background_crop_upper) + int(background_height)
                    background = background.crop((int(background_crop_left),int(background_crop_upper),background_crop_right,background_crop_lower))
                
                # save post-processed background
                background.save(background_filename, "jpeg", quality=100, subsampling=0)
        return True
    else:
        logging.error(f"\t#BACKGROUND: file does not exist at url: {background_url}")
        return False


class QPlainTextEditLogger(logging.Handler):
    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.text_edit.setReadOnly(True)
 
    def emit(self, record):
        msg = self.format(record)
        self.text_edit.appendPlainText(msg)


class QUMainWindow(QMainWindow, Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        
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
        
        self.filter_proxy_model = QtCore.QSortFilterProxyModel()
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
        available_songs = web_scraper.get_usdb_available_songs()
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
                #self.treeView_availableSongs.setRowHidden(row, QtCore.QModelIndex(), True)
        self.download_songs(ids)
        
        ### generate song list PDF -> own function
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
        dl_video = self.groupBox_video.isChecked()
        dl_audio = self.groupBox_audio.isChecked()
        dl_cover = self.groupBox_cover.isChecked()
        dl_background = self.groupBox_background.isChecked()
        
        songdir = self.lineEdit_song_dir.text()
        #songdir = "usdb_songs"
        if not os.path.exists(songdir):
            os.mkdir(songdir)
        os.chdir(songdir)
        
        for num, id in enumerate(ids):
            idp = str(id).zfill(5)
                        
            logging.info(f"#{idp} ({num+1}/{len(ids)} - {(num+1)/len(ids)*100:.1f}%):")
            
            exists, details = web_scraper.get_usdb_details(id)
            if not exists:
                # song was deleted meanwhile, TODO: uncheck/remove from model
                continue
            
            songtext = web_scraper.get_notes(id)
            
            #song = createsong(songtext)
            header, notes = note_utils.parse_notes(songtext)
            
            self.statusbar.showMessage(f"Downloading '{header['#ARTIST']} - {header['#TITLE']}' ({num+1}/{len(ids)})") # TODO: this is not updated until after download all songs
            
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
            
            logging.info(f"\t- usdb::artist_title: {header['#ARTIST']} - {header['#TITLE']}")
            
            #sc_info = getscinfo(header)
            
            # if sc_info.get("artist_ldist"):
            #     if sc_info["artist_ldist"] <= 3: # TODO: which value is sensible here?
            #         header["#ARTIST"] = sc_info["artist"]
            #         logging.info(f"\t- artist_ldist <= 3, thus using #ARTIST:{header['#ARTIST']}")
            #     else:
            #         logging.info(f"\t- artist_ldist > 3, is \'{header['#ARTIST']}\' spelled correctly?")
                
            # if sc_info.get("title_ldist"):
            #     if sc_info["title_ldist"] <= 3: # TODO: which value is sensible here?
            #         header["#TITLE"] = sc_info["title"]
            #         logging.info(f"\t- sc::title_ldist <= 3, therefore using #TITLE:{header['#TITLE']}")
            #     else:
            #         logging.info(f"\t- sc::title_ldist > 3, is \'{header['#TITLE']}\' spelled correctly?")
            
            #header, notes, details = cleansong(header, notes, details, resource_params, sc_info, duet)
            dirname = note_utils.generate_dirname(header, resource_params)
                    
            #if not os.path.exists(idp):
            #    os.mkdir(idp)
            #os.chdir(idp)
            
            if not os.path.exists(dirname):
                os.mkdir(dirname)    
            os.chdir(dirname)
            if not os.path.exists(idp):
                os.mkdir(idp)
            os.chdir(idp)
            
            # write .usdb file for synchronization
            with open(f"temp.usdb", 'w', encoding="utf_8") as f:
                f.write(songtext)
            if os.path.exists(f"{idp}.usdb"):
                if filecmp.cmp("temp.usdb", f"{idp}.usdb"):
                    logging.info("\t FILES ARE IDENTICAL - SKIPPING SONG")
                    os.remove("temp.usdb")
                    os.chdir("..")
                    os.chdir("..")
                    continue
                else:
                    logging.info("\t USDB file has been updated, re-downloading...")
                    # TODO: check if resources in #VIDEO tag have changed and if so, re-download new resources only
                    os.remove(f"{idp}.usdb")
                    os.rename("temp.usdb", f"{idp}.usdb")
            else:
                os.rename("temp.usdb", f"{idp}.usdb")
            
            # download audio
            has_audio = False
            if dl_audio:
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
                    if "bestaudio" in self.comboBox_audio_format.currentText():
                        audio_dl_format = "bestaudio"
                    elif "m4a" in self.comboBox_audio_format.currentText():
                        audio_dl_format = "m4a"
                    elif "webm" in self.comboBox_audio_format.currentText():
                        audio_dl_format = "webm"
                        
                    audio_target_format = ""
                    audio_target_codec = ""
                    if self.groupBox_reencode_audio.isChecked():
                        if "mp3" in self.comboBox_audio_conversion_format.currentText():
                            audio_target_format = "mp3"
                            audio_target_codec = "mp3"
                        elif "ogg" in self.comboBox_audio_conversion_format.currentText():
                            audio_target_format = "ogg"
                            audio_target_codec = "vorbis"
                        elif "opus" in self.comboBox_audio_conversion_format.currentText():
                            audio_target_format = "opus"
                            audio_target_codec = "opus"
                    
                    logging.info("\t- downloading audio from #VIDEO params")
                        
                    has_audio, ext = download_and_process_audio(header, audio_resource, audio_dl_format, audio_target_codec)
                    
                    header["#MP3"] = f"{note_utils.generate_filename(header)}.{ext}" 
                    
                    # delete #VIDEO tag used for resources
                    if header.get("#VIDEO"):
                        header.pop("#VIDEO")
                        
                    if has_audio:
                        self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 9, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
            
            # download video
            has_video = False
            if dl_video:
                if video_resource := resource_params.get("v"):
                    pass
                elif not resource_params.get("a"):
                    video_params = details.get("video_params")
                    if video_params:
                        video_resource = video_params.get("v")
                        if video_resource:
                            logging.warning(f"Using Youtube ID {audio_resource} extracted from comments.")
                
                if video_resource:
                    logging.info("\t- downloading video from #VIDEO params")
                    video_params = {
                            "container": self.comboBox_videocontainer.currentText(),
                            "resolution": self.comboBox_videoresolution.currentText(),
                            "fps": self.comboBox_fps.currentText(),
                            "allow_reencode": self.groupBox_reencode_video.isChecked(),
                            "encoder": self.comboBox_videoencoder.currentText()
                        }
                    has_video = download_and_process_video(header, video_resource, video_params, resource_params)
            #     elif resource_params := details.get("video_params"):
            #         logging.info("\t- downloading video from usdb comments")
            #         has_video = dl_yt_video(header, resource_params)
            #     elif resource_params := sc_info.get("video_params"):
            #         logging.info("\t- downloading video from swisscharts song page")
            #         has_video = dl_yt_video(header, resource_params)
                    
                    #if not header.get("#VIDEO"):
                    header["#VIDEO"] = f"{note_utils.generate_filename(header)}{video_params['container']}" 
                    if has_video:
                        self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 10, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
                else:
                    logging.warning("\t- no video resource in #VIDEO tag")

            # download cover
            has_cover = False
            if dl_cover:
                has_cover = download_and_process_cover(header, resource_params, details)
                header["#COVER"] = f"{note_utils.generate_filename(header)} [CO].jpg"
                if has_cover:
                    self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 11, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
            
            # download background
            has_background = False
            if dl_background:
                if self.comboBox_background.currentText() == "always" or (not has_video and self.comboBox_background.currentText() == "only if no video"):
                    has_background = download_and_process_background(header, resource_params)
                    header["#BACKGROUND"] = f"{note_utils.generate_filename(header)} [BG].jpg"
                    
                    if has_background:
                        self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 12, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
                
            # if not has_cover and do_dl_sc_covers and sc_info.get("cover_urls"):
            #     cover_params = {"co": sc_info.get("cover_urls")[0].replace("https://", "")} # TODO: download *all* covers
            #     has_cover = download_and_process_cover(header, cover_params)
            
            # if not has_cover and do_dl_usdb_cover and details.get("cover_url"):    
            #     cover_params = {"co": details.get("cover_url").replace("http://", ""), "co-p": "http"}
            #     has_cover = download_and_process_cover(header, cover_params)
            
            # if do_dl_google_cover:    
            #     dl_google_cover(header)
                
            # if not has_video and do_dl_sc_sample:
            #     sample_url = sc_info.get("sample_url")
            #     if sample_url:
            #         dl_sc_sample(header, sc_info["sample_url"])
            #         header["#TITLE"] += " (Sample)"
            #         mp3 = header["#MP3"]
            #         if mp3.endswith(".mp4"):
            #             header["#MP3"] = mp3.replace(".mp4", " (Sample).mp3")
            #         elif mp3.endswith(".mp3"):
            #             header["#MP3"] = mp3.replace(".mp3", " (Sample).mp3")
            
            # download text file
            bom = False
            if self.comboBox_encoding.currentText() == "UTF-8":
                encoding = "utf_8"
            elif self.comboBox_encoding.currentText() == "UTF-8 BOM":
                encoding = "utf_8_sig"
            elif self.comboBox_encoding.currentText() == "CP1252":
                encoding = "cp1252"
            newline = self.comboBox_line_endings.currentText()
            if newline == "Windows (CRLF)":
                newline = '\r\n'
            elif newline == "Mac/Linux (LF)":
                newline = '\n'
            note_utils.dump_notes(header, notes, duet, encoding, newline)
            self.model.setItem(self.model.findItems(idp, flags=Qt.MatchExactly, column=0)[0].row(), 8, QStandardItem(QIcon(":/icons/resources/tick.png"), ""))
            
            os.chdir("..")
            os.chdir("..")
        
        os.chdir("..")
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
    
    #loader = QUiLoader()
    #quMainWindow = loader.load("QUMainWindow.ui", None)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="UltraStar script.")

    args = parser.parse_args()

    # Call main
    main()
