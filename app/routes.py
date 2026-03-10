# ============================================================
# ROUTES.PY — Main Application Routes
# Updated for async analysis + PostgreSQL
# ============================================================

from flask import render_template, request, jsonify, session, redirect, url_for
import os
import time
from datetime import datetime

# Import core modules
from core.analyzer import analyze_idea
from core.tasks import queue_analysis, get_task_status
from database.db import (
    init_db, create_user, get_user_by_email, 
    get_user_by_id, verify_password,
    save_research, get_history, get_research_by_id
)
from config import Config


# ── 1. INITIALIZE ───────────────────────────────────────────
def init_routes(app):
    
    # Initialize database
    with app.app_context():
        init_db(app)
    
    # ── 2. HEALTH CHECK ─────────────────────────────────────
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for Railway"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected"
        })
    
    # ── 3. MAIN PAGE ────────────────────────────────────────
    @app.route('/')
    def index():
        """Render main analysis page"""
        user = None
        if 'user_id' in session:
            user = get_user_by_id(session['user_id'])
        return render_template('index.html', user=user)
    
    # ── 4. ANALYZE IDEA (ASYNC) ─────────────────────────────
    @app.route('/analyze', methods=['POST'])
    def analyze():
        """Start analysis in background"""
        try:
            data = request.get_json()
            idea = data.get('idea', '').strip()
            
            if not idea:
                return jsonify({"error": "No idea provided"}), 400
            
            # Optional email for report
            recipient_email = data.get('email', '')
            user_id = session.get('user_id')
            
            # Queue the analysis (10-minute timeout)
            task_id = queue_analysis(idea, user_id, recipient_email)
            
            return jsonify({
                "status": "queued",
                "task_id": task_id,
                "message": "Analysis started. This may take 3-10 minutes.",
                "estimated_time": "5-10 minutes"
            })
            
        except Exception as e:
            print(f"❌ Error queueing analysis: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ── 5. CHECK ANALYSIS STATUS ────────────────────────────
    @app.route('/analysis-status/<task_id>', methods=['GET'])
    def analysis_status(task_id):
        """Check if analysis is complete"""
        status = get_task_status(task_id)
        return jsonify(status)
    
    # ── 6. GET RESULTS ──────────────────────────────────────
    @app.route('/results/<task_id>', methods=['GET'])
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
    
    # ── 7. DOWNLOAD PDF ─────────────────────────────────────
    @app.route('/download/<task_id>', methods=['GET'])
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
                    download_name=f"MarketMind_Report_{task_id}.pdf"
                )
        
        return jsonify({"error": "PDF not found"}), 404
    
    # ── 8. HISTORY ──────────────────────────────────────────
    @app.route('/history')
    def history():
        """View research history"""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = get_user_by_id(session['user_id'])
        researches = get_history(session['user_id'])
        
        return render_template(
            'history.html',
            user=user,
            researches=researches
        )
    
    # ── 9. VIEW RESEARCH ────────────────────────────────────
    @app.route('/research/<int:research_id>')
    def view_research(research_id):
        """View past research"""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        research = get_research_by_id(research_id)
        
        # Check ownership
        if not research or research.get('user_id') != session['user_id']:
            return "Research not found", 404
        
        return render_template(
            'results.html',
            results=research
        )
    
    # ── 10. USER AUTH ───────────────────────────────────────
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration"""
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            
            user_id = create_user(name, email, password)
            
            if user_id:
                session['user_id'] = user_id
                return redirect(url_for('index'))
            else:
                return render_template(
                    'register.html',
                    error="Email already exists"
                )
        
        return render_template('register.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login"""
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = get_user_by_email(email)
            
            if user and verify_password(password, user['password']):
                session['user_id'] = user['id']
                return redirect(url_for('index'))
            else:
                return render_template(
                    'login.html',
                    error="Invalid email or password"
                )
        
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        """User logout"""
        session.pop('user_id', None)
        return redirect(url_for('index'))
    
    # ── 11. PROGRESS POLLING ENDPOINT ───────────────────────
    @app.route('/progress/<task_id>', methods=['GET'])
    def get_progress(task_id):
        """Get detailed progress information"""
        status = get_task_status(task_id)
        
        # Add estimated time remaining
        if status["status"] == "processing":
            # You could track start time and estimate
            status["estimated_remaining"] = "2-5 minutes"
            status["progress"] = 50  # percentage
        elif status["status"] == "queued":
            status["estimated_remaining"] = "Starting soon..."
            status["progress"] = 0
        
        return jsonify(status)
    
    # ── 12. QUICK ANALYZE (SYNC) ────────────────────────────
    @app.route('/quick-analyze', methods=['POST'])
    def quick_analyze():
        """Quick analysis for simple ideas (returns immediately)"""
        try:
            data = request.get_json()
            idea = data.get('idea', '').strip()
            
            if not idea:
                return jsonify({"error": "No idea provided"}), 400
            
            # Use a simplified analysis that returns quickly
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
            return jsonify({"error": str(e)}), 500# ============================================================
