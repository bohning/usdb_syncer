"""Functionality related to the usdb.animux.de web page."""

import logging
import re
import urllib.parse
from typing import Any, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup  # type: ignore

_logger: logging.Logger = logging.getLogger(__file__)


def get_usdb_page(
    rel_url: str,
    method: str = "GET",
    headers: dict[str, str] = None,
    payload: dict[str, str] = None,
    params: dict[str, str] = None,
) -> str:
    """Retrieve html subpage from usbd.

    Parameters:
        rel_url: relative url of page to retrieve
        method: GET or POST
        headers: dict of headers to send with request
        payload: dict of data to send with request
        params: dict of params to send with request
    """
    # wildcard login
    _headers = {"Cookie": "PHPSESSID"}
    if headers:
        _headers.update(headers)

    url = "http://usdb.animux.de/" + rel_url

    if method == "GET":
        _logger.debug("get request for %s", url)
        response = requests.get(url, headers=_headers, params=params, timeout=3)

    elif method == "POST":
        _logger.debug("post request for %s", url)
        response = requests.post(url, headers=_headers, data=payload, params=params, timeout=3)
    else:
        raise NotImplementedError(f"{method} request not supported")
    response.raise_for_status()
    response.encoding = response.encoding = "utf-8"
    return response.text


def get_usdb_available_songs(content_filter: Dict[str, str] = None) -> List[dict]:
    """Return a list of all available songs.

    Parameters:
        content_filter: filters response (e.g. {'artist': 'The Beatles'})
    """
    params = {"link": "list"}
    payload = {"limit": "50000", "order": "id", "ud": "desc"}
    if content_filter:
        payload.update(content_filter)

    html = get_usdb_page("index.php", "POST", params=params, payload=payload)

    regex = (
        r'<td onclick="show_detail\((\d+)\)">(.*)</td>\n'
        r'<td onclick="show_detail\(\d+\)">(.*)</td>\n'
        r'<td onclick="show_detail\(\d+\)">(.*)</td>\n'
        r'<td onclick="show_detail\(\d+\)">(.*)</td>\n'
        r'<td onclick="show_detail\(\d+\)">(.*)</td>\n'
        r'<td onclick="show_detail\(\d+\)">(.*)</td>\n'
        r'<td onclick="show_detail\(\d+\)">(.*)</td>'
    )
    matches = re.findall(regex, html)

    available_songs = []
    for match in matches:
        (
            song_id,
            artist,
            title,
            edition,
            goldennotes,
            language,
            rating_string,
            views,
        ) = match
        song = {
            "id": song_id,
            "artist": artist,
            "title": title,
            "language": language,
            "edition": edition,
            "goldennotes": bool(goldennotes == "Yes"),
            "rating": str(rating_string.count("star.png")),
            "views": views,
        }
        available_songs.append(song)
    _logger.info("fetched %d available songs", len(available_songs))
    return available_songs


def _parse_song_details(details: Dict[str, str], details_table: BeautifulSoup) -> Dict[str, str]:
    """Parse song attributes from usdb page.

    Parameters:
        details: dict of song attributes
        details_table: BeautifulSoup object of song details table
    """
    details["artist"] = details_table.find_next("td").text
    details["title"] = details_table.find_next("td").find_next("td").text

    cover_url = details_table.img["src"]
    if not "nocover" in cover_url:
        details["cover_url"] = "http://usdb.animux.de/" + cover_url

    details["bpm"] = details_table.find(text="BPM").next.text
    details["gap"] = details_table.find(text="GAP").next.text
    details["golden_notes"] = str("Yes" in details_table.find(text="Golden Notes").next.text)
    details["song_check"] = str("Yes" in details_table.find(text="Songcheck").next.text)
    date_time = details_table.find(text="Date").next.text
    details["date"], details["time"] = date_time.split(" - ")
    details["uploader"] = details_table.find(text="Created by").next.text

    editors = []

    pointer = details_table.find(text="Song edited by:")
    while pointer is not None:
        pointer = pointer.find_next("td")
        if pointer.a is None:
            break
        editors.append(pointer.text.strip())
        pointer = pointer.find_next("tr")

    details["views"] = details_table.find(text="Views").next.text

    stars = details_table.find(text="Rating").next.find_all("img")
    details["rating"] = str(sum(["star.png" in s.get("src") for s in stars]))
    details["votes"] = details_table.find(text="Rating").next.next.next.next.next.next.next.next.next.next.next[
        2:-2
    ]  # " (number) "

    if param := details_table.find("param", attrs={"name": "FlashVars"}):
        flash_vars = urllib.parse.parse_qs(param.get("value"))
        details["audio_sample"] = flash_vars["soundFile"][0]
    # only captures first team comment (example of multiple needed!)
    team_comments = details_table.find(text="Team Comment").next.text
    if "No comment yet" not in team_comments:
        details["team_comments"] = team_comments
    return details


