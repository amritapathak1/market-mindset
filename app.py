"""
Stock Market Mindset - Main Application

A Dash-based research application for studying investment decision-making.
Participants make investment decisions across multiple scenarios with stock information.
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================
# DATABASE SETUP
# ============================================

DB_ENABLED = False
db_functions = {}

try:
    from database import (
        create_participant, log_event,
        save_demographics, save_task_response, save_portfolio_investment,
        save_confidence_risk, save_feedback, update_participant_completion,
        update_participant_withdrawal
    )
    # Test if database is actually usable
    import psycopg2
    
    # Check if DATABASE_URL is set or database credentials are provided
    if os.getenv('DATABASE_URL') or os.getenv('DB_NAME'):
        # Try to connect to verify database is available
        from database import get_db_connection
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1')
            DB_ENABLED = True
            print("✓ Database connection successful - using database for logging")
            
            db_functions = {
                'create_participant': create_participant,
                'log_event': log_event,
                'save_demographics': save_demographics,
                'save_task_response': save_task_response,
                'save_portfolio_investment': save_portfolio_investment,
                'save_confidence_risk': save_confidence_risk,
                'save_feedback': save_feedback,
                'update_participant_completion': update_participant_completion,
                'update_participant_withdrawal': update_participant_withdrawal
            }
        except Exception as conn_error:
            print(f"✗ Database connection failed: {conn_error}")
            DB_ENABLED = False
    else:
        print("✗ No database credentials configured")
        DB_ENABLED = False
        
except Exception as e:
    print(f"✗ Database not configured: {e}")
    DB_ENABLED = False

# ============================================
# FILE-BASED LOGGING (FALLBACK)
# ============================================

if not DB_ENABLED:
    from file_logger import (
        create_participant, log_event,
        save_demographics, save_task_response, save_portfolio_investment,
        save_confidence_risk, save_feedback, update_participant_completion,
        update_participant_withdrawal,
        LOGS_DIR
    )
    print(f"✓ File-based logging enabled. Logs directory: {LOGS_DIR.absolute()}")
    
    db_functions = {
        'create_participant': create_participant,
        'log_event': log_event,
        'save_demographics': save_demographics,
        'save_task_response': save_task_response,
        'save_portfolio_investment': save_portfolio_investment,
        'save_confidence_risk': save_confidence_risk,
        'save_feedback': save_feedback,
        'update_participant_completion': update_participant_completion,
        'update_participant_withdrawal': update_participant_withdrawal
    }

# ============================================
# APP INITIALIZATION
# ============================================

from config import INITIAL_AMOUNT, TUTORIAL_INITIAL_AMOUNT, PAGES, MODAL_SIZE, INFO_COSTS

# Initialize the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Stock Market Mindset"

# App layout
app.layout = dbc.Container([
    # Store components for state management (memory only - no persistence)
    dcc.Store(id='participant-id', data=None, storage_type='memory'),
    dcc.Store(id='current-page', data=PAGES['consent'], storage_type='memory'),
    dcc.Store(id='amount', data=TUTORIAL_INITIAL_AMOUNT, storage_type='memory'),
    dcc.Store(id='current-task', data=1, storage_type='memory'),  # Index into task-order (1-based)
    dcc.Store(id='task-order', data=None, storage_type='memory'),  # List of task IDs (main tasks only)
    dcc.Store(id='tutorial-completed', data=False, storage_type='memory'),  # Flag for tutorial completion
    dcc.Store(id='consent-given', data=False, storage_type='memory'),
    dcc.Store(id='demographics', data={}, storage_type='memory'),
    dcc.Store(id='task-responses', data={}, storage_type='memory'),
    dcc.Store(id='portfolio', data=[], storage_type='memory'),
    dcc.Store(id='confidence-risk', data={}, storage_type='memory'),
    dcc.Store(id='feedback', data='', storage_type='memory'),
    dcc.Store(id='modal-context', data={}, storage_type='memory'),
    dcc.Store(id='pending-info-request', data={}, storage_type='memory'),  # Store for pending info requests
    dcc.Store(id='info-cost-spent', data=0, storage_type='memory'),  # Track total spent on information
    dcc.Store(id='purchased-info', data=[], storage_type='memory'),  # Track purchased info for current task
    
    # Modal for cost confirmation
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Information Cost"), close_button=False),
        dbc.ModalBody(id='cost-modal-body'),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="cost-modal-cancel", color="secondary", className="me-2"),
            dbc.Button("OK", id="cost-modal-ok", color="primary")
        ]),
    ], id="cost-modal", size="md", is_open=False, backdrop="static", keyboard=False),
    
    # Modal for stock details
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id='modal-title'), close_button=False),
        dbc.ModalBody(id='modal-body'),
        dbc.ModalFooter(
            dbc.Button("Close", id="close-modal", className="ms-auto", n_clicks=0)
        ),
    ], id="stock-modal", size=MODAL_SIZE, is_open=False, backdrop="static"),
    
    # Main content area
    dcc.Loading(
        id="loading-page",
        type="default",
        children=html.Div(id='page-content', style={'minHeight': '100vh', 'paddingTop': '20px', 'paddingBottom': '40px'})
    )
], fluid=True)

# ============================================
# REGISTER CALLBACKS
# ============================================

from callbacks import register_callbacks
register_callbacks(app, DB_ENABLED, db_functions)

# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 8050))
    
    if debug_mode:
        app.run_server(debug=True, dev_tools_hot_reload=True, dev_tools_ui=True, port=port)
    else:
        print("⚠️  For production, run with: gunicorn -w 2 -b 0.0.0.0:8050 application:application")
        app.run_server(debug=False, port=port)
