"""
Universal Subtitle Extractor v3.3
MKV / MP4 내장 자막을 원본 형식 그대로 추출하는 순수 Python GUI 프로그램
외부 도구(FFmpeg, MKVToolNix) 불필요 - Python 3.9+

사전 설치: pip install tkinterdnd2

지원 추출 형식:
  MKV: S_TEXT/UTF8   → .srt
       S_TEXT/ASS    → .ass
       S_TEXT/SSA    → .ssa
       S_TEXT/WEBVTT → .vtt
  MP4: tx3g/mov_text → .srt
"""

import struct
import os
import re
import threading
import platform
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from dataclasses import dataclass
from typing import Optional

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False


# ═══════════════════════════════════════════════════════════════
#  공통
# ═══════════════════════════════════════════════════════════════

LANG_NAMES = {
    "kor": "한국어", "ko": "한국어", "eng": "영어", "en": "영어",
    "jpn": "일본어", "ja": "일본어", "chi": "중국어", "zh": "중국어",
    "zho": "중국어", "spa": "스페인어", "es": "스페인어",
    "fre": "프랑스어", "fra": "프랑스어", "fr": "프랑스어",
    "ger": "독일어", "deu": "독일어", "de": "독일어",
    "por": "포르투갈어", "pt": "포르투갈어",
    "ita": "이탈리아어", "it": "이탈리아어",
    "rus": "러시아어", "ru": "러시아어",
    "ara": "아랍어", "ar": "아랍어", "hin": "힌디어", "hi": "힌디어",
    "tha": "태국어", "th": "태국어", "vie": "베트남어", "vi": "베트남어",
    "ind": "인도네시아어", "id": "인도네시아어",
    "may": "말레이어", "msa": "말레이어", "ms": "말레이어",
    "dan": "덴마크어", "da": "덴마크어",
    "cze": "체코어", "ces": "체코어", "cs": "체코어",
    "dut": "네덜란드어", "nld": "네덜란드어", "nl": "네덜란드어",
    "fin": "핀란드어", "fi": "핀란드어",
    "gre": "그리스어", "ell": "그리스어", "el": "그리스어",
    "heb": "히브리어", "he": "히브리어",
    "hun": "헝가리어", "hu": "헝가리어",
    "nor": "노르웨이어", "nob": "노르웨이어", "no": "노르웨이어",
    "pol": "폴란드어", "pl": "폴란드어",
    "rum": "루마니아어", "ron": "루마니아어", "ro": "루마니아어",
    "swe": "스웨덴어", "sv": "스웨덴어",
    "tur": "터키어", "tr": "터키어",
    "ukr": "우크라이나어", "uk": "우크라이나어",
    "bul": "불가리아어", "bg": "불가리아어",
    "hrv": "크로아티아어", "hr": "크로아티아어",
    "slv": "슬로베니아어", "sl": "슬로베니아어",
    "srp": "세르비아어", "sr": "세르비아어",
    "cat": "카탈루냐어", "ca": "카탈루냐어",
    "fil": "필리핀어", "tl": "필리핀어",
    "und": "알 수 없음",
}

CODEC_EXT_MAP = {
    "S_TEXT/UTF8":   (".srt", "SRT"),
    "S_TEXT/ASS":    (".ass", "ASS"),
    "S_TEXT/SSA":    (".ssa", "SSA"),
    "S_TEXT/WEBVTT": (".vtt", "WebVTT"),
    "tx3g":          (".srt", "SRT"),
    "text":          (".srt", "SRT"),
    "mov_text":      (".srt", "SRT"),
}


@dataclass
class SubTrack:
    number: int = 0
    codec_id: str = ""
    language: str = "und"
    name: str = ""
    codec_private: bytes = b""
    container: str = ""

    @property
    def extension(self) -> str:
        return CODEC_EXT_MAP.get(self.codec_id, (".srt", "SRT"))[0]

    @property
    def format_name(self) -> str:
        return CODEC_EXT_MAP.get(self.codec_id, (".srt", "SRT"))[1]


@dataclass
class SubEvent:
    track_number: int = 0
    start_ms: int = 0
    duration_ms: int = 0
    raw_data: bytes = b""


