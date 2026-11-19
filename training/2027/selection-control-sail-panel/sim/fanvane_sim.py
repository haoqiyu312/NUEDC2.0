# -*- coding: utf-8 -*-
"""
帆板控制系统 v2 —— 电路与闭环数值验证
=====================================
依赖：仅 numpy。不依赖 scipy / matplotlib / SPICE。

用法：  python fanvane_sim.py
输出：  sim_output.txt （UTF-8，含全部结果表）

设计原则
--------
* 电路部分（运放、比较器、积分器）按理想运放 + 输出饱和建模，
  对 LM358/LM393 这个速率档次是足够精确的。
* 被控对象（风扇 + 帆板）参数在拿到实物前是未知的，
  因此全部按"参数化"处理，并扫描不确定区间，
  结论一律给出"在什么参数范围内成立"。
"""

import io
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_out = io.open(os.path.join(HERE, "sim_output.txt"), "w", encoding="utf-8")


def P(*a):
    line = " ".join(str(x) for x in a)
    _out.write(line + "\n")


def H(title):
    P()
    P("=" * 78)
    P(title)
    P("=" * 78)


# ============================================================
# 1. 电路常数（全部取自 帆板控制系统实施方案-v2.md）
# ============================================================
# ------------------------------------------------------------
# 【重要】下面这组 R7/R8/C1 是【原方案的错误参数】，只用于第 0~5 节
# 演示"为什么原来的值不可用"以及绘制稳定性地图。
# 定稿要焊的参数在文件后部定义：KP_REC, TI_REC = 0.22, 0.68
#   即 R7=100k, R8=22k, C1=6.8µF  ->  Kp=0.22, 积分时间常数 R7*C1=0.68s
# 不要拿 R7/R8/C1 这三个模块级常数当成施工值。
# ------------------------------------------------------------
R7, C1 = 10e3, 1e-6          # 原方案 PI 输入电阻 / 积分电容（错误值，仅作对照）
R8 = 220e3                   # 原方案 PI 比例电阻（错误值，仅作对照）
R9, C2 = 15e3, 10e-9         # 三角波积分器
R10, R11 = 10e3, 13.9e3      # 三角波迟滞网络
VREF = 2.5                   # 中点基准
VPU, RPU = 5.0, 2.2e3        # LM393 上拉到 5V
VOL_CMP = 0.10               # LM393 低电平
VOH_OP, VOL_OP = 10.4, 0.05  # LM358 在 12V 下的输出上下限


def cmp_high():
    """LM393 高电平：被 R11 负载从 5V 拉下来多少"""
    return (VPU / RPU + VREF / R11) / (1.0 / RPU + 1.0 / R11)


VOH_CMP = cmp_high()


def triangle_params():
    """三角波的下限 V_L、上限 V_H、频率 f"""
    r = R10 / R11
    v_low = VREF * (1 + r) - VOH_CMP * r      # V_cmp 高时对应的低门限
    v_high = VREF * (1 + r) - VOL_CMP * r     # V_cmp 低时对应的高门限
    slope_dn = (VOH_CMP - VREF) / (R9 * C2)   # 下降速率 [V/s]
    slope_up = (VREF - VOL_CMP) / (R9 * C2)   # 上升速率 [V/s]
    amp = v_high - v_low
    period = amp / slope_dn + amp / slope_up
    return v_low, v_high, 1.0 / period, slope_up, slope_dn


V_L, V_H, F_TRI, SLOPE_UP, SLOPE_DN = triangle_params()
K_V = (1.0 / SLOPE_UP + 1.0 / SLOPE_DN) / (1.0 / F_TRI)   # 占空比/伏


# ============================================================
# 2. 被控对象参数（未知量，全部参数化）
# ============================================================
G_ACC = 9.81
M_VANE = 0.010        # 帆板质量 10 g
R_CG = 0.025          # 重心到轴距离 25 mm
G_TORQ = M_VANE * G_ACC * R_CG        # 重力力矩系数 [N·m]
I_VANE = 8e-5         # 转动惯量 [kg·m²]
THETA_CAL = np.deg2rad(70.0)          # 设计判据：100% 占空比 → 约 70°
U0 = 0.35             # 风扇起转占空比
TAU_F = 0.15          # 风扇转速一阶时间常数 [s]
P_WIND = 2.0          # 风力矩 ∝ cos^p(theta)
KF = 0.0185           # 反馈灵敏度 [V/度]：电位器 1:1 直连，270°, 5V


def wind_coeff(d_cm):
    """标定：d=15cm、100% 占空比时平衡角约 70°；其它距离按 (15/d)^1 缩放"""
    c15 = G_TORQ * np.sin(THETA_CAL) / np.cos(THETA_CAL) ** P_WIND
    return c15 * (15.0 / d_cm)


def operating_point(d_cm, theta_deg=45.0):
    """给定 d 和角度，返回线性化参数"""
    th = np.deg2rad(theta_deg)
    cw = wind_coeff(d_cm)
    # Cw*s^2*cos^p = G*sin  ->  s^2
    s2 = G_TORQ * np.sin(th) / (cw * np.cos(th) ** P_WIND)
    s = np.sqrt(s2)
    # 刚度 K = G*(p*sin^2/cos + cos)
    K = G_TORQ * (P_WIND * np.sin(th) ** 2 / np.cos(th) + np.cos(th))
    wn = np.sqrt(K / I_VANE)
    # 风力矩对转速的偏导
    dtau_ds = 2.0 * cw * s * np.cos(th) ** P_WIND
    ds_du = 1.0 / (1.0 - U0)
    dtheta_du = dtau_ds * ds_du / K      # [rad per unit duty]
    return dict(th=th, cw=cw, s=s, K=K, wn=wn, dtheta_du=dtheta_du,
                duty=U0 + (1 - U0) * s)


