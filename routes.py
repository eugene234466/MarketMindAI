# ============================================================
# ROUTES.PY — Main Application Routes
# ============================================================

from flask import render_template, request, jsonify, session, redirect, url_for, flash, Blueprint
import os
import time
from datetime import datetime

# Create blueprint
main = Blueprint('main', __name__)

# ── 1. ROOT REDIRECT ───────────────────────────────────────
@main.route('/')
def root():
    """Root URL - redirect based on login status"""
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    return redirect(url_for('main.intro'))

# ── 2. INTRO PAGE ──────────────────────────────────────────
@main.route('/intro')
def intro():
    """Intro page for non-logged-in users"""
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    return render_template('intro.html')

# ── 3. MAIN DASHBOARD ──────────────────────────────────────
@main.route('/dashboard')
def index():
    """Main analysis page for logged-in users"""
    if 'user_id' not in session:
        return redirect(url_for('main.intro'))
    
    user = get_user_by_id(session['user_id'])
    return render_template('index.html', user=user)

# ... rest of your routes