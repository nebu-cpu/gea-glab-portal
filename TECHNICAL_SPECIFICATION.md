# GEA Portal - Complete Technical Specification

## 1. User Types & Roles

### 1.1 Role Definitions

| Role | Code | Description | Parent Org |
|------|------|-------------|------------|
| GEA Admin | `gea_admin` | Full system access, can create all accounts | GEA |
| GEA Staff | `gea_staff` | Limited GEA access, assigned to functions | GEA |
| GLAB Admin | `glab_admin` | Manages their GLAB's operations | GLAB |
| GLAB Assessor | `glab_assessor` | Conducts assessments for their GLAB | GLAB |
| Technical Expert | `technical_expert` | Domain expert, not tied to a GLAB | Independent |
| Certification Committee | `cert_committee` | Reviews and decides certification | GEA-appointed |
| Client Organization | `client_user` | Organization seeking certification | Client |

### 1.2 Staff Functions (for GEA Staff)

```
STAFF_FUNCTIONS = [
    'review_team',      # Reviews project submissions
    'quality_team',     # Quality assurance
    'operations',       # Day-to-day operations
    'finance',          # Financial matters
    'registry',         # Certificate registry
]
```

---

## 2. Database Models

### 2.1 User Model (Enhanced)

```python
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120))
    
    # Profile
    profile_photo = db.Column(db.String(255))  # Stored filename
    phone = db.Column(db.String(50))
    bio = db.Column(db.Text)
    
    # Role & Organization
    role = db.Column(db.String(30), nullable=False)
    staff_function = db.Column(db.String(30))  # For gea_staff only
    glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))  # For client_user
    
    # Assessor-specific fields
    assessor_id = db.Column(db.String(50), unique=True)  # Certificate ID
    certification_date = db.Column(db.Date)
    recertification_due = db.Column(db.Date)  # certification_date + 3 years
    assessor_specializations = db.Column(db.Text)  # JSON array of domains
    
    # Technical Expert fields
    expert_domains = db.Column(db.Text)  # JSON array of expertise areas
    
    # Status & Tracking
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_login = db.Column(db.DateTime)
    
    # Notification preferences
    email_notifications = db.Column(db.Boolean, default=True)
    
    # Relationships
    cpd_logs = db.relationship('CPDLog', backref='assessor', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
```

### 2.2 GLAB Model (Enhanced)

```python
class GLAB(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    license_number = db.Column(db.String(50), unique=True, nullable=False)  # Unique ID
    
    # Contact Info
    country = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(50))
    
    # License & Payment
    license_type = db.Column(db.String(20), default='annual')  # 'annual' or 'triennial'
    license_start_date = db.Column(db.Date)
    license_expiry_date = db.Column(db.Date)  # Calculated based on type
    last_payment_date = db.Column(db.Date)
    next_payment_due = db.Column(db.Date)  # For reminders
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, suspended, terminated
    
    # Tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
```

### 2.3 Client Model (Enhanced)

```python
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    
    # Organization Details
    country = db.Column(db.String(100), nullable=False)
    registered_address = db.Column(db.Text)
    industry_sector = db.Column(db.String(100))
    total_employees = db.Column(db.Integer)
    number_of_sites = db.Column(db.Integer, default=1)
    
    # Primary Contact
    primary_contact_name = db.Column(db.String(100))
    primary_contact_email = db.Column(db.String(120))
    primary_contact_phone = db.Column(db.String(50))
    
    # Assignment
    glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'))  # Assigned GLAB
    
    # Tracking
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='client', lazy='dynamic')
```

### 2.4 Project Model (Enhanced)

```python
# Association tables
project_assessors = db.Table('project_assessors', ...)
project_technical_experts = db.Table('project_technical_experts',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)
project_committee_members = db.Table('project_committee_members',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reference_number = db.Column(db.String(50), unique=True, nullable=False)
    
    # Assignments
    glab_id = db.Column(db.Integer, db.ForeignKey('glab.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    lead_assessor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Assessment Details
    assessment_type = db.Column(db.String(50), default='initial')
    current_phase = db.Column(db.Integer, default=1)
    
    # GEA Review Status (per phase)
    gea_status = db.Column(db.String(30), default='pending')
    gea_notes = db.Column(db.Text)
    gea_reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    gea_reviewed_at = db.Column(db.DateTime)
    
    # Financial fields...
    
    # Relationships
    assessors = db.relationship('User', secondary=project_assessors, ...)
    technical_experts = db.relationship('User', secondary=project_technical_experts, ...)
    committee_members = db.relationship('User', secondary=project_committee_members, ...)
```

### 2.5 Checklist Models (Dual System)

