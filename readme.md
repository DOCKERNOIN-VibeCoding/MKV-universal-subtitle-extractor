# Universal Subtitle Extractor v3.2

MKV / MP4 동영상 파일에 내장된 자막을 추출하는 순수 Python GUI 프로그램입니다.
FFmpeg이나 MKVToolNix 같은 외부 도구 없이 단독 실행됩니다.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

## 지원 형식

**입력**: MKV (`.mkv`), MP4 (`.mp4`, `.m4v`)

**추출 가능한 자막**

| 컨테이너 | 코덱 | 추출 형식 |
|-----------|-------|-----------|
| MKV | S_TEXT/UTF8 | `.srt` |
| MKV | S_TEXT/ASS | `.ass` |
| MKV | S_TEXT/SSA | `.ssa` |
| MKV | S_TEXT/WEBVTT | `.vtt` |
| MP4 | tx3g / mov_text | `.srt` |

> ⚠️ PGS(블루레이), VobSub(DVD) 등 **이미지 기반 자막은 지원하지 않습니다.**

## 설치 및 실행

### Python으로 실행

```bash
# 필수
pip install tkinterdnd2

# 실행
python universal_subtitle_extractor.py
