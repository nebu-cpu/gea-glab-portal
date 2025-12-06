"""
GEA-GLAB Management Portal
Comprehensive portal for managing GLAB operations, client certifications, 
documents, and financial tracking under the GEA Financial Operations Framework.
"""

import os
import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'gea-glab-portal-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///glab_portal.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'gif'}

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# =============================================================================
# DATABASE MODELS
# =============================================================================

class User(UserMixin, db.Model):
    """User model for authentication - GEA admins and GLAB users"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'gea_admin', 'glab_admin', 'glab_user'
    glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    glab = db.relationship('GLAB', backref='users')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class GLAB(db.Model):
    """GLAB (Licensed Assessment Body) model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    country = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=True)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default='active')  # active, suspended, terminated
    pre_approved = db.Column(db.Boolean, default=False)  # Pre-Approval Status per Article 4.4
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    clients = db.relationship('Client', backref='glab', lazy='dynamic')
    projects = db.relationship('Project', backref='glab', lazy='dynamic')


class Client(db.Model):
    """Client/Organization seeking certification"""
    id = db.Column(db.Integer, primary_key=True)
    glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    registered_address = db.Column(db.Text, nullable=True)
    country = db.Column(db.String(100), nullable=False)
    industry_sector = db.Column(db.String(100), nullable=True)
    total_employees = db.Column(db.Integer, nullable=True)
    number_of_sites = db.Column(db.Integer, default=1)
    primary_contact_name = db.Column(db.String(100), nullable=True)
    primary_contact_email = db.Column(db.String(120), nullable=False)
    primary_contact_phone = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    projects = db.relationship('Project', backref='client', lazy='dynamic')


class Project(db.Model):
    """Assessment project/engagement"""
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True, nullable=False)
    glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    
    # Assessment Type
    assessment_type = db.Column(db.String(50), nullable=False)  # initial, recertification, surveillance, endorsement, followup
    
    # Current Phase
    current_phase = db.Column(db.String(50), default='proposal')
    # Phases: proposal, engagement, assessment, reporting, certification, post_certification
    
    # Phase Statuses (JSON stored as string for simplicity)
    phase_status = db.Column(db.Text, default='{}')
    
    # Financial Information
    assessment_days = db.Column(db.Integer, nullable=True)
    day_rate = db.Column(db.Float, nullable=True)
    multi_site_premium = db.Column(db.Float, default=0)
    other_fees = db.Column(db.Float, default=0)
    total_assessment_fees = db.Column(db.Float, nullable=True)
    travel_accommodation = db.Column(db.Float, default=0)
    applicable_taxes = db.Column(db.Float, default=0)
    
    # GEA Fee (15%)
    net_assessment_fees = db.Column(db.Float, nullable=True)
    gea_fee = db.Column(db.Float, nullable=True)
    glab_revenue = db.Column(db.Float, nullable=True)
    
    # Payment Tracking
    initial_payment_received = db.Column(db.Boolean, default=False)
    initial_payment_date = db.Column(db.DateTime, nullable=True)
    initial_payment_amount = db.Column(db.Float, nullable=True)
    final_payment_received = db.Column(db.Boolean, default=False)
    final_payment_date = db.Column(db.DateTime, nullable=True)
    final_payment_amount = db.Column(db.Float, nullable=True)
    
    # GEA Fee Remittance
    gea_fee_remitted = db.Column(db.Boolean, default=False)
    gea_fee_remittance_date = db.Column(db.DateTime, nullable=True)
    
    # Timeline
    proposed_start_date = db.Column(db.DateTime, nullable=True)
    document_review_date = db.Column(db.DateTime, nullable=True)
    onsite_assessment_start = db.Column(db.DateTime, nullable=True)
    onsite_assessment_end = db.Column(db.DateTime, nullable=True)
    draft_report_date = db.Column(db.DateTime, nullable=True)
    final_report_date = db.Column(db.DateTime, nullable=True)
    certification_decision_date = db.Column(db.DateTime, nullable=True)
    
    # Assessment Team
    lead_assessor = db.Column(db.String(100), nullable=True)
    technical_specialist = db.Column(db.String(100), nullable=True)
    additional_team_members = db.Column(db.Text, nullable=True)
    
    # GEA Review
    gea_proposal_status = db.Column(db.String(20), default='pending')  # pending, approved, adjustment_required, rejected
    gea_reviewer = db.Column(db.String(100), nullable=True)
    gea_review_date = db.Column(db.DateTime, nullable=True)
    gea_review_notes = db.Column(db.Text, nullable=True)
    
    # Certification Outcome
    certification_status = db.Column(db.String(50), nullable=True)  # pending, full, conditional, endorsement, deferred, denied
    certification_date = db.Column(db.DateTime, nullable=True)
    certification_expiry = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    documents = db.relationship('Document', backref='project', lazy='dynamic')
    checklist_items = db.relationship('ChecklistItem', backref='project', lazy='dynamic')
    phase_logs = db.relationship('PhaseLog', backref='project', lazy='dynamic')