```python
class ChecklistItem(db.Model):
    """Operational checklist - managed by GLAB"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    phase_number = db.Column(db.Integer, nullable=False)
    item_text = db.Column(db.String(500), nullable=False)
    
    # Completion
    is_completed = db.Column(db.Boolean, default=False)
    completed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    completed_at = db.Column(db.DateTime)
    
    # Configuration
    is_required = db.Column(db.Boolean, default=True)
    is_custom = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)
    
    # Document attachment
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'))


class QualityChecklistItem(db.Model):
    """Quality/Review checklist - managed by GEA"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    phase_number = db.Column(db.Integer, nullable=False)
    
    # Quality check items
    item_text = db.Column(db.String(500), nullable=False)
    check_type = db.Column(db.String(30))  # 'received', 'verified', 'approved'
    
    # Review
    is_checked = db.Column(db.Boolean, default=False)
    checked_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    checked_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    # Links to document being reviewed
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'))


class PhaseReview(db.Model):
    """Phase-level review outcome"""
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    phase_number = db.Column(db.Integer, nullable=False)
    
    # Review outcome
    outcome = db.Column(db.String(30))  # 'approved', 'changes_requested', 'rejected'
    comments = db.Column(db.Text)
    
    # Reviewer
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### 2.6 Document Model (Enhanced)

```python
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    phase_number = db.Column(db.Integer, nullable=False)
    
    # Document info
    document_key = db.Column(db.String(50), nullable=False)
    document_type = db.Column(db.String(100))
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    
    # Upload info
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Review status
    status = db.Column(db.String(20), default='pending')
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_at = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)
    
    # Version control
    version = db.Column(db.Integer, default=1)
    parent_id = db.Column(db.Integer, db.ForeignKey('document.id'))  # For replacements
