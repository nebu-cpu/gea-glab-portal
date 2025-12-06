"""
GEA Portal - GLAB Management System
Comprehensive portal for managing GLAB operations, client certifications, 
documents, and financial tracking under the GEA Standard.
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
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///glab_portal_v2.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['TEMPLATES_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'phase_templates')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'gif'}

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMPLATES_FOLDER'], exist_ok=True)

# =============================================================================
# 8 PHASES DEFINITION (from GEAS-Doc Set & Workflow Order)
# =============================================================================

PHASES = {
    1: {
        'name': 'Expression of Interest & Enrollment',
        'key': 'enrollment',
        'documents': [
            {'key': 'enrollment_form', 'name': 'GEA Certification Enrollment Form', 'required': True},
            {'key': 'readiness_checklist', 'name': 'Enrollment Readiness Criteria/Checklist', 'required': True},
        ],
        'default_checklist': [
            'Receive expression of interest from organization',
            'Review enrollment form for completeness',
            'Verify organization eligibility',
            'Capture baseline profile',
            'Make eligibility decision (accept/defer/request info)',
            'Notify organization of decision',
        ]
    },
    2: {
        'name': 'Ethical Safeguards & Assessor Assignment',
        'key': 'safeguards',
        'documents': [
            {'key': 'coi_declaration', 'name': 'Conflict of Interest Declaration', 'required': True},
            {'key': 'code_of_conduct', 'name': 'Assessor Code of Conduct & Posture Guide', 'required': True},
            {'key': 'assessor_checklist', 'name': 'GEA Assessor Checklist', 'required': True},
        ],
        'default_checklist': [
            'Assign assessor(s) to the project',
            'Complete Conflict of Interest Declaration',
            'Assessor signs Code of Conduct',
            'Verify assessor neutrality',
            'Confirm assessor cleared to engage',
        ]
    },
    3: {
        'name': 'Preliminary Assessment (Optional)',
        'key': 'preliminary',
        'documents': [
            {'key': 'preliminary_request', 'name': 'Preliminary Assessment Request Form', 'required': False},
            {'key': 'preliminary_report', 'name': 'Preliminary Assessment Report', 'required': False},
        ],
        'default_checklist': [
            'Receive preliminary assessment request (if applicable)',
            'Conduct light diagnostic review',
            'Prepare preliminary assessment report',
            'Share non-binding findings with organization',
            'Organization decides on readiness to proceed',
        ]
    },
    4: {
        'name': 'Engagement & Planning',
        'key': 'engagement',
        'documents': [
            {'key': 'letter_of_engagement', 'name': 'Letter of Engagement', 'required': True},
            {'key': 'planning_form', 'name': 'Assessment Planning & Logistics Form', 'required': True},
            {'key': 'timeline_map', 'name': 'Assessment Timeline & Workflow Map', 'required': True},
        ],
        'default_checklist': [
            'Issue Letter of Engagement to organization',
            'Organization signs Letter of Engagement',
            'Complete Assessment Planning & Logistics Form',
            'Define scope and assessor team roles',
            'Share Assessment Timeline & Workflow Map',
            'Collect initial payment (50%)',
            'Remit GEA fee for initial payment',
        ]
    },
    5: {
        'name': 'Formal Assessment',
        'key': 'assessment',
        'documents': [
            {'key': 'triangulation_checklist', 'name': 'Triangulation Checklist Sheet', 'required': True},
            {'key': 'rca_worksheet', 'name': 'Root Cause Analysis (RCA) Worksheet', 'required': True},
            {'key': 'ncr_form', 'name': 'Non-Conformance Tracker (NCR / CAR Form)', 'required': True},
        ],
        'default_checklist': [
            'Conduct document review',
            'Perform on-site assessment',
            'Complete Triangulation Checklist',
            'Collect and cross-check evidence',
            'Complete Root Cause Analysis worksheet',
            'Issue Non-Conformances (if any)',
            'Set deadlines for Corrective Action Requests',
        ]
    },
    6: {
        'name': 'Reporting & Peer Review',
        'key': 'reporting',
        'documents': [
            {'key': 'assessment_report', 'name': 'Formal Assessment Report', 'required': True},
            {'key': 'peer_review_checklist', 'name': 'Peer Review Guide / Checklist', 'required': True},
        ],
        'default_checklist': [
            'Draft Formal Assessment Report',
            'Submit report for peer review',
            'Complete Peer Review checklist',
            'Address peer review feedback',
            'Finalize assessment report',
            'Submit report to GEA for review',
        ]
    },
    7: {
        'name': 'Certification Decision',
        'key': 'certification',
        'documents': [
            {'key': 'decision_record', 'name': 'Certification Decision Record', 'required': True},
            {'key': 'feedback_report', 'name': 'Feedback Report to Organization', 'required': True},
        ],
        'default_checklist': [
            'Convene certification committee',
            'Review all assessment evidence',
            'Make certification decision',
            'Complete Certification Decision Record',
            'Submit to GEA for final review',
            'Prepare Feedback Report',
            'Collect final payment (50%)',
            'Remit GEA fee for final payment',
            'Deliver decision and feedback to organization',
        ]
    },
    8: {
        'name': 'Post-Certification Obligations',
        'key': 'post_certification',
        'documents': [
            {'key': 'change_notification', 'name': 'Change Notification Form', 'required': False},
            {'key': 'feedback_form', 'name': 'Feedback Form on GLAB Services', 'required': False},
        ],
        'default_checklist': [
            'Schedule surveillance assessments',
            'Monitor for significant changes',
            'Process change notifications (if any)',
            'Collect feedback on GLAB services',
            'Archive all project documentation',
            'Plan for recertification (if applicable)',
        ]
    }
}

# =============================================================================
# DATABASE MODELS
# =============================================================================

class User(UserMixin, db.Model):
    """User model - GEA admins, GEA staff, GLAB admins, GLAB assessors"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120))
    role = db.Column(db.String(20), nullable=False)  # 'gea_admin', 'gea_staff', 'glab_admin', 'glab_assessor'
    glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    glab = db.relationship('GLAB', backref='users', foreign_keys=[glab_id])
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_gea(self):
        return self.role in ['gea_admin', 'gea_staff']
    
    def is_gea_admin(self):
        return self.role == 'gea_admin'


