# Universal Subtitle Extractor v3.2

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🇰🇷 한국어

### 프로그램 개요

MKV / MP4 동영상 파일에 내장된 자막을 추출하는 순수 Python GUI 프로그램입니다.
FFmpeg이나 MKVToolNix 같은 외부 도구 없이 단독 실행됩니다.

### 지원 형식

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

### 설치 및 실행

#### Python으로 실행

```bash
# 드래그 앤 드롭 기능 활성화 (선택사항)
pip install tkinterdnd2

# 실행
python universal_subtitle_extractor.py
```

#### EXE 빌드 (Windows)

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --icon=subtitle_extractor.ico --name "SubtitleExtractor" universal_subtitle_extractor.py
```

빌드 결과: `dist/SubtitleExtractor.exe`

### 사용 방법

1. 프로그램을 실행합니다.
2. 동영상 파일을 **드래그 앤 드롭**하거나 **"동영상 파일 열기"** 버튼으로 선택합니다.
3. 내장 자막 트랙 목록이 표시됩니다.
4. **"자막 추출"** 버튼을 클릭하면 원본 동영상과 같은 위치에 `동영상명_subs` 폴더가 생성되고, 그 안에 자막 파일이 저장됩니다.
5. 추출 완료 시 알림음과 함께 결과 팝업이 표시됩니다.

### 추출 파일명 규칙

추출된 자막은 원본 동영상과 같은 위치의 `동영상명_subs` 폴더 안에 저장됩니다.

기본 형식: `원본파일명_언어코드.확장자`

| 상황 | 저장 위치 / 파일명 예시 |
|------|-------------|
| 기본 | `탑건매버릭_subs/탑건매버릭_kor.srt` |
| 특수 태그 (SDH, Forced 등) | `탑건매버릭_subs/탑건매버릭_eng_SDH.srt` |
| 언어 변형 (간체/번체 등) | `탑건매버릭_subs/탑건매버릭_chi_Traditional.ass` |
| 알 수 없는 언어 (und) | `탑건매버릭_subs/탑건매버릭_undefined.srt` |

### 자동 처리 규칙

#### 중복 자막 제거

같은 언어 + 같은 태그의 자막이 여러 개 있으면 **첫 번째만 추출**하고 나머지는 건너뜁니다.

#### 태그 자동 인식

트랙 이름에서 아래 태그를 자동으로 감지하여 파일명에 반영합니다.

| 구분 | 인식되는 태그 |
|------|---------------|
| 특수 목적 | SDH, Forced, Commentary, CC, Signs, Songs |
| 중국어 변형 | Traditional, Simplified, Cantonese, Mandarin |
| 스페인어 변형 | Latin, Castilian, Spain, Mexico |
| 포르투갈어 변형 | Brazil, Portugal |
| 프랑스어 변형 | Canada, France, Belgium, Swiss |
| 영어 변형 | UK, US, Australian |

트랙 이름이 단순 언어명(English, Korean, 日本語 등)인 경우 태그로 추가하지 않습니다.

#### 드래그 앤 드롭

`tkinterdnd2` 패키지가 설치되어 있으면 드래그 앤 드롭이 활성화됩니다. 미설치 시에도 "동영상 파일 열기" 버튼으로 정상 사용 가능합니다.

### 요구 사항

- Python 3.9+
- `tkinterdnd2` (드래그 앤 드롭 기능, 선택사항)

---

## 🇺🇸 English

### Overview

A pure Python GUI program that extracts embedded subtitles from MKV / MP4 video files.
No external tools required (no FFmpeg, no MKVToolNix).

### Supported Formats

**Input**: MKV (`.mkv`), MP4 (`.mp4`, `.m4v`)

**Extractable Subtitles**

| Container | Codec | Output |
|-----------|-------|--------|
| MKV | S_TEXT/UTF8 | `.srt` |
| MKV | S_TEXT/ASS | `.ass` |
| MKV | S_TEXT/SSA | `.ssa` |
| MKV | S_TEXT/WEBVTT | `.vtt` |
| MP4 | tx3g / mov_text | `.srt` |

> ⚠️ Image-based subtitles (PGS, VobSub, DVB) are **not supported**.

### Installation & Running

#### Run with Python

```bash
# Enable drag & drop (optional)
pip install tkinterdnd2

# Run
python universal_subtitle_extractor.py
```

#### Build EXE (Windows)

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --icon=subtitle_extractor.ico --name "SubtitleExtractor" universal_subtitle_extractor.py
```

Output: `dist/SubtitleExtractor.exe`

### How to Use

1. Launch the program.
2. **Drag & drop** a video file or click the **"동영상 파일 열기" (Open Video File)** button.
3. The list of embedded subtitle tracks will be displayed.
4. Click the **"자막 추출" (Extract Subtitles)** button. A `VideoName_subs` folder is created in the same location as the original video, and the subtitle files are saved inside it.
5. A notification sound and result popup will appear when extraction is complete.

### Output Filename Rules

Extracted subtitles are saved inside a `VideoName_subs` folder located next to the original video.

Format: `OriginalFileName_LanguageCode.extension`

| Case | Location / Filename Example |
|------|------------------|
| Basic | `TopGun_subs/TopGun_kor.srt` |
| Special tag (SDH, Forced, etc.) | `TopGun_subs/TopGun_eng_SDH.srt` |
| Language variant | `TopGun_subs/TopGun_chi_Traditional.ass` |
| Unknown language (und) | `TopGun_subs/TopGun_undefined.srt` |

### Automatic Processing Rules

#### Duplicate Subtitle Removal

When multiple subtitle tracks share the same language + tag combination, only the **first track is extracted** and the rest are skipped.

#### Auto Tag Detection

Tags are automatically detected from track names and appended to the output filename.

| Category | Detected Tags |
|----------|---------------|
| Special Purpose | SDH, Forced, Commentary, CC, Signs, Songs |
| Chinese Variants | Traditional, Simplified, Cantonese, Mandarin |
| Spanish Variants | Latin, Castilian, Spain, Mexico |
| Portuguese Variants | Brazil, Portugal |
| French Variants | Canada, France, Belgium, Swiss |
| English Variants | UK, US, Australian |

Track names that are simple language names (e.g., English, Korean, 日本語) are ignored and not added as tags.

#### Drag & Drop

Drag & drop is enabled when `tkinterdnd2` is installed. The program works normally without it using the file open button.

### Requirements

- Python 3.9+
- `tkinterdnd2` (for drag & drop, optional)

---

## License

MIT License

## Credits

Developed by **DOCKERNOIN** with **Claude AI**
