---
name: App Overview
description: Architecture, study flow, experiments, infrastructure, known issues, and gotchas for the Stock Market Mindset app
type: project
---

# Stock Market Mindset — App Overview

## What It Is
A Plotly Dash (Flask/WSGI) web app for a UChicago research study on investment decision-making. Participants make simulated stock investment decisions across 10 tasks, with 2 tutorial tasks first. Runs on AWS, recruited via Prolific.

**IRB:** IRB26-0568  
**PI:** Henry K. Dambanemuya  
**Researcher:** Amrita Pathak  
**Payment:** $2.50 base + $10 bonus for top 10 performers  

---

## Infrastructure
- **EC2:** 6 × t3.large (2 vCPU, 8GB RAM), T3 Unlimited enabled, eu-north-1
- **Gunicorn:** `gthread` worker class, 4 workers × 4 threads = 16 concurrent slots
- **Nginx:** reverse proxy on port 80 → Gunicorn on 127.0.0.1:8050
- **RDS:** db.t4g.medium PostgreSQL (2 vCPU, 4GB RAM, ~450 max_connections), eu-north-1. T3 Unlimited is on by default for RDS T4g.
- **DB pool:** max 20 connections per instance (20 × 6 = 120 total, well within 450 limit)
- **Service file:** `market-mindset.service` — systemd unit, logs to `logs/access.log` and `logs/error.log`
- **Deploy:** `./deploy.sh` — git pull, pip install, systemctl restart

---

## Experiments (6 conditions)

| Key | Slug | URL path | Profit/Loss | Information | Info cost mode | Completion code |
|-----|------|----------|-------------|-------------|----------------|-----------------|
| e1  | pfdkr | /pfdkr | Yes | Yes | fixed | A3F91D6C24 |
| e2  | ytnqm | /ytnqm | Yes | Yes | variable | F0D428EEAC |
| e3  | hcslv | /hcslv | Yes | No | none | 852242C9B0 |
| e4  | rbxjw | /rbxjw | No | Yes | fixed | 0BA073AFF8 |
| e5  | mkgza | /mkgza | No | Yes | variable | E77E5AC7D3 |
| e6  | uqnpe | /uqnpe | No | No | none | 720B2C10EB |

Participants arrive via `http://<ec2-ip>/<slug>?participantId=...&assignmentId=...&projectId=...`  
Each EC2 instance runs one experiment. All 6 run in parallel.

---

## Study Flow
```
consent → demographics → tutorial_1 → tutorial_2 → task (×10) → [confidence_risk after each task] → [attention_check after tasks 3, 7] → feedback → debrief → thank_you
```
- Tutorial amount: $100 (`TUTORIAL_INITIAL_AMOUNT`)
- Main task amount: resets to $1000 (`INITIAL_AMOUNT`) on transition from tutorial_2 → task_1
- Profit/loss is feedback only — not added/subtracted from available balance across tasks
- Task order is randomized per participant on session start

---

## Key Files

| File | Role |
|------|------|
| `app.py` | Dash app init, persistent layout, all `dcc.Store` definitions |
| `callbacks.py` | All Dash callbacks — page navigation, task submission, modals, logging |
| `pages.py` | Page rendering functions (pure layout, no logic) |
| `config.py` | Experiment definitions, slider config, demographics options, constants |
| `database.py` | All DB operations — psycopg2, ThreadedConnectionPool, retry logic |
| `utils.py` | `validate_investment`, `validate_total_investment`, `get_task_data_safe` |
| `components.py` | Reusable UI helpers (buttons, alerts, sliders, etc.) |
| `schema.sql` | PostgreSQL schema |
| `tasks_data_e{1-6}.json` | Main task data per experiment |
| `tutorial_tasks_data_e{1-6}.json` | Tutorial task data per experiment |

---

## State Management
All state lives in `dcc.Store` components with `storage_type='memory'` (resets on refresh):
- `participant-id` — UUID
- `experiment-key` — e1–e6
- `current-page` — drives `display_page` callback
- `current-task` — 1-indexed task counter
- `task-order` — randomized list of task IDs
- `amount` — available balance
- `purchased-info` — list of purchased info bundles (reset between tutorial_1 and tutorial_2)
- `portfolio`, `task-responses`, `confidence-risk`, etc.

Modals (`cost-modal`, `stock-modal`, `cr-modal`) live in the persistent layout, not in `page-content`.

---

## Known Issues / Gotchas

### Logging bug (unfixed)
`handle_cost_confirmation` in `callbacks.py` hardcodes `page_name='task'` for all log_event calls, even when called from tutorial pages. This makes it impossible to distinguish tutorial vs. task info events in the DB. Events logged as `page=task` may actually be tutorial_1 or tutorial_2 events.

### Dropout root causes (from first run, e1, 72 participants, 44 completed)
1. **~8 participants** — last action `modal_close` then nothing. After closing info modal, users don't scroll to/see the investment form. Likely submit button below fold.
2. **3 participants** — 5 consecutive `validation_error` (investment_exceeds) in ~2.5s. Error message not visible/actionable enough.
3. **2 participants** — clicked "Purchase Information" → clicked "Cancel" in cost modal → stuck. Continue button remains disabled, no guidance to retry.
4. **4 participants** — navigated to tutorial_1 but did nothing (some showed double demographics submits suggesting server lag perception).

### Dash callback behavior
- `dcc.Store` with `storage_type='memory'` resets on page refresh — participants who refresh lose all state
- `allow_duplicate=True` outputs always fire even if value is unchanged — downstream callbacks always trigger
- `prevent_initial_call='initial_duplicate'` on `display_page` — only prevents the very first duplicate fire

### Tutorial info purchase
- Tutorial_1: Continue button starts disabled; enabled as soon as `purchased-info` is non-empty (purchase required, viewing not required)
- Tutorial_2: `purchased-info` is reset to `[]` on entry (intentional — re-purchase required). Info buttons start disabled until purchase.
- `enable_tutorial_1_button` triggers on `Input('stock-modal', 'is_open')` — fires even on False→False because Dash always sends outputs to client

---

## Performance Notes
- First run: peak 11 requests/second observed in access logs. With old 6 sync workers this caused queuing. Now 16 gthread slots.
- Access log now includes `%(D)s` (response time in microseconds) — use future logs to confirm if DB latency is a bottleneck
- If DB latency is confirmed as bottleneck: make event logging fire-and-forget in a background thread (callback doesn't need to wait for log write)
