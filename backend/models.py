# models.py - Complete database models with all required columns
from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, ForeignKey, Enum, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid
import enum

Base = declarative_base()

# Additional imports for vector search
from sqlalchemy.dialects.postgresql import ARRAY

# Enums for Matter
class MatterType(enum.Enum):
    PERSONAL_INJURY = "personal_injury"
    CRIMINAL = "criminal"
    IMMIGRATION = "immigration"
    FAMILY = "family"
    CORPORATE = "corporate"
    REAL_ESTATE = "real_estate"
    OTHER = "other"

class MatterStatus(enum.Enum):
    PROSPECTIVE = "prospective"
    ACTIVE = "active"
    CLOSED = "closed"
    ON_HOLD = "on_hold"
    ARCHIVED = "archived"

# Organization model for law firms
class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)  # "Smith & Associates Law"
    subscription_tier = Column(String, default="basic")  # basic, pro, enterprise
    billing_email = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # AI Backend Configuration
    ai_backend = Column(String, default="cloud")  # cloud, local, auto
    local_llm_endpoint = Column(String, nullable=True)  # e.g., http://localhost:11434
    local_llm_model = Column(String, nullable=True)  # e.g., llama2, mixtral
    ai_fallback_enabled = Column(Boolean, default=True)  # Allow cloud fallback
    
    # AI Budget and Limits
    ai_monthly_budget = Column(Float, nullable=True)  # Monthly budget in USD
    ai_budget_alert_threshold = Column(Float, default=0.8)  # Alert at 80% by default
    ai_budget_period_start = Column(DateTime, nullable=True)  # Start of current budget period
    ai_current_month_cost = Column(Float, default=0.0)  # Running total for current month
    ai_cost_alerts_enabled = Column(Boolean, default=True)
    ai_max_tokens_per_request = Column(Integer, default=4000)
    ai_rate_limit_per_minute = Column(Integer, default=10)  # Requests per minute
    
    # Relationships
    users = relationship("User", back_populates="organization")
    documents = relationship("Document", back_populates="organization")
    chat_sessions = relationship("ChatSession", back_populates="organization")
    
    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name}, tier={self.subscription_tier})>"

# User model for attorneys and staff
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    role = Column(String, default="attorney")  # attorney, admin, paralegal
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    
    # AI preferences
    ai_provider_preference = Column(String(50), nullable=True)  # claude, openai, gemini, local
    ai_model_preferences = Column(JSON, nullable=True)  # {"claude": "opus", "openai": "gpt-4"}
    ai_consent_given = Column(Boolean, default=False)
    ai_consent_date = Column(DateTime, nullable=True)
    
    # Relationship
    organization = relationship("Organization", back_populates="users")
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)  # Path to stored file
    file_size = Column(Integer, nullable=False)  # Size in bytes
    content_type = Column(String, nullable=True)  # MIME type
    
    # Multi-tenancy
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    uploaded_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    matter_id = Column(String, ForeignKey("matters.id"), nullable=True, index=True)
    
    # Processing fields
    processing_status = Column(String, default="pending")  # pending, processing, completed, failed
    extracted_content = Column(Text, nullable=True)  # Extracted text content
    summary = Column(Text, nullable=True)  # AI-generated summary
    page_count = Column(Integer, nullable=True)  # Number of pages (for PDFs)
    legal_metadata = Column(Text, nullable=True)  # JSON string containing extracted legal metadata
    error_message = Column(String, nullable=True)  # Error details if processing failed
    
    # Timestamps
    upload_timestamp = Column(DateTime, default=datetime.utcnow)
    processed_timestamp = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="documents")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
    matter = relationship("Matter", back_populates="documents")
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, status={self.processing_status})>"

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, index=True)
    session_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=True)
    
    # Multi-tenancy
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="chat_sessions")
    user = relationship("User")
    messages = relationship("ChatMessage", back_populates="session")
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, name={self.session_name})>"

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # AI response metadata
    model_used = Column(String, nullable=True)
    processing_time = Column(Integer, nullable=True)  # Time in milliseconds
    
    # Relationship
    session = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session={self.session_id}, role={self.role})>"

