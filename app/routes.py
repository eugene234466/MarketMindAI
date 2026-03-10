# ============================================================
# ROUTES.PY — Main Application Routes
# Fixed: history page, error handling, debug routes
# ============================================================

from flask import render_template, request, jsonify, session, redirect, url_for, flash, Blueprint, send_file
import os
import time
import json
from datetime import datetime

# Create blueprint
main = Blueprint('main', __name__)

# Import core modules
from core.analyzer import analyze_idea, quick_analyze
from core.tasks import queue_analysis, get_task_status
from database.db import (
    init_db, create_user, get_user_by_email, 
    get_user_by_id, verify_password,
    save_research, get_history, get_research_by_id, delete_research
)
from config import Config


# ── 1. DEBUG ROUTES ─────────────────────────────────────────
@main.route('/debug')
def debug():
    """Debug endpoint to check routing"""
    return jsonify({
        "status": "ok",
        "message": "Routes are working!",
        "available_routes": [
            "/",
            "/intro",
            "/dashboard",
            "/about",
            "/terms",
            "/login",
            "/register",
            "/history",
            "/health",
            "/debug",
            "/debug-history",
            "/test",
            "/test-html"
        ],
        "session": {k: str(v) for k, v in session.items() if k != '_permanent'},
        "config": {
            "gemini_configured": bool(Config.GEMINI_API_KEY),
            "email_configured": bool(Config.EMAIL_ADDRESS),
            "base_url": Config.BASE_URL
        }
    })

@main.route('/debug-history')
def debug_history():
    """Debug endpoint for history issues"""
    if 'user_id' not in session:
        return jsonify({
            "error": "Not logged in", 
            "session": {k: str(v) for k, v in session.items()}
        }), 401
    
    try:
        from database.db import get_history, get_user_by_id
        
        user = get_user_by_id(session['user_id'])
        researches = get_history(session['user_id'])
        
        return jsonify({
            "success": True,
            "user": user,
            "research_count": len(researches) if researches else 0,
            "research": researches,
            "session": {k: str(v) for k, v in session.items()}
        })
    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc().split('\n')
        }), 500

@main.route('/test')
def test():
    """Simple test page"""
    return "<h1 style='color:#00e5ff; text-align:center; margin-top:100px;'>✅ Test Page Working!</h1><p style='text-align:center;'>Your app is running correctly.</p>"

@main.route('/test-html')
def test_html():
    """Test HTML template rendering"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MarketMind AI Test</title>
        <style>
            body { 
                background: #0a1628; 
                color: white; 
                font-family: 'Inter', Arial, sans-serif; 
                padding: 40px; 
                margin: 0;
            }
            .container { max-width: 600px; margin: 0 auto; }
            .card { 
                background: rgba(255,255,255,0.05); 
                padding: 30px; 
                border-radius: 15px;
                border: 1px solid rgba(0,229,255,0.2);
            }
            h1 { color: #00e5ff; margin-bottom: 20px; }
            a { 
                color: #00e5ff; 
                text-decoration: none; 
                margin-right: 15px;
                display: inline-block;
                padding: 10px 20px;
                border: 1px solid #00e5ff;
                border-radius: 50px;
                transition: all 0.3s;
            }
            a:hover {
                background: #00e5ff;
                color: #0a1628;
            }
            .links { margin-top: 30px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="card">
                <h1>✅ Templates Working!</h1>
                <p>If you can see this styled page, templates are working correctly.</p>
                <div class="links">
                    <a href="/intro">→ Intro Page</a>
                    <a href="/dashboard">→ Dashboard</a>
                    <a href="/about">→ About</a>
                    <a href="/login">→ Login</a>
                    <a href="/register">→ Register</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """


# ── 2. ROOT REDIRECT ────────────────────────────────────────
@main.route('/')
def root():
    """Root URL - redirect based on login status"""
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    return redirect(url_for('main.intro'))