# ROUTES.PY — Main Application Routes
# Updated for async analysis + PostgreSQL
# ============================================================

from flask import render_template, request, jsonify, session, redirect, url_for
import os
import time
from datetime import datetime

# Import core modules
from core.analyzer import analyze_idea
from core.tasks import queue_analysis, get_task_status
from database.db import (
    init_db, create_user, get_user_by_email, 
    get_user_by_id, verify_password,
    save_research, get_history, get_research_by_id
)
from config import Config


# ── 1. INITIALIZE ───────────────────────────────────────────
def init_routes(app):
    
    # Initialize database
    with app.app_context():
        init_db(app)
    
    # ── 2. HEALTH CHECK ─────────────────────────────────────
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for Railway"""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected"
        })
    
    # ── 3. MAIN PAGE ────────────────────────────────────────
    @app.route('/')
    def index():
        """Render main analysis page"""
        user = None
        if 'user_id' in session:
            user = get_user_by_id(session['user_id'])
        return render_template('index.html', user=user)
    
    # ── 4. ANALYZE IDEA (ASYNC) ─────────────────────────────
    @app.route('/analyze', methods=['POST'])
    def analyze():
        """Start analysis in background"""
        try:
            data = request.get_json()
            idea = data.get('idea', '').strip()
            
            if not idea:
                return jsonify({"error": "No idea provided"}), 400
            
            # Optional email for report
            recipient_email = data.get('email', '')
            user_id = session.get('user_id')
            
            # Queue the analysis (10-minute timeout)
            task_id = queue_analysis(idea, user_id, recipient_email)
            
            return jsonify({
                "status": "queued",
                "task_id": task_id,
                "message": "Analysis started. This may take 3-10 minutes.",
                "estimated_time": "5-10 minutes"
            })
            
        except Exception as e:
            print(f"❌ Error queueing analysis: {e}")
            return jsonify({"error": str(e)}), 500
    
    # ── 5. CHECK ANALYSIS STATUS ────────────────────────────
    @app.route('/analysis-status/<task_id>', methods=['GET'])
    def analysis_status(task_id):
        """Check if analysis is complete"""
        status = get_task_status(task_id)
        return jsonify(status)
    
    # ── 6. GET RESULTS ──────────────────────────────────────
    @app.route('/results/<task_id>', methods=['GET'])
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
    
    # ── 7. DOWNLOAD PDF ─────────────────────────────────────
    @app.route('/download/<task_id>', methods=['GET'])
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
                    download_name=f"MarketMind_Report_{task_id}.pdf"
                )
        
        return jsonify({"error": "PDF not found"}), 404
    
    # ── 8. HISTORY ──────────────────────────────────────────
    @app.route('/history')
    def history():
        """View research history"""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = get_user_by_id(session['user_id'])
        researches = get_history(session['user_id'])
        
        return render_template(
            'history.html',
            user=user,
            researches=researches
        )
    
    # ── 9. VIEW RESEARCH ────────────────────────────────────
    @app.route('/research/<int:research_id>')
    def view_research(research_id):
        """View past research"""
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        research = get_research_by_id(research_id)
        
        # Check ownership
        if not research or research.get('user_id') != session['user_id']:
            return "Research not found", 404
        
        return render_template(
            'results.html',
            results=research
        )
    
    # ── 10. USER AUTH ───────────────────────────────────────
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration"""
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            
            user_id = create_user(name, email, password)
            
            if user_id:
                session['user_id'] = user_id
                return redirect(url_for('index'))
            else:
                return render_template(
                    'register.html',
                    error="Email already exists"
                )
        
        return render_template('register.html')
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login"""
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = get_user_by_email(email)
            
            if user and verify_password(password, user['password']):
                session['user_id'] = user['id']
                return redirect(url_for('index'))
            else:
                return render_template(
                    'login.html',
                    error="Invalid email or password"
                )
        
        return render_template('login.html')
    
    @app.route('/logout')
    def logout():
        """User logout"""
        session.pop('user_id', None)
        return redirect(url_for('index'))
    
    # ── 11. PROGRESS POLLING ENDPOINT ───────────────────────
    @app.route('/progress/<task_id>', methods=['GET'])
    def get_progress(task_id):
        """Get detailed progress information"""
        status = get_task_status(task_id)
        
        # Add estimated time remaining
        if status["status"] == "processing":
            # You could track start time and estimate
            status["estimated_remaining"] = "2-5 minutes"
            status["progress"] = 50  # percentage
        elif status["status"] == "queued":
            status["estimated_remaining"] = "Starting soon..."
            status["progress"] = 0
        
        return jsonify(status)
    
    # ── 12. QUICK ANALYZE (SYNC) ────────────────────────────
    @app.route('/quick-analyze', methods=['POST'])
    def quick_analyze():
        """Quick analysis for simple ideas (returns immediately)"""
        try:
            data = request.get_json()
            idea = data.get('idea', '').strip()
            
            if not idea:
                return jsonify({"error": "No idea provided"}), 400
            
            # Use a simplified analysis that returns quickly
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
