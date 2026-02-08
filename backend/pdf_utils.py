from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from datetime import datetime

class PDFGenerator:
    @staticmethod
    def generate_variation_proposal(proposal_data, output_path):
        """
        Generates a professional Variation Proposal PDF.
        proposal_data: dict containing item details, rates, and impacts.
        """
        doc = SimpleDocTemplate(output_path, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=1, # Center
            spaceAfter=20
        )
        elements.append(Paragraph("VARIATION PROPOSAL", title_style))
        elements.append(Spacer(1, 12))

        # Date and Project Info
        curr_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elements.append(Paragraph(f"<b>Date:</b> {curr_date}", styles['Normal']))
        elements.append(Paragraph(f"<b>Item ID:</b> {proposal_data.get('item_id', 'N/A')}", styles['Normal']))
        elements.append(Spacer(1, 12))

        # Description
        elements.append(Paragraph("<b>Variation Description:</b>", styles['Heading3']))
        desc_text = f"Change from <i>{proposal_data.get('original_item', 'Original')}</i> to <i>{proposal_data.get('new_item', 'New Material')}</i>."
        elements.append(Paragraph(desc_text, styles['Normal']))
        elements.append(Spacer(1, 20))

        # Table of Impacts
        elements.append(Paragraph("<b>Cost Impact Summary:</b>", styles['Heading3']))
        data = [
            ["Description", "Original Rate", "New Rate", "Total Impact"],
            [
                proposal_data.get('new_item', 'New Item'),
                f"${proposal_data.get('original_rate', 0)}",
                f"${proposal_data.get('new_rate', 0)}",
                f"${proposal_data.get('cost_impact', 0)}"
            ]
        ]
        
        t = Table(data, colWidths=[200, 100, 100, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)
        
        if proposal_data.get('time_impact'):
            elements.append(Spacer(1, 20))
            elements.append(Paragraph("<b>Time Impact Summary:</b>", styles['Heading3']))
            elements.append(Paragraph(f"The variation results in an estimated Extension of Time (EOT) of <b>{proposal_data['time_impact']} days</b>.", styles['Normal']))

        # Signature
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("_" * 30, styles['Normal']))
        elements.append(Paragraph("Authorized Signature", styles['Normal']))

        doc.build(elements)
        return output_path
