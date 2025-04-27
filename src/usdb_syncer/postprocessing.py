"""Functions for postprocessing audio/video files."""

from base64 import b64encode
from os import devnull
from pathlib import Path

from ffmpeg_normalize import FFmpegNormalize
from mutagen import id3
from mutagen.flac import Picture
from mutagen.id3 import ID3, TXXX
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover
from mutagen.ogg import OggFileType
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis
from PIL import Image

from usdb_syncer import settings
from usdb_syncer.constants import ISO_639_2B_LANGUAGE_CODES
from usdb_syncer.download_options import AudioOptions, VideoOptions
from usdb_syncer.logger import Logger
from usdb_syncer.settings import AudioFormat, AudioNormalization, VideoContainer
from usdb_syncer.song_txt import SongTxt

# Normalization parameters
DEFAULT_TARGET_LEVEL_RG_DB = -18.0
DEFAULT_TARGET_LEVEL_R128_DB = -23.0

# Explicitly initialize the Python Image Library
Image.init()


def normalize_audio(
    options: AudioOptions, path_stem: Path, input_ext: str, logger: Logger
) -> None:
    normalizer = _create_normalizer(options)
    input_file = f"{path_stem}.{input_ext}"
    output_file = f"{path_stem}.{options.format.value}"
    if options.normalization == AudioNormalization.REPLAYGAIN:
        # audio file is already in target format from postprocessor
        input_file = f"{path_stem}.{options.format.value}"
        # we do not want to actually rewrite the file, so we use 'null'
        output_file = devnull

    normalizer.add_media_file(input_file, output_file)
    normalizer.run_normalization()

    if options.normalization == AudioNormalization.REPLAYGAIN:
        _write_replaygain_tags(normalizer, input_file, logger)


def _create_normalizer(options: AudioOptions) -> FFmpegNormalize:
    target_level = (
        DEFAULT_TARGET_LEVEL_R128_DB
        if options.format == settings.AudioFormat.OPUS
        else DEFAULT_TARGET_LEVEL_RG_DB
    )
    normalizer = FFmpegNormalize(
        normalization_type="ebu",
        target_level=target_level,
        keep_loudness_range_target=True,
        dynamic=False,
        audio_codec=options.format.ffmpeg_encoder(),
        audio_bitrate=options.bitrate.ffmpeg_format(),
        progress=True,
        extra_output_options=(
            ["-f", "null"]
            if options.normalization == AudioNormalization.REPLAYGAIN
            else []
        ),
    )

    return normalizer


def _write_replaygain_tags(
    normalizer: FFmpegNormalize, audio_file: str, logger: Logger
) -> None:
    """Writes ReplayGain values to audio file metadata."""

    # extract stats from 2-pass normalization, then set replay gain values to audio file
    stats = next(iter(normalizer.media_files[0].get_stats()), None)
    if not stats:
        logger.warning("Normalization failed: no stats")
        return
    ebu_pass2 = stats.get("ebu_pass2")
    if not ebu_pass2:
        logger.warning("Normalization failed: no EBU pass 2 normalization stats")
        return

    if (input_i := ebu_pass2.get("input_i")) is None or (
        input_tp := ebu_pass2.get("input_tp")
    ) is None:
        logger.warning("Normalization failed: no loudness or true peak stats")
        return
    track_gain = normalizer.target_level - input_i  # dB
    track_peak = 10 ** (input_tp / 20)  # Linear scale

    try:
        match Path(audio_file).suffix[1:]:
            case AudioFormat.M4A.value:
                _write_replaygain_tags_m4a(audio_file, track_gain, track_peak)
            case AudioFormat.MP3.value:
                _write_replaygain_tags_mp3(audio_file, track_gain, track_peak)
            case AudioFormat.OGG.value:
                _write_replaygain_tags_ogg(audio_file, track_gain, track_peak)
            case AudioFormat.OPUS.value:
                _write_replaygain_tags_opus(audio_file, track_gain)
            case other:
                logger.debug(f"ReplayGain tags not supported for suffix '{other}'.")

        logger.info(f"ReplayGain tags written to {audio_file}")

    except Exception:
        logger.exception(f"Failed to write audio tags to file '{audio_file}'!")
    else:
        logger.debug(f"Audio tags written to file '{audio_file}'.")


