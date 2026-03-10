# ============================================================
# CORE/ANALYZER.PY — Main Analysis Orchestrator
# Coordinates all analysis modules for a complete market report
# ============================================================

import time
import os
from datetime import datetime

# Import all analysis modules
from core.gemini_client import analyze_idea as ai_analyze
from core.market_researcher import get_market_data
from core.competitor_analyzer import get_competitors
from core.niche_identifier import identify_niches
from core.sales_predictor import predict_sales
from core.ecommerce_scraper import get_ecommerce_data
from core.report_generator import generate_pdf
from core.email_sender import send_report
from database.db import save_research


def analyze_idea(idea, user_id=None, recipient_email=None):
    """
    Complete market analysis pipeline
    Runs all analysis modules and returns combined results
    """
    start_time = time.time()
    print(f"🚀 Starting full analysis for: {idea[:50]}...")
    
    try:
        # ── STEP 1: MARKET RESEARCH (fastest) ────────────────
        print("📊 Researching market trends...")
        market_data = get_market_data(idea)
        
        # ── STEP 2: AI ANALYSIS ──────────────────────────────
        print("🧠 Getting AI insights...")
        ai_insights = ai_analyze(idea)
        
        # ── STEP 3: COMPETITOR ANALYSIS ──────────────────────
        print("🏆 Analyzing competitors...")
        competitors = get_competitors(idea)
        
        # ── STEP 4: NICHE IDENTIFICATION ─────────────────────
        print("💡 Identifying niche opportunities...")
        niches = identify_niches(idea, market_data)
        
        # ── STEP 5: SALES FORECAST ───────────────────────────
        print("💰 Predicting sales performance...")
        sales_forecast = predict_sales(market_data)
        
        # ── STEP 6: ECOMMERCE DATA (optional) ────────────────
        print("🛒 Fetching ecommerce data...")
        ecommerce_data = get_ecommerce_data(idea)
        
        # ── COMBINE ALL RESULTS ───────────────────────────────
        results = {
            "idea": idea,
            "ai_insights": ai_insights,
            "market_data": market_data,
            "competitors": competitors,
            "niches": niches,
            "sales_forecast": sales_forecast,
            "ecommerce": ecommerce_data,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # ── STEP 7: SAVE TO DATABASE ─────────────────────────
        if user_id:
            print("💾 Saving results to database...")
            research_id = save_research(results, user_id)
            results["id"] = research_id
        
        # ── STEP 8: GENERATE PDF REPORT ──────────────────────
        print("📄 Generating PDF report...")
        pdf_path = generate_pdf(idea, results)
        
        # ── STEP 9: SEND EMAIL (if requested) ─────────────────
        if recipient_email and pdf_path:
            print(f"📧 Sending report to {recipient_email}...")
            send_report(recipient_email, idea, pdf_path, results)
        
        # ── DONE! ────────────────────────────────────────────
        elapsed = time.time() - start_time
        print(f"✅ Analysis complete in {elapsed:.1f} seconds")
        
        return results, pdf_path
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Return partial results if available, otherwise error
        error_results = {
            "idea": idea,
            "error": str(e),
            "ai_insights": {
                "verdict": "ERROR",
                "summary": f"Analysis failed: {str(e)[:100]}",
                "recommendations": ["Please try again with a different idea"],
                "key_risks": ["System error occurred"]
            },
            "market_data": {
                "market_size": "N/A",
                "competition_level": "N/A",
                "profit_potential": "N/A",
                "trend_score": 0,
                "trends": {"dates": [], "values": []}
            },
            "competitors": [],
            "niches": [],
            "sales_forecast": {
                "months": [],
                "revenue": [],
                "total_year": 0,
                "growth_rate": "N/A",
                "summary": "Forecast unavailable due to error"
            },
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return error_results, None


def quick_analyze(idea):
    """
    Quick analysis for simple ideas (returns immediately)
    Uses only Gemini AI, no external data
    """
    print(f"⚡ Quick analyzing: {idea[:50]}...")
    
    try:
        ai_insights = ai_analyze(idea)
        
        return {
            "idea": idea,
            "ai_insights": ai_insights,
            "quick": True
        }
    except Exception as e:
        print(f"❌ Quick analysis failed: {e}")
        return {
            "idea": idea,
            "error": str(e),
            "ai_insights": {
                "verdict": "ERROR",
                "summary": f"Quick analysis failed: {str(e)[:100]}",
                "recommendations": ["Please try again"]
            }
        }