class GLAB(db.Model):
    """Licensed Assessment Body"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    country = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(50))
    status = db.Column(db.String(20), default='active')  # active, suspended, terminated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    clients = db.relationship('Client', backref='glab', lazy='dynamic')
    projects = db.relationship('Project', backref='glab', lazy='dynamic')


class Client(db.Model):
    """Client organization seeking certification"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    registered_address = db.Column(db.Text)
    industry_sector = db.Column(db.String(100))
    total_employees = db.Column(db.Integer)
    number_of_sites = db.Column(db.Integer, default=1)
    primary_contact_name = db.Column(db.String(100))
    primary_contact_email = db.Column(db.String(120))
    primary_contact_phone = db.Column(db.String(50))
    glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='client', lazy='dynamic')


# Association table for assessors assigned to projects
project_assessors = db.Table('project_assessors',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


class Project(db.Model):
    """Certification project"""
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True, nullable=False)
    glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    
    # Assessment details
    assessment_type = db.Column(db.String(50), default='initial')  # initial, surveillance, recertification
    current_phase = db.Column(db.Integer, default=1)  # 1-8
    
    # GEA Review Status
    gea_status = db.Column(db.String(30), default='pending')  # pending, approved, changes_requested, denied
    gea_notes = db.Column(db.Text)
    gea_reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    gea_reviewed_at = db.Column(db.DateTime)
    
    # Financial
    total_assessment_fees = db.Column(db.Float, default=0)
    gea_fee = db.Column(db.Float, default=0)
    glab_revenue = db.Column(db.Float, default=0)
    initial_payment_received = db.Column(db.Boolean, default=False)
    initial_payment_date = db.Column(db.DateTime)
    final_payment_received = db.Column(db.Boolean, default=False)
    final_payment_date = db.Column(db.DateTime)
    gea_fee_remitted = db.Column(db.Boolean, default=False)
    gea_fee_remitted_date = db.Column(db.DateTime)
    
    # Dates
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    documents = db.relationship('Document', backref='project', lazy='dynamic')
    checklists = db.relationship('ChecklistItem', backref='project', lazy='dynamic')
    phase_logs = db.relationship('PhaseLog', backref='project', lazy='dynamic')
    messages = db.relationship('ChatMessage', backref='project', lazy='dynamic')
    assessors = db.relationship('User', secondary=project_assessors, backref='assigned_projects')