def _write_replaygain_tags_m4a(
    audio_file: str, track_gain: float, track_peak: float
) -> None:
    mp4 = MP4(audio_file)
    if not mp4.tags:
        mp4.add_tags()
    if not mp4.tags:
        return
    mp4.tags["----:com.apple.iTunes:REPLAYGAIN_TRACK_GAIN"] = [
        f"{track_gain:.2f} dB".encode()
    ]
    mp4.tags["----:com.apple.iTunes:REPLAYGAIN_TRACK_PEAK"] = [
        f"{track_peak:.6f}".encode()
    ]
    mp4.save()


def _write_replaygain_tags_mp3(
    audio_file: str, track_gain: float, track_peak: float
) -> None:
    mp3 = MP3(audio_file, ID3=ID3)
    if not mp3.tags:
        return
    mp3.tags.add(TXXX(desc="REPLAYGAIN_TRACK_GAIN", text=[f"{track_gain:.2f} dB"]))
    mp3.tags.add(TXXX(desc="REPLAYGAIN_TRACK_PEAK", text=[f"{track_peak:.6f}"]))
    mp3.save()


def _write_replaygain_tags_ogg(
    audio_file: str, track_gain: float, track_peak: float
) -> None:
    ogg = OggVorbis(audio_file)
    ogg["REPLAYGAIN_TRACK_GAIN"] = [f"{track_gain:.2f} dB"]
    ogg["REPLAYGAIN_TRACK_PEAK"] = [f"{track_peak:.6f}"]
    ogg.save()


def _write_replaygain_tags_opus(audio_file: str, track_gain: float) -> None:
    opus = OggOpus(audio_file)
    # See https://datatracker.ietf.org/doc/html/rfc7845#section-5.2.1
    opus["R128_TRACK_GAIN"] = [str(round(256 * track_gain))]
    opus.save()


def write_audio_tags(
    *,
    txt: SongTxt,
    options: AudioOptions,
    audio: tuple[Path, str],
    cover: tuple[Path, str] | None,
    background: tuple[Path, str] | None,
    logger: Logger,
) -> None:
    audio_path = audio[0]
    try:
        match audio_path.suffix[1:]:
            case AudioFormat.M4A.value:
                _write_tags_m4a_mp4(
                    audio, cover, background, txt, options.embed_artwork
                )
            case AudioFormat.MP3.value:
                _write_tags_mp3(audio, cover, txt, options.embed_artwork)
            case AudioFormat.OGG.value:
                _write_tags_ogg(audio, cover, txt, options.embed_artwork)
            case AudioFormat.OPUS.value:
                _write_tags_ogg(audio, cover, txt, options.embed_artwork)
            case other:
                logger.debug(f"Audio tags not supported for suffix '{other}'.")
                return
    except Exception:
        logger.exception(f"Failed to write audio tags to file '{audio_path}'!")
    else:
        logger.debug(f"Audio tags written to file '{audio_path}'.")


def write_video_tags(
    *,
    txt: SongTxt,
    options: VideoOptions,
    video: tuple[Path, str],
    cover: tuple[Path, str] | None,
    background: tuple[Path, str] | None,
    logger: Logger,
) -> None:
    video_path = video[0]
    try:
        match video_path.suffix[1:]:
            case VideoContainer.MP4.value:
                _write_tags_m4a_mp4(
                    video, cover, background, txt, options.embed_artwork
                )
            case other:
                logger.debug(f"Video tags not supported for suffix '{other}'.")
                return
    except Exception:
        logger.exception(f"Failed to write video tags to file '{video_path}'!")
    else:
        logger.debug(f"Video tags written to file '{video_path}'.")


def _write_tags_m4a_mp4(
    audio_video: tuple[Path, str],
    cover: tuple[Path, str] | None,
    background: tuple[Path, str] | None,
    txt: SongTxt,
    embed_artwork: bool,
) -> None:
    m4a_mp4 = MP4(audio_video[0])
    if not m4a_mp4.tags:
        m4a_mp4.add_tags()
    if not m4a_mp4.tags:
        return
    m4a_mp4.tags["\xa9ART"] = txt.headers.artist
    m4a_mp4.tags["\xa9nam"] = txt.headers.title
    if txt.headers.genre:
        m4a_mp4.tags["\xa9gen"] = txt.headers.genre
    if txt.headers.year:
        m4a_mp4.tags["\xa9day"] = txt.headers.year
    m4a_mp4.tags["\xa9lyr"] = txt.unsynchronized_lyrics()
    m4a_mp4.tags["\xa9cmt"] = audio_video[1]

    if embed_artwork:
        cover_path = cover[0] if cover else None
        background_path = background[0] if background else None
        m4a_mp4.tags["covr"] = [
            MP4Cover(image.read_bytes(), imageformat=MP4Cover.FORMAT_JPEG)
            for image in (cover_path, background_path)
            if image
        ]

    m4a_mp4.save()