def decode_text(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "utf-16-le", "utf-16-be",
                "utf-16", "cp949", "shift_jis", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace")


# ═══════════════════════════════════════════════════════════════
#  MKV 파서
# ═══════════════════════════════════════════════════════════════

TRACK_TYPE_SUBTITLE = 0x11
CONTAINER_IDS = {
    0x1A45DFA3, 0x18538067, 0x1549A966, 0x1654AE6B,
    0xAE, 0x1F43B675, 0xA0, 0x1C53BB6B, 0x1254C367,
    0x1043A770, 0x1941A469,
}


def _read_ebml_id(f) -> tuple:
    first = f.read(1)
    if not first:
        return -1, 0
    b = first[0]
    length, mask = 1, 0x80
    while length <= 4:
        if b & mask:
            break
        mask >>= 1
        length += 1
    if length > 4:
        return -1, 0
    value = b
    for _ in range(length - 1):
        nb = f.read(1)
        if not nb:
            return -1, 0
        value = (value << 8) | nb[0]
    return value, length


def _read_ebml_vint(f) -> tuple:
    first = f.read(1)
    if not first:
        return -1, 0
    b = first[0]
    length, mask = 1, 0x80
    while length <= 8:
        if b & mask:
            break
        mask >>= 1
        length += 1
    if length > 8:
        return -1, 0
    value = b & (mask - 1)
    for _ in range(length - 1):
        nb = f.read(1)
        if not nb:
            return -1, 0
        value = (value << 8) | nb[0]
    return value, length


def _read_uint(data: bytes) -> int:
    val = 0
    for b in data:
        val = (val << 8) | b
    return val


def _read_ebml_header(f) -> tuple:
    eid, _ = _read_ebml_id(f)
    if eid == -1:
        return -1, -1
    size, _ = _read_ebml_vint(f)
    return eid, size


class MKVParser:
    def __init__(self, filepath: str, progress_cb=None):
        self.filepath = filepath
        self.file_size = os.path.getsize(filepath)
        self.timecode_scale = 1_000_000
        self.tracks: list[SubTrack] = []
        self.events: list[SubEvent] = []
        self.progress_cb = progress_cb

    def parse_tracks_only(self):
        with open(self.filepath, "rb") as f:
            self._scan_top(f, True)

    def parse_all(self):
        with open(self.filepath, "rb") as f:
            self._scan_top(f, False)

    def _report(self, pos):
        if self.progress_cb:
            self.progress_cb(min(int(pos / self.file_size * 100), 100))

    def _scan_top(self, f, tracks_only):
        while f.tell() < self.file_size:
            eid, size = _read_ebml_header(f)
            if eid == -1 or size < 0:
                break
            if eid == 0x18538067:
                self._parse_segment(f, f.tell() + size, tracks_only)
                break
            else:
                f.seek(f.tell() + size)

    def _parse_segment(self, f, end, tracks_only):
        while f.tell() < end:
            eid, size = _read_ebml_header(f)
            if eid == -1 or size < 0:
                break
            start = f.tell()
            if size >= (1 << 56) - 1:
                if not tracks_only:
                    self._parse_segment_unk(f, end)
                break
            if eid == 0x1549A966:
                self._parse_info(f, start + size)
            elif eid == 0x1654AE6B:
                self._parse_tracks(f, start + size)
                if tracks_only:
                    return
            elif eid == 0x1F43B675:
                if tracks_only:
                    return
                self._parse_cluster(f, start + size)
                self._report(f.tell())
            else:
                f.seek(start + size)

    def _parse_segment_unk(self, f, end):
        while f.tell() < end:
            eid, size = _read_ebml_header(f)
            if eid == -1 or size < 0:
                break
            start = f.tell()
            if size >= (1 << 56) - 1:
                break
            if eid == 0x1F43B675:
                self._parse_cluster(f, start + size)
                self._report(f.tell())
            else:
                f.seek(start + size)

    def _parse_info(self, f, end):
        while f.tell() < end:
            eid, size = _read_ebml_header(f)
            if eid == -1 or size < 0:
                break
            if eid == 0x2AD7B1:
                self.timecode_scale = _read_uint(f.read(size))
            else:
                f.read(size)

    def _parse_tracks(self, f, end):
        while f.tell() < end:
            eid, size = _read_ebml_header(f)
            if eid == -1 or size < 0:
                break
            if eid == 0xAE:
                self._parse_track_entry(f, f.tell() + size)
            else:
                f.read(size)

    def _parse_track_entry(self, f, end):
        trk = SubTrack(container="mkv")
        ttype = 0
        while f.tell() < end:
            eid, size = _read_ebml_header(f)
            if eid == -1 or size < 0:
                break
            start = f.tell()
            if eid == 0xD7:
                trk.number = _read_uint(f.read(size))
            elif eid == 0x83:
                ttype = _read_uint(f.read(size))
            elif eid == 0x86:
                trk.codec_id = f.read(size).decode("ascii", errors="replace").strip("\x00")
            elif eid == 0x22B59C:
                trk.language = f.read(size).decode("ascii", errors="replace").strip("\x00")
            elif eid == 0x536E:
                trk.name = f.read(size).decode("utf-8", errors="replace").strip("\x00")
            elif eid == 0x63A2:
                trk.codec_private = f.read(size)
            else:
                f.seek(start + size)
        if ttype == TRACK_TYPE_SUBTITLE:
            self.tracks.append(trk)

    def _parse_cluster(self, f, end):
        cl_tc = 0
        while f.tell() < end:
            eid, size = _read_ebml_header(f)
            if eid == -1 or size < 0:
                break
            start = f.tell()
            if eid == 0xE7:
                cl_tc = _read_uint(f.read(size))
            elif eid == 0xA3:
                self._handle_block(f.read(size), cl_tc, 0)
            elif eid == 0xA0:
                self._parse_block_group(f, start + size, cl_tc)
            else:
                f.seek(start + size)

    def _parse_block_group(self, f, end, cl_tc):
        bdata, dur = None, 0
        while f.tell() < end:
            eid, size = _read_ebml_header(f)
            if eid == -1 or size < 0:
                break
            if eid == 0xA1:
                bdata = f.read(size)
            elif eid == 0x9B:
                dur = _read_uint(f.read(size))
            else:
                f.read(size)
        if bdata:
            self._handle_block(bdata, cl_tc, dur)

    def _handle_block(self, data, cl_tc, dur):
        if len(data) < 4:
            return
        b = data[0]
        length, mask = 1, 0x80
        while length <= 4:
            if b & mask:
                break
            mask >>= 1
            length += 1
        if length > 4:
            return
        tnum = b & (mask - 1)
        for i in range(1, length):
            tnum = (tnum << 8) | data[i]
        if not any(t.number == tnum for t in self.tracks):
            return
        pos = length
        if pos + 2 > len(data):
            return
        rel = struct.unpack(">h", data[pos:pos + 2])[0]
        pos += 3
        sf = self.timecode_scale / 1_000_000
        self.events.append(SubEvent(
            track_number=tnum,
            start_ms=int((cl_tc + rel) * sf),
            duration_ms=int(dur * sf) if dur > 0 else 0,
            raw_data=data[pos:]
        ))


# ═══════════════════════════════════════════════════════════════
#  MP4 파서
# ═══════════════════════════════════════════════════════════════

class MP4Parser:
    def __init__(self, filepath: str, progress_cb=None):
        self.filepath = filepath
        self.file_size = os.path.getsize(filepath)
        self.tracks: list[SubTrack] = []
        self.events: list[SubEvent] = []
        self.progress_cb = progress_cb
        self._track_info: list[dict] = []

    def parse_tracks_only(self):
        with open(self.filepath, "rb") as f:
            self._parse_boxes(f, self.file_size, scan_only=True)

    def parse_all(self):
        self._track_info.clear()
        self.events.clear()
        with open(self.filepath, "rb") as f:
            self._parse_boxes(f, self.file_size, scan_only=False)
        self._build_events()

    def _report(self, pos):
        if self.progress_cb:
            self.progress_cb(min(int(pos / self.file_size * 100), 100))

    def _read_box_header(self, f) -> tuple:
        hdr = f.read(8)
        if len(hdr) < 8:
            return None, 0, 0
        size = struct.unpack(">I", hdr[:4])[0]
        btype = hdr[4:8]
        header_size = 8
        if size == 1:
            ext = f.read(8)
            if len(ext) < 8:
                return None, 0, 0
            size = struct.unpack(">Q", ext)[0]
            header_size = 16
        elif size == 0:
            size = self.file_size - f.tell() + 8
        return btype, size - header_size, header_size

    def _parse_boxes(self, f, end_pos, scan_only, ctx=None):
        while f.tell() < end_pos:
            btype, dsize, _ = self._read_box_header(f)
            if btype is None:
                break
            box_end = f.tell() + dsize
            if btype == b"moov":
                self._parse_boxes(f, box_end, scan_only, ctx)
            elif btype == b"trak":
                tctx = {"track_id": 0, "handler": b"", "language": "und",
                        "name": "", "codec": "", "timescale": 1000,
                        "sample_sizes": [], "chunk_offsets": [],
                        "stts": [], "stsc": [], "codec_private": b""}
                self._parse_boxes(f, box_end, scan_only, tctx)
                if tctx["handler"] in (b"sbtl", b"subt", b"text", b"subp", b"clcp"):
                    trk = SubTrack(
                        number=tctx["track_id"], codec_id=tctx["codec"],
                        language=tctx["language"], name=tctx["name"],
                        codec_private=tctx["codec_private"], container="mp4")
                    self.tracks.append(trk)
                    if not scan_only:
                        self._track_info.append(tctx)
            elif btype in (b"mdia", b"minf", b"stbl", b"udta", b"dinf", b"edts"):
                self._parse_boxes(f, box_end, scan_only, ctx)
            elif btype == b"tkhd":
                self._p_tkhd(f, dsize, ctx)
            elif btype == b"mdhd":
                self._p_mdhd(f, dsize, ctx)
            elif btype == b"hdlr":
                self._p_hdlr(f, dsize, ctx)
            elif btype == b"stsd":
                self._p_stsd(f, dsize, ctx)
            elif btype == b"stts":
                self._p_stts(f, dsize, ctx)
            elif btype == b"stsz":
                self._p_stsz(f, dsize, ctx)
            elif btype == b"stco":
                self._p_stco(f, dsize, ctx)
            elif btype == b"co64":
                self._p_co64(f, dsize, ctx)
            elif btype == b"stsc":
                self._p_stsc(f, dsize, ctx)
            elif btype == b"name" and ctx and dsize < 1024:
                ctx["name"] = f.read(dsize).decode("utf-8", errors="replace").strip("\x00")
            else:
                f.seek(box_end)
            if f.tell() != box_end:
                f.seek(box_end)
            self._report(f.tell())

    def _p_tkhd(self, f, size, ctx):
        data = f.read(size)
        if not ctx or len(data) < 4:
            return
        v = data[0]
        if v == 0 and len(data) >= 84:
            ctx["track_id"] = struct.unpack(">I", data[12:16])[0]
        elif v == 1 and len(data) >= 96:
            ctx["track_id"] = struct.unpack(">I", data[20:24])[0]

    def _p_mdhd(self, f, size, ctx):
        data = f.read(size)
        if not ctx or len(data) < 4:
            return
        v = data[0]
        if v == 0 and len(data) >= 24:
            ctx["timescale"] = struct.unpack(">I", data[12:16])[0]
            ctx["language"] = self._dlang(struct.unpack(">H", data[20:22])[0])
        elif v == 1 and len(data) >= 36:
            ctx["timescale"] = struct.unpack(">I", data[20:24])[0]
            ctx["language"] = self._dlang(struct.unpack(">H", data[28:30])[0])

    @staticmethod
    def _dlang(code: int) -> str:
        if code == 0 or code >= 0x7FFF:
            return "und"
        try:
            c1 = ((code >> 10) & 0x1F) + 0x60
            c2 = ((code >> 5) & 0x1F) + 0x60
            c3 = (code & 0x1F) + 0x60
            lang = chr(c1) + chr(c2) + chr(c3)
            return lang if lang.isalpha() else "und"
        except:
            return "und"

    def _p_hdlr(self, f, size, ctx):
        data = f.read(size)
        if not ctx or len(data) < 12:
            return
        ctx["handler"] = data[8:12]
        if len(data) > 24 and not ctx.get("name"):
            ctx["name"] = data[24:].decode("utf-8", errors="replace").strip("\x00").strip()

    def _p_stsd(self, f, size, ctx):
        data = f.read(size)
        if not ctx or len(data) < 16:
            return
        ctx["codec"] = data[12:16].decode("ascii", errors="replace").strip()
        if len(data) > 16:
            ctx["codec_private"] = data[16:]

    def _p_stts(self, f, size, ctx):
        data = f.read(size)
        if not ctx or len(data) < 8:
            return
        count = struct.unpack(">I", data[4:8])[0]
        entries, off = [], 8
        for _ in range(count):
            if off + 8 > len(data):
                break
            entries.append(struct.unpack(">II", data[off:off + 8]))
            off += 8
        ctx["stts"] = entries

    def _p_stsz(self, f, size, ctx):
        data = f.read(size)
        if not ctx or len(data) < 12:
            return
        ss = struct.unpack(">I", data[4:8])[0]
        count = struct.unpack(">I", data[8:12])[0]
        if ss == 0:
            sizes, off = [], 12
            for _ in range(count):
                if off + 4 > len(data):
                    break
                sizes.append(struct.unpack(">I", data[off:off + 4])[0])
                off += 4
        else:
            sizes = [ss] * count
        ctx["sample_sizes"] = sizes

    def _p_stco(self, f, size, ctx):
        data = f.read(size)
        if not ctx or len(data) < 8:
            return
        count = struct.unpack(">I", data[4:8])[0]
        offsets, off = [], 8
        for _ in range(count):
            if off + 4 > len(data):
                break
            offsets.append(struct.unpack(">I", data[off:off + 4])[0])
            off += 4
        ctx["chunk_offsets"] = offsets

    def _p_co64(self, f, size, ctx):
        data = f.read(size)
        if not ctx or len(data) < 8:
            return
        count = struct.unpack(">I", data[4:8])[0]
        offsets, off = [], 8
        for _ in range(count):
            if off + 8 > len(data):
                break
            offsets.append(struct.unpack(">Q", data[off:off + 8])[0])
            off += 8
        ctx["chunk_offsets"] = offsets

    def _p_stsc(self, f, size, ctx):
        data = f.read(size)
        if not ctx or len(data) < 8:
            return
        count = struct.unpack(">I", data[4:8])[0]
        entries, off = [], 8
        for _ in range(count):
            if off + 12 > len(data):
                break
            entries.append(struct.unpack(">III", data[off:off + 12]))
            off += 12
        ctx["stsc"] = entries

    def _build_events(self):
        with open(self.filepath, "rb") as f:
            for ti, tctx in enumerate(self._track_info):
                track = self.tracks[ti]
                ts = tctx["timescale"] or 1000
                stts, sizes = tctx["stts"], tctx["sample_sizes"]
                offsets, stsc = tctx["chunk_offsets"], tctx["stsc"]
                if not sizes or not offsets:
                    continue
                sample_times, sample_durs = [], []
                t = 0
                for count, delta in stts:
                    for _ in range(count):
                        sample_times.append(t)
                        sample_durs.append(delta)
                        t += delta
                sample_offsets = self._calc_offsets(stsc, offsets, sizes)
                n = min(len(sizes), len(sample_offsets), len(sample_times))
                for i in range(n):
                    if sizes[i] == 0:
                        continue
                    f.seek(sample_offsets[i])
                    raw = f.read(sizes[i])
                    if not raw:
                        continue
                    self.events.append(SubEvent(
                        track_number=track.number,
                        start_ms=int(sample_times[i] * 1000 / ts),
                        duration_ms=int(sample_durs[i] * 1000 / ts) if i < len(sample_durs) else 3000,
                        raw_data=raw))
                self._report(self.file_size)

    @staticmethod
    def _calc_offsets(stsc, chunk_offsets, sample_sizes) -> list:
        total = len(sample_sizes)
        result = [0] * total
        nc = len(chunk_offsets)
        if not stsc or not chunk_offsets:
            for i in range(min(total, nc)):
                result[i] = chunk_offsets[i]
            return result
        expanded = []
        for idx in range(len(stsc)):
            fc, spc = stsc[idx][0], stsc[idx][1]
            nf = stsc[idx + 1][0] if idx + 1 < len(stsc) else nc + 1
            for cn in range(fc, nf):
                if cn > nc:
                    break
                expanded.append(spc)
        si = 0
        for ci, spc in enumerate(expanded):
            if ci >= nc:
                break
            off = chunk_offsets[ci]
            for _ in range(spc):
                if si >= total:
                    break
                result[si] = off
                off += sample_sizes[si]
                si += 1
        return result


# ═══════════════════════════════════════════════════════════════
#  자막 출력
# ═══════════════════════════════════════════════════════════════

def ms_to_srt_time(ms):
    if ms < 0:
        ms = 0
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms % 1000:03d}"


