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

from config import PAGES, NUM_TASKS, CONFIDENCE_RISK_CHECKPOINT
from utils import (
    validate_investment, validate_total_investment, get_task_data_safe,
    validate_demographics, validate_page_access
)
from components import create_centered_card, create_error_alert
from pages import (
    consent_page, demographics_page, task_page, confidence_risk_page,
    feedback_page, thank_you_page
)


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
                
                # Create randomized task order
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
        Input('current-page', 'data'),
        State('current-task', 'data'),
        State('task-order', 'data'),
        State('amount', 'data'),
        State('consent-given', 'data'),
        State('demographics', 'data'),
        State('confidence-risk', 'data'),
        State('portfolio', 'data'),
        prevent_initial_call='initial_duplicate'
    )
    def display_page(page, current_task, task_order, amount, consent_given, demographics, confidence_risk, portfolio):
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
            return error_content, False, redirect_page
        
        # Always close modal when changing pages
        if page == PAGES['consent']:
            return consent_page(), False, dash.no_update
        elif page == PAGES['demographics']:
            return demographics_page(), False, dash.no_update
        elif page == PAGES['task']:
            # Use the randomized task order
            actual_task_id = task_order[current_task - 1] if task_order else current_task
            return task_page(actual_task_id, amount, sequential_task_num=current_task), False, dash.no_update
        elif page == PAGES['confidence_risk']:
            return confidence_risk_page(), False, dash.no_update
        elif page == PAGES['feedback']:
            return feedback_page(amount, portfolio or []), False, dash.no_update
        elif page == PAGES['thank_you']:
            return thank_you_page(), False, dash.no_update
        return html.Div("Page not found"), False, dash.no_update
    
    
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
                    page_name='task',
                    task_id=1,
                    action='navigate'
                )
            except Exception as e:
                print(f"Error saving demographics: {e}")
        
        return PAGES['task'], demographics_data, ""
    
    
    # ============================================
    # MODAL CALLBACKS
    # ============================================
    
    @app.callback(
        Output('stock-modal', 'is_open'),
        Output('modal-title', 'children'),
        Output('modal-body', 'children'),
        Output('modal-context', 'data'),
        Input({'type': 'show-more', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        Input('close-modal', 'n_clicks'),
        State('stock-modal', 'is_open'),
        State('current-task', 'data'),
        State('participant-id', 'data'),
        State('modal-context', 'data'),
        prevent_initial_call=True
    )
    def toggle_modal(show_clicks, close_clicks, is_open, current_task, participant_id, modal_context):
        """Handle opening/closing of stock details modal."""
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
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
            return False, "", "", {}
        
        if 'show-more' in triggered_id and ctx.triggered_id:
            button_id = ctx.triggered_id
            if not isinstance(button_id, dict):
                return dash.no_update, dash.no_update, dash.no_update
            
            if show_clicks and any(clicks and clicks > 0 for clicks in show_clicks if clicks is not None):
                task_id = button_id.get('task')
                stock_index = button_id.get('stock')
                
                if task_id is None or stock_index is None:
                    return dash.no_update, dash.no_update, dash.no_update
                
                task_data, error = get_task_data_safe(task_id)
                if error:
                    return True, "Error", html.P(error, className="text-danger")
                
                stock = task_data['stocks'][stock_index]
                
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
                            task_id=task_id,
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
                
                return True, stock['name'], html.Div(modal_content), modal_ctx
        
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    
    @app.callback(
        Output('stock-modal', 'is_open', allow_duplicate=True),
        Output('modal-title', 'children', allow_duplicate=True),
        Output('modal-body', 'children', allow_duplicate=True),
        Output('modal-context', 'data', allow_duplicate=True),
        Input({'type': 'show-week', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        State('current-task', 'data'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def show_week_analysis(week_clicks, current_task, participant_id):
        """Show weekly chart and analysis for a stock."""
        if not ctx.triggered or not ctx.triggered_id:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        button_id = ctx.triggered_id
        if not isinstance(button_id, dict):
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        if week_clicks and any(clicks and clicks > 0 for clicks in week_clicks if clicks is not None):
            task_id = button_id.get('task')
            stock_index = button_id.get('stock')
            
            if task_id is None or stock_index is None:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            task_data, error = get_task_data_safe(task_id)
            if error:
                return True, "Error", html.P(error, className="text-danger"), {}
            
            stock = task_data['stocks'][stock_index]
            
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
                        task_id=task_id,
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
            ]), modal_ctx
        
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    
    @app.callback(
        Output('stock-modal', 'is_open', allow_duplicate=True),
        Output('modal-title', 'children', allow_duplicate=True),
        Output('modal-body', 'children', allow_duplicate=True),
        Output('modal-context', 'data', allow_duplicate=True),
        Input({'type': 'show-month', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        State('current-task', 'data'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def show_month_analysis(month_clicks, current_task, participant_id):
        """Show monthly chart and analysis for a stock."""
        if not ctx.triggered or not ctx.triggered_id:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        button_id = ctx.triggered_id
        if not isinstance(button_id, dict):
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        if month_clicks and any(clicks and clicks > 0 for clicks in month_clicks if clicks is not None):
            task_id = button_id.get('task')
            stock_index = button_id.get('stock')
            
            if task_id is None or stock_index is None:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
            
            task_data, error = get_task_data_safe(task_id)
            if error:
                return True, "Error", html.P(error, className="text-danger"), {}
            
            stock = task_data['stocks'][stock_index]
            
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
                        task_id=task_id,
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
            ]), modal_ctx
        
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    
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
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
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
                return False, "", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, error
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
            return False, "", dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, error
        
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
        return True, modal_message, dash.no_update, next_task, new_amount, responses, portfolio, ""
    
    
    # Handle modal OK button - navigate to next page
    @app.callback(
        Output('result-modal', 'is_open', allow_duplicate=True),
        Output('current-page', 'data', allow_duplicate=True),
        Input('result-modal-ok', 'n_clicks'),
        State('current-task', 'data'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def handle_modal_ok(n_clicks, current_task, participant_id):
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
        
        # Route to next page based on completed task
        if completed_task == CONFIDENCE_RISK_CHECKPOINT:
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
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def submit_confidence_risk(n_clicks, confidence, risk, participant_id):
        """Handle confidence and risk assessment submission."""
        if not n_clicks:
            return dash.no_update, dash.no_update
        
        confidence_risk_data = {
            'confidence': confidence,
            'risk': risk
        }
        
        if participant_id:
            try:
                save_confidence_risk(participant_id, confidence, risk)
                log_event(
                    participant_id=participant_id,
                    event_type='confidence_risk_submit',
                    event_category='interaction',
                    page_name='confidence_risk',
                    element_id='confidence-risk-submit',
                    element_type='button',
                    action='submit',
                    metadata={'confidence': confidence, 'risk': risk}
                )
                log_event(
                    participant_id=participant_id,
                    event_type='page_navigation',
                    event_category='navigation',
                    page_name='task',
                    task_id=CONFIDENCE_RISK_CHECKPOINT + 1,
                    action='navigate'
                )
            except Exception as e:
                print(f"Error saving confidence/risk: {e}")
        
        return PAGES['task'], confidence_risk_data
    
    
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