class Document(db.Model):
    """Document uploaded for a project phase"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    phase_number = db.Column(db.Integer, nullable=False)
    document_key = db.Column(db.String(50), nullable=False)  # e.g., 'enrollment_form', 'coi_declaration'
    document_type = db.Column(db.String(100))  # Human readable name
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Review status (GEA only can change)
    status = db.Column(db.String(20), default='pending')  # pending, approved, changes_requested, denied
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_at = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)
    
    # Relationships
    uploader = db.relationship('User', foreign_keys=[uploaded_by])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])


class PhaseTemplate(db.Model):
    """Templates uploaded by GEA for each phase"""
    id = db.Column(db.Integer, primary_key=True)
    phase_number = db.Column(db.Integer, nullable=False)
    document_key = db.Column(db.String(50), nullable=False)
    template_name = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)


class ChecklistItem(db.Model):
    """Checklist items for project phases"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    phase_number = db.Column(db.Integer, nullable=False)
    item_text = db.Column(db.String(500), nullable=False)
    is_required = db.Column(db.Boolean, default=True)
    is_custom = db.Column(db.Boolean, default=False)  # True if added by GEA admin
    is_completed = db.Column(db.Boolean, default=False)
    completed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    completed_at = db.Column(db.DateTime)
    order = db.Column(db.Integer, default=0)
    
    # Relationship
    completer = db.relationship('User', foreign_keys=[completed_by])


class PhaseLog(db.Model):
    """Log of phase transitions"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    from_phase = db.Column(db.Integer)
    to_phase = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(50))
    performed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    performed_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)


class ChatMessage(db.Model):
    """Chat messages between GEA and GLAB for a project"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    # Relationship
    sender = db.relationship('User', foreign_keys=[sender_id])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_reference_number(glab):
    """Generate unique project reference number"""
    year = datetime.now().year
    count = Project.query.filter(
        Project.glab_id == glab.id,
        Project.created_at >= datetime(year, 1, 1)
    ).count() + 1
    return f"{glab.license_number}-{year}-{count:04d}"


def gea_admin_required(f):
    """Decorator for GEA admin only routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_gea_admin():
            flash('Access denied. GEA Admin privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def gea_required(f):
    """Decorator for GEA (admin or staff) routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_gea():
            flash('Access denied. GEA privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def create_default_checklists(project):
    """Create default checklist items for all phases of a project"""
    for phase_num, phase_data in PHASES.items():
        for order, item_text in enumerate(phase_data['default_checklist']):
            checklist = ChecklistItem(
                project_id=project.id,
                phase_number=phase_num,
                item_text=item_text,
                is_required=True,
                is_custom=False,
                order=order
            )
            db.session.add(checklist)
    db.session.commit()


# =============================================================================
# AUTHENTICATION ROUTES
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
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))


# =============================================================================
# DASHBOARD ROUTES
# =============================================================================

@app.route('/')
@login_required
def dashboard():
    if current_user.is_gea():
        # GEA Dashboard
        glabs = GLAB.query.all()
        pending_reviews = Project.query.filter_by(gea_status='pending').count()
        pending_documents = Document.query.filter_by(status='pending').count()
        projects = Project.query.order_by(Project.created_at.desc()).limit(10).all()
        unread_messages = ChatMessage.query.filter_by(is_read=False).count()
        
        # Calculate outstanding GEA fees
        total_gea_fees_due = db.session.query(db.func.sum(Project.gea_fee)).filter(
            Project.gea_fee_remitted == False,
            Project.gea_fee > 0
        ).scalar() or 0
        
        return render_template('dashboard_gea.html',
            glabs=glabs,
            pending_reviews=pending_reviews,
            pending_documents=pending_documents,
            projects=projects,
            unread_messages=unread_messages,
            total_gea_fees_due=total_gea_fees_due,
            phases=PHASES
        )
    
    elif current_user.role == 'glab_admin':
        # GLAB Admin Dashboard
        glab = current_user.glab
        clients = glab.clients.all() if glab else []
        projects = glab.projects.order_by(Project.created_at.desc()).all() if glab else []
        unread_messages = ChatMessage.query.join(Project).filter(
            Project.glab_id == glab.id,
            ChatMessage.is_read == False,
            ChatMessage.sender_id != current_user.id
        ).count() if glab else 0
        
        return render_template('dashboard_glab.html',
            glab=glab,
            clients=clients,
            projects=projects,
            unread_messages=unread_messages,
            phases=PHASES
        )
    
    elif current_user.role == 'glab_assessor':
        # Assessor Dashboard - only sees assigned projects
        projects = current_user.assigned_projects
        
        return render_template('dashboard_assessor.html',
            projects=projects,
            phases=PHASES
        )
    
    return redirect(url_for('login'))


