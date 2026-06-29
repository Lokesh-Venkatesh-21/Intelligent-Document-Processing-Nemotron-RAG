from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def create_dummy_pdf(filename="dummy_document.pdf"):
    # Target 0.75 inch margins
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=12
    )
    
    section_style = ParagraphStyle(
        'DocSection',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor('#334155'),
        spaceAfter=10
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=colors.white
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor('#0f172a')
    )

    story = []
    
    # 1. Document Title
    story.append(Paragraph("Global Tech Corp — Q2 2026 Business Report", title_style))
    story.append(Spacer(1, 10))
    
    # 2. Section 1 & Narrative Text
    story.append(Paragraph("Executive Summary", section_style))
    narrative_1 = (
        "Global Tech Corp reported strong financial performance for the second quarter of 2026. "
        "Overall revenue reached $150 million, representing a 15.4% increase compared to Q2 of the previous fiscal year. "
        "This growth was primarily driven by accelerated enterprise adoption of our cloud platforms. "
        "Operating income rose to $35 million, reflecting enhanced margins in software divisions."
    )
    story.append(Paragraph(narrative_1, body_style))
    story.append(Spacer(1, 8))
    
    # 3. Section 2 & Data Table
    story.append(Paragraph("Financial Performance by Segment", section_style))
    
    # Define Table Data (wrapped in Paragraphs to support text wrapping if needed)
    raw_data = [
        ["Segment Division", "Revenue Q2 2025", "Revenue Q2 2026", "YoY Growth (%)"],
        ["Cloud Services", "$45M", "$60M", "+33.3%"],
        ["Hardware Products", "$55M", "$50M", "-9.1%"],
        ["Consulting & Support", "$30M", "$40M", "+33.3%"],
        ["Consolidated Total", "$130M", "$150M", "+15.4%"]
    ]
    
    formatted_data = []
    # Header Row
    formatted_data.append([Paragraph(cell, table_header_style) for cell in raw_data[0]])
    # Body Rows
    for row in raw_data[1:]:
        formatted_data.append([Paragraph(cell, table_cell_style) for cell in row])
        
    # Table Styling
    t = Table(formatted_data, colWidths=[150, 110, 110, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.white),
        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#e2e8f0')), # Totals row
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
    ]))
    story.append(t)
    story.append(Spacer(1, 12))
    
    # 4. Section 3 & Forecast Text
    story.append(Paragraph("Strategic Outlook", section_style))
    narrative_2 = (
        "Cloud Services continues to expand as our highest margin division, now accounting for 40.0% of overall corporate revenue. "
        "Hardware segments faced temporary supply chain adjustments leading to a slight contraction, but backlog orders remain high. "
        "Based on these results, we are initiating expansion into South American markets in Q3 2026, targeting initial operations "
        "in Lima and Bogota."
    )
    story.append(Paragraph(narrative_2, body_style))
    
    # Build PDF
    doc.build(story)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    create_dummy_pdf()
