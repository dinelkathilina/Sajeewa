from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from datetime import datetime
import os

class PDFGenerator:
    """Enhanced PDF Generator for professional variation proposals"""
    
    @staticmethod
    def _create_header(elements, styles, project_name="Construction Project"):
        """Create professional header"""
        header_style = ParagraphStyle(
            'HeaderStyle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a365d'),
            alignment=TA_CENTER,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        )
        
        subheader_style = ParagraphStyle(
            'SubHeaderStyle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#2d3748'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        elements.append(Paragraph("VARIATION PROPOSAL", header_style))
        elements.append(Paragraph(f"Project: {project_name}", subheader_style))
        elements.append(Spacer(1, 0.2*inch))
    
    @staticmethod
    def _create_info_section(elements, styles, proposal_data):
        """Create proposal information section"""
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=14
        )
        
        curr_date = datetime.now().strftime("%d %B %Y")
        variation_id = proposal_data.get('variation_id', 'DRAFT')
        variation_type = proposal_data.get('variation_type', 'Type 1: Quantity Changes')
        
        info_data = [
            ["Proposal Reference:", f"VAR-{variation_id}"],
            ["Date of Submission:", curr_date],
            ["Variation Type:", variation_type],
            ["Status:", proposal_data.get('status', 'Under Review')]
        ]
        
        info_table = Table(info_data, colWidths=[2.5*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2d3748')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
    
    @staticmethod
    def _create_section_header(elements, styles, title):
        """Create section header"""
        section_style = ParagraphStyle(
            'SectionStyle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a365d'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderColor=colors.HexColor('#cbd5e0'),
            borderPadding=8,
            backColor=colors.HexColor('#edf2f7')
        )
        
        elements.append(Paragraph(title, section_style))
    
    @staticmethod
    def _create_description_section(elements, styles, proposal_data):
        """Create variation description section"""
        PDFGenerator._create_section_header(elements, styles, "1. VARIATION DESCRIPTION")
        
        description = proposal_data.get('description', 'No description provided')
        
        desc_style = ParagraphStyle(
            'DescStyle',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            alignment=TA_JUSTIFY
        )
        
        elements.append(Paragraph(description, desc_style))
        elements.append(Spacer(1, 0.2*inch))
    
    @staticmethod
    def _create_cost_breakdown_section(elements, styles, proposal_data):
        """Create detailed cost breakdown section"""
        PDFGenerator._create_section_header(elements, styles, "2. COST IMPACT ANALYSIS")
        
        # Get variation details
        details = proposal_data.get('details', [])
        
        if not details:
            # Fallback to simple format
            details = [{
                'description': proposal_data.get('new_item', 'Variation Item'),
                'original_rate': proposal_data.get('original_rate', 0),
                'new_rate': proposal_data.get('new_rate', 0),
                'quantity': proposal_data.get('quantity', 0),
                'cost_impact': proposal_data.get('cost_impact', 0),
                'rate_source': proposal_data.get('rate_source', 'Original BOQ')
            }]
        
        # Create table data
        table_data = [
            ["Item Description", "Qty", "Original Rate", "New Rate", "Impact", "Source"]
        ]
        
        total_impact = 0
        for detail in details:
            table_data.append([
                Paragraph(detail.get('description', 'N/A')[:60], styles['Normal']),
                f"{detail.get('quantity', 0):.2f}",
                f"${detail.get('original_rate', 0):.2f}",
                f"${detail.get('new_rate', 0):.2f}",
                f"${detail.get('cost_impact', 0):.2f}",
                detail.get('rate_source', 'N/A')[:15]
            ])
            total_impact += detail.get('cost_impact', 0)
        
        # Add total row
        table_data.append([
            Paragraph("<b>TOTAL COST IMPACT</b>", styles['Normal']),
            "", "", "",
            Paragraph(f"<b>${total_impact:.2f}</b>", styles['Normal']),
            ""
        ])
        
        cost_table = Table(table_data, colWidths=[2.5*inch, 0.6*inch, 1*inch, 1*inch, 1*inch, 0.9*inch])
        cost_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f7fafc')]),
            
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#edf2f7')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#2c5282')),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#2c5282')),
        ]))
        
        elements.append(cost_table)
        elements.append(Spacer(1, 0.3*inch))
    
    @staticmethod
    def _create_time_impact_section(elements, styles, proposal_data):
        """Create time impact section with EOT breakdown"""
        eot_breakdown = proposal_data.get('eot_breakdown')
        
        if not eot_breakdown:
            return
        
        PDFGenerator._create_section_header(elements, styles, "3. TIME IMPACT ANALYSIS")
        
        eot_days = eot_breakdown.get('eot_days', 0)
        
        # Summary paragraph
        summary_text = f"""
        The proposed variation results in an Extension of Time (EOT) of <b>{eot_days:.1f} days</b>.
        This assessment is based on Critical Path Method (CPM) analysis of the project schedule.
        """
        
        elements.append(Paragraph(summary_text, styles['Normal']))
        elements.append(Spacer(1, 0.1*inch))
        
        # EOT details table
        affected_activity = eot_breakdown.get('affected_activity', {})
        
        eot_data = [
            ["Parameter", "Value"],
            ["Affected Activity", affected_activity.get('name', 'N/A')],
            ["Original Duration", f"{affected_activity.get('original_duration', 0):.1f} days"],
            ["Delay Added", f"{affected_activity.get('delay_added', 0):.1f} days"],
            ["New Duration", f"{affected_activity.get('new_duration', 0):.1f} days"],
            ["On Critical Path", "Yes" if eot_breakdown.get('is_on_critical_path') else "No"],
            ["Original Float", f"{eot_breakdown.get('original_float', 0):.1f} days"],
            ["Original Project Duration", f"{eot_breakdown.get('original_project_duration', 0):.1f} days"],
            ["New Project Duration", f"{eot_breakdown.get('new_project_duration', 0):.1f} days"],
            ["Extension of Time (EOT)", f"{eot_days:.1f} days"]
        ]
        
        eot_table = Table(eot_data, colWidths=[3*inch, 3.5*inch])
        eot_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#2c5282')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            # Highlight EOT row
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fef5e7')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#d68910')),
        ]))
        
        elements.append(eot_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Justification
        justification = eot_breakdown.get('justification', '')
        if justification:
            elements.append(Paragraph("<b>Justification:</b>", styles['Heading4']))
            elements.append(Paragraph(justification, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
    
    @staticmethod
    def _create_validation_section(elements, styles, proposal_data):
        """Create QS validation results section"""
        validation = proposal_data.get('validation_results')
        
        if not validation:
            return
        
        PDFGenerator._create_section_header(elements, styles, "4. QS VALIDATION RESULTS")
        
        status = validation.get('status', 'unknown')
        status_color = {
            'passed': colors.HexColor('#38a169'),
            'warnings': colors.HexColor('#d69e2e'),
            'failed': colors.HexColor('#e53e3e')
        }.get(status, colors.grey)
        
        status_text = f"<font color='{status_color.hexval()}'>●</font> <b>Status: {status.upper()}</b>"
        elements.append(Paragraph(status_text, styles['Normal']))
        elements.append(Spacer(1, 0.1*inch))
        
        # Warnings
        warnings = validation.get('warnings', [])
        if warnings:
            elements.append(Paragraph("<b>Warnings:</b>", styles['Heading4']))
            for warning in warnings:
                elements.append(Paragraph(f"⚠ {warning}", styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
        
        # Errors
        errors = validation.get('errors', [])
        if errors:
            elements.append(Paragraph("<b>Errors:</b>", styles['Heading4']))
            for error in errors:
                elements.append(Paragraph(f"✗ {error}", styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
    
    @staticmethod
    def _create_summary_section(elements, styles, proposal_data):
        """Create executive summary"""
        PDFGenerator._create_section_header(elements, styles, "5. EXECUTIVE SUMMARY")
        
        total_cost = proposal_data.get('cost_impact', 0)
        total_time = proposal_data.get('time_impact', 0)
        
        summary_data = [
            ["Total Cost Impact:", f"${total_cost:.2f}"],
            ["Total Time Impact:", f"{total_time:.1f} days"],
            ["Recommendation:", proposal_data.get('recommendation', 'Approve subject to validation')]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1a365d')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#edf2f7')),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#2c5282')),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
    
    @staticmethod
    def _create_footer(elements, styles):
        """Create signature section"""
        elements.append(Spacer(1, 0.5*inch))
        
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER
        )
        
        elements.append(Paragraph("_" * 40, footer_style))
        elements.append(Paragraph("Authorized Signature", footer_style))
        elements.append(Spacer(1, 0.1*inch))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y at %H:%M')}", footer_style))
    
    @staticmethod
    def generate_variation_proposal(proposal_data, output_path):
        """
        Generate comprehensive variation proposal PDF
        
        Args:
            proposal_data: Dictionary containing all proposal information
            output_path: Path where PDF will be saved
            
        Returns:
            Path to generated PDF
        """
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        elements = []
        
        # Build document sections
        project_name = proposal_data.get('project_name', 'Construction Project')
        
        PDFGenerator._create_header(elements, styles, project_name)
        PDFGenerator._create_info_section(elements, styles, proposal_data)
        PDFGenerator._create_description_section(elements, styles, proposal_data)
        PDFGenerator._create_cost_breakdown_section(elements, styles, proposal_data)
        PDFGenerator._create_time_impact_section(elements, styles, proposal_data)
        PDFGenerator._create_validation_section(elements, styles, proposal_data)
        PDFGenerator._create_summary_section(elements, styles, proposal_data)
        PDFGenerator._create_footer(elements, styles)
        
        # Build PDF
        doc.build(elements)
        
        return output_path
