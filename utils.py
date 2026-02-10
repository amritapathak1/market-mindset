"""
Utility functions for the Stock Market Mindset application.
"""

from config import ERROR_MESSAGES, MAX_DECIMAL_PLACES, MIN_INVESTMENT, TASKS_DATA, TUTORIAL_TASKS_DATA


def validate_investment(value, stock_name=None):
    """
    Validate individual investment amount.
    
    Args:
        value: The investment amount to validate
        stock_name: Optional name of the stock for error messages
        
    Returns:
        tuple: (validated_amount, error_message)
            - If valid: (float_amount, None)
            - If invalid: (None, error_string)
    """
    # Handle None or empty string
    if value is None or value == "" or value == 0:
        return 0, None
    
    try:
        amount = float(value)
        
        # Check for negative amounts
        if amount < MIN_INVESTMENT:
            prefix = f"{stock_name}: " if stock_name else ""
            return None, f"{prefix}{ERROR_MESSAGES['investment_negative']}"
        
        # Check decimal places
        if round(amount, MAX_DECIMAL_PLACES) != amount:
            prefix = f"{stock_name}: " if stock_name else ""
            return None, f"{prefix}{ERROR_MESSAGES['investment_decimal']}"
        
        return amount, None
        
    except (ValueError, TypeError):
        prefix = f"{stock_name}: " if stock_name else ""
        return None, f"{prefix}{ERROR_MESSAGES['investment_invalid']}"


def validate_total_investment(investments, available_amount):
    """
    Validate that total investment doesn't exceed available amount.
    
    Args:
        investments: List of investment amounts
        available_amount: Available balance
        
    Returns:
        tuple: (is_valid, error_message)
    """
    total = sum(v if v else 0 for v in investments)
    
    if total > available_amount:
        error = ERROR_MESSAGES['investment_exceeds'].format(
            total=total,
            available=available_amount
        )
        return False, error
    
    return True, None


def get_task_data_safe(task_id):
    """
    Safely retrieve task data with error handling.
    Supports both tutorial tasks (string IDs like 'tutorial_1') and main tasks (integer IDs).
    
    Args:
        task_id: The ID of the task to retrieve (string for tutorial, 1-indexed int for main)
        
    Returns:
        tuple: (task_data, error_message)
            - If successful: (task_dict, None)
            - If error: (None, error_string)
    """
    try:
        # Check if this is a tutorial task
        if isinstance(task_id, str) and task_id.startswith('tutorial_'):
            # Find tutorial task by task_id field
            for task_data in TUTORIAL_TASKS_DATA:
                if task_data.get('task_id') == task_id:
                    # Validate required fields
                    if 'task_id' not in task_data or 'stocks' not in task_data:
                        return None, "Missing required fields in tutorial task data"
                    
                    if len(task_data['stocks']) != 1:
                        return None, "Task must have exactly 1 stock"
                    
                    # Validate stock data structure
                    for i, stock in enumerate(task_data['stocks']):
                        required_fields = ['name', 'ticker',
                                         'short_description', 'detailed_description']
                        for field in required_fields:
                            if field not in stock:
                                return None, f"Stock {i} missing required field: {field}"
                    
                    return task_data, None
            
            return None, f"Tutorial task not found: {task_id}"
        
        # Handle main tasks (integer IDs)
        # Validate task_id range
        if not isinstance(task_id, int) or not 1 <= task_id <= len(TASKS_DATA):
            return None, f"Invalid task ID: {task_id}"
        
        # Get task data (convert to 0-indexed)
        task_data = TASKS_DATA[task_id - 1]
        
        # Validate required fields
        if 'task_id' not in task_data or 'stocks' not in task_data:
            return None, "Missing required fields in task data"
        
        if len(task_data['stocks']) != 1:
            return None, "Task must have exactly 1 stock"
        
        # Validate stock data structure
        for i, stock in enumerate(task_data['stocks']):
            required_fields = ['name', 'ticker',
                             'short_description', 'detailed_description']
            for field in required_fields:
                if field not in stock:
                    return None, f"Stock {i} missing required field: {field}"
        
        return task_data, None
        
    except (IndexError, KeyError, TypeError) as e:
        return None, f"{ERROR_MESSAGES['task_data_error']} ({str(e)})"
    except Exception as e:
        return None, f"{ERROR_MESSAGES['unknown_error']} ({str(e)})"


