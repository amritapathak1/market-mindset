"""
Database operations for the Stock Market Mindset.
Handles PostgreSQL connections and all data persistence.
"""

import os
import time
import logging
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
import json
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)

# Database configuration from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'market-mindset'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', '5')),
}

DB_POOL_MIN_CONN = int(os.getenv('DB_POOL_MIN_CONN', '1'))
DB_POOL_MAX_CONN = int(os.getenv('DB_POOL_MAX_CONN', '20'))
DB_RETRY_ATTEMPTS = int(os.getenv('DB_RETRY_ATTEMPTS', '3'))
DB_RETRY_BASE_DELAY = float(os.getenv('DB_RETRY_BASE_DELAY', '0.2'))
DB_CONNECT_RETRY_ATTEMPTS = int(os.getenv('DB_CONNECT_RETRY_ATTEMPTS', '2'))

TRANSIENT_SQLSTATES = {
    '40001',  # serialization_failure
    '40P01',  # deadlock_detected
    '53300',  # too_many_connections
    '57P01',  # admin_shutdown
    '57P02',  # crash_shutdown
    '57P03',  # cannot_connect_now
    '08000',  # connection_exception
    '08001',  # sqlclient_unable_to_establish_sqlconnection
    '08003',  # connection_does_not_exist
    '08006',  # connection_failure
}

_db_pool = None
_db_pool_lock = Lock()
_log_executor = None
_log_executor_lock = Lock()


def _is_transient_db_error(error):
    """Return True when an error is likely transient and safe to retry."""
    if isinstance(error, (psycopg2.OperationalError, psycopg2.InterfaceError)):
        return True

    if isinstance(error, psycopg2.pool.PoolError):
        return True

    sqlstate = getattr(error, 'pgcode', None)
    return sqlstate in TRANSIENT_SQLSTATES


def _run_db_write_with_retry(operation_name, operation):
    """Run a DB write operation with small retry/backoff for transient failures."""
    max_attempts = max(1, DB_RETRY_ATTEMPTS)

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except Exception as exc:
            is_retryable = _is_transient_db_error(exc)
            is_last_attempt = attempt >= max_attempts

            if (not is_retryable) or is_last_attempt:
                raise

            delay_seconds = DB_RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "Transient DB error in %s (attempt %s/%s): %s. Retrying in %.2fs",
                operation_name,
                attempt,
                max_attempts,
                exc.__class__.__name__,
                delay_seconds,
            )
            time.sleep(delay_seconds)


def get_db_pool():
    """Get or initialize PostgreSQL connection pool."""
    global _db_pool

    if _db_pool is None:
        with _db_pool_lock:
            if _db_pool is None:
                _db_pool = ThreadedConnectionPool(
                    minconn=DB_POOL_MIN_CONN,
                    maxconn=DB_POOL_MAX_CONN,
                    **DB_CONFIG,
                )
    return _db_pool


def reset_db_pool():
    """Reset the connection pool so new connections are created on next checkout."""
    global _db_pool

    with _db_pool_lock:
        old_pool = _db_pool
        _db_pool = None

        if old_pool is not None:
            try:
                old_pool.closeall()
            except Exception:
                logger.exception("Failed to close existing DB pool during reset")


def _get_log_executor():
    """Get or initialize the bounded thread pool for async log_event writes."""
    global _log_executor
    if _log_executor is None:
        with _log_executor_lock:
            if _log_executor is None:
                _log_executor = ThreadPoolExecutor(max_workers=2)
    return _log_executor


def _get_connection_with_reconnect():
    """Get a pooled connection, resetting the pool and retrying on transient checkout errors."""
    max_attempts = max(1, DB_CONNECT_RETRY_ATTEMPTS)

    for attempt in range(1, max_attempts + 1):
        pool = get_db_pool()
        try:
            return pool, pool.getconn()
        except Exception as exc:
            is_retryable = _is_transient_db_error(exc)
            is_last_attempt = attempt >= max_attempts

            if (not is_retryable) or is_last_attempt:
                raise

            delay_seconds = DB_RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "DB connection checkout failed (attempt %s/%s): %s. Resetting pool and retrying in %.2fs",
                attempt,
                max_attempts,
                exc.__class__.__name__,
                delay_seconds,
            )
            reset_db_pool()
            time.sleep(delay_seconds)