# ── 3. INTRO PAGE ───────────────────────────────────────────
@main.route('/intro')
def intro():
    """Intro page for non-logged-in users"""
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    return render_template('intro.html')


# ── 4. MAIN DASHBOARD ───────────────────────────────────────
@main.route('/dashboard')
def index():
    """Main analysis page for logged-in users"""
    if 'user_id' not in session:
        return redirect(url_for('main.intro'))
    
    user = get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        flash('User not found. Please log in again.', 'warning')
        return redirect(url_for('main.login'))
    
    # Check if we have results from an analysis
    task_id = request.args.get('task')
    results_loaded = request.args.get('results')
    
    if task_id and results_loaded:
        # Get the results from the task
        from core.tasks import get_task_status
        status = get_task_status(task_id)
        if status["status"] == "completed" and status.get("results"):
            # Render dashboard with results
            return render_template(
                'dashboard.html', 
                user=user, 
                results=status["results"]
            )
        elif status["status"] == "processing":
            # Still processing - redirect back to loading
            return redirect(url_for('main.results', task_id=task_id))
    
    # Regular dashboard without results
    return render_template('index.html', user=user)


# ── 5. ABOUT PAGE ───────────────────────────────────────────
@main.route('/about')
def about():
    """About page"""
    user = None
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
    return render_template('about.html', user=user)


# ── 6. TERMS PAGE ───────────────────────────────────────────
@main.route('/terms')
def terms():
    """Terms and conditions page"""
    user = None
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
    return render_template('terms.html', user=user)


# ── 7. HEALTH CHECK ─────────────────────────────────────────
@main.route('/health')
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected",
        "service": "MarketMind AI"
    })


# ── 8. ANALYZE IDEA (ASYNC) ─────────────────────────────────
@main.route('/analyze', methods=['POST'])
def analyze():
    """Start analysis in background"""
    try:
        # Handle both form and JSON
        if request.is_json:
            data = request.get_json()
            idea = data.get('idea', '').strip()
            recipient_email = data.get('email', '')
        else:
            idea = request.form.get('idea', '').strip()
            recipient_email = request.form.get('email', '')
        
        if not idea:
            if request.is_json:
                return jsonify({"error": "No idea provided"}), 400
            flash('Please enter a business idea', 'danger')
            return redirect(url_for('main.index'))
        
        user_id = session.get('user_id')
        
        # Save idea to session for loading page
        session['last_idea'] = idea
        
        # Queue the analysis (10-minute timeout)
        task_id = queue_analysis(idea, user_id, recipient_email)
        
        if request.is_json:
            return jsonify({
                "status": "queued",
                "task_id": task_id,
                "message": "Analysis started. This may take 3-10 minutes.",
                "estimated_time": "5-10 minutes"
            })
        else:
            return redirect(url_for('main.results', task_id=task_id))
        
    except Exception as e:
        print(f"❌ Error queueing analysis: {e}")
        import traceback
        traceback.print_exc()
        if request.is_json:
            return jsonify({"error": str(e)}), 500
        flash('Analysis failed. Please try again.', 'danger')
        return redirect(url_for('main.index'))


# ── 9. RESULTS PAGE ─────────────────────────────────────────
@main.route('/results/<task_id>')
def results(task_id):
    """Show analysis results loading page"""
    user = None
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
    
    return render_template(
        'results_loading.html',
        task_id=task_id,
        user=user
    )


# ── 10. CHECK ANALYSIS STATUS ───────────────────────────────
@main.route('/analysis-status/<task_id>', methods=['GET'])
def analysis_status(task_id):
    """Check if analysis is complete"""
    status = get_task_status(task_id)
    return jsonify(status)


