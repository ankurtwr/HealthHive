from flask import Blueprint, render_template, redirect, url_for, request, jsonify, flash, current_app
from flask_login import login_required, current_user
from medicine_service import get_search_history
from forms import SearchForm
from db import query_one, query_all, execute

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    # If the user is authenticated, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('main/home.html')


@main_bp.route('/dashboard')
@login_required                           
def dashboard():
    history = get_search_history(current_user.id, limit=8)
    form    = SearchForm()
    return render_template('main/dashboard.html', history=history, form=form)


@main_bp.route('/image-search')
@login_required
def image_search_page():
    return render_template('main/image_search.html')


# ── Terms & Conditions ──────────────────────────────────────────────────
@main_bp.route('/terms', methods=['GET', 'POST'])
@login_required
def terms():
    if request.method == 'POST':
        current_user.accept_terms()
        flash('Terms and Conditions accepted. Welcome to HealthHive!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('main/terms.html')


# ── User Profile ────────────────────────────────────────────────────────
@main_bp.route('/profile')
@login_required
def profile():
    # Fetch saved medicines
    saved_medicines = query_all("""
        SELECT um.id as save_id, m.* FROM user_medicines um
        JOIN medicines m ON um.medicine_id = m.id
        WHERE um.user_id = %s
        ORDER BY um.created_at DESC
    """, (current_user.id,))
    
    # Fetch prescriptions (only saved ones)
    prescriptions = query_all("""
        SELECT * FROM user_prescriptions
        WHERE user_id = %s AND is_saved = 1
        ORDER BY created_at DESC
    """, (current_user.id,))
    
    # Fetch active medicine reminders
    reminders = query_all("""
        SELECT * FROM medicine_reminders
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (current_user.id,))
    
    # Fetch saved medical reports (Health Vault - only explicitly saved ones)
    saved_reports = query_all("""
        SELECT id, report_type, file_path, created_at FROM user_reports
        WHERE user_id = %s AND is_saved = 1
        ORDER BY created_at DESC
    """, (current_user.id,))
    
    return render_template('main/profile.html', 
                           saved_medicines=saved_medicines, 
                           prescriptions=prescriptions, 
                           reminders=reminders,
                           saved_reports=saved_reports)


# ── Medicine Reminders ──────────────────────────────────────────────────
@main_bp.route('/profile/reminder/add', methods=['POST'])
@login_required
def add_reminder():
    medicine_name = request.form.get('medicine_name', '').strip()
    dosage = request.form.get('dosage', '').strip()
    reminder_time = request.form.get('reminder_time', '08:00').strip()
    instructions = request.form.get('instructions', '').strip()
    
    if not medicine_name:
        flash('Medicine name is required for reminders.', 'danger')
        return redirect(url_for('main.profile'))
        
    execute("""
        INSERT INTO medicine_reminders 
        (user_id, medicine_name, dosage, reminder_time, instructions)
        VALUES (%s, %s, %s, %s, %s)
    """, (current_user.id, medicine_name, dosage, reminder_time, instructions))
    
    flash('Medicine reminder added successfully!', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route('/profile/reminder/delete/<int:reminder_id>', methods=['POST'])
@login_required
def delete_reminder(reminder_id):
    execute("DELETE FROM medicine_reminders WHERE id = %s AND user_id = %s", (reminder_id, current_user.id))
    flash('Reminder deleted successfully.', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route('/profile/phone/update', methods=['POST'])
@login_required
def update_phone():
    phone_number = request.form.get('phone_number', '').strip()
    execute("UPDATE users SET phone_number = %s WHERE id = %s", (phone_number or None, current_user.id))
    flash('WhatsApp phone number updated successfully!', 'success')
    return redirect(url_for('main.profile'))


# ── Save / Remove Medicines ────────────────────────────────────────────
@main_bp.route('/profile/medicine/save/<int:medicine_id>', methods=['POST'])
@login_required
def save_medicine(medicine_id):
    try:
        execute("""
            INSERT IGNORE INTO user_medicines (user_id, medicine_id)
            VALUES (%s, %s)
        """, (current_user.id, medicine_id))
        return jsonify({'success': True, 'message': 'Medicine saved to your profile.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@main_bp.route('/profile/medicine/remove/<int:save_id>', methods=['POST'])
@login_required
def remove_saved_medicine(save_id):
    execute("DELETE FROM user_medicines WHERE id = %s AND user_id = %s", (save_id, current_user.id))
    flash('Saved medicine removed.', 'success')
    return redirect(url_for('main.profile'))


# ── Prescription Upload & OCR ──────────────────────────────────────────
@main_bp.route('/profile/prescription/upload', methods=['POST'])
@login_required
def upload_prescription():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('main.profile'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('main.profile'))
        
    if file:
        import io
        import os
        import tempfile
        import subprocess
        from PIL import Image
        from google import genai
        from google.genai import types
        
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            extracted_text = ""
            
            # Save file to static/uploads upload folder
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
                
            import uuid
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            file_path = os.path.join('static', 'uploads', filename)
            abs_file_path = os.path.join(upload_dir, filename)
            
            file.save(abs_file_path)
            
            is_pdf = file.filename.lower().endswith('.pdf')
            
            # Perform OCR extraction
            if api_key:
                client = genai.Client(api_key=api_key)
                prompt = "Extract all text visible in this prescription, especially medicine names and directions. Return only the extracted text."
                
                if is_pdf:
                    with open(abs_file_path, 'rb') as f:
                        pdf_bytes = f.read()
                    doc_input = types.Part.from_bytes(data=pdf_bytes, mime_type='application/pdf')
                else:
                    doc_input = Image.open(abs_file_path)

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[doc_input, prompt]
                )
                extracted_text = response.text.strip()
            else:
                # Fallback to local OCR script (images only)
                if not is_pdf:
                    scripts_dir = os.path.join(current_app.root_path, 'scripts')
                    ps_script = os.path.join(scripts_dir, 'ocr.ps1')
                    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_script, "-ImagePath", abs_file_path]
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if result.returncode == 0:
                        for line in result.stdout.splitlines():
                            if line.startswith("RECOGNIZED:"):
                                extracted_text = line[len("RECOGNIZED:"):].strip()
                                break
                            
            if not extracted_text:
                extracted_text = "No readable text extracted from prescription."
                
            # Insert record as explicitly saved (is_saved = 1)
            execute("""
                INSERT INTO user_prescriptions (user_id, file_path, extracted_text, is_saved)
                VALUES (%s, %s, %s, 1)
            """, (current_user.id, file_path, extracted_text))
            
            flash('Prescription uploaded and saved to Health Vault successfully!', 'success')
            
        except Exception as e:
            flash(f"Error processing prescription: {e}", 'danger')
            
    return redirect(url_for('main.profile'))


# ── Health Vault: Delete Report ────────────────────────────────────────
@main_bp.route('/profile/report/delete/<int:report_id>', methods=['POST'])
@login_required
def delete_report(report_id):
    """Delete a saved medical report from the Health Vault."""
    import os
    
    # Get file path before deleting
    report = query_one("SELECT file_path FROM user_reports WHERE id = %s AND user_id = %s", 
                       (report_id, current_user.id))
    
    if report and report.get('file_path'):
        abs_path = os.path.join(current_app.root_path, report['file_path'])
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
            except OSError:
                pass
    
    execute("DELETE FROM user_reports WHERE id = %s AND user_id = %s", (report_id, current_user.id))
    flash('Report deleted from Health Vault.', 'success')
    return redirect(url_for('main.profile'))


# ── Health Vault: Delete Prescription ──────────────────────────────────
@main_bp.route('/profile/prescription/delete/<int:prescription_id>', methods=['POST'])
@login_required
def delete_prescription(prescription_id):
    """Delete a saved prescription from the Health Vault."""
    import os
    
    record = query_one("SELECT file_path FROM user_prescriptions WHERE id = %s AND user_id = %s",
                       (prescription_id, current_user.id))
    
    if record and record.get('file_path'):
        abs_path = os.path.join(current_app.root_path, record['file_path'])
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
            except OSError:
                pass
    
    execute("DELETE FROM user_prescriptions WHERE id = %s AND user_id = %s", (prescription_id, current_user.id))
    flash('Prescription deleted from Health Vault.', 'success')
    return redirect(url_for('main.profile'))