def loop_tot(d_cm, kf=KF):
    """直流环路增益（环路里除 PI 之外的全部增益，量纲 1）"""
    op = operating_point(d_cm)
    return op["dtheta_du"] * 180.0 / np.pi * kf * K_V


# ============================================================
# 3. 频域：环路增益、相位裕度、增益裕度
# ============================================================
def loop_response(f, kp, ti, ktot, zeta, wn, tau_f):
    s = 1j * 2 * np.pi * f
    pi_part = kp + 1.0 / (s * ti)
    plant = wn ** 2 / (s ** 2 + 2 * zeta * wn * s + wn ** 2)
    return pi_part * ktot * plant / (1.0 + s * tau_f)


def stability(kp, ti, ktot, zeta, wn, tau_f):
    """
    用"向量裕度"判稳：VM = min|1 + L(jw)|，即环路曲线到 -1 点的最近距离。
    这个指标对"谐振导致增益二次翘起"的情况同样有效（相位裕度会失效）。
    """
    f = np.logspace(-4, 5, 80000)
    L = loop_response(f, kp, ti, ktot, zeta, wn, tau_f)
    mag = np.abs(L)
    ph = np.angle(L, deg=True)
    vm = float(np.min(np.abs(1.0 + L)))
    over = mag >= 1.0
    down = np.where(over[:-1] & (~over[1:]))[0]
    if len(down):
        i = down[0]
        fc, pm = f[i], 180.0 + ph[i]
    else:
        fc, pm = np.nan, np.nan
    fn = wn / (2 * np.pi)
    band = (f > 0.6 * fn) & (f < 2.5 * fn)
    bump = float(np.max(mag[band])) if band.any() else np.nan
    return dict(fc=fc, pm=pm, vm=vm, bump=bump)


def verdict(vm):
    if vm > 0.6:
        return "好"
    if vm > 0.4:
        return "勉强"
    return "危险"


# ============================================================
# 4. 时域：闭环阶跃（向量化，一次跑很多组参数）
# ============================================================
# ============================================================
# 关于参数 `ti`（重要，容易与标准 PI 形式的 Ti 混淆）
# ------------------------------------------------------------
# 本脚本里 `ti` 一律指【积分时间常数】= R7 * C1，对应代码 `dv = -e / ti`。
#   物理含义：误差 1V 时，PI 输出每秒变化 1/ti 伏。
#   定稿值：R7=100k, C1=6.8µF  ->  ti = 0.68 s
#
# 它【不是】标准 PI 形式 Kp(1 + 1/(Ti·s)) 里的那个 Ti。
# 两者差一个 Kp：  Ti_标准 = Kp * ti = 0.22 * 0.68 = 0.15 s
#
# 所以读输出里的 "τi=0.68s" 时，必须理解为"积分时间常数 0.68s"，
# 不要当成标准形式的 Ti。
# ============================================================
def transient(batch, t_end=30.0, dt=2e-4, mode="PI", record=False):
    """
    batch: list of dict(kp, ti, d, zeta, tau_f, u0, kf, theta_set, theta0, tau_c)
    其中 ti = 积分时间常数 R7*C1（不是标准 PI 形式的 Ti）
    返回 list of dict(settle5, settle1, overshoot, final, oscillating, t, th)
    """
    n = len(batch)
    A = lambda key, dflt: np.array([b.get(key, dflt) for b in batch], float)

    kp = A("kp", 22.0)
    ti = A("ti", 0.01)
    d = A("d", 15.0)
    zeta = A("zeta", 0.05)
    tau_f = A("tau_f", TAU_F)
    u0 = A("u0", U0)
    kf = A("kf", KF)
    th_set = np.deg2rad(A("theta_set", 45.0))
    th = np.deg2rad(A("theta0", 20.0))
    tau_c = A("tau_c", 0.0)
    use_i = np.array([b.get("mode", mode) != "P" for b in batch])

    cw = np.array([wind_coeff(x) for x in d])
    # 转动惯量：可由 batch 指定（不同材料/质量）
    I_b = A("I", I_VANE)
    # 支持"距离突变"与"电位器噪声"
    d2 = A("d2", np.nan)
    t_sw = A("t_switch", 1e9)
    noise = A("noise", 0.0)
    cw2 = np.array([wind_coeff(x) if np.isfinite(x) else 1.0 for x in d2])
    has_d2 = np.isfinite(d2)
    rng = np.random.default_rng(20261117)
    # 粘性阻尼：按 45° 处的刚度折算成阻尼比 zeta
    k_ref = G_TORQ * (P_WIND * 0.5 / np.sqrt(0.5) + np.sqrt(0.5))
    B_VISC = 2.0 * zeta * np.sqrt(np.maximum(k_ref * I_b, 1e-15))
    w = np.zeros(n)
    s_f = np.zeros(n)
    vc = np.zeros(n)
    th_min = np.deg2rad(np.full(n, 10.0))
    th_max = np.deg2rad(np.full(n, 78.0))

    steps = int(t_end / dt)
    hist_t = np.zeros(steps)
    hist_th = np.zeros((n, steps))
    eps = 1e-4

    for k in range(steps):
        t = k * dt
        # --- 反馈与误差 ---
        v_fb = VREF + kf * (np.rad2deg(th) - 45.0)   # 45度时正好 2.5V
        if noise.any():
            v_fb = v_fb + noise * rng.standard_normal(n)
        v_set = VREF + kf * (np.rad2deg(th_set) - 45.0)
        e = (v_fb - v_set)                            # = V_err - 2.5
        # --- PI ---
        v_ctrl = VREF + vc - kp * e
        sat_hi = v_ctrl > VOH_OP
        sat_lo = v_ctrl < VOL_OP
        v_ctrl = np.clip(v_ctrl, VOL_OP, VOH_OP)
        dv = -e / ti
        dv = np.where((sat_hi & (dv > 0)) | (sat_lo & (dv < 0)), 0.0, dv)
        dv = np.where(use_i, dv, 0.0)
        # --- PWM ---
        u = np.clip((v_ctrl - V_L) * K_V, 0.0, 1.0)
        s_tgt = np.clip((u - u0) / (1.0 - u0), 0.0, 1.0)
        # --- 对象 ---
        cw_eff = np.where(has_d2 & (t >= t_sw), cw2, cw)
        tau_w = cw_eff * s_f ** 2 * np.cos(th) ** P_WIND
        tau_g = G_TORQ * np.sin(th)
        tau_fr = B_VISC * w
        tau_c_eff = tau_c * np.tanh(w / eps)
        dth = w
        dw = (tau_w - tau_g - tau_fr - tau_c_eff) / I_b
        # --- 限位 ---
        hit_lo = th <= th_min
        hit_hi = th >= th_max
        dth = np.where(hit_lo & (dth < 0), 0.0, dth)
        dw = np.where(hit_lo & (dw < 0), 0.0, dw)
        dth = np.where(hit_hi & (dth > 0), 0.0, dth)
        dw = np.where(hit_hi & (dw > 0), 0.0, dw)

        th = np.clip(th + dt * dth, th_min, th_max)
        w = w + dt * dw
        s_f = s_f + dt * (s_tgt - s_f) / tau_f
        vc = vc + dt * dv

        hist_t[k] = t
        hist_th[:, k] = th

    res = []
    for i, b in enumerate(batch):
        y = np.rad2deg(hist_th[i])
        target = np.rad2deg(th_set[i])
        t0 = t_sw[i] if t_sw[i] < t_end else 0.0
        sel = hist_t >= t0
        tt = hist_t[sel]
        err = y[sel] - target
        idx5 = np.where(np.abs(err) > 5.0)[0]
        idx1 = np.where(np.abs(err) > 1.0)[0]
        settle5 = np.nan if len(idx5) == 0 else tt[idx5[-1]] - t0
        settle1 = np.nan if len(idx1) == 0 else tt[idx1[-1]] - t0
        # 若末尾 3 秒仍在 ±0.3 度之外跳动，判为振荡
        tail = y[hist_t > t_end - 3.0]
        osc = bool(np.ptp(tail) > 0.6)
        final = float(np.mean(y[hist_t > t_end - 3.0]))
        overshoot = float(max(0.0, (y.max() - target))) if target > y[0] else \
            float(max(0.0, (y.min() - target)))
        rec = dict(settle5=float(settle5), settle1=float(settle1),
                   overshoot=overshoot, final=final,
                   oscillating=osc, amp=float(np.ptp(tail)))
        if record:
            rec["t"] = hist_t
            rec["th"] = y
        res.append(rec)
    return res


