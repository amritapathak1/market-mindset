# Stock Investment Study - Dash Application

A Python Dash web application for conducting investment decision research studies.

## Features

- **Consent Form**: Participants must provide informed consent before participating
- **Demographics Survey**: Collects age, gender, education, and investment experience with validation
- **7 Investment Tasks**: Participants make investment decisions across 7 different scenarios
  - Each task presents 2 stocks with detailed information
  - Participants can view additional details via modal popups
  - Investment amounts are validated against available funds and for valid input
  - Amount automatically updates after each task (fixed adjustments)
- **Mid-Study Assessment**: After task 3, participants rate confidence and risk perception
- **Final Results**: Shows starting amount, final amount, and net change
- **Feedback Collection**: Optional feedback form at the end
- **Data Persistence**: Study progress is saved in browser localStorage
- **Loading States**: Smooth transitions with loading indicators
- **Error Handling**: Comprehensive validation and user-friendly error messages

## Installation

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

```bash
python app.py
```

The application will start on `http://127.0.0.1:8050/`

## Application Flow

1. **Consent Page**: User must check consent box to continue
2. **Demographics**: User fills out demographic information
3. **Tasks 1-3**: Investment decisions
4. **Confidence/Risk Rating**: User rates confidence and perceived risk
5. **Tasks 4-7**: More investment decisions
6. **Final Results**: Display final amount and collect feedback
7. **Thank You**: Completion message

## File Structure

- `app.py` (302 lines): Main Dash application with callbacks and routing logic
- `pages.py` (324 lines): All page rendering functions (consent, demographics, tasks, etc.)
- `stock_data.py` (163 lines): Stock information for all 7 tasks and amount adjustments
- `config.py` (144 lines): Configuration constants, error messages, and UI settings
- `utils.py` (240 lines): Utility functions for validation, data processing, and flow control
- `components.py` (230 lines): Reusable UI components for consistent design
- `requirements.txt`: Python dependencies
- `README.md`: This file
- `REFACTORING_PLAN.md`: Detailed refactoring plan and implementation notes

## Customization

### Modifying Stock Data
Edit `stock_data.py` to change stock information, number of tasks, or amount adjustments.

### Changing Initial Amount
In `config.py`, modify the `INITIAL_AMOUNT` constant (default: 1000).

### Adjusting Number of Tasks
Update `NUM_TASKS` in `config.py` and add/remove task data in `stock_data.py`.

### Modifying Confidence/Risk Checkpoint
Change `CONFIDENCE_RISK_CHECKPOINT` in `config.py` (default: 3).
localStorage:
- Consent status
- Demographics (age, gender, education, investment experience)
- Task responses (investment amounts for each stock)
- Confidence and risk ratings
- Feedback text
- Current progress (page, task number, available amount)

**Note**: Data persists in browser localStorage. Users can resume if they close the browser accidentally. For production use, implement server-side storage for permanent data retention

The application stores the following data in browser session:
- Consent status
- Demographics (age, gender, education, investment experience)
- Task responses (investment amounts for each stock)
- Confidence and risk ratings
- Feedback text

**Note**: This demo stores data in browser memory only. For production use, implement server-side storage.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete AWS deployment instructions.

For production deployment, this application requires:
- PostgreSQL database (AWS RDS recommended)
- Python 3.8+ environment
- Gunicorn WSGI server
- Nginx reverse proxy (optional but recommended)

Environment variables (see `.env.example`):
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - Database connection
- `DEBUG` - Set to `False` for production
- `PORT` - Application port (default: 8050)

## Technologies Used

- **Dash**: Web application framework
- **Dash Bootstrap Components**: UI components and styling
- **Python**: Backend logic
- **PostgreSQL**: Database for participant data (with file-based fallback)
- **Gunicorn**: Production WSGI server

## License

For research purposes only.
