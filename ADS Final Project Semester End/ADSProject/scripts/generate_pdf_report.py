"""Utility script to compile the official Alliance University MCA Project Report PDF."""
import os
import shutil
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas

ROOT_DIR = Path(__file__).resolve().parent.parent

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute total page count for 'Page X of Y'."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            return  # Skip header and footer on cover page

        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header
        self.drawString(
            54, 11.25 * inch,
            "ALLIANCE UNIVERSITY  |  Alliance School of Advanced Computing  |  MCA Semester 1"
        )
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 11.15 * inch, A4[0] - 54, 11.15 * inch)

        # Running Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 54, 36, page_text)
        self.drawString(54, 36, "Bitewise: Local Menu Comparison and Dish Finder")
        self.line(54, 48, A4[0] - 54, 48)

        self.restoreState()


def build_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    primary_color = colors.HexColor("#1e3a8a")  # Deep Navy
    text_dark = colors.HexColor("#0f172a")      # Slate 900
    text_muted = colors.HexColor("#475569")     # Slate 600
    border_color = colors.HexColor("#e2e8f0")

    style_cover_title = ParagraphStyle(
        'CoverTitle', fontName='Helvetica-Bold', fontSize=20, leading=24, alignment=1, textColor=primary_color
    )
    style_cover_subtitle = ParagraphStyle(
        'CoverSubTitle', fontName='Helvetica-Bold', fontSize=13, leading=17, alignment=1, textColor=text_dark
    )
    style_cover_body = ParagraphStyle(
        'CoverBody', fontName='Helvetica', fontSize=10, leading=14, alignment=1, textColor=text_muted
    )
    style_h1 = ParagraphStyle(
        'SectionH1', fontName='Helvetica-Bold', fontSize=15, leading=19, textColor=primary_color, spaceBefore=14, spaceAfter=8, keepWithNext=True
    )
    style_h2 = ParagraphStyle(
        'SectionH2', fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor("#1e293b"), spaceBefore=10, spaceAfter=5, keepWithNext=True
    )
    style_body = ParagraphStyle(
        'NormalBody', fontName='Helvetica', fontSize=9.5, leading=14, textColor=text_dark, spaceAfter=7
    )
    style_bullet = ParagraphStyle(
        'BulletText', fontName='Helvetica', fontSize=9.5, leading=14, textColor=text_dark, leftIndent=15, spaceAfter=4
    )
    style_table_header = ParagraphStyle(
        'TableHeader', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.white, alignment=0
    )
    style_table_cell = ParagraphStyle(
        'TableCell', fontName='Helvetica', fontSize=8.5, leading=11, textColor=text_dark
    )
    style_table_cell_bold = ParagraphStyle(
        'TableCellBold', fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=text_dark
    )

    story = []
    
    # Check for images in static, data, or artifacts
    logo1 = ROOT_DIR / "static" / "image1.jpeg"
    logo2 = ROOT_DIR / "static" / "image2.jpeg"
    if not logo1.exists():
        # Fallback to user uploaded media in antigravity if present
        alt_logo1 = Path(r"C:\Users\SHAURYA VENKTA\Desktop\ADSProject\static\image1.jpeg")

    # =========================================================================
    # PAGE 1: COVER PAGE
    # =========================================================================
    if logo1.exists():
        img1 = Image(str(logo1), width=4.8 * inch, height=1.35 * inch)
        img1.hAlign = 'CENTER'
        story.append(img1)
        story.append(Spacer(1, 10))

    story.append(Paragraph("ALLIANCE UNIVERSITY", style_cover_title))
    story.append(Spacer(1, 3))
    story.append(Paragraph("Alliance School of Advanced Computing", style_cover_subtitle))
    story.append(Spacer(1, 3))
    story.append(Paragraph("Department of Computer Applications", style_cover_body))
    story.append(Paragraph("Program: Master of Computer Applications (MCA) &bull; Semester 1", style_cover_body))
    story.append(Paragraph("ACADEMIC YEAR: 2026&ndash;2028", style_cover_body))
    story.append(Spacer(1, 12))

    if logo2.exists():
        img2 = Image(str(logo2), width=1.5 * inch, height=1.5 * inch)
        img2.hAlign = 'CENTER'
        story.append(img2)
        story.append(Spacer(1, 14))

    p_box_data = [
        [Paragraph("<b>PROJECT REPORT</b>", ParagraphStyle('PBoxHead', fontName='Helvetica-Bold', fontSize=10, alignment=1, textColor=primary_color))],
        [Spacer(1, 4)],
        [Paragraph("Bitewise: Local Menu Comparison and Dish Finder", ParagraphStyle('PBoxTitle', fontName='Helvetica-Bold', fontSize=13, alignment=1, leading=17, textColor=text_dark))],
        [Spacer(1, 4)],
        [Paragraph("An Applied Data Science &amp; Machine Learning Feasibility Engine", ParagraphStyle('PBoxSub', fontName='Helvetica-Oblique', fontSize=9, alignment=1, textColor=text_muted))]
    ]
    p_box = Table(p_box_data, colWidths=[400])
    p_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    p_box.hAlign = 'CENTER'
    story.append(p_box)
    story.append(Spacer(1, 22))

    meta_data = [
        [Paragraph("<b>Student Name:</b>", style_table_cell_bold), Paragraph("Shaurya Venkta", style_table_cell)],
        [Paragraph("<b>Register Number:</b>", style_table_cell_bold), Paragraph("[Register Number]", style_table_cell)],
        [Paragraph("<b>Degree &amp; Semester:</b>", style_table_cell_bold), Paragraph("MCA &ndash; Semester 1", style_table_cell)],
        [Paragraph("<b>Project Guide:</b>", style_table_cell_bold), Paragraph("Oleti Durga Bravish", style_table_cell)],
    ]
    meta_table = Table(meta_data, colWidths=[130, 240])
    meta_table.setStyle(TableStyle([
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
    ]))
    meta_table.hAlign = 'CENTER'
    story.append(meta_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: ACKNOWLEDGEMENT
    # =========================================================================
    story.append(Paragraph("ACKNOWLEDGEMENT", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=14))

    ack_p1 = "I would like to express my sincere gratitude to everyone who supported and guided me throughout the successful completion of this project."
    ack_p2 = "I am thankful to my Project Guide for providing valuable guidance, suggestions, encouragement, and continuous support throughout the development of this project. I also express my gratitude to the faculty members and my institution for providing the necessary resources and a supportive learning environment."
    ack_p3 = "I would also like to thank my friends and classmates for their cooperation and support during the completion of this project. Finally, I am deeply grateful to my family for their constant encouragement, motivation, and support."
    ack_p4 = "I sincerely thank everyone who contributed directly or indirectly to the successful completion of this project."

    story.append(Paragraph(ack_p1, style_body))
    story.append(Paragraph(ack_p2, style_body))
    story.append(Paragraph(ack_p3, style_body))
    story.append(Paragraph(ack_p4, style_body))
    story.append(Spacer(1, 20))

    ack_details = [
        [Paragraph("<b>Student Name:</b>", style_table_cell_bold), Paragraph("Shaurya Venkta", style_table_cell)],
        [Paragraph("<b>Register Number:</b>", style_table_cell_bold), Paragraph("[Register Number]", style_table_cell)],
        [Paragraph("<b>Project Title:</b>", style_table_cell_bold), Paragraph("Bitewise: Local Menu Comparison and Dish Finder", style_table_cell)],
        [Paragraph("<b>Project Faculty &amp; Guide:</b>", style_table_cell_bold), Paragraph("Oleti Durga Bravish", style_table_cell)],
    ]
    ack_t = Table(ack_details, colWidths=[150, 310])
    ack_t.setStyle(TableStyle([
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
    ]))
    story.append(ack_t)
    story.append(Spacer(1, 45))

    sig_data = [
        [Paragraph("____________________________<br/><b>Signature of Student</b><br/>Shaurya Venkta", style_body),
         Paragraph("____________________________<br/><b>Signature of Faculty &amp; Project Guide</b><br/>Oleti Durga Bravish", style_body)]
    ]
    sig_t = Table(sig_data, colWidths=[240, 240])
    sig_t.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    story.append(sig_t)

    story.append(PageBreak())

    # =========================================================================
    # CORE SECTIONS
    # =========================================================================
    story.append(Paragraph("1. Abstract", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=10))
    abstract_text = (
        "The exponential growth of on-demand food delivery platforms has catalyzed the rise of cloud kitchens—delivery-only "
        "commercial food preparation facilities. However, high operational failure rates persist due to market cannibalization and "
        "severe menu redundancy within concentrated delivery radiuses. Operators frequently deploy duplicate menus (such as generic "
        "biryani, burger, or North Indian concepts) in trade areas that are already hyper-saturated, while genuine consumer demand gaps "
        "remain unaddressed.<br/><br/>"
        "This project presents an Applied Data Science (ADS) and Machine Learning system that quantifies trade-area menu redundancy "
        "and identifies unmet market whitespace. By integrating multi-source datasets—including web-scraped Zomato restaurant listings, "
        "Indian culinary taxonomies, OpenStreetMap (OSM) competitor density points, 2011 Census demographic tables, and online delivery "
        "survey data—the system computes intra-locality pairwise TF-IDF cosine similarity matrices. It pairs this with a trained regression "
        "prediction engine incorporating competitive density, local population, menu overlap percentage, price point (INR), and token "
        "novelty. The platform is deployed as an end-to-end interactive workbench featuring GIS spatial coordinate mapping, trade-area "
        "saturation tables, and an interactive concept simulator. The automated data cleaning, canonical token mapping, and feature extraction "
        "pipeline is documented and executed in a dedicated Jupyter Notebook, establishing an empirical decision-making framework for culinary "
        "entrepreneurs and food analysts."
    )
    story.append(Paragraph(abstract_text, style_body))
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. Introduction", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=10))
    intro_text = (
        "In the contemporary digital economy, cloud kitchens operate without physical dine-in storefronts, relying entirely on "
        "online food delivery aggregators such as Zomato and Swiggy. While this operational model reduces real estate and front-of-house "
        "overheads, it introduces intense digital shelf competition.<br/><br/>"
        "In densely populated metropolitan corridors (e.g., Koramangala and Indiranagar in Bangalore; Connaught Place in Delhi), "
        "dozens of kitchens operate within overlapping 3-to-5 kilometer delivery radiuses. Due to lack of data-driven market validation, "
        "aspiring operators frequently replicate prevailing menu offerings, causing severe category cannibalization while regional dietary "
        "gaps and underserved price points remain neglected.<br/><br/>"
        "This project bridges the gap between raw culinary data and commercial viability forecasting through NLP menu tokenization, "
        "geospatial competitor clustering, demographic normalization, and predictive machine learning."
    )
    story.append(Paragraph(intro_text, style_body))
    story.append(Spacer(1, 10))

    story.append(Paragraph("3. Problem Statement", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=10))
    prob_points = [
        "<b>Unquantified Menu Overlap:</b> No standardized tool to evaluate semantic menu similarity between competing delivery kitchens.",
        "<b>Geographic Oversaturation:</b> Aggregator apps show ratings and prices but obscure competitor density relative to population.",
        "<b>Price Disconnect:</b> Item prices are set arbitrarily without analyzing median competitor price distributions.",
        "<b>Intuition-Driven Decision Making:</b> Concepts are launched based on anecdotal trends rather than empirical demand-scarcity analysis."
    ]
    for p in prob_points:
        story.append(Paragraph(f"&bull; {p}", style_bullet))
    story.append(Spacer(1, 10))

    story.append(Paragraph("4. Existing System", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=10))
    exist_text = (
        "Current practice relies on manual consumer app browsing, subjective field visits, and broad city-level reports that lack granular locality resolution."
    )
    story.append(Paragraph(exist_text, style_body))
    story.append(Paragraph("Limitations of the Existing System:", style_h2))
    exist_limits = [
        "<b>No Semantic Menu Comparison:</b> Cannot detect duplicate items under differing titles.",
        "<b>Static and Subjective:</b> Lacks mathematical similarity thresholds.",
        "<b>No Multi-Source Fusion:</b> Ignores physical OSM density and Census demographics.",
        "<b>Absence of Simulation:</b> No pre-launch viability forecasting before leasing and purchasing."
    ]
    for l in exist_limits:
        story.append(Paragraph(f"&bull; {l}", style_bullet))
    story.append(Spacer(1, 10))

    story.append(Paragraph("5. Proposed System", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=10))
    prop_features = [
        "<b>Canonical Token Normalization &amp; Fuzzy Matching:</b> Levenshtein distance correction against Indian Food 101 taxonomy.",
        "<b>Intra-Locality Pairwise TF-IDF Cosine Similarity:</b> N-gram (1–2) overlap calculation across restaurant menus.",
        "<b>Geospatial &amp; Demographic Fusion:</b> Merges OSM competitor counts and Census populations onto a GIS coordinate space.",
        "<b>ML Concept Simulator:</b> Multi-feature regression model outputting viability prediction with confidence intervals.",
        "<b>Interactive Workbench:</b> Real-time trade-area saturation metrics, dynamic range filtering (50%–95%), and dish scarcity indices.",
        "<b>Reproducible Notebook Pipeline:</b> End-to-end cleaning, joining, and model assembly in an executable notebook."
    ]
    for pf in prop_features:
        story.append(Paragraph(f"&bull; {pf}", style_bullet))
    story.append(Spacer(1, 10))

    story.append(Paragraph("6. About Dataset", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=10))
    dataset_table_data = [
        [Paragraph("Dataset Name", style_table_header),
         Paragraph("Source &amp; Format", style_table_header),
         Paragraph("Records &amp; Features", style_table_header),
         Paragraph("Primary Role in System", style_table_header)],

        [Paragraph("<b>Zomato Menus</b><br/><code>cleaned_zomato_menus.csv</code>", style_table_cell),
         Paragraph("Scraped catalog (CSV)", style_table_cell),
         Paragraph("4,000+ dish records across Bangalore &amp; Delhi", style_table_cell),
         Paragraph("Baseline dish catalog, restaurant names, price bands, ratings, and locations.", style_table_cell)],

        [Paragraph("<b>Indian Food 101</b><br/><code>indian_food_101.csv</code>", style_table_cell),
         Paragraph("Culinary DB (CSV)", style_table_cell),
         Paragraph("255 curated dishes with ingredients &amp; diet", style_table_cell),
         Paragraph("Ground truth dictionary for fuzzy spelling correction &amp; canonical mapping.", style_table_cell)],

        [Paragraph("<b>OSM Density</b><br/><code>osm_restaurant_density.csv</code>", style_table_cell),
         Paragraph("OpenStreetMap (CSV)", style_table_cell),
         Paragraph("Locality-level POI spatial density counts", style_table_cell),
         Paragraph("Physical commercial competitor density per square kilometer.", style_table_cell)],

        [Paragraph("<b>Census 2011</b><br/><code>census_districts_2011.csv</code>", style_table_cell),
         Paragraph("Census of India (CSV)", style_table_cell),
         Paragraph("District demographics &amp; household counts", style_table_cell),
         Paragraph("Trade-area population scale &amp; per-capita kitchen penetration index.", style_table_cell)],

        [Paragraph("<b>Delivery Survey</b><br/><code>online_food_delivery_survey.csv</code>", style_table_cell),
         Paragraph("Survey (CSV)", style_table_cell),
         Paragraph("Consumer dining preferences &amp; price tiers", style_table_cell),
         Paragraph("Weights consumer demand signals against locality supply gaps.", style_table_cell)]
    ]
    ds_table = Table(dataset_table_data, colWidths=[110, 85, 125, 160])
    ds_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(ds_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("7. Technologies Used", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=10))
    tech_data = [
        [Paragraph("Category", style_table_header),
         Paragraph("Technologies / Libraries", style_table_header),
         Paragraph("Purpose in System Architecture", style_table_header)],
        [Paragraph("<b>Language</b>", style_table_cell), Paragraph("Python 3.x", style_table_cell), Paragraph("Core runtime environment for analytical models, API, and notebooks.", style_table_cell)],
        [Paragraph("<b>ML &amp; NLP</b>", style_table_cell), Paragraph("Scikit-learn, NumPy, Pandas, FuzzyWuzzy", style_table_cell), Paragraph("TF-IDF vectorization, pairwise Cosine Similarity, Ridge regression, StandardScaler.", style_table_cell)],
        [Paragraph("<b>Notebook</b>", style_table_cell), Paragraph("Jupyter (<code>nbclient</code>, <code>nbformat</code>)", style_table_cell), Paragraph("Reproducible execution and interactive documentation of data transformation.", style_table_cell)],
        [Paragraph("<b>Backend</b>", style_table_cell), Paragraph("Flask, SQLite3, Werkzeug", style_table_cell), Paragraph("REST API routing, session authentication, and database storage.", style_table_cell)],
        [Paragraph("<b>Frontend</b>", style_table_cell), Paragraph("HTML5, CSS3, JavaScript (ES6+)", style_table_cell), Paragraph("Clean Applied Data Science interface: GIS coordinate grid and telemetry.", style_table_cell)]
    ]
    t_table = Table(tech_data, colWidths=[120, 150, 210])
    t_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("8. Data Flow Diagram", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=10))
    dfd_data = [
        [Paragraph("<b>Level 0: Raw Data Sources</b>", style_table_header)],
        [Paragraph("Zomato Menu Listings &bull; Indian Food 101 &bull; OSM Competitor Density &bull; Census 2011 &bull; Delivery Survey", style_table_cell)],
        [Paragraph("&darr; <i>(Data Cleaning, Regex Normalization, Price Imputation &amp; Locality Standardization)</i>", style_table_cell_bold)],
        [Paragraph("<b>Level 1: Feature Extraction &amp; NLP Processing</b>", style_table_header)],
        [Paragraph("Restaurant Aggregation &rarr; Unigram/Bigram TF-IDF &rarr; Pairwise Cosine Similarity &rarr; Geospatial Fusion", style_table_cell)],
        [Paragraph("&darr; <i>(Feature Assembly &amp; Train/Test Split)</i>", style_table_cell_bold)],
        [Paragraph("<b>Level 2: Model Training &amp; Storage</b>", style_table_header)],
        [Paragraph("Multi-Feature Regression Engine &bull; StandardScaler &bull; SQLite Database (<code>menus.sqlite3</code>)", style_table_cell)],
        [Paragraph("&darr; <i>(REST API Request Handling)</i>", style_table_cell_bold)],
        [Paragraph("<b>Level 3: Application &amp; Analytics Workbench</b>", style_table_header)],
        [Paragraph("GIS Coordinate Map (dynamic filter) &bull; Saturation Tables &bull; Pre-Launch Concept Simulator", style_table_cell)]
    ]
    dfd_table = Table(dfd_data, colWidths=[480])
    dfd_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), primary_color),
        ('BACKGROUND', (0,3), (0,3), primary_color),
        ('BACKGROUND', (0,6), (0,6), primary_color),
        ('BACKGROUND', (0,9), (0,9), primary_color),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('ALIGN', (0,2), (0,2), 'CENTER'),
        ('ALIGN', (0,5), (0,5), 'CENTER'),
        ('ALIGN', (0,8), (0,8), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,1), (0,1), colors.HexColor("#f8fafc")),
        ('BACKGROUND', (0,4), (0,4), colors.HexColor("#f8fafc")),
        ('BACKGROUND', (0,7), (0,7), colors.HexColor("#f8fafc")),
        ('BACKGROUND', (0,10), (0,10), colors.HexColor("#f8fafc")),
    ]))
    story.append(dfd_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("9. Output", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=10))
    outputs = [
        "<b>Jupyter Notebook Outputs:</b> Complete execution of 8 cells in <code>data_cleaning_and_transformation.ipynb</code>; calculated pairwise similarity scores from 0.12 to 0.89; generated <code>model_features.csv</code> (11 regression features).",
        "<b>Dashboard Map Interface (<code>/</code>):</b> Dark GIS coordinate space plotting cloud kitchens in Bangalore and Delhi with spatial micro-offsets; interactive range slider filtering redundancy links between 50% and 95%.",
        "<b>Trade-Area Saturation Table (<code>/analysis</code>):</b> Comprehensive metrics detailing competitor count, OSM density/km², average menu similarity, and whitespace opportunity scores across Koramangala, Indiranagar, Connaught Place, etc.",
        "<b>Concept Simulator (<code>/simulator</code>):</b> Accepts target city, locality, menu items, and price point; performs fuzzy token correction; outputs Estimated Performance Score (0–100).",
        "<b>Automated Test Suite:</b> 10/10 automated tests passing with zero regressions."
    ]
    for out in outputs:
        story.append(Paragraph(f"&bull; {out}", style_bullet))
    story.append(Spacer(1, 10))

    story.append(Paragraph("10. Conclusion", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=10))
    conclusion_text = (
        "The <b>Bitewise local menu comparison system</b> replaces intuition-based "
        "restaurant planning with an empirical, data-driven methodology. By combining NLP-based TF-IDF pairwise similarity "
        "with OpenStreetMap spatial density and Census demographic indicators, the system accurately detects hyper-saturated "
        "culinary segments and highlights lucrative, unmet market whitespace.<br/><br/>"
        "The interactive web workbench alongside an automated Jupyter Notebook transformation pipeline provides a robust "
        "technical tool for culinary operators and market analysts. Future enhancements include real-time aggregator review "
        "sentiment streams and dynamic supply-chain ingredient cost tracking."
    )
    story.append(Paragraph(conclusion_text, style_body))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"PDF successfully generated at: {output_path}")


if __name__ == "__main__":
    out_file = ROOT_DIR / "project_report.pdf"
    build_pdf(out_file)
