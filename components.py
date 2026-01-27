"""
Reusable UI components for the Stock Investment Study application.
"""

import dash_bootstrap_components as dbc
from dash import html


def create_page_header(title, subtitle=None):
    """
    Create a standardized page header.
    
    Args:
        title: Main heading text
        subtitle: Optional subtitle text
        
    Returns:
        html.Div containing the header
    """
    components = [html.H1(title, className="text-center mb-4")]
    
    if subtitle:
        components.append(html.P(subtitle, className="text-center text-muted mb-4"))
    
    return html.Div(components)


def create_centered_card(children, width=8):
    """
    Create a centered card container.
    
    Args:
        children: Content to place inside the card
        width: Column width (1-12, default 8)
        
    Returns:
        dbc.Container with centered card
    """
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody(children)
                ])
            ], width=12, lg=width, className="mx-auto")
        ])
    ])


def create_form_field(label, input_component, error_id=None, help_text=None):
    """
    Create a standardized form field with label and optional error display.
    
    Args:
        label: Field label text
        input_component: Dash component (Input, Select, etc.)
        error_id: Optional ID for error message div
        help_text: Optional help text to display below field
        
    Returns:
        html.Div containing the form field
    """
    components = [dbc.Label(label), input_component]
    
    if help_text:
        components.append(html.Small(help_text, className="form-text text-muted"))
    
    if error_id:
        components.append(html.Div(id=error_id, className="text-danger small mt-1"))
    
    return html.Div(components, className="mb-3")


def create_action_button(label, button_id, color="primary", size="lg", full_width=True, disabled=False, className=""):
    """
    Create a standardized action button.
    
    Args:
        label: Button text
        button_id: Component ID
        color: Bootstrap color (default: primary)
        size: Button size (sm, md, lg)
        full_width: Whether button should be full width
        disabled: Whether button is disabled
        className: Additional CSS classes
        
    Returns:
        dbc.Button
    """
    classes = "w-100" if full_width else ""
    if className:
        classes = f"{classes} {className}".strip()
    
    return dbc.Button(
        label,
        id=button_id,
        color=color,
        size=size,
        className=classes,
        disabled=disabled
    )


def create_error_alert(title, message, details=None):
    """
    Create a standardized error alert.
    
    Args:
        title: Error title
        message: Error message
        details: Optional additional details
        
    Returns:
        dbc.Alert containing error information
    """
    content = [
        html.H4(title, className="alert-heading"),
        html.P(message)
    ]
    
    if details:
        content.extend([
            html.Hr(),
            html.P(details, className="mb-0 small")
        ])
    
    return dbc.Alert(content, color="danger")


def create_success_alert(message):
    """
    Create a standardized success alert.
    
    Args:
        message: Success message
        
    Returns:
        dbc.Alert containing success message
    """
    return dbc.Alert(message, color="success")


def create_info_card(title, value, color=None, outline=False):
    """
    Create an info card for displaying stats.
    
    Args:
        title: Card title
        value: Value to display
        color: Bootstrap color (optional)
        outline: Whether to use outline style
        
    Returns:
        dbc.Card with info
    """
    return dbc.Card([
        dbc.CardBody([
            html.H6(title, className="text-muted"),
            html.H3(value, className="text-center")
        ])
    ], className="mb-3", color=color, outline=outline)


def create_slider_with_labels(slider_id, min_val, max_val, default, step, label_min, label_max):
    """
    Create a slider with labels on both ends.
    
    Args:
        slider_id: Slider component ID
        min_val: Minimum value
        max_val: Maximum value
        default: Default value
        step: Step size
        label_min: Label for minimum end
        label_max: Label for maximum end
        
    Returns:
        html.Div containing slider and labels
    """
    from dash import dcc
    
    return html.Div([
        dcc.Slider(
            id=slider_id,
            min=min_val,
            max=max_val,
            step=step,
            marks={i: str(i) for i in range(min_val, max_val + 1)},
            value=default,
            tooltip={"placement": "bottom", "always_visible": True}
        ),
        html.Div([
            html.Span(label_min, className="float-start text-muted"),
            html.Span(label_max, className="float-end text-muted")
        ], className="mb-4", style={'clear': 'both'})
    ])


def create_checkbox_field(checkbox_id, label):
    """
    Create a checkbox field.
    
    Args:
        checkbox_id: Checkbox component ID
        label: Checkbox label
        
    Returns:
        dbc.Checkbox
    """
    return dbc.Checkbox(
        id=checkbox_id,
        label=label,
        value=False,
        className="mb-3"
    )


def create_text_area(textarea_id, placeholder, min_height="150px"):
    """
    Create a text area field.
    
    Args:
        textarea_id: Textarea component ID
        placeholder: Placeholder text
        min_height: Minimum height
        
    Returns:
        dbc.Textarea
    """
    return dbc.Textarea(
        id=textarea_id,
        placeholder=placeholder,
        style={"minHeight": min_height},
        className="mb-3"
    )
