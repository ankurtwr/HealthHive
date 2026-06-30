"""
WhatsApp Bot for HealthHive Report Explainer
=============================================
Uses Twilio WhatsApp API to receive medical report images,
analyze them with Gemini, generate a PDF, and send it back.

Setup:
1. Create a Twilio account (free trial works)
2. Enable Twilio Sandbox for WhatsApp
3. Set webhook URL to: https://your-domain.com/api/whatsapp/webhook
4. Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER to .env
"""

import io
import os
import json
import uuid
import requests as http_requests
from flask import Blueprint, request, current_app
from PIL import Image
from google import genai

whatsapp_bp = Blueprint('whatsapp', __name__, url_prefix='/api/whatsapp')


def get_twilio_client():
    """Lazy-load Twilio client to avoid import errors if not installed."""
    try:
        from twilio.rest import Client
        sid = os.getenv('TWILIO_ACCOUNT_SID')
        token = os.getenv('TWILIO_AUTH_TOKEN')
        if sid and token:
            return Client(sid, token)
    except ImportError:
        current_app.logger.warning("Twilio not installed. WhatsApp bot disabled.")
    return None


def send_whatsapp_message(to_number, body, media_url=None):
    """Send a WhatsApp message via Twilio."""
    client = get_twilio_client()
    if not client:
        return None

    from_number = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
    
    kwargs = {
        'from_': from_number,
        'to': to_number,
        'body': body
    }
    
    if media_url:
        kwargs['media_url'] = [media_url]

    try:
        message = client.messages.create(**kwargs)
        return message.sid
    except Exception as e:
        current_app.logger.error(f"WhatsApp send error: {e}")
        return None


def analyze_report_image(image_bytes):
    """Analyze a medical report image using Gemini Vision API."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None, "Gemini API key not configured."

    try:
        img = Image.open(io.BytesIO(image_bytes))
        client = genai.Client(api_key=api_key)

        analysis_prompt = """You are a medical report analysis assistant. Analyze this medical report image and return a JSON response with the following structure:

{
  "report_title": "Type of report (e.g., Complete Blood Count, Lipid Profile, etc.)",
  "patient_info": "Any patient info visible (name, age, date) or 'Not visible'",
  "parameters": [
    {
      "name": "Parameter name (e.g., Hemoglobin)",
      "value": "The measured value with unit",
      "reference_range": "Normal reference range",
      "status": "normal" or "borderline" or "critical",
      "explanation": "Simple 1-2 sentence explanation of what this parameter means and why the value matters"
    }
  ],
  "summary": "A 3-4 sentence plain-language summary of the overall report findings, highlighting any concerns",
  "abnormalities": ["List of parameter names that are borderline or critical"],
  "recommendations": "General health recommendations based on the findings (2-3 sentences)"
}

IMPORTANT RULES:
- Use ONLY the JSON format above, no markdown, no code fences, just raw JSON
- status must be exactly one of: "normal", "borderline", "critical"
- Provide simple, patient-friendly explanations (avoid medical jargon)
- If you cannot read a value clearly, mark it as "unclear" in the value field
- Always include the reference range if visible on the report"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[img, analysis_prompt]
        )

        raw_text = response.text.strip()
        
        # Clean markdown fences
        if raw_text.startswith('```'):
            raw_text = raw_text.split('\n', 1)[1] if '\n' in raw_text else raw_text[3:]
        if raw_text.endswith('```'):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        analysis = json.loads(raw_text)
        return analysis, None

    except json.JSONDecodeError:
        return None, "Could not parse the report. Please send a clearer image."
    except Exception as e:
        return None, f"Analysis error: {str(e)}"


