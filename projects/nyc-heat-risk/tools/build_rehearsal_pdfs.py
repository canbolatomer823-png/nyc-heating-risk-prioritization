from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, Paragraph, Table, TableStyle


ROOT = Path("/Users/omer/aws-analytics-pipeline")
PROJECT = ROOT / "projects/nyc-heat-risk"
DATA_PATH = PROJECT / "reports/presentation_data.json"
DOWNLOADS = Path("/Users/omer/Downloads")
START_OUT = DOWNLOADS / "NYC_Heating_Risk_Baslangic_Rehberi_Omer_Canbolat.pdf"
BOARD_OUT = DOWNLOADS / "NYC_Heating_Risk_Tahta_Prova_Paketi_Omer_Canbolat.pdf"
FINAL_OUT = DOWNLOADS / "NYC_Heating_Risk_Final_Prova_Paketi_Omer_Canbolat.pdf"
SUMMARY_OUT = DOWNLOADS / "NYC_Heating_Risk_Sinif_Ozeti_Afis_Omer_Canbolat.pdf"

PAGE_W, PAGE_H = landscape(A4)


def register_fonts() -> tuple[str, str, str, str]:
    font_dir = Path("/System/Library/Fonts/Supplemental")
    pdfmetrics.registerFont(TTFont("DeckRegular", str(font_dir / "Arial Unicode.ttf")))
    pdfmetrics.registerFont(TTFont("DeckBold", str(font_dir / "Arial Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DeckTitle", str(font_dir / "Georgia Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DeckMono", str(font_dir / "Arial Narrow.ttf")))
    return "DeckRegular", "DeckBold", "DeckTitle", "DeckMono"


REGULAR, BOLD, TITLE, MONO = register_fonts()

INK = colors.HexColor("#142026")
MUTED = colors.HexColor("#5D6870")
PAPER = colors.HexColor("#F6F0E6")
PANEL = colors.HexColor("#FFFDF8")
MOSS = colors.HexColor("#1F6D58")
MOSS_DARK = colors.HexColor("#14493A")
GOLD = colors.HexColor("#C99A44")
CORAL = colors.HexColor("#D86F54")
SKY = colors.HexColor("#4F83D1")
BORDER = colors.HexColor("#D8C8B2")
GREEN_SOFT = colors.HexColor("#E4EFEA")
GOLD_SOFT = colors.HexColor("#F7E8CF")
CORAL_SOFT = colors.HexColor("#F8E8DF")
SKY_SOFT = colors.HexColor("#E8F0FB")
WHITE = colors.white


def fmt(value, digits=3):
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "—"


def fmt_int(value):
    return f"{int(value):,}"


def load_data():
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def pstyle(size=11, color=INK, font=REGULAR, leading=None, align=TA_LEFT, bold=False):
    return ParagraphStyle(
        "s",
        fontName=BOLD if bold else font,
        fontSize=size,
        leading=leading or size * 1.25,
        textColor=color,
        alignment=align,
        spaceAfter=0,
    )


def html_text(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def draw_para(c, text, x, y, w, h, style=None):
    frame = Frame(x, PAGE_H - y - h, w, h, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, showBoundary=0)
    frame.addFromList([Paragraph(html_text(text), style or pstyle())], c)


def draw_header(c, page_no, title, subtitle=None, kicker="IST-312 | NYC Heating Risk"):
    c.setFillColor(PAPER)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    c.setFillColor(MOSS_DARK)
    c.rect(0, PAGE_H - 20 * mm, PAGE_W, 20 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(BOLD, 10)
    c.drawString(18 * mm, PAGE_H - 12.5 * mm, kicker)
    c.setFont(MONO, 9)
    c.drawRightString(PAGE_W - 18 * mm, PAGE_H - 12.5 * mm, f"{page_no:02d}")
    c.setFillColor(INK)
    c.setFont(TITLE, 24)
    c.drawString(18 * mm, PAGE_H - 33 * mm, title)
    if subtitle:
        draw_para(c, subtitle, 18 * mm, 38 * mm, PAGE_W - 36 * mm, 12 * mm, pstyle(10.5, MUTED))


def draw_footer(c, label):
    c.setFillColor(MUTED)
    c.setFont(REGULAR, 7.5)
    c.drawString(18 * mm, 9 * mm, label)
    c.drawRightString(PAGE_W - 18 * mm, 9 * mm, "Omer Canbolat | 22050622")


def card(c, x, y, w, h, title, body="", accent=MOSS, fill=PANEL, title_size=11, body_size=9.5, body_color=MUTED):
    c.setFillColor(fill)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.8)
    c.roundRect(x, PAGE_H - y - h, w, h, 8, fill=1, stroke=1)
    c.setFillColor(accent)
    c.roundRect(x, PAGE_H - y - h, 5, h, 3, fill=1, stroke=0)
    c.setFillColor(accent)
    c.setFont(BOLD, title_size)
    c.drawString(x + 10, PAGE_H - y - 17, title)
    if body:
        draw_para(c, body, x + 10, y + 25, w - 18, h - 31, pstyle(body_size, body_color, leading=body_size * 1.22))


def metric(c, x, y, w, h, value, label, accent=MOSS):
    c.setFillColor(accent)
    c.roundRect(x, PAGE_H - y - h, w, h, 8, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(BOLD, 15)
    c.drawCentredString(x + w / 2, PAGE_H - y - 15, str(value))
    c.setFont(REGULAR, 8.5)
    c.drawCentredString(x + w / 2, PAGE_H - y - 30, str(label))


def centered_lines(c, text, x, y, w, size=10, color=WHITE, font=BOLD, leading=None):
    c.setFillColor(color)
    c.setFont(font, size)
    leading = leading or size * 1.16
    lines = str(text).split("\n")
    start_y = PAGE_H - y - (len(lines) - 1) * leading / 2
    for idx, line in enumerate(lines):
        c.drawCentredString(x + w / 2, start_y - idx * leading, line)


def arrow(c, x1, y1, x2, y2, color=MOSS_DARK):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(2)
    c.line(x1, PAGE_H - y1, x2, PAGE_H - y2)
    c.line(x2, PAGE_H - y2, x2 - 5, PAGE_H - y2 - 4)
    c.line(x2, PAGE_H - y2, x2 - 5, PAGE_H - y2 + 4)


def simple_table(c, rows, x, y, w, h, col_widths=None, font_size=8.5):
    styles = [
        ("BACKGROUND", (0, 0), (-1, 0), MOSS_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), BOLD),
        ("FONTNAME", (0, 1), (-1, -1), REGULAR),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size * 1.15),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#FFFAF2")),
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    table = Table(rows, colWidths=col_widths or [w / len(rows[0])] * len(rows[0]), rowHeights=None)
    table.setStyle(TableStyle(styles))
    _, table_h = table.wrapOn(c, w, h)
    table.drawOn(c, x, PAGE_H - y - table_h)


def start_guide_pdf(data):
    c = canvas.Canvas(str(START_OUT), pagesize=landscape(A4))
    draw_header(
        c,
        0,
        "Nereden Başlamalıyım?",
        "Projeyi çalışmaya başlarken tek sayfalık sıra. Koddan veya klasörlerden değil, hikayeden başla.",
        kicker="IST-312 | Başlangıç Rehberi",
    )

    card(
        c,
        18 * mm,
        54 * mm,
        260 * mm,
        24 * mm,
        "Tek ana cümle",
        "Bu proje, NYC resmi açık verilerini kullanarak ertesi gün heating/hot water complaint riski yüksek binaları tahmin eden ve bu tahmini denetim öncelik listesine çeviren bir karar destek prototipidir.",
        MOSS,
        GREEN_SOFT,
        title_size=12,
        body_size=10.2,
    )

    c.setFillColor(INK)
    c.setFont(BOLD, 15)
    c.drawString(18 * mm, PAGE_H - 89 * mm, "Bugün çalışma sırası")
    c.drawString(178 * mm, PAGE_H - 89 * mm, "Kontrol sayıları")

    steps = [
        ("1", "20 dk", "Ana hikaye", "Problem, çözüm ve sınırı tek cümleyle söyle."),
        ("2", "30 dk", "Final prova", "30 dakikalık akışı Final Prova PDF 1. sayfadan çalış."),
        ("3", "30 dk", "Broşür 2-4", "Akış, yöntem haritası ve formül savunmasını oku."),
        ("4", "20 dk", "Ana sunum", "Slaytları okuma; her slaytın ana mesajını yakala."),
        ("5", "10 dk", "Demo kontrol", "class-demo-check, final-audit ve QR linkini doğrula."),
    ]
    for idx, (num, duration, title, body) in enumerate(steps):
        y = 98 * mm + idx * 18 * mm
        accent = [MOSS, GOLD, CORAL, SKY, MOSS_DARK][idx]
        c.setFillColor(PANEL)
        c.setStrokeColor(BORDER)
        c.roundRect(18 * mm, PAGE_H - y - 14 * mm, 146 * mm, 14 * mm, 7, fill=1, stroke=1)
        c.setFillColor(accent)
        c.roundRect(18 * mm, PAGE_H - y - 14 * mm, 17 * mm, 14 * mm, 7, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(BOLD, 12)
        c.drawCentredString(26.5 * mm, PAGE_H - y - 9 * mm, num)
        c.setFillColor(accent)
        c.setFont(BOLD, 8.5)
        c.drawString(39 * mm, PAGE_H - y - 5.2 * mm, f"{duration} | {title}")
        c.setFillColor(MUTED)
        c.setFont(REGULAR, 7.2)
        c.drawString(39 * mm, PAGE_H - y - 10.5 * mm, body)

    metric(c, 178 * mm, 98 * mm, 43 * mm, 18 * mm, fmt_int(data["headline_metrics"]["complaints"]), "complaint", MOSS)
    metric(c, 228 * mm, 98 * mm, 43 * mm, 18 * mm, fmt_int(data["headline_metrics"]["buildings"]), "bina", GOLD)
    metric(c, 178 * mm, 122 * mm, 43 * mm, 18 * mm, "8.79M", "building-day", CORAL)
    metric(
        c,
        228 * mm,
        122 * mm,
        43 * mm,
        18 * mm,
        fmt(data["logistic_summary"]["ranking_metrics"]["50"]["mean_precision_at_k"], 3),
        "Mean P@50",
        SKY,
    )
    metric(
        c,
        178 * mm,
        146 * mm,
        43 * mm,
        18 * mm,
        fmt(data["oot_summary"]["ranking_metrics"]["50"]["mean_precision_at_k"], 3),
        "OOT P@50",
        MOSS_DARK,
    )
    metric(c, 228 * mm, 146 * mm, 43 * mm, 18 * mm, "READY", "audit/demo", MOSS)

    card(
        c,
        178 * mm,
        171 * mm,
        43 * mm,
        22 * mm,
        "Sunum günü açılacak sıra",
        "Ana sunum PDF → QR → dashboard/demo proof → audit raporu.",
        SKY,
        SKY_SOFT,
        title_size=7.8,
        body_size=6.7,
    )
    card(
        c,
        228 * mm,
        171 * mm,
        43 * mm,
        22 * mm,
        "Panik olursan tek cevap",
        "Şikayeti bitirdim demiyorum; denetim önceliği üretiyorum.",
        CORAL,
        CORAL_SOFT,
        title_size=7.8,
        body_size=6.7,
    )

    draw_footer(c, "Başlangıç rehberi | önce hikaye, sonra dosyalar")
    c.save()


def board_pdf(data):
    c = canvas.Canvas(str(BOARD_OUT), pagesize=landscape(A4))

    # Page 1
    draw_header(
        c,
        1,
        "Tahtaya Yazılacak Ana Hikaye",
        "Sinifta ilk 3 dakikada kurulacak problem, karar birimi ve veri akisi.",
    )
    card(
        c,
        18 * mm,
        55 * mm,
        83 * mm,
        43 * mm,
        "1 | Problem",
        "Denetim kapasitesi sınırlı.\nHer binaya aynı anda gidilemez.\n\nKarar sorusu:\nYarın hangi binalara önce gidilmeli?",
        CORAL,
        CORAL_SOFT,
        body_size=11,
    )
    card(
        c,
        110 * mm,
        55 * mm,
        82 * mm,
        43 * mm,
        "2 | Birim",
        "i = bina, t = gün\n\nY(i,t+1)=1: ertesi gün heating/hot water complaint var.\nY(i,t+1)=0: complaint yok.",
        SKY,
        SKY_SOFT,
        body_size=10.5,
    )
    card(
        c,
        202 * mm,
        55 * mm,
        76 * mm,
        43 * mm,
        "3 | Çıktı",
        "Calibrated risk score\n+ Top-50 inspection priority list\n+ why_risky açıklaması\n+ FastAPI/Docker/AWS proof",
        MOSS,
        GREEN_SOFT,
        body_size=10.5,
    )

    y = 118 * mm
    stages = [
        ("NYC 311\ncomplaints", MOSS),
        ("HPD\nbuilding + violations", GOLD),
        ("NOAA\nweather", SKY),
        ("Census CRE\nvulnerability", CORAL),
        ("Building-day\npanel", MOSS_DARK),
        ("Priority\nlist", SKY),
    ]
    x0 = 18 * mm
    box_w = 38 * mm
    gap = 8 * mm
    for idx, (label, color) in enumerate(stages):
        x = x0 + idx * (box_w + gap)
        c.setFillColor(color)
        c.roundRect(x, PAGE_H - y - 21 * mm, box_w, 21 * mm, 7, fill=1, stroke=0)
        centered_lines(c, label, x, y + 10.5 * mm, box_w, size=9.2, color=WHITE, font=BOLD)
        if idx < len(stages) - 1:
            arrow(c, x + box_w + 1.5 * mm, y + 10.5 * mm, x + box_w + gap - 2 * mm, y + 10.5 * mm)

    card(
        c,
        18 * mm,
        154 * mm,
        260 * mm,
        30 * mm,
        "Tek cümle",
        "Bu proje sikayeti ortadan kaldırdığını iddia etmez; resmi veriye dayanarak hangi binalara önce bakılması gerektiğini ölçülebilir ve tekrar üretilebilir hale getirir.",
        GOLD,
        GOLD_SOFT,
        body_size=11,
    )
    draw_footer(c, "Sayfa 1 | Problem ve veri akisi")
    c.showPage()

    # Page 2
    draw_header(c, 2, "Tahtaya Yazılacak İstatistik", "Hipotez, formül ve yöntemin projedeki görevi tek sayfada.")
    cards = [
        (
            18 * mm,
            52 * mm,
            125 * mm,
            55 * mm,
            "ANOVA | Grup ortalaması testi",
            "Soru: Aylara göre complaint yoğunluğu farklı mı?\n\nH0: μOct = μNov = ... = μMay\nH1: En az bir ay farklı\n\nF = MS_between / MS_within\nη² = SS_between / SS_total\nSonuç: F=33.62, p<0.0001, η²≈0.500",
            SKY,
            SKY_SOFT,
        ),
        (
            153 * mm,
            52 * mm,
            125 * mm,
            55 * mm,
            "Logistic Regression | Ana tahmin modeli",
            "Soru: Yarın complaint olur mu? (0/1)\n\nlogit(p)=ln(p/(1-p))\nlogit(p)=β0+β1x1+...+βkxk\np=1/(1+e^-η)\n\nÇıktı: P(Y=1), threshold, priority rank.",
            MOSS,
            GREEN_SOFT,
        ),
        (
            18 * mm,
            116 * mm,
            125 * mm,
            55 * mm,
            "Negative Binomial | Count modeli",
            "Soru: Complaint sayısı hangi faktörlerle artıyor?\n\nY_count ~ NB(μ, θ)\nlog(μ)=β0+βX\n\nNeden NB?\nVar(Y) > E(Y) ise Poisson zayıf kalır.\nSonuç: RMSE≈0.548; destek model.",
            CORAL,
            CORAL_SOFT,
        ),
        (
            153 * mm,
            116 * mm,
            125 * mm,
            55 * mm,
            "GEE / GLMM | Panel kontrolü",
            "Soru: Aynı binanın tekrar eden günleri sonucu etkiler mi?\n\nGEE: clustered/repeated observation yorumu\nGLMM: bina random intercept diagnostic\n\nNot: Primary model logistic ranking; GLMM ana model değil.",
            GOLD,
            GOLD_SOFT,
        ),
    ]
    for args in cards:
        card(c, *args, body_size=9.4)
    draw_footer(c, "Sayfa 2 | Hipotez ve modeller")
    c.showPage()

    # Page 3
    draw_header(c, 3, "Yöntem Haritası ve Kritik Sayılar", "Hangi yöntem neyi kanıtlıyor; hangi sayı hangi iddiayı destekliyor?")
    simple_table(
        c,
        [
            ["Yöntem", "İstatistik sorusu", "Projede görevi", "Kanıt"],
            ["Logistic", "Yarın complaint olur mu?", "Ana risk sıralaması", f"P@50={fmt(data['logistic_summary']['ranking_metrics']['50']['mean_precision_at_k'])}, Lift@50={fmt(data['logistic_summary']['ranking_metrics']['50']['mean_lift_at_k'],1)}x"],
            ["ANOVA", "Ay ortalamaları farklı mı?", "Mevsimsel fark testi", f"F={fmt(data['seasonal_anova']['monthly_complaints_f'],2)}, η²={fmt(data['seasonal_anova']['monthly_complaints_eta_sq'],3)}"],
            ["NB", "Complaint sayısı nasıl değişiyor?", "Count-side destek", f"RMSE={fmt(data['nb_summary']['test_rmse'],3)}"],
            ["GEE/GLMM", "Tekrar eden bina etkisi var mı?", "Panel diagnostic", f"GLMM SD={fmt(data['glmm_summary']['random_intercept_sd'],3)}"],
            ["OOT", "Zaman dışı pencere dayanıklı mı?", "Gerçekçi validasyon", f"Mean P@50={fmt(data['oot_summary']['ranking_metrics']['50']['mean_precision_at_k'],3)}"],
        ],
        18 * mm,
        55 * mm,
        260 * mm,
        72 * mm,
        [35 * mm, 58 * mm, 75 * mm, 92 * mm],
        font_size=8.5,
    )
    mx = 18 * mm
    for idx, item in enumerate(
        [
            (fmt_int(data["headline_metrics"]["complaints"]), "complaint kaydı", MOSS),
            (fmt_int(data["headline_metrics"]["buildings"]), "benzersiz bina", GOLD),
            ("8.79M", "building-day", CORAL),
            (fmt(data["logistic_summary"]["test_roc_auc"], 4), "AUC", SKY),
            (fmt(data["logistic_summary"]["ranking_metrics"]["50"]["mean_precision_at_k"], 4), "P@50", MOSS_DARK),
        ]
    ):
        metric(c, mx + idx * 52 * mm, 146 * mm, 44 * mm, 24 * mm, *item)
    card(
        c,
        18 * mm,
        176 * mm,
        260 * mm,
        17 * mm,
        "Sunumda bu sayıları nasıl oku?",
        "Veri büyüklüğü ayrı, hipotez testi ayrı, operasyonel sıralama ayrı kanıt verir. Bu yüzden sadece F1 değil; ANOVA, P@K, Lift, OOT ve why_risky birlikte okunur.",
        MOSS,
        GREEN_SOFT,
        body_size=9.3,
    )
    draw_footer(c, "Sayfa 3 | Yontem ve sayilar")
    c.showPage()

    # Page 4
    draw_header(c, 4, "Demo ve Kanıt Akışı", "Hoca 'çalışıyor mu?' derse gösterilecek net sıra.")
    card(c, 18 * mm, 52 * mm, 82 * mm, 45 * mm, "1 | Hazırlık kontrolü", "make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk class-demo-check\n\nBeklenen: Overall READY", MOSS, GREEN_SOFT, body_size=9.2)
    card(c, 108 * mm, 52 * mm, 82 * mm, 45 * mm, "2 | API kanıtı", "make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk demo-proof\n\nÜretir: health, metadata, top priorities, score response.", SKY, SKY_SOFT, body_size=9.2)
    card(c, 198 * mm, 52 * mm, 80 * mm, 45 * mm, "3 | Dashboard", "make -C ... serve\n\nTarayıcı:\nhttp://127.0.0.1:8000/dashboard?top_n=10", GOLD, GOLD_SOFT, body_size=9.2)
    card(
        c,
        18 * mm,
        112 * mm,
        125 * mm,
        58 * mm,
        "AWS cevabı",
        "AWS live proof alındı; maliyet için kapatıldı.\n\nDoğru ifade:\n'Sürekli açık public endpoint iddiası yapmıyorum. Local API ve timestamped AWS proof dosyalarını gösteriyorum.'",
        CORAL,
        CORAL_SOFT,
        body_size=10,
    )
    card(
        c,
        153 * mm,
        112 * mm,
        125 * mm,
        58 * mm,
        "QR cevabı",
        "QR kod API'yi değil, broşür PDF'ini açar.\n\n127.0.0.1 sadece benim laptopumdur.\nTelefonlardan dashboard açılmaz; sınıf QR ile broşürü görür.",
        MOSS,
        GREEN_SOFT,
        body_size=10,
    )
    draw_footer(c, "Sayfa 4 | Demo proof")
    c.showPage()

    # Page 5
    draw_header(c, 5, "Hoca Sorarsa Kısa Cevaplar", "Riskli iddia kurmadan, net ve savunulabilir cevaplar.")
    simple_table(
        c,
        [
            ["Soru", "Kısa cevap"],
            ["Tam olarak neyi çözüyor?", "Sınırlı denetim kapasitesinde önce hangi binalara bakılacağını sıralıyor."],
            ["Heat wave modeli mi?", "Hayır. Bu heating season complaint modelidir."],
            ["Ana model hangisi?", "Calibrated logistic ranking."],
            ["GLMM ana model mi?", "Hayır. Diagnostic; ana karar listesi logistic modelden gelir."],
            ["ANOVA ne işe yaradı?", "Aylara göre complaint ortalaması farklı mı test etti."],
            ["NB neden var?", "Complaint sayısı count veri; overdispersion için destek model."],
            ["F1 neden tek başarı değil?", "Pozitif sınıf nadir; P@50 ve Lift@50 operasyonel olarak daha doğrudan."],
            ["Canlı ürün mü?", "Hayır. Production'a taşınabilir audit-ready prototip."],
        ],
        18 * mm,
        52 * mm,
        260 * mm,
        112 * mm,
        [58 * mm, 202 * mm],
        font_size=8.6,
    )
    card(
        c,
        18 * mm,
        174 * mm,
        260 * mm,
        18 * mm,
        "Kapanış cümlesi",
        "Resmi veriyi, istatistiksel modellemeyi ve servis mimarisini birleştirerek complaint verisini sadece rapor değil, denetim önceliği üreten karar destek aracına dönüştürdüm.",
        GOLD,
        GOLD_SOFT,
        body_size=9.4,
    )
    draw_footer(c, "Sayfa 5 | Soru-cevap")
    c.save()


def final_pdf(data):
    c = canvas.Canvas(str(FINAL_OUT), pagesize=landscape(A4))
    slide_groups = [
        (
            "Slayt 1-2 | Problem ve karar sorusu",
            "Kapak: 'Bu proje resmi veriyle ertesi gün heating/hot water complaint riski yüksek binaları sıralıyor.'\n\nQR: 'Broşür telefondan açılır; problem, veri, yöntem ve sınırlar tek yerde.'\n\nKarar problemi: 'Her binaya gidilemez; bu yüzden asıl soru yarın ilk hangi binalara bakılmalı?'",
            "Sakın: 'Sikayeti tamamen çözdüm' deme. Doğru ifade: 'Denetim önceliği üretiyorum.'",
        ),
        (
            "Slayt 3-4 | Veri ve leakage audit",
            "311 + HPD + NOAA + CRE tek building-day panelde birleşti.\n\nHedef: Y(i,t+1)=1 ise ertesi gün complaint var.\n\nLeakage audit: feature'lar sadece t gününe kadar bilinen bilgilerden üretildi; future as-of ve target mismatch kontrol edildi.",
            "Bu bölüm güven yaratır. Modelden önce veri tasarımının doğru olduğunu göster.",
        ),
        (
            "Slayt 5-6 | ANOVA, validation, calibration",
            "ANOVA: H0 ay ortalamaları eşit. F=33.62, p<0.0001, eta²≈0.500.\n\nValidation: düşük prevalence nedeniyle accuracy yeterli değil. AUC, P@50, Lift@50, calibration ve OOT birlikte okundu.",
            "F1 sorulursa: 'Düşük base-rate için ranking metriği operasyonel olarak daha doğru' cevabını ver.",
        ),
        (
            "Slayt 7-8 | Modeller ve istatistiksel bulgu",
            "Primary model: calibrated logistic ranking.\n\nGEE: tekrar eden bina-gün yapısını yorumlamak.\nNB: complaint sayısını count model olarak okumak.\nGLMM: random-intercept diagnostic, ana karar modeli değil.",
            "Bu ayrımı net yaparsan hoca mixed-effects sorusunda yakalayamaz.",
        ),
        (
            "Slayt 9-13 | Çıktı, cloud, demo, kapanış",
            "Operasyonel çıktı: Top-50 priority list + why_risky.\n\nCloud: FastAPI + Docker + S3/ECR/EKS proof; endpoint maliyet için kapatıldı.\n\nDemo: class-demo-check ve demo-proof ile kanıt.\n\nKapanış: 'Karar destek prototipi, otomatik denetim sistemi değil.'",
            "QR slayt kapaktan sonra; kapanış slaytında sınırları dürüst söyle.",
        ),
    ]

    # Page 1
    draw_header(c, 1, "30 Dakikalık Sunum Akışı", "Bu sayfa sunum masasında açık dursun; ritmi ve ana mesajı kaçırmazsın.")
    times = [
        ("0-2", "Problem", "Isınma/sıcak su şikayeti kamu hizmeti sorunu; amaç şikayeti bitirdim demek değil, erken öncelik üretmek."),
        ("2-5", "Karar sorusu", "Her binaya aynı anda gidilemez. Soru: yarın ilk hangi binalara bakılmalı?"),
        ("5-8", "Veri paneli", "311, HPD, NOAA ve Census CRE tek building-day panelde birleşti; i=bina, t=gün."),
        ("8-11", "Leakage audit", "Sadece t gününe kadar bilinen bilgi kullanıldı; gelecek bilgi modele sokulmadı."),
        ("11-14", "ANOVA", "H0: ay ortalamaları eşit. F=33.62, p<0.0001; mevsimsel fark anlamlı."),
        ("14-18", "Logistic + validation", "Ana model calibrated logistic ranking. P@50, Lift@50, AUC, calibration birlikte okunur."),
        ("18-21", "GEE/NB/GLMM", "NB count hedefi; GEE/GLMM tekrar bina yapısı için diagnostic, ana karar modeli değil."),
        ("21-24", "Priority output", "Top-50 priority list, why_risky açıklaması ve borough dağılımını göster."),
        ("24-28", "Demo proof", "class-demo-check, demo-proof, API health, dashboard ve QR broşür kanıtlarını aç."),
        ("28-30", "Kapanış", "Karar destek prototipi; otomatik denetim/ceza sistemi değil. Sınırları dürüst söyle."),
    ]
    x = 18 * mm
    for idx, (minute, label, body) in enumerate(times):
        y = 54 * mm + (idx % 5) * 25 * mm
        col_x = x + (idx // 5) * 132 * mm
        accent = GOLD if idx in (4, 5, 6) else MOSS
        metric(c, col_x, y, 28 * mm, 18 * mm, minute, "dk", MOSS if idx < 5 else SKY)
        card(
            c,
            col_x + 33 * mm,
            y,
            92 * mm,
            18 * mm,
            label,
            body,
            accent,
            PANEL,
            title_size=9.5,
            body_size=6.9,
        )
    card(
        c,
        18 * mm,
        180 * mm,
        260 * mm,
        16 * mm,
        "Ana vaat",
        "Resmi verilerle ertesi gün complaint riski yüksek binaları sıralayan, neden riskli olduğunu açıklayan ve denetim önceliğine çeviren çalışan prototip.",
        CORAL,
        CORAL_SOFT,
        body_size=9.4,
    )
    draw_footer(c, "Final prova | Akis")
    c.showPage()

    # Pages 2-6
    for page_no, (title, body, note) in enumerate(slide_groups, start=2):
        draw_header(c, page_no, title, "Slayt anlatim metni: once iddia, sonra kanit, sonra gecis cumlesi.")
        card(c, 18 * mm, 55 * mm, 170 * mm, 82 * mm, "Söyleyeceğin metin", body, MOSS, GREEN_SOFT, body_size=11)
        card(c, 198 * mm, 55 * mm, 80 * mm, 82 * mm, "Dikkat", note, CORAL, CORAL_SOFT, body_size=10.5)
        card(
            c,
            18 * mm,
            150 * mm,
            260 * mm,
            36 * mm,
            "Geçiş cümlesi",
            "Bir sonraki slayta geçerken 'Bu noktada...' veya 'Bu yüzden...' diye bağla. Slaytları tek tek okumak yerine her slaytta bir iddia ve bir kanıt göster.",
            GOLD,
            GOLD_SOFT,
            body_size=10,
        )
        draw_footer(c, f"Final prova | {title}")
        c.showPage()

    # Page 7
    draw_header(c, 7, "İstatistik Cevap Kartı", "Regresyon, ANOVA, NB, GEE ve GLMM'i lisans seviyesinde savunma metni.")
    simple_table(
        c,
        [
            ["Yöntem", "Kısa savunma"],
            ["Logistic regression", "Hedef 0/1 olduğu için kullandım. Olasılık üretir; bu olasılıkla priority ranking yapılır."],
            ["ANOVA", "Modelden önce aylara göre complaint ortalaması farklı mı test ettim. H0 eşit ortalamalar; p<0.0001 ile reddedildi."],
            ["Negative Binomial", "Complaint sayısı count veridir. Overdispersion riski nedeniyle Poisson yerine NB destek model olarak kullanıldı."],
            ["GEE", "Aynı binanın tekrar eden günleri bağımsız değildir. GEE clustered panel yorumunu destekler."],
            ["GLMM", "Bina random intercept fikrini diagnostic olarak kontrol eder; ana model değildir."],
            ["Calibration/OOT", "Skorların olasılık yorumu ve zaman dışı dayanıklılığı için eklendi."],
        ],
        18 * mm,
        55 * mm,
        260 * mm,
        105 * mm,
        [48 * mm, 212 * mm],
        font_size=8.8,
    )
    mini_cards = [
        ("Logit formülü", "logit(p)=ln(p/(1-p))=β0+βX\np=1/(1+e^-η)", MOSS, GREEN_SOFT),
        ("ANOVA formülü", "F = MS_between / MS_within\nη² = SS_between / SS_total", SKY, SKY_SOFT),
        ("NB formülü", "Y_count ~ NB(μ,θ)\nlog(μ)=β0+βX", CORAL, CORAL_SOFT),
        ("Panel notu", "GEE: cluster bina\nGLMM: random intercept diagnostic", GOLD, GOLD_SOFT),
    ]
    for idx, (title, body, accent, fill) in enumerate(mini_cards):
        card(
            c,
            18 * mm + idx * 65 * mm,
            120 * mm,
            58 * mm,
            38 * mm,
            title,
            body,
            accent,
            fill,
            title_size=9.5,
            body_size=8.9,
        )
    card(
        c,
        18 * mm,
        172 * mm,
        260 * mm,
        20 * mm,
        "Altın cümle",
        "Tek bir yöntemle her şeyi çözmedim; her yöntem farklı bir istatistik sorusuna hizmet etti.",
        GOLD,
        GOLD_SOFT,
        body_size=10.5,
    )
    draw_footer(c, "Final prova | Yontem savunmasi")
    c.showPage()

    # Page 8
    draw_header(c, 8, "Canlı Demo ve Acil Durum Planı", "Projeyi çalışır göstermek için net komut sırası.")
    card(c, 18 * mm, 55 * mm, 125 * mm, 38 * mm, "Komut 1", "make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk class-demo-check\n\nBeklenen: Overall READY", MOSS, GREEN_SOFT, body_size=9.2)
    card(c, 153 * mm, 55 * mm, 125 * mm, 38 * mm, "Komut 2", "make -C /Users/omer/aws-analytics-pipeline/projects/nyc-heat-risk demo-proof\n\nKanıt: demo_proof.md + JSON cevapları", SKY, SKY_SOFT, body_size=9.2)
    card(c, 18 * mm, 105 * mm, 125 * mm, 50 * mm, "Dashboard", "make -C ... serve\n\nhttp://127.0.0.1:8000/dashboard?top_n=10\n\nNot: 127.0.0.1 sadece benim laptopum.", GOLD, GOLD_SOFT, body_size=9.2)
    card(c, 153 * mm, 105 * mm, 125 * mm, 50 * mm, "Eğer demo açılmazsa", "Panik yok. class_demo_check.md, demo_proof.md ve final_project_audit.md dosyalarını göster.\n\nBunlar endpointlerin ve artifact'lerin test edildiğini kaydeder.", CORAL, CORAL_SOFT, body_size=9.5)
    card(c, 18 * mm, 170 * mm, 260 * mm, 18 * mm, "Kapanış", "Bu proje otomatik denetim sistemi değil; resmi veriye dayalı, açıklanabilir ve servislenebilir karar destek prototipi.", MOSS, GREEN_SOFT, body_size=10)
    draw_footer(c, "Final prova | Demo")
    c.save()


def summary_poster_pdf(data):
    width, height = PAGE_W, PAGE_H
    c = canvas.Canvas(str(SUMMARY_OUT), pagesize=landscape(A4))
    c.setFillColor(PAPER)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # Editorial header
    c.setFillColor(MOSS_DARK)
    c.rect(0, height - 28 * mm, width, 28 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#DCECE3"))
    c.circle(width - 22 * mm, height - 17 * mm, 34 * mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(BOLD, 10)
    c.drawString(15 * mm, height - 11 * mm, "IST-312 | Omer Canbolat | 22050622")
    c.setFont(TITLE, 22)
    c.drawString(15 * mm, height - 22 * mm, "NYC Heating Complaint Risk")

    draw_para(
        c,
        "Resmi açık verilerle ertesi gün heating / hot water complaint riski yüksek binaları sıralayan karar destek prototipi.",
        15 * mm,
        36 * mm,
        190 * mm,
        14 * mm,
        pstyle(12, INK, REGULAR, leading=15),
    )

    # Main problem strip
    card(
        c,
        15 * mm,
        56 * mm,
        128 * mm,
        32 * mm,
        "Çözdüğüm karar problemi",
        "Denetim kapasitesi sınırlıysa, yarın hangi binalara önce gidilmeli? Model bu soruya günlük risk sıralaması ve why_risky açıklamasıyla cevap verir.",
        CORAL,
        CORAL_SOFT,
        title_size=11,
        body_size=9.7,
    )

    # Flow
    stages = [
        ("311", "complaint", MOSS),
        ("HPD", "bina + violation", GOLD),
        ("NOAA", "hava", SKY),
        ("CRE", "kırılganlık", CORAL),
        ("Logit", "risk skoru", MOSS_DARK),
        ("Top-50", "öncelik", SKY),
    ]
    x0 = 15 * mm
    y = 104 * mm
    box_w = 21 * mm
    gap = 2 * mm
    for idx, (label, sub, fill) in enumerate(stages):
        x = x0 + idx * (box_w + gap)
        c.setFillColor(fill)
        c.roundRect(x, height - y - 20 * mm, box_w, 20 * mm, 6, fill=1, stroke=0)
        centered_lines(c, f"{label}\n{sub}", x, y + 10 * mm, box_w, size=7.3, color=WHITE, font=BOLD)
        if idx < len(stages) - 1:
            c.setStrokeColor(MOSS_DARK)
            c.setLineWidth(1.4)
            c.line(x + box_w + 1.5 * mm, height - y - 10 * mm, x + box_w + gap - 1.5 * mm, height - y - 10 * mm)

    # Metrics
    c.setFillColor(INK)
    c.setFont(TITLE, 16)
    c.drawString(166 * mm, height - 60 * mm, "Akılda kalacak kanıtlar")
    metric_items = [
        (fmt_int(data["headline_metrics"]["complaints"]), "complaint kaydı", MOSS),
        (fmt_int(data["headline_metrics"]["buildings"]), "benzersiz bina", GOLD),
        ("8.79M", "building-day", CORAL),
        (fmt(data["logistic_summary"]["ranking_metrics"]["50"]["mean_lift_at_k"], 1) + "x", "Lift@50", SKY),
        (fmt(data["seasonal_anova"]["monthly_complaints_f"], 2), "ANOVA F", MOSS_DARK),
        (fmt(data["oot_summary"]["ranking_metrics"]["50"]["mean_precision_at_k"], 3), "OOT P@50", CORAL),
    ]
    for idx, item in enumerate(metric_items):
        col = idx % 2
        row = idx // 2
        metric(c, 166 * mm + col * 52 * mm, 70 * mm + row * 28 * mm, 45 * mm, 21 * mm, *item)

    # Methods panel
    card(
        c,
        15 * mm,
        150 * mm,
        260 * mm,
        28 * mm,
        "Yöntemleri nasıl kullandım?",
        "Logistic regression: P(Y=1) risk olasılığı ve sıralama.\nANOVA: ay ortalamaları farklı mı? H0 eşit ortalamalar.\nNegative Binomial: complaint sayısı gibi count veri.\nGEE/GLMM: aynı binanın tekrar eden günleri için diagnostic.",
        MOSS,
        GREEN_SOFT,
        title_size=11,
        body_size=8.2,
    )

    # Bottom statement
    c.setFillColor(MOSS_DARK)
    c.roundRect(15 * mm, 12 * mm, 260 * mm, 17 * mm, 8, fill=1, stroke=0)
    draw_para(
        c,
        "Kısa sonuç: Bu sistem otomatik karar vermez; denetçiye resmi veriyle açıklanabilir öncelik listesi sunar.",
        20 * mm,
        183 * mm,
        250 * mm,
        8 * mm,
        pstyle(8.8, WHITE, BOLD, leading=10.5),
    )
    c.save()


def main():
    data = load_data()
    start_guide_pdf(data)
    board_pdf(data)
    final_pdf(data)
    summary_poster_pdf(data)
    print(START_OUT)
    print(BOARD_OUT)
    print(FINAL_OUT)
    print(SUMMARY_OUT)


if __name__ == "__main__":
    main()
