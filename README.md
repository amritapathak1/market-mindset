# Stock Market Mindset - Dash Application

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
- **Task-by-Task Summary**: Final feedback page includes a collapsible per-task results breakdown in participant shown order
- **Feedback Collection**: Optional feedback form at the end
- **Data Persistence**: Participant data is written to PostgreSQL (with JSONL file fallback when DB is unavailable)
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

The application will start on localhost

Use one of the experiment-specific opaque links (not the root URL):
- `http://13.63.182.207/pfdkr`
- `http://13.63.182.207/ytnqm`
- `http://13.63.182.207/hcslv`
- `http://13.63.182.207/rbxjw`
- `http://13.63.182.207/mkgza`
- `http://13.63.182.207/uqnpe`

Each link maps to a different condition and its own task/tutorial JSON files.

## Application Flow

1. **Consent Page**: User must check consent box to continue
2. **Demographics**: User fills out demographic information
3. **Tasks 1-3**: Investment decisions
4. **Confidence/Risk Rating**: User rates confidence and perceived risk
5. **Tasks 4-7**: More investment decisions
6. **Final Results**: Display final amount and collect feedback
7. **Thank You**: Completion message

## File Structure

- `app.py`: Main Dash application with database integration and routing logic
- `application.py`: WSGI entry point for production deployment
- `callbacks.py`: All callback functions for UI interactions and data collection
- `pages.py`: All page rendering functions (consent, demographics, tasks, etc.)
- `components.py`: Reusable UI components for consistent design
- `config.py`: Configuration constants, error messages, and UI settings
- `utils.py`: Utility functions for validation, data processing, and flow control
- `database.py`: PostgreSQL database operations
- `file_logger.py`: File-based logging fallback when database unavailable
- `tasks_data.json`: Stock information for all 7 tasks and investment scenarios
- `tasks_data_e1.json` ... `tasks_data_e6.json`: Main-task variants for six experiment conditions
- `tutorial_tasks_data_e1.json` ... `tutorial_tasks_data_e6.json`: Tutorial variants aligned to each experiment condition
- `schema.sql`: PostgreSQL database schema
- `requirements.txt`: Python dependencies
- `deploy.sh`: Deployment script for AWS EC2
- `nginx.conf`: Nginx reverse proxy configuration
- `market-mindset.service`: Systemd service file for Gunicorn
- `market-mindset.logrotate`: Logrotate policy for Gunicorn access/error logs
- `DEPLOYMENT.md`: Complete AWS deployment guide
- `README.md`: This file

## Data Generation and Stimuli Construction

The investment scenarios used in the application are generated from real-world financial data using a preprocessing pipeline implemented in `massive data.ipynb`.

### Data Source

