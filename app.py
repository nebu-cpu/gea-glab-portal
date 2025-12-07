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

# Countries list for dropdown
COUNTRIES = [
    'Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola', 'Antigua and Barbuda', 'Argentina', 
    'Armenia', 'Australia', 'Austria', 'Azerbaijan', 'Bahamas', 'Bahrain', 'Bangladesh', 'Barbados', 
    'Belarus', 'Belgium', 'Belize', 'Benin', 'Bhutan', 'Bolivia', 'Bosnia and Herzegovina', 'Botswana', 
    'Brazil', 'Brunei', 'Bulgaria', 'Burkina Faso', 'Burundi', 'Cambodia', 'Cameroon', 'Canada', 
    'Cape Verde', 'Central African Republic', 'Chad', 'Chile', 'China', 'Colombia', 'Comoros', 
    'Congo', 'Costa Rica', 'Croatia', 'Cuba', 'Cyprus', 'Czech Republic', 'Denmark', 'Djibouti', 
    'Dominica', 'Dominican Republic', 'East Timor', 'Ecuador', 'Egypt', 'El Salvador', 'Equatorial Guinea', 
    'Eritrea', 'Estonia', 'Eswatini', 'Ethiopia', 'Fiji', 'Finland', 'France', 'Gabon', 'Gambia', 
    'Georgia', 'Germany', 'Ghana', 'Greece', 'Grenada', 'Guatemala', 'Guinea', 'Guinea-Bissau', 
    'Guyana', 'Haiti', 'Honduras', 'Hungary', 'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq', 
    'Ireland', 'Israel', 'Italy', 'Ivory Coast', 'Jamaica', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 
    'Kiribati', 'Kosovo', 'Kuwait', 'Kyrgyzstan', 'Laos', 'Latvia', 'Lebanon', 'Lesotho', 'Liberia', 
    'Libya', 'Liechtenstein', 'Lithuania', 'Luxembourg', 'Madagascar', 'Malawi', 'Malaysia', 'Maldives', 
    'Mali', 'Malta', 'Marshall Islands', 'Mauritania', 'Mauritius', 'Mexico', 'Micronesia', 'Moldova', 
    'Monaco', 'Mongolia', 'Montenegro', 'Morocco', 'Mozambique', 'Myanmar', 'Namibia', 'Nauru', 
    'Nepal', 'Netherlands', 'New Zealand', 'Nicaragua', 'Niger', 'Nigeria', 'North Korea', 'North Macedonia', 
    'Norway', 'Oman', 'Pakistan', 'Palau', 'Palestine', 'Panama', 'Papua New Guinea', 'Paraguay', 
    'Peru', 'Philippines', 'Poland', 'Portugal', 'Qatar', 'Romania', 'Russia', 'Rwanda', 
    'Saint Kitts and Nevis', 'Saint Lucia', 'Saint Vincent and the Grenadines', 'Samoa', 'San Marino', 
    'Sao Tome and Principe', 'Saudi Arabia', 'Senegal', 'Serbia', 'Seychelles', 'Sierra Leone', 
    'Singapore', 'Slovakia', 'Slovenia', 'Solomon Islands', 'Somalia', 'South Africa', 'South Korea', 
    'South Sudan', 'Spain', 'Sri Lanka', 'Sudan', 'Suriname', 'Sweden', 'Switzerland', 'Syria', 
    'Taiwan', 'Tajikistan', 'Tanzania', 'Thailand', 'Togo', 'Tonga', 'Trinidad and Tobago', 'Tunisia', 
    'Turkey', 'Turkmenistan', 'Tuvalu', 'Uganda', 'Ukraine', 'United Arab Emirates', 'United Kingdom', 
    'United States', 'Uruguay', 'Uzbekistan', 'Vanuatu', 'Vatican City', 'Venezuela', 'Vietnam', 
    'Yemen', 'Zambia', 'Zimbabwe'
]

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
            'Enrollment form received and complete',
            'Eligibility criteria verified',
            'Organizational scope defined',
            'Multi-site requirements clarified (if applicable)',
            'Timeline expectations documented',
            'Resource commitment confirmed',
            'Preliminary risk assessment completed',
            'Enrollment decision communicated',
        ],
        'gea_review_checklist': [
            'Enrollment form complete and accurate',
            'Organization meets eligibility criteria',
            'Scope appropriately defined',
            'Risk assessment is adequate',
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
            'Conflict of interest declarations obtained',
            'All conflicts reviewed and resolved',
            'Assessor competencies matched to scope',
            'Code of conduct acknowledged',
            'Team composition finalized',
            'Confidentiality agreements signed',
            'Assessment team briefing conducted',
            'Organization notified of team assignment',
        ],
        'gea_review_checklist': [
            'All COI declarations submitted',
            'No unresolved conflicts of interest',
            'Assessor team appropriately qualified',
            'Code of conduct signed by all assessors',
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
            'Preliminary assessment request received',
            'Scope and objectives clarified',
            'Implementation evidence reviewed',
            'Leadership interviews conducted',
            'Cultural/operational observations completed',
            'Preliminary findings documented',
            'Improvement recommendations identified',
            'Preliminary report delivered',
            'Improvement period timeline agreed',
        ],
        'gea_review_checklist': [
            'Preliminary report follows required format',
            'Findings are objective and evidence-based',
            'Recommendations are appropriate',
            'Improvement timeline is reasonable',
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
            'Readiness verification completed',
            'Letter of Engagement drafted',
            'Scope and boundaries confirmed',
            'Assessment timeline developed',
            'Site visit schedule finalized',
            'Resource requirements confirmed',
            'Communication protocols established',
            'Logistics arrangements completed',
            'Stakeholder responsibilities defined',
            'Engagement documents signed',
            'Initial payment (50%) collected',
            'GEA fee remitted for initial payment',
        ],
        'gea_review_checklist': [
            'Letter of Engagement properly executed',
            'Scope is clearly defined',
            'Timeline is realistic',
            'Initial payment received',
            'GEA fee remitted',
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
            'Document review completed',
            'Assessment tools prepared',
            'Evidence requirements communicated',
            'Opening meeting conducted',
            'All 8 dimensions assessed',
            'Triangulation methodology applied',
            'Evidence collection documented',
            'Root cause analysis performed',
            'Non-conformances identified',
            'CARs issued as required',
            'Daily team debriefs conducted',
            'Closing meeting held',
            'Evidence organized and secured',
            'Finding validation completed',
            'Non-conformance tracker updated',
        ],
        'gea_review_checklist': [
            'All dimensions properly assessed',
            'Triangulation properly applied',
            'Evidence is sufficient and verifiable',
            'Non-conformances appropriately identified',
            'CARs properly documented',
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
            'Draft report prepared',
            'Evidence references verified',
            'Cross-dimensional analysis completed',
            'Report structure compliance checked',
            'Peer reviewer assigned',
            'Peer review conducted',
            'Review feedback addressed',
            'Final report approved',
            'Report delivered to GLAB',
        ],
        'gea_review_checklist': [
            'Report follows required format',
            'All findings are evidence-based',
            'Cross-dimensional analysis is comprehensive',
            'Peer review properly conducted',
            'Feedback has been addressed',
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
            'Report submitted for decision',
            'Certification criteria evaluated',
            'Risk assessment completed',
            'Decision record prepared',
            'Feedback report developed',
            'Decision communicated to organization',
            'Certificate issued (if applicable)',
            'Appeals process explained',
            'Final payment (50%) collected',
            'GEA fee remitted for final payment',
        ],
        'gea_review_checklist': [
            'Decision is supported by evidence',
            'Decision record is complete',
            'Feedback report is objective',
            'Final payment received',
            'GEA fee remitted',
            'Certificate ready for issuance (if approved)',
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
            'Change notification process explained',
            'Surveillance schedule established',
            'Continuous improvement expectations set',
            'Feedback on GLAB services requested',
            'Assessment documents archived',
            'Confidential materials returned/destroyed',
            'Final billing processed',
            'Case study permissions obtained (optional)',
        ],
        'gea_review_checklist': [
            'Surveillance schedule is appropriate',
            'All documentation properly archived',
            'Organization informed of obligations',
            'Feedback collected',
        ]
    }
}

