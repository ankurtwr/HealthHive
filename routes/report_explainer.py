import io
import os
import json
import uuid
import markdown
from flask import Blueprint, request, jsonify, render_template, send_file, current_app
from flask_login import login_required, current_user
from PIL import Image
from google import genai
from google.genai import types
from db import execute, query_all, query_one

report_bp = Blueprint('report', __name__)


# ── Page Routes ─────────────────────────────────────────────────────────

@report_bp.route('/report-explainer')
@login_required
def report_explainer_page():
    """Render the report upload & analysis page."""
    load_id = request.args.get('load')
    loaded_report = None
    loaded_analysis = None
    loaded_diet = None

    if load_id:
        row = query_one("""
            SELECT id, analysis_json, diet_suggestions, is_saved FROM user_reports
            WHERE id = %s AND user_id = %s
        """, (load_id, current_user.id))
        if row:
            loaded_report = row
            try:
                loaded_analysis = json.loads(row['analysis_json']) if isinstance(row['analysis_json'], str) else row['analysis_json']
            except Exception:
                loaded_analysis = row['analysis_json']
            loaded_diet = row['diet_suggestions']

    # Fetch user's past reports for the sidebar (only explicitly saved ones)
    reports = []
    if not getattr(current_user, 'is_guest', False):
        reports = query_all("""
            SELECT id, report_type, created_at FROM user_reports
            WHERE user_id = %s AND is_saved = 1 ORDER BY created_at DESC LIMIT 10
        """, (current_user.id,))

    return render_template('main/report_explainer.html',
                           past_reports=reports,
                           loaded_report=loaded_report,
                           loaded_analysis=loaded_analysis,
                           loaded_diet=loaded_diet)


@report_bp.route('/diet-suggestions')
@login_required
def diet_suggestions_page():
    """Render the diet suggestions page with report context."""
    report_id = request.args.get('report_id')
    analysis = None
    suggestions = None

    if report_id:
        row = query_one("""
            SELECT analysis_json, diet_suggestions FROM user_reports
            WHERE id = %s AND user_id = %s
        """, (report_id, current_user.id))
        if row:
            analysis = json.loads(row['analysis_json']) if row['analysis_json'] else None
            raw_suggestions = row['diet_suggestions']
            if raw_suggestions:
                suggestions = markdown.markdown(raw_suggestions, extensions=['extra', 'nl2br'])

    return render_template('main/diet_suggestions.html',
                           analysis=analysis,
                           suggestions=suggestions,
                           report_id=report_id)


# ── API: Analyze Report ─────────────────────────────────────────────────

