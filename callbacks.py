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
from flask import request

from config import PAGES, NUM_TASKS, NUM_TUTORIAL_TASKS, CONFIDENCE_RISK_CHECKPOINTS
from utils import (
    validate_investment, validate_total_investment, get_task_data_safe,
    validate_demographics, validate_page_access
)
from components import create_centered_card, create_error_alert
from pages import (
    consent_page, demographics_page, tutorial_page, task_page, confidence_risk_page,
    feedback_page, thank_you_page
)

# Import INFO_COSTS and INITIAL_AMOUNT for cost confirmation and amount display
from config import INFO_COSTS, INITIAL_AMOUNT


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
    
    DB_ENABLED = db_enabled
    
    # ============================================
    # INITIALIZATION CALLBACK
    # ============================================
    
    @app.callback(
        Output('participant-id', 'data'),
        Output('task-order', 'data'),
        Input('participant-id', 'data')
    )
    def initialize_participant(participant_id):
        """Create new participant on first load."""
        if participant_id is None:
            try:
                # Get client info
                ip_address = request.remote_addr if request else None
                user_agent = request.headers.get('User-Agent') if request else None
                
                if DB_ENABLED:
                    # Create new participant in database (no session tracking)
                    new_participant_id = create_participant(
                        session_id=None,  # Not using sessions
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                else:
                    # Create participant ID for file-based logging
                    new_participant_id = create_participant()
                
                # Log initial event
                if new_participant_id:
                    log_event(
                        participant_id=new_participant_id,
                        event_type='session_start',
                        event_category='navigation',
                        page_name='consent',
                        action='load'
                    )
                
                # Create randomized task order for main tasks only
                import random
                task_order = list(range(1, NUM_TASKS + 1))
                random.shuffle(task_order)
                
                return str(new_participant_id), task_order
            except Exception as e:
                print(f"Error creating participant: {e}")
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
        State('current-task', 'data'),
        State('task-order', 'data'),
        State('amount', 'data'),
        State('consent-given', 'data'),
        State('demographics', 'data'),
        State('confidence-risk', 'data'),
        State('portfolio', 'data'),
        State('info-cost-spent', 'data'),
        prevent_initial_call='initial_duplicate'
    )
    def display_page(page, current_task, task_order, amount, consent_given, demographics, confidence_risk, portfolio, info_spent):
        """Display the appropriate page based on current page state with flow validation."""
        # Validate page access
        demographics_completed = bool(demographics and demographics.get('age'))
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
            return tutorial_page(1, amount), False, dash.no_update, {}
        elif page == PAGES['tutorial_2']:
            return tutorial_page(2, amount), False, dash.no_update, {}
        elif page == PAGES['task']:
            # Use the randomized task order
            actual_task_id = task_order[current_task - 1] if task_order else current_task
            return task_page(actual_task_id, amount, sequential_task_num=current_task), False, dash.no_update, {}
        elif page == PAGES['confidence_risk']:
            # Calculate number of completed main tasks (excluding tutorials)
            completed_main_tasks = max(0, current_task - 1)
            return confidence_risk_page(completed_tasks=completed_main_tasks), False, dash.no_update, {}
        elif page == PAGES['feedback']:
            return feedback_page(amount, portfolio or [], info_spent or 0), False, dash.no_update, {}
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
            except Exception as e:
                print(f"Error logging event: {e}")
        
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
                except Exception as e:
                    print(f"Error logging event: {e}")
            
            return PAGES['demographics'], True
        return dash.no_update, dash.no_update
    
    
    # ============================================
    # DATA COLLECTION
    # ============================================
    
    @app.callback(
        Output('current-page', 'data', allow_duplicate=True),
        Output('demographics', 'data'),
        Output('demographics-error', 'children'),
        Input('demographics-submit', 'n_clicks'),
        State('age-input', 'value'),
        State('gender-select', 'value'),
        State('education-select', 'value'),
        State('experience-select', 'value'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def submit_demographics(n_clicks, age, gender, education, experience, participant_id):
        """Handle demographics form submission with validation."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update
        
        # Validate
        is_valid, error, demographics_data = validate_demographics(age, gender, education, experience)
        
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
                except Exception as e:
                    print(f"Error logging event: {e}")
            return dash.no_update, dash.no_update, error
        
        # Save
        if participant_id:
            try:
                save_demographics(participant_id, age, gender, education, experience)
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
            except Exception as e:
                print(f"Error saving demographics: {e}")
        
        return PAGES['tutorial_1'], demographics_data, ""
    
    
    # ============================================
    # COST CONFIRMATION CALLBACKS
    # ============================================
    
    @app.callback(
        Output('cost-modal', 'is_open'),
        Output('cost-modal-body', 'children'),
        Output('pending-info-request', 'data'),
        Input({'type': 'show-more', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        Input({'type': 'show-week', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        Input({'type': 'show-month', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        Input('cost-modal-cancel', 'n_clicks'),
        State('pending-info-request', 'data'),
        State('current-task', 'data'),
        State('participant-id', 'data'),
        State('purchased-info', 'data'),
        prevent_initial_call=True
    )
    def handle_cost_confirmation(show_more_clicks, show_week_clicks, show_month_clicks, 
                                  cancel_clicks, pending_request, current_task, participant_id, purchased_info):
        """Handle cost confirmation modal for information requests."""
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
        
        triggered_id = ctx.triggered[0]['prop_id']
        button_id = ctx.triggered_id
        
        # CRITICAL: Check that something was actually clicked (not just component rendered)
        if not button_id or (isinstance(button_id, dict) and not any([
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
                except Exception as e:
                    print(f"Error logging event: {e}")
            return False, "", {}
        
        # Handle information request buttons
        if isinstance(button_id, dict):
            info_type = button_id.get('type')
            task_id = button_id.get('task')
            stock_index = button_id.get('stock')
            
            if info_type in ['show-more', 'show-week', 'show-month']:
                # Get task data to retrieve stock info
                task_data, error = get_task_data_safe(task_id)
                if error:
                    return False, "", {}
                
                stock = task_data['stocks'][stock_index]
                
                # Get cost from stock data
                cost_key = info_type.replace('-', '_')
                cost = stock.get('info_costs', {}).get(cost_key, 0)
                
                # Check if this info has already been purchased for current task
                info_identifier = f'{info_type}-{stock_index}'
                already_purchased = info_identifier in (purchased_info or [])
                
                # If already purchased, treat as free
                if already_purchased:
                    cost = 0
                
                # Determine info type label
                info_type_labels = {
                    'show-more': 'Additional Details',
                    'show-week': "Week's Chart & Analysis",
                    'show-month': "Month's Chart & Analysis"
                }
                info_label = info_type_labels.get(info_type, 'Information')
                
                # Log the initial request
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
                                'cost': cost,
                                'info_type': info_type,
                                'stock_name': stock['name'],
                                'stock_index': stock_index
                            }
                        )
                    except Exception as e:
                        print(f"Error logging event: {e}")
                
                # Create pending request
                pending = {
                    'info_type': info_type,
                    'task_id': task_id,
                    'stock_index': stock_index,
                    'stock_ticker': stock['ticker'],
                    'stock_name': stock['name'],
                    'cost': cost,
                    'element_id': f'{info_type}-{stock_index}'
                }
                
                # If cost is $0, skip the confirmation modal - directly store pending request
                if cost == 0:
                    return False, "", pending
                
                # Create modal body for non-zero cost
                modal_body = html.Div([
                    html.P([
                        f"Viewing {info_label} for ",
                        html.Strong(stock['name']),
                        f" ({stock['ticker']}) will cost ",
                        html.Strong(f"${cost:.2f}"),
                        "."
                    ], className="mb-3"),
                    html.P("Do you want to proceed?", className="mb-0")
                ])
                
                return True, modal_body, pending
        
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
        prevent_initial_call=True
    )
    def toggle_modal(ok_clicks, close_clicks, pending_request, is_open, current_task, task_order, participant_id, modal_context, current_amount, info_spent, purchased_info, current_page):
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
                except Exception as e:
                    print(f"Error logging event: {e}")
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
                        print(f"DEBUG: Task ID mismatch for free info - pending task_id={task_id}, actual_task_id={actual_task_id}")
                        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, {}, dash.no_update, dash.no_update, dash.no_update, dash.no_update
                
                if task_id is None or stock_index is None:
                    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, {}, dash.no_update, dash.no_update, dash.no_update, dash.no_update
                
                task_data, error = get_task_data_safe(task_id)
                if error:
                    return True, "Error", html.P(error, className="text-danger"), {}, {}, dash.no_update, dash.no_update, dash.no_update, dash.no_update
                
                stock = task_data['stocks'][stock_index]
                
                # Add to purchased list
                info_identifier = f'{info_type}-{stock_index}'
                updated_purchased = list(purchased_info or [])
                if info_identifier not in updated_purchased:
                    updated_purchased.append(info_identifier)
                
                # Don't log acceptance for free information (cost = 0)
                
                # Handle different info types (same logic as OK button handler)
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
                        except Exception as e:
                            print(f"Error logging event: {e}")
                    
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
                    
                    return True, stock['name'], html.Div(modal_content), modal_ctx, dash.no_update, False, current_amount, info_spent, updated_purchased
                
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
                        except Exception as e:
                            print(f"Error logging event: {e}")
                    
                    return True, f"{stock['name']} - Weekly Analysis", html.Div([
                        html.H5(f"{stock['ticker']}", className="text-muted mb-3"),
                        html.Img(
                            src=stock.get('week_image', 'https://via.placeholder.com/600x300?text=Weekly+Chart'),
                            style={'width': '100%', 'maxWidth': '600px'},
                            className="mb-3 d-block mx-auto"
                        ),
                        html.H6("Weekly Performance Analysis", className="mb-2"),
                        html.P(stock.get('week_analysis', 'Weekly performance data for this stock.'))
                    ]), modal_ctx, dash.no_update, False, current_amount, info_spent, updated_purchased
                
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
                        except Exception as e:
                            print(f"Error logging event: {e}")
                    
                    return True, f"{stock['name']} - Monthly Analysis", html.Div([
                        html.H5(f"{stock['ticker']}", className="text-muted mb-3"),
                        html.Img(
                            src=stock.get('month_image', 'https://via.placeholder.com/600x300?text=Monthly+Chart'),
                            style={'width': '100%', 'maxWidth': '600px'},
                            className="mb-3 d-block mx-auto"
                        ),
                        html.H6("Monthly Performance Analysis", className="mb-2"),
                        html.P(stock.get('month_analysis', 'Monthly performance data for this stock.'))
                    ]), modal_ctx, dash.no_update, False, current_amount, info_spent, updated_purchased
        
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
                except Exception as e:
                    print(f"Error logging event: {e}")
            
            info_type = pending_request.get('info_type')
            task_id = pending_request.get('task_id')
            stock_index = pending_request.get('stock_index')
            
            # Validate task ID - skip validation for tutorial tasks
            if not str(task_id).startswith('tutorial_'):
                # Get the actual task ID for current task from randomized order
                actual_task_id = task_order[current_task - 1] if task_order else current_task
                
                # Validate that pending request matches current task - prevents stale data issues
                if task_id != actual_task_id:
                    print(f"DEBUG: Task ID mismatch - pending task_id={task_id}, actual_task_id={actual_task_id}")
                    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, {}, False, dash.no_update, dash.no_update, dash.no_update
            
            if task_id is None or stock_index is None:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, {}, False, dash.no_update, dash.no_update, dash.no_update
            
            task_data, error = get_task_data_safe(task_id)
            if error:
                return True, "Error", html.P(error, className="text-danger"), {}, dash.no_update, False, dash.no_update, dash.no_update, dash.no_update
            
            stock = task_data['stocks'][stock_index]
            
            # Add to purchased list
            info_identifier = f'{info_type}-{stock_index}'
            updated_purchased = list(purchased_info or [])
            if info_identifier not in updated_purchased:
                updated_purchased.append(info_identifier)
            
            # Handle show-more
            if info_type == 'show-more':
                # Store modal context for close event
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
                    except Exception as e:
                        print(f"Error logging event: {e}")
                
                # Build modal body content
                modal_content = [
                    html.H5(f"{stock['ticker']}", className="text-muted mb-3"),
                    html.P(stock['detailed_description'])
                ]
                
                # Add performance metrics table if available
                if 'performance_metrics' in stock:
                    metrics = stock['performance_metrics']
                    modal_content.append(html.Hr(className="my-4"))
                    modal_content.append(html.H5("Performance Metrics", className="mb-3"))
                    modal_content.append(
                        dbc.Table([
                            html.Tbody([
                                html.Tr([
                                    html.Td("5-day", style={'fontWeight': 'bold', 'width': '40%'}),
                                    html.Td(metrics.get('5-day', 'N/A'), style={'textAlign': 'right'})
                                ]),
                                html.Tr([
                                    html.Td("10-day", style={'fontWeight': 'bold'}),
                                    html.Td(metrics.get('10-day', 'N/A'), style={'textAlign': 'right'})
                                ]),
                                html.Tr([
                                    html.Td("1-month", style={'fontWeight': 'bold'}),
                                    html.Td(metrics.get('1-month', 'N/A'), style={'textAlign': 'right'})
                                ]),
                                html.Tr([
                                    html.Td("3-month", style={'fontWeight': 'bold'}),
                                    html.Td(metrics.get('3-month', 'N/A'), style={'textAlign': 'right'})
                                ]),
                                html.Tr([
                                    html.Td("6-month", style={'fontWeight': 'bold'}),
                                    html.Td(metrics.get('6-month', 'N/A'), style={'textAlign': 'right'})
                                ]),
                                html.Tr([
                                    html.Td("YTD", style={'fontWeight': 'bold'}),
                                    html.Td(metrics.get('YTD', 'N/A'), style={'textAlign': 'right'})
                                ])
                            ])
                        ], bordered=True, hover=True, striped=True, className="mb-0")
                    )
                
                # Don't clear pending_request here - let it be cleared when modal closes or page changes
                # Close cost modal and open info modal, deduct cost from amount
                return True, stock['name'], html.Div(modal_content), modal_ctx, dash.no_update, False, new_amount, new_info_spent, updated_purchased
            
            # Handle show-week
            elif info_type == 'show-week':
                # Store modal context for close event
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
                    except Exception as e:
                        print(f"Error logging event: {e}")
                
                return True, f"{stock['name']} - Weekly Analysis", html.Div([
                    html.H5(f"{stock['ticker']}", className="text-muted mb-3"),
                    html.Img(
                        src=stock.get('week_image', 'https://via.placeholder.com/600x300?text=Weekly+Chart'),
                        style={'width': '100%', 'maxWidth': '600px'},
                        className="mb-3 d-block mx-auto"
                    ),
                    html.H6("Weekly Performance Analysis", className="mb-2"),
                    html.P(stock.get('week_analysis', 'Weekly performance data for this stock.'))
                ]), modal_ctx, dash.no_update, False, new_amount, new_info_spent, updated_purchased
            
            # Handle show-month
            elif info_type == 'show-month':
                # Store modal context for close event
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
                    except Exception as e:
                        print(f"Error logging event: {e}")
                
                return True, f"{stock['name']} - Monthly Analysis", html.Div([
                    html.H5(f"{stock['ticker']}", className="text-muted mb-3"),
                    html.Img(
                        src=stock.get('month_image', 'https://via.placeholder.com/600x300?text=Monthly+Chart'),
                        style={'width': '100%', 'maxWidth': '600px'},
                        className="mb-3 d-block mx-auto"
                    ),
                    html.H6("Monthly Performance Analysis", className="mb-2"),
                    html.P(stock.get('month_analysis', 'Monthly performance data for this stock.'))
                ]), modal_ctx, dash.no_update, False, new_amount, new_info_spent, updated_purchased
        
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
        prevent_initial_call=True
    )
    def reset_tutorial_1_button(current_page):
        """Ensure tutorial 1 button starts disabled and reset purchased info."""
        if current_page == PAGES['tutorial_1']:
            return True, []  # Reset purchased-info to empty list
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
        prevent_initial_call=True
    )
    def enable_tutorial_1_button(modal_is_open, current_page, purchased_info):
        """Enable tutorial 1 button after viewing info."""
        # Only act on tutorial 1 page
        if current_page != PAGES['tutorial_1']:
            return dash.no_update, dash.no_update
        
        # Check if modal just closed AND user has viewed at least one piece of info
        if not modal_is_open and purchased_info and len(purchased_info) > 0:
            return False, dbc.Alert([
                html.I(className="bi bi-check-circle me-2"),
                "Great! You've learned how to view information. Now enter an investment amount and click Continue."
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
        prevent_initial_call=True
    )
    def submit_tutorial_1(n_clicks, investment_values, current_amount, participant_id):
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
        task_data, task_error = get_task_data_safe('tutorial_1')
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
        
        # Create result modal content
        profit_loss_color = 'success' if total_profit_loss >= 0 else 'warning'
        result_content = dbc.Alert([
            html.H5([html.I(className="bi bi-check-circle me-2"), "Tutorial 1 Complete!"], className="mb-3"),
            html.Hr(),
            html.H6("Your Practice Result:", className="mb-2"),
            html.P(f"Investment: ${total_investment:,.2f}", className="mb-1"),
            html.P([
                "Result: ",
                html.Span(f"${total_profit_loss:+,.2f}", 
                         style={'color': 'green' if total_profit_loss >= 0 else 'red', 
                                'fontWeight': 'bold'}),
                " (" + ("Profit" if total_profit_loss >= 0 else "Loss") + ")"
            ], className="mb-3"),
            html.Hr(),
            html.P([
                html.I(className="bi bi-lightbulb me-2"),
                "In the actual study, you'll see results like this after each investment. "
                "Your goal is to maximize your final amount through strategic investments."
            ], className="text-muted small mb-0")
        ], color=profit_loss_color)
        
        if participant_id:
            try:
                log_event(
                    participant_id=participant_id,
                    event_type='tutorial_submit',
                    event_category='interaction',
                    page_name='tutorial_1',
                    element_id='tutorial-1-submit',
                    action='submit',
                    metadata={'investment': total_investment, 'profit_loss': total_profit_loss}
                )
            except Exception as e:
                print(f"Error logging tutorial: {e}")
        
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
            except Exception as e:
                print(f"Error logging event: {e}")
        
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
        prevent_initial_call=True
    )
    def submit_tutorial_2(n_clicks, investment_values, current_amount, participant_id):
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
        task_data, task_error = get_task_data_safe('tutorial_2')
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
        
        # Create result modal content
        profit_loss_color = 'success' if total_profit_loss >= 0 else 'warning'
        result_content = dbc.Alert([
            html.H5([html.I(className="bi bi-trophy me-2"), "Tutorial Complete - Ready to Begin!"], className="mb-3"),
            html.Hr(),
            html.H6("Your Practice Result:", className="mb-2"),
            html.P(f"Investment: ${total_investment:,.2f}", className="mb-1"),
            html.P([
                "Result: ",
                html.Span(f"${total_profit_loss:+,.2f}", 
                         style={'color': 'green' if total_profit_loss >= 0 else 'red', 
                                'fontWeight': 'bold'}),
                " (" + ("Profit" if total_profit_loss >= 0 else "Loss") + ")"
            ], className="mb-3"),
            html.Hr(),
            html.Div([
                html.P([html.Strong("You're now ready for the main study!")], className="mb-2"),
                html.P([
                    html.I(className="bi bi-info-circle me-2"),
                    "From this point forward, your investment decisions will be recorded. "
                    "Remember: you can view additional information (at a cost) or make decisions based on the basic information provided."
                ], className="text-muted small mb-0")
            ])
        ], color="primary")
        
        if participant_id:
            try:
                log_event(
                    participant_id=participant_id,
                    event_type='tutorial_submit',
                    event_category='interaction',
                    page_name='tutorial_2',
                    element_id='tutorial-2-submit',
                    action='submit',
                    metadata={'investment': total_investment, 'profit_loss': total_profit_loss}
                )
            except Exception as e:
                print(f"Error logging tutorial: {e}")
        
        # Deduct investment from amount
        new_amount = current_amount - total_investment
        return True, result_content, "", new_amount
    
    
    @app.callback(
        Output('current-page', 'data', allow_duplicate=True),
        Output('tutorial-completed', 'data'),
        Output('amount', 'data', allow_duplicate=True),
        Input('tutorial-2-result-ok', 'n_clicks'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def tutorial_2_next(n_clicks, participant_id):
        """Navigate from tutorial 2 to first main task and reset amount to $1000."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update
        
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
            except Exception as e:
                print(f"Error logging event: {e}")
        
        return PAGES['task'], True, INITIAL_AMOUNT
    
    
    # ============================================
    # TASK SUBMISSION
    # ============================================
    
    @app.callback(
        Output('result-modal', 'is_open'),
        Output('result-modal-body', 'children'),
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
        prevent_initial_call=True
    )
    def submit_task(n_clicks, investment_values, current_task, task_order, current_amount, responses, portfolio, participant_id):
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
                    except Exception as e:
                        print(f"Error logging event: {e}")
                return False, "", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, error, dash.no_update
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
                except Exception as e:
                    print(f"Error logging event: {e}")
            return False, "", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, error, dash.no_update
        
        # Get task data using the actual randomized task ID
        task_data, task_error = get_task_data_safe(actual_task_id)
        if task_error:
            return False, "", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, task_error
        
        total_investment = sum(validated_investments)
        responses[f'task_{current_task}'] = {
            'investments': validated_investments,
            'total': total_investment
        }
        
        # Update portfolio and calculate profit/loss
        if portfolio is None:
            portfolio = []
        
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
                portfolio.append(portfolio_item)
                
                if participant_id:
                    try:
                        save_portfolio_investment(
                            participant_id=participant_id,
                            task_id=current_task,
                            stock_name=stock['name'],
                            ticker=stock['ticker'],
                            invested_amount=investment_amount,
                            return_percent=return_percent,
                            final_value=final_value,
                            profit_loss=final_value - investment_amount
                        )
                    except Exception as e:
                        print(f"Error saving portfolio: {e}")
        
        new_amount = current_amount - total_investment
        
        # Save task response
        if participant_id:
            try:
                stocks = task_data['stocks']
                save_task_response(
                    participant_id=participant_id,
                    task_id=current_task,
                    stock_1_ticker=stocks[0]['ticker'],
                    stock_1_name=stocks[0]['name'],
                    stock_1_investment=validated_investments[0] if len(validated_investments) > 0 else 0,
                    stock_2_ticker=stocks[0]['ticker'] if len(stocks) > 1 else "",
                    stock_2_name=stocks[0]['name'] if len(stocks) > 1 else "",
                    stock_2_investment=0,
                    total_investment=total_investment,
                    remaining_amount=new_amount
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
                        'profit_loss': total_profit_loss
                    }
                )
            except Exception as e:
                print(f"Error saving task response: {e}")
        
        # Determine profit/loss message
        if total_investment == 0:
            modal_message = "You did not invest in this task."
        elif total_profit_loss > 0:
            modal_message = "Your investment made a profit! 📈"
        elif total_profit_loss < 0:
            modal_message = "Your investment made a loss. 📉"
        else:
            modal_message = "Your investment broke even."
        
        next_task = current_task + 1
        
        # Route to next page - but first show the modal
        # We're not changing the page yet, the modal OK button will do that
        # Clear purchased-info for next task
        return True, modal_message, dash.no_update, next_task, new_amount, responses, portfolio, "", []
    
    
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
        """Handle modal OK button click and navigate to appropriate next page."""
        if not n_clicks:
            return dash.no_update, dash.no_update
        
        # current_task has already been incremented in submit_task
        # So current_task - 1 is the task that was just completed
        completed_task = current_task - 1
        
        # Log the modal OK button click
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
            except Exception as e:
                print(f"Error logging event: {e}")
        
        # Route to next page based on completed task number
        if completed_task in CONFIDENCE_RISK_CHECKPOINTS:
            if participant_id:
                try:
                    log_event(
                        participant_id=participant_id,
                        event_type='page_navigation',
                        event_category='navigation',
                        page_name='confidence_risk',
                        action='navigate'
                    )
                except Exception as e:
                    print(f"Error logging event: {e}")
            return False, PAGES['confidence_risk']
        
        if completed_task == NUM_TASKS:
            if participant_id:
                try:
                    log_event(
                        participant_id=participant_id,
                        event_type='page_navigation',
                        event_category='navigation',
                        page_name='feedback',
                        action='navigate'
                    )
                except Exception as e:
                    print(f"Error logging event: {e}")
            return False, PAGES['feedback']
        
        # Continue to next task
        if participant_id:
            try:
                log_event(
                    participant_id=participant_id,
                    event_type='page_navigation',
                    event_category='navigation',
                    page_name='task',
                    task_id=current_task,
                    action='navigate'
                )
            except Exception as e:
                print(f"Error logging event: {e}")
        return False, PAGES['task']
    
    
    # ============================================
    # CONFIDENCE/RISK & FEEDBACK
    # ============================================
    
    @app.callback(
        Output('current-page', 'data', allow_duplicate=True),
        Output('confidence-risk', 'data'),
        Input('confidence-risk-submit', 'n_clicks'),
        State('confidence-slider', 'value'),
        State('risk-slider', 'value'),
        State('current-task', 'data'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def submit_confidence_risk(n_clicks, confidence, risk, current_task, participant_id):
        """Handle confidence and risk assessment submission."""
        if not n_clicks:
            return dash.no_update, dash.no_update
        
        confidence_risk_data = {
            'confidence': confidence,
            'risk': risk
        }
        
        if participant_id:
            try:
                # Completed task number (already incremented, so -1)
                completed_after_task = current_task - 1
                save_confidence_risk(participant_id, confidence, risk, completed_after_task=completed_after_task)
                log_event(
                    participant_id=participant_id,
                    event_type='confidence_risk_submit',
                    event_category='interaction',
                    page_name='confidence_risk',
                    element_id='confidence-risk-submit',
                    element_type='button',
                    action='submit',
                    metadata={'confidence': confidence, 'risk': risk, 'completed_after_task': completed_after_task}
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
            except Exception as e:
                print(f"Error saving confidence/risk: {e}")
        
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
        """Handle final feedback submission."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update
        
        if participant_id:
            try:
                save_feedback(participant_id, feedback_text or "")
                update_participant_completion(participant_id, completed=True)
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
                    event_type='study_completed',
                    event_category='navigation',
                    page_name='thank_you',
                    action='complete'
                )
            except Exception as e:
                print(f"Error saving feedback: {e}")
        
        return PAGES['thank_you'], feedback_text or "", ""