# Matter model for case management
class Matter(Base):
    __tablename__ = "matters"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    client_id = Column(String, ForeignKey("users.id"), nullable=False)
    matter_type = Column(Enum(MatterType), nullable=False)
    status = Column(Enum(MatterStatus), default=MatterStatus.ACTIVE)
    date_opened = Column(DateTime, default=datetime.utcnow)
    date_closed = Column(DateTime, nullable=True)
    opposing_parties = Column(JSON, default=list)  # Array of party objects
    jurisdiction = Column(JSON, nullable=True)  # {"state": "KY/OH", "county": "..."}
    case_number = Column(String, nullable=True)
    judge_assigned = Column(String, nullable=True)
    mcp_metadata = Column(JSON, default=dict)  # Store MCP server references
    
    # Additional fields
    matter_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    billing_type = Column(String, default="hourly")  # hourly, flat_fee, contingency
    estimated_value = Column(Integer, nullable=True)  # In cents
    
    # Relationships
    organization = relationship("Organization")
    client = relationship("User", foreign_keys=[client_id])
    documents = relationship("Document", back_populates="matter")
    deadlines = relationship("Deadline", back_populates="matter")
    communications = relationship("Communication", back_populates="matter")
    
    def __repr__(self):
        return f"<Matter(id={self.id}, name={self.matter_name}, type={self.matter_type}, status={self.status})>"

