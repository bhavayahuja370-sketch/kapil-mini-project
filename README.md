# CampusPass — QR Code Based Event Check-in System

A basic individual Python mini project with a college event theme. Built for Bhavay Ahuja, BCA 3-A, Manav Rachna International Institute of Research and Studies.

## Run on Windows

Extract this ZIP, open the campus_checkin folder in VS Code, and open its terminal. Run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:5000 in Chrome or Edge. Keep the terminal running. Press Ctrl+C to stop.

Organizer login: **college123** (local classroom demonstration password).

To choose your own password before starting:

```powershell
$env:ADMIN_PASSWORD = "your-own-password"
.\.venv\Scripts\python.exe app.py
```

## Demonstrate the project

1. Explore the three sample college events and select **Get my pass**.
2. Register with name, college roll number, email and course/section.
3. Download the generated QR image, or print the pass as PDF.
4. Open **Organizer hub**, sign in and select the corresponding event.
5. Start the laptop camera and show the QR on a phone, or upload the downloaded QR image.
6. Check the attendance count and guest list; download the CSV attendance file.
7. Scan the same pass again to demonstrate duplicate check-in prevention.
8. Create a new event and find it on the home page.

Camera and image decoding use the browser's native BarcodeDetector API, available on supported Chrome/Edge installations. Camera access requires permission and localhost or HTTPS. If the browser reports detection unavailable, use a supported Chrome/Edge installation or a USB QR scanner that types into the code field. The manual field expects the QR token, not a pass URL. Downloading the QR itself works independently of browser scan support. The scanner works locally and does not send images to a third-party service.

## Files and technology

- `app.py`: Flask routes, registration, QR generation, organizer login, SQLite and exports.
- `templates/`: Jinja HTML pages.
- `static/style.css`: responsive green, cream and pastel college theme.
- `static/scanner.js`: QR camera/image reader and guest search.
- `requirements.txt`: Python dependencies.
- `test_app.py`: automated workflow checks.
- `campus.db`: generated on first run. Stores events and registrations permanently between restarts.

The font stylesheet is optional and loads from Google Fonts; the app uses fallback fonts when offline. Install Python dependencies once before an offline demonstration. Sample event dates are editable in the seed list before the first launch; existing databases keep their records.

## Project explanation for viva

**Problem:** Manual attendance queues are slow and duplicate entries are hard to track.

**Objective:** Register students, issue unique QR passes, validate entry and maintain attendance automatically.

**Flow:** Student chooses event → enters details → server saves registration → generates QR token → organizer scans token → server validates event and checks prior attendance → saves check-in timestamp → dashboard updates.

**Modules:** Event listing/creation, student registration, QR pass generation, organizer authentication, check-in verification and attendance reporting.

**Database:** `events` has id, title, category, date, venue and description. `registrations` has id, event_id, name, roll, email, course, token and checked_at. One event has many registrations. Event + roll number is unique. QR tokens are unique and randomly generated.

**Validation:** Required fields, duplicate registration protection, organizer-only check-in/export, CSRF protection, invalid/wrong-event QR rejection and an atomic database update to prevent duplicate check-ins.

**Scope:** A local classroom demonstration with one organizer password. A QR is a bearer pass: anyone holding a copy could present it first. It does not independently verify student identity. Real deployment would need individual organizer accounts, password hashing, login rate limits, HTTPS, production hosting, backups and an identity check if required. Restarting resets login sessions unless a persistent SECRET_KEY environment variable is set. Registration email is stored only; the app does not send email.

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_app
```

Tests use a temporary database and do not change your project attendance records.
