# -*- coding: utf-8 -*-
"""帆板控制系统 · 洞洞板布局示意图（带排版审计）"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1500, 1120
C_BG = (255, 255, 255)
C_TXT, C_GRAY = (35, 35, 35), (150, 155, 165)
C_HOLE = (228, 231, 236)

F_TITLE = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 30)
F_SEC = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 20)
F_LAB = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
F_SM = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 14)

# 洞洞板：10 x 15 cm，孔距 2.54mm → 约 39 x 59 孔
PITCH = 15
NX, NY = 39, 59
BX, BY = 90, 120

img = Image.new("RGB", (W, H), C_BG)
d = ImageDraw.Draw(img)
_texts = []


def txt(x, y, s, font, fill=C_TXT, anchor="la"):
    d.multiline_text((x, y), s, font=font, fill=fill, anchor=anchor, spacing=3)
    _texts.append((d.multiline_textbbox((x, y), s, font=font, anchor=anchor, spacing=3),
                   s.replace("\n", "/")))


def gx(n):  # 孔列 -> px
    return BX + n * PITCH


def gy(n):  # 孔行 -> px
    return BY + n * PITCH


def chip(c1, r1, c2, r2, name, pins=8, color=(255, 236, 179), edge=(176, 132, 20)):
    """DIP-8 竖直放置：左右各 4 脚"""
    x1, y1, x2, y2 = gx(c1), gy(r1), gx(c2), gy(r2)
    d.rounded_rectangle([x1, y1, x2, y2], radius=4, fill=color, outline=edge, width=2)
    # 缺口
    d.arc([x1 + 4, y1 - 5, x2 - 4, y1 + 7], 0, 180, fill=edge, width=2)
    for k in range(4):
        yy = gy(r1 + 2 + k * 3)
        d.ellipse([x1 - 4, yy - 3, x1 + 2, yy + 3], fill=(90, 90, 90))
        d.ellipse([x2 - 2, yy - 3, x2 + 4, yy + 3], fill=(90, 90, 90))
    txt((x1 + x2) / 2, (y1 + y2) / 2, name, F_SM, C_TXT, "mm")
    return (x1, y1, x2, y2)


def block(c1, r1, c2, r2, label, color, edge, fs=F_SM):
    x1, y1, x2, y2 = gx(c1), gy(r1), gx(c2), gy(r2)
    d.rounded_rectangle([x1, y1, x2, y2], radius=3, fill=color, outline=edge, width=2)
    if label:
        txt((x1 + x2) / 2, (y1 + y2) / 2, label, fs, C_TXT, "mm")
    return (x1, y1, x2, y2)


# ---------- 板 ----------
d.rectangle([BX - 8, BY - 8, gx(NX - 1) + 8, gy(NY - 1) + 8],
            fill=(248, 249, 250), outline=(120, 125, 135), width=3)
for i in range(NX):
    for j in range(NY):
        x, y = gx(i), gy(j)
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=C_HOLE)

txt(W // 2, 26, "洞洞板布局示意（10 × 15 cm，约 39 × 59 孔）", F_TITLE, C_TXT, "ma")
txt(W // 2, 70, "按这个摆位，信号从左往右走，地线在底部集中", F_SM, C_GRAY, "ma")

# ---------- 电源区（左上） ----------
d.rounded_rectangle([gx(0), gy(0), gx(12), gy(9)], radius=3,
                    fill=(253, 237, 237), outline=(190, 80, 80), width=2)
txt(gx(6), gy(1), "电源入口区", F_SM, (150, 50, 50), "ma")
block(1, 2, 4, 3, "DC-005", (255, 245, 230), (200, 130, 30))
block(5, 2, 7, 3, "保险丝", (255, 245, 230), (200, 130, 30))
block(8, 2, 11, 3, "开关", (255, 245, 230), (200, 130, 30))
block(1, 5, 3, 6, "LED", (255, 240, 240), (190, 80, 80))
block(4, 5, 6, 6, "1k", (240, 240, 250), (100, 100, 160))
block(7, 5, 12, 8, "470µF\n+0.1µF", (253, 237, 237), (190, 80, 80), F_SM)

# ---------- 7805 ----------
d.rounded_rectangle([gx(14), gy(0), gx(20), gy(8)], radius=3,
                    fill=(235, 245, 235), outline=(60, 140, 80), width=2)
txt(gx(17), gy(0) - 18, "7805", F_SM, (40, 110, 60), "mm")
block(15, 2, 19, 4, "7805", (220, 240, 220), (60, 140, 80))
block(15, 5, 17, 6, "0.33µF", (240, 240, 250), (100, 100, 160))
block(18, 5, 20, 6, "10µF", (240, 240, 250), (100, 100, 160))

# ---------- 2.5V 基准 + 跟随器 ----------
d.rounded_rectangle([gx(22), gy(0), gx(31), gy(14)], radius=3,
                    fill=(245, 240, 255), outline=(110, 80, 190), width=2)
txt(gx(26), gy(0) - 18, "2.5V 基准 + 缓冲", F_SM, (85, 55, 165), "mm")
block(23, 2, 24, 3, "10k", (240, 240, 250), (100, 100, 160))
block(25, 2, 26, 3, "10k", (240, 240, 250), (100, 100, 160))
chip(27, 2, 30, 9, "A1")
txt(gx(28.5), gy(10), "→ 2V5", F_SM, (85, 55, 165), "ma")

# ---------- 三片 LM358 ----------
LX = 34
chip(LX, 1, LX + 3, 8, "A2")
txt(gx(LX + 1.5), gy(9), "P1 跟随\n→ V_set", F_SM, C_TXT, "ma")

chip(LX, 11, LX + 3, 18, "A3")
txt(gx(LX + 1.5), gy(19), "P2 跟随\n→ V_fb", F_SM, C_TXT, "ma")

chip(LX, 21, LX + 3, 28, "A4")
txt(gx(LX + 1.5), gy(29), "减法器", F_SM, C_TXT, "ma")

# ---------- 比较器 ----------
chip(LX, 33, LX + 3, 40, "A8", color=(255, 224, 224), edge=(180, 60, 60))
txt(gx(LX + 1.5), gy(41), "PWM", F_SM, (150, 40, 40), "ma")

chip(LX, 44, LX + 3, 51, "A7", color=(255, 224, 224), edge=(180, 60, 60))
txt(gx(LX + 1.5), gy(52), "三角波\n比较", F_SM, (150, 40, 40), "ma")

# ---------- 中列：减法器/PI/积分器 ----------
MX = 22
chip(MX, 17, MX + 3, 24, "A5")
txt(gx(MX + 1.5), gy(25), "PI 控制器", F_SM, C_TXT, "ma")
block(MX - 4, 18, MX - 2, 19, "100k", (240, 240, 250), (100, 100, 160))
block(MX - 4, 21, MX - 2, 22, "22k", (240, 240, 250), (100, 100, 160))
block(MX - 4, 23, MX - 2, 24, "6.8µF", (255, 245, 220), (200, 150, 40))

chip(MX, 29, MX + 3, 36, "A6")
txt(gx(MX + 1.5), gy(37), "三角波积分\n15k / 10nF", F_SM, C_TXT, "ma")

# 减法器 4 个 10k
for k, (cx, cy) in enumerate([(MX - 2, 13), (MX + 2, 13), (MX - 2, 15), (MX + 2, 15)]):
    block(cx, cy, cx + 1, cy, "10k", (240, 240, 250), (100, 100, 160))
txt(gx(MX), gy(10.6), "4×10k 1%", F_SM, (85, 55, 165), "ma")

# ---------- 功率级（右下） ----------
d.rounded_rectangle([gx(8), gy(42), gx(30), gy(52)], radius=3,
                    fill=(240, 250, 240), outline=(50, 120, 70), width=2)
txt(gx(19), gy(42) - 18, "功率级", F_SM, (40, 110, 60), "mm")
block(10, 44, 13, 46, "IRLZ44N", (215, 245, 215), (50, 120, 70))
block(14, 44, 16, 45, "100Ω", (240, 240, 250), (100, 100, 160))
block(17, 44, 19, 45, "10k", (240, 240, 250), (100, 100, 160))
block(21, 44, 24, 46, "1N4007", (255, 245, 230), (200, 130, 30))
block(10, 48, 14, 50, "风扇座", (255, 245, 230), (200, 130, 30))
block(16, 48, 20, 50, "100µF", (253, 237, 237), (190, 80, 80))

# ---------- 测试点排针 ----------
d.rounded_rectangle([gx(2), gy(26), gx(18), gy(38)], radius=3,
                    fill=(250, 250, 240), outline=(150, 150, 90), width=2)
txt(gx(10), gy(26) - 18, "测试点 TP1~TP8", F_SM, (120, 120, 60), "mm")
for k in range(8):
    yy = gy(28 + k * 1)
    d.ellipse([gx(4) - 4, yy - 4, gx(4) + 4, yy + 4], fill=(120, 120, 60))
    txt(gx(5.5), yy, f"TP{k+1}", F_SM, (90, 90, 50), "lm")

# ---------- 地线 ----------
d.line([(BX - 4, gy(NY - 1) + 2), (gx(NX - 1) + 4, gy(NY - 1) + 2)],
       fill=(60, 60, 60), width=7)
txt(gx(1), gy(NY - 1) + 10, "地线：整条镀锡加粗，所有 GND 就近扎上去", F_SM, (60, 60, 60))

# ---------- 右侧说明 ----------
RX = gx(NX - 1) + 40
d.rectangle([RX, 120, RX + 300, 470], outline=(205, 208, 214), width=2)
txt(RX + 14, 134, "布局原则", F_SEC)
rules = [
    "① 信号从左往右：P1/P2 → 跟随",
    "   → 减法 → PI → PWM → MOS",
    "② 地线在底部一条，单点汇到",
    "   12V 入口电容负极",
    "③ 大电流（12V/风扇）与弱信",
    "   号分在两头，别交叉",
    "④ 芯片之间留 2 个孔位，方便",
    "   飞线和改线",
    "⑤ 先摆不焊，确认不打架再动",
    "   烙铁",
]
yy = 172
for s in rules:
    txt(RX + 14, yy, s, F_LAB)
    yy += 28

d.rectangle([RX, 500, RX + 300, 900], outline=(205, 208, 214), width=2)
txt(RX + 14, 514, "焊接顺序", F_SEC)
steps = [
    "1  4 个 DIP-8 插座（缺口朝上）",
    "2  地线：整条焊好并镀锡加粗",
    "3  电源：12V 入口、470µF、",
    "   7805、5V 去耦",
    "4  测试点排针 TP1~TP8",
    "5  电阻（先 4×10k，再其他）",
    "6  电容（电解注意极性）",
    "7  最后：IRLZ44N、1N4007、",
    "   风扇座、电位器引线",
    "8  芯片最后插（测完电源）",
]
yy = 552
for s in steps:
    txt(RX + 14, yy, s, F_LAB)
    yy += 30

txt(RX + 14, 862, "⚠ 每焊完一个模块，用通断档", F_SM, (170, 40, 40))
txt(RX + 14, 882, "   量一遍再焊下一个", F_SM, (170, 40, 40))

# ---------- 审计 ----------
print("=" * 60)
bad = 0
oob = [s for bb, s in _texts if bb[0] < 0 or bb[1] < 0 or bb[2] > W or bb[3] > H]
print("① 越界:", "无" if not oob else oob); bad += len(oob)
ov = []
for i in range(len(_texts)):
    for j in range(i + 1, len(_texts)):
        a, b = _texts[i][0], _texts[j][0]
        if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
            ov.append((_texts[i][1], _texts[j][1]))
print("② 互压:", "无" if not ov else f"{len(ov)} 对"); bad += len(ov)
for a, b in ov:
    print("   ", a, "×", b)

out = r"D:\BBA\University\electronic competition\training\2027\selection-control-sail-panel\assets\洞洞板布局.png"
img.save(out, "PNG")
print("=" * 60)
print("问题:", bad)
print("saved:", out, img.size)