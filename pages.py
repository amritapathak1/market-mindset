"""
Page rendering functions for the Stock Market Mindset app.

This module contains all page rendering functions that generate the UI
for different stages of the study: consent, demographics, tasks,
confidence/risk assessment, feedback, and thank you.
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from config import (
    INITIAL_AMOUNT, NUM_TASKS, CONFIDENCE_RISK_CHECKPOINT,
    SLIDER_CONFIG, GENDER_OPTIONS, EDUCATION_OPTIONS, EXPERIENCE_OPTIONS,
    MIN_AGE, MAX_AGE, COLORS
)
from utils import (
    get_task_data_safe, format_currency, format_percentage, calculate_profit_loss
)
from components import (
    create_page_header, create_centered_card, create_form_field,
    create_action_button, create_error_alert, create_success_alert,
    create_info_card, create_slider_with_labels, create_checkbox_field,
    create_text_area
)


def create_amount_display(amount):
    """Create a display showing the current available amount."""
    return dbc.Alert([
        html.H4([
            html.I(className="bi bi-wallet2 me-2"),
            f"Available Amount: ${amount:,.2f}"
        ], className="mb-0")
    ], color="success", className="text-center mb-4")


def create_stock_card(stock, stock_index, task_id):
    """Create a card displaying information about a single stock."""
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                # Daily image
                html.Img(src=stock.get('image', ''), style={'width': '100%', 'maxWidth': '150px', 'height': 'auto'}, 
                        className="mb-3 d-block mx-auto"),
                html.H4(stock['name'], className="text-center"),
                html.H6(f"Ticker: {stock['ticker']}", className="text-center text-muted mb-3"),
                
                html.P(stock['short_description'], className="text-muted mb-3"),
                
                # Three buttons for different time periods
                dbc.Button(
                    "Show More Details",
                    id={'type': 'show-more', 'task': task_id, 'stock': stock_index},
                    color="info",
                    outline=True,
                    size="sm",
                    className="w-100 mb-2"
                ),
                
                dbc.Button(
                    "Week's Chart & Analysis",
                    id={'type': 'show-week', 'task': task_id, 'stock': stock_index},
                    color="secondary",
                    outline=True,
                    size="sm",
                    className="w-100 mb-2"
                ),
                
                dbc.Button(
                    "Month's Chart & Analysis",
                    id={'type': 'show-month', 'task': task_id, 'stock': stock_index},
                    color="secondary",
                    outline=True,
                    size="sm",
                    className="w-100 mb-3"
                ),
                
                html.Hr(),
                
                dbc.Label(f"Amount to invest in {stock['name']}:"),
                dbc.InputGroup([
                    dbc.InputGroupText("$"),
                    dbc.Input(
                        id={'type': 'investment-input', 'task': task_id, 'stock': stock_index},
                        type="number",
                        min=0,
                        step=0.01,
                        placeholder="0.00",
                        value=0
                    )
                ])
            ])
        ])
    ])


def consent_page():
    """Render the consent form page."""
    content = [
        html.H4("Investment Decision Study", className="mb-3"),
        html.P([
            "Thank you for your interest in participating in this research study. ",
            "This study investigates how individuals make investment decisions when presented with stock information."
        ]),
        html.H5("Study Overview:", className="mt-3"),
        html.Ul([
            html.Li(f"Duration: Approximately 15-20 minutes"),
            html.Li("You will be asked to complete a brief demographic survey"),
            html.Li(f"You will make investment decisions across {NUM_TASKS} different scenarios"),
            html.Li(f"You will start with a virtual {format_currency(INITIAL_AMOUNT)}"),
            html.Li("You will be asked to rate your confidence and risk perception midway through"),
            html.Li("All data collected will be anonymous and used for research purposes only")
        ]),
        html.H5("Your Rights:", className="mt-3"),
        html.Ul([
            html.Li("Participation is completely voluntary"),
            html.Li("You may withdraw at any time without penalty"),
            html.Li("Your responses will be kept confidential"),
            html.Li("There are no known risks associated with this study")
        ]),
        html.Hr(),
        create_checkbox_field(
            "consent-checkbox",
            "I have read and understood the above information and consent to participate in this study"
        ),
        create_action_button("Continue to Study", "consent-submit", disabled=True),
        html.Div(id="consent-error", className="text-danger mt-2")
    ]
    
    return dbc.Container([
        create_page_header("Research Study Consent Form"),
        create_centered_card(content)
    ])


def demographics_page():
    """Render the demographics survey page."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1("Demographic Survey", className="text-center mb-4"),
                dbc.Card([
                    dbc.CardBody([
                        html.P("Please provide some basic information about yourself. This information helps us understand our participant pool."),
                        
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Age:"),
                                dbc.Input(id="age-input", type="number", min=MIN_AGE, max=MAX_AGE, placeholder="Enter your age")
                            ], md=6),
                            dbc.Col([
                                dbc.Label("Gender:"),
                                dbc.Select(
                                    id="gender-select",
                                    options=GENDER_OPTIONS,
                                    value=""
                                )
                            ], md=6)
                        ], className="mb-3"),
                        
                        dbc.Label("Education Level:"),
                        dbc.Select(
                            id="education-select",
                            options=EDUCATION_OPTIONS,
                            value="",
                            className="mb-3"
                        ),
                        
                        dbc.Label("Investment Experience:"),
                        dbc.Select(
                            id="experience-select",
                            options=EXPERIENCE_OPTIONS,
                            value="",
                            className="mb-3"
                        ),
                        
                        html.Div(id="demographics-error", className="text-danger mb-2"),
                        dbc.Button(
                            "Continue to Tasks",
                            id="demographics-submit",
                            color="primary",
                            size="lg",
                            className="w-100"
                        )
                    ])
                ])
            ], width=12, lg=8, className="mx-auto")
        ])
    ])


