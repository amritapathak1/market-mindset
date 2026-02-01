"""
File-based logging fallback for when database is not available.

This module provides the same interface as database.py but writes to
JSONL files instead of a PostgreSQL database.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

# Create logs directory
LOGS_DIR = Path(__file__).parent / 'logs'
LOGS_DIR.mkdir(exist_ok=True)


def _write_log_entry(participant_id, log_type, data):
    """Write a log entry to participant-specific file."""
    if not participant_id:
        return
    
    log_file = LOGS_DIR / f'participant_{participant_id}_{log_type}.jsonl'
    entry = {
        'timestamp': datetime.now().isoformat(),
        'data': data
    }
    
    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    except Exception as e:
        print(f"Error writing to log file: {e}")


def create_participant(**kwargs): 
    """Generate a UUID for file-based logging."""
    return str(uuid.uuid4())


def log_event(participant_id=None, event_type=None, event_category=None, 
              page_name=None, element_id=None, element_type=None, 
              action=None, task_id=None, stock_ticker=None, metadata=None, **kwargs):
    """Log event to file."""
    _write_log_entry(participant_id, 'events', {
        'event_type': event_type,
        'event_category': event_category,
        'page_name': page_name,
        'element_id': element_id,
        'element_type': element_type,
        'action': action,
        'task_id': task_id,
        'stock_ticker': stock_ticker,
        'metadata': metadata,
        **kwargs
    })


def save_demographics(participant_id=None, age=None, gender=None, 
                     education=None, experience=None, **kwargs):
    """Save demographics to file."""
    _write_log_entry(participant_id, 'demographics', {
        'age': age,
        'gender': gender,
        'education': education,
        'experience': experience
    })


def save_task_response(participant_id=None, task_id=None, stock_1_ticker=None,
                      stock_1_name=None, stock_1_investment=None,
                      stock_2_ticker=None, stock_2_name=None, stock_2_investment=None,
                      total_investment=None, remaining_amount=None, **kwargs):
    """Save task response to file."""
    _write_log_entry(participant_id, 'tasks', {
        'task_id': task_id,
        'stock_1_ticker': stock_1_ticker,
        'stock_1_name': stock_1_name,
        'stock_1_investment': stock_1_investment,
        'stock_2_ticker': stock_2_ticker,
        'stock_2_name': stock_2_name,
        'stock_2_investment': stock_2_investment,
        'total_investment': total_investment,
        'remaining_amount': remaining_amount
    })


def save_portfolio_investment(participant_id=None, task_id=None, stock_ticker=None,
                              amount_invested=None, return_percent=None, 
                              final_value=None, **kwargs):
    """Save portfolio investment to file."""
    _write_log_entry(participant_id, 'portfolio', {
        'task_id': task_id,
        'stock_ticker': stock_ticker,
        'amount_invested': amount_invested,
        'return_percent': return_percent,
        'final_value': final_value,
        **kwargs
    })


def save_confidence_risk(participant_id=None, confidence=None, risk_perception=None, completed_after_task=None, **kwargs):
    """Save confidence and risk perception to file."""
    _write_log_entry(participant_id, 'confidence_risk', {
        'confidence': confidence,
        'risk_perception': risk_perception,
        'completed_after_task': completed_after_task
    })


def save_feedback(participant_id=None, feedback_text=None, **kwargs):
    """Save feedback to file."""
    _write_log_entry(participant_id, 'feedback', {
        'feedback': feedback_text
    })


def update_participant_completion(participant_id=None, completed=None, **kwargs):
    """Log completion status to file."""
    _write_log_entry(participant_id, 'completion', {
        'completed': completed
    })