# Deadline model for matter-related deadlines
class Deadline(Base):
    __tablename__ = "deadlines"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    matter_id = Column(String, ForeignKey("matters.id"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=False)
    is_court_deadline = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    # MCP integration
    mcp_sync_source = Column(String, nullable=True)  # court_calendar, client_calendar, etc.
    mcp_sync_id = Column(String, nullable=True)  # External ID from MCP source
    
    # Relationships
    matter = relationship("Matter", back_populates="deadlines")
    organization = relationship("Organization")
    created_by = relationship("User")
    
    def __repr__(self):
        return f"<Deadline(id={self.id}, title={self.title}, due={self.due_date})>"

# Communication model for tracking emails, calls, etc.
class Communication(Base):
    __tablename__ = "communications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    matter_id = Column(String, ForeignKey("matters.id"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    communication_type = Column(String, nullable=False)  # email, phone, meeting, letter
    direction = Column(String, nullable=False)  # inbound, outbound
    subject = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    participants = Column(JSON, default=list)  # Array of participant info
    timestamp = Column(DateTime, default=datetime.utcnow)
    created_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    # MCP integration
    mcp_source = Column(String, nullable=True)  # email_server, calendar, etc.
    mcp_external_id = Column(String, nullable=True)
    mcp_metadata = Column(JSON, default=dict)
    
    # Relationships
    matter = relationship("Matter", back_populates="communications")
    organization = relationship("Organization")
    created_by = relationship("User")
    
    def __repr__(self):
        return f"<Communication(id={self.id}, type={self.communication_type}, subject={self.subject})>"

# MCP Query Cache for performance optimization
class MCPQueryCache(Base):
    __tablename__ = "mcp_query_cache"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    server_type = Column(String, nullable=False, index=True)  # legal_data, court_api, client_data
    query_hash = Column(String, nullable=False, index=True)  # SHA256 of query params
    response_data = Column(JSON, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional metadata
    query_params = Column(JSON, nullable=True)  # Store original query for debugging
    hit_count = Column(Integer, default=0)  # Track cache effectiveness
    
    # Relationships
    organization = relationship("Organization")
    
    def __repr__(self):
        return f"<MCPQueryCache(id={self.id}, server={self.server_type}, expires={self.expires_at})>"

# Client Communication tracking models
class ClientCommunication(Base):
    __tablename__ = "client_communications"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    matter_id = Column(String, ForeignKey("matters.id"), nullable=False, index=True)
    client_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Communication details
    communication_type = Column(String, nullable=False)  # email, phone, sms, meeting, letter
    direction = Column(String, nullable=False)  # inbound, outbound
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    subject = Column(String, nullable=True)
    content = Column(Text, nullable=True)  # Encrypted for privileged communications
    
    # Participants
    participants = Column(JSON, default=list)  # List of participant objects
    
    # Privilege information
    privilege_type = Column(String, default="not_privileged")  # attorney_client, work_product, confidential
    is_privileged = Column(Boolean, default=False, index=True)
    privilege_description = Column(Text, nullable=True)
    
    # Metadata
    attachments = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    communication_metadata = Column(JSON, default=dict)  # Additional integration-specific data
    
    # Tracking
    created_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Follow-up
    follow_up_required = Column(Boolean, default=False)
    follow_up_completed = Column(Boolean, default=False)
    
    # Integration references
    external_id = Column(String, nullable=True)  # ID from external system
    integration_source = Column(String, nullable=True)  # email_server, phone_system, etc.
    
    # Relationships
    organization = relationship("Organization")
    matter = relationship("Matter", back_populates="client_communications")
    client = relationship("User", foreign_keys=[client_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    follow_ups = relationship("CommunicationFollowUp", back_populates="communication")
    
    def __repr__(self):
        return f"<ClientCommunication(id={self.id}, type={self.communication_type}, matter={self.matter_id})>"

class CommunicationFollowUp(Base):
    __tablename__ = "communication_follow_ups"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    communication_id = Column(String, ForeignKey("client_communications.id"), nullable=False)
    matter_id = Column(String, ForeignKey("matters.id"), nullable=False)
    
    # Follow-up details
    due_date = Column(DateTime, nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String, default="medium")  # low, medium, high, critical
    
    # Assignment
    assigned_to_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Status
    completed = Column(Boolean, default=False)
    completed_date = Column(DateTime, nullable=True)
    completed_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Auto-escalation
    auto_escalate = Column(Boolean, default=True)
    escalated = Column(Boolean, default=False)
    escalated_date = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    communication = relationship("ClientCommunication", back_populates="follow_ups")
    matter = relationship("Matter")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    completed_by = relationship("User", foreign_keys=[completed_by_id])
    
    def __repr__(self):
        return f"<CommunicationFollowUp(id={self.id}, due={self.due_date}, completed={self.completed})>"

class CommunicationTemplate(Base):
    __tablename__ = "communication_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    
    # Template info
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    communication_type = Column(String, nullable=False)  # email, letter, sms
    
    # Content
    subject_template = Column(String, nullable=True)
    content_template = Column(Text, nullable=False)
    
    # Variables
    available_variables = Column(JSON, default=list)  # List of variable names
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    
    # Metadata
    tags = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    
    def __repr__(self):
        return f"<CommunicationTemplate(id={self.id}, name={self.name}, type={self.communication_type})>"

# Add relationship to Matter model
Matter.client_communications = relationship("ClientCommunication", back_populates="matter")

# MCP Monitoring Models
class MCPMetrics(Base):
    __tablename__ = "mcp_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    server_name = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False, index=True)
    duration = Column(Float, nullable=False)  # Response time in seconds
    success = Column(Boolean, nullable=False)
    error = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    metrics_metadata = Column(JSON, default=dict)
    
    def __repr__(self):
        return f"<MCPMetrics(server={self.server_name}, action={self.action}, success={self.success})>"

class MCPHealthStatus(Base):
    __tablename__ = "mcp_health_status"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    server_name = Column(String, nullable=False, unique=True, index=True)
    status = Column(String, nullable=False)  # healthy, degraded, unhealthy, error
    response_time = Column(Float, nullable=True)
    last_check = Column(DateTime, nullable=False)
    error = Column(String, nullable=True)
    health_metadata = Column(JSON, default=dict)  # capabilities, version, uptime_percentage
    
    def __repr__(self):
        return f"<MCPHealthStatus(server={self.server_name}, status={self.status})>"

class MCPAlert(Base):
    __tablename__ = "mcp_alerts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    severity = Column(String, nullable=False, index=True)  # low, medium, high, critical
    type = Column(String, nullable=False)  # error_rate, slow_response, server_down, etc.
    server_name = Column(String, nullable=True, index=True)
    message = Column(Text, nullable=False)
    alert_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, nullable=False, index=True)
    resolved = Column(Boolean, default=False, index=True)
    resolved_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<MCPAlert(severity={self.severity}, type={self.type}, resolved={self.resolved})>"

class MCPCacheMetrics(Base):
    __tablename__ = "mcp_cache_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cache_name = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)  # hit, miss, eviction, stale, refresh
    key = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    cache_metadata = Column(JSON, default=dict)
    
    def __repr__(self):
        return f"<MCPCacheMetrics(cache={self.cache_name}, event={self.event_type}, key={self.key})>"

# API Key Management Models
class APIKeyStore(Base):
    """Database model for encrypted API key storage"""
    __tablename__ = "api_key_store"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # claude, openai, gemini
    encrypted_key = Column(Text, nullable=False)
    key_hint = Column(String(20))  # Last 4 characters for identification
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Validation metadata
    last_validated = Column(DateTime)
    validation_status = Column(String(20))  # valid, invalid, unchecked
    
    # Usage tracking
    last_used = Column(DateTime)
    usage_count = Column(Integer, default=0)
    
    # Relationships
    organization = relationship("Organization")
    created_by_user = relationship("User", foreign_keys=[created_by])

# Consent Management Models
class ConsentType(enum.Enum):
    """Types of AI processing consent"""
    CLOUD_AI = "cloud_ai"
    LOCAL_AI = "local_ai"
    THIRD_PARTY_SHARING = "third_party_sharing"
    DATA_RETENTION = "data_retention"
    ANALYTICS = "analytics"

class ConsentScope(enum.Enum):
    """Scope of consent"""
    ORGANIZATION = "organization"
    USER = "user"
    DOCUMENT = "document"
    SESSION = "session"

class ConsentRecord(Base):
    """Database model for consent records"""
    __tablename__ = "consent_records"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=True)
    
    consent_type = Column(Enum(ConsentType), nullable=False)
    consent_scope = Column(Enum(ConsentScope), nullable=False)
    granted = Column(Boolean, nullable=False)
    
    # Consent details
    purpose = Column(Text)
    data_categories = Column(Text)  # JSON array of data categories
    providers_allowed = Column(Text)  # JSON array of allowed AI providers
    
    # Timestamps
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    
    # Audit trail
    granted_by = Column(String, ForeignKey("users.id"))
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    
    # Legal basis
    legal_basis = Column(String(50))  # consent, legitimate_interest, contract, etc.
    version = Column(String(20))  # Privacy policy version
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[user_id])
    document = relationship("Document", foreign_keys=[document_id])
    granted_by_user = relationship("User", foreign_keys=[granted_by])

class ConsentPreference(Base):
    """Organization-wide consent preferences"""
    __tablename__ = "consent_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), unique=True)
    
    # Default preferences
    require_explicit_consent = Column(Boolean, default=True)
    default_ai_provider = Column(String(50))
    allowed_providers = Column(Text)  # JSON array
    
    # Data handling preferences
    allow_cloud_processing = Column(Boolean, default=True)
    require_local_only = Column(Boolean, default=False)
    data_retention_days = Column(Integer, default=90)
    
    # Notification preferences
    notify_on_processing = Column(Boolean, default=False)
    consent_renewal_days = Column(Integer, default=365)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")

# AI Audit Trail Models
class AIAuditLog(Base):
    """Database model for AI decision audit logs"""
    __tablename__ = "ai_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Request details
    request_id = Column(String(36), unique=True, index=True)
    request_type = Column(String(50))  # chat, analysis, comparison, etc.
    request_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # AI provider details
    provider_used = Column(String(50), nullable=False)
    model_used = Column(String(100))
    provider_fallback = Column(String(200))  # JSON array of attempted providers
    
    # Input data
    input_hash = Column(String(64))  # SHA-256 hash of input for privacy
    input_size = Column(Integer)  # Size in characters
    document_ids = Column(Text)  # JSON array of document IDs
    
    # Output data
    output_hash = Column(String(64))  # SHA-256 hash of output
    output_size = Column(Integer)
    response_time_ms = Column(Integer)
    
    # Consent tracking
    consent_id = Column(Integer, ForeignKey("consent_records.id"))
    consent_verified = Column(String(20))  # granted, denied, default
    
    # Cost and usage
    tokens_used = Column(Integer)
    estimated_cost = Column(Float)
    
    # Decision details
    decision_type = Column(String(100))  # risk_assessment, party_extraction, etc.
    decision_summary = Column(Text)  # Brief summary of AI decision
    confidence_score = Column(Float)
    
    # Data location
    processing_location = Column(String(50))  # cloud, local, hybrid
    data_residency = Column(String(50))  # Country/region code
    
    # Compliance metadata
    retention_expires = Column(DateTime)
    anonymized = Column(DateTime)
    deleted = Column(DateTime)
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User")
    consent = relationship("ConsentRecord")

class AIDecisionDetail(Base):
    """Detailed AI decisions for comprehensive audit"""
    __tablename__ = "ai_decision_details"
    
    id = Column(Integer, primary_key=True, index=True)
    audit_log_id = Column(Integer, ForeignKey("ai_audit_logs.id"), nullable=False)
    
    # Decision components
    decision_category = Column(String(50))  # legal_risk, compliance, extraction
    decision_item = Column(String(200))  # Specific item decided
    decision_value = Column(Text)  # The actual decision/extraction
    confidence = Column(Float)
    
    # Supporting evidence
    evidence_type = Column(String(50))  # document_section, pattern_match, etc.
    evidence_reference = Column(Text)  # Reference to source
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    audit_log = relationship("AIAuditLog")


# Anonymization Models
class AnonymizationPattern(Base):
    """Custom regex patterns for anonymization"""
    __tablename__ = "anonymization_patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    name = Column(String(100), nullable=False)
    description = Column(Text)
    regex_pattern = Column(Text, nullable=False)
    pattern_type = Column(String(50), nullable=False)  # person_name, case_number, etc.
    
    # Configuration
    confidence_threshold = Column(Float, default=0.8)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority patterns are applied first
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[user_id])
    created_by_user = relationship("User", foreign_keys=[created_by])