def validate_demographics(age_range, gender, gender_self_describe, education, income, experience, hispanic_latino, race, race_other):
    """
    Validate demographics form data.
    
    Args:
        age_range: Age range selection
        gender: Gender selection
        gender_self_describe: Self-described gender (if applicable)
        education: Education level selection
        income: Income range selection
        experience: Investment experience selection
        hispanic_latino: Hispanic/Latino identification
        race: Race identification
        race_other: Other race specification (if applicable)
        
    Returns:
        tuple: (is_valid, error_message, validated_data)
    """
    # Validate age range
    if not age_range or age_range == "":
        return False, "Please select your age range", None
    
    # Validate gender
    if not gender or gender == "":
        return False, ERROR_MESSAGES['gender_required'], None
    
    # If "prefer to self-describe" is selected, validate the text input
    if gender == "prefer-to-self-describe" and not gender_self_describe:
        return False, "Please specify your gender", None
    
    # Validate education
    if not education or education == "":
        return False, ERROR_MESSAGES['education_required'], None
    
    # Validate income
    if not income or income == "":
        return False, "Please select your income range", None
    
    # Validate experience
    if not experience or experience == "":
        return False, ERROR_MESSAGES['experience_required'], None
    
    # Validate hispanic/latino
    if not hispanic_latino or hispanic_latino == "":
        return False, "Please indicate whether you are Hispanic/Latino", None
    
    # Validate race
    if not race or race == "":
        return False, "Please select your race/ethnicity", None
    
    # If "other" is selected for race, validate the text input
    if race == "other" and not race_other:
        return False, "Please specify your race/ethnicity", None
    
    # Return validated data
    validated_data = {
        'age_range': age_range,
        'gender': gender,
        'gender_self_describe': gender_self_describe if gender == "prefer-to-self-describe" else None,
        'education': education,
        'income': income,
        'experience': experience,
        'hispanic_latino': hispanic_latino,
        'race': race,
        'race_other': race_other if race == "other" else None
    }
    
    return True, None, validated_data


def format_currency(amount):
    """Format amount as currency string."""
    return f"${amount:,.2f}"


def format_percentage(value):
    """Format value as percentage string."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def calculate_profit_loss(final_amount, initial_amount):
    """
    Calculate profit/loss and percentage.
    
    Returns:
        tuple: (profit_loss_amount, profit_loss_percentage)
    """
    profit_loss = final_amount - initial_amount
    percentage = (profit_loss / initial_amount) * 100
    return profit_loss, percentage


def validate_page_access(requested_page, consent_given, demographics_completed, current_task, confidence_risk_completed):
    """
    Validate if user can access the requested page based on current progress.
    Prevents skipping required steps.
    
    Args:
        requested_page: The page the user is trying to access
        consent_given: Whether consent has been given
        demographics_completed: Whether demographics are filled
        current_task: Current task number
        confidence_risk_completed: Whether confidence/risk assessment is done
        
    Returns:
        tuple: (is_allowed, redirect_page, error_message)
            - If allowed: (True, None, None)
            - If not allowed: (False, redirect_page, error_message)
    """
    from config import PAGES, CONFIDENCE_RISK_CHECKPOINTS
    
    # Consent page is always accessible
    if requested_page == PAGES['consent']:
        return True, None, None
    
    # Demographics requires consent
    if requested_page == PAGES['demographics']:
        if not consent_given:
            return False, PAGES['consent'], "Please provide consent before continuing"
        return True, None, None
    
    # Tutorials require demographics
    if requested_page == PAGES['tutorial_1'] or requested_page == PAGES['tutorial_2']:
        if not consent_given:
            return False, PAGES['consent'], "Please provide consent before continuing"
        if not demographics_completed:
            return False, PAGES['demographics'], "Please complete demographics before starting tutorials"
        return True, None, None
    
    # Tasks require demographics (tutorials are optional to enforce)
    if requested_page == PAGES['task']:
        if not consent_given:
            return False, PAGES['consent'], "Please provide consent before continuing"
        if not demographics_completed:
            return False, PAGES['demographics'], "Please complete demographics before starting tasks"
        return True, None, None
    
    # Confidence/risk requires completing checkpoint tasks
    if requested_page == PAGES['confidence_risk']:
        if current_task <= CONFIDENCE_RISK_CHECKPOINTS[0]:
            return False, PAGES['task'], f"Please complete task {CONFIDENCE_RISK_CHECKPOINTS[0]} first"
        return True, None, None
    
    # Feedback requires all tasks completed
    if requested_page == PAGES['feedback']:
        from config import NUM_TASKS
        if current_task <= NUM_TASKS:
            return False, PAGES['task'], f"Please complete all {NUM_TASKS} tasks first"
        return True, None, None
    
    # Thank you page requires feedback submission
    if requested_page == PAGES['thank_you']:
        return True, None, None
    
    return True, None, None
