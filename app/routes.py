# ============================================================
# ROUTES.PY — Main Application Routes
# Updated for async analysis + PostgreSQL + all templates
# ============================================================

from flask import render_template, request, jsonify, session, redirect, url_for, flash, Blueprint
import os
import time
from datetime import datetime

# Create blueprint
main = Blueprint('main', __name__)

# Import core modules
from core.analyzer import analyze_idea
from core.tasks import queue_analysis, get_task_status
from database.db import (
    init_db, create_user, get_user_by_email, 
    get_user_by_id, verify_password,
    save_research, get_history, get_research_by_id, delete_research
)
from config import Config


# ── 1. INITIALIZE ───────────────────────────────────────────
def init_routes(app):
    
    # Initialize database
    with app.app_context():
        init_db(app)
    
    # Register blueprint
    app.register_blueprint(main)
    
    # ── 2. HEALTH CHECK ─────────────────────────────────────
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for Railway"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected"
        })
    
    # ── 3. INTRO PAGE ───────────────────────────────────────
    @main.route('/')
    def intro():
        """Intro page for non-logged-in users"""
        if 'user_id' in session:
            return redirect(url_for('main.index'))
        return render_template('intro.html')
    
    # ── 4. MAIN DASHBOARD ───────────────────────────────────
    @main.route('/dashboard')
    def index():
        """Main analysis page for logged-in users"""
        if 'user_id' not in session:
            return redirect(url_for('main.intro'))
        
        user = get_user_by_id(session['user_id'])
        return render_template('index.html', user=user)
    
    # ── 5. ABOUT PAGE ───────────────────────────────────────
    @main.route('/about')
    def about():
        """About page"""
        user = None
        if 'user_id' in session:
            user = get_user_by_id(session['user_id'])
        return render_template('about.html', user=user)
    
    # ── 6. TERMS PAGE ───────────────────────────────────────
    @main.route('/terms')
    def terms():
        """Terms and conditions page"""
        user = None
        if 'user_id' in session:
            user = get_user_by_id(session['user_id'])
        return render_template('terms.html', user=user)
    
    # ── 7. ANALYZE IDEA (ASYNC) ─────────────────────────────
    @main.route('/analyze', methods=['POST'])
    def analyze():
        """Start analysis in background"""
        try:
            if request.method == 'GET':
                return render_template('index.html')
            
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
            if request.is_json:
                return jsonify({"error": str(e)}), 500
            flash('Analysis failed. Please try again.', 'danger')
            return redirect(url_for('main.index'))
    
    # ── 8. RESULTS PAGE ─────────────────────────────────────
    @main.route('/results/<task_id>')
    def results(task_id):
        """Show analysis results page"""
        user = None
        if 'user_id' in session:
            user = get_user_by_id(session['user_id'])
        
        return render_template(
            'results_loading.html',
            task_id=task_id,
            user=user
        )
    
    # ── 9. CHECK ANALYSIS STATUS ────────────────────────────
    @main.route('/analysis-status/<task_id>', methods=['GET'])
    def analysis_status(task_id):
        """Check if analysis is complete"""
        status = get_task_status(task_id)
        return jsonify(status)
    
    # ── 10. GET RESULTS ─────────────────────────────────────
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
    
    # ── 11. DOWNLOAD PDF ─────────────────────────────────────
    @main.route('/download/<task_id>', methods=['GET'])
    def download_pdf(task_id):
        """Download generated PDF"""
        from flask import send_file
        
        status = get_task_status(task_id)
        if status["status"] == "completed" and status.get("pdf_path"):
            pdf_path = status["pdf_path"]
            if os.path.exists(pdf_path):
                return send_file(
                    pdf_path,
                    as_attachment=True,
                    download_name=f"MarketMind_Report_{task_id}.pdf",
                    mimetype='application/pdf'
                )
        
        flash('PDF not found', 'danger')
        return redirect(url_for('main.index'))
    
    # ── 12. HISTORY ─────────────────────────────────────────
    @main.route('/history')
    def history():
        """View research history"""
        if 'user_id' not in session:
            return redirect(url_for('main.intro'))
        
        user = get_user_by_id(session['user_id'])
        researches = get_history(session['user_id'])
        
        return render_template(
            'history.html',
            user=user,
            research=researches
        )
    
    # ── 13. VIEW RESEARCH ───────────────────────────────────
    @main.route('/research/<int:research_id>')
    def view_research(research_id):
        """View past research"""
        if 'user_id' not in session:
            return redirect(url_for('main.intro'))
        
        research = get_research_by_id(research_id)
        
        # Check ownership
        if not research or research.get('user_id') != session['user_id']:
            flash('Research not found', 'danger')
            return redirect(url_for('main.history'))
        
        return render_template(
            'dashboard.html',
            results=research
        )
    
    # ── 14. DELETE RESEARCH ─────────────────────────────────
    @main.route('/history/delete/<int:research_id>', methods=['POST'])
    def delete_research_route(research_id):
        """Delete a research item"""
        if 'user_id' not in session:
            return redirect(url_for('main.intro'))
        
        research = get_research_by_id(research_id)
        
        # Check ownership
        if research and research.get('user_id') == session['user_id']:
            delete_research(research_id)
            flash('Research deleted successfully', 'success')
        else:
            flash('Research not found', 'danger')
        
        return redirect(url_for('main.history'))
    
    # ── 15. USER REGISTRATION ───────────────────────────────
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
    
    # ── 16. USER LOGIN ──────────────────────────────────────
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
    
    # ── 17. USER LOGOUT ─────────────────────────────────────
    @main.route('/logout')
    def logout():
        """User logout"""
        session.clear()
        flash('You have been logged out', 'info')
        return redirect(url_for('main.intro'))
    
    # ── 18. PROGRESS POLLING ENDPOINT ───────────────────────
    @main.route('/progress/<task_id>', methods=['GET'])
    def get_progress(task_id):
        """Get detailed progress information"""
        status = get_task_status(task_id)
        
        # Add estimated time remaining
        if status["status"] == "processing":
            status["estimated_remaining"] = "2-5 minutes"
            status["progress"] = 50
        elif status["status"] == "queued":
            status["estimated_remaining"] = "Starting soon..."
            status["progress"] = 0
        elif status["status"] == "completed":
            status["progress"] = 100
        
        return jsonify(status)
    
    # ── 19. QUICK ANALYZE ───────────────────────────────────
    @main.route('/quick-analyze', methods=['POST'])
    def quick_analyze():
        """Quick analysis for simple ideas"""
        try:
            data = request.get_json()
            idea = data.get('idea', '').strip()
            
            if not idea:
                return jsonify({"error": "No idea provided"}), 400
            
            from core.gemini_client import analyze_idea as quick_ai
            
            ai_insights = quick_ai(idea)
            
            return jsonify({
                "status": "completed",
                "results": {
                    "idea": idea,
                    "ai_insights": ai_insights,
                    "quick": True
                }
            })
            
        except Exception as e:
            print(f"❌ Quick analyze error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ── 20. GENERATE REPORT ─────────────────────────────────
    @main.route('/report', methods=['POST'])
    def generate_report():
        """Generate PDF report"""
        try:
            from core.report_generator import generate_pdf
            
            idea = request.form.get('idea')
            results_json = request.form.get('results')
            
            if not idea or not results_json:
                return jsonify({"error": "Missing data"}), 400
            
            import json
            results = json.loads(results_json)
            
            pdf_path = generate_pdf(idea, results)
            
            if pdf_path:
                return jsonify({
                    "success": True,
                    "pdf_path": os.path.basename(pdf_path)
                })
            else:
                return jsonify({"error": "PDF generation failed"}), 500
                
        except Exception as e:
            print(f"❌ Report error: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ── 21. SEND EMAIL ─────────────────────────────────────
    @main.route('/email', methods=['POST'])
    def send_email_report():
        """Email report to user"""
        try:
            from core.email_sender import send_report
            
            email = request.form.get('email')
            idea = request.form.get('idea')
            results_json = request.form.get('results')
            
            if not email or not idea or not results_json:
                return jsonify({"error": "Missing data"}), 400
            
            import json
            results = json.loads(results_json)
            
            # Generate PDF first
            from core.report_generator import generate_pdf
            pdf_path = generate_pdf(idea, results)
            
            if not pdf_path:
                return jsonify({"error": "PDF generation failed"}), 500
            
            # Send email
            success = send_report(email, idea, pdf_path, results)
            
            return jsonify({
                "success": success,
                "error": None if success else "Email sending failed"
            })
                
        except Exception as e:
            print(f"❌ Email error: {e}")
            return jsonify({"error": str(e)}), 500
    
    return app