def _parse_comment_details(details: Dict[str, str], _comments_table: BeautifulSoup) -> Dict[str, str]:
    """Tbd.

    Parameters:
        details: dict of song attributes
        comments_table: BeautifulSoup object of song details table
    """
    # user comments (with video links and possible GAP/BPM values)
    comment_headers = _comments_table.find_all("tr", class_="list_tr2")[
        :-1
    ]  # last entry is the field to enter a new comment, so this one is ignored
    if comment_headers:
        comments = []
        for i, comment_header in enumerate(comment_headers):
            comment = {}
            comment_details = comment_header.find("td").text.strip()
            regex = r".*(\d{2})\.(\d{2})\.(\d{2}) - (\d{2}):(\d{2}) \| (.*)"
            match = re.search(regex, comment_details)
            if not match:
                _logger.info("\t- usdb::song has no comments!")
                continue

            (
                comment_day,
                comment_month,
                comment_year,
                comment_hour,
                comment_minute,
                comment_commenter,
            ) = match.groups()
            comment_date = f"20{comment_year}-{comment_month}-{comment_day}"
            comment_time = f"{comment_hour}:{comment_minute}"
            comment_contents = comment_header.next_sibling
            comment_urls = []
            if comment_embeds := comment_contents.find_all("embed"):
                for i, comment_embed in enumerate(comment_embeds):
                    yt_url = comment_embed.get("src").split("&")[0]  # TODO: this assumes youtube embeds
                    try:
                        yt_id = extract.video_id(yt_url)
                    except:
                        _logger.warning(
                            f"\t- usdb::comment embed contains a url ({yt_url}), but the Youtube video ID could not be extracted."
                        )
                    else:
                        comment_urls.append(yt_url)
                        details["video_params"] = {
                            "v": yt_id
                        }  # TODO: this only takes the first youtube link in the newest comments
            comment_text = comment_contents.find("td").text.strip()
            regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
            urls = re.findall(regex, comment_text)
            for url in urls:
                try:
                    yt_id = extract.video_id(url[0])
                except:
                    _logger.warning(
                        f"\t- usdb::comment contains a plain url ({url}), but it does not seem to be a Youtube link."
                    )
                else:
                    comment_urls.append(f"https://www.youtube.com/watch?v={yt_id}")
                    if not details.get("video_params"):
                        details["video_params"] = {"v": yt_id}
                    comment_text = comment_text.replace(url[0], "").strip()
            comment = {
                "date": comment_date,
                "time": comment_time,
                "commenter": comment_commenter,
                "comment_urls": comment_urls,
                "comment_text": comment_text,
            }
            comments.append(comment)
        if comments:
            details["comments"] = comments

    return details


def get_usdb_details(song_id: str) -> Tuple[bool, dict[str, Any]]:
    """Retrieve song details from usdb webpage.

    Parameters:
        song_id: id of song to retrieve details for
    """
    html = get_usdb_page("index.php", params={"id": song_id, "link": "detail"})
    soup = BeautifulSoup(html, "lxml")
    # german response for 'dataset not found'
    exists = "Datensatz nicht gefunden" not in soup.get_text()

    details = {"id": song_id}
    details["exists"] = str(exists)

    if not exists:
        return exists, details

    if not (tables := soup.find_all("table", border="0", width="500")):
        raise LookupError("no tables in usdb details page.")

    details_table = tables[0]
    comments_table = tables[1]

    # parse song attributes from page
    details = _parse_song_details(details, details_table)
    # user comments (with video links and possible GAP/BPM values)
    details = _parse_comment_details(details, comments_table)
    return exists, details


def get_notes(song_id: str) -> str:
    """Retrieve notes for a song.

    Parameters:
        id: song id
    """
    _logger.debug("\t- fetch notes for song %s", song_id)
    params = {"link": "gettxt", "id": song_id}
    payload = {"wd": "1"}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    html = get_usdb_page("index.php", "POST", headers=headers, params=params, payload=payload)
    soup = BeautifulSoup(html, "lxml")
    try:
        songtext = soup.find("textarea").string
    except AttributeError as exception:
        raise LookupError(f"no notes found for song {song_id}") from exception
    songtext = songtext.replace("<", "(")
    songtext = songtext.replace(">", ")")
    return songtext