- Financial data is retrieved using the **Massive API** (https://massive.com/)
- Historical daily price data is collected for a predefined set of publicly traded stocks

---

### Initial Stock Selection

- An initial pool of **14 stocks** is selected to ensure diversity across:
  - industries
  - sectors
  - market capitalizations (large-cap, mid-cap, small-cap)

---

### Data Processing Pipeline

The notebook (`massive data.ipynb`) performs the following steps:

- Fetches historical price data using the Massive API
- Computes daily returns
- Calculates volatility and return-based metrics
- Constructs structured datasets with:
  - price series
  - return distributions
  - volatility estimates
  - metadata (sector, market cap, exchange)

---

### Risk Classification and Selection

- Stocks are classified based on computed volatility and return characteristics
- From the initial pool, **10 stocks are selected**:
  - 5 relatively **low-volatility (stable)** assets
  - 5 relatively **high-volatility (risky)** assets

---

### Stimuli Construction

- Each selected stock is:
  - assigned a **pseudonymous identifier** (e.g., A1, A2)
  - anonymized to remove company names and tickers

- Each stimulus includes:
  - a short company description
  - sector classification
  - summary characteristics derived from processed data

---

### Temporal Setup

- Decision data corresponds to a fixed historical snapshot:
  - **Decision date:** February 19

- Outcomes are computed using forward price movement:
  - **Outcome window:** ~1 month later (March)
---

## Platform development

### System architecture

- **Application language**: Python 3.8+
- **Web framework**: Dash (`dash==2.14.2`) with Dash Bootstrap Components for the UI
- **App server**: Gunicorn (`application:application`) managed by systemd in production
- **Reverse proxy**: Nginx forwards requests to Gunicorn on `127.0.0.1:8050`
- **Primary data layer**: PostgreSQL via `psycopg2` (AWS RDS deployment target)
- **Fallback data layer**: File-based JSONL logging in `logs/` when DB connectivity is unavailable

### Hosting and infrastructure

- **Production target**: AWS EC2 (application host) + AWS RDS PostgreSQL (database)
- **Network model**: RDS access is restricted via security group rules to the application host security group
- **Process supervision**: systemd service (`market-mindset.service`) for restart/recovery behavior

### Data storage model (where and how data is stored)

- **Transactional study data (primary)**: Stored in PostgreSQL tables defined in `schema.sql`
  - `participants`, `demographics`, `task_responses`, `portfolio`, `confidence_risk`, `feedback`, `page_visits`, `events`
- **Fallback/runtime logs (secondary)**: Participant-scoped JSONL files in `logs/`
  - Example pattern: `logs/participant_<uuid>_events.jsonl`
- **Static research inputs**: Versioned files in repository root
  - `tasks_data.json`, `tutorial_tasks_data.json`
  - `market_mindset_final_dataset.csv`, `market_mindset_final_dataset_with_metadata.csv`

### Data captured (participant and study data)

The platform stores the following categories of data for each participant record:

- **Study record metadata**: Random UUID participant ID, created/last-active timestamps, completion flag/time, withdrawal flag/time
- **Demographics**: Age range, gender (and optional self-describe), Hispanic/Latino, race (and optional other), education, employment, executive/shareholder status, exchange/brokerage status, income band, investment experience
- **Task responses**: Task ID, stock tickers/names presented, investment amounts, total invested, remaining amount, task timing
- **Portfolio outcomes**: Invested amount, return %, final value, profit/loss per task
- **Confidence/risk assessments**: Confidence rating, risk rating, attention-check response, checkpoint index
- **Feedback**: Optional free-text feedback
- **Behavioral telemetry**: Page navigation, element interactions (button/input/modal/slider events), event timestamps, and event metadata used for quality control and analysis

### Security and data protection

- **Encryption at rest**: PostgreSQL data can be encrypted at rest using AWS RDS encryption settings (must be enabled in AWS configuration)
- **Network access controls**: Database access is restricted at the network layer using AWS security groups
- **Transport path**: Browser traffic terminates at Nginx and is proxied to Gunicorn internally on localhost
- **Secrets handling**: Database credentials and runtime secrets are loaded from environment variables (`.env`) and are not hard-coded in application source
- **Application-level data minimization target**: Study protocol is to avoid collecting direct identifiers (for example, names/contact details)
- **Proxy/service defaults**: Gunicorn production config writes access/error logs to files under `logs/`; app stdout/stderr can be captured into Gunicorn error logs via `--capture-output`

### Important implementation note for IRB alignment

- Current app flow initializes participants without collecting request IP address or browser user-agent.
- Current database schema and write paths do not include IP address or browser user-agent fields.
- Current withdrawal behavior marks records as withdrawn (`withdrawn=true`) so responses are excluded from analysis rather than automatically deleted.
- Compensation policy: participants who choose to withdraw before completing the study are not paid.

## Customization

### Modifying Stock Data
Edit `tasks_data.json` to change stock information, investment scenarios, or add/remove tasks. Each task contains:
- Stock details (name, ticker, images, descriptions)
- Past week performance and return percentages
- Weekly and monthly analysis text

For the six-experiment setup, update the corresponding condition files (`tasks_data_e1.json` ... `tasks_data_e6.json` and matching tutorial files) rather than only the base files.

### Changing Initial Amount
In `config.py`, modify the `INITIAL_AMOUNT` constant (default: 1000).

### Adjusting Number of Tasks
Update `NUM_TASKS` in `config.py` and add/remove task objects in `tasks_data.json`.

### Modifying Confidence/Risk Checkpoint
Change `CONFIDENCE_RISK_CHECKPOINT` in `config.py` (default: 3).

For data architecture and security details, see the **Platform development** section above.

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