# ── 11. GET RESULTS ─────────────────────────────────────────
@main.route('/get-results/<task_id>', methods=['GET'])
def get_results(task_id):
    """Get completed analysis results"""
    status = get_task_status(task_id)
    
    if status["status"] == "completed":
        return jsonify({
            "status": "completed",
            "results": status["results"],
            "pdf_url": f"/download/{task_id}" if status.get("pdf_path") else None
        })
    elif status["status"] == "processing":
        return jsonify({
            "status": "processing",
            "message": "Analysis still running..."
        })
    elif status["status"].startswith("failed"):
        return jsonify({
            "status": "failed",
            "error": status["status"]
        }), 500
    else:
        return jsonify({
            "status": "not_found",
            "error": "Task not found"
        }), 404


# ── 12. DOWNLOAD PDF ────────────────────────────────────────
@main.route('/download/<path:filename>')
def download_pdf(filename):
    """Download generated PDF file"""
    try:
        # Check multiple possible locations
        possible_paths = [
            filename,  # direct path
            os.path.join(Config.REPORTS_FOLDER, filename),  # in reports folder
            os.path.join(Config.REPORTS_FOLDER, os.path.basename(filename)),  # just filename in reports
        ]
        
        for pdf_path in possible_paths:
            if os.path.exists(pdf_path):
                return send_file(
                    pdf_path,
                    as_attachment=True,
                    download_name=os.path.basename(pdf_path),
                    mimetype='application/pdf'
                )
        
        # Also check if it's a task_id
        if not '.' in filename and not '/' in filename:
            # Might be a task_id
            from core.tasks import task_pdfs
            if filename in task_pdfs and task_pdfs[filename] and os.path.exists(task_pdfs[filename]):
                return send_file(
                    task_pdfs[filename],
                    as_attachment=True,
                    download_name=f"MarketMind_Report_{filename}.pdf",
                    mimetype='application/pdf'
                )
        
        flash('PDF file not found', 'danger')
        return redirect(url_for('main.history'))
        
    except Exception as e:
        print(f"❌ Download error: {e}")
        flash('Error downloading PDF', 'danger')
        return redirect(url_for('main.history'))