# ============================================================
# 5. 报告
# ============================================================
def main():
    H("0. 文档常数与派生量")
    P("R7=%.0fk C1=%.1fuF R8=%.0fk  -> Kp = R8/R7 = %.1f , 积分时间常数 = R7*C1 = %.1f ms"
      % (R7 / 1e3, C1 * 1e6, R8 / 1e3, R8 / R7, R7 * C1 * 1e3))
    P("R9=%.0fk C2=%.0fnF R10=%.0fk R11=%.0fk" % (R9 / 1e3, C2 * 1e9, R10 / 1e3, R11 / 1e3))
    P("")
    P(">> 注意：上面这组 R7/R8/C1 是【原方案错误值】，只用于第 0~5 节演示为什么不可用。")
    P("   定稿施工值 = R7=100k / R8=22k / C1=6.8µF  ->  Kp=0.22, 积分时间常数 R7*C1=0.68s（第 11 节起使用）")
    P("LM393 高电平（被 R11 拉低）= %.3f V" % VOH_CMP)
    P("LM358 @12V 输出范围 = %.2f ~ %.2f V" % (VOL_OP, VOH_OP))

    H("1. 三角波发生器（文档声称 0.70~4.30V, 约 2.3kHz）")
    P("下限 V_L = %.3f V" % V_L)
    P("上限 V_H = %.3f V" % V_H)
    P("幅度     = %.3f Vpp" % (V_H - V_L))
    P("频率     = %.1f Hz" % F_TRI)
    P("上升斜率 = %.0f V/s   下降斜率 = %.0f V/s" % (SLOPE_UP, -SLOPE_DN))
    P("")
    P(">> 判定：与文档 0.70/4.30/2.3k 对比")
    P("   下限偏高 %.3f V、上限偏低 %.3f V" % (V_L - 0.70, 4.30 - V_H))
    P("   原因：LM393 高电平不是 5V，而是被 R11 拉低到 %.2fV；" % VOH_CMP)
    P("   文档用理想 0/5V 计算，所以限值偏乐观。频率结论正确（误差 <1%%）。")
    P("   影响：PWM 的 0%% 点从 0.70V 抬到 %.2fV，满度点从 4.30V 降到 %.2fV。" % (V_L, V_H))
    P("   这不影响闭环（PI 输出范围 0~10.4V，远大于需要），但**测试表的电压要用实测值**。")

    H("2. PWM 占空比映射")
    P("duty = (V_ctrl - %.3f) * %.4f   [V -> 0~1]" % (V_L, K_V))
    for vc in (0.5, V_L, 1.5, 2.0, 2.5, 3.0, 3.5, V_H, 5.0):
        duty = float(np.clip((vc - V_L) * K_V, 0, 1))
        P("  V_ctrl = %5.2f V  ->  duty = %6.2f %%" % (vc, duty * 100))
    P(">> 单调、线性，两端饱和正确。极性正确：V_ctrl 升高 -> 占空比升高。")

    H("3. 环路增益与稳定性（核心）")
    P("反馈灵敏度假设：P2 与转轴 1:1 直连（270°电位器, 5V），kf=%.4f V/度" % KF)
    for d in (10, 15, 25):
        op = operating_point(d)
        P("  d=%2dcm: 45°时 s=%.3f duty=%.1f%%  刚度K=%.3e  谐振 f_n=%.2f Hz  dθ/du=%.1f 度"
          % (d, op["s"], op["duty"] * 100, op["K"], op["wn"] / 2 / np.pi,
             op["dtheta_du"] * 180 / np.pi))
        P("           直流环路增益 K_tot = %.3f" % loop_tot(d))
    P("")
    P("  >> K_tot 只有 0.3~1.1 量级，说明只用 P 控制会留下很大静差（需要 I）。")

    op15 = operating_point(15)
    wn = op15["wn"]

    H("4. 环路鲁棒性：Kp × C1  （积分时间常数 = R7*C1）")
    P("zeta=0.05, tau_fan=0.15s, d=15cm, kf=%.4f V/度" % KF)
    P("VM = 向量裕度 = min|1+L|，环路到 -1 点的最近距离；<0.4 危险，>0.6 良好")
    P("括号内 = 谐振频段上 |L| 的最大值，>1 表示谐振峰把增益顶回了 1 以上")
    P("")
    c1s = (1e-6, 10e-6, 33e-6, 100e-6, 220e-6, 470e-6)
    kps = (0.2, 0.5, 1.0, 2.0, 4.0, 22.0)
    head = "  %-7s" % "Kp\\C1" + "".join("%-16s" % ("%.0fuF" % (c * 1e6)) for c in c1s)
    P(head)
    for kp in kps:
        row = "  %-7.1f" % kp
        for c1 in c1s:
            st = stability(kp, R7 * c1, loop_tot(15), 0.05, wn, TAU_F)
            row += "%-16s" % ("%.2f(%s)" % (st["vm"], "%.1f" % st["bump"]))
        P(row)
    P("")
    P("  解读：括号里的数远大于 1，说明帆板 1.28Hz 的谐振把环路增益顶起来了，")
    P("        此时只能靠把穿越频率压到谐振以下（加大 C1 / 减小 Kp）来换稳定，代价是变慢。")

    H("5. 机械阻尼 zeta 的影响（决定这题能不能做到 5 秒）")
    P("配置：Kp=0.5 (R8=5k)，C1 扫描；d=15cm")
    P("")
    P("  %-8s %-9s %-10s %-10s %-10s %s"
      % ("zeta", "C1(uF)", "VM", "fc(Hz)", "谐振峰", "结论"))
    for zeta in (0.03, 0.05, 0.10, 0.20, 0.30):
        for c1 in (10e-6, 100e-6, 470e-6):
            st = stability(0.5, R7 * c1, loop_tot(15), zeta, wn, TAU_F)
            P("  %-8.2f %-9.0f %-10.2f %-10.3f %-10.1f %s"
              % (zeta, c1 * 1e6, st["vm"], st["fc"], st["bump"], verdict(st["vm"])))
        P("")

    H("6. 时域：20° -> 45° 阶跃（要求 5 秒内进入 ±5°）")
    combos, names = [], []
    grid = [
        (0.5, 10e-6, 0.05), (0.5, 470e-6, 0.05),
        (0.2, 470e-6, 0.05), (0.5, 100e-6, 0.05),
        (0.5, 470e-6, 0.20), (0.5, 100e-6, 0.20),
        (1.0, 100e-6, 0.20), (0.5, 33e-6, 0.20),
        (0.5, 100e-6, 0.30), (1.0, 33e-6, 0.30),
    ]
    for kp, c1, z in grid:
        combos.append(dict(kp=kp, ti=R7 * c1, d=15.0, zeta=z))
        names.append("Kp=%.1f C1=%guF z=%.2f" % (kp, c1 * 1e6, z))
    r = transient(combos, t_end=40.0)
    P("  %-26s %-9s %-9s %-9s %-9s %s"
      % ("配置", "5°内(s)", "1°内(s)", "超调(度)", "终值(度)", "残留摆动(度)"))
    for nm, x in zip(names, r):
        f5 = "未稳" if np.isnan(x["settle5"]) else "%.2f" % x["settle5"]
        f1 = "未稳" if np.isnan(x["settle1"]) else "%.2f" % x["settle1"]
        flag = " <<振荡" if x["oscillating"] else ""
        P("  %-26s %-9s %-9s %-9.1f %-9.1f %.2f%s"
          % (nm, f5, f1, x["overshoot"], x["final"], x["amp"], flag))

    H("7. 距离 d = 10~25cm 的可行性（发挥部分）")
    P("  %-6s %-12s %-12s %-12s %-10s" % ("d(cm)", "10°占空比", "45°占空比", "60°占空比", "100%角"))
    for d in (10, 12, 15, 20, 25):
        row = "  %-6d" % d
        for th in (10, 45, 60):
            op = operating_point(d, th)
            row += "%-12s" % ("%.1f%%" % (op["duty"] * 100))
        # 100% 时的平衡角
        cw = wind_coeff(d)
        lo, hi = 1.0, 89.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            lhs = cw * np.cos(np.deg2rad(mid)) ** P_WIND
            rhs = G_TORQ * np.sin(np.deg2rad(mid))
            if lhs > rhs:
                lo = mid
            else:
                hi = mid
        row += "%-10s" % ("%.1f°" % mid)
        P(row)
    P("")
    P("  >> 若 10° 的所需占空比 < 风扇起转占空比 u0=%.2f，则电路到不了 10°，" % U0)
    P("     必须靠 10° 机械限位兜底（v2 第 3.5 节）。")

    H("8. 干摩擦敏感性（干摩擦过大 -> 爬行/极限环）")
    P("配置：Kp=0.5, 积分时间常数=1.0s, zeta=0.20, d=15cm")
    P("  %-11s %-10s %-11s %-10s %s"
      % ("干摩擦mN·m", "5°内(s)", "终值(度)", "残留摆动(度)", "结论"))
    combos = [dict(kp=0.5, ti=1.0, d=15.0, zeta=0.20, tau_c=tc)
              for tc in (0, 1e-4, 3e-4, 1e-3, 3e-3)]
    r = transient(combos, t_end=40.0)
    for tc, x in zip((0, 1e-4, 3e-4, 1e-3, 3e-3), r):
        f5 = "未稳" if np.isnan(x["settle5"]) else "%.2f" % x["settle5"]
        P("  %-11s %-10s %-11.1f %-10.2f %s"
          % ("%.2f" % (tc * 1e3), f5, x["final"], x["amp"],
             "可接受" if x["amp"] < 1.0 else "有爬行/极限环"))

    H("9. 参数选择表：先量阻尼，再查表（频域裕度 + 时域阶跃 双重筛选）")
    P("怎么量 zeta：风扇断电，把帆板拨到约 45° 松手，数它来回摆几次停住")
    P("  >4 个来回             -> zeta < 0.05  ★ 必须加阻尼")
    P("  2~3 个来回            -> zeta ≈ 0.10")
    P("  1 个来回就停 / 两下就停 -> zeta ≥ 0.20")
    P("")
    P("  %-6s %-7s %-8s %-7s %-9s %-9s %s"
      % ("zeta", "Kp", "τi(s)", "VM", "fc(Hz)", "5°内(s)", "结论"))
    kp_grid = (0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0)
    ti_grid = (0.1, 0.2, 0.33, 0.47, 0.68, 1.0, 1.5, 2.2)
    for zeta in (0.05, 0.10, 0.15, 0.20, 0.30):
        cands = []
        for kp in kp_grid:
            for ti in ti_grid:
                st = stability(kp, ti, loop_tot(15), zeta, wn, TAU_F)
                if st["vm"] > 0.55 and not np.isnan(st["fc"]):
                    cands.append((kp, ti))
        if not cands:
            P("  %-6.2f  —— 没有任何组合通过频域裕度，必须加阻尼" % zeta)
            P("")
            continue
        combos = [dict(kp=c[0], ti=c[1], d=15.0, zeta=zeta) for c in cands]
        rr = transient(combos, t_end=15.0, dt=3e-4)
        good = [(x["settle5"], c, x) for c, x in zip(cands, rr)
                if (not np.isnan(x["settle5"])) and x["settle5"] <= 5.0
                and not x["oscillating"]]
        if good:
            good.sort(key=lambda t: t[0])
            for s5, (kp, ti), x in good[:2]:
                vm = stability(kp, ti, loop_tot(15), zeta, wn, TAU_F)["vm"]
                fc = stability(kp, ti, loop_tot(15), zeta, wn, TAU_F)["fc"]
                P("  %-6.2f %-7.1f %-8.2f %-7.2f %-9.3f %-9.2f ★满足5秒"
                  % (zeta, kp, ti, vm, fc, s5))
        else:
            # 没有合格的：报告最好的一个，用来说明为什么不够
            def key(t):
                x = t[1]
                return (1 if x["oscillating"] else 0,
                        x["settle5"] if not np.isnan(x["settle5"]) else 1e9)
            best = min(zip(cands, rr), key=key)
            (kp, ti), x = best
            vm = stability(kp, ti, loop_tot(15), zeta, wn, TAU_F)["vm"]
            fc = stability(kp, ti, loop_tot(15), zeta, wn, TAU_F)["fc"]
            s5 = "未稳" if np.isnan(x["settle5"]) else "%.2f" % x["settle5"]
            P("  %-6.2f %-7.1f %-8.2f %-7.2f %-9.3f %-9s ✗ 做不到 5 秒%s"
              % (zeta, kp, ti, vm, fc, s5, "（振荡）" if x["oscillating"] else ""))
        P("")

    H("10. 元件容差影响（以 zeta=0.20, Kp=0.5, τi=1.0s 为基准）")
    base = stability(0.5, 1.0, loop_tot(15), 0.20, wn, TAU_F)
    P("  基准：VM=%.2f  fc=%.3f Hz  V_H=%.3f V" % (base["vm"], base["fc"], V_H))
    P("  %-24s %-9s %-11s %s" % ("扰动", "VM", "相对基准", "影响"))
    for name, kp, ti in (("C1 -20% (τi=0.8s)", 0.5, 0.8),
                         ("C1 +20% (τi=1.2s)", 0.5, 1.2),
                         ("R8 -5%  (Kp=0.475)", 0.475, 1.0),
                         ("R8 +5%  (Kp=0.525)", 0.525, 1.0)):
        vm = stability(kp, ti, loop_tot(15), 0.20, wn, TAU_F)["vm"]
        d = vm - base["vm"]
        P("  %-24s %-9.2f %-11s %s"
          % (name, vm, "%+.3f" % d, "可接受" if d > -0.12 else "裕度明显下降"))
    P("")
    P("  R10/R11 误差只改变三角波幅度（进而改变占空比标定），不破坏稳定性：")
    for name, r10, r11v in (("R10 +5%", 10.5e3, 13.9e3), ("R11 +5%", 10e3, 14.6e3),
                            ("R11 -5%", 10e3, 13.2e3)):
        rr = r10 / r11v
        v_low = VREF * (1 + rr) - VOH_CMP * rr
        v_high = VREF * (1 + rr) - VOL_CMP * rr
        P("    %-10s V_L=%.3f  V_H=%.3f  幅度=%.2f Vpp" % (name, v_low, v_high, v_high - v_low))

    KP_REC, TI_REC, Z_REC = 0.22, 0.68, 0.20

    H("11. 极限角度：能不能真的覆盖 10~60°（zeta=%.2f, Kp=%.2f, τi=%.2fs）"
      % (Z_REC, KP_REC, TI_REC))
    P("  %-9s %-10s %-11s %-11s %s" % ("设定角", "终值", "5°内(s)", "残留摆动", "结论"))
    sets = (10, 12, 15, 30, 45, 60)
    combos = [dict(kp=KP_REC, ti=TI_REC, d=15.0, zeta=Z_REC,
                   theta_set=s, theta0=20.0) for s in sets]
    rr = transient(combos, t_end=30.0)
    for s, x in zip(sets, rr):
        f5 = "未稳" if np.isnan(x["settle5"]) else "%.2f" % x["settle5"]
        ok = (abs(x["final"] - s) <= 5) and (not x["oscillating"])
        extra = "（靠限位兜底）" if s == 10 else ""
        P("  %-9s %-10.1f %-11s %-11.2f %s%s"
          % ("%d°" % s, x["final"], f5, x["amp"], "合格" if ok else "不合格", extra))

    H("12. 发挥部分：d 突变后 5 秒内恢复（第 5 秒换距离）")
    P("  %-14s %-11s %-11s %s" % ("d 变化", "终值", "恢复(s)", "结论"))
    cases = [(15.0, 10.0), (15.0, 25.0), (10.0, 25.0), (25.0, 10.0)]
    combos = [dict(kp=KP_REC, ti=TI_REC, d=a, d2=b, t_switch=5.0, zeta=Z_REC,
                   theta_set=45.0, theta0=45.0) for a, b in cases]
    rr = transient(combos, t_end=30.0)
    for (a, b), x in zip(cases, rr):
        f5 = "未稳" if np.isnan(x["settle5"]) else "%.2f" % x["settle5"]
        ok = (not np.isnan(x["settle5"])) and x["settle5"] <= 5.0 and not x["oscillating"]
        P("  %-14s %-11.1f %-11s %s"
          % ("%g->%gcm" % (a, b), x["final"], f5, "★满足5秒" if ok else "不满足"))

    H("13. 电位器噪声 / 电源纹波（碳膜电位器的抖动）")
    P("  %-11s %-11s %-11s %s" % ("噪声rms", "终值", "角度抖动", "结论"))
    combos = [dict(kp=KP_REC, ti=TI_REC, d=15.0, zeta=Z_REC, noise=nv)
              for nv in (0.0, 0.001, 0.003, 0.010, 0.030)]
    rr = transient(combos, t_end=30.0)
    for nv, x in zip((0.0, 0.001, 0.003, 0.010, 0.030), rr):
        P("  %-11s %-11.1f %-11.2f %s"
          % ("%gmV" % (nv * 1e3), x["final"], x["amp"],
             "可接受" if x["amp"] < 1.0 else "抖动过大"))

    H("14. 风扇死区 u0 的鲁棒性（买到的风扇起转占空比不一样）")
    P("  %-8s %-12s %-12s %-12s %s"
      % ("u0", "10°终值", "45°终值", "60°终值", "结论"))
    for u0v in (0.20, 0.30, 0.35, 0.45, 0.55):
        combos = [dict(kp=KP_REC, ti=TI_REC, d=15.0, zeta=Z_REC, u0=u0v,
                       theta_set=s, theta0=20.0) for s in (10, 45, 60)]
        rr = transient(combos, t_end=30.0)
        vals = "".join("%-12s" % ("%.1f°" % x["final"]) for x in rr)
        ok = all(abs(x["final"] - s) <= 5 for x, s in zip(rr, (10, 45, 60)))
        P("  %-8.2f %s%s" % (u0v, vals, "合格" if ok else "有角度够不着"))

    H("15. 帆板材料与厚度选择（尺寸已锁定 10x15cm）")
    P("题目规定帆板 10cm x 15cm，材料和厚度自定。尺寸一固定，质量就成了唯一自由变量，")
    P("而质量同时决定两件事：① 需要多大风力（能不能吹到 60°）② 谐振频率（好不好控）。")
    P("")
    P("转动惯量按 I = m*(h^2/12 + r^2) 算，取 h=0.15m（15cm 为垂直跨度）、r=25mm")
    P("")

    def inertia(m, h=0.15, r=R_CG):
        return m * (h ** 2 / 12.0 + r ** 2)

    def eq_angle(cw, G):
        """解 cw*cos^2(th) = G*sin(th)"""
        lo, hi = 0.5, 89.5
        for _ in range(90):
            mid = 0.5 * (lo + hi)
            lhs = cw * np.cos(np.deg2rad(mid)) ** P_WIND
            rhs = G * np.sin(np.deg2rad(mid))
            if lhs > rhs:
                lo = mid
            else:
                hi = mid
        return mid

    P("  %-7s %-20s %-11s %-10s %-11s %-11s %-9s"
      % ("质量", "参考材料", "I(kg·m²)", "f_n(Hz)", "100%@15cm", "100%@25cm", "结论"))
    mat = [(3, "2mm 泡沫板"), (5, "2mm 硬纸板"), (8, "3mm 硬纸板"),
           (10, "1.5mm 硬纸板+加强"), (15, "1mm 亚克力"), (20, "1.2mm 亚克力"),
           (30, "2mm 亚克力")]
    for mg, name in mat:
        m = mg / 1000.0
        Iv = inertia(m)
        G = m * G_ACC * R_CG
        a15 = eq_angle(wind_coeff(15), G)
        a25 = eq_angle(wind_coeff(25), G)
        wn_v = np.sqrt(G * 2.1213 / Iv) / (2 * np.pi)
        if a25 >= 62:
            v = "推荐"
        elif a15 >= 62:
            v = "只能做基本要求"
        else:
            v = "吹不到 60°"
        P("  %-7s %-20s %-11.3e %-10.2f %-11s %-11s %-9s"
          % ("%dg" % mg, name, Iv, wn_v, "%.1f°" % a15, "%.1f°" % a25, v))
    P("")
    P("  >> 结论：**帆板质量必须控制在 10g 上下**。15g 就很难在 d=25cm 吹到 60°，")
    P("     20g 以上连 d=15cm 的基本要求都危险。所以用硬纸板/泡沫板，别用亚克力。")

    H("15b. 质量锁定 10g 后，重新定积分时间常数 / C1")
    m10 = 0.010
    I10 = inertia(m10)
    G10 = m10 * G_ACC * R_CG
    wn10 = np.sqrt(G10 * 2.1213 / I10)
    P("  质量 10g -> I = %.2e kg·m²，f_n = %.2f Hz（比旧假设的 1.28Hz 高）"
      % (I10, wn10 / 2 / np.pi))
    P("  谐振频率变高 = 更容易控，可以把环路调快一些。")
    P("")
    P("  %-10s %-10s %-11s %-11s %s"
      % ("τi(s)", "C1(6.8uF?)", "5°内(s)", "残留摆动", "评价"))
    tis = (0.1, 0.2, 0.33, 0.47, 0.68, 1.0, 1.5)
    combos = [dict(kp=KP_REC, ti=t, d=15.0, zeta=Z_REC, I=I10,
                   theta_set=45.0, theta0=20.0) for t in tis]
    rr = transient(combos, t_end=20.0)
    for t, x in zip(tis, rr):
        f5 = "未稳" if np.isnan(x["settle5"]) else "%.2f" % x["settle5"]
        c1 = t / 100e3
        ok = (not np.isnan(x["settle5"])) and x["settle5"] <= 5.0 and not x["oscillating"]
        P("  %-10.2f %-10s %-11s %-11.2f %s"
          % (t, "%.1fµF" % (c1 * 1e6), f5, x["amp"],
             "★可选" if ok else ("振荡" if x["oscillating"] else "慢")))

    H("15c. 修正惯量后，阻尼要求还成立吗？（10g, f_n=2.30Hz）")
    P("  %-8s" % "zeta" + "".join("%-16s" % ("τi=%.2fs" % t) for t in (0.33, 0.68, 1.0)))
    for zv in (0.05, 0.10, 0.15, 0.20, 0.30):
        row = "  %-8.2f" % zv
        combos = [dict(kp=KP_REC, ti=t, d=15.0, zeta=zv, I=I10,
                       theta_set=45.0, theta0=20.0) for t in (0.33, 0.68, 1.0)]
        rr = transient(combos, t_end=25.0)
        for x in rr:
            if x["oscillating"]:
                cell = "振荡"
            elif np.isnan(x["settle5"]):
                cell = "未稳"
            else:
                cell = "%.2fs" % x["settle5"]
            row += "%-16s" % cell
        P(row)
    P("")
    P("  >> 目标：5s 以内且不振荡。若整行出现振荡，说明该阻尼下必须放慢（加大 τi）。")

    H("15d. 轴在上沿时，配重到底需要多少？（10x15cm）")
    P("题目图纸的转轴在帆板上沿。此时帆板质心自然在轴下 7.5cm，")
    P("重力力矩 = m_total * r_eff * g，而 r_eff 由【对轴的质量矩】决定：")
    P("    m_total * r_eff = m_vane*7.5cm - m_weight*d_weight")
    P("")
    P("  %-28s %-10s %-12s %-12s %s"
      % ("配置", "r_eff(cm)", "100%@15cm", "100%@25cm", "判定"))
    cfg = [(10, 0, 0), (10, 5, 5), (10, 7, 5), (10, 10, 6),
           (15, 7, 5), (15, 10, 5), (20, 12, 5)]
    for mv, mw, dw in cfg:
        moment = mv * 7.5 - mw * dw          # g·cm
        m_tot = mv + mw
        r_eff = moment / m_tot               # cm
        G = G_ACC * moment * 1e-5            # N·m
        a15 = eq_angle(wind_coeff(15), G) if G > 0 else 89.0
        a25 = eq_angle(wind_coeff(25), G) if G > 0 else 89.0
        if r_eff <= 0:
            v = "重心反到轴上方，无稳定点"
        elif a25 >= 62:
            v = "推荐"
        elif a15 >= 62:
            v = "只够基本要求"
        else:
            v = "吹不到 60°"
        name = ("帆板%gg" % mv) + ("  无配重" if mw == 0 else
                                   "  +%gg配重@%gcm" % (mw, dw))
        P("  %-28s %-10.1f %-12s %-12s %s"
          % (name, r_eff, "%.1f°" % a15, "%.1f°" % a25, v))
    P("")
    P("  >> 关键：轴在上沿又不加配重时，r_eff=7.5cm，100%占空比只到 ~56°，**做不到 60°**。")
    P("     必须在轴上方加配重，把【对轴的质量矩】压到 40 g·cm 以下。")

    H("16. 关键问题：阻尼差但是否还能过【基本要求】？（基本要求无时间指标）")
    P("题目原文：基本要求只说“能变化”“能稳定在45±5”，没有给稳定时间；")
    P("只有发挥部分的 d 突变才要求 5 秒。所以慢环路也能拿 70 分。")
    P("")
    for zv in (0.05, 0.08, 0.10):
        P("  --- zeta = %.2f ---" % zv)
        P("  %-9s %-11s %-11s %-11s %s"
          % ("τi(s)", "C1(µF)", "5°内(s)", "终值", "判定"))
        tis = (0.68, 1.0, 1.5, 2.2, 3.3, 4.7)
        combos = [dict(kp=KP_REC, ti=t, d=15.0, zeta=zv, I=I10,
                       theta_set=45.0, theta0=20.0) for t in tis]
        rr = transient(combos, t_end=90.0, dt=4e-4)
        for t, x in zip(tis, rr):
            f5 = "未稳" if np.isnan(x["settle5"]) else "%.2f" % x["settle5"]
            if x["oscillating"]:
                v = "振荡 ✗"
            elif not np.isnan(x["settle5"]) and x["settle5"] <= 5.0:
                v = "★可拿发挥"
            elif x["settle5"] < 60:
                v = "只够基本要求"
            else:
                v = "太慢/不稳"
            P("  %-9.2f %-11.1f %-11s %-11.1f %s"
              % (t, t / 100e3 * 1e6, f5, x["final"], v))
        P("")

    H("17. 临界阻尼下的衰减诊断（判断是真收敛还是缓慢发散）")
    P("每隔 20s 统计一次摆幅；逐段变小 = 收敛，不减小 = 临界/发散。")
    P("")
    for zv in (0.04, 0.05, 0.06, 0.08):
        P("  --- zeta = %.2f, Kp=%.2f, τi=0.68s ---" % (zv, KP_REC))
        cb = [dict(kp=KP_REC, ti=0.68, d=15.0, zeta=zv, I=I10,
                   theta_set=45.0, theta0=20.0)]
        rr = transient(cb, t_end=120.0, dt=4e-4, record=True)
        t = rr[0]["t"]
        y = rr[0]["th"]
        segs = []
        for a in range(0, 120, 20):
            m = (t >= a) & (t < a + 20)
            segs.append("%.2f" % np.ptp(y[m]) if m.any() else "-")
        trend = "收敛" if float(segs[-1]) < float(segs[-2]) < float(segs[-3]) else "未衰减"
        P("    摆幅(每20s): " + "  ".join("%6s" % s for s in segs) + "   -> " + trend)
        P("    末段均值 %.1f°，最终 5°内稳定: %s"
          % (np.mean(y[t > 110]),
             "未稳" if np.isnan(rr[0]["settle5"]) else "%.1fs" % rr[0]["settle5"]))
        P("")

    H("18. 干摩擦 vs 低角度可达性（10~20° 端能不能下去）")
    P("原理：风扇只能往上吹，往下的唯一动力是重力。")
    P("帆板最低只能到 asin(tau_f / G)。摩擦再大就真的'粘住'下不去。")
    P("")
    P("注意：本仿真的摩擦用 tanh 正则化，**没有真正的静摩擦**，会低估粘滞。")
    P("     所以判定以【理论下限】为准，时域结果只作参考。")
    P("")
    tau_lim = G_TORQ * np.sin(np.deg2rad(10.0))
    P("  当前 G = %.3e N·m，摩擦预算 = G*sin(10°) = %.2f mN·m"
      % (G_TORQ, tau_lim * 1e3))
    P("")
    P("  %-14s %-12s %-13s %s" % ("干摩擦(mN·m)", "理论下限", "是否可行", "说明"))
    for tc in (0.1e-3, 0.2e-3, 0.3e-3, 0.4e-3, 0.6e-3, 1.0e-3):
        ratio = tc / G_TORQ
        th_lim = np.rad2deg(np.arcsin(ratio)) if ratio <= 1 else 180.0
        ok = tc < tau_lim
        P("  %-14s %-12s %-13s %s"
          % ("%.2f" % (tc * 1e3), "%.1f°" % th_lim,
             "可以到 10°" if ok else "卡在 %.0f° ✗" % th_lim,
             "" if ok else "超预算 %.1f 倍" % (tc / tau_lim)))
    P("")
    P("  >> 判据：静摩擦 < G*sin(10°)。G 越小（配重越重），摩擦预算越紧。")
    P("     推荐配重（10g帆板 + 10g@6cm，G≈1.5e-3）→ 预算约 0.25 mN·m。")
    P("     所以轴承/衬套的启动力矩必须 < 0.2 mN·m（留 2 倍余量）。")

    _out.close()
    print("done -> sim_output.txt")


if __name__ == "__main__":
    main()