def task_page(task_id, amount):
    """Render the main investment task page for a given task number."""
    # Safely get task data
    task_data, error = get_task_data_safe(task_id)
    
    if error:
        return dbc.Container([
            dbc.Alert([
                html.H4("Error Loading Task", className="alert-heading"),
                html.P(error),
                html.Hr(),
                html.P("Please refresh the page or contact the study administrator.", className="mb-0")
            ], color=COLORS['danger'])
        ])
    
    stocks = task_data['stocks']
    
    return dbc.Container([
        create_amount_display(amount),
        
        html.H2(f"Investment Decision {task_id} of {NUM_TASKS}", className="text-center mb-4"),
        
        html.P("Review the two stocks below and decide how much to invest in each. You can invest in one, both, or neither.", 
               className="text-center text-muted mb-4"),
        
        dbc.Row([
            dbc.Col([
                create_stock_card(stocks[0], 0, task_id)
            ], md=6, className="mb-4"),
            dbc.Col([
                create_stock_card(stocks[1], 1, task_id)
            ], md=6, className="mb-4")
        ]),
        
        html.Div(id="task-error", className="text-danger text-center mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "Submit Investments",
                    id="task-submit",
                    color="primary",
                    size="lg",
                    className="w-100"
                )
            ], md=6, className="mx-auto")
        ])
    ])


def confidence_risk_page():
    """Render the confidence and risk assessment page."""
    conf_config = SLIDER_CONFIG['confidence']
    risk_config = SLIDER_CONFIG['risk']
    
    content = [
        html.P(f"You've completed {CONFIDENCE_RISK_CHECKPOINT} investment decisions. Please rate your confidence and risk perception."),
        
        html.H5("How confident are you in the investment decisions you've made so far?", className="mt-4 mb-3"),
        create_slider_with_labels(
            'confidence-slider',
            conf_config['min'],
            conf_config['max'],
            conf_config['default'],
            conf_config['step'],
            conf_config['label_min'],
            conf_config['label_max']
        ),
        
        html.H5("How would you rate the overall risk of your investment strategy?", className="mt-5 mb-3"),
        create_slider_with_labels(
            'risk-slider',
            risk_config['min'],
            risk_config['max'],
            risk_config['default'],
            risk_config['step'],
            risk_config['label_min'],
            risk_config['label_max']
        ),
        
        create_action_button("Continue", "confidence-risk-submit", className="mt-4")
    ]
    
    return dbc.Container([
        create_page_header("Confidence and Risk Assessment"),
        create_centered_card(content)
    ])