# ── 13. HISTORY ─────────────────────────────────────────────
@main.route('/history')
def history():
    """View research history"""
    if 'user_id' not in session:
        flash('Please log in to view history', 'warning')
        return redirect(url_for('main.intro'))
    
    try:
        # Get user info
        user = get_user_by_id(session['user_id'])
        if not user:
            # User not found in database, clear session
            session.clear()
            flash('User not found. Please log in again.', 'warning')
            return redirect(url_for('main.login'))
        
        # Get research history
        researches = get_history(session['user_id'])
        
        # Ensure researches is a list
        if researches is None:
            researches = []
        
        return render_template(
            'history.html',
            user=user,
            research=researches
        )
    except Exception as e:
        print(f"❌ History page error: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading history. Please try again.', 'danger')
        # Return empty history rather than crashing
        return render_template(
            'history.html',
            user={'id': session.get('user_id'), 'name': 'User', 'email': ''},
            research=[]
        )



         # ── 14. VIEW RESEARCH ───────────────────────────────────────
@main.route('/research/<int:research_id>')
def view_research(research_id):
    """View past research"""
    if 'user_id' not in session:
        flash('Please log in to view research', 'warning')
        return redirect(url_for('main.intro'))
    
    try:
        # Get research from database
        research = get_research_by_id(research_id)
        
        # Check if research exists
        if not research:
            flash(f'Research ID {research_id} not found', 'danger')
            return redirect(url_for('main.history'))
        
        # Check ownership
        if research.get('user_id') and research.get('user_id') != session['user_id']:
            flash('You do not have permission to view this research', 'danger')
            return redirect(url_for('main.history'))
        
        # Get user for template
        user = get_user_by_id(session['user_id'])
        if not user:
            user = {'id': session['user_id'], 'name': 'User', 'email': ''}
        
        print(f"✅ Loading research {research_id} for user {session['user_id']}")
        
        # Render dashboard with results
        return render_template(
            'dashboard.html',
            results=research,
            user=user
        )
        
    except Exception as e:
        print(f"❌ View research error for ID {research_id}: {e}")
        flash('Error loading research. Please try again.', 'danger')
        return redirect(url_for('main.history'))

# ── 15. DELETE RESEARCH ─────────────────────────────────────
@main.route('/history/delete/<int:research_id>', methods=['POST'])
def delete_research_route(research_id):
    """Delete a research item"""
    if 'user_id' not in session:
        flash('Please log in first', 'warning')
        return redirect(url_for('main.login'))
    
    try:
        # Get the research to check ownership
        research = get_research_by_id(research_id)
        
        # Check if research exists
        if not research:
            flash('Research not found', 'danger')
            return redirect(url_for('main.history'))
        
        # Check ownership
        if research.get('user_id') and research.get('user_id') != session['user_id']:
            flash('You do not have permission to delete this research', 'danger')
            return redirect(url_for('main.history'))
        
        # Delete the research
        success = delete_research(research_id)
        
        if success:
            flash('Research deleted successfully', 'success')
            print(f"✅ Deleted research ID: {research_id}")
        else:
            flash('Failed to delete research', 'danger')
        
    except Exception as e:
        print(f"❌ Delete error: {e}")
        flash('Error deleting research', 'danger')
    
    return redirect(url_for('main.history'))


# ── 16. USER REGISTRATION ───────────────────────────────────
@main.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        
        # Validation
        if not first_name or not last_name or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('register.html')
        
        if password != confirm:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return render_template('register.html')
        
        # Create full name
        name = f"{first_name} {last_name}".strip()
        
        user_id = create_user(name, email, password)
        
        if user_id:
            session['user_id'] = user_id
            session['user_name'] = name
            session['user_email'] = email
            flash('Account created successfully!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Email already exists. Please login instead.', 'warning')
            return redirect(url_for('main.login'))
    
    return render_template('register.html')


# ── 17. USER LOGIN ──────────────────────────────────────────
@main.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        
        if not email or not password:
            flash('Email and password are required', 'danger')
            return render_template('login.html')
        
        user = get_user_by_email(email)
        
        if user and verify_password(password, user['password']):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            
            if not remember:
                session.permanent = False
            
            flash(f'Welcome back, {user["name"]}!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password', 'danger')
            return render_template('login.html')
    
    return render_template('login.html')


# ── 18. USER LOGOUT ─────────────────────────────────────────
@main.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.intro'))


# ── 19. PROGRESS POLLING ENDPOINT ───────────────────────────
@main.route('/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    """Get detailed progress information"""
    status = get_task_status(task_id)
    
    # Add estimated time remaining
    if status["status"] == "processing":
        # Calculate progress based on time elapsed
        from core.tasks import task_start_time
        import time
        
        start_time = task_start_time.get(task_id, time.time())
        elapsed = time.time() - start_time
        
        if elapsed < 30:
            status["message"] = "AI is analysing your idea..."
            status["progress"] = 20
        elif elapsed < 60:
            status["message"] = "Researching market trends..."
            status["progress"] = 40
        elif elapsed < 120:
            status["message"] = "Analysing competitors..."
            status["progress"] = 60
        elif elapsed < 180:
            status["message"] = "Predicting sales performance..."
            status["progress"] = 80
        else:
            status["message"] = "Generating your report..."
            status["progress"] = 90
        
        remaining = max(0, 300 - elapsed)
        if remaining > 60:
            status["estimated_remaining"] = f"~{int(remaining/60)} minutes"
        else:
            status["estimated_remaining"] = f"~{int(remaining)} seconds"
    
    elif status["status"] == "queued":
        status["message"] = "Waiting in queue..."
        status["progress"] = 5
        status["estimated_remaining"] = "Starting soon..."
    
    elif status["status"] == "completed":
        status["progress"] = 100
        status["message"] = "Analysis complete!"
    
    return jsonify(status)


# ── 20. QUICK ANALYZE ───────────────────────────────────────
@main.route('/quick-analyze', methods=['POST'])
def quick_analyze_route():
    """Quick analysis for simple ideas"""
    try:
        data = request.get_json()
        idea = data.get('idea', '').strip()
        
        if not idea:
            return jsonify({"error": "No idea provided"}), 400
        
        results = quick_analyze(idea)
        
        return jsonify({
            "status": "completed",
            "results": results
        })
        
    except Exception as e:
        print(f"❌ Quick analyze error: {e}")
        return jsonify({"error": str(e)}), 500


# ── 21. GENERATE REPORT ─────────────────────────────────────
@main.route('/report', methods=['POST'])
def generate_report():
    """Generate PDF report"""
    print("📄 Report endpoint called")  # Debug log
    try:
        from core.report_generator import generate_pdf
        
        idea = request.form.get('idea')
        results_json = request.form.get('results')
        
        if not idea or not results_json:
            print(f"Missing data: idea={idea}, results_json={bool(results_json)}")
            return jsonify({"error": "Missing data"}), 400
        
        try:
            results = json.loads(results_json)
        except Exception as e:
            print(f"Error parsing results JSON: {e}")
            return jsonify({"error": "Invalid results format"}), 400
        
        print(f"Generating PDF for idea: {idea}")
        pdf_path = generate_pdf(idea, results)
        
        if pdf_path:
            print(f"PDF generated: {pdf_path}")
            return jsonify({
                "success": True,
                "pdf_path": os.path.basename(pdf_path)
            })
        else:
            print(f"PDF generation failed")
            return jsonify({"error": "PDF generation failed"}), 500
            
    except Exception as e:
        print(f"❌ Report error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



# ── 22. SEND EMAIL ──────────────────────────────────────────
@main.route('/email', methods=['POST'])
def send_email_report():
    """Email report to user"""
    print("📧 Email endpoint called")  # Debug log
    try:
        from core.email_sender import send_report
        
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        print(f"Email data received: {list(data.keys())}")  # Debug log
        
        email = data.get('email')
        idea = data.get('idea')
        results_json = data.get('results')
        pdf_path = data.get('pdf_path')
        
        if not email or not idea:
            print(f"Missing email or idea: email={email}, idea={idea}")
            return jsonify({"success": False, "error": "Missing email or idea"}), 400
        
        # Validate email format
        if '@' not in email or '.' not in email:
            return jsonify({"success": False, "error": "Invalid email format"}), 400
        
        # Parse results if provided
        results = None
        if results_json:
            try:
                results = json.loads(results_json) if isinstance(results_json, str) else results_json
                print(f"Results parsed successfully")
            except Exception as e:
                print(f"Error parsing results: {e}")
                results = {"idea": idea}
        else:
            results = {"idea": idea}
        
        # Generate PDF if not provided or doesn't exist
        if not pdf_path or not os.path.exists(pdf_path):
            print(f"Generating new PDF for idea: {idea}")
            from core.report_generator import generate_pdf
            pdf_path = generate_pdf(idea, results)
            print(f"PDF generated at: {pdf_path}")
        
        if not pdf_path or not os.path.exists(pdf_path):
            print(f"PDF generation failed")
            return jsonify({"success": False, "error": "PDF generation failed"}), 500
        
        # Send email
        print(f"Sending email to {email}")
        success = send_report(email, idea, pdf_path, results)
        print(f"Email send result: {success}")
        
        return jsonify({
            "success": success,
            "message": "Email sent successfully" if success else "Email sending failed"
        })
            
    except Exception as e:
        print(f"❌ Email error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ── 23. CATCH-ALL FOR DEBUGGING ─────────────────────────────
@main.route('/<path:path>')
def catch_all(path):
    """Catch all undefined routes for debugging"""
    return jsonify({
        "error": "Route not found",
        "path": path,
        "available_routes": [
            "/",
            "/intro",
            "/dashboard",
            "/about",
            "/terms",
            "/login",
            "/register",
            "/history",
            "/health",
            "/debug",
            "/debug-history",
            "/test",
            "/test-html"
        ]
    }), 404
