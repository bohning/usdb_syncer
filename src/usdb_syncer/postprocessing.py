"""Functions for postprocessing audio/video files."""

import traceback
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
from usdb_syncer.context import Context
from usdb_syncer.download_options import AudioOptions, VideoOptions
from usdb_syncer.logger import Log
from usdb_syncer.settings import AudioFormat, AudioNormalization, VideoContainer

# Normalization parameters
DEFAULT_TARGET_LEVEL_RG_DB = -18.0
DEFAULT_TARGET_LEVEL_R128_DB = -23.0


def normalize_audio(
    options: AudioOptions, path_stem: Path, input_ext: str, logger: Log
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
    normalizer: FFmpegNormalize, audio_file: str, logger: Log
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

    except Exception:  # pylint: disable=broad-exception-caught
        logger.debug(traceback.format_exc())
        logger.error(f"Failed to write audio tags to file '{audio_file}'!")
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
    ctx: Context, options: AudioOptions, path_resource: tuple[Path, str]
) -> None:
    path, resource = path_resource
    try:
        match path.suffix[1:]:
            case AudioFormat.M4A.value:
                _write_tags_m4a_mp4(path, resource, ctx, options.embed_artwork)
            case AudioFormat.MP3.value:
                _write_tags_mp3(path, resource, ctx, options.embed_artwork)
            case AudioFormat.OGG.value:
                _write_tags_ogg(OggVorbis(path), resource, ctx, options.embed_artwork)
            case AudioFormat.OPUS.value:
                _write_tags_ogg(OggOpus(path), resource, ctx, options.embed_artwork)
            case other:
                ctx.logger.debug(f"Audio tags not supported for suffix '{other}'.")
                return
    except Exception:  # pylint: disable=broad-exception-caught
        ctx.logger.debug(traceback.format_exc())
        ctx.logger.error(f"Failed to write audio tags to file '{path}'!")
    else:
        ctx.logger.debug(f"Audio tags written to file '{path}'.")


def write_video_tags(
    ctx: Context, options: VideoOptions, path_resource: tuple[Path, str]
) -> None:
    path, resource = path_resource
    try:
        match path.suffix[1:]:
            case VideoContainer.MP4.value:
                _write_tags_m4a_mp4(path, resource, ctx, options.embed_artwork)
            case other:
                ctx.logger.debug(f"Video tags not supported for suffix '{other}'.")
                return
    except Exception:  # pylint: disable=broad-exception-caught
        ctx.logger.debug(traceback.format_exc())
        ctx.logger.error(f"Failed to write video tags to file '{path}'!")
    else:
        ctx.logger.debug(f"Video tags written to file '{path}'.")


def _write_tags_m4a_mp4(
    path: Path, resource: str, ctx: Context, embed_artwork: bool
) -> None:
    mp4 = MP4(path)
    if not mp4.tags:
        mp4.add_tags()
    if not mp4.tags:
        return
    mp4.tags["\xa9ART"] = ctx.txt.headers.artist
    mp4.tags["\xa9nam"] = ctx.txt.headers.title
    if ctx.txt.headers.genre:
        mp4.tags["\xa9gen"] = ctx.txt.headers.genre
    if ctx.txt.headers.year:
        mp4.tags["\xa9day"] = ctx.txt.headers.year
    mp4.tags["\xa9lyr"] = ctx.txt.unsynchronized_lyrics()
    mp4.tags["\xa9cmt"] = resource

    if embed_artwork:
        mp4.tags["covr"] = [
            MP4Cover(image.read_bytes(), imageformat=MP4Cover.FORMAT_JPEG)
            for image in (
                ctx.out.cover.path(ctx.locations, temp=True),
                ctx.out.background.path(ctx.locations, temp=True),
            )
            if image
        ]

    mp4.save()


def _write_tags_mp3(
    path: Path, resource: str, ctx: Context, embed_artwork: bool
) -> None:
    mp3 = MP3(path, ID3=id3.ID3)
    if not mp3.tags:
        mp3.add_tags()
    if not mp3.tags:
        return
    lang = ISO_639_2B_LANGUAGE_CODES.get(ctx.txt.headers.main_language(), "und")
    mp3.tags["TPE1"] = id3.TPE1(encoding=id3.Encoding.UTF8, text=ctx.txt.headers.artist)
    mp3.tags["TIT2"] = id3.TIT2(encoding=id3.Encoding.UTF8, text=ctx.txt.headers.title)
    mp3.tags["TLAN"] = id3.TLAN(encoding=id3.Encoding.UTF8, text=lang)
    if genre := ctx.txt.headers.genre:
        mp3.tags["TCON"] = id3.TCON(encoding=id3.Encoding.UTF8, text=genre)
    if year := ctx.txt.headers.year:
        mp3.tags["TDRC"] = id3.TDRC(encoding=id3.Encoding.UTF8, text=year)
    mp3.tags[f"USLT::'{lang}'"] = id3.USLT(
        encoding=id3.Encoding.UTF8,
        lang=lang,
        desc="Lyrics",
        text=ctx.txt.unsynchronized_lyrics(),
    )
    mp3.tags["SYLT"] = id3.SYLT(
        encoding=id3.Encoding.UTF8,
        lang=lang,
        format=2,  # milliseconds as units
        type=1,  # lyrics
        text=ctx.txt.synchronized_lyrics(),
    )
    mp3.tags["COMM"] = id3.COMM(
        encoding=id3.Encoding.UTF8, lang="eng", desc="Audio Source", text=resource
    )

    if embed_artwork and (
        path_resource := ctx.out.cover.path_and_resource(ctx.locations, temp=True)
    ):
        mp3.tags.add(
            id3.APIC(
                encoding=id3.Encoding.UTF8,
                mime="image/jpeg",
                type=id3.PictureType.COVER_FRONT,
                desc=f"Source: {path_resource[1]}",
                data=path_resource[0].read_bytes(),
            )
        )

    mp3.save()


def _write_tags_ogg(
    audio: OggFileType, resource: str, ctx: Context, embed_artwork: bool
) -> None:
    # Set basic tags
    audio["artist"] = ctx.txt.headers.artist
    audio["title"] = ctx.txt.headers.title
    lang = ISO_639_2B_LANGUAGE_CODES.get(ctx.txt.headers.main_language(), "und")
    audio["language"] = lang
    if genre := ctx.txt.headers.genre:
        audio["genre"] = genre
    if year := ctx.txt.headers.year:
        audio["date"] = year
    audio["lyrics"] = ctx.txt.unsynchronized_lyrics()
    audio["comment"] = resource

    if embed_artwork and (cover_path := ctx.out.cover.path(ctx.locations, temp=True)):
        picture = Picture()
        with cover_path.open("rb") as file:
            picture.data = file.read()
        with Image.open(cover_path) as image:
            picture.width, picture.height = image.size
        picture.type = 3  # "Cover (front)"
        picture.desc = "Cover art"
        picture.mime = "image/jpeg"
        picture.depth = 24

        picture_data = picture.write()
        encoded_data = b64encode(picture_data)
        vcomment_value = encoded_data.decode("ascii")

        audio["metadata_block_picture"] = [vcomment_value]

    audio.save()