def ms_to_vtt_time(ms):
    if ms < 0:
        ms = 0
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms % 1000:03d}"


def ms_to_ass_time(ms):
    if ms < 0:
        ms = 0
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    cs = (ms % 1000) // 10
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _decode_tx3g(raw):
    if len(raw) < 2:
        return ""
    tl = struct.unpack(">H", raw[:2])[0]
    return decode_text(raw[2:2 + tl]) if tl > 0 else ""


def build_srt(track, events):
    lines, seq = [], 0
    for ev in sorted(events, key=lambda e: e.start_ms):
        text = (_decode_tx3g(ev.raw_data) if track.container == "mp4"
                else decode_text(ev.raw_data)).strip()
        if not text:
            continue
        seq += 1
        dur = ev.duration_ms if ev.duration_ms > 0 else 3000
        lines += [str(seq),
                  f"{ms_to_srt_time(ev.start_ms)} --> {ms_to_srt_time(ev.start_ms + dur)}",
                  text, ""]
    return "\n".join(lines)


def build_ass(track, events):
    header = decode_text(track.codec_private) if track.codec_private else ""
    lines = header.rstrip("\n").split("\n") if header else []
    if not any("[events]" in l.lower() for l in lines):
        if not lines:
            lines = [
                "[Script Info]", "ScriptType: v4.00+",
                "PlayResX: 1920", "PlayResY: 1080", "",
                "[V4+ Styles]",
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                "Alignment, MarginL, MarginR, MarginV, Encoding",
                "Style: Default,Arial,60,&H00FFFFFF,&H000000FF,&H00000000,"
                "&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,30,30,45,1"
            ]
        lines += ["", "[Events]",
                  "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
                  "MarginV, Effect, Text"]
    for ev in sorted(events, key=lambda e: e.start_ms):
        raw = decode_text(ev.raw_data).strip()
        if not raw:
            continue
        dur = ev.duration_ms if ev.duration_ms > 0 else 3000
        st = ms_to_ass_time(ev.start_ms)
        et = ms_to_ass_time(ev.start_ms + dur)
        parts = raw.split(",", 8)
        if len(parts) >= 9:
            lines.append(
                f"Dialogue: {parts[1]},{st},{et},{parts[2]},{parts[3]},"
                f"{parts[4]},{parts[5]},{parts[6]},{parts[7]},{parts[8]}")
        else:
            lines.append(
                f"Dialogue: 0,{st},{et},Default,,0,0,0,,"
                f"{raw.replace(chr(10), '\\N')}")
    return "\n".join(lines) + "\n"