```

### 2.7 Notification System

```python
class Notification(db.Model):
    """User notifications"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Content
    notification_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    
    # Links
    link_type = db.Column(db.String(30))  # 'project', 'announcement', 'chat', etc.
    link_id = db.Column(db.Integer)
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    
    # Email
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Notification Types
NOTIFICATION_TYPES = {
    'chat_message': 'New message in project chat',
    'announcement': 'New announcement',
    'document_review': 'Document review completed',
    'phase_approved': 'Phase approved by GEA',
    'changes_requested': 'Changes requested by GEA',
    'assessor_assigned': 'You have been assigned to a project',
    'license_reminder': 'License payment reminder',
    'cpd_reminder': 'CPD compliance reminder',
    'recertification_reminder': 'Recertification due reminder',
    'project_created': 'New project created',
}
```

### 2.8 CPD & Recertification

```python
class CPDLog(db.Model):
    """Continuing Professional Development logs for assessors"""
    id = db.Column(db.Integer, primary_key=True)
    assessor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Activity details
    activity_type = db.Column(db.String(50), nullable=False)
    activity_title = db.Column(db.String(200), nullable=False)
    activity_date = db.Column(db.Date, nullable=False)
    hours = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    
    # Evidence
    evidence_filename = db.Column(db.String(255))
    evidence_stored_filename = db.Column(db.String(255))
    
    # Review
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewed_at = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)
    
    # Tracking
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)


class RecertificationRecord(db.Model):
    """Tracks assessor recertification cycles"""
    id = db.Column(db.Integer, primary_key=True)
    assessor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Cycle
    cycle_start = db.Column(db.Date, nullable=False)
    cycle_end = db.Column(db.Date, nullable=False)  # cycle_start + 3 years
    
    # Status
    status = db.Column(db.String(20), default='active')  # active, completed, lapsed
    
    # Completion
    total_cpd_hours = db.Column(db.Float, default=0)
    required_cpd_hours = db.Column(db.Float, default=60)  # Configurable
    renewed_at = db.Column(db.DateTime)
    renewed_by = db.Column(db.Integer, db.ForeignKey('user.id'))
```

### 2.9 Scheduled Reminders

```python
class ScheduledReminder(db.Model):
    """Tracks scheduled reminders to avoid duplicates"""
    id = db.Column(db.Integer, primary_key=True)
    
    # Target
    reminder_type = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(30), nullable=False)  # 'glab', 'assessor'
    target_id = db.Column(db.Integer, nullable=False)
    
    # Schedule
    due_date = db.Column(db.Date, nullable=False)
    days_before = db.Column(db.Integer, nullable=False)  # 60, 30, 15, 5
    
    # Status
    sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime)
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('reminder_type', 'target_type', 'target_id', 'days_before'),
    )
```

---

## 3. Permissions Matrix

### 3.1 Checklist Permissions (Recommended: Option C - Dual Checklists)

| Action | GEA Admin | GEA Staff | GLAB Admin | Assessor | Tech Expert | Committee |
|--------|-----------|-----------|------------|----------|-------------|-----------|
| View Operational Checklist | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Complete Operational Items | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Add Operational Items | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| View Quality Checklist | ✓ | ✓ | ✓ (read) | ✓ (read) | ✗ | ✓ |
| Complete Quality Items | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Review Phase Outcome | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |

### 3.2 Project Permissions

| Action | GEA Admin | GEA Staff | GLAB Admin | Assessor | Tech Expert | Client |
|--------|-----------|-----------|------------|----------|-------------|--------|
| Create Project | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| View All Projects | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| View GLAB Projects | ✓ | ✓ | ✓ | Assigned | Assigned | Own |
| Edit Project | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Assign Assessors | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Assign Tech Experts | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Assign Committee | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Upload Documents | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ |
| Review Documents | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |
| Advance Phase | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| Approve Phase | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ |

---

## 4. Notification System Logic

### 4.1 Trigger Events

```python
def create_notification(user_id, notification_type, title, message, link_type=None, link_id=None):
    """Create a notification and optionally send email"""
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
    
    # Send email if user has email_notifications enabled
    user = User.query.get(user_id)
    if user.email_notifications:
        send_notification_email(user, notification)

# Event triggers:
# 1. Chat message → notify all project participants except sender
# 2. Announcement → notify all target users
# 3. Document uploaded → notify GEA reviewers
# 4. Document reviewed → notify uploader
# 5. Phase approved → notify GLAB
# 6. Changes requested → notify GLAB
# 7. Assessor assigned → notify assessor
# 8. License reminder → notify GLAB users
# 9. CPD reminder → notify assessor
# 10. Recertification reminder → notify assessor
```

### 4.2 Reminder Schedules

```python
REMINDER_DAYS = [60, 30, 15, 5]  # Days before due date

def check_and_send_reminders():
    """Run daily to check for upcoming reminders"""
    today = date.today()
    
    # GLAB License Reminders
    for days in REMINDER_DAYS:
        target_date = today + timedelta(days=days)
        glabs = GLAB.query.filter(
            GLAB.next_payment_due == target_date,
            GLAB.status == 'active'
        ).all()
        for glab in glabs:
            # Check if reminder already sent
            existing = ScheduledReminder.query.filter_by(
                reminder_type='license_payment',
                target_type='glab',
                target_id=glab.id,
                days_before=days
            ).first()
            if not existing or not existing.sent:
                send_license_reminder(glab, days)
    
    # Assessor CPD Reminders (quarterly)
    # ...
    
    # Assessor Recertification Reminders
    for days in REMINDER_DAYS:
        target_date = today + timedelta(days=days)
        assessors = User.query.filter(
            User.role == 'glab_assessor',
            User.recertification_due == target_date,
            User.is_active == True
        ).all()
        for assessor in assessors:
            send_recertification_reminder(assessor, days)
```

---

## 5. Quality-Oriented Review Checklist

### 5.1 Default Quality Items per Phase

```python
QUALITY_CHECKLIST = {
    1: [  # Enrollment Phase
        {'text': 'Enrollment form is complete and signed', 'type': 'received'},
        {'text': 'Organization eligibility verified', 'type': 'verified'},
        {'text': 'Baseline profile is accurate', 'type': 'verified'},
        {'text': 'Decision documented and justified', 'type': 'approved'},
    ],
    2: [  # Ethical Safeguards
        {'text': 'COI declarations received from all assessors', 'type': 'received'},
        {'text': 'No conflicts of interest identified', 'type': 'verified'},
        {'text': 'Code of conduct signed by all assessors', 'type': 'received'},
        {'text': 'Assessor neutrality confirmed', 'type': 'approved'},
    ],
    # ... phases 3-8
}
```

### 5.2 Review Workflow

1. GLAB completes operational checklist items
2. GLAB uploads required documents
3. GEA staff reviews each document (approve/request changes/reject)
4. GEA staff completes quality checklist items
5. GEA staff sets phase review outcome
6. If approved, GLAB can advance to next phase
7. If changes requested, GLAB makes corrections and resubmits

---

## 6. API Endpoints Summary

### 6.1 Notifications

```
GET  /api/notifications              # Get user's notifications
POST /api/notifications/:id/read     # Mark as read
POST /api/notifications/mark-all-read
GET  /api/notifications/unread-count # For badge display
```

### 6.2 Chat

```
GET  /api/projects/:id/messages      # Get messages (polling)
POST /api/projects/:id/messages      # Send message
```

### 6.3 Checklists

```
POST /api/projects/:id/checklist/:item_id/toggle     # Toggle operational item
POST /api/projects/:id/quality-checklist/:item_id/toggle  # Toggle quality item
```

---

## 7. Implementation Priority

### Phase 1 (Critical - Fix 500 Errors)
1. Debug and fix all 500 errors
2. Ensure all view routes handle edge cases
3. Add proper error logging

### Phase 2 (Core Features)
1. Implement enhanced User model with photos
2. Add Notification model and basic notifications
3. Implement dual checklist system

### Phase 3 (User Types)
1. Add Technical Expert and Committee member support
2. Add Client user accounts
3. Implement CPD logs and recertification tracking

### Phase 4 (Reminders)
1. Implement scheduled reminder system
2. Add GLAB license reminders
3. Add assessor CPD and recertification reminders

### Phase 5 (Polish)
1. Email notifications
2. Notification center UI
3. Admin dashboard improvements