# =============================================================================
# USER MANAGEMENT (GEA Admin Only)
# =============================================================================

@app.route('/users')
@login_required
@gea_admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    glabs = GLAB.query.all()
    return render_template('users/list.html', users=users, glabs=glabs)


@app.route('/users/create', methods=['GET', 'POST'])
@login_required
@gea_admin_required
def create_user():
    glabs = GLAB.query.filter_by(status='active').all()
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        role = request.form.get('role')
        glab_id = request.form.get('glab_id') or None
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('create_user'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return redirect(url_for('create_user'))
        
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            glab_id=int(glab_id) if glab_id else None,
            created_by=current_user.id
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {username} created successfully.', 'success')
        return redirect(url_for('list_users'))
    
    return render_template('users/form.html', glabs=glabs, user=None)


@app.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@gea_admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot deactivate your own account.', 'error')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        status = 'activated' if user.is_active else 'deactivated'
        flash(f'User {user.username} {status}.', 'success')
    return redirect(url_for('list_users'))


# =============================================================================
# GLAB MANAGEMENT (GEA Admin Only)
# =============================================================================

@app.route('/glabs')
@login_required
@gea_admin_required
def list_glabs():
    glabs = GLAB.query.order_by(GLAB.created_at.desc()).all()
    return render_template('glabs/list.html', glabs=glabs)


@app.route('/glabs/create', methods=['GET', 'POST'])
@login_required
@gea_admin_required
def create_glab():
    if request.method == 'POST':
        glab = GLAB(
            name=request.form.get('name'),
            license_number=request.form.get('license_number'),
            country=request.form.get('country'),
            address=request.form.get('address'),
            contact_email=request.form.get('contact_email'),
            contact_phone=request.form.get('contact_phone'),
            created_by=current_user.id
        )
        db.session.add(glab)
        db.session.commit()
        
        flash(f'GLAB {glab.name} created successfully.', 'success')
        return redirect(url_for('list_glabs'))
    
    return render_template('glabs/form.html', glab=None)


@app.route('/glabs/<int:glab_id>')
@login_required
def view_glab(glab_id):
    glab = GLAB.query.get_or_404(glab_id)
    if not current_user.is_gea() and current_user.glab_id != glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    projects = glab.projects.order_by(Project.created_at.desc()).all()
    clients = glab.clients.all()
    assessors = User.query.filter_by(glab_id=glab_id, role='glab_assessor').all()
    
    return render_template('glabs/view.html', glab=glab, projects=projects, clients=clients, assessors=assessors)


# =============================================================================
# CLIENT MANAGEMENT (GEA and GLAB)
# =============================================================================

@app.route('/clients')
@login_required
def list_clients():
    if current_user.is_gea():
        clients = Client.query.order_by(Client.created_at.desc()).all()
    else:
        clients = Client.query.filter_by(glab_id=current_user.glab_id).order_by(Client.created_at.desc()).all()
    
    return render_template('clients/list.html', clients=clients)


@app.route('/clients/create', methods=['GET', 'POST'])
@login_required
def create_client():
    glabs = GLAB.query.filter_by(status='active').all() if current_user.is_gea() else None
    
    if request.method == 'POST':
        glab_id = request.form.get('glab_id') if current_user.is_gea() else current_user.glab_id
        
        client = Client(
            name=request.form.get('name'),
            country=request.form.get('country'),
            registered_address=request.form.get('registered_address'),
            industry_sector=request.form.get('industry_sector'),
            total_employees=request.form.get('total_employees') or None,
            number_of_sites=request.form.get('number_of_sites') or 1,
            primary_contact_name=request.form.get('primary_contact_name'),
            primary_contact_email=request.form.get('primary_contact_email'),
            primary_contact_phone=request.form.get('primary_contact_phone'),
            glab_id=glab_id,
            created_by=current_user.id
        )
        db.session.add(client)
        db.session.commit()
        
        flash(f'Client {client.name} created successfully.', 'success')
        return redirect(url_for('list_clients'))
    
    return render_template('clients/form.html', client=None, glabs=glabs)


@app.route('/clients/<int:client_id>')
@login_required
def view_client(client_id):
    client = Client.query.get_or_404(client_id)
    if not current_user.is_gea() and client.glab_id != current_user.glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    projects = client.projects.all()
    return render_template('clients/view.html', client=client, projects=projects, phases=PHASES)


# =============================================================================
# PROJECT MANAGEMENT
# =============================================================================

@app.route('/projects')
@login_required
def list_projects():
    if current_user.is_gea():
        projects = Project.query.order_by(Project.created_at.desc()).all()
    elif current_user.role == 'glab_assessor':
        projects = current_user.assigned_projects
    else:
        projects = Project.query.filter_by(glab_id=current_user.glab_id).order_by(Project.created_at.desc()).all()
    
    return render_template('projects/list.html', projects=projects, phases=PHASES)


@app.route('/projects/create', methods=['GET', 'POST'])
@login_required
def create_project():
    if current_user.role == 'glab_assessor':
        flash('Assessors cannot create projects.', 'error')
        return redirect(url_for('dashboard'))
    
    glabs = GLAB.query.filter_by(status='active').all() if current_user.is_gea() else None
    
    if current_user.is_gea():
        clients = Client.query.all()
    else:
        clients = Client.query.filter_by(glab_id=current_user.glab_id).all()
    
    if request.method == 'POST':
        glab_id = request.form.get('glab_id') if current_user.is_gea() else current_user.glab_id
        glab = GLAB.query.get(glab_id)
        
        project = Project(
            reference_number=generate_reference_number(glab),
            glab_id=glab_id,
            client_id=request.form.get('client_id'),
            assessment_type=request.form.get('assessment_type'),
            total_assessment_fees=float(request.form.get('total_fees') or 0),
            created_by=current_user.id
        )
        
        # Calculate GEA fee (15%)
        project.gea_fee = project.total_assessment_fees * 0.15
        project.glab_revenue = project.total_assessment_fees * 0.85
        
        db.session.add(project)
        db.session.commit()
        
        # Create default checklists
        create_default_checklists(project)
        
        # Log phase
        log = PhaseLog(
            project_id=project.id,
            from_phase=None,
            to_phase=1,
            action='created',
            performed_by=current_user.id
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'Project {project.reference_number} created successfully.', 'success')
        return redirect(url_for('view_project', project_id=project.id))
    
    return render_template('projects/form.html', glabs=glabs, clients=clients, project=None)


@app.route('/projects/<int:project_id>')
@login_required
def view_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Access control
    if current_user.role == 'glab_assessor':
        if project not in current_user.assigned_projects:
            flash('Access denied. You are not assigned to this project.', 'error')
            return redirect(url_for('dashboard'))
    elif not current_user.is_gea() and project.glab_id != current_user.glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    current_phase = PHASES.get(project.current_phase, {})
    checklist = ChecklistItem.query.filter_by(
        project_id=project_id,
        phase_number=project.current_phase
    ).order_by(ChecklistItem.order).all()
    
    documents = Document.query.filter_by(
        project_id=project_id,
        phase_number=project.current_phase
    ).all()
    
    # Get templates for current phase
    templates = PhaseTemplate.query.filter_by(
        phase_number=project.current_phase,
        is_active=True
    ).all()
    
    # Get chat messages
    messages = ChatMessage.query.filter_by(project_id=project_id).order_by(ChatMessage.sent_at.desc()).limit(50).all()
    
    # Get assigned assessors
    assessors = project.assessors
    
    # Get available assessors for assignment (GEA/GLAB admin only)
    available_assessors = []
    if current_user.is_gea() or current_user.role == 'glab_admin':
        available_assessors = User.query.filter_by(
            glab_id=project.glab_id,
            role='glab_assessor',
            is_active=True
        ).all()
    
    phase_logs = PhaseLog.query.filter_by(project_id=project_id).order_by(PhaseLog.performed_at.desc()).all()
    
    return render_template('projects/view.html',
        project=project,
        current_phase=current_phase,
        phase_number=project.current_phase,
        checklist=checklist,
        documents=documents,
        templates=templates,
        messages=messages,
        assessors=assessors,
        available_assessors=available_assessors,
        phase_logs=phase_logs,
        phases=PHASES
    )


# =============================================================================
# GEA REVIEW (Approve/Deny/Request Changes)
# =============================================================================

@app.route('/projects/<int:project_id>/review', methods=['POST'])
@login_required
@gea_required
def review_project(project_id):
    project = Project.query.get_or_404(project_id)
    action = request.form.get('action')
    notes = request.form.get('notes', '')
    
    if action in ['approved', 'changes_requested', 'denied']:
        project.gea_status = action
        project.gea_notes = notes
        project.gea_reviewed_by = current_user.id
        project.gea_reviewed_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'Project {action.replace("_", " ")}.', 'success')
    
    return redirect(url_for('view_project', project_id=project_id))


