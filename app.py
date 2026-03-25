"""
Stock Market Mindset - Main Application

A Dash-based research application for studying investment decision-making.
Participants make investment decisions across multiple scenarios with stock information.
"""

import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import os
import logging
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

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
            logger.info("Database connection successful - using database for logging")
            
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
        except Exception:
            logger.exception("Database connection failed; using file-based logging")
            DB_ENABLED = False
    else:
        logger.warning("No database credentials configured; using file-based logging")
        DB_ENABLED = False
        
except Exception:
    logger.exception("Database module initialization failed; using file-based logging")
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
    logger.info("File-based logging enabled. Logs directory: %s", LOGS_DIR.absolute())
    
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
from components import create_slider_with_labels

# Initialize the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Stock Market Mindset"

# Add clientside callback to scroll to top when page changes
app.clientside_callback(
    """
    function(page) {
        window.scrollTo({top: 0, behavior: 'instant'});
        return window.dash_clientside.no_update;
    }
    """,
    Output('page-content', 'style', allow_duplicate=True),
    Input('current-page', 'data'),
    prevent_initial_call=True
)

# App layout
app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),

    # Store components for state management (memory only - no persistence)
    dcc.Store(id='participant-id', data=None, storage_type='memory'),
    dcc.Store(id='experiment-key', data=None, storage_type='memory'),
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
    dcc.Store(id='pending-result', data=None, storage_type='memory'),  # Store result data shown after CR modal
    
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
    
    # Confidence/Risk modal (shown after each task submission)
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Quick Check-In"), close_button=False),
        dbc.ModalBody([
            html.P(id='cr-modal-message', className="mb-3 text-muted"),
            html.H6("How confident are you in the investment decisions you've made so far?", className="mt-3 mb-2"),
            create_slider_with_labels('cr-modal-confidence', 1, 7, 4, 1, 'Not at all confident', 'Extremely confident'),
            html.H6("How would you rate the overall risk of your investment strategy?", className="mt-4 mb-2"),
            create_slider_with_labels('cr-modal-risk', 1, 7, 4, 1, 'Very low risk', 'Very high risk'),
            html.Div([
                html.H6(id='cr-modal-attention-prompt', className="mt-4 mb-2", style={'color': '#0066cc'}),
                create_slider_with_labels('cr-modal-attention', 1, 7, 4, 1, '1', '7'),
            ], id='cr-modal-attention-section', style={'display': 'none'}),
        ]),
        dbc.ModalFooter(
            dbc.Button("Continue", id="cr-modal-submit", color="primary")
        ),
    ], id="cr-modal", size="lg", is_open=False, centered=True, backdrop="static", keyboard=False),
    
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
        logger.warning("For production, run with Gunicorn via systemd service")
        app.run_server(debug=False, port=port)