@contextmanager
def get_db_connection():
    """Context manager for pooled database connections."""
    conn = None
    pool = None
    close_conn = False
    try:
        pool, conn = _get_connection_with_reconnect()
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                close_conn = True

        if _is_transient_db_error(e):
            close_conn = True

        raise e
    finally:
        if pool and conn:
            try:
                pool.putconn(conn, close=close_conn)
            except Exception:
                logger.exception("Failed to return DB connection to pool")


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

def create_participant(session_id=None, experiment_key=None):
    """
    Create a new participant record.
    
    Args:
        session_id: Optional session identifier (None for anonymous participants)
        experiment_key: Optional experiment identifier (e1-e6)
        
    Returns:
        UUID: The participant_id
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO participants (session_id, experiment_key)
                VALUES (%s, %s)
                RETURNING participant_id
            """, (session_id, experiment_key))
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


def update_participant_withdrawal(participant_id, withdrawn=True):
    """Update participant data withdrawal status."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE participants
                SET withdrawn = %s, withdrawn_at = CURRENT_TIMESTAMP, last_active = CURRENT_TIMESTAMP
                WHERE participant_id = %s
            """, (withdrawn, participant_id))


# ============================================
# EVENT TRACKING
# ============================================

def log_event(participant_id, event_type, event_category, page_name=None,
              task_id=None, element_id=None, element_type=None, action=None,
              old_value=None, new_value=None, stock_ticker=None, metadata=None):
    """
    Log a user interaction event.

    Captures the event timestamp immediately, writes to the application log
    (file-backed, guaranteed), then submits the DB INSERT to a bounded
    ThreadPoolExecutor (max 2 workers) so the caller is never blocked and
    the connection pool is never starved.

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
    event_time = datetime.utcnow()

    logger.info("event: %s", json.dumps({
        'participant_id': str(participant_id) if participant_id else None,
        'event_type': event_type,
        'event_category': event_category,
        'page_name': page_name,
        'task_id': task_id,
        'element_id': element_id,
        'element_type': element_type,
        'action': action,
        'old_value': old_value,
        'new_value': new_value,
        'stock_ticker': stock_ticker,
        'metadata': metadata,
        'timestamp': event_time.isoformat(),
    }, default=str))

    def _write():
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO events (
                        participant_id, event_type, event_category, page_name,
                        task_id, element_id, element_type, action,
                        old_value, new_value, stock_ticker, metadata, timestamp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    participant_id, event_type, event_category, page_name,
                    task_id, element_id, element_type, action,
                    old_value, new_value, stock_ticker,
                    json.dumps(metadata) if metadata else None,
                    event_time,
                ))

    def _write_with_logging():
        try:
            _run_db_write_with_retry('log_event', _write)
        except Exception:
            logger.exception(
                "log_event DB write failed permanently for participant %s", participant_id
            )

    _get_log_executor().submit(_write_with_logging)


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

def save_demographics(
    participant_id,
    age_range,
    gender,
    gender_self_describe,
    hispanic_latino,
    race,
    race_other,
    education,
    employment,
    executive_shareholder,
    exchange_brokerage,
    income,
    experience,
):
    """Save participant demographics."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO demographics (
                    participant_id, age_range, gender, gender_self_describe,
                    hispanic_latino, race, race_other, education, employment,
                    executive_shareholder, exchange_brokerage, income, experience
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (participant_id) DO UPDATE
                SET age_range = EXCLUDED.age_range, gender = EXCLUDED.gender,
                    gender_self_describe = EXCLUDED.gender_self_describe,
                    hispanic_latino = EXCLUDED.hispanic_latino, race = EXCLUDED.race,
                    race_other = EXCLUDED.race_other, education = EXCLUDED.education,
                    employment = EXCLUDED.employment,
                    executive_shareholder = EXCLUDED.executive_shareholder,
                    exchange_brokerage = EXCLUDED.exchange_brokerage,
                    income = EXCLUDED.income, experience = EXCLUDED.experience
            """, (
                participant_id,
                age_range,
                gender,
                gender_self_describe,
                hispanic_latino,
                race,
                race_other,
                education,
                employment,
                executive_shareholder,
                exchange_brokerage,
                income,
                experience,
            ))


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
                       show_profit_loss=True, show_information=True,
                       time_spent_seconds=None, experiment_key=None):
    """Save task response data."""
    def _write():
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO task_responses (
                        participant_id, task_id, stock_1_ticker, stock_1_name, stock_1_investment,
                        stock_2_ticker, stock_2_name, stock_2_investment, total_investment,
                        remaining_amount, show_profit_loss, show_information, time_spent_seconds, experiment_key
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (participant_id, task_id) DO UPDATE
                    SET stock_1_ticker = EXCLUDED.stock_1_ticker,
                        stock_1_name = EXCLUDED.stock_1_name,
                        stock_1_investment = EXCLUDED.stock_1_investment,
                        stock_2_ticker = EXCLUDED.stock_2_ticker,
                        stock_2_name = EXCLUDED.stock_2_name,
                        stock_2_investment = EXCLUDED.stock_2_investment,
                        total_investment = EXCLUDED.total_investment,
                        remaining_amount = EXCLUDED.remaining_amount,
                        show_profit_loss = EXCLUDED.show_profit_loss,
                        show_information = EXCLUDED.show_information,
                        experiment_key = EXCLUDED.experiment_key,
                        time_spent_seconds = EXCLUDED.time_spent_seconds,
                        submitted_at = CURRENT_TIMESTAMP
                """, (
                    participant_id, task_id, stock_1_ticker, stock_1_name, stock_1_investment,
                    stock_2_ticker, stock_2_name, stock_2_investment, total_investment,
                    remaining_amount, show_profit_loss, show_information, time_spent_seconds, experiment_key
                ))

    _run_db_write_with_retry('save_task_response', _write)


