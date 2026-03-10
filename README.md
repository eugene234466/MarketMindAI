# MarketMind AI

AI-powered business idea analysis tool built with Flask, Gemini AI, and PostgreSQL.

## Project Structure

```
marketmind_ai/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── routes.py            # All URL routes
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS, JS, images
├── core/
│   ├── analyze.py           # Main pipeline runner
│   ├── gemini_client.py     # Gemini AI integration
│   ├── market_researcher.py # Google Trends (pytrends)
│   ├── competitor_analyzer.py
│   ├── ecommerce_scraper.py
│   ├── niche_identifier.py
│   ├── sales_predictor.py
│   ├── report_generator.py  # PDF generation
│   └── email_sender.py
├── database/
│   └── db.py                # PostgreSQL (psycopg2)
├── config.py
├── main.py                  # Entry point
├── requirements.txt
├── Procfile                 # Railway/Heroku
├── railway.toml
└── .env.example
```

## Local Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
python main.py
```

## Railway Deployment

1. Push to GitHub
2. Connect repo in Railway dashboard
3. Add PostgreSQL plugin (DATABASE_URL auto-injected)
4. Add environment variables from .env
5. Deploy
