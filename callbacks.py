"""
Callback functions for the Stock Investment Study app.

This module contains all Dash callback functions that handle:
- Participant initialization
- Page navigation
- UI interactions
- Data collection and validation
- Modal displays
"""

import dash
from dash import html, ctx, Input, Output, State, ALL
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
                
                return str(new_participant_id)
            except Exception as e:
                print(f"Error creating participant: {e}")
                return None
        return participant_id or None
    
    
    # ============================================
    # PAGE NAVIGATION
    # ============================================
    
    @app.callback(
        Output('page-content', 'children'),
        Output('stock-modal', 'is_open', allow_duplicate=True),
        Output('current-page', 'data', allow_duplicate=True),
        Input('current-page', 'data'),
        State('current-task', 'data'),
        State('amount', 'data'),
        State('consent-given', 'data'),
        State('demographics', 'data'),
        State('confidence-risk', 'data'),
        State('portfolio', 'data'),
        prevent_initial_call='initial_duplicate'
    )
    def display_page(page, current_task, amount, consent_given, demographics, confidence_risk, portfolio):
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
            return task_page(current_task, amount), False, dash.no_update
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
        Input({'type': 'show-more', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        Input('close-modal', 'n_clicks'),
        State('stock-modal', 'is_open'),
        State('current-task', 'data'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def toggle_modal(show_clicks, close_clicks, is_open, current_task, participant_id):
        """Handle opening/closing of stock details modal."""
        if not ctx.triggered:
            return dash.no_update, dash.no_update, dash.no_update
        
        triggered_id = ctx.triggered[0]['prop_id']
        
        if 'close-modal' in triggered_id:
            if participant_id:
                try:
                    log_event(
                        participant_id=participant_id,
                        event_type='modal_close',
                        event_category='interaction',
                        page_name='task',
                        task_id=current_task,
                        element_id='close-modal',
                        element_type='button',
                        action='click'
                    )
                except Exception as e:
                    print(f"Error logging event: {e}")
            return False, "", ""
        
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
                
                if participant_id:
                    try:
                        log_event(
                            participant_id=participant_id,
                            event_type='modal_open',
                            event_category='interaction',
                            page_name='task',
                            task_id=task_id,
                            element_id=f'show-more-{stock_index}',
                            element_type='button',
                            action='click',
                            stock_ticker=stock['ticker'],
                            metadata={'stock_name': stock['name'], 'stock_index': stock_index}
                        )
                    except Exception as e:
                        print(f"Error logging event: {e}")
                
                return True, stock['name'], html.Div([
                    html.H5(f"{stock['ticker']}", className="text-muted mb-3"),
                    html.P(stock['detailed_description'])
                ])
        
        return dash.no_update, dash.no_update, dash.no_update
    
    
    @app.callback(
        Output('stock-modal', 'is_open', allow_duplicate=True),
        Output('modal-title', 'children', allow_duplicate=True),
        Output('modal-body', 'children', allow_duplicate=True),
        Input({'type': 'show-week', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        State('current-task', 'data'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def show_week_analysis(week_clicks, current_task, participant_id):
        """Show weekly chart and analysis for a stock."""
        if not ctx.triggered or not ctx.triggered_id:
            return dash.no_update, dash.no_update, dash.no_update
        
        button_id = ctx.triggered_id
        if not isinstance(button_id, dict):
            return dash.no_update, dash.no_update, dash.no_update
        
        if week_clicks and any(clicks and clicks > 0 for clicks in week_clicks if clicks is not None):
            task_id = button_id.get('task')
            stock_index = button_id.get('stock')
            
            if task_id is None or stock_index is None:
                return dash.no_update, dash.no_update, dash.no_update
            
            task_data, error = get_task_data_safe(task_id)
            if error:
                return True, "Error", html.P(error, className="text-danger")
            
            stock = task_data['stocks'][stock_index]
            
            if participant_id:
                try:
                    log_event(
                        participant_id=participant_id,
                        event_type='modal_open',
                        event_category='interaction',
                        page_name='task',
                        task_id=task_id,
                        element_id=f'show-week-{stock_index}',
                        element_type='button',
                        action='click',
                        stock_ticker=stock['ticker'],
                        metadata={'stock_name': stock['name'], 'stock_index': stock_index, 'view_type': 'week'}
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
            ])
        
        return dash.no_update, dash.no_update, dash.no_update
    
    
    @app.callback(
        Output('stock-modal', 'is_open', allow_duplicate=True),
        Output('modal-title', 'children', allow_duplicate=True),
        Output('modal-body', 'children', allow_duplicate=True),
        Input({'type': 'show-month', 'task': ALL, 'stock': ALL}, 'n_clicks'),
        State('current-task', 'data'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def show_month_analysis(month_clicks, current_task, participant_id):
        """Show monthly chart and analysis for a stock."""
        if not ctx.triggered or not ctx.triggered_id:
            return dash.no_update, dash.no_update, dash.no_update
        
        button_id = ctx.triggered_id
        if not isinstance(button_id, dict):
            return dash.no_update, dash.no_update, dash.no_update
        
        if month_clicks and any(clicks and clicks > 0 for clicks in month_clicks if clicks is not None):
            task_id = button_id.get('task')
            stock_index = button_id.get('stock')
            
            if task_id is None or stock_index is None:
                return dash.no_update, dash.no_update, dash.no_update
            
            task_data, error = get_task_data_safe(task_id)
            if error:
                return True, "Error", html.P(error, className="text-danger")
            
            stock = task_data['stocks'][stock_index]
            
            if participant_id:
                try:
                    log_event(
                        participant_id=participant_id,
                        event_type='modal_open',
                        event_category='interaction',
                        page_name='task',
                        task_id=task_id,
                        element_id=f'show-month-{stock_index}',
                        element_type='button',
                        action='click',
                        stock_ticker=stock['ticker'],
                        metadata={'stock_name': stock['name'], 'stock_index': stock_index, 'view_type': 'month'}
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
            ])
        
        return dash.no_update, dash.no_update, dash.no_update
    
    
    # ============================================
    # TASK SUBMISSION
    # ============================================
    
    @app.callback(
        Output('current-page', 'data', allow_duplicate=True),
        Output('current-task', 'data'),
        Output('amount', 'data'),
        Output('task-responses', 'data'),
        Output('portfolio', 'data'),
        Output('task-error', 'children'),
        Input('task-submit', 'n_clicks'),
        State({'type': 'investment-input', 'task': ALL, 'stock': ALL}, 'value'),
        State('current-task', 'data'),
        State('amount', 'data'),
        State('task-responses', 'data'),
        State('portfolio', 'data'),
        State('participant-id', 'data'),
        prevent_initial_call=True
    )
    def submit_task(n_clicks, investment_values, current_task, current_amount, responses, portfolio, participant_id):
        """Handle task submission with investment validation and portfolio tracking."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
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
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, error
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
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, error
        
        # Get task data
        task_data, task_error = get_task_data_safe(current_task)
        if task_error:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, task_error
        
        total_investment = sum(validated_investments)
        responses[f'task_{current_task}'] = {
            'investments': validated_investments,
            'total': total_investment
        }
        
        # Update portfolio
        if portfolio is None:
            portfolio = []
        
        for i, investment_amount in enumerate(validated_investments):
            if investment_amount > 0:
                stock = task_data['stocks'][i]
                return_percent = stock.get('return_percent', 0)
                final_value = investment_amount * (1 + return_percent / 100)
                
                portfolio_item = {
                    'task_id': current_task,
                    'stock_name': stock['name'],
                    'ticker': stock['ticker'],
                    'invested': investment_amount,
                    'return_percent': return_percent,
                    'final_value': final_value,
                    'profit_loss': final_value - investment_amount
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
                    stock_2_ticker=stocks[1]['ticker'],
                    stock_2_name=stocks[1]['name'],
                    stock_2_investment=validated_investments[1] if len(validated_investments) > 1 else 0,
                    total_investment=total_investment,
                    remaining_amount=new_amount
                )
                log_event(
                    participant_id=participant_id,
                    event_type='task_submit',
                    event_category='interaction',
                    page_name='task',
                    task_id=current_task,
                    element_id='task-submit',
                    element_type='button',
                    action='submit',
                    metadata={
                        'investments': validated_investments,
                        'total_investment': total_investment,
                        'remaining_amount': new_amount
                    }
                )
            except Exception as e:
                print(f"Error saving task response: {e}")
        
        next_task = current_task + 1
        
        # Route to next page
        if current_task == CONFIDENCE_RISK_CHECKPOINT:
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
            return PAGES['confidence_risk'], next_task, new_amount, responses, portfolio, ""
        
        if current_task == NUM_TASKS:
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
            return PAGES['feedback'], next_task, new_amount, responses, portfolio, ""
        
        if participant_id:
            try:
                log_event(
                    participant_id=participant_id,
                    event_type='page_navigation',
                    event_category='navigation',
                    page_name='task',
                    task_id=next_task,
                    action='navigate'
                )
            except Exception as e:
                print(f"Error logging event: {e}")
        return PAGES['task'], next_task, new_amount, responses, portfolio, ""
    
    
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