def generate_report_pdf(analysis):
    """Generate a PDF from the analysis data. Returns bytes."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=20*mm, rightMargin=20*mm,
                                topMargin=20*mm, bottomMargin=20*mm)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle', parent=styles['Title'],
                                     fontSize=18, textColor=HexColor('#0d9488'),
                                     spaceAfter=12)
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'],
                                       fontSize=13, textColor=HexColor('#1e293b'),
                                       spaceAfter=8, spaceBefore=16)
        body_style = ParagraphStyle('CustomBody', parent=styles['Normal'],
                                    fontSize=10, textColor=HexColor('#334155'),
                                    spaceAfter=6, leading=14)
        disclaimer_style = ParagraphStyle('Disclaimer', parent=styles['Normal'],
                                          fontSize=8, textColor=HexColor('#94a3b8'),
                                          spaceAfter=4, leading=10)

        elements = []

        # Title
        elements.append(Paragraph("HealthHive — Medical Report Analysis", title_style))
        elements.append(Paragraph("via WhatsApp Bot", body_style))
        elements.append(Spacer(1, 4*mm))

        # Report info
        elements.append(Paragraph(
            f"<b>Report:</b> {analysis.get('report_title', 'Medical Report')}", body_style))
        elements.append(Paragraph(
            f"<b>Patient:</b> {analysis.get('patient_info', 'N/A')}", body_style))
        elements.append(Spacer(1, 6*mm))

        # Summary
        elements.append(Paragraph("Summary", heading_style))
        elements.append(Paragraph(analysis.get('summary', 'No summary available.'), body_style))

        # Parameters table
        params = analysis.get('parameters', [])
        if params:
            elements.append(Spacer(1, 4*mm))
            elements.append(Paragraph("Test Parameters", heading_style))

            table_data = [['Parameter', 'Value', 'Reference', 'Status']]
            row_colors = []
            for p in params:
                status = p.get('status', 'normal')
                table_data.append([
                    p.get('name', ''),
                    p.get('value', ''),
                    p.get('reference_range', ''),
                    status.upper()
                ])
                if status == 'critical':
                    row_colors.append(HexColor('#FEE2E2'))
                elif status == 'borderline':
                    row_colors.append(HexColor('#FEF3C7'))
                else:
                    row_colors.append(HexColor('#DCFCE7'))

            t = Table(table_data, colWidths=[55*mm, 35*mm, 40*mm, 30*mm])
            style_cmds = [
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#0d9488')),
                ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CBD5E1')),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ]
            for i, color in enumerate(row_colors):
                style_cmds.append(('BACKGROUND', (0, i+1), (-1, i+1), color))

            t.setStyle(TableStyle(style_cmds))
            elements.append(t)

        # Explanations
        elements.append(Spacer(1, 6*mm))
        elements.append(Paragraph("What Do These Values Mean?", heading_style))
        for p in params:
            status_marker = 'NORMAL' if p.get('status') == 'normal' else ('BORDERLINE' if p.get('status') == 'borderline' else 'CRITICAL')
            elements.append(Paragraph(
                f"<b>[{status_marker}] {p.get('name', '')}:</b> {p.get('explanation', '')}",
                body_style))

        # Recommendations
        if analysis.get('recommendations'):
            elements.append(Spacer(1, 4*mm))
            elements.append(Paragraph("Recommendations", heading_style))
            elements.append(Paragraph(analysis['recommendations'], body_style))

        # Disclaimer
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph(
            "DISCLAIMER: This analysis is generated by AI and is for informational purposes only. "
            "It is NOT a substitute for professional medical advice, diagnosis, or treatment. "
            "Always consult a qualified healthcare provider. © 2026 HealthHive",
            disclaimer_style))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    except Exception as e:
        current_app.logger.error(f"PDF generation error: {e}")
        return None


@whatsapp_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Twilio WhatsApp webhook endpoint.
    
    Receives incoming messages from WhatsApp users:
    - If the message contains an image → analyze it and reply with PDF
    - If it's a text message → reply with instructions
    """
    from twilio.twiml.messaging_response import MessagingResponse
    
    resp = MessagingResponse()

    # Get message details
    incoming_msg = request.values.get('Body', '').strip().lower()
    from_number = request.values.get('From', '')
    num_media = int(request.values.get('NumMedia', 0))

    current_app.logger.info(f"WhatsApp from {from_number}: '{incoming_msg}', media: {num_media}")

    # If user sent an image
    if num_media > 0:
        media_url = request.values.get('MediaUrl0', '')
        media_type = request.values.get('MediaContentType0', '')

        if not media_type.startswith('image/'):
            resp.message("⚠️ Please send an *image* of your medical report (JPG or PNG). I can't process other file types yet.")
            return str(resp), 200

        try:
            # Download the image from Twilio
            # Twilio requires auth to download media
            sid = os.getenv('TWILIO_ACCOUNT_SID')
            token = os.getenv('TWILIO_AUTH_TOKEN')
            
            image_response = http_requests.get(media_url, auth=(sid, token))
            
            if image_response.status_code != 200:
                resp.message("❌ Could not download the image. Please try again.")
                return str(resp), 200

            image_bytes = image_response.content

            # Send processing message
            resp.message("🔍 Analyzing your medical report... This may take a moment.")

            # Analyze the report
            analysis, error = analyze_report_image(image_bytes)

            if error:
                resp.message(f"❌ {error}")
                return str(resp), 200

            # Generate text summary for WhatsApp
            summary_lines = [
                f"📋 *HealthHive Report Analysis*",
                f"*{analysis.get('report_title', 'Medical Report')}*",
                "",
                f"📝 *Summary:* {analysis.get('summary', 'N/A')}",
                ""
            ]

            # Add abnormal values
            abnormals = analysis.get('abnormalities', [])
            if abnormals:
                summary_lines.append("⚠️ *Abnormal Values:*")
                for ab in abnormals:
                    summary_lines.append(f"  • {ab}")
                summary_lines.append("")

            # Add parameters summary
            params = analysis.get('parameters', [])
            if params:
                summary_lines.append("📊 *Test Results:*")
                for p in params:
                    icon = '🟢' if p.get('status') == 'normal' else ('🟡' if p.get('status') == 'borderline' else '🔴')
                    summary_lines.append(f"  {icon} {p['name']}: {p['value']}")
                summary_lines.append("")

            # Recommendations
            if analysis.get('recommendations'):
                summary_lines.append(f"💡 *Recommendations:* {analysis['recommendations']}")
                summary_lines.append("")

            summary_lines.append("⚕️ _Disclaimer: This is AI-generated analysis for informational purposes only. Always consult your doctor._")
            summary_lines.append("")
            summary_lines.append("🌐 Visit healthhive.in for the full experience!")

            # Generate PDF
            pdf_bytes = generate_report_pdf(analysis)

            if pdf_bytes:
                # Save PDF to static/uploads for serving
                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'whatsapp')
                os.makedirs(upload_dir, exist_ok=True)
                
                pdf_filename = f"report_{uuid.uuid4().hex[:12]}.pdf"
                pdf_path = os.path.join(upload_dir, pdf_filename)
                
                with open(pdf_path, 'wb') as f:
                    f.write(pdf_bytes)

                # Build the public URL for the PDF
                # In production, this should be your actual domain
                base_url = os.getenv('BASE_URL', request.host_url.rstrip('/'))
                pdf_url = f"{base_url}/static/uploads/whatsapp/{pdf_filename}"

                # Send the summary text
                msg = resp.message('\n'.join(summary_lines))
                
                # Send a follow-up with the PDF
                # Note: Twilio TwiML can only respond once, so we send PDF via API
                send_whatsapp_message(
                    from_number,
                    "📄 Here's your detailed report PDF:",
                    media_url=pdf_url
                )
            else:
                resp.message('\n'.join(summary_lines))

        except Exception as e:
            current_app.logger.error(f"WhatsApp webhook error: {e}")
            resp.message("❌ Something went wrong while processing your report. Please try again later.")

    # Text-only messages
    elif incoming_msg in ['hi', 'hello', 'hey', 'start']:
        resp.message(
            "👋 *Welcome to HealthHive!*\n\n"
            "I can analyze your medical reports instantly.\n\n"
            "📸 *Just send me a photo* of your blood test, pathology report, or any medical report, "
            "and I'll:\n"
            "  • Explain every value in simple language\n"
            "  • Color-code abnormal results\n"
            "  • Generate a downloadable PDF summary\n"
            "  • Suggest dietary improvements\n\n"
            "🔒 Your data is processed securely and not stored.\n\n"
            "Try it now — snap a photo of your report and send it!"
        )

    elif incoming_msg == 'help':
        resp.message(
            "ℹ️ *HealthHive Bot Help*\n\n"
            "• Send a *photo of a medical report* to get an instant AI analysis\n"
            "• Type *hi* to see the welcome message\n"
            "• Type *help* to see this message\n\n"
            "🌐 For the full experience, visit our website:\n"
            "healthhive.in\n\n"
            "⚕️ _This bot provides informational analysis only. Always consult your doctor._"
        )

    else:
        resp.message(
            "📸 Send me a *photo of your medical report* and I'll analyze it for you!\n\n"
            "Type *help* for more info."
        )

    return str(resp), 200


@whatsapp_bp.route('/status', methods=['POST'])
def message_status():
    """Twilio message status callback (optional, for tracking delivery)."""
    message_sid = request.values.get('MessageSid', '')
    status = request.values.get('MessageStatus', '')
    current_app.logger.info(f"WhatsApp message {message_sid}: {status}")
    return '', 204
