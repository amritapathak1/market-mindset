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
    INITIAL_AMOUNT, NUM_TASKS, NUM_TUTORIAL_TASKS, CONFIDENCE_RISK_CHECKPOINTS,
    SLIDER_CONFIG, GENDER_OPTIONS, EDUCATION_OPTIONS, EXPERIENCE_OPTIONS,
    AGE_RANGE_OPTIONS, INCOME_OPTIONS, HISPANIC_LATINO_OPTIONS, RACE_OPTIONS,
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


def create_stock_card(stock, stock_index, task_id, amount=None):
    """Create a card displaying information about a single stock."""
    
    return dbc.Card([
        dbc.CardBody([
            # Header - Company name and ticker
            html.Div([
                html.H4(stock['name'], className="text-center"),
                html.H6(f"Ticker: {stock['ticker']}", className="text-center text-muted mb-3"),
                html.P(stock['short_description'], className="text-muted mb-4 text-center"),
            ]),
            
            # Two column layout
            dbc.Row([
                # Left column - Image
                dbc.Col([
                    html.Img(src=stock.get('image', ''), style={'width': '100%', 'height': 'auto'}, 
                            className="d-block")
                ], md=6),
                
                # Right column - Buttons and inputs
                dbc.Col([
                    # Purchase information button
                    dbc.Button(
                        "Purchase Information",
                        id={'type': 'purchase-info', 'task': task_id, 'stock': stock_index},
                        color="primary",
                        size="sm",
                        className="w-100 mb-3"
                    ),
                    
                    # Three buttons for different time periods (disabled by default)
                    dbc.Button(
                        "Show More Details",
                        id={'type': 'show-more', 'task': task_id, 'stock': stock_index},
                        color="info",
                        outline=True,
                        size="sm",
                        className="w-100 mb-2",
                        disabled=True
                    ),
                    
                    dbc.Button(
                        "Week's Chart & Analysis",
                        id={'type': 'show-week', 'task': task_id, 'stock': stock_index},
                        color="secondary",
                        outline=True,
                        size="sm",
                        className="w-100 mb-2",
                        disabled=True
                    ),
                    
                    dbc.Button(
                        "Month's Chart & Analysis",
                        id={'type': 'show-month', 'task': task_id, 'stock': stock_index},
                        color="secondary",
                        outline=True,
                        size="sm",
                        className="w-100 mb-3",
                        disabled=True
                    ),
                    
                    html.Hr(),
                    
                    # Available amount display - made reactive with ID
                    html.H5([
                        html.I(className="bi bi-wallet2 me-2"),
                        f"Available: ${amount:,.2f}" if amount is not None else "Available: $0.00"
                    ],
                        id={'type': 'amount-display', 'task': task_id, 'stock': stock_index},
                        className="text-success mb-3"
                    ),
                    
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
                ], md=6)
            ])
        ])
    ])