@report_bp.route('/api/report/analyze', methods=['POST'])
@login_required
def analyze_report():
    """Accept a medical report image, extract text via Gemini Vision, return analysis."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return jsonify({'error': 'Gemini API key not configured. Report analysis requires AI.'}), 500

    try:
        # Save uploaded file
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'reports')
        os.makedirs(upload_dir, exist_ok=True)

        filename = f"{uuid.uuid4().hex}_{file.filename}"
        file_path_rel = os.path.join('static', 'uploads', 'reports', filename)
        abs_path = os.path.join(upload_dir, filename)
        file.save(abs_path)

        # Check if PDF or Image
        is_pdf = file.filename.lower().endswith('.pdf')
        client = genai.Client(api_key=api_key)

        if is_pdf:
            with open(abs_path, 'rb') as f:
                pdf_bytes = f.read()
            doc_input = types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf')
        else:
            doc_input = Image.open(abs_path)

        # Step 1: Extract and analyze the medical report
        analysis_prompt = """You are a medical report analysis assistant. Analyze this medical report document (image or PDF) and return a JSON response with the following structure:

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
            contents=[doc_input, analysis_prompt]
        )

        raw_text = response.text.strip()

        # Clean potential markdown fences from response
        if raw_text.startswith('```'):
            raw_text = raw_text.split('\n', 1)[1] if '\n' in raw_text else raw_text[3:]
        if raw_text.endswith('```'):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        analysis = json.loads(raw_text)

        # Step 2: Generate diet suggestions based on abnormalities
        diet_suggestions = ""
        if analysis.get('abnormalities'):
            diet_prompt = f"""Based on these medical report abnormalities: {', '.join(analysis['abnormalities'])}

Provide WHO-based dietary suggestions in this format:

For each abnormality, suggest:
1. Foods to INCLUDE (that help improve the condition)
2. Foods to AVOID (that worsen the condition)
3. General lifestyle tip

Keep it practical and easy to understand. Use bullet points.
End with a clear disclaimer: "These are general WHO-based nutritional guidelines and NOT a substitute for professional medical advice. Always consult your doctor or registered dietitian."

Format as plain text with clear sections."""

            diet_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=diet_prompt
            )
            diet_suggestions = diet_response.text.strip()

        # Save to database
        report_id = execute("""
            INSERT INTO user_reports (user_id, file_path, report_type, raw_text, analysis_json, diet_suggestions)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            current_user.id,
            file_path_rel,
            analysis.get('report_title', 'Medical Report'),
            raw_text,
            json.dumps(analysis),
            diet_suggestions
        ))

        return jsonify({
            'success': True,
            'report_id': report_id,
            'analysis': analysis,
            'diet_suggestions': diet_suggestions
        })

    except json.JSONDecodeError:
        return jsonify({
            'success': False,
            'error': 'AI returned an invalid response format. Please try again with a clearer image.'
        }), 422
    except Exception as e:
        current_app.logger.error(f"Report analysis error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ── API: Ask Question About Report ──────────────────────────────────────

@report_bp.route('/api/report/ask', methods=['POST'])
@login_required
def ask_about_report():
    """Q&A about a previously analyzed report."""
    data = request.json
    if not data or 'question' not in data or 'report_id' not in data:
        return jsonify({'error': 'Question and report_id are required'}), 400

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return jsonify({'error': 'AI not available'}), 500

    report = query_one("""
        SELECT analysis_json FROM user_reports
        WHERE id = %s AND user_id = %s
    """, (data['report_id'], current_user.id))

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    try:
        client = genai.Client(api_key=api_key)
        prompt = f"""You are a helpful medical report assistant. A patient has a medical report with this analysis:

{report['analysis_json']}

The patient asks: "{data['question']}"

Respond in simple, patient-friendly language. Be helpful but always remind them to consult their doctor for personalized advice. Keep your answer concise (3-5 sentences)."""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )

        return jsonify({
            'success': True,
            'answer': response.text.strip()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── API: Save Report to Vault ───────────────────────────────────────────

@report_bp.route('/api/report/save/<int:report_id>', methods=['POST'])
@login_required
def save_report_to_vault(report_id):
    """Mark a temporary report analysis as permanently saved in the Health Vault."""
    try:
        execute("""
            UPDATE user_reports 
            SET is_saved = 1 
            WHERE id = %s AND user_id = %s
        """, (report_id, current_user.id))
        return jsonify({'success': True, 'message': 'Report saved to your Health Vault.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── API: Download Report as PDF ─────────────────────────────────────────

@report_bp.route('/api/report/download-pdf', methods=['POST'])
@login_required
def download_report_pdf():
    """Generate a PDF of the analyzed report."""
    data = request.json
    if not data or 'report_id' not in data:
        return jsonify({'error': 'report_id required'}), 400

    lang = data.get('lang', 'en')

    report = query_one("""
        SELECT * FROM user_reports
        WHERE id = %s AND user_id = %s
    """, (data['report_id'], current_user.id))

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    api_key = os.getenv("GEMINI_API_KEY")

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        analysis = json.loads(report['analysis_json']) if report['analysis_json'] else {}

        # ── HINDI TRANSLATION BLOCK ──
        if lang == 'hi' and api_key:
            try:
                client = genai.Client(api_key=api_key)
                translation_prompt = f"""You are an expert health communicator translating medical reports for everyday patients. Translate this medical report analysis JSON into natural, conversational Hindi (आम बोलचाल की हिंदी) that is easy for a layperson to understand.

JSON to translate:
{report['analysis_json']}

In the translated output, you MUST follow these critical rules:
1. Keep the JSON keys EXACTLY the same (report_title, patient_info, parameters, summary, recommendations, name, value, reference_range, status, explanation).
2. Avoid obscure or pure Sanskritized Hindi words. Use simple, conversational Hindi terms that people use in daily life. For example, use "रिपोर्ट" (not "विवरणपत्र" or "प्रतिवेदन"), "टेस्ट" (not "परीक्षण"), "ब्लड प्रेशर" (not "रक्तदाब"), "डॉक्टर" (not "चिकित्सक"), "चेकअप" (not "निरीक्षण").
3. For parameters[].name, write the parameter name with its English name and the Hindi transliteration in brackets, e.g. "Hemoglobin (हीमोग्लोबिन)" or "Cholesterol Total (टोटल कोलेस्ट्रॉल)".
4. For parameters[].value and parameters[].reference_range, do NOT translate digits, symbols (<, >, -, >=), or standard English units (mg/dL, g/dL, % etc.). Keep them exactly as they are in the original JSON.
5. Translate parameters[].explanation, summary, and recommendations into clear, encouraging, and simple Hindi. Explain what the terms mean in layperson's terms (e.g. explain Hemoglobin as "शरीर में ऑक्सीजन ले जाने वाले लाल रक्त कोशिकाओं का हिस्सा").
6. Translate parameters[].status to be exactly one of: "normal", "borderline", "critical". Do NOT translate this value itself (keep it in English lowercase), so the code's color coding logic continues to work.

Output ONLY the translated JSON in valid JSON format. Do not include markdown code fences or extra text."""

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=translation_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                
                raw_translation = response.text.strip()
                analysis = json.loads(raw_translation)
            except Exception as translation_error:
                current_app.logger.error(f"Translation failed, falling back to English: {translation_error}")
                # Fallback to English if translation fails

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=15*mm, bottomMargin=15*mm)

        # ── FONT SELECTION ──
        # Standard Helvetica does not support Devanagari script. We register Nirmala if Hindi is requested.
        pdf_font = 'Helvetica'
        pdf_font_bold = 'Helvetica-Bold'
        pdf_font_italic = 'Helvetica-Oblique'

        if lang == 'hi':
            try:
                # Nirmala UI is the standard Windows font supporting all Indic scripts
                # Index 0 is Nirmala UI Regular, Index 1 is Nirmala UI Bold
                pdfmetrics.registerFont(TTFont('Nirmala', 'C:/Windows/Fonts/Nirmala.ttc', subfontIndex=0))
                pdfmetrics.registerFont(TTFont('Nirmala-Bold', 'C:/Windows/Fonts/Nirmala.ttc', subfontIndex=1))
                pdf_font = 'Nirmala'
                pdf_font_bold = 'Nirmala-Bold'
                pdf_font_italic = 'Nirmala'
            except Exception as e:
                current_app.logger.error(f"Failed to register Nirmala font collection: {e}")

        # ── LABELS IN HINDI / ENGLISH ──
        labels = {
            'pdf_title': "HealthHive — Medical Report Analysis" if lang != 'hi' else "HealthHive — मेडिकल रिपोर्ट विश्लेषण",
            'report_title_lbl': "Report Title:" if lang != 'hi' else "रिपोर्ट का शीर्षक:",
            'patient_info_lbl': "Patient Info:" if lang != 'hi' else "मरीज की जानकारी:",
            'analyzed_on_lbl': "Analyzed On:" if lang != 'hi' else "विश्लेषण की तिथि:",
            'summary_lbl': "Summary" if lang != 'hi' else "सारांश",
            'parameters_lbl': "Test Parameters" if lang != 'hi' else "परीक्षण के पैरामीटर",
            'th_parameter': "Parameter" if lang != 'hi' else "पैरामीटर",
            'th_value': "Value" if lang != 'hi' else "मान / मूल्य",
            'th_reference': "Reference Range" if lang != 'hi' else "सामान्य रेंज",
            'th_status': "Status" if lang != 'hi' else "स्थिति",
            'explanations_lbl': "What Do These Values Mean?" if lang != 'hi' else "इन मूल्यों का क्या मतलब है?",
            'disclaimer': ("<b>⚕️ Important Disclaimer:</b> This analysis is generated by AI for informational purposes only. "
                           "It is NOT a substitute for professional medical advice, diagnosis, or treatment. "
                           "Always consult a qualified healthcare provider before making any health decisions. © 2026 HealthHive") if lang != 'hi' else
                          ("<b>⚕️ महत्वपूर्ण अस्वीकरण (Disclaimer):</b> यह विश्लेषण केवल सूचनात्मक उद्देश्यों के लिए एआई द्वारा उत्पन्न किया गया है। "
                           "यह पेशेवर चिकित्सा सलाह, निदान या उपचार का विकल्प नहीं है। "
                           "कोई भी स्वास्थ्य संबंधी निर्णय लेने से पहले हमेशा किसी योग्य डॉक्टर से सलाह लें। © 2026 HealthHive")
        }

        styles = getSampleStyleSheet()
        
        # Typography matching language font selection
        title_style = ParagraphStyle('CustomTitle', parent=styles['Title'],
                                     fontSize=20, textColor=HexColor('#0d9488'),
                                     spaceAfter=12, alignment=0, fontName=pdf_font_bold)
        
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'],
                                       fontSize=13, textColor=HexColor('#1a2e2a'),
                                       spaceAfter=10, spaceBefore=18, fontName=pdf_font_bold)
        
        body_style = ParagraphStyle('CustomBody', parent=styles['Normal'],
                                    fontSize=10, textColor=HexColor('#4a6b63'),
                                    spaceAfter=6, leading=14, fontName=pdf_font)
        
        disclaimer_style = ParagraphStyle('Disclaimer', parent=styles['Normal'],
                                          fontSize=8, textColor=HexColor('#6b8f86'),
                                          spaceAfter=4, leading=10, fontName=pdf_font_italic)

        # Table Styles
        th_style = ParagraphStyle('TableHeader', parent=styles['Normal'],
                                  fontSize=9, textColor=HexColor('#ffffff'),
                                  fontName=pdf_font_bold, leading=12)
        
        td_style = ParagraphStyle('TableCell', parent=styles['Normal'],
                                  fontSize=9, textColor=HexColor('#1a2e2a'),
                                  fontName=pdf_font, leading=12)
        
        td_status_style = ParagraphStyle('TableStatusCell', parent=styles['Normal'],
                                         fontSize=9, textColor=HexColor('#1a2e2a'),
                                         fontName=pdf_font_bold, leading=12)

        elements = []

        # Header Block
        elements.append(Paragraph(labels['pdf_title'], title_style))
        elements.append(Paragraph(f"<b>{labels['report_title_lbl']}</b> {analysis.get('report_title', 'Medical Report')}", body_style))
        elements.append(Paragraph(f"<b>{labels['patient_info_lbl']}</b> {analysis.get('patient_info', 'N/A')}", body_style))
        elements.append(Paragraph(f"<b>{labels['analyzed_on_lbl']}</b> {report['created_at'].strftime('%d %b %Y, %H:%M') if report['created_at'] else 'N/A'}", body_style))
        elements.append(Spacer(1, 4*mm))

        # Overall Summary Section
        elements.append(Paragraph(labels['summary_lbl'], heading_style))
        elements.append(Paragraph(analysis.get('summary', 'No summary available.'), body_style))
        elements.append(Spacer(1, 4*mm))

        # Parameters Table
        params = analysis.get('parameters', [])
        if params:
            elements.append(Paragraph(labels['parameters_lbl'], heading_style))

            # Table Header
            table_data = [[
                Paragraph(f"<b>{labels['th_parameter']}</b>", th_style),
                Paragraph(f"<b>{labels['th_value']}</b>", th_style),
                Paragraph(f"<b>{labels['th_reference']}</b>", th_style),
                Paragraph(f"<b>{labels['th_status']}</b>", th_style)
            ]]

            row_backgrounds = []
            
            for p in params:
                status = p.get('status', 'normal').lower()
                
                # Dynamic translation for status tags in Hindi
                status_label = status.upper()
                if lang == 'hi':
                    if status == 'critical':
                        status_label = 'गंभीर'
                    elif status == 'borderline':
                        status_label = 'सीमा पर'
                    else:
                        status_label = 'सामान्य'
                
                table_data.append([
                    Paragraph(p.get('name', ''), td_style),
                    Paragraph(p.get('value', ''), td_style),
                    Paragraph(p.get('reference_range', ''), td_style),
                    Paragraph(status_label, td_status_style)
                ])

                if status == 'critical':
                    row_backgrounds.append(HexColor('#fee2e2')) # Light red
                elif status == 'borderline':
                    row_backgrounds.append(HexColor('#fef3c7')) # Light yellow
                else:
                    row_backgrounds.append(HexColor('#dcfce7')) # Light green

            t = Table(table_data, colWidths=[55*mm, 35*mm, 55*mm, 35*mm])
            
            style_cmds = [
                ('BACKGROUND', (0, 0), (-1, 0), HexColor('#0d9488')), # Teal header
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cbd5e1')),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]
            
            for i, bg_color in enumerate(row_backgrounds):
                style_cmds.append(('BACKGROUND', (0, i+1), (-1, i+1), bg_color))

            t.setStyle(TableStyle(style_cmds))
            elements.append(t)
            elements.append(Spacer(1, 4*mm))

        # "What Do These Values Mean?" Section
        if params:
            elements.append(Paragraph(labels['explanations_lbl'], heading_style))
            
            for p in params:
                status = p.get('status', 'normal').lower()
                status_bullet = "🟢"
                bg_color_hex = "#dcfce7"
                border_color_hex = "#0d9488"
                
                if status == 'critical':
                    status_bullet = "🔴"
                    bg_color_hex = "#fee2e2"
                    border_color_hex = "#ef4444"
                elif status == 'borderline':
                    status_bullet = "🟡"
                    bg_color_hex = "#fef3c7"
                    border_color_hex = "#f59e0b"

                explanation_html = f"<b>{status_bullet} {p.get('name', '')}</b> ({p.get('value', '')})<br/>{p.get('explanation', '')}"
                card_para = Paragraph(explanation_html, td_style)
                
                card_table = Table([[card_para]], colWidths=[180*mm])
                card_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), HexColor(bg_color_hex)),
                    ('BOX', (0, 0), (-1, -1), 0.5, HexColor(border_color_hex)),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 10),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                
                elements.append(card_table)
                elements.append(Spacer(1, 2*mm))

        # Standard Medical Disclaimer
        elements.append(Spacer(1, 6*mm))
        elements.append(Paragraph(labels['disclaimer'], disclaimer_style))

        doc.build(elements)
        buffer.seek(0)

        download_filename = f"HealthHive_Report_{data['report_id']}_Hindi.pdf" if lang == 'hi' else f"HealthHive_Report_{data['report_id']}.pdf"

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"HealthHive_Report_{data['report_id']}.pdf"
        )

    except Exception as e:
        current_app.logger.error(f"PDF generation error: {e}")
        return jsonify({'error': str(e)}), 500


# ── API: WhatsApp Share Link ────────────────────────────────────────────

@report_bp.route('/api/report/share-whatsapp', methods=['POST'])
@login_required
def share_whatsapp():
    """Generate a WhatsApp share deep-link with report summary."""
    data = request.json
    if not data or 'report_id' not in data:
        return jsonify({'error': 'report_id required'}), 400

    report = query_one("""
        SELECT analysis_json FROM user_reports
        WHERE id = %s AND user_id = %s
    """, (data['report_id'], current_user.id))

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    try:
        analysis = json.loads(report['analysis_json']) if report['analysis_json'] else {}

        # Build a concise WhatsApp message
        lines = [
            f"📋 *HealthHive Report Analysis*",
            f"*{analysis.get('report_title', 'Medical Report')}*",
            "",
            f"📝 *Summary:* {analysis.get('summary', 'N/A')}",
            "",
        ]

        abnormals = analysis.get('abnormalities', [])
        if abnormals:
            lines.append("⚠️ *Abnormal Values:*")
            for ab in abnormals:
                lines.append(f"  • {ab}")
            lines.append("")

        lines.append("🔗 Analyzed on HealthHive — Your Digital Health Companion")
        lines.append("⚕️ _Please consult your doctor for medical advice._")

        import urllib.parse
        message = '\n'.join(lines)
        whatsapp_url = f"https://wa.me/?text={urllib.parse.quote(message)}"

        return jsonify({
            'success': True,
            'whatsapp_url': whatsapp_url,
            'message': message
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ── API: Get Diet Suggestions ──────────────────────────────────────────

@report_bp.route('/api/report/diet/<int:report_id>')
@login_required
def get_diet_suggestions(report_id):
    """Fetch diet suggestions for a specific report."""
    report = query_one("""
        SELECT analysis_json, diet_suggestions FROM user_reports
        WHERE id = %s AND user_id = %s
    """, (report_id, current_user.id))

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    analysis = json.loads(report['analysis_json']) if report['analysis_json'] else {}

    return jsonify({
        'success': True,
        'abnormalities': analysis.get('abnormalities', []),
        'diet_suggestions': report['diet_suggestions'] or 'No specific dietary suggestions for this report.',
        'report_title': analysis.get('report_title', 'Medical Report')
    })
