"""
Configuration constants for the Stock Market Mindset application.
"""

import json
import os

# ============================================
# STUDY CONFIGURATION
# ============================================

# Load tutorial tasks data from JSON file
TUTORIAL_TASKS_DATA_FILE = os.path.join(os.path.dirname(__file__), 'tutorial_tasks_data.json')
with open(TUTORIAL_TASKS_DATA_FILE, 'r') as f:
    TUTORIAL_TASKS_DATA = json.load(f)

# Load tasks data from JSON file
TASKS_DATA_FILE = os.path.join(os.path.dirname(__file__), 'tasks_data.json')
with open(TASKS_DATA_FILE, 'r') as f:
    TASKS_DATA = json.load(f)

# Initial amount given to participants
INITIAL_AMOUNT = 1000

# Initial amount for tutorial tasks
TUTORIAL_INITIAL_AMOUNT = 100

# Number of tutorial rounds (practice tasks before main tasks)
NUM_TUTORIAL_TASKS = 2

# Total number of investment tasks (main tasks, excluding tutorials)
NUM_TASKS = 14

# Task numbers after which to show confidence/risk assessment
# Note: These are relative to main tasks only (not including tutorial tasks)
CONFIDENCE_RISK_CHECKPOINTS = [3, 9, 14]

# ============================================
# VALIDATION SETTINGS
# ============================================

# Demographics validation
MIN_AGE = 18
MAX_AGE = 120

# Investment validation
MIN_INVESTMENT = 0
MAX_DECIMAL_PLACES = 2

# ============================================
# UI CONFIGURATION
# ============================================

# Bootstrap theme
BOOTSTRAP_THEME = "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css"

# Color scheme
COLORS = {
    'primary': 'primary',
    'success': 'success',
    'danger': 'danger',
    'warning': 'warning',
    'info': 'info',
    'positive': 'success',  # For positive stock changes
    'negative': 'danger',   # For negative stock changes
}

# Modal settings
MODAL_SIZE = 'lg'

# ============================================
# INFORMATION COSTS
# ============================================

# Cost to view different types of information (in dollars)
INFO_COSTS = {
    'show_more': 5.00,      # Cost to view additional details
    'show_week': 10.00,     # Cost to view week's chart and analysis
    'show_month': 15.00     # Cost to view month's chart and analysis
}

# ============================================
# ERROR MESSAGES
# ============================================

ERROR_MESSAGES = {
    'age_required': 'Please enter a valid age (18 or older)',
    'age_too_young': 'You must be at least 18 years old to participate',
    'age_invalid': 'Please enter a valid age between 18 and 120',
    'gender_required': 'Please select a gender',
    'education_required': 'Please select an education level',
    'experience_required': 'Please select your investment experience',
    'investment_negative': 'Investment amount cannot be negative',
    'investment_exceeds': 'Total investment (${total:.2f}) exceeds available amount (${available:.2f})',
    'investment_invalid': 'Please enter a valid investment amount',
    'investment_decimal': 'Investment amount can have at most 2 decimal places',
    'task_data_error': 'Error loading task data. Please refresh the page.',
    'unknown_error': 'An unexpected error occurred. Please try again.',
}

# Success messages
SUCCESS_MESSAGES = {
    'consent_given': 'Thank you for your consent',
    'demographics_saved': 'Demographics saved successfully',
    'task_completed': 'Investment decision recorded',
    'study_complete': 'Thank you for completing the study!',
}

# ============================================
# PAGE CONFIGURATION
# ============================================

# Page identifiers
PAGES = {
    'consent': 'consent',
    'demographics': 'demographics',
    'tutorial_1': 'tutorial-1',
    'tutorial_2': 'tutorial-2',
    'task': 'task',
    'confidence_risk': 'confidence-risk',
    'feedback': 'feedback',
    'thank_you': 'thank-you',
}

# ============================================
# SLIDER CONFIGURATION
# ============================================

SLIDER_CONFIG = {
    'confidence': {
        'min': 1,
        'max': 7,
        'step': 1,
        'default': 4,
        'label_min': 'Not at all confident',
        'label_max': 'Extremely confident',
    },
    'risk': {
        'min': 1,
        'max': 7,
        'step': 1,
        'default': 4,
        'label_min': 'Very low risk',
        'label_max': 'Very high risk',
    }
}

# ============================================
# DEMOGRAPHICS OPTIONS
# ============================================

GENDER_OPTIONS = [
    {"label": "Select...", "value": ""},
    {"label": "Male", "value": "male"},
    {"label": "Female", "value": "female"},
    {"label": "Non-binary", "value": "non-binary"},
    {"label": "Prefer not to say", "value": "prefer-not-to-say"}
]

EDUCATION_OPTIONS = [
    {"label": "Select...", "value": ""},
    {"label": "High School", "value": "high-school"},
    {"label": "Some College", "value": "some-college"},
    {"label": "Bachelor's Degree", "value": "bachelors"},
    {"label": "Master's Degree", "value": "masters"},
    {"label": "Doctoral Degree", "value": "doctoral"},
    {"label": "Other", "value": "other"}
]

EXPERIENCE_OPTIONS = [
    {"label": "Select...", "value": ""},
    {"label": "None - No prior experience", "value": "none"},
    {"label": "Beginner - Less than 1 year", "value": "beginner"},
    {"label": "Intermediate - 1-5 years", "value": "intermediate"},
    {"label": "Advanced - 5-10 years", "value": "advanced"},
    {"label": "Expert - More than 10 years", "value": "expert"}
]