def consent_page():
    """Render the consent form page."""
    content = [
        html.H3("University of Chicago Online Consent Form for Research Participation", className="mb-4 text-center"),
        
        html.Div([
            html.P([html.Strong("Study Number: "), "IRB26-XXXX"]),
            html.P([html.Strong("Study Title: "), "Investment Decisions in a Simulated Stock Market"]),
            html.P([html.Strong("Researcher(s): "), "Amrita Pathak, Henry K. Dambanemuya (PI)"])
        ], className="mb-4"),
        
        html.H5("Description:", className="mt-3"),
        html.P([
            "We are researchers at the University of Chicago doing a research study on how people make investment decisions in a simulated market environment. ",
            "If you agree to participate, you will complete an interactive online task in which you make a series of investment decisions using virtual money across multiple rounds, ",
            "along with a short set of demographic questions (age, gender, education, income). ",
            "The full study takes about 25 to 30 minutes to complete in a single session. Your participation is voluntary."
        ]),
        
        html.H5("Incentives:", className="mt-3"),
        html.P([
            "Your participation in this study is entirely voluntary. While we welcome participants who are motivated by an interest in contributing to research, ",
            "we also offer a small token of appreciation for your time. All participants who complete the study and pass the attention checks will receive a base payment of $5. ",
            "An additional $10 bonus will be awarded to the top 10 participants whose investment decisions result in the highest overall returns during the task. ",
            "Participants will not lose any compensation if their task performance results in a loss, and no real money is at risk. ",
            "Participants who choose to withdraw before completing the study will not receive payment. ",
            "To ensure data quality, the study includes attention check questions. Participants who fail these checks or do not complete the full study may not be eligible for compensation."
        ]),
        
        html.H5("Risks and Benefits:", className="mt-3"),
        html.P([
            "Your participation in this study does not involve any risk to you beyond that of everyday life. ",
            "The study involves making decisions using virtual money in a simulated market environment and answering brief, non-sensitive questions. ",
            "You may not receive any direct personal benefit from participating in this study; however, the information collected may help researchers better understand ",
            "how people make investment decisions, which could inform future research and educational efforts related to investment behavior."
        ]),
        
        html.H5("Confidentiality:", className="mt-3"),
        html.P([
            "The information collected in this study will be used only for research purposes related to this study. ",
            "The study does not collect names, contact information, IP addresses, or other directly identifying information within the study application. ",
            "Data collected during participation include demographic information, investment decisions, time spent viewing additional information, and optional feedback responses."
        ]),
        html.P([
            "Study data are recorded under a non-identifying study-specific record. ",
            "Any identifiers used by the recruitment platform for compensation or participation management are handled by the platform and are not stored with study response data. ",
            "Access to the study data is limited to the research team."
        ]),
        html.P([
            "If a participant chooses to withdraw before completing the study, any data collected up to the point of withdrawal will not be saved or included in the analysis. ",
            "At the end of the study, you will have the opportunity to request that your data be excluded from the research analysis. ",
            "Because the study does not collect identifying information, data cannot be withdrawn after you have left the study session."
        ]),
        html.P([
            "Identifiable information will not be shared outside the research team because it is not collected as part of this study. ",
            "The information collected as part of this research will not be used or shared for future research studies, even if all identifiers are removed."
        ]),
        
        html.H5("Contacts & Questions:", className="mt-3"),
        html.P("If you have questions or concerns about the study, you can contact the researchers:"),
        html.Ul([
            html.Li("Amrita Pathak at 773-406-4622 or amritap1@uchicago.edu"),
            html.Li("Principal Investigator: Henry Dambanemuya at 773-834-6207 or hdambane@uchicago.edu")
        ]),
        html.P([
            "If you have any questions about your rights as a participant in this research, feel you have been harmed, or wish to discuss other study-related concerns with someone who is not part of the research team, ",
            "you can contact the University of Chicago Social & Behavioral Sciences Institutional Review Board (IRB) Office by phone at (773) 702-2915, or by email at sbs-irb@uchicago.edu."
        ]),
        
        html.H5("Consent:", className="mt-3"),
        html.P([
            "Participation is voluntary. Refusal to participate or withdrawing from the research will involve no penalty or loss of benefits to which you might otherwise be entitled."
        ]),
        html.P([
            "By clicking \"I agree to participate\" below, you confirm that you have read the consent form, are at least 18 years old, and agree to participate in the research. ",
            "Please print or save a copy of this page for your records."
        ]),
        
        html.Hr(),
        create_checkbox_field(
            "consent-checkbox",
            "I agree to participate in the research"
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
                html.P("Study Number: IRB26-XXXX", className="text-center text-muted"),
                html.P("Study Title: Investment Decisions in a Simulated Stock Market", className="text-center text-muted"),
                html.P("Researcher(s): Amrita Pathak, Henry K. Dambanemuya (PI)", className="text-center text-muted mb-4"),
                dbc.Card([
                    dbc.CardBody([
                        html.P("Please provide some basic information about yourself. This information helps us understand our participant pool."),
                        
                        # Age Range
                        dbc.Label("1. Please indicate your age:"),
                        dbc.Select(
                            id="age-select",
                            options=AGE_RANGE_OPTIONS,
                            value="",
                            className="mb-3"
                        ),
                        
                        # Gender
                        dbc.Label("2. Please indicate your gender:"),
                        dbc.Select(
                            id="gender-select",
                            options=GENDER_OPTIONS,
                            value="",
                            className="mb-2"
                        ),
                        # Self-describe option (conditional)
                        dbc.Input(
                            id="gender-self-describe",
                            type="text",
                            placeholder="Please specify",
                            className="mb-3",
                            style={'display': 'none'}
                        ),
                        
                        # Education Level
                        dbc.Label("3. What is the highest level of education you have completed?"),
                        dbc.Select(
                            id="education-select",
                            options=EDUCATION_OPTIONS,
                            value="",
                            className="mb-3"
                        ),
                        
                        # Income
                        dbc.Label("4. Which of the following best describes your total annual personal income before taxes?"),
                        dbc.Select(
                            id="income-select",
                            options=INCOME_OPTIONS,
                            value="",
                            className="mb-3"
                        ),
                        
                        # Investment Experience
                        dbc.Label("5. Which of the following best describes your personal investment experience?"),
                        dbc.Select(
                            id="experience-select",
                            options=EXPERIENCE_OPTIONS,
                            value="",
                            className="mb-3"
                        ),
                        
                        # Hispanic/Latino
                        dbc.Label("6. Are you Hispanic/Latino?"),
                        dbc.Select(
                            id="hispanic-latino-select",
                            options=HISPANIC_LATINO_OPTIONS,
                            value="",
                            className="mb-3"
                        ),
                        
                        # Race
                        dbc.Label("7. Regardless of your answer to the prior question, please indicate how you identify yourself:"),
                        dbc.Select(
                            id="race-select",
                            options=RACE_OPTIONS,
                            value="",
                            className="mb-2"
                        ),
                        # Other race option (conditional)
                        dbc.Input(
                            id="race-other",
                            type="text",
                            placeholder="Please specify",
                            className="mb-3",
                            style={'display': 'none'}
                        ),
                        
                        html.Div(id="demographics-error", className="text-danger mb-2"),
                        dbc.Button(
                            "Continue to Tutorial",
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


def tutorial_page(tutorial_num, amount):
    """Render a tutorial page (practice round)."""
    # Get tutorial task ID
    tutorial_task_id = f'tutorial_{tutorial_num}'
    
    # Safely get task data
    task_data, error = get_task_data_safe(tutorial_task_id)
    
    if error:
        return dbc.Container([
            dbc.Alert([
                html.H4("Error Loading Tutorial", className="alert-heading"),
                html.P(error),
                html.Hr(),
                html.P("Please refresh the page or contact the study administrator.", className="mb-0")
            ], color=COLORS['danger'])
        ])
    
    stocks = task_data['stocks']
    
    # Instructions for each tutorial
    if tutorial_num == 1:
        instructions = dbc.Alert([
            html.H4([html.I(className="bi bi-lightbulb me-2"), "Tutorial 1: Exploring Information"], className="mb-3"),
            html.P([
                html.Strong("Welcome!"),
                " This is a practice round to help you learn the interface."
            ], className="mb-2"),
            html.Hr(),
            html.P([
                html.Strong("Step 1: "),
                "Click on the 'Purchase Information' button to buy access to all information about this stock. ",
                "Notice that purchasing information costs money and is deducted from your available amount."
            ], className="mb-2"),
            html.P([
                html.Strong("Step 2: "),
                "After purchasing, the three information buttons (Show More Details, Week's Chart, Month's Chart) will be enabled. ",
                "Click on them to view different types of information about the stock."
            ], className="mb-2"),
            html.P([
                html.Strong("Step 3: "),
                "After viewing the information, click Continue to proceed to the next tutorial."
            ], className="mb-0")
        ], color="primary", className="mb-4")
    else:  # tutorial_num == 2
        instructions = dbc.Alert([
            html.H4([html.I(className="bi bi-lightbulb me-2"), "Tutorial 2: Making Investments"], className="mb-3"),
            html.P([
                html.Strong("Great job!"),
                " Now practice making an investment decision."
            ], className="mb-2"),
            html.Hr(),
            html.P([
                "Enter an investment amount in the box below (you can enter $0 if you don't want to invest). ",
                "Then click 'Start Main Study' to see the result and begin the actual study."
            ], className="mb-0")
        ], color="primary", className="mb-4")
    
    return dbc.Container([
        instructions,
        
        html.H2(f"Tutorial {tutorial_num} of {NUM_TUTORIAL_TASKS}", className="text-center mb-2"),
        
        html.P("Practice round - decisions here are not recorded.", 
               className="text-center text-muted mb-4"),
        
        # Stock card
        create_stock_card(stocks[0], 0, tutorial_task_id, amount),
        
        html.Div(id="tutorial-error", className="text-danger text-center mb-3 mt-3"),
        
        # Completion status
        html.Div(id=f'tutorial-{tutorial_num}-status', className="text-center mb-3"),
        
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "Continue" if tutorial_num < NUM_TUTORIAL_TASKS else "Start Main Study",
                    id=f"tutorial-{tutorial_num}-submit",
                    color="success" if tutorial_num < NUM_TUTORIAL_TASKS else "primary",
                    size="lg",
                    className="w-100",
                    disabled=(tutorial_num == 1)  # Only tutorial 1 starts disabled
                )
            ], md=6, className="mx-auto")
        ]),
        
        # Result Modal for tutorial
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Investment Result (Practice)"), close_button=False),
            dbc.ModalBody(id=f"tutorial-{tutorial_num}-result-body"),
            dbc.ModalFooter(
                dbc.Button("Continue", id=f"tutorial-{tutorial_num}-result-ok", color="primary")
            )
        ], id=f"tutorial-{tutorial_num}-result-modal", is_open=False, centered=True, backdrop="static", keyboard=False)
    ])


