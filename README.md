# GEA-GLAB Management Portal

A comprehensive web portal for managing GEA Licensed Assessment Bodies (GLABs), client certifications, and financial operations under the GEA Financial Operations Framework Agreement.

## Features

### 1. Client & Project Management
- Register and manage client organizations
- Create assessment projects with full certification workflow
- Track projects through 6 phases: Proposal → Engagement → Assessment → Reporting → Certification → Post-Certification

### 2. Phase-Based Workflow
Each phase has a standardized checklist based on the GEA Financial Operations Framework:
- **Proposal Phase**: GEA template usage, fee verification, conflict of interest checks
- **Engagement Phase**: Letter of engagement, initial payment (50%), GEA fee remittance
- **Assessment Phase**: Document review, on-site assessment, evidence collection
- **Reporting Phase**: Draft report, peer review, GEA compliance review
- **Certification Phase**: Final payment, certification decision, CDR completion
- **Post-Certification**: Surveillance scheduling, change notification monitoring

### 3. Document Management
- Upload documents (proposals, invoices, reports, certificates, etc.)
- Review and approve/deny/request changes
- Track document status through certification process

### 4. Financial Tracking
- Automatic 15% GEA fee calculation
- Payment tracking (50% initial, 50% final)
- GEA fee remittance tracking
- Monthly financial reports per Article 11

### 5. GEA Admin Features
- Review and approve GLAB proposals (Article 4.2)
- Manage multiple GLABs
- Financial oversight across all GLABs
- Pre-approval status management

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Navigate to the portal directory:**
   ```bash
   cd GLAB_Portal
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Access the portal:**
   Open your browser and go to: `http://localhost:5000`

## Default Login Credentials

### GEA Admin
- **Username:** `admin`
- **Password:** `admin123`

### GLAB Admin (Sample)
- **Username:** `glabadmin`
- **Password:** `glab123`

⚠️ **Important:** Change these default passwords in production!

## Configuration

### Environment Variables
Set these environment variables for production:

```bash
export SECRET_KEY="your-secure-secret-key"
export FLASK_ENV="production"
```

### Database
By default, the portal uses SQLite (`glab_portal.db`). For production, consider migrating to PostgreSQL or MySQL.

## Project Structure

```
GLAB_Portal/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── uploads/              # Document uploads directory
├── templates/            # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── login.html        # Login page
│   ├── dashboard_gea.html    # GEA admin dashboard
│   ├── dashboard_glab.html   # GLAB dashboard
│   ├── clients/          # Client management templates
│   ├── projects/         # Project management templates
│   ├── glabs/            # GLAB management templates
│   ├── documents/        # Document upload templates
│   ├── reviews/          # GEA review templates
│   ├── financials/       # Financial overview templates
│   ├── reports/          # Report templates
│   └── errors/           # Error page templates
└── static/               # Static assets (CSS, JS)
```

## Usage Guide

### For GLAB Users

1. **Add a Client:**
   - Go to Clients → Add Client
   - Enter organization details

2. **Create a Project:**
   - Go to Projects → New Project
   - Select client, assessment type, and enter fee details
   - System auto-calculates 15% GEA fee

3. **Work Through Phases:**
   - Complete checklist items for each phase
   - Upload required documents
   - Record payments when received
   - Click "Advance to Next Phase" when ready

### For GEA Admins

1. **Review Proposals:**
   - Go to Pending Reviews
   - Review fee calculations and compliance
   - Approve, request adjustment, or reject

2. **Monitor GLABs:**
   - View all GLABs and their projects
   - Track financial compliance
   - Review documents

3. **Financial Oversight:**
   - View total fees and remittances
   - Generate monthly reports

## Security Notes

- Change default passwords immediately
- Use HTTPS in production
- Set a strong SECRET_KEY
- Consider adding rate limiting
- Implement proper backup procedures

## Deployment

### Option 1: Traditional Server (e.g., DigitalOcean, AWS EC2)

1. Set up a Linux server
2. Install Python 3.8+
3. Clone or upload the portal
4. Use Gunicorn + Nginx for production
5. Set up SSL certificate (Let's Encrypt)

### Option 2: Platform as a Service (e.g., Heroku, Railway)

1. Create a `Procfile`:
   ```
   web: gunicorn app:app
   ```
2. Add `gunicorn` to requirements.txt
3. Deploy to your chosen platform

## Support

For questions about the GEA Financial Operations Framework, refer to the agreement document.

## License

Proprietary - Global Excellence Assembly (GEA)
