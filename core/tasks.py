# ============================================================
# CORE/TASKS.PY — Background Task Processor
# Handles async analysis jobs
# ============================================================

import threading
import time
import json
from queue import Queue
from datetime import datetime

# Task storage
task_queue = Queue()
task_status = {}
task_results = {}
task_pdfs = {}

# Start time tracking for progress estimates
task_start_time = {}

def worker():
    """Background worker that processes analysis tasks"""
    print("🧠 Background worker started")
    
    while True:
        try:
            # Get task from queue
            task_id, idea, user_id, recipient_email = task_queue.get()
            
            # Update status
            task_status[task_id] = "processing"
            task_start_time[task_id] = time.time()
            
            print(f"📊 Processing task {task_id}: {idea[:50]}...")
            
            # Run the analysis
            from core.analyzer import analyze_idea
            results, pdf_path = analyze_idea(idea, user_id, recipient_email)
            
            # Store results
            task_results[task_id] = results
            task_pdfs[task_id] = pdf_path
            task_status[task_id] = "completed"
            
            elapsed = time.time() - task_start_time[task_id]
            print(f"✅ Task {task_id} completed in {elapsed:.1f}s")
            
        except Exception as e:
            print(f"❌ Task failed: {e}")
            task_status[task_id] = f"failed: {str(e)}"
            task_results[task_id] = {"error": str(e)}
        
        finally:
            task_queue.task_done()
            # Clean up old tasks (keep last 100)
            if len(task_status) > 100:
                oldest = min(task_start_time.keys(), key=lambda k: task_start_time[k])
                del task_status[oldest]
                del task_results[oldest]
                del task_pdfs[oldest]
                del task_start_time[oldest]

def start_worker():
    """Start the background worker thread"""
    worker_thread = threading.Thread(target=worker, daemon=True)
    worker_thread.start()
    return worker_thread

def queue_analysis(idea, user_id=None, recipient_email=None):
    """Queue an analysis task and return task ID"""
    task_id = f"task_{int(time.time())}_{hash(idea) % 10000}"
    
    task_queue.put((task_id, idea, user_id, recipient_email))
    task_status[task_id] = "queued"
    task_start_time[task_id] = time.time()
    
    print(f"📥 Queued task {task_id}: {idea[:50]}...")
    return task_id

def get_task_status(task_id):
    """Get task status and results if completed"""
    status = task_status.get(task_id, "not_found")
    
    result = {
        "status": status,
        "task_id": task_id
    }
    
    if status == "processing":
        # Calculate progress estimate
        elapsed = time.time() - task_start_time.get(task_id, time.time())
        if elapsed < 60:
            result["message"] = "AI is analysing your idea..."
            result["progress"] = 20
        elif elapsed < 120:
            result["message"] = "Researching market trends..."
            result["progress"] = 40
        elif elapsed < 180:
            result["message"] = "Analysing competitors..."
            result["progress"] = 60
        elif elapsed < 240:
            result["message"] = "Predicting sales performance..."
            result["progress"] = 80
        else:
            result["message"] = "Generating your report..."
            result["progress"] = 90
        
        remaining = max(0, 300 - elapsed)
        if remaining > 60:
            result["estimated_remaining"] = f"~{int(remaining/60)} minutes"
        else:
            result["estimated_remaining"] = f"~{int(remaining)} seconds"
    
    elif status == "queued":
        result["message"] = "Waiting in queue..."
        result["progress"] = 5
        result["estimated_remaining"] = "Starting soon..."
    
    elif status == "completed":
        result["results"] = task_results.get(task_id)
        result["pdf_path"] = task_pdfs.get(task_id)
        result["progress"] = 100
    
    elif status.startswith("failed"):
        result["error"] = status
        result["progress"] = 0
    
    return result