def task_page(task_id, amount, sequential_task_num=None):
    """Render the main investment task page for a given task number."""
    # Use sequential number for display if provided, otherwise use task_id
    display_task_num = sequential_task_num if sequential_task_num is not None else task_id
    
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
        html.H2(f"Investment Decision {display_task_num} of {NUM_TASKS}", className="text-center mb-4"),
        
        html.P("Review the stock below and decide how much to invest. You can invest any amount up to your available balance, or choose not to invest.", 
               className="text-center text-muted mb-4"),
        
        # Stock card - now full width
        create_stock_card(stocks[0], 0, task_id, amount),
        
        html.Div(id="task-error", className="text-danger text-center mb-3 mt-3"),
        
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
        ]),
        
        # Profit/Loss Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Investment Result"), close_button=False),
            dbc.ModalBody(id="result-modal-body"),
            dbc.ModalFooter(
                dbc.Button("OK", id="result-modal-ok", color="primary")
            )
        ], id="result-modal", is_open=False, centered=True, backdrop="static", keyboard=False)
    ])


def confidence_risk_page(completed_tasks=None):
    """Render the confidence and risk assessment page."""
    conf_config = SLIDER_CONFIG['confidence']
    risk_config = SLIDER_CONFIG['risk']
    
    # Determine which checkpoint this is
    if completed_tasks:
        message = f"You've completed {completed_tasks} investment decisions. Please rate your confidence and risk perception."
    else:
        message = "Please rate your confidence and risk perception."
    
    content = [
        html.P(message),
        
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
    ]
    
    # Add attention check for checkpoints 3 and 9 (not 14)
    # Always include the slider (for callback), but hide it when not needed
    if completed_tasks == 3:
        content.extend([
            html.Div([
                html.H5("Please select option 2 for this item. This question is used to verify attentive responding.", 
                       className="mt-5 mb-3", style={'color': '#0066cc'}),
                create_slider_with_labels(
                    'attention-slider',
                    1,
                    7,
                    4,
                    1,
                    '1',
                    '7'
                ),
            ])
        ])
    elif completed_tasks == 9:
        content.extend([
            html.Div([
                html.H5("Please select option 4 for this item. This question is used to verify attentive responding.", 
                       className="mt-5 mb-3", style={'color': '#0066cc'}),
                create_slider_with_labels(
                    'attention-slider',
                    1,
                    7,
                    4,
                    1,
                    '1',
                    '7'
                ),
            ])
        ])
    else:
        # Hidden slider for callback compatibility
        content.append(
            html.Div(
                create_slider_with_labels(
                    'attention-slider',
                    1,
                    7,
                    4,
                    1,
                    '1',
                    '7'
                ),
                style={'display': 'none'}
            )
        )
    
    content.append(create_action_button("Continue", "confidence-risk-submit", className="mt-4"))
    
    return dbc.Container([
        create_page_header("Confidence and Risk Assessment"),
        create_centered_card(content)
    ])


