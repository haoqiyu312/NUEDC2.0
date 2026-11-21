# -*- coding: utf-8 -*-
"""帆板控制系统装置示意图：侧视图 + 正视图，自带排版审计"""
import math
from PIL import Image, ImageDraw, ImageFont

W, H = 1900, 1200
S = 12.0

C_BG, C_STR, C_STR_F = (255, 255, 255), (70, 70, 70), (223, 226, 231)
C_VANE, C_VANE_O = (203, 228, 255), (41, 98, 165)
C_CW, C_CW_O = (255, 213, 166), (176, 108, 30)
C_FAN, C_FAN_O = (214, 242, 214), (39, 122, 74)
C_BOARD, C_BOARD_O = (231, 226, 250), (101, 70, 190)
C_DIM, C_DIM_T = (214, 124, 20), (150, 82, 10)
C_TXT, C_GRAY, C_WIND = (35, 35, 35), (150, 155, 165), (52, 152, 219)

F_TITLE = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 32)
F_SEC   = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 22)
F_LAB   = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 18)
F_SM    = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
F_DIM   = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 17)

img = Image.new("RGB", (W, H), C_BG)
d = ImageDraw.Draw(img)
_texts, _shapes = [], []


def txt(x, y, s, font, fill=C_TXT, anchor="la"):
    d.multiline_text((x, y), s, font=font, fill=fill, anchor=anchor, spacing=4)
    _texts.append((d.multiline_textbbox((x, y), s, font=font, anchor=anchor, spacing=4),
                   s.replace("\n", "/")))


def box(x1, y1, x2, y2, fill, outline, w=2, name=""):
    d.rectangle([x1, y1, x2, y2], fill=fill, outline=outline, width=w)
    _shapes.append(((x1, y1, x2, y2), name))
    return (x1, y1, x2, y2)


def arrowhead(p_from, p_to, color=C_DIM, size=9):
    ang = math.atan2(p_to[1] - p_from[1], p_to[0] - p_from[0])
    for a in (ang + math.radians(152), ang - math.radians(152)):
        d.line([p_to, (p_to[0] + size * math.cos(a), p_to[1] + size * math.sin(a))],
               fill=color, width=2)


def dim_h(x1, x2, y, label, above=True):
    d.line([(x1, y), (x2, y)], fill=C_DIM, width=2)
    arrowhead((x2, y), (x1, y)); arrowhead((x1, y), (x2, y))
    txt((x1 + x2) / 2, y - 7 if above else y + 7, label, F_DIM, C_DIM_T, "mb" if above else "mt")


def dim_v(y1, y2, x, label, left=True):
    d.line([(x, y1), (x, y2)], fill=C_DIM, width=2)
    arrowhead((x, y2), (x, y1)); arrowhead((x, y1), (x, y2))
    txt(x - 9, (y1 + y2) / 2, label, F_DIM, C_DIM_T, "rm" if left else "lm")


def leader(x1, y1, x2, y2):
    d.line([(x1, y1), (x2, y2)], fill=C_GRAY, width=1)
    d.ellipse([x1 - 3, y1 - 3, x1 + 3, y1 + 3], fill=C_GRAY)


def in_poly(pt, poly):
    x, y = pt; n = len(poly); c = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            c = not c
        j = i
    return c


