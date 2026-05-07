from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


WIDTH = 1800
HEIGHT = 1460

BG = "#f6f1e8"
PANEL = "#fbf8f2"
BORDER = "#d7ccba"
INK = "#172126"
GRAPHITE = "#465158"
GREEN = "#1f9d69"
GREEN_DARK = "#136044"
GOLD = "#d6a447"
CORAL = "#db6e57"
SKY = "#5b8def"
WHITE = "#ffffff"

OUT_PATH = Path(
    "<project-root>/outputs/board-visuals/nyc-heat-risk-board-visual.png"
)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Avenir Next.ttc" if bold else "/System/Library/Fonts/Supplemental/Avenir.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


TITLE = load_font(58, bold=True)
SUBTITLE = load_font(26)
SECTION = load_font(28, bold=True)
LABEL = load_font(20, bold=True)
BODY = load_font(22)
SMALL = load_font(17)
MONO = load_font(19)


def draw_round_box(draw: ImageDraw.ImageDraw, xy, fill=PANEL, outline=BORDER, width=2, radius=24):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_text_block(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font, fill=INK, max_width=320, line_gap=6):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_gap
    return y


def centered(draw: ImageDraw.ImageDraw, box, text: str, font, fill=WHITE):
    x1, y1, x2, y2 = box
    w = draw.textlength(text, font=font)
    h = font.size
    draw.text((x1 + (x2 - x1 - w) / 2, y1 + (y2 - y1 - h) / 2 - 2), text, font=font, fill=fill)


