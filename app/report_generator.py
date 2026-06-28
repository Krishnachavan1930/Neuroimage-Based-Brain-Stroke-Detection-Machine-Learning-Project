import os
import logging
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from PIL import Image as PILImage

def generate_pdf(patient_data, output_pdf_path):
    """
    Generates a professional PDF medical report using reportlab.
    """
    # Setup document
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Define custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0F4C81'),  # Clinical Blue
        spaceAfter=6,
        alignment=0
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        textColor=colors.HexColor('#2E7D32'),  # Medical Green
        spaceAfter=15,
        alignment=0
    )
    
    h2_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#0F4C81'),
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#333333')
    )
    
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#555555')
    )
    
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#777777'),
        alignment=1
    )
    
    # Hospital Logo & Hospital Info Header
    logo_path = patient_data.get('hospital_logo_path', None)
    hospital_name = patient_data.get('hospital_name', 'Brain Stroke AI Diagnostic Center')
    hospital_address = patient_data.get('hospital_address', 'Medical Science Park, Neurological Wing, Block-C')
    
    # Custom styling for hospital info
    h_name_style = ParagraphStyle(
        'HospitalName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        textColor=colors.HexColor('#0F4C81')
    )
    
    h_addr_style = ParagraphStyle(
        'HospitalAddress',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#666666')
    )
    
    doc_type_style = ParagraphStyle(
        'DocType',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        textColor=colors.HexColor('#2E7D32'),
        alignment=2 # Right align
    )
    
    header_left = []
    if logo_path and os.path.isfile(logo_path):
        try:
            # Scale logo
            logo_img = Image(logo_path, width=40, height=40)
            
            # Put logo and names side by side
            logo_table = Table(
                [[logo_img, [Paragraph(hospital_name, h_name_style), Paragraph(hospital_address, h_addr_style)]]],
                colWidths=[50, 250]
            )
            logo_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
            ]))
            header_left.append(logo_table)
        except Exception as ex:
            logging.error(f"Error drawing logo in PDF header: {ex}")
            header_left.append(Paragraph(hospital_name, h_name_style))
            header_left.append(Paragraph(hospital_address, h_addr_style))
    else:
        header_left.append(Paragraph(hospital_name, h_name_style))
        header_left.append(Paragraph(hospital_address, h_addr_style))
        
    header_right = [
        Paragraph("DIAGNOSTIC REPORT", doc_type_style),
        Spacer(1, 4),
        Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d')}", ParagraphStyle('HeaderDate', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=9, leading=11, textColor=colors.HexColor('#777777'), alignment=2))
    ]
    
    header_table = Table([[header_left, header_right]], colWidths=[350, 182])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    
    # Divider Line
    divider = Table([[""]], colWidths=[532])
    divider.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 2, colors.HexColor('#0F4C81')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(divider)
    story.append(Spacer(1, 15))
    
    # Patient details section
    story.append(Paragraph("Patient Details", h2_style))
    
    # Format dates and defaults
    dob = patient_data.get('dob', 'N/A')
    reg_date = patient_data.get('datetime', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    # Grid of patient details
    details_data = [
        [
            Paragraph("Patient Name:", label_style), Paragraph(patient_data.get('name', 'N/A'), value_style),
            Paragraph("Hospital ID:", label_style), Paragraph(patient_data.get('hospital_id', 'N/A'), value_style)
        ],
        [
            Paragraph("Age:", label_style), Paragraph(str(patient_data.get('age', 'N/A')), value_style),
            Paragraph("Gender:", label_style), Paragraph(patient_data.get('gender', 'N/A'), value_style)
        ],
        [
            Paragraph("Date of Birth:", label_style), Paragraph(dob, value_style),
            Paragraph("Mobile Number:", label_style), Paragraph(patient_data.get('mobile', 'N/A'), value_style)
        ],
        [
            Paragraph("Referring Doctor:", label_style), Paragraph(patient_data.get('doctor', 'N/A') or 'N/A', value_style),
            Paragraph("Report Date/Time:", label_style), Paragraph(reg_date, value_style)
        ],
        [
            Paragraph("Symptoms:", label_style), Paragraph(patient_data.get('symptoms', 'N/A') or 'N/A', value_style),
            Paragraph("Additional Notes:", label_style), Paragraph(patient_data.get('notes', 'N/A') or 'N/A', value_style)
        ]
    ]
    
    # Create details table
    details_table = Table(details_data, colWidths=[110, 156, 110, 156])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('SPAN', (1, 4), (3, 4)),  # Span symptoms across the row if needed, actually symptoms is col 1 span to 3, let's keep it simple
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FA')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E0E0E0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F0F0F0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    
    # Adjust symptoms span manually to avoid overlapping
    # Let's rebuild details data to support long text symptoms/notes
    # Row 4: Symptoms label, Symptoms value span to end
    # Row 5: Notes label, Notes value span to end
    details_data = [
        [
            Paragraph("Patient Name:", label_style), Paragraph(patient_data.get('name', 'N/A'), value_style),
            Paragraph("Hospital ID:", label_style), Paragraph(patient_data.get('hospital_id', 'N/A'), value_style)
        ],
        [
            Paragraph("Age:", label_style), Paragraph(str(patient_data.get('age', 'N/A')), value_style),
            Paragraph("Gender:", label_style), Paragraph(patient_data.get('gender', 'N/A'), value_style)
        ],
        [
            Paragraph("Date of Birth:", label_style), Paragraph(dob, value_style),
            Paragraph("Mobile Number:", label_style), Paragraph(patient_data.get('mobile', 'N/A'), value_style)
        ],
        [
            Paragraph("Referring Doctor:", label_style), Paragraph(patient_data.get('doctor', 'N/A') or 'N/A', value_style),
            Paragraph("Report Date/Time:", label_style), Paragraph(reg_date, value_style)
        ],
        [
            Paragraph("Symptoms:", label_style), Paragraph(patient_data.get('symptoms', 'None') or 'None', value_style),
            Paragraph("", label_style), Paragraph("", value_style)
        ],
        [
            Paragraph("Additional Notes:", label_style), Paragraph(patient_data.get('notes', 'None') or 'None', value_style),
            Paragraph("", label_style), Paragraph("", value_style)
        ]
    ]
    
    details_table = Table(details_data, colWidths=[100, 166, 100, 166])
    details_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('SPAN', (1, 4), (3, 4)),  # Span symptoms
        ('SPAN', (1, 5), (3, 5)),  # Span notes
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FA')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E0E0E0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#F0F0F0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    
    story.append(details_table)
    story.append(Spacer(1, 15))
    
    # Diagnostic Results & MRI Scan layout
    story.append(Paragraph("Diagnostic Results & Scan", h2_style))
    
    # Prediction values
    prediction_result = patient_data.get('prediction', 'N/A')
    confidence = patient_data.get('confidence', None)
    
    # Result Box styling
    is_stroke = "Stroke" in prediction_result
    result_bg = colors.HexColor('#FFEBEE') if is_stroke else colors.HexColor('#E8F5E9')
    result_border = colors.HexColor('#EF5350') if is_stroke else colors.HexColor('#66BB6A')
    result_text_color = colors.HexColor('#C62828') if is_stroke else colors.HexColor('#2E7D32')
    result_status = "Stroke Detected" if is_stroke else "Normal (No Stroke Detected)"
    
    result_header_style = ParagraphStyle(
        'ResultHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        textColor=result_text_color
    )
    
    result_val_style = ParagraphStyle(
        'ResultVal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=18,
        textColor=result_text_color
    )
    
    result_details_data = [
        [Paragraph("AI CLASSIFICATION STATUS", result_header_style)],
        [Paragraph(result_status.upper(), result_val_style)]
    ]
    if confidence is not None:
        confidence_style = ParagraphStyle(
            'ConfidenceStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=13,
            textColor=colors.HexColor('#333333')
        )
        result_details_data.append([Paragraph(f"Analysis Confidence: {confidence:.1f}%", confidence_style)])
    
    result_details_table = Table(result_details_data, colWidths=[240])
    result_details_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), result_bg),
        ('BOX', (0,0), (-1,-1), 1.5, result_border),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    
    # Model Metadata Details
    meta_data = [
        [Paragraph("Analytical Model:", label_style), Paragraph(patient_data.get('model_name', 'CNN'), value_style)],
        [Paragraph("Target Resolution:", label_style), Paragraph("224 × 224 pixels", value_style)],
        [Paragraph("Framework:", label_style), Paragraph("TensorFlow / Keras", value_style)],
        [Paragraph("Deployment Stage:", label_style), Paragraph("Clinical Evaluation (v1.0)", value_style)]
    ]
    meta_table = Table(meta_data, colWidths=[110, 130])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    
    right_panel = [
        result_details_table,
        Spacer(1, 10),
        meta_table
    ]
    
    # Left panel: Uploaded MRI Image
    img_path = patient_data.get('img_disk_path', None)
    left_panel = []
    
    mri_image_rendered = False
    if img_path and os.path.isfile(img_path):
        # Calculate aspect ratio
        try:
            with PILImage.open(img_path) as pil_img:
                w, h = pil_img.size
                aspect = h / w
                img_width = 180
                img_height = img_width * aspect
            
            mri_image = Image(img_path, width=img_width, height=img_height)
            
            # Table wrapping image with card style border
            img_table = Table([[mri_image]], colWidths=[img_width + 10])
            img_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CCCCCC')),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING', (0,0), (-1,-1), 5),
                ('RIGHTPADDING', (0,0), (-1,-1), 5),
            ]))
            left_panel.append(Paragraph("<b>Uploaded MRI Scan</b>", label_style))
            left_panel.append(Spacer(1, 6))
            left_panel.append(img_table)
            mri_image_rendered = True
        except Exception as img_err:
            logging.error(f"Failed to read or render MRI image in PDF: {img_err}")
            
    if not mri_image_rendered:
        left_panel.append(Paragraph("<i>No MRI Scan Image Available</i>", value_style))
        
    # Combine panels using a parent layout table
    layout_data = [[left_panel, right_panel]]
    layout_table = Table(layout_data, colWidths=[250, 282])
    layout_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    
    story.append(layout_table)
    story.append(Spacer(1, 20))
    
    # Disclaimer Line
    disclaimer_text = (
        "<b>Medical Disclaimer:</b> This report is generated using an AI-based Brain Stroke Detection model. "
        "The prediction is intended to assist healthcare professionals and should not be considered a final medical diagnosis. "
        "Clinical evaluation by a qualified neurologist or radiologist is strongly recommended."
    )
    
    disclaimer_box = Table([[Paragraph(disclaimer_text, disclaimer_style)]], colWidths=[532])
    disclaimer_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFDE7')),  # Soft Yellow
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#FFF9C4')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(disclaimer_box)
    story.append(Spacer(1, 30))
    
    # Footer Section
    footer_text = f"Generated by Brain Stroke Detection System v1.0 | Date: {datetime.now().strftime('%Y-%m-%d')}"
    footer_para = Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#999999'), alignment=1))
    story.append(footer_para)
    
    # Build Document
    doc.build(story)