# ================= 标题 =================
txt(W // 2, 20, "帆板控制系统 · 装置结构示意", F_TITLE, C_TXT, "ma")
txt(W // 2, 66, "左：侧视图（帆板、配重、风力方向）        右：正视图（转轴与两侧板）",
    F_SM, C_GRAY, "ma")

# ================= 侧视图 =================
BASE_Y = 860
AXIS = (440, 668)
PANEL_TOP = BASE_Y - int(24 * S)

base = box(100, BASE_Y, 740, BASE_Y + 22, C_STR_F, C_STR, 2, "底座")
panel = box(434, PANEL_TOP, 444, BASE_Y, C_STR_F, C_STR, 2, "侧板")


TH = math.radians(45)
dx, dy = math.sin(TH), math.cos(TH)
px, py = dy, -dx
L, HW = 15 * S, 5 * S

P = lambda t, s=1: (AXIS[0] + t * dx + s * HW * px, AXIS[1] + t * dy + s * HW * py)

vane = [P(0, 1), P(L, 1), P(L, -1), P(0, -1)]
d.polygon(vane, fill=C_VANE, outline=C_VANE_O, width=3)

ARM = 5 * S
cw = (AXIS[0] - ARM * dx, AXIS[1] - ARM * dy)
d.line([AXIS, cw], fill=C_CW_O, width=5)
box(cw[0] - 13, cw[1] - 13, cw[0] + 13, cw[1] + 13, C_CW, C_CW_O, 2, "配重")
# 量角器：画在帆板之上（它贴在侧板外侧，离观察者更近）
for rr, wd in ((96, 1), (90, 2)):
    for k in range(0, 360, 14):
        a0, a1 = math.radians(k), math.radians(k + 7)
        if not (300 <= k or k <= 96):
            continue
        d.line([(AXIS[0] + rr * math.cos(math.radians(90 - (90 - k))), AXIS[1] + rr * math.sin(math.radians(k))),
                (AXIS[0] + rr * math.cos(math.radians(k + 7)), AXIS[1] + rr * math.sin(math.radians(k + 7)))],
               fill=(120, 125, 135), width=wd)
for deg in range(0, 91, 10):
    a = math.radians(90 - deg)
    r1, r2 = 96, (74 if deg % 30 == 0 else 86)
    d.line([(AXIS[0] + r1 * math.cos(a), AXIS[1] + r1 * math.sin(a)),
            (AXIS[0] + r2 * math.cos(a), AXIS[1] + r2 * math.sin(a))], fill=(95, 100, 110), width=2)
    if deg % 30 == 0:
        lx = AXIS[0] + 108 * math.cos(a) + (14 if deg == 0 else 0)
        ly = AXIS[1] + 108 * math.sin(a) + (2 if deg == 0 else 0)
        txt(lx, ly, f"{deg}°", F_SM, (110, 115, 125), "mm")

d.ellipse([AXIS[0] - 9, AXIS[1] - 9, AXIS[0] + 9, AXIS[1] + 9], fill=C_STR)

FX1, FX2 = 150, 260
FY1 = BASE_Y - 108
fan = box(FX1, FY1, FX2, BASE_Y, C_FAN, C_FAN_O, 2, "风扇")
ccx, ccy, cr = (FX1 + FX2) / 2, (FY1 + BASE_Y) / 2, 36
d.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], outline=C_FAN_O, width=2)
for k in range(4):
    a = math.radians(45 + k * 90)
    d.line([(ccx, ccy), (ccx + cr * .8 * math.cos(a), ccy + cr * .8 * math.sin(a))], fill=C_FAN_O, width=2)
for yy in (ccy - 24, ccy, ccy + 24):
    d.line([(FX2 + 6, yy), (FX2 + 62, yy)], fill=C_WIND, width=2)
    arrowhead((FX2 - 12, yy), (FX2 + 62, yy), C_WIND, 8)

board = box(480, BASE_Y - 28, 690, BASE_Y, C_BOARD, C_BOARD_O, 2, "洞洞板")
pwr = box(690, BASE_Y - 46, 740, BASE_Y, C_STR_F, C_STR, 2, "电源")

# 竖直参考线（0°）
for yy in range(PANEL_TOP - 8, BASE_Y + 6, 12):
    d.line([(AXIS[0], yy), (AXIS[0], yy + 6)], fill=C_GRAY, width=1)

# d 尺寸（放在底座下方，避免与图形打架）
DY = BASE_Y + 58
d.line([(FX2, BASE_Y + 22), (FX2, DY + 10)], fill=C_GRAY, width=1)
d.line([(AXIS[0], BASE_Y + 22), (AXIS[0], DY + 10)], fill=C_GRAY, width=1)
dim_h(FX2, AXIS[0], DY, "d = 10 ~ 25 cm（滑槽前后可调）", above=True)