@app.route('/reviews')
@login_required
@gea_required
def pending_reviews():
    projects = Project.query.filter_by(gea_status='pending').order_by(Project.created_at.desc()).all()
    return render_template('reviews/list.html', projects=projects, phases=PHASES)


# =============================================================================
# DOCUMENT MANAGEMENT
# =============================================================================

@app.route('/projects/<int:project_id>/documents/upload', methods=['GET', 'POST'])
@login_required
def upload_document(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Access control
    if current_user.role == 'glab_assessor' and project not in current_user.assigned_projects:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    phase = PHASES.get(project.current_phase, {})
    document_slots = phase.get('documents', [])
    
    if request.method == 'POST':
        document_key = request.form.get('document_key')
        file = request.files.get('file')
        
        if not file or not allowed_file(file.filename):
            flash('Invalid file type.', 'error')
            return redirect(url_for('upload_document', project_id=project_id))
        
        # Find document type name
        doc_name = next((d['name'] for d in document_slots if d['key'] == document_key), document_key)
        
        filename = secure_filename(file.filename)
        stored_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
        file.save(file_path)
        
        doc = Document(
            project_id=project_id,
            phase_number=project.current_phase,
            document_key=document_key,
            document_type=doc_name,
            original_filename=filename,
            stored_filename=stored_filename,
            file_size=os.path.getsize(file_path),
            uploaded_by=current_user.id
        )
        db.session.add(doc)
        db.session.commit()
        
        flash(f'Document "{doc_name}" uploaded successfully.', 'success')
        return redirect(url_for('view_project', project_id=project_id))
    
    # Get existing documents for this phase
    existing_docs = {d.document_key: d for d in Document.query.filter_by(
        project_id=project_id,
        phase_number=project.current_phase
    ).all()}
    
    # Get templates
    templates = {t.document_key: t for t in PhaseTemplate.query.filter_by(
        phase_number=project.current_phase,
        is_active=True
    ).all()}
    
    return render_template('documents/upload.html',
        project=project,
        phase=phase,
        document_slots=document_slots,
        existing_docs=existing_docs,
        templates=templates
    )


@app.route('/documents/<int:document_id>/review', methods=['POST'])
@login_required
@gea_required
def review_document(document_id):
    doc = Document.query.get_or_404(document_id)
    action = request.form.get('action')
    notes = request.form.get('notes', '')
    
    if action in ['approved', 'changes_requested', 'denied']:
        doc.status = action
        doc.review_notes = notes
        doc.reviewed_by = current_user.id
        doc.reviewed_at = datetime.utcnow()
        db.session.commit()
        
        flash(f'Document {action.replace("_", " ")}.', 'success')
    
    return redirect(url_for('view_project', project_id=doc.project_id))


@app.route('/documents/<int:document_id>/download')
@login_required
def download_document(document_id):
    doc = Document.query.get_or_404(document_id)
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        doc.stored_filename,
        as_attachment=True,
        download_name=doc.original_filename
    )


