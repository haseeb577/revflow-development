"""
RevSPY™ PDF Report Exporter
Generates professional PDF reports from competitive analysis
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus import Image as RLImage
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from datetime import datetime
from typing import Dict
import os

class PDFReportGenerator:
    """Generate professional PDF reports"""
    
    def __init__(self, output_dir: str = "/tmp"):
        self.output_dir = output_dir
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c5aa0'),
            spaceBefore=20,
            spaceAfter=12
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666')
        ))
        
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#1a1a1a'),
            fontName='Helvetica-Bold'
        ))
    
    def generate_prospect_report(self, report: Dict, filename: str = None) -> str:
        """
        Generate PDF report for prospect
        Returns: Path to generated PDF file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"prospect_report_{timestamp}.pdf"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Create document
        doc = SimpleDocTemplate(filepath, pagesize=letter,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Build content
        story = []
        
        # Title
        title = Paragraph("Competitive Analysis Report", self.styles['CustomTitle'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Business Info
        prospect = report['prospect']
        business_name = prospect.get('business_name', 'Unknown Business')
        
        story.append(Paragraph(f"<b>{business_name}</b>", self.styles['Heading2']))
        story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%B %d, %Y')}", 
                              self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Current Position Section
        story.append(Paragraph("Current Position", self.styles['SectionHeader']))
        
        position_data = [
            ['Metric', 'Value'],
            ['Market Rank', f"#{prospect.get('competitor_rank')} of {report['market'].get('total_competitors')}"],
            ['Rating', f"{prospect.get('rating')} ⭐"],
            ['Total Reviews', str(prospect.get('review_count'))],
            ['Health Score', f"{prospect.get('gbp_health_score', 0)}/100"],
            ['Threat Level', prospect.get('competitive_threat', 'Unknown')]
        ]
        
        position_table = Table(position_data, colWidths=[3*inch, 3*inch])
        position_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
        ]))
        
        story.append(position_table)
        story.append(Spacer(1, 20))
        
        # Market Comparison
        story.append(Paragraph("Market Comparison", self.styles['SectionHeader']))
        
        market = report['market']
        gaps = report['gaps']
        
        comparison_data = [
            ['', 'Your Business', 'Market Average', 'Gap'],
            ['Rating', f"{prospect.get('rating')}", f"{market.get('avg_rating')}", 
             f"{gaps.get('rating', 0):.1f}"],
            ['Reviews', str(prospect.get('review_count')), str(market.get('avg_reviews')), 
             str(int(gaps.get('reviews', 0)))],
            ['Photos', str(prospect.get('photo_count')), str(market.get('avg_photos')), 
             str(int(gaps.get('photos', 0)))]
        ]
        
        comparison_table = Table(comparison_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        comparison_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
        ]))
        
        story.append(comparison_table)
        story.append(Spacer(1, 20))
        
        # Top Competitors
        if report.get('top_competitors'):
            story.append(Paragraph("Top Competitors", self.styles['SectionHeader']))
            
            comp_data = [['Rank', 'Business', 'Rating', 'Reviews', 'Health Score']]
            for comp in report['top_competitors'][:3]:
                comp_data.append([
                    f"#{comp.get('competitor_rank')}",
                    comp.get('business_name', 'Unknown'),
                    str(comp.get('rating', 0)),
                    str(comp.get('review_count', 0)),
                    f"{comp.get('gbp_health_score', 0)}/100"
                ])
            
            comp_table = Table(comp_data, colWidths=[0.75*inch, 2.5*inch, 1*inch, 1*inch, 1.25*inch])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5aa0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')])
            ]))
            
            story.append(comp_table)
            story.append(Spacer(1, 20))
        
        # Recommendation
        recommendation = report.get('recommendation', {})
        story.append(Paragraph("Recommendation", self.styles['SectionHeader']))
        
        rec_data = [
            ['Priority', recommendation.get('priority', 'N/A')],
            ['Strategy', recommendation.get('message', 'N/A')],
            ['Investment', recommendation.get('investment', 'N/A')]
        ]
        
        rec_table = Table(rec_data, colWidths=[2*inch, 4*inch])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#2c5aa0')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('PADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (-1, -1), colors.HexColor('#fff8dc')),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        story.append(rec_table)
        story.append(Spacer(1, 30))
        
        # Footer
        footer_text = f"""
        <i>This report was generated by RevSPY™ GBP Intelligence on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}. 
        Data is based on current Google Business Profile information and competitive analysis algorithms.</i>
        """
        story.append(Paragraph(footer_text, self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        return filepath


# Convenience function
def export_to_pdf(report: Dict, output_dir: str = "/tmp", filename: str = None) -> str:
    """Export report to PDF"""
    generator = PDFReportGenerator(output_dir)
    return generator.generate_prospect_report(report, filename)