# 高度尺寸
dim_v(PANEL_TOP, BASE_Y, 782, "24 cm", left=False)
dim_v(AXIS[1], BASE_Y, 826, "16 cm", left=False)

# θ 角
d.arc([AXIS[0] - 110, AXIS[1] - 110, AXIS[0] + 110, AXIS[1] + 110], 45, 90, fill=C_DIM, width=2)
leader(447, 778, 384, 792)
txt(380, 792, "θ = 45°", F_DIM, C_DIM_T, "rm")

txt(120, BASE_Y + 36, "底座", F_LAB, C_TXT)

# ================= 侧视图标注（右列） =================
LX = 892
leader(cw[0], cw[1] - 15, LX - 14, 262)
txt(LX, 250, "配重（轴上方、可上下滑动）\n对轴质量矩 20~30 g·cm", F_LAB)

leader(487, 726, LX - 14, 372)
txt(LX, 360, "量角器：粘在靠近帆板那侧侧板的外面，\n圆心对准轴心，竖直向下为 0°", F_LAB)

leader(AXIS[0] + 12, AXIS[1] - 8, LX - 14, 486)
txt(LX, 470, "转轴：4mm 光轴，两端各一个 624ZZ 轴承\n用 4mm 轴环做轴向定位", F_LAB)

leader(566, 748, LX - 14, 596)
txt(LX, 580, "帆板 10 × 15 cm，质量 ≤10 g\n上沿装轴，迎风面要平整", F_LAB)

leader(ccx, ccy + 40, LX - 14, 706)
txt(LX, 690, "风扇 12V 2 线（92 或 120mm）\n装在可前后滑动的支架上", F_LAB)

leader(600, BASE_Y - 20, LX - 14, 816)
txt(LX, 800, "洞洞板：4 个芯片 + 电位器接线\n留 TP1~TP8 测试点", F_LAB)

leader(716, BASE_Y - 46, LX - 14, 926)
txt(LX, 910, "电源座 / 船型开关 / 保险丝 / 指示灯", F_LAB)

# ================= 正视图 =================
FB_Y = 1000
FL_X1, FL_X2 = 1330, 1342
SPAN = 144
FR_X1 = FL_X1 + SPAN
FCX = (FL_X2 + FR_X1) / 2
FAX = (FCX, FB_Y - int(16 * S))
FTOP = FB_Y - int(24 * S)

box(1290, FB_Y, 1840, FB_Y + 22, C_STR_F, C_STR, 2, "底座F")
box(FL_X1, FTOP, FL_X2, FB_Y, C_STR_F, C_STR, 2, "左侧板")
box(FR_X1, FTOP, FR_X1 + 12, FB_Y, C_STR_F, C_STR, 2, "右侧板")
fvan = box(FCX - 60, FAX[1], FCX + 60, FAX[1] + int(15 * S), C_VANE, C_VANE_O, 2, "帆板F")
d.line([(FL_X2, FAX[1]), (FR_X1, FAX[1])], fill=C_STR, width=3)
d.ellipse([FAX[0] - 8, FAX[1] - 8, FAX[0] + 8, FAX[1] + 8], fill=C_STR)
for k in range(0, 360, 12):
    a0, a1 = math.radians(k), math.radians(k + 6)
    d.line([(FCX + 76 * math.cos(a0), FAX[1] + 76 * math.sin(a0)),
            (FCX + 76 * math.cos(a1), FAX[1] + 76 * math.sin(a1))], fill=C_GRAY, width=2)
box(FL_X1 - 4, FAX[1] - 22, FL_X1 + 14, FAX[1] + 22, (198, 198, 203), C_STR, 2, "轴承1")
box(FR_X1 - 2, FAX[1] - 22, FR_X1 + 16, FAX[1] + 22, (198, 198, 203), C_STR, 2, "轴承2")

