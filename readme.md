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

사용 방법
프로그램을 실행합니다.
동영상 파일을 드래그 앤 드롭하거나 "동영상 파일 열기" 버튼으로 선택합니다.
내장 자막 트랙 목록이 표시됩니다.
"자막 추출" 버튼을 클릭하면 원본 동영상과 같은 폴더에 자막 파일이 저장됩니다.
추출 파일명 규칙
기본 형식: 원본파일명_언어코드.확장자

상황	파일명 예시
기본	TopGun_kor.srt
특수 태그	TopGun_eng_SDH.srt
언어 변형	TopGun_chi_Traditional.ass
알 수 없는 언어	TopGun_undefined.srt
자동 처리 규칙
중복 자막 제거
같은 언어 + 같은 태그의 자막이 여러 개 있으면 첫 번째만 추출하고 나머지는 건너뜁니다.

태그 자동 인식
구분	태그
특수 목적	SDH, Forced, Commentary, CC, Signs, Songs
중국어	Traditional, Simplified, Cantonese, Mandarin
스페인어	Latin, Castilian, Spain, Mexico
포르투갈어	Brazil, Portugal
프랑스어	Canada, France, Belgium, Swiss
영어	UK, US, Australian
트랙 이름이 단순 언어명(English, Korean, 日本語 등)인 경우 태그로 추가하지 않습니다.

요구 사항
Python 3.9+
tkinterdnd2 (드래그 앤 드롭 기능, 선택사항)
License
MIT License

Credits
Developed by DOCKERNOIN with Claude AI