def _write_tags_mp3(
    audio: tuple[Path, str],
    cover: tuple[Path, str] | None,
    txt: SongTxt,
    embed_artwork: bool,
) -> None:
    audio_path, audio_resource = audio
    mp3 = MP3(audio_path, ID3=id3.ID3)
    if not mp3.tags:
        mp3.add_tags()
    if not mp3.tags:
        return
    lang = ISO_639_2B_LANGUAGE_CODES.get(txt.headers.main_language(), "und")
    mp3.tags["TPE1"] = id3.TPE1(encoding=id3.Encoding.UTF8, text=txt.headers.artist)
    mp3.tags["TIT2"] = id3.TIT2(encoding=id3.Encoding.UTF8, text=txt.headers.title)
    mp3.tags["TLAN"] = id3.TLAN(encoding=id3.Encoding.UTF8, text=lang)
    if genre := txt.headers.genre:
        mp3.tags["TCON"] = id3.TCON(encoding=id3.Encoding.UTF8, text=genre)
    if year := txt.headers.year:
        mp3.tags["TDRC"] = id3.TDRC(encoding=id3.Encoding.UTF8, text=year)
    mp3.tags[f"USLT::'{lang}'"] = id3.USLT(
        encoding=id3.Encoding.UTF8,
        lang=lang,
        desc="Lyrics",
        text=txt.unsynchronized_lyrics(),
    )
    mp3.tags["SYLT"] = id3.SYLT(
        encoding=id3.Encoding.UTF8,
        lang=lang,
        format=2,  # milliseconds as units
        type=1,  # lyrics
        text=txt.synchronized_lyrics(),
    )
    mp3.tags["COMM"] = id3.COMM(
        encoding=id3.Encoding.UTF8, lang="eng", desc="Audio Source", text=audio_resource
    )

    if embed_artwork and cover:
        cover_path, cover_resource = cover
        mp3.tags.add(
            id3.APIC(
                encoding=id3.Encoding.UTF8,
                mime=Image.MIME["JPEG"],
                type=id3.PictureType.COVER_FRONT,
                desc=f"Source: {cover_resource}",
                data=cover_path.read_bytes(),
            )
        )

    mp3.save()


def _write_tags_ogg(
    audio: tuple[Path, str],
    cover: tuple[Path, str] | None,
    txt: SongTxt,
    embed_artwork: bool,
) -> None:
    audio_path, audio_resource = audio
    ogg = OggFileType()
    match audio_path.suffix[1:]:
        case AudioFormat.OGG.value:
            ogg = OggVorbis(audio_path)
        case AudioFormat.OPUS.value:
            ogg = OggOpus(audio_path)
        case _:
            return
    # Set basic tags
    ogg["artist"] = txt.headers.artist
    ogg["title"] = txt.headers.title
    ogg["language"] = ISO_639_2B_LANGUAGE_CODES.get(txt.headers.main_language(), "und")
    if genre := txt.headers.genre:
        ogg["genre"] = genre
    if year := txt.headers.year:
        ogg["date"] = year
    ogg["lyrics"] = txt.unsynchronized_lyrics()
    ogg["comment"] = audio_resource

    if embed_artwork and cover:
        cover_path = cover[0]
        picture = Picture()
        with cover_path.open("rb") as file:
            picture.data = file.read()
        with Image.open(cover_path) as image:
            picture.width, picture.height = image.size
        picture.type = 3  # "Cover (front)"
        picture.desc = "Cover art"
        picture.mime = Image.MIME["JPEG"]
        picture.depth = 24

        encoded_data = b64encode(picture.write())
        vcomment_value = encoded_data.decode("ascii")

        ogg["metadata_block_picture"] = [vcomment_value]

    ogg.save()