def build_ssa(track, events):
    return build_ass(track, events)


def build_vtt(track, events):
    lines, seq = ["WEBVTT", ""], 0
    for ev in sorted(events, key=lambda e: e.start_ms):
        text = decode_text(ev.raw_data).strip()
        if not text:
            continue
        seq += 1
        dur = ev.duration_ms if ev.duration_ms > 0 else 3000
        lines += [str(seq),
                  f"{ms_to_vtt_time(ev.start_ms)} --> {ms_to_vtt_time(ev.start_ms + dur)}",
                  text, ""]
    return "\n".join(lines)


def build_subtitle_file(track, events):
    c = track.codec_id
    if c == "S_TEXT/UTF8":
        return build_srt(track, events)
    elif c == "S_TEXT/ASS":
        return build_ass(track, events)
    elif c == "S_TEXT/SSA":
        return build_ssa(track, events)
    elif c == "S_TEXT/WEBVTT":
        return build_vtt(track, events)
    elif c in ("tx3g", "text", "mov_text"):
        return build_srt(track, events)
    else:
        return build_srt(track, events)


# ═══════════════════════════════════════════════════════════════
#  GUI (스크롤 가능한 트랙 목록)
# ═══════════════════════════════════════════════════════════════

class ScrollableTrackList(tk.Frame):
    """스크롤 가능한 자막 트랙 목록 위젯"""

    def __init__(self, parent, max_height=200, **kwargs):
        super().__init__(parent, bg="#1e1e2e", **kwargs)
        self.max_height = max_height

        self.canvas = tk.Canvas(self, bg="#1e1e2e", highlightthickness=0,
                                borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical",
                                       command=self.canvas.yview)
        self.inner_frame = tk.Frame(self.canvas, bg="#1e1e2e")

        self.inner_frame.bind("<Configure>", self._on_inner_configure)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar_visible = False

    def _on_inner_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        inner_h = self.inner_frame.winfo_reqheight()
        display_h = min(inner_h, self.max_height)
        self.canvas.configure(height=display_h)
        if inner_h > self.max_height:
            if not self._scrollbar_visible:
                self.scrollbar.pack(side="right", fill="y")
                self._scrollbar_visible = True
        else:
            if self._scrollbar_visible:
                self.scrollbar.pack_forget()
                self._scrollbar_visible = False

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _bind_mousewheel(self, event):
        if platform.system() == "Windows":
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        elif platform.system() == "Darwin":
            self.canvas.bind_all("<MouseWheel>", self._on_mousewheel_mac)
        else:
            self.canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
            self.canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

    def _unbind_mousewheel(self, event):
        if platform.system() == "Windows":
            self.canvas.unbind_all("<MouseWheel>")
        elif platform.system() == "Darwin":
            self.canvas.unbind_all("<MouseWheel>")
        else:
            self.canvas.unbind_all("<Button-4>")
            self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_mac(self, event):
        self.canvas.yview_scroll(int(-1 * event.delta), "units")

    def _on_mousewheel_linux(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")

    def clear(self):
        for w in self.inner_frame.winfo_children():
            w.destroy()

    def add_track(self, text: str):
        lbl = tk.Label(self.inner_frame, text=text, font=("맑은 고딕", 10),
                       bg="#45475a", fg="#cdd6f4", anchor="w", padx=12, pady=7)
        lbl.pack(fill="x", pady=1, padx=0)


class App(TkinterDnD.Tk if HAS_DND else tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Universal Subtitle Extractor v3.3")
        self.geometry("700x640")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")

        self.file_path: Optional[str] = None
        self.parser = None
        self._build_ui()

    def _build_ui(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Title.TLabel", font=("맑은 고딕", 18, "bold"),
                    background="#1e1e2e", foreground="#cdd6f4")
        s.configure("Sub.TLabel", font=("맑은 고딕", 9),
                    background="#1e1e2e", foreground="#7f849c")
        s.configure("Info.TLabel", font=("맑은 고딕", 10),
                    background="#1e1e2e", foreground="#a6adc8")
        s.configure("File.TLabel", font=("맑은 고딕", 11, "bold"),
                    background="#1e1e2e", foreground="#a6e3a1")
        s.configure("Big.TButton", font=("맑은 고딕", 12, "bold"), padding=12)
        s.configure("Bar.Horizontal.TProgressbar",
                    troughcolor="#313244", background="#89b4fa", thickness=22)

        # ── 제목 ──
        ttk.Label(self, text="Universal Subtitle Extractor",
                  style="Title.TLabel").pack(pady=(20, 2))
        dnd_status = ("드래그 앤 드롭 지원 ✅" if HAS_DND
                      else "pip install tkinterdnd2 → 드래그 앤 드롭 활성화")
        ttk.Label(self,
                  text=f"MKV · MP4 내장 자막을 원본 형식 그대로 추출  |  {dnd_status}",
                  style="Sub.TLabel").pack(pady=(0, 12))

        # ── 드롭 영역 ──
        self.drop_frame = tk.Frame(self, bg="#313244",
                                   highlightbackground="#585b70",
                                   highlightthickness=2)
        self.drop_frame.pack(padx=30, fill="x", ipady=20)
        drop_text = ("📂  MKV / MP4 파일을 여기에 드래그 앤 드롭\n또는 아래 버튼을 클릭하세요"
                     if HAS_DND
                     else "📂  아래 버튼을 클릭하여 파일을 선택하세요")
        self.drop_label = tk.Label(self.drop_frame, text=drop_text,
                                   font=("맑은 고딕", 11), bg="#313244",
                                   fg="#a6adc8", justify="center")
        self.drop_label.pack(pady=(14, 8))
        self.btn_open = ttk.Button(self.drop_frame, text="동영상 파일 열기",
                                   style="Big.TButton", command=self._open_file)
        self.btn_open.pack(pady=(0, 14))
        self.drop_label.bind("<Button-1>", lambda e: self._open_file())
        self.drop_frame.bind("<Button-1>", lambda e: self._open_file())

        if HAS_DND:
            for widget in (self.drop_frame, self.drop_label):
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind("<<Drop>>", self._on_drop)
                widget.dnd_bind("<<DragEnter>>", self._on_drag_enter)
                widget.dnd_bind("<<DragLeave>>", self._on_drag_leave)

        # ── 파일 정보 ──
        self.file_label = ttk.Label(self, text="", style="File.TLabel")
        self.file_label.pack(pady=(14, 2))
        self.format_label = ttk.Label(self, text="", style="Info.TLabel")
        self.format_label.pack(pady=(0, 4))

        # ── 트랙 헤더 ──
        self.track_header = ttk.Label(self, text="", style="Info.TLabel")

        # ── 스크롤 가능한 트랙 목록 ──
        self.track_list = ScrollableTrackList(self, max_height=200)

        # ── 프로그래스 ──
        self.progress = ttk.Progressbar(self, orient="horizontal", length=640,
                                        mode="determinate",
                                        style="Bar.Horizontal.TProgressbar")
        self.progress_label = ttk.Label(self, text="", style="Info.TLabel")

        # ── 크레딧 (추출 버튼보다 먼저 pack → 가장 아래에 위치) ──
        self.credit_label = tk.Label(
            self, text="Developed by DOCKERNOIN with Claude AI",
            font=("맑은 고딕", 8), bg="#1e1e2e", fg="#585b70")
        self.credit_label.pack(side="bottom", pady=(0, 8))

        # ── 추출 버튼 (크레딧 바로 위에 위치) ──
        self.btn_extract = tk.Button(
            self, text="자막 추출",
            font=("맑은 고딕", 11, "bold"),
            bg="#a6e3a1", fg="#1e1e2e",
            activebackground="#94e2d5", activeforeground="#1e1e2e",
            relief="flat", cursor="hand2",
            command=self._on_extract)
        # ※ 여기서는 pack하지 않음 — 파일 로드 후 _load_file에서 pack

    # ── DnD 이벤트 ──
    def _on_drop(self, event):
        raw = event.data.strip()
        path = (raw.split("}")[0].strip("{}")
                if raw.startswith("{") else raw.split()[0])
        if path.lower().endswith((".mkv", ".mp4", ".m4v")):
            self._on_drag_leave(None)
            self._load_file(path)
        else:
            self._on_drag_leave(None)
            messagebox.showwarning("지원하지 않는 파일",
                                   "MKV 또는 MP4 파일만 지원합니다.")

    def _on_drag_enter(self, event):
        self.drop_frame.config(bg="#45475a", highlightbackground="#89b4fa")
        self.drop_label.config(bg="#45475a", fg="#89b4fa",
                               text="📥  여기에 놓으세요!")

    def _on_drag_leave(self, event):
        self.drop_frame.config(bg="#313244", highlightbackground="#585b70")
        self.drop_label.config(
            bg="#313244", fg="#a6adc8",
            text="📂  MKV / MP4 파일을 여기에 드래그 앤 드롭\n또는 아래 버튼을 클릭하세요")

    # ── 파일 열기 ──
    def _open_file(self):
        path = filedialog.askopenfilename(
            title="동영상 파일 선택",
            filetypes=[("지원 동영상", "*.mkv *.mp4 *.m4v"),
                       ("MKV", "*.mkv"), ("MP4", "*.mp4 *.m4v"),
                       ("모든 파일", "*.*")])
        if path:
            self._load_file(path)

    def _load_file(self, path):
        self.file_path = path
        ext = os.path.splitext(path)[1].lower()
        filename = os.path.basename(path)
        size_mb = os.path.getsize(path) / (1024 * 1024)

        self.file_label.config(text=f"📄  {filename}")
        ct = "MKV (Matroska)" if ext == ".mkv" else "MP4 (MPEG-4)"
        self.format_label.config(
            text=f"포맷: {ct}   |   크기: {size_mb:.1f} MB")
        self.drop_label.config(text=f"✅  {filename}")

        # 이전 결과 숨기기
        self.track_header.pack_forget()
        self.track_list.pack_forget()
        self.track_list.clear()
        self.btn_extract.pack_forget()
        self.progress.pack_forget()
        self.progress_label.pack_forget()

        try:
            if ext == ".mkv":
                self.parser = MKVParser(path)
            else:
                self.parser = MP4Parser(path)
            self.parser.parse_tracks_only()
        except Exception as e:
            messagebox.showerror("오류", f"파일 파싱 실패:\n{e}")
            return

        tracks = self.parser.tracks
        if not tracks:
            messagebox.showwarning("알림", "내장 자막 트랙이 없습니다.")
            return

        # 트랙 헤더
        self.track_header.config(
            text=f"🗂  내장 자막 트랙: {len(tracks)}개",
            font=("맑은 고딕", 11, "bold"), foreground="#89b4fa")
        self.track_header.pack(anchor="w", padx=30, pady=(10, 4))

        # 트랙 목록
        self.track_list.clear()
        for i, t in enumerate(tracks):
            lang_name = LANG_NAMES.get(t.language, t.language)
            name_part = f'  "{t.name}"' if t.name else ""
            txt = (f"  #{i + 1}   {t.language} ({lang_name})   "
                   f"|   원본: {t.format_name} → {t.extension}{name_part}")
            self.track_list.add_track(txt)

        self.track_list.pack(padx=30, fill="x", pady=(0, 4))

        # ★ 추출 버튼: 크레딧 바로 위에 pack
        self.btn_extract.pack(side="bottom", pady=10, ipady=8,
                              fill="x", padx=20,
                              before=self.credit_label)

    # ── 추출 ──
    def _on_extract(self):
        """추출 버튼 클릭 핸들러"""
        if not self.file_path or not self.parser:
            return
        self.btn_extract.config(state="disabled")
        self.progress["value"] = 0
        self.progress.pack(padx=30, pady=(6, 2))
        self.progress_label.config(text="자막 데이터를 읽는 중...")
        self.progress_label.pack()
        threading.Thread(target=self._extract_worker, daemon=True).start()

    def _extract_worker(self):
        try:
            ext = os.path.splitext(self.file_path)[1].lower()
            if ext == ".mkv":
                self.parser = MKVParser(self.file_path,
                                        progress_cb=self._update_progress)
            else:
                self.parser = MP4Parser(self.file_path,
                                        progress_cb=self._update_progress)
            self.parser.parse_tracks_only()
            self.parser.parse_all()

            base_name = os.path.splitext(
                os.path.basename(self.file_path))[0]
            # 동영상 파일과 같은 위치에 '동영상명_subs' 폴더 생성
            output_dir = os.path.join(
                os.path.dirname(self.file_path),
                f"{base_name}_subs")
            os.makedirs(output_dir, exist_ok=True)

            # ★ 언어별 그룹핑
            lang_groups = {}
            for track in self.parser.tracks:
                lang = ("undefined" if track.language == "und"
                        else track.language)
                if lang not in lang_groups:
                    lang_groups[lang] = []
                lang_groups[lang].append(track)

            # ★ 트랙 분류
            track_plan = []
            for lang, tracks in lang_groups.items():
                if len(tracks) == 1:
                    tag = self._get_meaningful_tag(tracks[0])
                    track_plan.append((tracks[0], tag, True))
                else:
                    seen_tags = set()
                    for track in tracks:
                        tag = self._get_meaningful_tag(track)
                        tag_key = f"{lang}{tag}"
                        if tag_key not in seen_tags:
                            track_plan.append((track, tag, True))
                            seen_tags.add(tag_key)
                        else:
                            track_plan.append((track, tag, False))

            # ★ 실제 추출
            results, used, skipped = [], set(), 0
            for track, tag, should_extract in track_plan:
                if not should_extract:
                    skipped += 1
                    continue

                tevs = [e for e in self.parser.events
                        if e.track_number == track.number]
                if not tevs:
                    continue

                content = build_subtitle_file(track, tevs)
                se = track.extension
                lang = ("undefined" if track.language == "und"
                        else track.language)

                out_name = f"{base_name}_{lang}{tag}{se}"
                c = 1
                while out_name in used:
                    out_name = f"{base_name}_{lang}{tag}_{c}{se}"
                    c += 1
                used.add(out_name)

                with open(os.path.join(output_dir, out_name),
                          "w", encoding="utf-8-sig") as f:
                    f.write(content)
                results.append((out_name, track.format_name))

            self.after(0, lambda: self._on_done(results, skipped))
        except Exception as e:
            self.after(0, lambda: self._on_error(str(e)))

    def _get_meaningful_tag(self, track) -> str:
        """트랙 이름에서 의미 있는 태그만 추출한다.
        단순 언어명 반복이면 빈 문자열 반환."""
        if not track.name:
            return ""

        name_stripped = track.name.strip()
        name_lower = name_stripped.lower()

        # 1순위: 특수 목적 태그
        if "sdh" in name_lower:
            return "_SDH"
        if "forced" in name_lower or "force" in name_lower:
            return "_Forced"
        if "commentary" in name_lower or "comment" in name_lower:
            return "_Commentary"
        if name_lower == "cc" or "closed caption" in name_lower:
            return "_CC"
        if "sign" in name_lower:
            return "_Signs"
        if "song" in name_lower or "lyric" in name_lower:
            return "_Songs"

        # 2순위: 언어 변형 태그
        # 중국어
        if ("traditional" in name_lower or "繁體" in name_lower
                or "繁体" in name_lower):
            return "_Traditional"
        if ("simplified" in name_lower or "简体" in name_lower
                or "簡體" in name_lower):
            return "_Simplified"
        if ("cantonese" in name_lower or "粵語" in name_lower
                or "广东话" in name_lower):
            return "_Cantonese"
        if ("mandarin" in name_lower or "普通話" in name_lower
                or "普通话" in name_lower):
            return "_Mandarin"

        # 스페인어
        if ("latin" in name_lower or "latinoam" in name_lower
                or "hispanoam" in name_lower):
            return "_Latin"
        if "castilian" in name_lower or "castellano" in name_lower:
            return "_Castilian"
        if ("españa" in name_lower or "spain" in name_lower
                or "espanol (espana" in name_lower
                or "español (españa" in name_lower):
            return "_Spain"
        if "mexican" in name_lower or "méxico" in name_lower:
            return "_Mexico"

        # 포르투갈어
        if "brasil" in name_lower or "brazil" in name_lower:
            return "_Brazil"
        if "portugal" in name_lower or "europeu" in name_lower:
            return "_Portugal"

        # 프랑스어
        if ("canada" in name_lower or "canadien" in name_lower
                or "québec" in name_lower or "quebec" in name_lower):
            return "_Canada"
        if "france" in name_lower or "parisian" in name_lower:
            return "_France"
        if "belgi" in name_lower:
            return "_Belgium"
        if "suisse" in name_lower or "swiss" in name_lower:
            return "_Swiss"

        # 영어
        if "british" in name_lower or name_lower == "uk":
            return "_UK"
        if "american" in name_lower or name_lower == "us":
            return "_US"
        if "australian" in name_lower:
            return "_Australian"

        # 기타 지역 변형
        if "european" in name_lower or "iberian" in name_lower:
            return "_European"

        # 3순위: 단순 언어명이면 무시
        ignore_names = set()

        for v in LANG_NAMES.values():
            ignore_names.add(v.lower())

        for code in LANG_NAMES.keys():
            ignore_names.add(code.lower())

        english_names = {
            "korean", "english", "japanese", "chinese", "spanish",
            "french", "german", "portuguese", "italian", "russian",
            "arabic", "hindi", "thai", "vietnamese", "indonesian",
            "malay", "danish", "czech", "dutch", "finnish", "greek",
            "hebrew", "hungarian", "norwegian", "polish", "romanian",
            "swedish", "turkish", "ukrainian", "bulgarian", "croatian",
            "slovenian", "serbian", "catalan", "filipino", "latvian",
            "lithuanian", "estonian", "persian", "tamil", "telugu",
            "bengali", "urdu", "swahili", "albanian", "bosnian",
            "macedonian", "icelandic", "georgian", "armenian",
            "azerbaijani", "kazakh", "uzbek", "mongolian", "nepali",
            "sinhala", "khmer", "lao", "burmese", "amharic",
            "somali", "yoruba", "igbo", "zulu", "afrikaans",
            "slovak", "galician", "basque", "welsh", "irish",
            "maltese", "luxembourgish",
        }
        for n in english_names:
            ignore_names.add(n)

        native_names = {
            "한국어", "영어", "日本語", "にほんご",
            "中文", "中文(简体)", "中文(繁體)",
            "español", "français", "deutsch", "português",
            "italiano", "русский", "العربية", "हिन्दी", "हिंदी",
            "ไทย", "tiếng việt", "bahasa indonesia",
            "bahasa malaysia", "bahasa melayu", "dansk",
            "čeština", "česky", "nederlands", "suomi",
            "ελληνικά", "ελληνικα", "עברית", "magyar",
            "norsk", "norsk bokmål", "polski", "română", "românã",
            "svenska", "türkçe", "türkce", "українська",
            "украïнська", "български", "srpski", "српски",
            "hrvatski", "slovenščina", "slovenčina", "slovensky",
            "slovenský", "català", "filipino", "tagalog",
            "latviešu", "latvian", "lietuvių", "lietuviu",
            "eesti", "فارسی", "فارسي", "தமிழ்", "తెలుగు",
            "বাংলা", "اردو", "kiswahili", "shqip",
            "bosanski", "македонски", "íslenska",
            "ქართული", "հայերեն", "azərbaycan",
            "қазақ", "oʻzbek", "монгол", "नेपाली",
            "සිංහල", "ភាសាខ្មែរ", "ລາວ", "မြန်မာ",
            "አማርኛ", "soomaali", "yorùbá", "igbo",
            "isizulu", "afrikaans", "slovenský", "galego",
            "euskara", "cymraeg", "gaeilge", "malti",
            "lëtzebuergesch",
        }
        for n in native_names:
            ignore_names.add(n.lower())

        if name_lower in ignore_names:
            return ""

        # 4순위: 알 수 없는 이름 → 그대로 태그로 사용
        safe_name = re.sub(r'[\\/:*?"<>|]', '', name_stripped)
        if safe_name:
            return f"_{safe_name}"

        return ""

    def _update_progress(self, pct):
        self.after(0, lambda: self._set_progress(pct))

    def _set_progress(self, pct):
        self.progress["value"] = pct
        self.progress_label.config(text=f"자막 데이터를 읽는 중... {pct}%")

    def _on_done(self, results, skipped=0):
        self.progress["value"] = 100
        self.progress_label.config(text="완료!")
        self.btn_extract.config(state="normal")
        self._play_sound()
        if results:
            fl = "\n".join(f"  • {n}  ({fmt})" for n, fmt in results)
            skip_msg = (f"\n\n⏭️ 중복 자막 {skipped}개는 건너뛰었습니다."
                        if skipped > 0 else "")
            messagebox.showinfo(
                "추출 성공!",
                f"자막 파일 {len(results)}개를 추출했습니다.\n\n"
                f"{fl}{skip_msg}\n\n"
                f"저장 위치:\n{os.path.dirname(self.file_path)}")
        else:
            messagebox.showwarning("알림", "추출할 자막 데이터가 없습니다.")

    def _on_error(self, msg):
        self.progress_label.config(text="오류 발생")
        self.btn_extract.config(state="normal")
        messagebox.showerror("추출 오류", f"자막 추출 중 오류:\n{msg}")

    @staticmethod
    def _play_sound():
        try:
            if platform.system() == "Windows":
                import winsound
                winsound.MessageBeep(winsound.MB_OK)
            elif platform.system() == "Darwin":
                os.system("afplay /System/Library/Sounds/Glass.aiff &")
            else:
                os.system(
                    "paplay /usr/share/sounds/freedesktop/stereo/"
                    "complete.oga 2>/dev/null &")
        except:
            print("\a")


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = App()
    app.mainloop()