def feedback_page(uninvested_amount, portfolio):
    """Render the final feedback and results page with investment portfolio breakdown."""
    # Calculate total invested value (current worth of all investments)
    total_invested_original = sum(inv['invested'] for inv in portfolio)
    total_invested_current = sum(inv['final_value'] for inv in portfolio)
    total_profit_loss = total_invested_current - total_invested_original
    
    # Total final amount = uninvested + current portfolio value
    total_final_amount = uninvested_amount + total_invested_current
    overall_profit_loss = total_final_amount - INITIAL_AMOUNT
    overall_profit_loss_percent = (overall_profit_loss / INITIAL_AMOUNT) * 100 if INITIAL_AMOUNT > 0 else 0
    
    # Summary stats
    stats_row = dbc.Row([
        dbc.Col([
            create_info_card("Starting Amount", format_currency(INITIAL_AMOUNT))
        ], md=3),
        dbc.Col([
            create_info_card("Uninvested Cash", format_currency(uninvested_amount))
        ], md=3),
        dbc.Col([
            create_info_card(
                "Portfolio Value", 
                html.Div([
                    format_currency(total_invested_current),
                    html.Br(),
                    html.Small(f"({len(portfolio)} investments)", className="text-muted")
                ])
            )
        ], md=3),
        dbc.Col([
            create_info_card(
                "Total Amount",
                html.Div([
                    format_currency(total_final_amount),
                    html.Br(),
                    html.Small(
                        format_percentage(overall_profit_loss_percent),
                        className="text-muted",
                        style={'color': 'green' if overall_profit_loss >= 0 else 'red'}
                    )
                ], style={'color': 'green' if overall_profit_loss >= 0 else 'red'}),
                color=COLORS['primary'],
                outline=True
            )
        ], md=3)
    ])
    
    # Investment portfolio breakdown
    portfolio_table = None
    if portfolio:
        portfolio_rows = []
        for inv in portfolio:
            color = 'success' if inv['profit_loss'] >= 0 else 'danger'
            portfolio_rows.append(
                html.Tr([
                    html.Td(f"Task {inv['task_id']}"),
                    html.Td([html.Strong(inv['stock_name']), html.Br(), html.Small(inv['ticker'], className="text-muted")]),
                    html.Td(format_currency(inv['invested']), className="text-end"),
                    html.Td(
                        f"{inv['return_percent']:+.1f}%",
                        className="text-end",
                        style={'color': 'green' if inv['return_percent'] >= 0 else 'red'}
                    ),
                    html.Td(format_currency(inv['final_value']), className="text-end"),
                    html.Td(
                        format_currency(inv['profit_loss']) if inv['profit_loss'] < 0 else f"+{format_currency(inv['profit_loss'])[1:]}",
                        className=f"text-end text-{color}",
                        style={'fontWeight': 'bold'}
                    )
                ])
            )
        
        portfolio_table = html.Div([
            html.H5("Investment Portfolio Breakdown", className="mt-4 mb-3"),
            dbc.Table([
                html.Thead(html.Tr([
                    html.Th("Task"),
                    html.Th("Stock"),
                    html.Th("Invested", className="text-end"),
                    html.Th("Return %", className="text-end"),
                    html.Th("Current Value", className="text-end"),
                    html.Th("Profit/Loss", className="text-end")
                ])),
                html.Tbody(portfolio_rows),
                html.Tfoot(html.Tr([
                    html.Th("Total", colSpan=2),
                    html.Th(format_currency(total_invested_original), className="text-end"),
                    html.Th(""),
                    html.Th(format_currency(total_invested_current), className="text-end"),
                    html.Th(
                        format_currency(total_profit_loss) if total_profit_loss < 0 else f"+{format_currency(total_profit_loss)[1:]}",
                        className=f"text-end",
                        style={'fontWeight': 'bold', 'color': 'green' if total_profit_loss >= 0 else 'red'}
                    )
                ], style={'borderTop': '2px solid #dee2e6'}))
            ], bordered=True, hover=True, responsive=True, striped=True, size='sm')
        ])
    
    content = [
        html.H3("Final Results", className="text-center mb-4"),
        stats_row,
        portfolio_table if portfolio_table else html.Div(),
        html.Hr(className="my-4"),
        html.H5("Feedback (Optional)", className="mb-3"),
        html.P("Please share any thoughts about your experience in this study:"),
        create_text_area("feedback-text", "Enter your feedback here..."),
        create_action_button("Submit and Finish", "feedback-submit", color=COLORS['success']),
        html.Div(id="completion-message", className="text-center mt-3")
    ]
    
    return dbc.Container([
        create_page_header("Study Complete - Thank You!"),
        create_centered_card(content)
    ])


def thank_you_page():
    """Render the final thank you page."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="bi bi-check-circle", style={'fontSize': '5rem', 'color': 'green'}),
                    html.H1("Thank You!", className="mt-3 mb-4"),
                    html.P("Your responses have been recorded. We appreciate your participation in this study.", 
                           className="lead"),
                    html.P("You may now close this window.", className="text-muted")
                ], className="text-center", style={'marginTop': '100px'})
            ], width=12)
        ])
    ])