# =============================================================================
# PHASE TEMPLATES (GEA Admin)
# =============================================================================

@app.route('/templates')
@login_required
@gea_admin_required
def list_templates():
    templates = PhaseTemplate.query.order_by(PhaseTemplate.phase_number, PhaseTemplate.document_key).all()
    return render_template('templates/list.html', templates=templates, phases=PHASES)


@app.route('/templates/upload', methods=['GET', 'POST'])
@login_required
@gea_admin_required
def upload_template():
    if request.method == 'POST':
        phase_number = int(request.form.get('phase_number'))
        document_key = request.form.get('document_key')
        file = request.files.get('file')
        
        if not file or not allowed_file(file.filename):
            flash('Invalid file type.', 'error')
            return redirect(url_for('upload_template'))
        
        filename = secure_filename(file.filename)
        stored_filename = f"template_{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['TEMPLATES_FOLDER'], stored_filename)
        file.save(file_path)
        
        # Deactivate old templates for same slot
        PhaseTemplate.query.filter_by(
            phase_number=phase_number,
            document_key=document_key
        ).update({'is_active': False})
        
        template = PhaseTemplate(
            phase_number=phase_number,
            document_key=document_key,
            template_name=request.form.get('template_name') or filename,
            original_filename=filename,
            stored_filename=stored_filename,
            uploaded_by=current_user.id
        )
        db.session.add(template)
        db.session.commit()
        
        flash('Template uploaded successfully.', 'success')
        return redirect(url_for('list_templates'))
    
    return render_template('templates/upload.html', phases=PHASES)