def save_portfolio_investment(participant_id, task_id, stock_name, ticker,
                               invested_amount, return_percent, final_value, profit_loss):
    """Save individual investment to portfolio."""
    def _write():
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO portfolio (
                        participant_id, task_id, stock_name, ticker, invested_amount,
                        return_percent, final_value, profit_loss
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (participant_id, task_id, ticker) DO UPDATE
                    SET stock_name = EXCLUDED.stock_name,
                        invested_amount = EXCLUDED.invested_amount,
                        return_percent = EXCLUDED.return_percent,
                        final_value = EXCLUDED.final_value,
                        profit_loss = EXCLUDED.profit_loss,
                        created_at = CURRENT_TIMESTAMP
                """, (
                    participant_id, task_id, stock_name, ticker, invested_amount,
                    return_percent, final_value, profit_loss
                ))

    _run_db_write_with_retry('save_portfolio_investment', _write)


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

def save_confidence_risk(participant_id, confidence_rating, risk_rating, attention_check_response=None, completed_after_task=None):
    """Save confidence and risk ratings."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO confidence_risk (participant_id, confidence_rating, risk_rating, attention_check_response, completed_after_task)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (participant_id, completed_after_task) DO UPDATE
                SET confidence_rating = EXCLUDED.confidence_rating,
                    risk_rating = EXCLUDED.risk_rating,
                    attention_check_response = EXCLUDED.attention_check_response,
                    submitted_at = CURRENT_TIMESTAMP
            """, (participant_id, confidence_rating, risk_rating, attention_check_response, completed_after_task))


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
