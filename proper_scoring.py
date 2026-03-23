def brier_score(confidence, outcome):
    """
    Brier score: Mean squared error of probability forecast
    
    Parameters:
    -----------
    confidence : float (0 to 1)
        Reported confidence 
    outcome : int (0 or 1)
        Actual outcome
    
    Returns:
    --------
    score : float in [0, 1]
    """
    return (confidence - outcome)**2

def quadratic_score(confidence, outcome):
    """
    Quadratic scoring rule: Inverted Brier score
    
    Parameters:
    -----------
    confidence : float (0 to 1)
        Reported confidence
    outcome : int (0 or 1)
        1 if event occurred, 0 if not
    
    Returns:
    --------
    score : float
        Score in range [0, 1]
    """
    return 1 - (confidence - outcome)**2

def explain_quadratic_scoring():
    """
    Tutorial explaining the quadratic scoring rule
    """
    explanation = """
    How Confidence Scoring Works
    
    After each investment, we'll ask: "How confident are you that your investment will make a profit?"
    We will score your self-reported confidence against the investment outcome such that:
    - High confidence and profitable investments earn high scores.
    - Low confidence and investment losses earn high scores.
    - High confidence and investment losses earn low scores.
    - Low confidence and profitable investments earn low scores.
    
    EXAMPLES:
    
    Example 1: You report 70% chance of profit
    - Investment actually profits → Score: 0.91
    - Investment actually loses  → Score: 0.51
    
    Example 2: You report 90% chance of profit (very confident!)
    - Investment actually profits → Score: 0.99
    - Investment actually loses  → Score: 0.19
    
    Example 3: You report 50% chance of profit (unsure)
    - Investment actually profits → Score: 0.75
    - Investment actually loses  → Score: 0.75
    
    Key Isight: You maximize your score by reporting your honest confidence in your investment decision. Exaggerating or hedging will earn you lower scores.
    
    """
    
    return explanation