"""
Database operations for the Stock Market Mindset.
Handles PostgreSQL connections and all data persistence.
"""

import os
import psycopg2
import psycopg2.extras
from datetime import datetime
import json
from contextlib import contextmanager

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'market-mindset'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
}


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


def init_database():
    """Initialize database tables from schema.sql"""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r') as f:
        schema = f.read()
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema)


# ============================================
# PARTICIPANT MANAGEMENT
# ============================================

def create_participant(session_id=None, ip_address=None, user_agent=None):
    """
    Create a new participant record.
    
    Args:
        session_id: Optional session identifier (None for anonymous participants)
        ip_address: Client IP address
        user_agent: Browser user agent string
        
    Returns:
        UUID: The participant_id
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO participants (session_id, ip_address, user_agent)
                VALUES (%s, %s, %s)
                RETURNING participant_id
            """, (session_id, ip_address, user_agent))
            return cur.fetchone()[0]


def get_participant_by_session(session_id):
    """Retrieve participant by session ID."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM participants WHERE session_id = %s
            """, (session_id,))
            return cur.fetchone()


def update_participant_completion(participant_id):
    """Mark participant as completed."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE participants 
                SET completed = TRUE, completed_at = CURRENT_TIMESTAMP
                WHERE participant_id = %s
            """, (participant_id,))


# ============================================
# EVENT TRACKING
# ============================================

def log_event(participant_id, event_type, event_category, page_name=None, 
              task_id=None, element_id=None, element_type=None, action=None,
              old_value=None, new_value=None, stock_ticker=None, metadata=None):
    """
    Log a user interaction event.
    
    Args:
        participant_id: UUID of participant
        event_type: Type of event (e.g., 'button_click', 'modal_open', 'page_view')
        event_category: Category ('navigation', 'interaction', 'input', 'error')
        page_name: Current page
        task_id: Task number if applicable
        element_id: ID of element interacted with
        element_type: Type of element ('button', 'modal', 'input', etc.)
        action: Action performed ('click', 'open', 'close', 'change', etc.)
        old_value: Previous value (for inputs)
        new_value: New value (for inputs)
        stock_ticker: Stock ticker if applicable
        metadata: Additional data as dict
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO events (
                    participant_id, event_type, event_category, page_name,
                    task_id, element_id, element_type, action,
                    old_value, new_value, stock_ticker, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                participant_id, event_type, event_category, page_name,
                task_id, element_id, element_type, action,
                old_value, new_value, stock_ticker,
                json.dumps(metadata) if metadata else None
            ))


# ============================================
# PAGE VISIT TRACKING
# ============================================

def start_page_visit(participant_id, page_name, task_id=None):
    """Record when a user enters a page."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO page_visits (participant_id, page_name, task_id)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (participant_id, page_name, task_id))
            return cur.fetchone()[0]


def end_page_visit(visit_id, duration_seconds=None):
    """Record when a user exits a page."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if duration_seconds is not None:
                cur.execute("""
                    UPDATE page_visits
                    SET exited_at = CURRENT_TIMESTAMP, duration_seconds = %s
                    WHERE id = %s
                """, (duration_seconds, visit_id))
            else:
                cur.execute("""
                    UPDATE page_visits
                    SET exited_at = CURRENT_TIMESTAMP,
                        duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - entered_at))
                    WHERE id = %s
                """, (visit_id,))


# ============================================
# DEMOGRAPHICS
# ============================================

def save_demographics(participant_id, age, gender, education, experience):
    """Save participant demographics."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO demographics (participant_id, age, gender, education, experience)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (participant_id) DO UPDATE
                SET age = EXCLUDED.age, gender = EXCLUDED.gender,
                    education = EXCLUDED.education, experience = EXCLUDED.experience
            """, (participant_id, age, gender, education, experience))


def get_demographics(participant_id):
    """Retrieve participant demographics."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM demographics WHERE participant_id = %s
            """, (participant_id,))
            return cur.fetchone()


# ============================================
# TASK RESPONSES
# ============================================

def save_task_response(participant_id, task_id, stock_1_ticker, stock_1_name, 
                       stock_1_investment, stock_2_ticker, stock_2_name,
                       stock_2_investment, total_investment, remaining_amount,
                       time_spent_seconds=None):
    """Save task response data."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO task_responses (
                    participant_id, task_id, stock_1_ticker, stock_1_name, stock_1_investment,
                    stock_2_ticker, stock_2_name, stock_2_investment, total_investment,
                    remaining_amount, time_spent_seconds
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                participant_id, task_id, stock_1_ticker, stock_1_name, stock_1_investment,
                stock_2_ticker, stock_2_name, stock_2_investment, total_investment,
                remaining_amount, time_spent_seconds
            ))


def save_portfolio_investment(participant_id, task_id, stock_name, ticker,
                               invested_amount, return_percent, final_value, profit_loss):
    """Save individual investment to portfolio."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO portfolio (
                    participant_id, task_id, stock_name, ticker, invested_amount,
                    return_percent, final_value, profit_loss
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                participant_id, task_id, stock_name, ticker, invested_amount,
                return_percent, final_value, profit_loss
            ))


def get_portfolio(participant_id):
    """Retrieve all portfolio investments for a participant."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM portfolio 
                WHERE participant_id = %s 
                ORDER BY task_id, id
            """, (participant_id,))
            return cur.fetchall()


# ============================================
# CONFIDENCE & RISK
# ============================================

def save_confidence_risk(participant_id, confidence_rating, risk_rating, completed_after_task=None):
    """Save confidence and risk ratings."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO confidence_risk (participant_id, confidence_rating, risk_rating, completed_after_task)
                VALUES (%s, %s, %s, %s)
            """, (participant_id, confidence_rating, risk_rating, completed_after_task))


def get_confidence_risk(participant_id):
    """Retrieve confidence and risk ratings."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM confidence_risk WHERE participant_id = %s
            """, (participant_id,))
            return cur.fetchone()


# ============================================
# FEEDBACK
# ============================================

def save_feedback(participant_id, feedback_text):
    """Save participant feedback."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO feedback (participant_id, feedback_text)
                VALUES (%s, %s)
                ON CONFLICT (participant_id) DO UPDATE
                SET feedback_text = EXCLUDED.feedback_text
            """, (participant_id, feedback_text))


# ============================================
# ANALYTICS & REPORTING
# ============================================

def get_participant_summary(participant_id):
    """Get complete summary of participant data."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM participant_summary WHERE participant_id = %s
            """, (participant_id,))
            return cur.fetchone()


def get_all_events_for_participant(participant_id):
    """Retrieve all events for a participant."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM events 
                WHERE participant_id = %s 
                ORDER BY timestamp
            """, (participant_id,))
            return cur.fetchall()


def get_study_statistics():
    """Get overall study statistics."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT participant_id) as total_participants,
                    COUNT(DISTINCT CASE WHEN completed = TRUE THEN participant_id END) as completed_participants,
                    AVG(CASE WHEN completed = TRUE THEN 
                        EXTRACT(EPOCH FROM (completed_at - created_at))/60 
                    END) as avg_completion_time_minutes,
                    COUNT(*) as total_events
                FROM participants, events
            """)
            return cur.fetchone()
