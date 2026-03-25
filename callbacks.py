"""
Callback functions for the Stock Market Mindset app.

This module contains all Dash callback functions that handle:
- Participant initialization
- Page navigation
- UI interactions
- Data collection and validation
- Modal displays
"""

import dash
from dash import html, ctx, Input, Output, State, ALL
import dash_bootstrap_components as dbc
import logging

from config import (
    PAGES,
    NUM_TASKS,
    NUM_TUTORIAL_TASKS,
    CONFIDENCE_RISK_CHECKPOINTS,
    ATTENTION_CHECK_TASKS,
    get_experiment_config,
    get_experiment_key_from_path,
)
from utils import (
    validate_investment, validate_total_investment, get_task_data_safe,
    validate_demographics, validate_page_access
)
from components import create_centered_card, create_error_alert
from pages import (
    consent_page, demographics_page, tutorial_page, task_page, confidence_risk_page,
    feedback_page, debrief_page, thank_you_page
)

# Import INFO_COSTS and INITIAL_AMOUNT for cost confirmation and amount display
from config import INFO_COSTS, INITIAL_AMOUNT

logger = logging.getLogger(__name__)


def register_callbacks(app, db_enabled, db_functions):
    """
    Register all callbacks with the app.
    
    Args:
        app: Dash application instance
        db_enabled: Boolean indicating if database is available
        db_functions: Dict of database functions (create_participant, log_event, save_*, etc.)
    """
    
    # Unpack database functions
    create_participant = db_functions['create_participant']
    log_event = db_functions['log_event']
    save_demographics = db_functions['save_demographics']
    save_task_response = db_functions['save_task_response']
    save_portfolio_investment = db_functions['save_portfolio_investment']
    save_confidence_risk = db_functions['save_confidence_risk']
    save_feedback = db_functions['save_feedback']
    update_participant_completion = db_functions['update_participant_completion']
    update_participant_withdrawal = db_functions['update_participant_withdrawal']
    
    DB_ENABLED = db_enabled
    
    # ============================================
    # INITIALIZATION CALLBACK
    # ============================================

    @app.callback(
        Output('experiment-key', 'data'),
        Input('url', 'pathname')
    )
    def resolve_experiment_key(pathname):
        """Resolve experiment key from opaque URL slug."""
        experiment_key = get_experiment_key_from_path(pathname)
        return experiment_key
    
    @app.callback(
        Output('participant-id', 'data'),
        Output('task-order', 'data'),
        Input('participant-id', 'data'),
        Input('experiment-key', 'data')
    )
    def initialize_participant(participant_id, experiment_key):
        """Create new participant on first load."""
        if not experiment_key:
            return participant_id or None, dash.no_update

        if participant_id is None:
            try:
                if DB_ENABLED:
                    # Create new participant in database (no session tracking, no IP/user-agent capture)
                    new_participant_id = create_participant(
                        session_id=None,  # Not using sessions
                        experiment_key=experiment_key,
                    )
                else:
                    # Create participant ID for file-based logging
                    new_participant_id = create_participant(experiment_key=experiment_key)
                
                # Log initial event
                if new_participant_id:
                    log_event(
                        participant_id=new_participant_id,
                        event_type='session_start',
                        event_category='navigation',
                        page_name='consent',
                        action='load',
                        metadata={'experiment_key': experiment_key}
                    )
                
                # Create randomized task order for main tasks only
                import random
                task_order = list(range(1, NUM_TASKS + 1))
                random.shuffle(task_order)
                
                return str(new_participant_id), task_order
            except Exception:
                logger.exception("Error creating participant")
                return None, None
        return participant_id or None, dash.no_update
    
    
    # ============================================
    # PAGE NAVIGATION
    # ============================================
    
    @app.callback(
        Output('page-content', 'children'),
        Output('stock-modal', 'is_open', allow_duplicate=True),
        Output('current-page', 'data', allow_duplicate=True),
        Output('pending-info-request', 'data', allow_duplicate=True),
        Input('current-page', 'data'),
        Input('experiment-key', 'data'),
        State('current-task', 'data'),
        State('task-order', 'data'),
        State('amount', 'data'),
        State('consent-given', 'data'),
        State('demographics', 'data'),
        State('confidence-risk', 'data'),
        State('task-responses', 'data'),
        State('portfolio', 'data'),
        State('info-cost-spent', 'data'),
        prevent_initial_call='initial_duplicate'
    )
    def display_page(page, experiment_key, current_task, task_order, amount, consent_given, demographics, confidence_risk, task_responses, portfolio, info_spent):
        """Display the appropriate page based on current page state with flow validation."""
        if not experiment_key:
            error_content = create_centered_card([
                create_error_alert(
                    "Invalid Study Link",
                    "This study URL is not active or is incomplete.",
                    "Please use the exact study link provided by the researcher."
                )
            ])
            return error_content, False, dash.no_update, {}

        experiment_config = get_experiment_config(experiment_key)
        if not experiment_config:
            error_content = create_centered_card([
                create_error_alert(
                    "Invalid Study Link",
                    "This study URL does not map to a configured experiment.",
                    "Please use the exact study link provided by the researcher."
                )
            ])
            return error_content, False, dash.no_update, {}

        # Validate page access
        demographics_completed = bool(demographics and demographics.get('age_range'))
        confidence_risk_completed = bool(confidence_risk and confidence_risk.get('confidence'))
        
        is_allowed, redirect_page, error_msg = validate_page_access(
            page, consent_given, demographics_completed, current_task, confidence_risk_completed
        )
        
        # If access denied, redirect and show error
        if not is_allowed:
            error_content = create_centered_card([
                create_error_alert("Access Denied", error_msg, "You will be redirected to the appropriate page."),
                html.Script("setTimeout(function(){ window.location.reload(); }, 2000);")
            ])
            return error_content, False, redirect_page, {}
        
        # Always close modal and clear pending requests when changing pages
        if page == PAGES['consent']:
            return consent_page(), False, dash.no_update, {}
        elif page == PAGES['demographics']:
            return demographics_page(), False, dash.no_update, {}
        elif page == PAGES['tutorial_1']:
            return tutorial_page(1, amount, experiment_key), False, dash.no_update, {}
        elif page == PAGES['tutorial_2']:
            return tutorial_page(2, amount, experiment_key), False, dash.no_update, {}
        elif page == PAGES['task']:
            # Use the randomized task order
            actual_task_id = task_order[current_task - 1] if task_order else current_task
            return task_page(actual_task_id, amount, sequential_task_num=current_task, experiment_key=experiment_key), False, dash.no_update, {}
        elif page == PAGES['confidence_risk']:
            # Calculate number of completed main tasks (excluding tutorials)
            completed_main_tasks = max(0, current_task - 1)
            return confidence_risk_page(completed_tasks=completed_main_tasks), False, dash.no_update, {}
        elif page == PAGES['feedback']:
            return feedback_page(
                amount,
                portfolio or [],
                info_spent or 0,
                task_order=task_order or [],
                task_responses=task_responses or {}
            ), False, dash.no_update, {}
        elif page == PAGES['debrief']:
            return debrief_page(amount, portfolio or [], info_spent or 0), False, dash.no_update, {}
        elif page == PAGES['thank_you']:
            return thank_you_page(), False, dash.no_update, {}
        return html.Div("Page not found"), False, dash.no_update, {}
    
    
    # ============================================
    # UI INTERACTIONS
    # ============================================
    
    @app.callback(
        Output('consent-submit', 'disabled'),
        Input('consent-checkbox', 'value'),
        State('participant-id', 'data')
    )
    def enable_consent_submit(checked, participant_id):
        """Enable consent submit button when checkbox is checked."""
        if participant_id:
            try:
                log_event(
                    participant_id=participant_id,
                    event_type='checkbox_change',
                    event_category='interaction',
                    page_name='consent',
                    element_id='consent-checkbox',
                    element_type='checkbox',
                    action='change',
                    new_value=str(checked)
                )
            except Exception:
                logger.exception("Error logging event")
        
        return not checked
    
    
    @app.callback(
        Output('current-page', 'data', allow_duplicate=True),
        Output('consent-given', 'data'),
        Input('consent-submit', 'n_clicks'),
        State('consent-checkbox', 'value'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def submit_consent(n_clicks, consent_value, participant_id):
        """Handle consent form submission."""
        if n_clicks and consent_value:
            if participant_id:
                try:
                    log_event(
                        participant_id=participant_id,
                        event_type='button_click',
                        event_category='interaction',
                        page_name='consent',
                        element_id='consent-submit',
                        element_type='button',
                        action='click',
                        metadata={'consent_given': True}
                    )
                    log_event(
                        participant_id=participant_id,
                        event_type='page_navigation',
                        event_category='navigation',
                        page_name='demographics',
                        action='navigate'
                    )
                except Exception:
                    logger.exception("Error logging event")
            
            return PAGES['demographics'], True
        return dash.no_update, dash.no_update
    
    
    @app.callback(
        Output('gender-self-describe', 'style'),
        Input('gender-select', 'value')
    )
    def toggle_gender_self_describe(gender):
        """Show/hide the gender self-describe field based on selection."""
        if gender == 'prefer-to-self-describe':
            return {'display': 'block'}
        return {'display': 'none'}
    
    
    @app.callback(
        Output('race-other', 'style'),
        Input('race-select', 'value')
    )
    def toggle_race_other(race):
        """Show/hide the race other field based on selection."""
        if race == 'other':
            return {'display': 'block'}
        return {'display': 'none'}
    
    
    # ============================================
    # DATA COLLECTION
    # ============================================
    
    @app.callback(
        Output('current-page', 'data', allow_duplicate=True),
        Output('demographics', 'data'),
        Output('demographics-error', 'children'),
        Input('demographics-submit', 'n_clicks'),
        State('age-select', 'value'),
        State('gender-select', 'value'),
        State('gender-self-describe', 'value'),
        State('hispanic-latino-select', 'value'),
        State('race-select', 'value'),
        State('race-other', 'value'),
        State('education-select', 'value'),
        State('employment-select', 'value'),
        State('executive-shareholder-select', 'value'),
        State('exchange-brokerage-select', 'value'),
        State('income-select', 'value'),
        State('experience-select', 'value'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def submit_demographics(
        n_clicks,
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
        participant_id,
    ):
        """Handle demographics form submission with validation."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update
        
        # Validate
        is_valid, error, demographics_data = validate_demographics(
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
        )
        
        if not is_valid:
            if participant_id:
                try:
                    log_event(
                        participant_id=participant_id,
                        event_type='validation_error',
                        event_category='error',
                        page_name='demographics',
                        element_id='demographics-submit',
                        action='submit',
                        metadata={'error': error}
                    )
                except Exception:
                    logger.exception("Error logging event")
            return dash.no_update, dash.no_update, error
        
        # Save
        if participant_id:
            try:
                save_demographics(
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
                )
                log_event(
                    participant_id=participant_id,
                    event_type='demographics_submit',
                    event_category='interaction',
                    page_name='demographics',
                    element_id='demographics-submit',
                    element_type='button',
                    action='submit',
                    metadata=demographics_data
                )
                log_event(
                    participant_id=participant_id,
                    event_type='page_navigation',
                    event_category='navigation',
                    page_name='tutorial_1',
                    action='navigate'
                )
            except Exception:
                logger.exception("Error saving demographics")
        
        return PAGES['tutorial_1'], demographics_data, ""
    
    
    # ============================================
    # COST CONFIRMATION CALLBACKS
    # ============================================
    
    @app.callback(
        Output('cost-modal', 'is_open'),
        Output('cost-modal-body', 'children'),
        Output('pending-info-request', 'data'),
        Input({'type': 'purchase-info', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        Input({'type': 'show-more', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        Input({'type': 'show-week', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        Input({'type': 'show-month', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        Input('cost-modal-cancel', 'n_clicks'),
        State('pending-info-request', 'data'),
        State('current-task', 'data'),
        State('participant-id', 'data'),
        State('purchased-info', 'data'),
        State('experiment-key', 'data'),
        prevent_initial_call=True
    )
    def handle_cost_confirmation(purchase_info_clicks, show_more_clicks, show_week_clicks, show_month_clicks, 
                                  cancel_clicks, pending_request, current_task, participant_id, purchased_info, experiment_key):
        """Handle cost confirmation modal for information requests."""
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
        
        triggered_id = ctx.triggered[0]['prop_id']
        button_id = ctx.triggered_id
        
        # CRITICAL: Check that something was actually clicked (not just component rendered)
        if not button_id or (isinstance(button_id, dict) and not any([
            purchase_info_clicks and any(c for c in purchase_info_clicks if c),
            show_more_clicks and any(c for c in show_more_clicks if c),
            show_week_clicks and any(c for c in show_week_clicks if c),
            show_month_clicks and any(c for c in show_month_clicks if c)
        ])) and 'cost-modal' not in triggered_id:
            return dash.no_update, dash.no_update, dash.no_update
        
        # Handle cancel button
        if 'cost-modal-cancel' in triggered_id:
            if participant_id and pending_request:
                try:
                    log_event(
                        participant_id=participant_id,
                        event_type='cost_confirmation_cancel',
                        event_category='interaction',
                        page_name='task',
                        task_id=current_task,
                        element_id=pending_request.get('element_id'),
                        element_type='button',
                        action='cancel',
                        stock_ticker=pending_request.get('stock_ticker'),
                        metadata={
                            'cost': pending_request.get('cost'),
                            'info_type': pending_request.get('info_type'),
                            'stock_name': pending_request.get('stock_name')
                        }
                    )
                except Exception:
                    logger.exception("Error logging event")
            return False, "", {}
        
        # Handle information request buttons
        if isinstance(button_id, dict):
            info_type = button_id.get('type')
            task_id = button_id.get('task')
            stock_index = button_id.get('stock')
            
            # Handle purchase-info button - bundle purchase
            if info_type == 'purchase-info':
                # Get task data to retrieve stock info
                task_data, error = get_task_data_safe(task_id, experiment_key)
                if error:
                    return False, "", {}
                
                stock = task_data['stocks'][stock_index]
                
                # Get bundle cost from stock data
                cost = stock.get('info_costs', {}).get('purchase_bundle', 0)
                
                # Check if bundle has already been purchased for this stock
                info_identifier = f'bundle-{stock_index}'
                already_purchased = info_identifier in (purchased_info or [])
                
                # If already purchased, treat as free (shouldn't happen since button should be disabled)
                if already_purchased:
                    cost = 0
                
                # Log the initial request
                if participant_id:
                    try:
                        log_event(
                            participant_id=participant_id,
                            event_type='info_request',
                            event_category='interaction',
                            page_name='task',
                            task_id=current_task,
                            element_id=f'purchase-info-{stock_index}',
                            element_type='button',
                            action='click',
                            stock_ticker=stock['ticker'],
                            metadata={
                                'cost': cost,
                                'info_type': 'purchase-info',
                                'stock_name': stock['name'],
                                'stock_index': stock_index
                            }
                        )
                    except Exception:
                        logger.exception("Error logging event")
                
                # Create pending request
                pending = {
                    'info_type': info_type,
                    'task_id': task_id,
                    'stock_index': stock_index,
                    'stock_ticker': stock['ticker'],
                    'stock_name': stock['name'],
                    'cost': cost,
                    'element_id': f'purchase-info-{stock_index}'
                }
                
                # If cost is $0, skip the confirmation modal
                if cost == 0:
                    return False, "", pending
                
                # Create modal body for bundle purchase
                modal_body = html.Div([
                    html.P([
                        "Purchasing information access for ",
                        html.Strong(stock['name']),
                        f" ({stock['ticker']}) will cost ",
                        html.Strong(f"${cost:.2f}"),
                        "."
                    ], className="mb-3"),
                    html.P("This will enable all information buttons (Show More Details, Week's Chart, and Month's Chart).", className="mb-3"),
                    html.P("Do you want to proceed?", className="mb-0")
                ])
                
                return True, modal_body, pending
            
            if info_type in ['show-more', 'show-week', 'show-month']:
                # Individual info buttons are now free after bundle purchase
                # These buttons are only enabled after bundle is purchased
                # Get task data to retrieve stock info
                task_data, error = get_task_data_safe(task_id, experiment_key)
                if error:
                    return False, "", {}
                
                stock = task_data['stocks'][stock_index]
                
                # Log the request
                if participant_id:
                    try:
                        log_event(
                            participant_id=participant_id,
                            event_type='info_request',
                            event_category='interaction',
                            page_name='task',
                            task_id=current_task,
                            element_id=f'{info_type}-{stock_index}',
                            element_type='button',
                            action='click',
                            stock_ticker=stock['ticker'],
                            metadata={
                                'cost': 0,  # Free after bundle purchase
                                'info_type': info_type,
                                'stock_name': stock['name'],
                                'stock_index': stock_index
                            }
                        )
                    except Exception:
                        logger.exception("Error logging event")
                
                # Create pending request with $0 cost (already paid via bundle)
                pending = {
                    'info_type': info_type,
                    'task_id': task_id,
                    'stock_index': stock_index,
                    'stock_ticker': stock['ticker'],
                    'stock_name': stock['name'],
                    'cost': 0,
                    'element_id': f'{info_type}-{stock_index}'
                }
                
                # No confirmation modal needed - directly open info modal
                return False, "", pending
        
        return dash.no_update, dash.no_update, dash.no_update
    
    
    # ============================================
    # MODAL CALLBACKS
    # ============================================
    
    @app.callback(
        Output('stock-modal', 'is_open'),
        Output('modal-title', 'children'),
        Output('modal-body', 'children'),
        Output('modal-context', 'data'),
        Output('pending-info-request', 'data', allow_duplicate=True),
        Output('cost-modal', 'is_open', allow_duplicate=True),
        Output('amount', 'data', allow_duplicate=True),
        Output('info-cost-spent', 'data', allow_duplicate=True),
        Output('purchased-info', 'data', allow_duplicate=True),
        Input('cost-modal-ok', 'n_clicks'),
        Input('close-modal', 'n_clicks'),
        Input('pending-info-request', 'data'),
        State('stock-modal', 'is_open'),
        State('current-task', 'data'),
        State('task-order', 'data'),
        State('participant-id', 'data'),
        State('modal-context', 'data'),
        State('amount', 'data'),
        State('info-cost-spent', 'data'),
        State('purchased-info', 'data'),
        State('current-page', 'data'),
        State('experiment-key', 'data'),
        prevent_initial_call=True
    )
    def toggle_modal(ok_clicks, close_clicks, pending_request, is_open, current_task, task_order, participant_id, modal_context, current_amount, info_spent, purchased_info, current_page, experiment_key):
        """Handle opening/closing of stock details modal after cost confirmation."""
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        triggered_id = ctx.triggered[0]['prop_id']
        
        if 'close-modal' in triggered_id:
            if participant_id and modal_context:
                try:
                    log_event(
                        participant_id=participant_id,
                        event_type='modal_close',
                        event_category='interaction',
                        page_name='task',
                        task_id=current_task,
                        element_id=modal_context.get('element_id', 'close-modal'),
                        element_type='button',
                        action='click',
                        stock_ticker=modal_context.get('stock_ticker'),
                        metadata=modal_context.get('metadata')
                    )
                except Exception:
                    logger.exception("Error logging event")
            # Clear pending request when closing info modal
            return False, "", "", {}, {}, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Handle pending request with $0 cost - directly open stock modal without confirmation
        if 'pending-info-request' in triggered_id and pending_request:
            cost = pending_request.get('cost', 0)
            # Only process if cost is 0 (free information)
            if cost == 0:
                info_type = pending_request.get('info_type')
                task_id = pending_request.get('task_id')
                stock_index = pending_request.get('stock_index')
                
                # Validate task ID - skip validation for tutorial tasks
                if not str(task_id).startswith('tutorial_'):
                    # Get the actual task ID for current task from randomized order
                    actual_task_id = task_order[current_task - 1] if task_order else current_task
                    
                    # Validate that pending request matches current task
                    if task_id != actual_task_id:
                        logger.warning("Task ID mismatch for free info - pending task_id=%s, actual_task_id=%s", task_id, actual_task_id)
                        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, {}, dash.no_update, dash.no_update, dash.no_update, dash.no_update
                
                if task_id is None or stock_index is None:
                    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, {}, dash.no_update, dash.no_update, dash.no_update, dash.no_update
                
                task_data, error = get_task_data_safe(task_id, experiment_key)
                if error:
                    return True, "Error", html.P(error, className="text-danger"), {}, {}, dash.no_update, dash.no_update, dash.no_update, dash.no_update
                
                stock = task_data['stocks'][stock_index]
                
                # Handle purchase-info (bundle) - no modal, just mark as purchased
                if info_type == 'purchase-info':
                    bundle_identifier = f'bundle-{stock_index}'
                    updated_purchased = list(purchased_info or [])
                    if bundle_identifier not in updated_purchased:
                        updated_purchased.append(bundle_identifier)
                    # Don't open modal, just update purchased list
                    return False, "", "", {}, dash.no_update, False, current_amount, info_spent, updated_purchased
                
                # Handle different info types (show-more, show-week, show-month)
                # These are free to view after bundle purchase, just open the modal
                if info_type == 'show-more':
                    modal_ctx = {
                        'element_id': f'show-more-{stock_index}',
                        'stock_ticker': stock['ticker'],
                        'metadata': {'stock_name': stock['name'], 'stock_index': stock_index}
                    }
                    
                    if participant_id:
                        try:
                            log_event(
                                participant_id=participant_id,
                                event_type='modal_open',
                                event_category='interaction',
                                page_name='task',
                                task_id=current_task,
                                element_id=modal_ctx['element_id'],
                                element_type='button',
                                action='click',
                                stock_ticker=modal_ctx['stock_ticker'],
                                metadata=modal_ctx['metadata']
                            )
                        except Exception:
                            logger.exception("Error logging event")
                    
                    modal_content = [
                        html.H5(f"{stock['ticker']}", className="text-muted mb-3"),
                        html.P(stock['detailed_description'])
                    ]
                    
                    if 'performance_metrics' in stock:
                        metrics = stock['performance_metrics']
                        modal_content.append(html.Hr(className="my-4"))
                        modal_content.append(html.H5("Performance Metrics", className="mb-3"))
                        modal_content.append(
                            dbc.Table([
                                html.Tbody([
                                    html.Tr([html.Td("5-day", style={'fontWeight': 'bold', 'width': '40%'}), html.Td(metrics.get('5-day', 'N/A'), style={'textAlign': 'right'})]),
                                    html.Tr([html.Td("10-day", style={'fontWeight': 'bold'}), html.Td(metrics.get('10-day', 'N/A'), style={'textAlign': 'right'})]),
                                    html.Tr([html.Td("1-month", style={'fontWeight': 'bold'}), html.Td(metrics.get('1-month', 'N/A'), style={'textAlign': 'right'})]),
                                    html.Tr([html.Td("3-month", style={'fontWeight': 'bold'}), html.Td(metrics.get('3-month', 'N/A'), style={'textAlign': 'right'})]),
                                    html.Tr([html.Td("6-month", style={'fontWeight': 'bold'}), html.Td(metrics.get('6-month', 'N/A'), style={'textAlign': 'right'})]),
                                    html.Tr([html.Td("YTD", style={'fontWeight': 'bold'}), html.Td(metrics.get('YTD', 'N/A'), style={'textAlign': 'right'})])
                                ])
                            ], bordered=True, hover=True, striped=True, className="mb-0")
                        )
                    
                    return True, stock['name'], html.Div(modal_content), modal_ctx, dash.no_update, False, current_amount, info_spent, dash.no_update
                
                elif info_type == 'show-week':
                    modal_ctx = {
                        'element_id': f'show-week-{stock_index}',
                        'stock_ticker': stock['ticker'],
                        'metadata': {'stock_name': stock['name'], 'stock_index': stock_index, 'view_type': 'week'}
                    }
                    
                    if participant_id:
                        try:
                            log_event(
                                participant_id=participant_id,
                                event_type='modal_open',
                                event_category='interaction',
                                page_name='task',
                                task_id=current_task,
                                element_id=modal_ctx['element_id'],
                                element_type='button',
                                action='click',
                                stock_ticker=modal_ctx['stock_ticker'],
                                metadata=modal_ctx['metadata']
                            )
                        except Exception:
                            logger.exception("Error logging event")
                    
                    return True, f"{stock['name']} - Weekly Analysis", html.Div([
                        html.H5(f"{stock['ticker']}", className="text-muted mb-3"),
                        html.Img(
                            src=stock.get('week_image', 'https://via.placeholder.com/600x300?text=Weekly+Chart'),
                            style={'width': '100%', 'maxWidth': '600px'},
                            className="mb-3 d-block mx-auto"
                        ),
                        html.H6("Weekly Performance Analysis", className="mb-2"),
                        html.P(stock.get('week_analysis', 'Weekly performance data for this stock.'))
                    ]), modal_ctx, dash.no_update, False, current_amount, info_spent, dash.no_update
                
                elif info_type == 'show-month':
                    modal_ctx = {
                        'element_id': f'show-month-{stock_index}',
                        'stock_ticker': stock['ticker'],
                        'metadata': {'stock_name': stock['name'], 'stock_index': stock_index, 'view_type': 'month'}
                    }
                    
                    if participant_id:
                        try:
                            log_event(
                                participant_id=participant_id,
                                event_type='modal_open',
                                event_category='interaction',
                                page_name='task',
                                task_id=current_task,
                                element_id=modal_ctx['element_id'],
                                element_type='button',
                                action='click',
                                stock_ticker=modal_ctx['stock_ticker'],
                                metadata=modal_ctx['metadata']
                            )
                        except Exception:
                            logger.exception("Error logging event")
                    
                    return True, f"{stock['name']} - Monthly Analysis", html.Div([
                        html.H5(f"{stock['ticker']}", className="text-muted mb-3"),
                        html.Img(
                            src=stock.get('month_image', 'https://via.placeholder.com/600x300?text=Monthly+Chart'),
                            style={'width': '100%', 'maxWidth': '600px'},
                            className="mb-3 d-block mx-auto"
                        ),
                        html.H6("Monthly Performance Analysis", className="mb-2"),
                        html.P(stock.get('month_analysis', 'Monthly performance data for this stock.'))
                    ]), modal_ctx, dash.no_update, False, current_amount, info_spent, dash.no_update
        
        # Handle OK button on cost modal - close cost modal and open info modal
        if 'cost-modal-ok' in triggered_id and pending_request and ok_clicks:
            # Deduct cost from available amount and add to spent tracker
            cost = pending_request.get('cost', 0)
            new_amount = current_amount - cost
            new_info_spent = (info_spent or 0) + cost
            
            # Log acceptance of cost (only if cost > 0)
            if participant_id and pending_request and cost > 0:
                try:
                    log_event(
                        participant_id=participant_id,
                        event_type='cost_confirmation_accept',
                        event_category='interaction',
                        page_name='task',
                        task_id=current_task,
                        element_id=pending_request.get('element_id'),
                        element_type='button',
                        action='accept',
                        stock_ticker=pending_request.get('stock_ticker'),
                        metadata={
                            'cost': pending_request.get('cost'),
                            'info_type': pending_request.get('info_type'),
                            'stock_name': pending_request.get('stock_name')
                        }
                    )
                except Exception:
                    logger.exception("Error logging event")
            
            info_type = pending_request.get('info_type')
            task_id = pending_request.get('task_id')
            stock_index = pending_request.get('stock_index')
            
            # Validate task ID - skip validation for tutorial tasks
            if not str(task_id).startswith('tutorial_'):
                # Get the actual task ID for current task from randomized order
                actual_task_id = task_order[current_task - 1] if task_order else current_task
                
                # Validate that pending request matches current task - prevents stale data issues
                if task_id != actual_task_id:
                    logger.warning("Task ID mismatch - pending task_id=%s, actual_task_id=%s", task_id, actual_task_id)
                    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, {}, False, dash.no_update, dash.no_update, dash.no_update
            
            if task_id is None or stock_index is None:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, {}, False, dash.no_update, dash.no_update, dash.no_update
            
            task_data, error = get_task_data_safe(task_id, experiment_key)
            if error:
                return True, "Error", html.P(error, className="text-danger"), {}, dash.no_update, False, dash.no_update, dash.no_update, dash.no_update
            
            stock = task_data['stocks'][stock_index]
            
            # Handle purchase-info - bundle purchase (this is the only type that goes through cost confirmation now)
            if info_type == 'purchase-info':
                # Add bundle to purchased list
                bundle_identifier = f'bundle-{stock_index}'
                updated_purchased = list(purchased_info or [])
                if bundle_identifier not in updated_purchased:
                    updated_purchased.append(bundle_identifier)
                
                # Close both modals and update amount, don't open any info modal
                return False, "", "", {}, {}, False, new_amount, new_info_spent, updated_purchased
            
            # Note: Individual info buttons (show-more, show-week, show-month) no longer go through
            # this cost confirmation path since they are free after bundle purchase
            # They go directly through the pending-info-request handler
            
            # If somehow we get here with another type, just close modals
            return False, "", "", {}, {}, False, dash.no_update, dash.no_update, dash.no_update
        
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    
    # ============================================
    # AMOUNT DISPLAY UPDATE
    # ============================================
    
    @app.callback(
        Output({'type': 'amount-display', 'task': ALL, 'stock': ALL}, 'children'),
        Input('amount', 'data'),
        prevent_initial_call=False
    )
    def update_amount_display(amount):
        """Update the available amount display when amount changes."""
        if amount is None:
            amount = INITIAL_AMOUNT
        
        # Return the same content for all amount displays on the page
        display_content = [
            html.I(className="bi bi-wallet2 me-2"),
            f"Available: ${amount:,.2f}"
        ]
        
        # Return list of same content for each display (pattern matching ALL)
        return [display_content] * len(dash.callback_context.outputs_list)
    
    
    # ============================================
    # BUTTON STATE UPDATE (Enable/Disable Purchase and Display Buttons)
    # ============================================
    
    @app.callback(
        Output({'type': 'purchase-info', 'task': ALL, 'stock': ALL}, 'disabled'),
        Output({'type': 'show-more', 'task': ALL, 'stock': ALL}, 'disabled'),
        Output({'type': 'show-week', 'task': ALL, 'stock': ALL}, 'disabled'),
        Output({'type': 'show-month', 'task': ALL, 'stock': ALL}, 'disabled'),
        Input('purchased-info', 'data'),
        State('current-task', 'data'),
        State('task-order', 'data'),
        State('current-page', 'data'),
        State('experiment-key', 'data'),
        prevent_initial_call=False
    )
    def update_button_states(purchased_info, current_task, task_order, current_page, experiment_key):
        """Enable/disable buttons based on purchase status."""
        # Get the number of outputs for each type to ensure we return the right number of values
        ctx = dash.callback_context
        num_purchase_outputs = len(ctx.outputs_list[0])
        num_more_outputs = len(ctx.outputs_list[1])
        num_week_outputs = len(ctx.outputs_list[2])
        num_month_outputs = len(ctx.outputs_list[3])
        
        # If no buttons are rendered, return empty lists
        if num_purchase_outputs == 0 and num_more_outputs == 0 and num_week_outputs == 0 and num_month_outputs == 0:
            return [], [], [], []
        
        # Determine the actual task ID based on current page
        if current_page == PAGES['tutorial_1']:
            actual_task_id = 'tutorial_1'
        elif current_page == PAGES['tutorial_2']:
            actual_task_id = 'tutorial_2'
        elif current_task and task_order and (current_task - 1) < len(task_order):
            # Get the actual task ID from the randomized order
            actual_task_id = task_order[current_task - 1]
        else:
            actual_task_id = current_task
        
        # Get task data to check bundle cost
        task_data, error = get_task_data_safe(actual_task_id, experiment_key)
        
        purchase_disabled = []
        more_disabled = []
        week_disabled = []
        month_disabled = []
        
        if not error and task_data and 'stocks' in task_data:
            # Check if information buttons should be shown at all
            show_information = task_data.get('show_information', True)
            
            if show_information:
                for stock_idx in range(len(task_data['stocks'])):
                    stock = task_data['stocks'][stock_idx]
                    bundle_identifier = f'bundle-{stock_idx}'
                    bundle_purchased = bundle_identifier in (purchased_info or [])
                    
                    # Check if bundle cost is $0 (free)
                    bundle_cost = stock.get('info_costs', {}).get('purchase_bundle', 0)
                    is_free = bundle_cost == 0
                    
                    # Only add to purchase_disabled if the button was actually rendered (cost > 0)
                    if bundle_cost > 0:
                        # If bundle is purchased, disable purchase button
                        purchase_disabled.append(bundle_purchased)
                    
                    # Info buttons should be enabled if bundle is purchased or free
                    more_disabled.append(not (bundle_purchased or is_free))
                    week_disabled.append(not (bundle_purchased or is_free))
                    month_disabled.append(not (bundle_purchased or is_free))
        
        # Ensure we return the correct number of values matching the number of outputs
        # Pad with True (disabled) if we don't have enough values
        while len(purchase_disabled) < num_purchase_outputs:
            purchase_disabled.append(True)
        while len(more_disabled) < num_more_outputs:
            more_disabled.append(True)
        while len(week_disabled) < num_week_outputs:
            week_disabled.append(True)
        while len(month_disabled) < num_month_outputs:
            month_disabled.append(True)
        
        return purchase_disabled, more_disabled, week_disabled, month_disabled
    
    
    # ============================================
    # TUTORIAL SUBMISSION
    # ============================================
    
    # ============================================
    # TUTORIAL CALLBACKS
    # ============================================
    
    # Reset tutorial buttons to disabled when entering tutorial pages
    @app.callback(
        Output('tutorial-1-submit', 'disabled', allow_duplicate=True),
        Output('purchased-info', 'data', allow_duplicate=True),
        Input('current-page', 'data'),
        State('experiment-key', 'data'),
        prevent_initial_call=True
    )
    def reset_tutorial_1_button(current_page, experiment_key):
        """Ensure tutorial 1 button starts disabled (if purchase required) and reset purchased info."""
        if current_page == PAGES['tutorial_1']:
            # Check if tutorial 1 requires purchase
            task_data, error = get_task_data_safe('tutorial_1', experiment_key)
            if not error and task_data:
                show_information = task_data.get('show_information', True)
                if show_information:
                    stocks = task_data.get('stocks', [])
                    if stocks:
                        purchase_cost = stocks[0].get('info_costs', {}).get('purchase_bundle', 0)
                        requires_purchase = purchase_cost > 0
                        return requires_purchase, []  # Reset purchased-info to empty list
            return False, []  # If no purchase required, button is enabled
        elif current_page == PAGES['tutorial_2']:
            return dash.no_update, []  # Reset purchased-info but don't touch tutorial 2 button
        return dash.no_update, dash.no_update
    
    
    # Simple tutorial 1 button enablement - enable button when info modal closes
    @app.callback(
        Output('tutorial-1-submit', 'disabled'),
        Output('tutorial-1-status', 'children'),
        Input('stock-modal', 'is_open'),
        State('current-page', 'data'),
        State('purchased-info', 'data'),
        State('experiment-key', 'data'),
        prevent_initial_call=True
    )
    def enable_tutorial_1_button(modal_is_open, current_page, purchased_info, experiment_key):
        """Enable tutorial 1 button after viewing info (only if purchase is required)."""
        # Only act on tutorial 1 page
        if current_page != PAGES['tutorial_1']:
            return dash.no_update, dash.no_update
        
        # Check if tutorial 1 requires purchase
        task_data, error = get_task_data_safe('tutorial_1', experiment_key)
        if error or not task_data:
            return dash.no_update, dash.no_update
        
        show_information = task_data.get('show_information', True)
        requires_purchase = False
        if show_information:
            stocks = task_data.get('stocks', [])
            if stocks:
                purchase_cost = stocks[0].get('info_costs', {}).get('purchase_bundle', 0)
                requires_purchase = purchase_cost > 0
        
        # Only enable button after purchase if purchase is required
        if requires_purchase:
            # Check if modal just closed AND user has viewed at least one piece of info
            if not modal_is_open and purchased_info and len(purchased_info) > 0:
                return False, dbc.Alert([
                    html.I(className="bi bi-check-circle me-2"),
                    "Great! You've learned how to purchase information. Now, view some information, and then enter an investment amount and click Continue. You can also choose to not invest, in which case enter 0 and click Continue."
                ], color="success", className="text-center mt-3")
        
        return dash.no_update, dash.no_update
    
    
    @app.callback(
        Output('tutorial-1-result-modal', 'is_open'),
        Output('tutorial-1-result-body', 'children'),
        Output('tutorial-error', 'children', allow_duplicate=True),
        Output('amount', 'data', allow_duplicate=True),
        Input('tutorial-1-submit', 'n_clicks'),
        State({'type': 'investment-input', 'task': ALL, 'stock': ALL}, 'value'),
        State('amount', 'data'),
        State('participant-id', 'data'),
        State('experiment-key', 'data'),
        prevent_initial_call=True
    )
    def submit_tutorial_1(n_clicks, investment_values, current_amount, participant_id, experiment_key):
        """Handle tutorial 1 submission."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Validate investment
        validated_investments = []
        for i, value in enumerate(investment_values):
            amount, error = validate_investment(value, f"Stock {i+1}")
            if error:
                return False, "", error, dash.no_update
            validated_investments.append(amount)
        
        # Validate total
        is_valid, error = validate_total_investment(validated_investments, current_amount)
        if not is_valid:
            return False, "", error, dash.no_update
        
        # Get task data
        task_data, task_error = get_task_data_safe('tutorial_1', experiment_key)
        if task_error:
            return False, "", task_error, dash.no_update
        
        total_investment = sum(validated_investments)
        
        # Calculate result
        total_profit_loss = 0
        for i, investment_amount in enumerate(validated_investments):
            if investment_amount > 0:
                stock = task_data['stocks'][i]
                return_percent = stock.get('return_percent', 0)
                final_value = investment_amount * (1 + return_percent / 100)
                profit_loss = final_value - investment_amount
                total_profit_loss += profit_loss
        
        # Check if we should show profit/loss details (configurable via task data)
        show_profit_loss = task_data.get('show_profit_loss', True)  # Default to True for tutorials
        show_information = task_data.get('show_information', True)  # For logging purposes
        experiment_config = get_experiment_config(experiment_key) or {}
        main_show_profit_loss = experiment_config.get('show_profit_loss', show_profit_loss)
        main_show_information = experiment_config.get('show_information', show_information)
        info_cost_mode = experiment_config.get('info_cost_mode', 'fixed')
        tutorial_purchase_cost = task_data['stocks'][0].get('info_costs', {}).get('purchase_bundle', 0)
        
        # Create result modal content
        # If show_profit_loss is True: show detailed breakdown with investment/profit amounts
        # If show_profit_loss is False: show simple "investment recorded" message
        if total_investment == 0:
            main_message = "You did not invest in this task."
            result_content_parts = [html.H5(main_message, className="text-center mb-4")]
        else:
            if show_profit_loss:
                # Show detailed profit/loss information
                if total_profit_loss > 0:
                    main_message = "Your investment made a profit! 📈"
                elif total_profit_loss < 0:
                    main_message = "Your investment made a loss. 📉"
                else:
                    main_message = "Your investment broke even."
                
                result_content_parts = [
                    html.H5(main_message, className="text-center mb-4"),
                    html.Div([
                        html.P([
                            html.Strong("Investment: "),
                            f"${total_investment:,.2f}"
                        ], className="mb-2"),
                        html.P([
                            html.Strong("Profit/Loss: "),
                            html.Span(
                                f"${total_profit_loss:+,.2f}",
                                style={
                                    'color': 'green' if total_profit_loss >= 0 else 'red',
                                    'fontWeight': 'bold'
                                }
                            )
                        ], className="mb-4"),
                    ], className="text-center"),
                    html.Hr(),
                ]
            else:
                # Simple message without details - matching main task behavior
                result_content_parts = [html.P("Your investment has been recorded.", className="mb-0")]
        
        # Message for tutorial 1
        if main_show_profit_loss:
            feedback_note = "In the main study, you will continue to see task-level outcome feedback after each decision."
        else:
            feedback_note = "In the main study, task-level outcome feedback appears in the final results summary."

        if main_show_information:
            if tutorial_purchase_cost > 0:
                if info_cost_mode == 'variable':
                    information_note = (
                        f"Information is available and prices vary by stock. "
                        f"In this tutorial stock, the information package costs ${tutorial_purchase_cost:,.2f}."
                    )
                else:
                    information_note = (
                        f"Information is available with fixed pricing. "
                        f"In this tutorial, the information package costs ${tutorial_purchase_cost:,.2f}."
                    )
            else:
                information_note = "Information panels are available directly from the stock card."
        else:
            information_note = "You will make decisions using the stock summary and investment amount entry."

        result_content_parts.append(
            html.Div([
                html.P([
                    html.I(className="bi bi-lightbulb-fill me-2"),
                    "Great job! You've completed the first tutorial."
                ], className="mb-2"),
                html.P(feedback_note, className="text-muted mb-2"),
                html.P(information_note, className="text-muted mb-0")
            ], style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '8px'})
        )
        
        result_content = html.Div(result_content_parts)
        
        if participant_id:
            try:
                log_event(
                    participant_id=participant_id,
                    event_type='tutorial_submit',
                    event_category='interaction',
                    page_name='tutorial_1',
                    element_id='tutorial-1-submit',
                    action='submit',
                    metadata={
                        'investment': total_investment, 
                        'profit_loss': total_profit_loss,
                        'show_profit_loss': show_profit_loss,
                        'show_information': show_information
                    }
                )
            except Exception:
                logger.exception("Error logging tutorial")
        
        # Deduct investment from amount
        new_amount = current_amount - total_investment
        return True, result_content, "", new_amount
    
    
    @app.callback(
        Output('current-page', 'data', allow_duplicate=True),
        Input('tutorial-1-result-ok', 'n_clicks'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def tutorial_1_next(n_clicks, participant_id):
        """Navigate from tutorial 1 to tutorial 2."""
        if not n_clicks:
            return dash.no_update
        
        if participant_id:
            try:
                log_event(
                    participant_id=participant_id,
                    event_type='page_navigation',
                    event_category='navigation',
                    page_name='tutorial_2',
                    action='navigate'
                )
            except Exception:
                logger.exception("Error logging event")
        
        return PAGES['tutorial_2']
    
    
    @app.callback(
        Output('tutorial-2-result-modal', 'is_open'),
        Output('tutorial-2-result-body', 'children'),
        Output('tutorial-error', 'children'),
        Output('amount', 'data', allow_duplicate=True),
        Input('tutorial-2-submit', 'n_clicks'),
        State({'type': 'investment-input', 'task': ALL, 'stock': ALL}, 'value'),
        State('amount', 'data'),
        State('participant-id', 'data'),
        State('experiment-key', 'data'),
        prevent_initial_call=True
    )
    def submit_tutorial_2(n_clicks, investment_values, current_amount, participant_id, experiment_key):
        """Handle tutorial 2 submission."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Validate investment
        validated_investments = []
        for i, value in enumerate(investment_values):
            amount, error = validate_investment(value, f"Stock {i+1}")
            if error:
                return False, "", error, dash.no_update
            validated_investments.append(amount)
        
        # Validate total
        is_valid, error = validate_total_investment(validated_investments, current_amount)
        if not is_valid:
            return False, "", error, dash.no_update
        
        # Get task data
        task_data, task_error = get_task_data_safe('tutorial_2', experiment_key)
        if task_error:
            return False, "", task_error, dash.no_update
        
        total_investment = sum(validated_investments)
        
        # Calculate result
        total_profit_loss = 0
        for i, investment_amount in enumerate(validated_investments):
            if investment_amount > 0:
                stock = task_data['stocks'][i]
                return_percent = stock.get('return_percent', 0)
                final_value = investment_amount * (1 + return_percent / 100)
                profit_loss = final_value - investment_amount
                total_profit_loss += profit_loss
        
        # Check if we should show profit/loss details (configurable via task data)
        show_profit_loss = task_data.get('show_profit_loss', True)  # Default to True for tutorials
        show_information = task_data.get('show_information', True)  # For logging purposes
        experiment_config = get_experiment_config(experiment_key) or {}
        main_show_profit_loss = experiment_config.get('show_profit_loss', show_profit_loss)
        main_show_information = experiment_config.get('show_information', show_information)
        info_cost_mode = experiment_config.get('info_cost_mode', 'fixed')
        tutorial_purchase_cost = task_data['stocks'][0].get('info_costs', {}).get('purchase_bundle', 0)
        
        # Create result modal content
        # If show_profit_loss is True: show detailed breakdown with investment/profit amounts
        # If show_profit_loss is False: show simple "investment recorded" message
        if total_investment == 0:
            main_message = "You did not invest in this task."
            result_content_parts = [html.H5(main_message, className="text-center mb-4")]
        else:
            if show_profit_loss:
                # Show detailed profit/loss information
                if total_profit_loss > 0:
                    main_message = "Your investment made a profit! 📈"
                elif total_profit_loss < 0:
                    main_message = "Your investment made a loss. 📉"
                else:
                    main_message = "Your investment broke even."
                
                result_content_parts = [
                    html.H5(main_message, className="text-center mb-4"),
                    html.Div([
                        html.P([
                            html.Strong("Investment: "),
                            f"${total_investment:,.2f}"
                        ], className="mb-2"),
                        html.P([
                            html.Strong("Profit/Loss: "),
                            html.Span(
                                f"${total_profit_loss:+,.2f}",
                                style={
                                    'color': 'green' if total_profit_loss >= 0 else 'red',
                                    'fontWeight': 'bold'
                                }
                            )
                        ], className="mb-4"),
                    ], className="text-center"),
                    html.Hr(),
                ]
            else:
                # Simple message without details - matching main task behavior
                result_content_parts = [html.P("Your investment has been recorded.", className="mb-0")]
        
        # Important note about main study
        if main_show_profit_loss:
            outcome_line_1 = "In the main study, you will see your task-level outcome after each investment decision."
            outcome_line_2 = "Those outcomes are for feedback and still do not directly change your available cash balance."
        else:
            outcome_line_1 = "In the main study, task-level outcomes are presented in the final results summary."
            outcome_line_2 = "Your available cash during tasks reflects your entered investments and information actions."

        if main_show_information:
            if tutorial_purchase_cost > 0:
                if info_cost_mode == 'variable':
                    info_line = (
                        f"Information is available and prices vary by stock; this tutorial stock uses ${tutorial_purchase_cost:,.2f}."
                    )
                else:
                    info_line = (
                        f"Information is available with fixed pricing; this tutorial stock uses ${tutorial_purchase_cost:,.2f}."
                    )
            else:
                info_line = "Information panels are available directly from the stock card."
            balance_line = "Your available amount decreases by what you invest and any information purchases."
        else:
            info_line = "You will make decisions using the stock summary and investment amount entry."
            balance_line = "Your available amount decreases with each investment amount you enter."

        result_content_parts.append(
            html.Div([
                html.P([
                    html.I(className="bi bi-info-circle-fill me-2"),
                    html.Strong("Important:")
                ], className="mb-2"),
                html.Ul([
                    html.Li(outcome_line_1),
                    html.Li(outcome_line_2),
                    html.Li(info_line),
                    html.Li(balance_line)
                ], className="mb-3 text-start"),
                html.P([
                    html.Strong("You're now ready for the main study!"),
                    " Your decisions will be recorded from this point forward."
                ], className="text-center mb-0")
            ], style={'backgroundColor': '#f8f9fa', 'padding': '20px', 'borderRadius': '8px'})
        )
        
        result_content = html.Div(result_content_parts)
        
        if participant_id:
            try:
                log_event(
                    participant_id=participant_id,
                    event_type='tutorial_submit',
                    event_category='interaction',
                    page_name='tutorial_2',
                    element_id='tutorial-2-submit',
                    action='submit',
                    metadata={
                        'investment': total_investment, 
                        'profit_loss': total_profit_loss,
                        'show_profit_loss': show_profit_loss,
                        'show_information': show_information
                    }
                )
            except Exception:
                logger.exception("Error logging tutorial")
        
        # Deduct investment from amount
        new_amount = current_amount - total_investment
        return True, result_content, "", new_amount
    
    
    @app.callback(
        Output('current-page', 'data', allow_duplicate=True),
        Output('tutorial-completed', 'data'),
        Output('amount', 'data', allow_duplicate=True),
        Output('pending-info-request', 'data', allow_duplicate=True),
        Output('purchased-info', 'data', allow_duplicate=True),
        Input('tutorial-2-result-ok', 'n_clicks'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def tutorial_2_next(n_clicks, participant_id):
        """Navigate from tutorial 2 to first main task and reset amount to $1000."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        if participant_id:
            try:
                log_event(
                    participant_id=participant_id,
                    event_type='page_navigation',
                    event_category='navigation',
                    page_name='task',
                    task_id=1,
                    action='navigate',
                    metadata={'tutorials_completed': True, 'amount_reset': INITIAL_AMOUNT}
                )
            except Exception:
                logger.exception("Error logging event")
        
        return PAGES['task'], True, INITIAL_AMOUNT, {}, []
    
    
    # ============================================
    # TASK SUBMISSION
    # ============================================
    
    @app.callback(
        Output('cr-modal', 'is_open'),
        Output('pending-result', 'data'),
        Output('current-page', 'data', allow_duplicate=True),
        Output('current-task', 'data'),
        Output('amount', 'data'),
        Output('task-responses', 'data'),
        Output('portfolio', 'data'),
        Output('task-error', 'children'),
        Output('purchased-info', 'data', allow_duplicate=True),
        Input('task-submit', 'n_clicks'),
        State({'type': 'investment-input', 'task': ALL, 'stock': ALL}, 'value'),
        State('current-task', 'data'),
        State('task-order', 'data'),
        State('amount', 'data'),
        State('task-responses', 'data'),
        State('portfolio', 'data'),
        State('participant-id', 'data'),
        State('experiment-key', 'data'),
        prevent_initial_call=True
    )
    def submit_task(n_clicks, investment_values, current_task, task_order, current_amount, responses, portfolio, participant_id, experiment_key):
        """Handle task submission with investment validation and portfolio tracking."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Get the actual task ID from the randomized order
        actual_task_id = task_order[current_task - 1] if task_order else current_task
        
        # Validate each investment
        validated_investments = []
        for i, value in enumerate(investment_values):
            amount, error = validate_investment(value, f"Stock {i+1}")
            if error:
                if participant_id:
                    try:
                        log_event(
                            participant_id=participant_id,
                            event_type='validation_error',
                            event_category='error',
                            page_name='task',
                            task_id=current_task,
                            element_id=f'investment-input-{i}',
                            action='submit',
                            metadata={'error': error}
                        )
                    except Exception:
                        logger.exception("Error logging event")
                return False, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, error, dash.no_update
            validated_investments.append(amount)
        
        # Validate total
        is_valid, error = validate_total_investment(validated_investments, current_amount)
        if not is_valid:
            if participant_id:
                try:
                    log_event(
                        participant_id=participant_id,
                        event_type='validation_error',
                        event_category='error',
                        page_name='task',
                        task_id=current_task,
                        action='submit',
                        metadata={'error': error, 'total_investment': sum(validated_investments)}
                    )
                except Exception:
                    logger.exception("Error logging event")
            return False, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, error, dash.no_update
        
        # Get task data using the actual randomized task ID
        task_data, task_error = get_task_data_safe(actual_task_id, experiment_key)
        if task_error:
            return False, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, task_error, dash.no_update
        
        total_investment = sum(validated_investments)
        response_entry = {
            'investments': validated_investments,
            'total': total_investment,
            'actual_task_id': actual_task_id,
            'stocks': [
                {
                    'name': stock.get('name', ''),
                    'ticker': stock.get('ticker', ''),
                    'is_risky': bool(stock.get('is_risky', False))
                }
                for stock in task_data.get('stocks', [])
            ]
        }
        
        # Update portfolio and calculate profit/loss
        if portfolio is None:
            portfolio = []

        updated_portfolio = list(portfolio)
        portfolio_items_to_save = []
        
        total_profit_loss = 0
        for i, investment_amount in enumerate(validated_investments):
            if investment_amount > 0:
                stock = task_data['stocks'][i]
                return_percent = stock.get('return_percent', 0)
                final_value = investment_amount * (1 + return_percent / 100)
                profit_loss = final_value - investment_amount
                total_profit_loss += profit_loss
                
                portfolio_item = {
                    'task_id': current_task,
                    'stock_name': stock['name'],
                    'ticker': stock['ticker'],
                    'invested': investment_amount,
                    'return_percent': return_percent,
                    'final_value': final_value,
                    'profit_loss': profit_loss
                }
                updated_portfolio.append(portfolio_item)
                portfolio_items_to_save.append(portfolio_item)
        
        new_amount = current_amount - total_investment
        
        # Save task response
        if participant_id:
            try:
                stocks = task_data['stocks']
                second_stock = stocks[1] if len(stocks) > 1 else None
                save_task_response(
                    participant_id=participant_id,
                    task_id=current_task,
                    stock_1_ticker=stocks[0]['ticker'],
                    stock_1_name=stocks[0]['name'],
                    stock_1_investment=validated_investments[0] if len(validated_investments) > 0 else 0,
                    stock_2_ticker=second_stock['ticker'] if second_stock else "",
                    stock_2_name=second_stock['name'] if second_stock else "",
                    stock_2_investment=validated_investments[1] if len(validated_investments) > 1 else 0,
                    total_investment=total_investment,
                    remaining_amount=new_amount,
                    show_profit_loss=task_data.get('show_profit_loss', False),
                    show_information=task_data.get('show_information', True),
                    experiment_key=experiment_key,
                )

                for portfolio_item in portfolio_items_to_save:
                    save_portfolio_investment(
                        participant_id=participant_id,
                        task_id=current_task,
                        stock_name=portfolio_item['stock_name'],
                        ticker=portfolio_item['ticker'],
                        invested_amount=portfolio_item['invested'],
                        return_percent=portfolio_item['return_percent'],
                        final_value=portfolio_item['final_value'],
                        profit_loss=portfolio_item['profit_loss']
                    )

                log_event(
                    participant_id=participant_id,
                    event_type='task_submit',
                    event_category='interaction',
                    page_name='task',
                    task_id=current_task,
                    stock_ticker=stocks[0]['ticker'],
                    element_id='task-submit',
                    element_type='button',
                    action='submit',
                    metadata={
                        'stock_name': stocks[0]['name'],
                        'investments': validated_investments,
                        'total_investment': total_investment,
                        'remaining_amount': new_amount,
                        'profit_loss': total_profit_loss,
                        'show_profit_loss': task_data.get('show_profit_loss', False),
                        'show_information': task_data.get('show_information', True)
                    }
                )
            except Exception:
                logger.exception("Error saving task response")
                return (
                    False,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    dash.no_update,
                    "We couldn't save your task response. Please try again.",
                    dash.no_update,
                )

        if responses is None:
            responses = {}
        responses[f'task_{current_task}'] = response_entry
        
        # Store result data to be displayed in the result modal after CR modal
        show_profit_loss = task_data.get('show_profit_loss', False)
        pending_result = {
            'total_investment': total_investment,
            'total_profit_loss': total_profit_loss,
            'new_amount': new_amount,
            'show_profit_loss': show_profit_loss
        }
        
        next_task = current_task + 1
        
        # Show confidence/risk modal first; result modal will appear after CR is submitted
        # Clear purchased-info for next task
        return True, pending_result, dash.no_update, next_task, new_amount, responses, updated_portfolio, "", []
    
    
    # Handle modal OK button - navigate to next page
    @app.callback(
        Output('result-modal', 'is_open', allow_duplicate=True),
        Output('current-page', 'data', allow_duplicate=True),
        Input('result-modal-ok', 'n_clicks'),
        State('current-task', 'data'),
        State('task-order', 'data'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def handle_modal_ok(n_clicks, current_task, task_order, participant_id):
        """Handle result modal OK button click and navigate to next task or feedback."""
        if not n_clicks:
            return dash.no_update, dash.no_update
        
        # current_task has already been incremented in submit_task
        completed_task = current_task - 1
        
        if participant_id:
            try:
                log_event(
                    participant_id=participant_id,
                    event_type='modal_ok',
                    event_category='interaction',
                    page_name='task',
                    task_id=completed_task,
                    element_id='result-modal-ok',
                    element_type='button',
                    action='click'
                )
            except Exception:
                logger.exception("Error logging event")
        
        # Navigate to feedback after all tasks, otherwise continue to next task
        if current_task > NUM_TASKS:
            if participant_id:
                try:
                    log_event(participant_id=participant_id, event_type='page_navigation',
                              event_category='navigation', page_name='feedback', action='navigate')
                except Exception:
                    logger.exception("Error logging event")
            return False, PAGES['feedback']
        
        if participant_id:
            try:
                log_event(participant_id=participant_id, event_type='page_navigation',
                          event_category='navigation', page_name='task',
                          task_id=current_task, action='navigate')
            except Exception:
                logger.exception("Error logging event")
        return False, PAGES['task']
    
    
    # ============================================
    # CONFIDENCE/RISK MODAL
    # ============================================
    
    # Update cr-modal content (message and attention check visibility) when modal opens
    @app.callback(
        Output('cr-modal-attention-section', 'style'),
        Output('cr-modal-attention-prompt', 'children'),
        Output('cr-modal-message', 'children'),
        Input('cr-modal', 'is_open'),
        State('current-task', 'data'),
        prevent_initial_call=True
    )
    def update_cr_modal_content(is_open, current_task):
        """Show/hide attention check and update message when CR modal opens."""
        if not is_open:
            return dash.no_update, dash.no_update, dash.no_update
        
        completed_task = (current_task or 2) - 1
        task_word = "decision" if completed_task == 1 else "decisions"
        message = f"You've completed {completed_task} investment {task_word}. Please take a moment to rate the following."
        
        if completed_task in ATTENTION_CHECK_TASKS:
            requested_option = 2 if completed_task == 3 else 4
            prompt = f"Please select option {requested_option} for this item. This question is used to verify attentive responding."
            return {'display': 'block'}, prompt, message
        
        return {'display': 'none'}, "", message
    
    # Handle CR modal submission: save data, then show result modal
    @app.callback(
        Output('cr-modal', 'is_open', allow_duplicate=True),
        Output('result-modal', 'is_open'),
        Output('result-modal-body', 'children'),
        Output('confidence-risk', 'data', allow_duplicate=True),
        Output('cr-modal-confidence', 'value'),
        Output('cr-modal-risk', 'value'),
        Output('cr-modal-attention', 'value'),
        Input('cr-modal-submit', 'n_clicks'),
        State('cr-modal-confidence', 'value'),
        State('cr-modal-risk', 'value'),
        State('cr-modal-attention', 'value'),
        State('current-task', 'data'),
        State('pending-result', 'data'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def submit_cr_modal(n_clicks, confidence, risk, attention_check, current_task, pending_result, participant_id):
        """Save confidence/risk data and open the result modal."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        completed_after_task = (current_task or 2) - 1
        
        # Only log attention check if it was actually shown; otherwise log as null
        attention_logged = attention_check if completed_after_task in ATTENTION_CHECK_TASKS else None
        
        confidence_risk_data = {
            'confidence': confidence,
            'risk': risk,
            'attention_check': attention_logged
        }
        
        if participant_id:
            try:
                save_confidence_risk(participant_id, confidence, risk,
                                     attention_check_response=attention_logged,
                                     completed_after_task=completed_after_task)
            except Exception:
                logger.exception("Error saving confidence/risk")
                return True, False, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

            try:
                log_event(
                    participant_id=participant_id,
                    event_type='confidence_risk_submit',
                    event_category='interaction',
                    page_name='confidence_risk',
                    element_id='cr-modal-submit',
                    element_type='button',
                    action='submit',
                    metadata={'confidence': confidence, 'risk': risk,
                              'attention_check': attention_logged,
                              'completed_after_task': completed_after_task}
                )
            except Exception:
                logger.exception("Error logging event")
        
        # Build result modal content from pending result data
        if not pending_result:
            result_body = html.P("Your investment has been recorded.", className="mb-0")
        else:
            total_investment = pending_result.get('total_investment', 0)
            total_profit_loss = pending_result.get('total_profit_loss', 0)
            new_amount = pending_result.get('new_amount', 0)
            show_profit_loss = pending_result.get('show_profit_loss', False)
            
            if total_investment == 0:
                result_body = html.P("You did not invest in this task.", className="mb-0")
            elif show_profit_loss:
                if total_profit_loss > 0:
                    color, icon, title = "success", "📈", "Your investment made a profit!"
                elif total_profit_loss < 0:
                    color, icon, title = "danger", "📉", "Your investment made a loss."
                else:
                    color, icon, title = "info", "➡️", "Your investment broke even."
                result_body = html.Div([
                    html.H5([icon, " ", title], className=f"text-{color} mb-3"),
                    html.Hr(),
                    html.P([html.Strong("Investment Amount: "), f"${total_investment:,.2f}"], className="mb-2"),
                    html.P([html.Strong("Final Value: "), f"${(total_investment + total_profit_loss):,.2f}"], className="mb-2"),
                    html.P([
                        html.Strong("Profit/Loss: "),
                        html.Span(
                            f"${abs(total_profit_loss):,.2f}" if total_profit_loss >= 0 else f"-${abs(total_profit_loss):,.2f}",
                            className=f"text-{color}"
                        )
                    ], className="mb-2"),
                    html.P([html.Strong("New Available Amount: "), f"${new_amount:,.2f}"], className="mb-0")
                ])
            else:
                result_body = html.P("Your investment has been recorded.", className="mb-0")
        
        # Reset all sliders to default (4) for next round
        return False, True, result_body, confidence_risk_data, 4, 4, 4
    
    
    # ============================================
    # CONFIDENCE/RISK & FEEDBACK
    # ============================================
    
    @app.callback(
        Output('current-page', 'data', allow_duplicate=True),
        Output('confidence-risk', 'data'),
        Input('confidence-risk-submit', 'n_clicks'),
        State('confidence-slider', 'value'),
        State('risk-slider', 'value'),
        State('attention-slider', 'value'),
        State('current-task', 'data'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def submit_confidence_risk(n_clicks, confidence, risk, attention_check, current_task, participant_id):
        """Handle confidence and risk assessment submission."""
        if not n_clicks:
            return dash.no_update, dash.no_update
        
        confidence_risk_data = {
            'confidence': confidence,
            'risk': risk,
            'attention_check': attention_check
        }
        
        if participant_id:
            # Completed task number (already incremented, so -1)
            completed_after_task = current_task - 1

            try:
                save_confidence_risk(participant_id, confidence, risk, attention_check_response=attention_check, completed_after_task=completed_after_task)
            except Exception:
                logger.exception("Error saving confidence/risk")
                return dash.no_update, dash.no_update

            try:
                log_event(
                    participant_id=participant_id,
                    event_type='confidence_risk_submit',
                    event_category='interaction',
                    page_name='confidence_risk',
                    element_id='confidence-risk-submit',
                    element_type='button',
                    action='submit',
                    metadata={'confidence': confidence, 'risk': risk, 'attention_check': attention_check, 'completed_after_task': completed_after_task}
                )
                # Navigate to next task or feedback
                next_task = current_task
                if current_task <= NUM_TASKS:
                    log_event(
                        participant_id=participant_id,
                        event_type='page_navigation',
                        event_category='navigation',
                        page_name='task',
                        task_id=next_task,
                        action='navigate'
                    )
                else:
                    log_event(
                        participant_id=participant_id,
                        event_type='page_navigation',
                        event_category='navigation',
                        page_name='feedback',
                        action='navigate'
                    )
            except Exception:
                logger.exception("Error logging event")
        
        # Navigate to task or feedback based on whether we've completed all tasks
        if current_task <= NUM_TASKS:
            return PAGES['task'], confidence_risk_data
        else:
            return PAGES['feedback'], confidence_risk_data
    
    
    @app.callback(
        Output('current-page', 'data', allow_duplicate=True),
        Output('feedback', 'data'),
        Output('completion-message', 'children'),
        Input('feedback-submit', 'n_clicks'),
        State('feedback-text', 'value'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def submit_feedback(n_clicks, feedback_text, participant_id):
        """Handle final feedback submission and navigate to debrief page."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update
        
        if participant_id:
            try:
                save_feedback(participant_id, feedback_text or "")
            except Exception:
                logger.exception("Error saving feedback")
                return dash.no_update, dash.no_update, "We couldn't save your feedback. Please try again."

            try:
                log_event(
                    participant_id=participant_id,
                    event_type='feedback_submit',
                    event_category='interaction',
                    page_name='feedback',
                    element_id='feedback-submit',
                    element_type='button',
                    action='submit',
                    metadata={'has_feedback': bool(feedback_text)}
                )
                log_event(
                    participant_id=participant_id,
                    event_type='page_navigation',
                    event_category='navigation',
                    page_name='debrief',
                    action='navigate'
                )
            except Exception:
                logger.exception("Error logging event")
        
        return PAGES['debrief'], feedback_text or "", ""
    
    
    @app.callback(
        Output('current-page', 'data', allow_duplicate=True),
        Output('debrief-message', 'children'),
        Input('debrief-submit', 'n_clicks'),
        State('withdrawal-choice', 'value'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def submit_debrief(n_clicks, withdrawal_choice, participant_id):
        """Handle debrief submission and data withdrawal option."""
        if not n_clicks:
            return dash.no_update, dash.no_update
        
        if participant_id:
            try:
                # Mark as completed (they finished the study)
                update_participant_completion(participant_id)
                
                # Update withdrawal status based on user choice
                if withdrawal_choice == 'yes':
                    update_participant_withdrawal(participant_id, withdrawn=True)
                else:
                    update_participant_withdrawal(participant_id, withdrawn=False)

                log_event(
                    participant_id=participant_id,
                    event_type='debrief_submit',
                    event_category='interaction',
                    page_name='debrief',
                    element_id='debrief-submit',
                    element_type='button',
                    action='submit',
                    metadata={'withdrawal_requested': withdrawal_choice == 'yes'}
                )

                if withdrawal_choice == 'yes':
                    log_event(
                        participant_id=participant_id,
                        event_type='data_withdrawal',
                        event_category='navigation',
                        page_name='debrief',
                        action='withdraw'
                    )

                log_event(
                    participant_id=participant_id,
                    event_type='study_completed',
                    event_category='navigation',
                    page_name='thank_you',
                    action='complete'
                )
            except Exception:
                logger.exception("Error completing study")
                return dash.no_update, "We couldn't save your completion status. Please try again."
        
        return PAGES['thank_you'], ""