class AnonymizationRule(Base):
    """Rules for how to handle different pattern types"""
    __tablename__ = "anonymization_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    pattern_type = Column(String(50), nullable=False)  # ssn, credit_card, or "all"
    action = Column(String(20), nullable=False)  # redact, preserve, conditional
    
    # Conditional rules
    condition = Column(JSON)  # {"min_confidence": 0.8, "context": "legal_brief"}
    
    # Consent requirements
    requires_consent = Column(Boolean, default=False)
    consent_message = Column(Text)
    
    # Configuration
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[user_id])


class RedactionToken(Base):
    """Store reversible redaction tokens"""
    __tablename__ = "redaction_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    
    token = Column(String(100), unique=True, index=True)
    encrypted_value = Column(Text, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User")


# Prompt Logging Models
class PromptStatus(enum.Enum):
    """Status of prompts in the system"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PromptLog(Base):
    """Log all prompts for review and audit"""
    __tablename__ = "prompt_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Prompt content
    original_prompt = Column(Text, nullable=False)
    redacted_prompt = Column(Text)
    final_prompt = Column(Text)  # After admin review/edits
    
    # Model selection
    model_requested = Column(String(100))
    model_used = Column(String(100))
    
    # Status and workflow
    status = Column(Enum(PromptStatus), default=PromptStatus.PENDING, index=True)
    requires_review = Column(Boolean, default=False)
    auto_approved = Column(Boolean, default=False)
    
    # Sensitive data detection
    sensitive_patterns_detected = Column(JSON)  # List of detected patterns
    confidence_scores = Column(JSON)  # Pattern confidence scores
    
    # Response data
    response_output = Column(Text)
    response_time_ms = Column(Integer)
    tokens_used = Column(Integer)
    
    # Admin actions
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text)
    rejection_reason = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    admin_actions = relationship("PromptAdminAction", back_populates="prompt_log")


class PromptAdminAction(Base):
    """Track admin actions on prompts"""
    __tablename__ = "prompt_admin_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_log_id = Column(Integer, ForeignKey("prompt_logs.id"), nullable=False)
    admin_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    action = Column(String(50), nullable=False)  # approve, reject, edit, flag
    action_details = Column(JSON)
    
    # For edits
    original_content = Column(Text)
    modified_content = Column(Text)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    prompt_log = relationship("PromptLog", back_populates="admin_actions")
    admin = relationship("User")


class PromptReviewQueue(Base):
    """Queue for prompts requiring review"""
    __tablename__ = "prompt_review_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt_log_id = Column(Integer, ForeignKey("prompt_logs.id"), unique=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    reason = Column(Text)  # Why review is required
    
    # Assignment
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)
    
    # Queue management
    added_at = Column(DateTime, default=datetime.utcnow, index=True)
    due_by = Column(DateTime)
    
    # Relationships
    prompt_log = relationship("PromptLog")
    organization = relationship("Organization")
    assignee = relationship("User")


# Vector Search Models for Semantic Search & RAG
class EmbeddingModel(Base):
    """Stores information about embedding models used"""
    __tablename__ = "embedding_models"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)  # e.g., 'legal-bert-base', 'all-MiniLM-L6-v2'
    dimension = Column(Integer, nullable=False)  # e.g., 768, 384
    provider = Column(String, nullable=False)  # 'local', 'openai', 'cohere'
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Model configuration
    model_config = Column(JSON)  # Additional model-specific settings
    
    # Performance metrics
    avg_encoding_time_ms = Column(Float)
    total_documents_encoded = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<EmbeddingModel(name={self.name}, dimension={self.dimension})>"


class DocumentChunk(Base):
    """Stores document chunks for RAG"""
    __tablename__ = "document_chunks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order within document
    
    # Content
    content = Column(Text, nullable=False)  # Actual text content
    tokens = Column(Integer)  # Token count
    start_char = Column(Integer)  # Character position in original document
    end_char = Column(Integer)
    
    # Metadata for legal documents
    chunk_metadata = Column(JSON)  # {"section": "3.2", "type": "clause", "headers": [...]}
    
    # Processing status
    created_at = Column(DateTime, default=datetime.utcnow)
    embedding_generated = Column(Boolean, default=False)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    embeddings = relationship("ChunkEmbedding", back_populates="chunk", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DocumentChunk(doc_id={self.document_id}, index={self.chunk_index})>"


class ChunkEmbedding(Base):
    """Stores vector embeddings for chunks"""
    __tablename__ = "chunk_embeddings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chunk_id = Column(String, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(String, ForeignKey("embedding_models.id"), nullable=False)
    
    # Vector storage - using Text for SQLite compatibility (store as JSON)
    embedding = Column(Text, nullable=False)  # JSON array of floats
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    encoding_time_ms = Column(Float)  # Time taken to generate embedding
    
    # Relationships
    chunk = relationship("DocumentChunk", back_populates="embeddings")
    model = relationship("EmbeddingModel")
    
    def __repr__(self):
        return f"<ChunkEmbedding(chunk_id={self.chunk_id}, model={self.model_id})>"


class SearchCache(Base):
    """Caches search results for performance"""
    __tablename__ = "search_cache"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    query_hash = Column(String, nullable=False, unique=True, index=True)
    query_text = Column(Text, nullable=False)
    query_embedding = Column(Text)  # Cached query embedding (JSON)
    
    # Results
    result_chunk_ids = Column(Text)  # Ordered list of chunk IDs (JSON)
    result_scores = Column(Text)  # Similarity scores (JSON)
    
    # Scope
    organization_id = Column(String, ForeignKey("organizations.id"))
    user_id = Column(String, ForeignKey("users.id"))
    
    # Cache management
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    hit_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization")
    user = relationship("User")
    
    def __repr__(self):
        return f"<SearchCache(query_hash={self.query_hash[:8]}..., hits={self.hit_count})>"


# Add relationships to existing Document model
Document.chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
Document.chunks_generated = Column(Boolean, default=False)
Document.embeddings_generated = Column(Boolean, default=False)
Document.embedding_model_id = Column(String, ForeignKey("embedding_models.id"))
Document.chunk_count = Column(Integer, default=0)
Document.last_embedded_at = Column(DateTime)