@app.route('/templates/<int:template_id>/download')
@login_required
def download_template(template_id):
    template = PhaseTemplate.query.get_or_404(template_id)
    return send_from_directory(
        app.config['TEMPLATES_FOLDER'],
        template.stored_filename,
        as_attachment=True,
        download_name=template.original_filename
    )


# =============================================================================
# CHECKLIST MANAGEMENT
# =============================================================================

@app.route('/projects/<int:project_id>/checklist/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_checklist(project_id, item_id):
    item = ChecklistItem.query.get_or_404(item_id)
    project = Project.query.get_or_404(project_id)
    
    # Only GLAB users can mark items complete
    if current_user.is_gea():
        return jsonify({'success': False, 'error': 'Only GLAB users can mark checklist items.'})
    
    if project not in current_user.assigned_projects and current_user.role != 'glab_admin':
        if current_user.glab_id != project.glab_id:
            return jsonify({'success': False, 'error': 'Access denied.'})
    
    item.is_completed = not item.is_completed
    if item.is_completed:
        item.completed_by = current_user.id
        item.completed_at = datetime.utcnow()
    else:
        item.completed_by = None
        item.completed_at = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_completed': item.is_completed,
        'completed_by': current_user.full_name or current_user.username if item.is_completed else None
    })


@app.route('/projects/<int:project_id>/checklist/add', methods=['POST'])
@login_required
@gea_admin_required
def add_checklist_item(project_id):
    project = Project.query.get_or_404(project_id)
    item_text = request.form.get('item_text')
    phase_number = int(request.form.get('phase_number', project.current_phase))
    
    max_order = db.session.query(db.func.max(ChecklistItem.order)).filter_by(
        project_id=project_id,
        phase_number=phase_number
    ).scalar() or 0
    
    item = ChecklistItem(
        project_id=project_id,
        phase_number=phase_number,
        item_text=item_text,
        is_required=True,
        is_custom=True,
        order=max_order + 1
    )
    db.session.add(item)
    db.session.commit()
    
    flash('Checklist item added.', 'success')
    return redirect(url_for('view_project', project_id=project_id))


# =============================================================================
# ASSESSOR MANAGEMENT
# =============================================================================