# =============================================================================
# DATABASE MODELS
# =============================================================================

class User(UserMixin, db.Model):
    """User model - supports all user types"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120))
    
    # Profile fields
    profile_photo = db.Column(db.String(255))  # Stored filename
    phone = db.Column(db.String(50))
    bio = db.Column(db.Text)
    
    # Role & Organization
    role = db.Column(db.String(30), nullable=False)  # gea_admin, gea_staff, glab_admin, glab_assessor, technical_expert, cert_committee, client_user
    staff_function = db.Column(db.String(30))  # For gea_staff: review_team, quality_team, operations, finance, registry
    glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'), nullable=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)  # For client_user
    
    # Assessor-specific fields
    assessor_id = db.Column(db.String(50), unique=True, nullable=True)  # Certificate ID
    certification_date = db.Column(db.Date)
    recertification_due = db.Column(db.Date)  # certification_date + 3 years
    assessor_specializations = db.Column(db.Text)  # JSON array of domains
    
    # Technical Expert fields
    expert_domains = db.Column(db.Text)  # JSON array of expertise areas
    
    # Status & Tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    
    # Notification preferences
    email_notifications = db.Column(db.Boolean, default=True)
    
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
    
    def can_review(self):
        """Can this user review documents/phases?"""
        return self.role in ['gea_admin', 'gea_staff']
    
    def can_edit_operational_checklist(self):
        """Can this user complete operational checklist items?"""
        return self.role in ['glab_admin', 'glab_assessor']
    
    def can_edit_quality_checklist(self):
        """Can this user complete quality checklist items?"""
        return self.role in ['gea_admin', 'gea_staff']
    
    def unread_notification_count(self):
        """Count unread notifications"""
        return Notification.query.filter_by(user_id=self.id, is_read=False).count()


class GLAB(db.Model):
    """Licensed Assessment Body with license tracking"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    country = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(50))
    
    # License & Payment tracking
    license_type = db.Column(db.String(20), default='annual')  # 'annual' or 'triennial'
    license_start_date = db.Column(db.Date)
    license_expiry_date = db.Column(db.Date)
    last_payment_date = db.Column(db.Date)
    next_payment_due = db.Column(db.Date)  # For reminder scheduling
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, suspended, terminated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    clients = db.relationship('Client', backref='glab', lazy='dynamic')
    projects = db.relationship('Project', backref='glab', lazy='dynamic')
    
    def calculate_next_payment_due(self):
        """Calculate next payment due date based on license type"""
        if self.last_payment_date:
            if self.license_type == 'annual':
                self.next_payment_due = self.last_payment_date + timedelta(days=365)
            else:  # triennial
                self.next_payment_due = self.last_payment_date + timedelta(days=365*3)


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