def arrow(draw: ImageDraw.ImageDraw, x1, y1, x2, y2, fill=GREEN_DARK, width=8):
    draw.line((x1, y1, x2, y2), fill=fill, width=width)
    dx = x2 - x1
    dy = y2 - y1
    if abs(dx) >= abs(dy):
        sign = 1 if dx >= 0 else -1
        tip = (x2, y2)
        p1 = (x2 - 22 * sign, y2 - 14)
        p2 = (x2 - 22 * sign, y2 + 14)
    else:
        sign = 1 if dy >= 0 else -1
        tip = (x2, y2)
        p1 = (x2 - 14, y2 - 22 * sign)
        p2 = (x2 + 14, y2 - 22 * sign)
    draw.polygon([tip, p1, p2], fill=fill)


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    # Background accents
    draw.ellipse((1370, -90, 1860, 400), fill="#dcefe5")
    draw.ellipse((-120, 980, 260, 1360), fill="#efe0bd")

    # Main frame
    draw_round_box(draw, (34, 28, WIDTH - 34, HEIGHT - 28), fill=PANEL, outline=BORDER, width=3, radius=28)
    draw.line((34, 118, WIDTH - 34, 118), fill=BORDER, width=2)

    # Header
    draw.text((78, 54), "NYC HEATING COMPLAINT RISK | TAHTA ANLATIM PLANI", font=LABEL, fill=GREEN_DARK)
    draw.text((80, 150), "Projeyi Tahtada Nasıl Anlatacağım?", font=TITLE, fill=INK)
    draw_text_block(
        draw,
        82,
        236,
        "Problem -> Veri -> Hipotez -> Model -> Test -> Operasyonel çıktı akışını tek bakışta gösteren kılavuz.",
        SUBTITLE,
        fill=GRAPHITE,
        max_width=900,
        line_gap=8,
    )

    # Top flow
    flow_y = 360
    box_w = 240
    box_h = 88
    start_x = 80
    gap = 44
    flow = [
        ("1. Problem", "Sınırlı kapasite", GREEN),
        ("2. Veri", "311 + HPD + NOAA + CRE", GOLD),
        ("3. Hipotez", "Hava + geçmiş + kırılganlık", CORAL),
        ("4. Model", "Logit + GEE + NB + diag", SKY),
        ("5. Test", "Calib. + ANOVA + audit", GREEN),
        ("6. Çıktı", "Inspection priority list", GOLD),
    ]
    boxes = []
    for i, (title, subtitle, color) in enumerate(flow):
        x = start_x + i * (box_w + gap)
        rect = (x, flow_y, x + box_w, flow_y + box_h)
        boxes.append(rect)
        draw_round_box(draw, rect, fill=color, outline=color, width=2, radius=24)
        draw.text((x + 18, flow_y + 18), title, font=LABEL, fill=WHITE)
        draw.text((x + 18, flow_y + 50), subtitle, font=SMALL, fill=WHITE)
        if i < len(flow) - 1:
            arrow(draw, x + box_w + 10, flow_y + box_h // 2, x + box_w + gap - 10, flow_y + box_h // 2)

    # Left panel: board equations and hypotheses
    left = (74, 510, 860, 1360)
    draw_round_box(draw, left, fill=WHITE, outline=BORDER, width=2)
    draw.text((100, 540), "Tahtaya Yazılacak Çekirdek Kısım", font=SECTION, fill=GREEN_DARK)

    draw.text((104, 600), "1) Problem ve karar cümlesi", font=LABEL, fill=CORAL)
    draw.text((120, 638), "Yarın önce hangi binalara gidilmeli?", font=BODY, fill=INK)
    draw.text((120, 676), "Amaç: heating / hot water complaint riskini önceliklendirmek", font=BODY, fill=GRAPHITE)

    draw.text((104, 738), "2) Analiz birimi ve hedefler", font=LABEL, fill=CORAL)
    draw.text((120, 776), "Analiz birimi = building-day", font=MONO, fill=INK)
    draw.text((120, 810), "Y1 = next_day_positive_flag", font=MONO, fill=INK)
    draw.text((120, 844), "Y2 = next_day_complaint_count", font=MONO, fill=INK)

    draw.text((104, 900), "3) Genel model mantığı", font=LABEL, fill=CORAL)
    draw.text((120, 938), "Risk_it = f(weather_it, history_it, violations_it, vulnerability_i)", font=MONO, fill=INK)
    draw.text((120, 974), "logit(P(Y1=1)) = beta0 + betaX + u_building", font=MONO, fill=INK)
    draw.text((120, 1010), "log(E[Y2])) = beta0 + betaX", font=MONO, fill=INK)

    draw.text((104, 1068), "4) Hipotezler", font=LABEL, fill=CORAL)
    draw.text((120, 1106), "H1: Weather + history + violations + vulnerability -> risk artışı", font=SMALL, fill=INK)
    draw.text((120, 1136), "H0(ANOVA): Aylık complaint ortalamaları eşit", font=SMALL, fill=INK)
    draw.text((120, 1164), "H1(ANOVA): En az bir ay farklı", font=SMALL, fill=INK)

    # Right top panel: why each method
    rt = (892, 510, 1726, 884)
    draw_round_box(draw, rt, fill=WHITE, outline=BORDER, width=2)
    draw.text((918, 540), "Hangi Yöntemi Neden Kullandım?", font=SECTION, fill=GREEN_DARK)

    method_cards = [
        ((920, 600, 1115, 720), GREEN, "Calibrated Logistic", "Benchmark + olasılık + ranking"),
        ((1130, 600, 1325, 720), GOLD, "GEE Logistic", "Clustered / repeated observations"),
        ((1340, 600, 1535, 720), CORAL, "GLMM Diagnostic", "Subset fit + convergence note"),
        ((1550, 600, 1710, 720), SKY, "Negative Binomial", "Count data + overdispersion"),
    ]
    for rect, color, title, body in method_cards:
        draw_round_box(draw, rect, fill=color, outline=color, width=2, radius=22)
        draw_text_block(draw, rect[0] + 14, rect[1] + 18, title, LABEL, fill=WHITE, max_width=rect[2] - rect[0] - 24, line_gap=4)
        draw_text_block(draw, rect[0] + 14, rect[1] + 58, body, SMALL, fill=WHITE, max_width=rect[2] - rect[0] - 24, line_gap=4)

    draw.text((920, 760), "Kısa savunma:", font=LABEL, fill=CORAL)
    draw_text_block(
        draw,
        920,
        798,
        "Prediction: calibrated logistic. Clustered inference: GEE. Count hedef: Negative Binomial. GLMM: diagnostic subset ve convergence notu.",
        BODY,
        fill=GRAPHITE,
        max_width=760,
        line_gap=6,
    )

    # Right bottom panel: what to say statistically
    rb = (892, 906, 1726, 1360)
    draw_round_box(draw, rb, fill=WHITE, outline=BORDER, width=2)
    draw.text((918, 936), "İstatistikte Özellikle Söyle", font=SECTION, fill=GREEN_DARK)

    stat_rows = [
        ("Regression", "Katsayı yönünü ve büyüklüğünü yorumlamak için kullandım."),
        ("GEE", "Aynı bina tekrar gözlendiği için bağımsızlık varsayımını gevşettim."),
        ("GLMM", "Tam panelde ana kanıt değil; diagnostic subset ve convergence notuyla raporladım."),
        ("ANOVA", "Heat-season boyunca aylık complaint yükü farkını test ettim."),
        ("Effect > 1", "İlgili değişken arttıkça beklenen risk artıyor."),
    ]
    y = 990
    for label, body in stat_rows:
        draw.rounded_rectangle((920, y, 1040, y + 48), radius=16, fill=PANEL, outline=BORDER, width=1)
        centered(draw, (920, y, 1040, y + 48), label, LABEL, fill=GREEN_DARK)
        draw_text_block(draw, 1062, y + 10, body, SMALL, fill=GRAPHITE, max_width=610, line_gap=4)
        y += 68

    draw.text((920, 1330), "Hazır sayı: ANOVA F=33.62 | GEE CRE OR=2.58 | why_risky explanation hazır", font=SMALL, fill=INK)

    image.save(OUT_PATH)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