class Document(db.Model):
    """Document uploads and tracking"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    
    # Document Info
    document_type = db.Column(db.String(50), nullable=False)
    # Types: proposal, letter_of_engagement, invoice, payment_proof, assessment_report, 
    #        certification_certificate, other
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    
    # Review Status
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, changes_requested
    reviewed_by = db.Column(db.String(100), nullable=True)
    review_date = db.Column(db.DateTime, nullable=True)
    review_notes = db.Column(db.Text, nullable=True)
    
    # Metadata
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=True)


class ChecklistItem(db.Model):
    """Standard checklist items for each phase"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    phase = db.Column(db.String(50), nullable=False)
    item_text = db.Column(db.Text, nullable=False)
    is_required = db.Column(db.Boolean, default=True)
    is_completed = db.Column(db.Boolean, default=False)
    completed_by = db.Column(db.String(100), nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    order = db.Column(db.Integer, default=0)


class PhaseLog(db.Model):
    """Audit log for phase transitions"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    from_phase = db.Column(db.String(50), nullable=True)
    to_phase = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # created, advanced, reverted, completed
    performed_by = db.Column(db.String(100), nullable=True)
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)


class FinancialReport(db.Model):
    """Monthly financial reports from GLABs"""
    id = db.Column(db.Integer, primary_key=True)
    glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'), nullable=False)
    reporting_period = db.Column(db.String(20), nullable=False)  # YYYY-MM
    
    # Engagement Summary
    new_engagements = db.Column(db.Integer, default=0)
    completed_engagements = db.Column(db.Integer, default=0)
    in_progress_engagements = db.Column(db.Integer, default=0)
    
    # Financial Summary
    total_invoiced = db.Column(db.Float, default=0)
    total_payments_received = db.Column(db.Float, default=0)
    gea_fees_due = db.Column(db.Float, default=0)
    gea_fees_remitted = db.Column(db.Float, default=0)
    
    # Status
    is_nil_activity = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='draft')  # draft, submitted, reviewed, confirmed
    reviewed_by = db.Column(db.String(100), nullable=True)
    review_date = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    submitted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    
    glab = db.relationship('GLAB', backref='financial_reports')


# =============================================================================
# STANDARD CHECKLIST TEMPLATES
# =============================================================================

PHASE_CHECKLISTS = {
    'proposal': [
        ('Prepare proposal using GEA-approved template', True),
        ('Verify fee is within approved Fee Schedule ranges', True),
        ('Confirm scope and timeline appropriate for organization', True),
        ('Verify assessment team composition is adequate', True),
        ('Check for conflicts of interest', True),
        ('Submit proposal to GEA Portal for review', True),
        ('Await GEA acknowledgment before issuing to client', True),
    ],
    'engagement': [
        ('Receive signed Letter of Engagement from client', True),
        ('Upload Letter of Engagement to portal within 5 days', True),
        ('Confirm initial payment (50%) received', True),
        ('Upload proof of initial payment', True),
        ('Remit GEA fee for initial payment within 5 days', True),
        ('Assign assessment team', True),
        ('Schedule document review phase', True),
    ],
    'assessment': [
        ('Complete document review', True),
        ('Send assessment plan to client', True),
        ('Conduct opening meeting', True),
        ('Execute on-site assessment', True),
        ('Collect and verify evidence', True),
        ('Conduct closing meeting', True),
        ('Complete assessment findings documentation', True),
    ],
    'reporting': [
        ('Prepare draft assessment report', True),
        ('Submit draft report for peer review', True),
        ('Address peer review feedback', True),
        ('Finalize assessment report', True),
        ('Upload final report to portal', True),
        ('Submit report to GEA for compliance review', True),
        ('Deliver final report to client', True),
    ],
    'certification': [
        ('Receive final payment (50%) from client', True),
        ('Upload proof of final payment', True),
        ('Remit GEA fee for final payment within 5 days', True),
        ('Submit to certification committee', True),
        ('Receive certification decision', True),
        ('Issue certification certificate (if approved)', True),
        ('Complete Certification Decision Record (CDR)', True),
        ('Send feedback report to organization', True),
    ],
    'post_certification': [
        ('Schedule surveillance assessment (annual)', True),
        ('Set up change notification monitoring', True),
        ('Plan for recertification (3-year cycle)', True),
        ('Document lessons learned', True),
        ('Archive project documentation', True),
    ],
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_reference_number(glab_license, year=None):
    """Generate unique project reference number"""
    if year is None:
        year = datetime.now().year
    count = Project.query.filter(
        Project.reference_number.like(f'GEA-{glab_license}-{year}%')
    ).count() + 1
    return f'GEA-{glab_license}-{year}-{count:04d}'


def calculate_fees(assessment_days, day_rate, multi_site_premium=0, other_fees=0):
    """Calculate assessment fees and GEA fee (15%)"""
    assessment_fees = (assessment_days * day_rate) + multi_site_premium + other_fees
    net_fees = assessment_fees  # Before taxes
    gea_fee = net_fees * 0.15
    glab_revenue = net_fees * 0.85
    return {
        'total_assessment_fees': assessment_fees,
        'net_assessment_fees': net_fees,
        'gea_fee': gea_fee,
        'glab_revenue': glab_revenue
    }


def create_checklist_for_project(project_id, phase):
    """Create checklist items for a project phase"""
    items = PHASE_CHECKLISTS.get(phase, [])
    for idx, (item_text, is_required) in enumerate(items):
        checklist_item = ChecklistItem(
            project_id=project_id,
            phase=phase,
            item_text=item_text,
            is_required=is_required,
            order=idx
        )
        db.session.add(checklist_item)
    db.session.commit()


def log_phase_change(project_id, from_phase, to_phase, action, user=None, notes=None):
    """Log phase transitions"""
    log = PhaseLog(
        project_id=project_id,
        from_phase=from_phase,
        to_phase=to_phase,
        action=action,
        performed_by=user,
        notes=notes
    )
    db.session.add(log)
    db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Role-based access decorator
def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# =============================================================================
# ROUTES - AUTHENTICATION
# =============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# =============================================================================
# ROUTES - DASHBOARD
# =============================================================================

@app.route('/')
@login_required
def dashboard():
    """Main dashboard with overview"""
    if current_user.role == 'gea_admin':
        # GEA Admin sees all GLABs and all projects
        glabs = GLAB.query.all()
        projects = Project.query.order_by(Project.updated_at.desc()).limit(20).all()
        pending_reviews = Project.query.filter_by(gea_proposal_status='pending').count()
        pending_documents = Document.query.filter_by(status='pending').count()
        
        # Financial overview
        total_gea_fees_due = db.session.query(db.func.sum(Project.gea_fee)).filter(
            Project.gea_fee_remitted == False,
            Project.gea_fee != None
        ).scalar() or 0
        
        return render_template('dashboard_gea.html',
                             glabs=glabs,
                             projects=projects,
                             pending_reviews=pending_reviews,
                             pending_documents=pending_documents,
                             total_gea_fees_due=total_gea_fees_due)
    else:
        # GLAB user sees their own projects
        glab = current_user.glab
        if not glab:
            flash('Your account is not associated with a GLAB.', 'error')
            return redirect(url_for('logout'))
        
        projects = Project.query.filter_by(glab_id=glab.id).order_by(Project.updated_at.desc()).all()
        clients = Client.query.filter_by(glab_id=glab.id).all()
        
        # Phase summary
        phase_counts = {}
        for phase in ['proposal', 'engagement', 'assessment', 'reporting', 'certification', 'post_certification']:
            phase_counts[phase] = Project.query.filter_by(glab_id=glab.id, current_phase=phase).count()
        
        return render_template('dashboard_glab.html',
                             glab=glab,
                             projects=projects,
                             clients=clients,
                             phase_counts=phase_counts)


# =============================================================================
# ROUTES - GLAB MANAGEMENT (GEA Admin only)
# =============================================================================

@app.route('/glabs')
@login_required
@role_required('gea_admin')
def list_glabs():
    """List all GLABs"""
    glabs = GLAB.query.all()
    return render_template('glabs/list.html', glabs=glabs)


@app.route('/glabs/new', methods=['GET', 'POST'])
@login_required
@role_required('gea_admin')
def new_glab():
    """Create new GLAB"""
    if request.method == 'POST':
        glab = GLAB(
            name=request.form.get('name'),
            license_number=request.form.get('license_number'),
            country=request.form.get('country'),
            address=request.form.get('address'),
            contact_email=request.form.get('contact_email'),
            contact_phone=request.form.get('contact_phone')
        )
        db.session.add(glab)
        db.session.commit()
        
        flash(f'GLAB "{glab.name}" created successfully.', 'success')
        return redirect(url_for('list_glabs'))
    
    return render_template('glabs/form.html', glab=None)


@app.route('/glabs/<int:glab_id>')
@login_required
def view_glab(glab_id):
    """View GLAB details"""
    glab = GLAB.query.get_or_404(glab_id)
    
    # Check access
    if current_user.role != 'gea_admin' and current_user.glab_id != glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    projects = Project.query.filter_by(glab_id=glab_id).order_by(Project.updated_at.desc()).all()
    clients = Client.query.filter_by(glab_id=glab_id).all()
    
    return render_template('glabs/view.html', glab=glab, projects=projects, clients=clients)


# =============================================================================
# ROUTES - CLIENT MANAGEMENT
# =============================================================================

@app.route('/clients')
@login_required
def list_clients():
    """List clients"""
    if current_user.role == 'gea_admin':
        clients = Client.query.all()
    else:
        clients = Client.query.filter_by(glab_id=current_user.glab_id).all()
    
    return render_template('clients/list.html', clients=clients)


@app.route('/clients/new', methods=['GET', 'POST'])
@login_required
def new_client():
    """Create new client"""
    if request.method == 'POST':
        glab_id = current_user.glab_id if current_user.role != 'gea_admin' else request.form.get('glab_id')
        
        client = Client(
            glab_id=glab_id,
            name=request.form.get('name'),
            registered_address=request.form.get('registered_address'),
            country=request.form.get('country'),
            industry_sector=request.form.get('industry_sector'),
            total_employees=request.form.get('total_employees', type=int),
            number_of_sites=request.form.get('number_of_sites', type=int) or 1,
            primary_contact_name=request.form.get('primary_contact_name'),
            primary_contact_email=request.form.get('primary_contact_email'),
            primary_contact_phone=request.form.get('primary_contact_phone')
        )
        db.session.add(client)
        db.session.commit()
        
        flash(f'Client "{client.name}" created successfully.', 'success')
        return redirect(url_for('list_clients'))
    
    glabs = GLAB.query.all() if current_user.role == 'gea_admin' else None
    return render_template('clients/form.html', client=None, glabs=glabs)


@app.route('/clients/<int:client_id>')
@login_required
def view_client(client_id):
    """View client details"""
    client = Client.query.get_or_404(client_id)
    
    # Check access
    if current_user.role != 'gea_admin' and current_user.glab_id != client.glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    projects = Project.query.filter_by(client_id=client_id).all()
    return render_template('clients/view.html', client=client, projects=projects)


# =============================================================================
# ROUTES - PROJECT MANAGEMENT
# =============================================================================

@app.route('/projects')
@login_required
def list_projects():
    """List projects"""
    phase_filter = request.args.get('phase')
    status_filter = request.args.get('status')
    
    query = Project.query
    
    if current_user.role != 'gea_admin':
        query = query.filter_by(glab_id=current_user.glab_id)
    
    if phase_filter:
        query = query.filter_by(current_phase=phase_filter)
    
    if status_filter:
        query = query.filter_by(gea_proposal_status=status_filter)
    
    projects = query.order_by(Project.updated_at.desc()).all()
    
    return render_template('projects/list.html', projects=projects)


@app.route('/projects/new', methods=['GET', 'POST'])
@login_required
def new_project():
    """Create new project"""
    if request.method == 'POST':
        glab_id = current_user.glab_id if current_user.role != 'gea_admin' else request.form.get('glab_id')
        glab = GLAB.query.get(glab_id)
        
        # Generate reference number
        ref_number = generate_reference_number(glab.license_number)
        
        # Calculate fees
        assessment_days = request.form.get('assessment_days', type=int) or 0
        day_rate = request.form.get('day_rate', type=float) or 0
        multi_site_premium = request.form.get('multi_site_premium', type=float) or 0
        other_fees = request.form.get('other_fees', type=float) or 0
        
        fees = calculate_fees(assessment_days, day_rate, multi_site_premium, other_fees)
        
        project = Project(
            reference_number=ref_number,
            glab_id=glab_id,
            client_id=request.form.get('client_id', type=int),
            assessment_type=request.form.get('assessment_type'),
            assessment_days=assessment_days,
            day_rate=day_rate,
            multi_site_premium=multi_site_premium,
            other_fees=other_fees,
            total_assessment_fees=fees['total_assessment_fees'],
            net_assessment_fees=fees['net_assessment_fees'],
            gea_fee=fees['gea_fee'],
            glab_revenue=fees['glab_revenue'],
            travel_accommodation=request.form.get('travel_accommodation', type=float) or 0,
            lead_assessor=request.form.get('lead_assessor'),
            technical_specialist=request.form.get('technical_specialist'),
            notes=request.form.get('notes')
        )
        
        # Parse dates
        for date_field in ['proposed_start_date', 'document_review_date', 'onsite_assessment_start', 
                          'onsite_assessment_end', 'draft_report_date', 'final_report_date']:
            date_value = request.form.get(date_field)
            if date_value:
                setattr(project, date_field, datetime.strptime(date_value, '%Y-%m-%d'))
        
        db.session.add(project)
        db.session.commit()
        
        # Create checklist for initial phase
        create_checklist_for_project(project.id, 'proposal')
        
        # Log phase creation
        log_phase_change(project.id, None, 'proposal', 'created', current_user.username)
        
        flash(f'Project {ref_number} created successfully.', 'success')
        return redirect(url_for('view_project', project_id=project.id))
    
    # Get clients based on role
    if current_user.role == 'gea_admin':
        clients = Client.query.all()
        glabs = GLAB.query.all()
    else:
        clients = Client.query.filter_by(glab_id=current_user.glab_id).all()
        glabs = None
    
    return render_template('projects/form.html', project=None, clients=clients, glabs=glabs)


@app.route('/projects/<int:project_id>')
@login_required
def view_project(project_id):
    """View project details with phase workflow"""
    project = Project.query.get_or_404(project_id)
    
    # Check access
    if current_user.role != 'gea_admin' and current_user.glab_id != project.glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get checklist for current phase
    checklist = ChecklistItem.query.filter_by(
        project_id=project_id,
        phase=project.current_phase
    ).order_by(ChecklistItem.order).all()
    
    # Get all documents
    documents = Document.query.filter_by(project_id=project_id).order_by(Document.uploaded_at.desc()).all()
    
    # Get phase logs
    phase_logs = PhaseLog.query.filter_by(project_id=project_id).order_by(PhaseLog.performed_at.desc()).all()
    
    # Define phase order and names
    phases = [
        ('proposal', 'Proposal & Pre-Approval'),
        ('engagement', 'Engagement & Contract'),
        ('assessment', 'Assessment Execution'),
        ('reporting', 'Reporting & Review'),
        ('certification', 'Certification Decision'),
        ('post_certification', 'Post-Certification')
    ]
    
    return render_template('projects/view.html',
                         project=project,
                         checklist=checklist,
                         documents=documents,
                         phase_logs=phase_logs,
                         phases=phases)


@app.route('/projects/<int:project_id>/advance-phase', methods=['POST'])
@login_required
def advance_phase(project_id):
    """Advance project to next phase"""
    project = Project.query.get_or_404(project_id)
    
    # Check access
    if current_user.role != 'gea_admin' and current_user.glab_id != project.glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    phase_order = ['proposal', 'engagement', 'assessment', 'reporting', 'certification', 'post_certification']
    current_idx = phase_order.index(project.current_phase)
    
    # Check if all required checklist items are completed
    incomplete = ChecklistItem.query.filter_by(
        project_id=project_id,
        phase=project.current_phase,
        is_required=True,
        is_completed=False
    ).count()
    
    if incomplete > 0:
        flash(f'{incomplete} required checklist items are incomplete.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    # For proposal phase, check GEA approval
    if project.current_phase == 'proposal' and project.gea_proposal_status != 'approved':
        flash('Project must be approved by GEA before advancing.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    if current_idx < len(phase_order) - 1:
        old_phase = project.current_phase
        new_phase = phase_order[current_idx + 1]
        project.current_phase = new_phase
        
        # Create checklist for new phase
        create_checklist_for_project(project_id, new_phase)
        
        # Log phase change
        log_phase_change(project_id, old_phase, new_phase, 'advanced', current_user.username)
        
        db.session.commit()
        flash(f'Project advanced to {new_phase.replace("_", " ").title()} phase.', 'success')
    else:
        flash('Project is already at the final phase.', 'info')
    
    return redirect(url_for('view_project', project_id=project_id))


@app.route('/projects/<int:project_id>/checklist/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_checklist(project_id, item_id):
    """Toggle checklist item completion"""
    item = ChecklistItem.query.get_or_404(item_id)
    
    if item.project_id != project_id:
        return jsonify({'error': 'Invalid item'}), 400
    
    item.is_completed = not item.is_completed
    if item.is_completed:
        item.completed_by = current_user.username
        item.completed_at = datetime.utcnow()
    else:
        item.completed_by = None
        item.completed_at = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_completed': item.is_completed,
        'completed_by': item.completed_by,
        'completed_at': item.completed_at.isoformat() if item.completed_at else None
    })


# =============================================================================
# ROUTES - DOCUMENT MANAGEMENT
# =============================================================================

@app.route('/projects/<int:project_id>/documents/upload', methods=['GET', 'POST'])
@login_required
def upload_document(project_id):
    """Upload document to project"""
    project = Project.query.get_or_404(project_id)
    
    # Check access
    if current_user.role != 'gea_admin' and current_user.glab_id != project.glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Secure filename and add unique identifier
            original_filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
            
            # Create project-specific folder
            project_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(project_id))
            os.makedirs(project_folder, exist_ok=True)
            
            file_path = os.path.join(project_folder, unique_filename)
            file.save(file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Create document record
            document = Document(
                project_id=project_id,
                document_type=request.form.get('document_type'),
                filename=unique_filename,
                original_filename=original_filename,
                file_path=file_path,
                file_size=file_size,
                uploaded_by=current_user.id,
                description=request.form.get('description')
            )
            db.session.add(document)
            db.session.commit()
            
            flash('Document uploaded successfully.', 'success')
            return redirect(url_for('view_project', project_id=project_id))
        else:
            flash('Invalid file type.', 'error')
    
    document_types = [
        ('proposal', 'Proposal'),
        ('letter_of_engagement', 'Letter of Engagement'),
        ('invoice', 'Invoice'),
        ('payment_proof', 'Proof of Payment'),
        ('assessment_report', 'Assessment Report'),
        ('certification_certificate', 'Certification Certificate'),
        ('other', 'Other')
    ]
    
    return render_template('documents/upload.html', project=project, document_types=document_types)


@app.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    """Download document"""
    document = Document.query.get_or_404(document_id)
    project = Project.query.get(document.project_id)
    
    # Check access
    if current_user.role != 'gea_admin' and current_user.glab_id != project.glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    directory = os.path.dirname(document.file_path)
    return send_from_directory(directory, document.filename, 
                              as_attachment=True, 
                              download_name=document.original_filename)


@app.route('/documents/<int:document_id>/review', methods=['POST'])
@login_required
@role_required('gea_admin')
def review_document(document_id):
    """Review document - approve, reject, or request changes"""
    document = Document.query.get_or_404(document_id)
    
    action = request.form.get('action')
    notes = request.form.get('notes')
    
    if action in ['approved', 'rejected', 'changes_requested']:
        document.status = action
        document.reviewed_by = current_user.username
        document.review_date = datetime.utcnow()
        document.review_notes = notes
        
        db.session.commit()
        flash(f'Document {action.replace("_", " ")}.', 'success')
    else:
        flash('Invalid action.', 'error')
    
    return redirect(url_for('view_project', project_id=document.project_id))


# =============================================================================
# ROUTES - GEA REVIEW (Proposal Approval)
# =============================================================================

@app.route('/reviews')
@login_required
@role_required('gea_admin')
def pending_reviews():
    """List projects pending GEA review"""
    projects = Project.query.filter_by(gea_proposal_status='pending').order_by(Project.created_at).all()
    return render_template('reviews/list.html', projects=projects)


@app.route('/projects/<int:project_id>/review', methods=['GET', 'POST'])
@login_required
@role_required('gea_admin')
def review_project(project_id):
    """Review project proposal"""
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        action = request.form.get('action')
        notes = request.form.get('notes')
        
        if action in ['approved', 'adjustment_required', 'rejected']:
            project.gea_proposal_status = action
            project.gea_reviewer = current_user.username
            project.gea_review_date = datetime.utcnow()
            project.gea_review_notes = notes
            
            db.session.commit()
            flash(f'Project proposal {action.replace("_", " ")}.', 'success')
            return redirect(url_for('pending_reviews'))
        else:
            flash('Invalid action.', 'error')
    
    return render_template('reviews/review.html', project=project)


# =============================================================================
# ROUTES - FINANCIAL MANAGEMENT
# =============================================================================

@app.route('/financials')
@login_required
def financial_overview():
    """Financial overview"""
    if current_user.role == 'gea_admin':
        # GEA sees all financial data
        projects = Project.query.filter(Project.total_assessment_fees > 0).all()
        
        total_fees = sum(p.total_assessment_fees or 0 for p in projects)
        total_gea_fees = sum(p.gea_fee or 0 for p in projects)
        total_remitted = sum(p.gea_fee or 0 for p in projects if p.gea_fee_remitted)
        total_outstanding = total_gea_fees - total_remitted
        
        return render_template('financials/overview_gea.html',
                             projects=projects,
                             total_fees=total_fees,
                             total_gea_fees=total_gea_fees,
                             total_remitted=total_remitted,
                             total_outstanding=total_outstanding)
    else:
        # GLAB sees their financial data
        glab = current_user.glab
        projects = Project.query.filter_by(glab_id=glab.id).filter(Project.total_assessment_fees > 0).all()
        
        total_fees = sum(p.total_assessment_fees or 0 for p in projects)
        total_glab_revenue = sum(p.glab_revenue or 0 for p in projects)
        total_gea_fees = sum(p.gea_fee or 0 for p in projects)
        total_remitted = sum(p.gea_fee or 0 for p in projects if p.gea_fee_remitted)
        
        return render_template('financials/overview_glab.html',
                             glab=glab,
                             projects=projects,
                             total_fees=total_fees,
                             total_glab_revenue=total_glab_revenue,
                             total_gea_fees=total_gea_fees,
                             total_remitted=total_remitted)


@app.route('/projects/<int:project_id>/record-payment', methods=['POST'])
@login_required
def record_payment(project_id):
    """Record payment received"""
    project = Project.query.get_or_404(project_id)
    
    # Check access
    if current_user.role != 'gea_admin' and current_user.glab_id != project.glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    payment_type = request.form.get('payment_type')
    amount = request.form.get('amount', type=float)
    date_str = request.form.get('payment_date')
    payment_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.utcnow()
    
    if payment_type == 'initial':
        project.initial_payment_received = True
        project.initial_payment_date = payment_date
        project.initial_payment_amount = amount
    elif payment_type == 'final':
        project.final_payment_received = True
        project.final_payment_date = payment_date
        project.final_payment_amount = amount
    
    db.session.commit()
    flash('Payment recorded successfully.', 'success')
    
    return redirect(url_for('view_project', project_id=project_id))


@app.route('/projects/<int:project_id>/record-remittance', methods=['POST'])
@login_required
def record_remittance(project_id):
    """Record GEA fee remittance"""
    project = Project.query.get_or_404(project_id)
    
    # Check access
    if current_user.role != 'gea_admin' and current_user.glab_id != project.glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    date_str = request.form.get('remittance_date')
    remittance_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else datetime.utcnow()
    
    project.gea_fee_remitted = True
    project.gea_fee_remittance_date = remittance_date
    
    db.session.commit()
    flash('GEA fee remittance recorded.', 'success')
    
    return redirect(url_for('view_project', project_id=project_id))


# =============================================================================
# ROUTES - REPORTS
# =============================================================================

@app.route('/reports/monthly', methods=['GET', 'POST'])
@login_required
def monthly_report():
    """Monthly financial report"""
    if current_user.role == 'gea_admin':
        glabs = GLAB.query.all()
        selected_glab_id = request.args.get('glab_id', type=int)
    else:
        glabs = None
        selected_glab_id = current_user.glab_id
    
    period = request.args.get('period', datetime.now().strftime('%Y-%m'))
    year, month = map(int, period.split('-'))
    
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # Build query
    query = Project.query.filter(
        Project.created_at >= start_date,
        Project.created_at < end_date
    )
    
    if selected_glab_id:
        query = query.filter_by(glab_id=selected_glab_id)
    
    projects = query.all()
    
    # Calculate summary
    new_engagements = len([p for p in projects if p.created_at >= start_date])
    total_invoiced = sum(p.total_assessment_fees or 0 for p in projects)
    total_gea_fees = sum(p.gea_fee or 0 for p in projects)
    
    return render_template('reports/monthly.html',
                         glabs=glabs,
                         selected_glab_id=selected_glab_id,
                         period=period,
                         projects=projects,
                         new_engagements=new_engagements,
                         total_invoiced=total_invoiced,
                         total_gea_fees=total_gea_fees)


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/api/projects/<int:project_id>/fees', methods=['POST'])
@login_required
def calculate_project_fees(project_id):
    """API to recalculate project fees"""
    project = Project.query.get_or_404(project_id)
    
    data = request.get_json()
    
    assessment_days = data.get('assessment_days', project.assessment_days or 0)
    day_rate = data.get('day_rate', project.day_rate or 0)
    multi_site_premium = data.get('multi_site_premium', project.multi_site_premium or 0)
    other_fees = data.get('other_fees', project.other_fees or 0)
    
    fees = calculate_fees(assessment_days, day_rate, multi_site_premium, other_fees)
    
    return jsonify(fees)


@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats():
    """API for dashboard statistics"""
    if current_user.role == 'gea_admin':
        total_glabs = GLAB.query.count()
        total_projects = Project.query.count()
        pending_reviews = Project.query.filter_by(gea_proposal_status='pending').count()
        total_fees = db.session.query(db.func.sum(Project.gea_fee)).scalar() or 0
        
        return jsonify({
            'total_glabs': total_glabs,
            'total_projects': total_projects,
            'pending_reviews': pending_reviews,
            'total_fees': total_fees
        })
    else:
        glab_id = current_user.glab_id
        total_clients = Client.query.filter_by(glab_id=glab_id).count()
        total_projects = Project.query.filter_by(glab_id=glab_id).count()
        active_projects = Project.query.filter_by(glab_id=glab_id).filter(
            Project.current_phase != 'post_certification'
        ).count()
        
        return jsonify({
            'total_clients': total_clients,
            'total_projects': total_projects,
            'active_projects': active_projects
        })


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db():
    """Initialize database with default data"""
    db.create_all()
    
    # Check if admin user exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        # Create default GEA admin
        admin = User(
            username='admin',
            email='admin@gea.org',
            role='gea_admin'
        )
        admin.set_password('admin123')  # Change this in production!
        db.session.add(admin)
        
        # Create a sample GLAB
        sample_glab = GLAB(
            name='Sample GLAB - Middle East',
            license_number='GLAB-ME001',
            country='United Arab Emirates',
            address='Dubai, UAE',
            contact_email='contact@sampleglab.com',
            contact_phone='+971-4-123-4567'
        )
        db.session.add(sample_glab)
        db.session.commit()
        
        # Create GLAB admin user
        glab_admin = User(
            username='glabadmin',
            email='admin@sampleglab.com',
            role='glab_admin',
            glab_id=sample_glab.id
        )
        glab_admin.set_password('glab123')  # Change this in production!
        db.session.add(glab_admin)
        
        db.session.commit()
        print("Database initialized with default users.")
        print("GEA Admin: username='admin', password='admin123'")
        print("GLAB Admin: username='glabadmin', password='glab123'")


# =============================================================================
# MAIN
# =============================================================================

# Initialize database on startup (for Railway/Gunicorn)
with app.app_context():
    init_db()

if __name__ == '__main__':
    # Run the app locally
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
