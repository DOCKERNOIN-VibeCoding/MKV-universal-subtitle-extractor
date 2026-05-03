"""
CC 말풍선 아이콘 생성 - Pillow로 직접 그리기
"""

from PIL import Image, ImageDraw, ImageFont
import os


def create_cc_icon():
    size = 512
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # ── 좌표 설정 ──
    pad = 30
    box_left = pad
    box_top = pad
    box_right = size - pad
    box_bottom = 390
    radius = 50
    outline_w = 18

    # 말풍선 꼬리 좌표
    tail_points = [
        (box_left + 60, box_bottom),
        (box_left + 30, size - pad - 10),
        (box_left + 160, box_bottom),
    ]

    # ── 1) 검은색 외곽선 (그림자 겸 테두리) ──
    # 꼬리 외곽
    tail_outline = [
        (tail_points[0][0] - 10, tail_points[0][1]),
        (tail_points[1][0] - 10, tail_points[1][1] + 10),
        (tail_points[2][0] + 10, tail_points[2][1]),
    ]
    draw.polygon(tail_outline, fill=(40, 40, 40, 255))

    # 박스 외곽
    draw.rounded_rectangle(
        [(box_left - outline_w//2, box_top - outline_w//2),
         (box_right + outline_w//2, box_bottom + outline_w//2)],
        radius=radius + 10,
        fill=(40, 40, 40, 255)
    )

    # ── 2) 회색 본체 ──
    # 꼬리 본체
    draw.polygon(tail_points, fill=(200, 200, 200, 255))

    # 박스 본체
    draw.rounded_rectangle(
        [(box_left, box_top), (box_right, box_bottom)],
        radius=radius,
        fill=(200, 200, 200, 255)
    )

    # ── 3) CC 텍스트 ──
    font = None
    font_size = 240
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except:
                continue
    if font is None:
        font = ImageFont.load_default()

    # 빨간 C (왼쪽)
    c1_x = 72
    c1_y = 60
    draw.text((c1_x, c1_y), "C", fill=(220, 60, 60, 255), font=font)

    # 파란 C (오른쪽)
    c2_x = 248
    c2_y = 60
    draw.text((c2_x, c2_y), "C", fill=(50, 150, 230, 255), font=font)

    # ── 4) 하단 대시 줄 (자막 라인 느낌) ──
    dash_y = 335
    dash_h = 18
    dash_r = 9
    dash_color = (70, 70, 70, 255)
    dashes = [
        (130, dash_y, 210, dash_y + dash_h),
        (225, dash_y, 305, dash_y + dash_h),
        (320, dash_y, 400, dash_y + dash_h),
    ]
    for d in dashes:
        draw.rounded_rectangle(d, radius=dash_r, fill=dash_color)

    # ── ICO 저장 ──
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48),
                  (64, 64), (128, 128), (256, 256)]
    icons = [img.resize(s, Image.LANCZOS) for s in icon_sizes]

    ico_path = "subtitle_extractor.ico"
    icons[-1].save(
        ico_path,
        format="ICO",
        sizes=[(i.width, i.height) for i in icons],
        append_images=icons[:-1]
    )

    # 미리보기 PNG
    img.save("subtitle_extractor_preview.png", format="PNG")

    print(f"✅ 아이콘 생성 완료!")
    print(f"   ICO: {ico_path}")
    print(f"   미리보기: subtitle_extractor_preview.png")


if __name__ == "__main__":
    create_cc_icon()