def feedback_page(uninvested_amount, portfolio, info_cost_spent=0):
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
        ], md=2),
        dbc.Col([
            create_info_card("Information Cost", format_currency(info_cost_spent))
        ], md=2),
        dbc.Col([
            create_info_card("Uninvested Cash", format_currency(uninvested_amount))
        ], md=2),
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
        create_action_button("Continue", "feedback-submit", color=COLORS['success']),
        html.Div(id="completion-message", className="text-center mt-3")
    ]
    
    return dbc.Container([
        create_page_header("Study Complete - Thank You!"),
        create_centered_card(content)
    ])


def debrief_page(uninvested_amount, portfolio, info_cost_spent=0):
    """Render the debriefing page with study explanation and withdrawal option."""
    # Calculate stats to show
    total_invested_original = sum(inv['invested'] for inv in portfolio)
    total_invested_current = sum(inv['final_value'] for inv in portfolio)
    total_profit_loss = total_invested_current - total_invested_original
    total_final_amount = uninvested_amount + total_invested_current
    overall_profit_loss = total_final_amount - INITIAL_AMOUNT
    overall_profit_loss_percent = (overall_profit_loss / INITIAL_AMOUNT) * 100 if INITIAL_AMOUNT > 0 else 0
    
    # Summary stats
    stats_row = dbc.Row([
        dbc.Col([
            create_info_card("Starting Amount", format_currency(INITIAL_AMOUNT))
        ], md=3),
        dbc.Col([
            create_info_card("Information Cost", format_currency(info_cost_spent))
        ], md=3),
        dbc.Col([
            create_info_card("Uninvested Cash", format_currency(uninvested_amount))
        ], md=3),
        dbc.Col([
            create_info_card(
                "Total Final Amount",
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
            html.H5("Your Investment Portfolio Breakdown", className="mt-4 mb-3"),
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
        html.H3("University of Chicago Debriefing Statement", className="text-center mb-4"),
        
        html.Div([
            html.P([html.Strong("Study Number: "), "IRB26-XXXX"]),
            html.P([html.Strong("Study Title: "), "How do online trading discussions reflect financial decision-making and risk-taking behavior?"]),
            html.P([html.Strong("Researcher(s): "), "Amrita Pathak, Dr. Henry K. Dambanemuya (PI)"])
        ], className="mb-4"),
        
        html.P([
            html.Strong("Thank you for your participation. "), 
            "We would now like to tell you a little more about the study."
        ], className="mb-3"),
        
        html.H5("Purpose of the Study:", className="mt-3"),
        html.Ul([
            html.Li([
                "The purpose of this study is to understand how people make investment decisions in a simulated market. ",
                "The study looks at how participants choose between investment options, how they respond to gains and losses, ",
                "how confident they feel about their decisions, and how they use available information while making choices over multiple rounds."
            ]),
            html.Li([
                "At the beginning of the study, participants were told that they would take part in a simulated investment game using virtual money ",
                "and that their decisions would be recorded for research purposes. This description accurately reflected the task."
            ]),
            html.Li([
                "The study did not involve deception. However, specific details about the exact research questions and analyses were not described in advance ",
                "in order to avoid influencing participants' natural decision-making."
            ]),
            html.Li([
                "The study is designed to examine patterns in risk-taking, learning from feedback, confidence, and information use across repeated investment decisions. ",
                "Providing full details in advance could have changed how participants approached the task, which is why some information was explained only after participation."
            ])
        ]),
        
        dbc.Alert([
            html.P([
                html.Strong("Important: "), 
                "As this study is ongoing, we ask that you not discuss this study with anyone else who is currently participating or might participate at a future time."
            ], className="mb-0")
        ], color="info", className="my-3"),
        
        html.Hr(className="my-4"),
        
        html.H5("Your Results:", className="mb-3"),
        stats_row,
        portfolio_table if portfolio_table else html.Div(),
        
        html.Hr(className="my-4"),
        
        html.H5("Data Withdrawal Option:", className="mt-4 mb-3"),
        html.P([
            "Now that we have explained this study more fully, you may request that your data be excluded from this research study. ",
            "If you decide that you do not want the researchers to include your data in the analysis, there is no penalty. ",
            "You will still receive compensation for this experiment."
        ]),
        
        html.P([html.Strong("Do you wish to exclude your data from the study?")], className="mt-3 mb-3"),
        
        dbc.RadioItems(
            id="withdrawal-choice",
            options=[
                {"label": " Yes, please exclude my data from the study", "value": "yes"},
                {"label": " No, you may include my data in the study", "value": "no"}
            ],
            value="no",
            className="mb-3"
        ),
        
        html.Hr(className="my-4"),
        
        html.H5("Contacts & Questions:", className="mt-3"),
        html.P("If you have questions or concerns about the study, you can contact the researchers at amritap1@uchicago.edu."),
        html.P([
            "If you have any questions about your rights as a participant in this research, or to discuss other study-related concerns with someone who is not part of the research team, ",
            "you can contact the University of Chicago Social & Behavioral Sciences Institutional Review Board (IRB) Office by phone at (773) 702-2915, or by email at sbs-irb@uchicago.edu."
        ]),
        
        create_action_button("Finish Study", "debrief-submit", color=COLORS['primary'], className="mt-4"),
        html.Div(id="debrief-message", className="text-center mt-3")
    ]
    
    return dbc.Container([
        create_page_header("Study Debriefing"),
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