# Association tables for project assignments
project_assessors = db.Table('project_assessors',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

project_technical_experts = db.Table('project_technical_experts',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

project_committee_members = db.Table('project_committee_members',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)


class Project(db.Model):
    """Certification project with enhanced tracking"""
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True, nullable=False)
    glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    lead_assessor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
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
    quality_checklists = db.relationship('QualityChecklistItem', backref='project', lazy='dynamic')
    phase_logs = db.relationship('PhaseLog', backref='project', lazy='dynamic')
    messages = db.relationship('ChatMessage', backref='project', lazy='dynamic')
    
    assessors = db.relationship('User', secondary=project_assessors, 
        backref=db.backref('assigned_projects', lazy='dynamic'))
    technical_experts = db.relationship('User', secondary=project_technical_experts,
        backref=db.backref('expert_projects', lazy='dynamic'))
    committee_members = db.relationship('User', secondary=project_committee_members,
        backref=db.backref('committee_projects', lazy='dynamic'))
    
    lead_assessor = db.relationship('User', foreign_keys=[lead_assessor_id])


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


class Announcement(db.Model):
    """Global announcements from GEA to all GLABs"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    target_glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'), nullable=True)  # None = all GLABs
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    author = db.relationship('User', foreign_keys=[created_by])
    target_glab = db.relationship('GLAB', foreign_keys=[target_glab_id])


class QualityChecklistItem(db.Model):
    """Quality/Review checklist items for GEA staff"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    phase_number = db.Column(db.Integer, nullable=False)
    item_text = db.Column(db.String(500), nullable=False)
    check_type = db.Column(db.String(30))  # 'received', 'verified', 'approved'
    
    is_checked = db.Column(db.Boolean, default=False)
    checked_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    checked_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    
    # Link to document being reviewed
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'))
    
    # Relationships
    checker = db.relationship('User', foreign_keys=[checked_by])


class Notification(db.Model):
    """User notifications for chat, announcements, reminders"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    notification_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    
    link_type = db.Column(db.String(30))  # 'project', 'announcement', 'chat', 'cpd'
    link_id = db.Column(db.Integer)
    
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CPDLog(db.Model):
    """Continuing Professional Development logs for assessors"""
    id = db.Column(db.Integer, primary_key=True)
    assessor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    activity_type = db.Column(db.String(50), nullable=False)  # training, workshop, seminar, self-study, etc.
    activity_title = db.Column(db.String(200), nullable=False)
    activity_date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    
    # Evidence document
    evidence_filename = db.Column(db.String(255))
    evidence_stored_filename = db.Column(db.String(255))
    
    # Review
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_at = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)
    
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    assessor = db.relationship('User', foreign_keys=[assessor_id], backref='cpd_logs')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])


class ScheduledReminder(db.Model):
    """Tracks scheduled reminders to avoid duplicates"""
    id = db.Column(db.Integer, primary_key=True)
    
    reminder_type = db.Column(db.String(50), nullable=False)  # license_payment, cpd_reminder, recertification
    target_type = db.Column(db.String(30), nullable=False)  # 'glab', 'assessor'
    target_id = db.Column(db.Integer, nullable=False)
    
    due_date = db.Column(db.Date, nullable=False)
    days_before = db.Column(db.Integer, nullable=False)  # 60, 30, 15, 5
    
    sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime)
    
    __table_args__ = (
        db.UniqueConstraint('reminder_type', 'target_type', 'target_id', 'days_before'),
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_global_vars():
    """Inject global variables into all templates"""
    if current_user.is_authenticated:
        # Count unread notifications
        unread_notifications = current_user.unread_notification_count()
        
        # Count unread announcements for this user
        if current_user.is_gea():
            unread_announcements = 0
        else:
            unread_announcements = Announcement.query.filter(
                db.or_(
                    Announcement.target_glab_id == None,
                    Announcement.target_glab_id == current_user.glab_id
                ),
                Announcement.is_active == True,
                Announcement.created_at >= current_user.created_at
            ).count()
        
        # Count unread chat messages
        if current_user.is_gea():
            unread_messages = ChatMessage.query.filter_by(is_read=False).filter(
                ChatMessage.sender_id != current_user.id
            ).count()
        elif current_user.glab_id:
            unread_messages = ChatMessage.query.join(Project).filter(
                Project.glab_id == current_user.glab_id,
                ChatMessage.is_read == False,
                ChatMessage.sender_id != current_user.id
            ).count()
        else:
            unread_messages = 0
        
        return {
            'unread_notifications': unread_notifications,
            'unread_announcements': unread_announcements,
            'unread_messages': unread_messages,
            'countries': COUNTRIES
        }
    return {
        'unread_notifications': 0,
        'unread_announcements': 0,
        'unread_messages': 0,
        'countries': COUNTRIES
    }


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


def create_notification(user_id, notification_type, title, message, link_type=None, link_id=None):
    """Create a notification for a user"""
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        link_type=link_type,
        link_id=link_id
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def notify_project_participants(project, notification_type, title, message, exclude_user_id=None):
    """Notify all participants of a project"""
    user_ids = set()
    
    # GLAB users
    for user in User.query.filter_by(glab_id=project.glab_id, is_active=True).all():
        user_ids.add(user.id)
    
    # Assessors
    for assessor in project.assessors:
        user_ids.add(assessor.id)
    
    # Technical experts
    for expert in project.technical_experts:
        user_ids.add(expert.id)
    
    # GEA staff
    for user in User.query.filter(User.role.in_(['gea_admin', 'gea_staff']), User.is_active == True).all():
        user_ids.add(user.id)
    
    # Remove excluded user
    if exclude_user_id:
        user_ids.discard(exclude_user_id)
    
    # Create notifications
    for user_id in user_ids:
        create_notification(user_id, notification_type, title, message, 'project', project.id)


def check_and_send_reminders():
    """Check for due reminders and create notifications"""
    today = datetime.utcnow().date()
    reminder_days = [60, 30, 15, 5]
    
    # GLAB License Payment Reminders
    for glab in GLAB.query.filter(GLAB.next_payment_due != None, GLAB.status == 'active').all():
        for days in reminder_days:
            reminder_date = glab.next_payment_due - timedelta(days=days)
            if today == reminder_date:
                # Check if already sent
                existing = ScheduledReminder.query.filter_by(
                    reminder_type='license_payment',
                    target_type='glab',
                    target_id=glab.id,
                    days_before=days
                ).first()
                
                if not existing or not existing.sent:
                    # Notify GLAB admins
                    for user in User.query.filter_by(glab_id=glab.id, role='glab_admin', is_active=True).all():
                        create_notification(
                            user.id,
                            'license_reminder',
                            f'License Payment Due in {days} Days',
                            f'Your GLAB license payment is due on {glab.next_payment_due.strftime("%B %d, %Y")}. Please ensure timely payment to maintain your license.',
                            'glab',
                            glab.id
                        )
                    
                    # Also notify GEA
                    for user in User.query.filter(User.role.in_(['gea_admin', 'gea_staff']), User.is_active == True).all():
                        create_notification(
                            user.id,
                            'license_reminder',
                            f'GLAB License Payment Due: {glab.name}',
                            f'{glab.name} license payment is due in {days} days ({glab.next_payment_due.strftime("%B %d, %Y")}).',
                            'glab',
                            glab.id
                        )
                    
                    # Mark as sent
                    if existing:
                        existing.sent = True
                        existing.sent_at = datetime.utcnow()
                    else:
                        reminder = ScheduledReminder(
                            reminder_type='license_payment',
                            target_type='glab',
                            target_id=glab.id,
                            due_date=glab.next_payment_due,
                            days_before=days,
                            sent=True,
                            sent_at=datetime.utcnow()
                        )
                        db.session.add(reminder)
    
    # Assessor Recertification Reminders
    for assessor in User.query.filter(User.role == 'glab_assessor', User.recertification_due != None, User.is_active == True).all():
        for days in reminder_days:
            reminder_date = assessor.recertification_due - timedelta(days=days)
            if today == reminder_date:
                existing = ScheduledReminder.query.filter_by(
                    reminder_type='recertification',
                    target_type='assessor',
                    target_id=assessor.id,
                    days_before=days
                ).first()
                
                if not existing or not existing.sent:
                    # Notify assessor
                    create_notification(
                        assessor.id,
                        'recertification_reminder',
                        f'Recertification Due in {days} Days',
                        f'Your assessor certification expires on {assessor.recertification_due.strftime("%B %d, %Y")}. Please ensure you have completed the required CPD hours and apply for recertification.',
                        'cpd',
                        None
                    )
                    
                    # Mark as sent
                    if existing:
                        existing.sent = True
                        existing.sent_at = datetime.utcnow()
                    else:
                        reminder = ScheduledReminder(
                            reminder_type='recertification',
                            target_type='assessor',
                            target_id=assessor.id,
                            due_date=assessor.recertification_due,
                            days_before=days,
                            sent=True,
                            sent_at=datetime.utcnow()
                        )
                        db.session.add(reminder)
    
    db.session.commit()


# Run reminder check on each request (lightweight, only checks dates)
@app.before_request
def before_request_reminder_check():
    """Check reminders once per day per session"""
    if current_user.is_authenticated:
        last_check = session.get('last_reminder_check')
        today = datetime.utcnow().date().isoformat()
        if last_check != today:
            try:
                check_and_send_reminders()
                session['last_reminder_check'] = today
            except Exception as e:
                app.logger.error(f"Reminder check error: {str(e)}")


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
    try:
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
            if not glab:
                flash('Your account is not assigned to a GLAB. Contact GEA admin.', 'error')
                return redirect(url_for('logout'))
            
            clients = list(glab.clients.all())
            projects = list(glab.projects.order_by(Project.created_at.desc()).all())
            unread_messages = ChatMessage.query.join(Project).filter(
                Project.glab_id == glab.id,
                ChatMessage.is_read == False,
                ChatMessage.sender_id != current_user.id
            ).count()
            
            # Calculate phase counts
            phase_counts = {
                'enrollment': len([p for p in projects if p.current_phase == 1]),
                'safeguards': len([p for p in projects if p.current_phase == 2]),
                'preliminary': len([p for p in projects if p.current_phase == 3]),
                'engagement': len([p for p in projects if p.current_phase == 4]),
                'assessment': len([p for p in projects if p.current_phase == 5]),
                'reporting': len([p for p in projects if p.current_phase == 6]),
                'certification': len([p for p in projects if p.current_phase == 7]),
                'post_certification': len([p for p in projects if p.current_phase == 8]),
            }
            
            return render_template('dashboard_glab.html',
                glab=glab,
                clients=clients,
                projects=projects,
                unread_messages=unread_messages,
                phase_counts=phase_counts,
                phases=PHASES
            )
        
        elif current_user.role == 'glab_assessor':
            # Assessor Dashboard - only sees assigned projects
            projects = list(current_user.assigned_projects)
            
            # CPD tracking
            cpd_hours = sum(log.hours for log in current_user.cpd_logs if log.status == 'approved')
            
            return render_template('dashboard_assessor.html',
                projects=projects,
                phases=PHASES,
                cpd_hours=cpd_hours
            )
        
        elif current_user.role == 'technical_expert':
            # Technical Expert Dashboard - sees assigned projects
            projects = list(current_user.expert_projects)
            
            return render_template('dashboard_expert.html',
                projects=projects,
                phases=PHASES
            )
        
        elif current_user.role == 'cert_committee':
            # Certification Committee Dashboard - sees projects in Phase 7
            projects = list(current_user.committee_projects)
            pending_decisions = [p for p in projects if p.current_phase == 7]
            
            return render_template('dashboard_committee.html',
                projects=projects,
                pending_decisions=pending_decisions,
                phases=PHASES
            )
        
        elif current_user.role == 'client_user':
            # Client User Dashboard - sees their organization's projects
            client = Client.query.get(current_user.client_id)
            if client:
                projects = list(client.projects.all())
            else:
                projects = []
            
            return render_template('dashboard_client.html',
                client=client,
                projects=projects,
                phases=PHASES
            )
        
        return redirect(url_for('login'))
    
    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}")
        db.session.rollback()
        flash('An error occurred loading the dashboard.', 'error')
        return render_template('errors/500.html'), 500


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
    try:
        glab = GLAB.query.get_or_404(glab_id)
        if not current_user.is_gea() and current_user.glab_id != glab_id:
            flash('Access denied.', 'error')
            return redirect(url_for('dashboard'))
        
        projects = list(glab.projects.order_by(Project.created_at.desc()).all())
        clients = list(glab.clients.all())
        assessors = User.query.filter_by(glab_id=glab_id, role='glab_assessor').all()
        
        return render_template('glabs/view.html', glab=glab, projects=projects, clients=clients, assessors=assessors, phases=PHASES)
    except Exception as e:
        app.logger.error(f"View GLAB error for glab {glab_id}: {str(e)}")
        db.session.rollback()
        flash('An error occurred loading GLAB details.', 'error')
        return redirect(url_for('list_glabs'))


# =============================================================================
# CLIENT MANAGEMENT (GEA and GLAB)
# =============================================================================

@app.route('/clients')
@login_required
def list_clients():
    try:
        if current_user.is_gea():
            clients = Client.query.order_by(Client.created_at.desc()).all()
        elif current_user.glab_id:
            clients = Client.query.filter_by(glab_id=current_user.glab_id).order_by(Client.created_at.desc()).all()
        else:
            clients = []
        
        return render_template('clients/list.html', clients=clients)
    except Exception as e:
        app.logger.error(f"List clients error: {str(e)}")
        flash('An error occurred.', 'error')
        return redirect(url_for('dashboard'))


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
    try:
        client = Client.query.get_or_404(client_id)
        if not current_user.is_gea() and client.glab_id != current_user.glab_id:
            flash('Access denied.', 'error')
            return redirect(url_for('dashboard'))
        
        projects = list(client.projects.all())
        return render_template('clients/view.html', client=client, projects=projects, phases=PHASES)
    except Exception as e:
        app.logger.error(f"View client error for client {client_id}: {str(e)}")
        db.session.rollback()
        flash('An error occurred loading client details.', 'error')
        return redirect(url_for('list_clients'))


# =============================================================================
# PROJECT MANAGEMENT
# =============================================================================

@app.route('/projects')
@login_required
def list_projects():
    try:
        if current_user.is_gea():
            projects = Project.query.order_by(Project.created_at.desc()).all()
        elif current_user.role == 'glab_assessor':
            projects = list(current_user.assigned_projects)
        elif current_user.glab_id:
            projects = Project.query.filter_by(glab_id=current_user.glab_id).order_by(Project.created_at.desc()).all()
        else:
            projects = []
        
        return render_template('projects/list.html', projects=projects, phases=PHASES)
    except Exception as e:
        app.logger.error(f"List projects error: {str(e)}")
        flash('An error occurred.', 'error')
        return redirect(url_for('dashboard'))


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
    try:
        project = Project.query.get_or_404(project_id)
        
        # Access control
        if current_user.role == 'glab_assessor':
            if project not in current_user.assigned_projects:
                flash('Access denied. You are not assigned to this project.', 'error')
                return redirect(url_for('dashboard'))
        elif not current_user.is_gea() and project.glab_id != current_user.glab_id:
            flash('Access denied.', 'error')
            return redirect(url_for('dashboard'))
        
        # Get all checklists organized by phase
        all_checklists = ChecklistItem.query.filter_by(project_id=project_id).order_by(ChecklistItem.order).all()
        checklist_by_phase = {}
        for item in all_checklists:
            if item.phase_number not in checklist_by_phase:
                checklist_by_phase[item.phase_number] = []
            checklist_by_phase[item.phase_number].append(item)
        
        # Get all documents organized by phase and document_key
        all_documents = Document.query.filter_by(project_id=project_id).all()
        documents_by_phase = {}
        for doc in all_documents:
            if doc.phase_number not in documents_by_phase:
                documents_by_phase[doc.phase_number] = {}
            if doc.document_key:
                documents_by_phase[doc.phase_number][doc.document_key] = doc
        
        # Get all templates organized by phase and document_key
        all_templates = PhaseTemplate.query.filter_by(is_active=True).all()
        templates_by_phase = {}
        for template in all_templates:
            if template.phase_number not in templates_by_phase:
                templates_by_phase[template.phase_number] = {}
            if template.document_key:
                templates_by_phase[template.phase_number][template.document_key] = template
        
        # Get chat messages
        messages = ChatMessage.query.filter_by(project_id=project_id).order_by(ChatMessage.sent_at.desc()).limit(50).all()
        
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
            checklist_by_phase=checklist_by_phase,
            documents_by_phase=documents_by_phase,
            templates_by_phase=templates_by_phase,
            messages=messages,
            available_assessors=available_assessors,
            phase_logs=phase_logs,
            phases=PHASES
        )
    except Exception as e:
        app.logger.error(f"View project error for project {project_id}: {str(e)}")
        db.session.rollback()
        flash('An error occurred loading project details.', 'error')
        return redirect(url_for('list_projects'))


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
    
    # GLAB admin can only assign assessors to their own GLAB's projects
    if current_user.role == 'glab_admin' and project.glab_id != current_user.glab_id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Access denied'})
        flash('Access denied.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    if not current_user.is_gea() and current_user.role != 'glab_admin':
        if request.is_json:
            return jsonify({'success': False, 'error': 'Access denied'})
        flash('Access denied.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    # Get assessor_id from JSON or form
    if request.is_json:
        assessor_id = request.json.get('assessor_id')
    else:
        assessor_id = request.form.get('assessor_id')
    
    assessor = User.query.get_or_404(assessor_id)
    
    # Verify assessor belongs to this GLAB
    if assessor.glab_id != project.glab_id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Assessor does not belong to this GLAB'})
        flash('Assessor does not belong to this GLAB.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    if assessor not in project.assessors:
        project.assessors.append(assessor)
        db.session.commit()
        
        # Create notification for the assessor
        create_notification(
            assessor.id,
            'assessor_assignment',
            f'Assigned to Project: {project.reference_number}',
            f'You have been assigned to project {project.reference_number} for {project.client.name}.',
            'project',
            project.id
        )
        
        if request.is_json:
            return jsonify({'success': True})
        flash(f'Assessor {assessor.full_name or assessor.username} assigned.', 'success')
    else:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Assessor already assigned'})
    
    return redirect(url_for('view_project', project_id=project_id))


@app.route('/projects/<int:project_id>/assessors/remove', methods=['POST'])
@login_required
def remove_assessor(project_id):
    project = Project.query.get_or_404(project_id)
    
    # GLAB admin can only manage assessors on their own GLAB's projects
    if current_user.role == 'glab_admin' and project.glab_id != current_user.glab_id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Access denied'})
        flash('Access denied.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    if not current_user.is_gea() and current_user.role != 'glab_admin':
        if request.is_json:
            return jsonify({'success': False, 'error': 'Access denied'})
        flash('Access denied.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    # Get assessor_id from JSON or form
    if request.is_json:
        assessor_id = request.json.get('assessor_id')
    else:
        assessor_id = request.form.get('assessor_id')
    
    assessor = User.query.get_or_404(assessor_id)
    
    if assessor in project.assessors:
        project.assessors.remove(assessor)
        db.session.commit()
        if request.is_json:
            return jsonify({'success': True})
        flash('Assessor removed.', 'success')
    else:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Assessor not assigned to this project'})
    
    return redirect(url_for('view_project', project_id=project_id))


# Keep the old route for backward compatibility
@app.route('/projects/<int:project_id>/assessors/<int:user_id>/remove', methods=['POST'])
@login_required
def remove_assessor_by_id(project_id, user_id):
    project = Project.query.get_or_404(project_id)
    
    if not current_user.is_gea() and current_user.role != 'glab_admin':
        flash('Access denied.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    assessor = User.query.get_or_404(user_id)
    
    if assessor in project.assessors:
        project.assessors.remove(assessor)
        db.session.commit()
        flash('Assessor removed.', 'success')
    
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
# PROFILE MANAGEMENT
# =============================================================================

@app.route('/profile')
@login_required
def view_profile():
    return render_template('profile/view.html')


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        current_user.phone = request.form.get('phone')
        current_user.bio = request.form.get('bio')
        
        # Handle profile photo upload
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and file.filename and allowed_file(file.filename):
                # Delete old photo if exists
                if current_user.profile_photo:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], current_user.profile_photo)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                
                filename = secure_filename(file.filename)
                stored_filename = f"profile_{current_user.id}_{uuid.uuid4()}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
                file.save(file_path)
                current_user.profile_photo = stored_filename
        
        # Update email notifications preference
        current_user.email_notifications = request.form.get('email_notifications') == 'on'
        
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('view_profile'))
    
    return render_template('profile/edit.html')


@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files (profile photos, etc.)"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# =============================================================================
# ANNOUNCEMENTS (GEA to GLABs)
# =============================================================================

@app.route('/announcements')
@login_required
def list_announcements():
    if current_user.is_gea():
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    else:
        # Show announcements for this GLAB or all GLABs
        announcements = Announcement.query.filter(
            db.or_(
                Announcement.target_glab_id == None,
                Announcement.target_glab_id == current_user.glab_id
            ),
            Announcement.is_active == True
        ).order_by(Announcement.created_at.desc()).all()
    
    glabs = GLAB.query.all() if current_user.is_gea() else None
    return render_template('announcements/list.html', announcements=announcements, glabs=glabs)


@app.route('/announcements/create', methods=['GET', 'POST'])
@login_required
@gea_required
def create_announcement():
    glabs = GLAB.query.filter_by(status='active').all()
    
    if request.method == 'POST':
        target_glab_id = request.form.get('target_glab_id') or None
        
        announcement = Announcement(
            title=request.form.get('title'),
            message=request.form.get('message'),
            priority=request.form.get('priority', 'normal'),
            target_glab_id=int(target_glab_id) if target_glab_id else None,
            created_by=current_user.id
        )
        db.session.add(announcement)
        db.session.commit()
        
        flash('Announcement sent successfully.', 'success')
        return redirect(url_for('list_announcements'))
    
    return render_template('announcements/form.html', glabs=glabs)


@app.route('/announcements/<int:announcement_id>/delete', methods=['POST'])
@login_required
@gea_admin_required
def delete_announcement(announcement_id):
    announcement = Announcement.query.get_or_404(announcement_id)
    announcement.is_active = False
    db.session.commit()
    flash('Announcement deleted.', 'success')
    return redirect(url_for('list_announcements'))


# =============================================================================
# NOTIFICATIONS
# =============================================================================

@app.route('/notifications')
@login_required
def list_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).limit(50).all()
    return render_template('notifications/list.html', notifications=notifications)


@app.route('/api/notifications/unread-count')
@login_required
def get_unread_count():
    return jsonify({'count': current_user.unread_notification_count()})


@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if notification.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True})


@app.route('/api/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({
        'is_read': True,
        'read_at': datetime.utcnow()
    })
    db.session.commit()
    
    return jsonify({'success': True})


# =============================================================================
# CPD LOGS (Assessor Continuing Professional Development)
# =============================================================================

@app.route('/cpd')
@login_required
def list_cpd_logs():
    if current_user.role == 'glab_assessor':
        # Assessor sees own CPD logs
        cpd_logs = CPDLog.query.filter_by(assessor_id=current_user.id).order_by(CPDLog.activity_date.desc()).all()
        total_hours = sum(log.hours for log in cpd_logs if log.status == 'approved')
    elif current_user.is_gea():
        # GEA sees all CPD logs (for review)
        cpd_logs = CPDLog.query.order_by(CPDLog.submitted_at.desc()).all()
        total_hours = 0
    else:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('cpd/list.html', cpd_logs=cpd_logs, total_hours=total_hours)


@app.route('/cpd/create', methods=['GET', 'POST'])
@login_required
def create_cpd_log():
    if current_user.role != 'glab_assessor':
        flash('Only assessors can submit CPD logs.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        cpd_log = CPDLog(
            assessor_id=current_user.id,
            activity_type=request.form.get('activity_type'),
            activity_title=request.form.get('activity_title'),
            activity_date=datetime.strptime(request.form.get('activity_date'), '%Y-%m-%d').date(),
            hours=float(request.form.get('hours')),
            description=request.form.get('description')
        )
        
        # Handle evidence upload
        if 'evidence' in request.files:
            file = request.files['evidence']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                stored_filename = f"cpd_{uuid.uuid4()}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], stored_filename)
                file.save(file_path)
                cpd_log.evidence_filename = filename
                cpd_log.evidence_stored_filename = stored_filename
        
        db.session.add(cpd_log)
        db.session.commit()
        
        flash('CPD activity logged successfully.', 'success')
        return redirect(url_for('list_cpd_logs'))
    
    return render_template('cpd/form.html')


@app.route('/cpd/<int:cpd_id>/review', methods=['POST'])
@login_required
@gea_required
def review_cpd_log(cpd_id):
    cpd_log = CPDLog.query.get_or_404(cpd_id)
    action = request.form.get('action')
    notes = request.form.get('notes', '')
    
    if action in ['approved', 'rejected']:
        cpd_log.status = action
        cpd_log.review_notes = notes
        cpd_log.reviewed_by = current_user.id
        cpd_log.reviewed_at = datetime.utcnow()
        db.session.commit()
        
        # Notify assessor
        create_notification(
            cpd_log.assessor_id,
            'cpd_review',
            f'CPD Log {action.title()}',
            f'Your CPD activity "{cpd_log.activity_title}" has been {action}.',
            'cpd',
            cpd_log.id
        )
        
        flash(f'CPD log {action}.', 'success')
    
    return redirect(url_for('list_cpd_logs'))


# =============================================================================
# TECHNICAL EXPERTS & COMMITTEE ASSIGNMENT
# =============================================================================

@app.route('/projects/<int:project_id>/experts/assign', methods=['POST'])
@login_required
@gea_required
def assign_expert(project_id):
    project = Project.query.get_or_404(project_id)
    expert_id = request.form.get('expert_id')
    expert = User.query.get_or_404(expert_id)
    
    if expert.role != 'technical_expert':
        flash('Selected user is not a technical expert.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    if expert not in project.technical_experts:
        project.technical_experts.append(expert)
        db.session.commit()
        
        # Notify expert
        create_notification(
            expert.id,
            'expert_assigned',
            'Assigned to Project',
            f'You have been assigned as a technical expert to project {project.reference_number}.',
            'project',
            project.id
        )
        
        flash(f'Technical expert {expert.full_name or expert.username} assigned.', 'success')
    
    return redirect(url_for('view_project', project_id=project_id))


@app.route('/projects/<int:project_id>/committee/assign', methods=['POST'])
@login_required
@gea_admin_required
def assign_committee_member(project_id):
    project = Project.query.get_or_404(project_id)
    member_id = request.form.get('member_id')
    member = User.query.get_or_404(member_id)
    
    if member.role != 'cert_committee':
        flash('Selected user is not a certification committee member.', 'error')
        return redirect(url_for('view_project', project_id=project_id))
    
    if member not in project.committee_members:
        project.committee_members.append(member)
        db.session.commit()
        
        # Notify member
        create_notification(
            member.id,
            'committee_assigned',
            'Assigned to Certification Committee',
            f'You have been assigned to the certification committee for project {project.reference_number}.',
            'project',
            project.id
        )
        
        flash(f'Committee member {member.full_name or member.username} assigned.', 'success')
    
    return redirect(url_for('view_project', project_id=project_id))


# =============================================================================
# QUALITY CHECKLIST (GEA Review)
# =============================================================================

@app.route('/api/projects/<int:project_id>/quality-checklist/<int:item_id>/toggle', methods=['POST'])
@login_required
@gea_required
def toggle_quality_checklist(project_id, item_id):
    item = QualityChecklistItem.query.get_or_404(item_id)
    
    if item.project_id != project_id:
        return jsonify({'success': False, 'error': 'Item not found'}), 404
    
    item.is_checked = not item.is_checked
    if item.is_checked:
        item.checked_by = current_user.id
        item.checked_at = datetime.utcnow()
    else:
        item.checked_by = None
        item.checked_at = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_checked': item.is_checked,
        'checked_by': current_user.full_name or current_user.username if item.is_checked else None
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