@app.route('/projects/<int:project_id>/assessors/assign', methods=['POST'])
@login_required
def assign_assessor(project_id):
    project = Project.query.get_or_404(project_id)
    
    if not current_user.is_gea() and current_user.role != 'glab_admin':
        flash('Access denied.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    assessor_id = request.form.get('assessor_id')
    assessor = User.query.get_or_404(assessor_id)
    
    if assessor not in project.assessors:
        project.assessors.append(assessor)
        db.session.commit()
        flash(f'Assessor {assessor.full_name or assessor.username} assigned.', 'success')
    
    return redirect(url_for('view_project', project_id=project_id))


@app.route('/projects/<int:project_id>/assessors/<int:user_id>/remove', methods=['POST'])
@login_required
def remove_assessor(project_id, user_id):
    project = Project.query.get_or_404(project_id)
    
    if not current_user.is_gea() and current_user.role != 'glab_admin':
        flash('Access denied.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    assessor = User.query.get_or_404(user_id)
    
    if assessor in project.assessors:
        project.assessors.remove(assessor)
        db.session.commit()
        flash(f'Assessor removed.', 'success')
    
    return redirect(url_for('view_project', project_id=project_id))


# =============================================================================
# CHAT / MESSAGING
# =============================================================================

@app.route('/projects/<int:project_id>/chat', methods=['GET', 'POST'])
@login_required
def project_chat(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Access control
    if current_user.role == 'glab_assessor' and project not in current_user.assigned_projects:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    elif not current_user.is_gea() and current_user.glab_id != project.glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        message_text = request.form.get('message')
        if message_text:
            msg = ChatMessage(
                project_id=project_id,
                sender_id=current_user.id,
                message=message_text
            )
            db.session.add(msg)
            db.session.commit()
        
        return redirect(url_for('project_chat', project_id=project_id))
    
    # Mark messages as read
    ChatMessage.query.filter(
        ChatMessage.project_id == project_id,
        ChatMessage.sender_id != current_user.id,
        ChatMessage.is_read == False
    ).update({'is_read': True})
    db.session.commit()
    
    messages = ChatMessage.query.filter_by(project_id=project_id).order_by(ChatMessage.sent_at.asc()).all()
    
    return render_template('chat/project.html', project=project, messages=messages, phases=PHASES)


@app.route('/api/projects/<int:project_id>/messages')
@login_required
def get_messages(project_id):
    """API endpoint for live chat polling"""
    project = Project.query.get_or_404(project_id)
    
    messages = ChatMessage.query.filter_by(project_id=project_id).order_by(ChatMessage.sent_at.asc()).all()
    
    return jsonify([{
        'id': m.id,
        'sender': m.sender.full_name or m.sender.username,
        'sender_role': m.sender.role,
        'message': m.message,
        'sent_at': m.sent_at.strftime('%Y-%m-%d %H:%M'),
        'is_mine': m.sender_id == current_user.id
    } for m in messages])


# =============================================================================
# PHASE ADVANCEMENT
# =============================================================================

@app.route('/projects/<int:project_id>/advance', methods=['POST'])
@login_required
def advance_phase(project_id):
    project = Project.query.get_or_404(project_id)
    
    if not current_user.is_gea() and current_user.glab_id != project.glab_id:
        flash('Access denied.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    if project.current_phase >= 8:
        flash('Project is already in the final phase.', 'warning')
        return redirect(url_for('view_project', project_id=project_id))
    
    old_phase = project.current_phase
    project.current_phase += 1
    
    log = PhaseLog(
        project_id=project_id,
        from_phase=old_phase,
        to_phase=project.current_phase,
        action='advanced',
        performed_by=current_user.id
    )
    db.session.add(log)
    db.session.commit()
    
    flash(f'Project advanced to Phase {project.current_phase}: {PHASES[project.current_phase]["name"]}', 'success')
    return redirect(url_for('view_project', project_id=project_id))


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
    """Initialize database with default admin user"""
    db.create_all()
    
    # Create default GEA admin if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@gea.org',
            full_name='GEA Administrator',
            role='gea_admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Database initialized.")
        print("GEA Admin: username='admin', password='admin123'")


# Initialize database on startup
with app.app_context():
    init_db()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
