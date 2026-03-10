# ============================================================
# CORE/ANALYZER.PY — Main Orchestrator
# Coordinates all analysis modules
# ============================================================

from core.gemini_client import analyze_idea as ai_analyze
from core.market_researcher import get_market_data
from core.competitor_analyzer import get_competitors
from core.niche_identifier import identify_niches
from core.sales_predictor import predict_sales
from core.ecommerce_scraper import get_ecommerce_data
from core.report_generator import generate_pdf
from core.email_sender import send_report
import time

def analyze_idea(idea, user_id=None, recipient_email=None):
    """Complete market analysis pipeline"""
    start_time = time.time()
    print(f"🚀 Starting analysis for: {idea}")
    
    # Step 1: Market Research (fastest)
    market_data = get_market_data(idea)
    
    # Step 2: AI Analysis
    ai_insights = ai_analyze(idea)
    
    # Step 3: Competitor Analysis (run in parallel)
    competitors = get_competitors(idea)
    
    # Step 4: Niche Identification
    niches = identify_niches(idea, market_data)
    
    # Step 5: Sales Forecast
    sales_forecast = predict_sales(market_data)
    
    # Step 6: Ecommerce Data (optional)
    ecommerce_data = get_ecommerce_data(idea)
    
    # Combine all results
    results = {
        "idea": idea,
        "ai_insights": ai_insights,
        "market_data": market_data,
        "competitors": competitors,
        "niches": niches,
        "sales_forecast": sales_forecast,
        "ecommerce": ecommerce_data
    }
    
    # Step 7: Generate PDF
    pdf_path = generate_pdf(idea, results)
    
    # Step 8: Send Email (if recipient provided)
    if recipient_email and pdf_path:
        send_report(recipient_email, idea, pdf_path, results)
    
    elapsed = time.time() - start_time
    print(f"✅ Analysis complete in {elapsed:.1f} seconds")
    
    return results, pdf_path