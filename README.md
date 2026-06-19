# After-Sales Service & Warranty Claim System

A complete full-stack web application for SRI VENKATA SAI FURNITURE WORKS to manage customer service requests, warranty claims, and technician assignments.

## Project Structure
- `frontend/`: Vanilla HTML/CSS/JS frontend application.
- `backend/`: Python Flask REST API backend.
- `database/`: Database schemas and seed data.
- `docs/`: Additional documentation.

## Tech Stack
- **Frontend**: HTML5, CSS3, Vanilla JavaScript, Chart.js
- **Backend**: Python, Flask, Flask-Session
- **Database**: MySQL

## Setup Instructions

### Database (MySQL)
1. Ensure MySQL is installed and running.
2. Create a database named `furniture_service`.
3. Import the schema and seed data:
   ```bash
   mysql -u root -p furniture_service < database/schema.sql
   mysql -u root -p furniture_service < database/seed.sql
   ```

### Backend (Flask)
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `backend/` directory with the following variables:
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your_secret_key_here
   DB_HOST=localhost
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   DB_NAME=furniture_service
   ```
5. Run the Flask server:
   ```bash
   flask run
   ```
   The backend will run on `http://127.0.0.1:5000`.

### Frontend
1. The frontend can be served statically. You can use an extension like VS Code Live Server or a simple Python server:
   ```bash
   cd frontend
   python -m http.server 3000
   ```
2. Alternatively, configure the Flask app to serve the `frontend/` directory as its static folder.
3. Access the application at `http://localhost:3000` (or `http://127.0.0.1:5000` if served via Flask).

## Default Accounts
- **Admin**: `admin` / `admin123`

## Deployment Guidelines
- **Frontend (Vercel)**: Point Vercel to the `frontend` folder and configure it as a static site.
- **Backend (Render)**: Set the root directory to `backend`, use `pip install -r requirements.txt` as build command, and `gunicorn app:app` as start command. Add Environment Variables.
- **Database (Railway/Supabase)**: Create a MySQL database and update the `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` in the backend environment variables.
