# FlightRL Inspector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only FlightRL log inspector tab to the Crazyflie client.

**Architecture:** Keep FlightRL-specific parsing in a small pure-Python model and keep Qt widgets focused on display. The first version loads CSV logs from disk, summarizes available fields, scrubs rows, and draws ranger, decision, and health views without opening any live control path.

**Tech Stack:** Python 3.10+, PyQt6, standard-library `csv`/`unittest`.

---

### Task 1: CSV Log Model

**Files:**
- Create: `src/cfclient/ui/flightrl/log_model.py`
- Create: `tests/test_flightrl_log_model.py`

- [ ] Add `FlightRLLog`, `FlightRLRow`, and `load_log(path)` that parse CSV rows, preserve sparse fields, and expose selected numeric values.
- [ ] Add summary metrics: row count, duration, field groups, min range, max horizontal speed, active fractions, and health flags.
- [ ] Test missing values, `32766` range handling, active flag fractions, and duration calculation with `python -m unittest tests.test_flightrl_log_model`.

### Task 2: Inspector Widgets

**Files:**
- Create: `src/cfclient/ui/flightrl/ranger_widget.py`
- Create: `src/cfclient/ui/flightrl/timeline_widget.py`
- Create: `src/cfclient/ui/flightrl/health_widget.py`

- [ ] Add a ranger bubble widget that paints horizontal ranger rays, vertical clearance, velocity vector, and selected row index.
- [ ] Add a decision timeline widget that paints active intervals for `emergency_active`, `direction_hold_active`, `vertical_priority_active`, `shield_active`, and `raw_control_active`.
- [ ] Add a health widget that shows battery, radio, supervisor, tumble, and motor/battery health states.

### Task 3: FlightRL Inspector Tab

**Files:**
- Create: `src/cfclient/ui/tabs/FlightRLInspectorTab.py`
- Modify: `src/cfclient/ui/tabs/__init__.py`

- [ ] Build a `TabToolbox` tab with a log directory picker, file list, summary table, scrubber, current row fields, and the three visual widgets.
- [ ] Default the directory to `/Users/sebastianboehler/Documents/GitHub/FlightRL/artifacts/crazyflie_logs` when present.
- [ ] Register the tab in `cfclient.ui.tabs.available`.

### Task 4: Verification

**Files:**
- Modify only if verification exposes a scoped issue.

- [ ] Run `python -m unittest tests.test_flightrl_log_model`.
- [ ] Run the installed client interpreter compile check: `/Users/sebastianboehler/.local/share/uv/tools/cfclient/bin/python -m compileall -q src/cfclient tests`.
- [ ] Run `cfclient --check-imports`.
- [ ] Confirm no file over 300 LOC was introduced.