dim_h(FL_X2, FR_X1, FB_Y + 32, "板间距 12 cm", above=False)
dim_h(FCX - 60, FCX + 60, FB_Y + 78, "帆板宽 10 cm", above=False)
dim_v(FTOP, FB_Y, 1512, "24 cm", left=False)

txt(1290, FB_Y + 120, "正视图：轴两端各一个 624ZZ 轴承", F_SM)
txt(1290, FB_Y + 142, "量角器贴在靠近帆板的侧板外侧（灰色虚线圆）", F_SM)

# ================= 说明框 =================
BX, BY, BX2, BY2 = 1290, 150, 1850, 700
d.rectangle([BX, BY, BX2, BY2], outline=(205, 208, 214), width=2)
txt(BX + 18, BY + 14, "关键尺寸与要求", F_SEC)
rows = [
    ("总高", "24 cm（轴上方留配重杆空间）"),
    ("轴高", "16 cm（距底座上表面）"),
    ("侧板间距", "12 cm"),
    ("帆板", "10 × 15 cm，质量 ≤10 g"),
    ("转轴", "4mm 光轴，两端 624ZZ"),
    ("配重", "对轴质量矩 20~30 g·cm"),
    ("风扇距离 d", "10 ~ 25 cm 可调"),
    ("量角器", "装在转轴处，评委直接读数"),
]
yy = BY + 56
for k, v in rows:
    txt(BX + 18, yy, k, F_LAB)
    txt(BX + 140, yy, v, F_LAB)
    yy += 34

txt(BX + 18, BY + 358, "为什么能稳在某个角度", F_SEC)
txt(BX + 18, BY + 394, "风力 → 把帆板推离竖直", F_LAB, (52, 120, 190))
txt(BX + 18, BY + 422, "重力 → 把帆板拉回竖直", F_LAB, (160, 90, 30))
txt(BX + 18, BY + 458, "两个力矩相等的位置，就是稳定角度。", F_SM)
txt(BX + 18, BY + 482, "风越大 → θ 越大，所以天然单调可调。", F_SM)
txt(BX + 18, BY + 514, "前提：整套转动件的总重心，必须在转轴下方。", F_SM, (170, 40, 40))

# ================= 审计 =================
print("=" * 66)
bad = 0

oob = [(bb, s) for bb, s in _texts if bb[0] < 0 or bb[1] < 0 or bb[2] > W or bb[3] > H]
print("① 文字越界:", "无" if not oob else f"{len(oob)} 处")
for bb, s in oob:
    print("   ", s, "->", tuple(round(v) for v in bb)); bad += 1

ov = []
for i in range(len(_texts)):
    for j in range(i + 1, len(_texts)):
        a, b = _texts[i][0], _texts[j][0]
        if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
            ov.append((_texts[i][1], _texts[j][1]))
print("② 文字互压:", "无" if not ov else f"{len(ov)} 对")
for a, b in ov:
    print(f"   [{a}] × [{b}]"); bad += 1

hit = []
for bb, s in _texts:
    if s.endswith("°") and len(s) <= 4:
        continue
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    if in_poly((cx, cy), vane) or in_poly((cx, cy), [fvan and (fvan[0], fvan[1]),
                                                     (fvan[2], fvan[1]),
                                                     (fvan[2], fvan[3]),
                                                     (fvan[0], fvan[3])]):
        hit.append((s, "帆板")); bad += 1
    for sb, nm in _shapes:
        if nm in ("帆板F",):
            continue
        if sb[0] <= cx <= sb[2] and sb[1] <= cy <= sb[3]:
            hit.append((s, nm)); bad += 1
print("③ 文字压在图形中心区:", "无" if not hit else f"{len(hit)} 处")
for s, nm in hit:
    print(f"   [{s}] 落在 [{nm}] 内")

out = r"D:\BBA\University\electronic competition\training\2027\selection-control-sail-panel\assets\装置示意图.png"
img.save(out, "PNG")
print("=" * 66)
print("问题总数:", bad)
print("saved:", out, img.size)