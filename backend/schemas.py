# schemas.py - Pydantic schemas for request/response models
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, date
from enum import Enum

# Enums for filtering and sorting
class DocumentType(str, Enum):
    CONTRACT = "contract"
    IMMIGRATION = "immigration"
    FAMILY_LAW = "family_law"
    BRIEF = "brief"
    COURT_FILING = "court_filing"
    PATENT = "patent"
    CORRESPONDENCE = "correspondence"
    OTHER = "other"

class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EXTRACTED = "extracted"
    COMPLETED = "completed"
    ERROR = "error"

class SortField(str, Enum):
    UPLOAD_DATE = "upload_date"
    RISK_SCORE = "risk_score"
    FILE_SIZE = "file_size"
    FILENAME = "filename"
    STATUS = "status"

class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"

# Search and filter parameters
class DocumentSearchParams(BaseModel):
    # Search parameters
    search: Optional[str] = Field(None, description="Full-text search query")
    
    # Filtering parameters
    document_type: Optional[DocumentType] = Field(None, description="Filter by document type")
    status: Optional[DocumentStatus] = Field(None, description="Filter by processing status")
    date_from: Optional[datetime] = Field(None, description="Filter documents uploaded after this date")
    date_to: Optional[datetime] = Field(None, description="Filter documents uploaded before this date")
    min_risk_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum risk score")
    max_risk_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Maximum risk score")
    min_file_size: Optional[int] = Field(None, ge=0, description="Minimum file size in bytes")
    max_file_size: Optional[int] = Field(None, ge=0, description="Maximum file size in bytes")
    
    # Sorting parameters
    sort_by: Optional[SortField] = Field(SortField.UPLOAD_DATE, description="Field to sort by")
    sort_order: Optional[SortOrder] = Field(SortOrder.DESC, description="Sort order")
    
    # Pagination parameters
    limit: int = Field(20, ge=1, le=100, description="Number of results per page")
    offset: int = Field(0, ge=0, description="Number of results to skip")

# Document schemas
class DocumentUpload(BaseModel):
    filename: str
    content_type: Optional[str] = None

class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: str
    upload_timestamp: datetime
    file_size: int
    page_count: Optional[int] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # Extracted legal metadata
    
    class Config:
        from_attributes = True

# Communication Management schemas
class CommunicationLogRequest(BaseModel):
    matter_id: str
    client_id: Optional[str] = None
    communication_type: Literal["email", "phone", "sms", "meeting", "letter", "fax", "portal_message"]
    direction: Literal["inbound", "outbound"]
    date: Optional[datetime] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    participants: List[Dict[str, Any]]
    attachments: Optional[List[Dict[str, Any]]] = []
    tags: Optional[List[str]] = []
    follow_up_required: bool = False
    privilege_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class CommunicationLogResponse(BaseModel):
    communication_id: str
    success: bool
    privileged: bool
    follow_ups_created: int

class CommunicationSearchRequest(BaseModel):
    search_query: Optional[str] = None
    matter_id: Optional[str] = None
    client_id: Optional[str] = None
    communication_type: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    privileged_only: bool = False
    offset: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)

class CommunicationSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int

class PrivilegeLogRequest(BaseModel):
    matter_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PrivilegeLogResponse(BaseModel):
    matter_id: str
    generated_date: str
    date_range: Dict[str, str]
    total_entries: int
    privileged_count: int
    entries: List[Dict[str, Any]]

class FollowUpRequest(BaseModel):
    communication_id: str
    due_date: datetime
    description: str
    priority: Optional[Literal["low", "medium", "high", "critical"]] = "medium"
    assigned_to_id: Optional[str] = None
    auto_escalate: bool = True

class FollowUpResponse(BaseModel):
    follow_up_id: str
    success: bool
    due_date: str

class BulkImportRequest(BaseModel):
    source: Literal["email", "phone", "calendar"]
    config: Dict[str, Any]
    matter_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None

class BulkImportResponse(BaseModel):
    success: bool
    message: str
    job_id: str

class CommunicationStatsResponse(BaseModel):
    total_communications: int
    privileged_count: int
    email_count: Optional[int] = 0
    phone_count: Optional[int] = 0
    meeting_count: Optional[int] = 0
    inbound_count: Optional[int] = 0
    outbound_count: Optional[int] = 0

class CommunicationTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    communication_type: Literal["email", "letter", "sms"]
    subject_template: Optional[str] = None
    content_template: str
    available_variables: Optional[List[str]] = []
    tags: Optional[List[str]] = []

class CommunicationTemplateResponse(BaseModel):
    id: str
    name: str
    communication_type: str
    created_at: str

# Chat schemas
class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    document_ids: Optional[List[str]] = None
    history: Optional[List[ChatMessage]] = None

class PerformanceMetrics(BaseModel):
    total_response_time_ms: int
    metadata_lookup_time_ms: Optional[int] = None
    ai_processing_time_ms: Optional[int] = None
    tokens_used: Optional[int] = None
    tokens_saved_via_cache: Optional[int] = None
    cache_hit: bool = False
    response_source: Literal["metadata_cache", "ai_analysis", "hybrid"]
    cost_savings_estimate: Optional[str] = None
    query_classification: Literal["metadata_query", "analysis_request", "conversational"]
    
class IntelligenceFlags(BaseModel):
    instant_response: bool = False
    context_utilized: List[str] = []
    optimization_applied: Optional[str] = None
    confidence_score: Optional[float] = None

class ChatResponse(BaseModel):
    session_id: str
    message: str
    sources: List[str] = []
    timestamp: datetime
    performance_metrics: PerformanceMetrics
    intelligence_flags: IntelligenceFlags
    
    # Legacy fields for backward compatibility
    response_metrics: Optional[Dict[str, Any]] = None
    response_type: Optional[str] = None
    tokens_used: Optional[int] = None
    response_time_ms: Optional[int] = None
    cost_saved: Optional[float] = None

# MCP schemas
class MCPServerConfig(BaseModel):
    server_name: str
    connection_type: str
    config: Dict[str, Any]

class MCPServerStatus(BaseModel):
    server_name: str
    status: str
    last_sync: Optional[datetime] = None

# Analysis schemas
class DocumentAnalysis(BaseModel):
    document_id: str
    analysis_type: str  # summary, key_points, legal_issues, etc.
    result: Dict[str, Any]
    generated_at: datetime

# System schemas
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    services: Dict[str, str] = {}

class APIError(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime

# Pagination response metadata
class PaginationMetadata(BaseModel):
    total_items: int
    page_size: int
    current_page: int
    total_pages: int
    has_next: bool
    has_previous: bool

# Enhanced document list response with pagination
class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    pagination: PaginationMetadata
    filters_applied: Dict[str, Any] = {}
    search_query: Optional[str] = None

# Authentication schemas
class UserCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role: Optional[str] = "attorney"  # attorney, admin, paralegal

class OrganizationCreate(BaseModel):
    name: str
    billing_email: str
    subscription_tier: Optional[str] = "basic"  # basic, pro, enterprise

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None
    organization_id: Optional[str] = None
    role: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    full_name: Optional[str] = None
    role: str
    organization_id: str
    created_at: datetime
    is_active: bool
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Communication Management schemas
class CommunicationLogRequest(BaseModel):
    matter_id: str
    client_id: Optional[str] = None
    communication_type: Literal["email", "phone", "sms", "meeting", "letter", "fax", "portal_message"]
    direction: Literal["inbound", "outbound"]
    date: Optional[datetime] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    participants: List[Dict[str, Any]]
    attachments: Optional[List[Dict[str, Any]]] = []
    tags: Optional[List[str]] = []
    follow_up_required: bool = False
    privilege_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class CommunicationLogResponse(BaseModel):
    communication_id: str
    success: bool
    privileged: bool
    follow_ups_created: int

class CommunicationSearchRequest(BaseModel):
    search_query: Optional[str] = None
    matter_id: Optional[str] = None
    client_id: Optional[str] = None
    communication_type: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    privileged_only: bool = False
    offset: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)

class CommunicationSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int

class PrivilegeLogRequest(BaseModel):
    matter_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PrivilegeLogResponse(BaseModel):
    matter_id: str
    generated_date: str
    date_range: Dict[str, str]
    total_entries: int
    privileged_count: int
    entries: List[Dict[str, Any]]

class FollowUpRequest(BaseModel):
    communication_id: str
    due_date: datetime
    description: str
    priority: Optional[Literal["low", "medium", "high", "critical"]] = "medium"
    assigned_to_id: Optional[str] = None
    auto_escalate: bool = True

class FollowUpResponse(BaseModel):
    follow_up_id: str
    success: bool
    due_date: str

class BulkImportRequest(BaseModel):
    source: Literal["email", "phone", "calendar"]
    config: Dict[str, Any]
    matter_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None

class BulkImportResponse(BaseModel):
    success: bool
    message: str
    job_id: str

class CommunicationStatsResponse(BaseModel):
    total_communications: int
    privileged_count: int
    email_count: Optional[int] = 0
    phone_count: Optional[int] = 0
    meeting_count: Optional[int] = 0
    inbound_count: Optional[int] = 0
    outbound_count: Optional[int] = 0

class CommunicationTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    communication_type: Literal["email", "letter", "sms"]
    subject_template: Optional[str] = None
    content_template: str
    available_variables: Optional[List[str]] = []
    tags: Optional[List[str]] = []

class CommunicationTemplateResponse(BaseModel):
    id: str
    name: str
    communication_type: str
    created_at: str

class OrganizationResponse(BaseModel):
    id: str
    name: str
    subscription_tier: str
    billing_email: str
    created_at: datetime
    is_active: bool
    user_count: Optional[int] = 0
    document_count: Optional[int] = 0
    storage_used_mb: Optional[float] = 0.0
    
    class Config:
        from_attributes = True

# Communication Management schemas
class CommunicationLogRequest(BaseModel):
    matter_id: str
    client_id: Optional[str] = None
    communication_type: Literal["email", "phone", "sms", "meeting", "letter", "fax", "portal_message"]
    direction: Literal["inbound", "outbound"]
    date: Optional[datetime] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    participants: List[Dict[str, Any]]
    attachments: Optional[List[Dict[str, Any]]] = []
    tags: Optional[List[str]] = []
    follow_up_required: bool = False
    privilege_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class CommunicationLogResponse(BaseModel):
    communication_id: str
    success: bool
    privileged: bool
    follow_ups_created: int

class CommunicationSearchRequest(BaseModel):
    search_query: Optional[str] = None
    matter_id: Optional[str] = None
    client_id: Optional[str] = None
    communication_type: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    privileged_only: bool = False
    offset: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)

class CommunicationSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int

class PrivilegeLogRequest(BaseModel):
    matter_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PrivilegeLogResponse(BaseModel):
    matter_id: str
    generated_date: str
    date_range: Dict[str, str]
    total_entries: int
    privileged_count: int
    entries: List[Dict[str, Any]]

class FollowUpRequest(BaseModel):
    communication_id: str
    due_date: datetime
    description: str
    priority: Optional[Literal["low", "medium", "high", "critical"]] = "medium"
    assigned_to_id: Optional[str] = None
    auto_escalate: bool = True

class FollowUpResponse(BaseModel):
    follow_up_id: str
    success: bool
    due_date: str

class BulkImportRequest(BaseModel):
    source: Literal["email", "phone", "calendar"]
    config: Dict[str, Any]
    matter_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None

class BulkImportResponse(BaseModel):
    success: bool
    message: str
    job_id: str

class CommunicationStatsResponse(BaseModel):
    total_communications: int
    privileged_count: int
    email_count: Optional[int] = 0
    phone_count: Optional[int] = 0
    meeting_count: Optional[int] = 0
    inbound_count: Optional[int] = 0
    outbound_count: Optional[int] = 0

class CommunicationTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    communication_type: Literal["email", "letter", "sms"]
    subject_template: Optional[str] = None
    content_template: str
    available_variables: Optional[List[str]] = []
    tags: Optional[List[str]] = []

class CommunicationTemplateResponse(BaseModel):
    id: str
    name: str
    communication_type: str
    created_at: str

class RegisterRequest(BaseModel):
    # Organization info
    organization_name: str
    billing_email: str
    
    # Admin user info
    admin_email: str
    admin_password: str
    admin_first_name: str
    admin_last_name: str

class RegisterResponse(BaseModel):
    organization: OrganizationResponse
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

# Organization management schemas
class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    billing_email: Optional[str] = None
    subscription_tier: Optional[str] = None

class UserInvite(BaseModel):
    email: str
    first_name: str
    last_name: str
    role: Literal["attorney", "admin", "paralegal"] = "attorney"
    frontend_url: Optional[str] = None  # For customizing invitation email link

class OrganizationUsersResponse(BaseModel):
    users: List[UserResponse]
    total_count: int
    active_count: int
    admin_count: int
    attorney_count: int
    paralegal_count: int

# Matter management schemas
class MatterCreateRequest(BaseModel):
    client_id: str
    client_name: str  # For conflict checking
    matter_name: str
    matter_type: Literal["personal_injury", "criminal", "immigration", "family", "corporate", "real_estate", "other"]
    status: Optional[Literal["prospective", "active", "closed", "on_hold", "archived"]] = "active"
    opposing_parties: Optional[List[Dict[str, Any]]] = []
    jurisdiction: Optional[Dict[str, str]] = None  # {"state": "KY/OH", "county": "..."}
    case_number: Optional[str] = None
    judge_assigned: Optional[str] = None
    description: Optional[str] = None
    billing_type: Optional[Literal["hourly", "flat_fee", "contingency"]] = "hourly"
    estimated_value: Optional[int] = None  # In cents

class MatterUpdateRequest(BaseModel):
    matter_name: Optional[str] = None
    status: Optional[Literal["prospective", "active", "closed", "on_hold", "archived"]] = None
    opposing_parties: Optional[List[Dict[str, Any]]] = None
    jurisdiction: Optional[Dict[str, str]] = None
    case_number: Optional[str] = None
    judge_assigned: Optional[str] = None
    description: Optional[str] = None
    billing_type: Optional[Literal["hourly", "flat_fee", "contingency"]] = None
    estimated_value: Optional[int] = None

class MatterResponse(BaseModel):
    id: str
    organization_id: str
    client_id: str
    matter_name: str
    matter_type: str
    status: str
    date_opened: datetime
    date_closed: Optional[datetime] = None
    opposing_parties: List[Dict[str, Any]]
    jurisdiction: Optional[Dict[str, str]] = None
    case_number: Optional[str] = None
    judge_assigned: Optional[str] = None
    description: Optional[str] = None
    billing_type: str
    estimated_value: Optional[int] = None
    mcp_metadata: Dict[str, Any] = {}
    
    # Related counts
    document_count: Optional[int] = 0
    deadline_count: Optional[int] = 0
    communication_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

# Communication Management schemas
class CommunicationLogRequest(BaseModel):
    matter_id: str
    client_id: Optional[str] = None
    communication_type: Literal["email", "phone", "sms", "meeting", "letter", "fax", "portal_message"]
    direction: Literal["inbound", "outbound"]
    date: Optional[datetime] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    participants: List[Dict[str, Any]]
    attachments: Optional[List[Dict[str, Any]]] = []
    tags: Optional[List[str]] = []
    follow_up_required: bool = False
    privilege_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class CommunicationLogResponse(BaseModel):
    communication_id: str
    success: bool
    privileged: bool
    follow_ups_created: int

class CommunicationSearchRequest(BaseModel):
    search_query: Optional[str] = None
    matter_id: Optional[str] = None
    client_id: Optional[str] = None
    communication_type: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    privileged_only: bool = False
    offset: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)

class CommunicationSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int

class PrivilegeLogRequest(BaseModel):
    matter_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PrivilegeLogResponse(BaseModel):
    matter_id: str
    generated_date: str
    date_range: Dict[str, str]
    total_entries: int
    privileged_count: int
    entries: List[Dict[str, Any]]

class FollowUpRequest(BaseModel):
    communication_id: str
    due_date: datetime
    description: str
    priority: Optional[Literal["low", "medium", "high", "critical"]] = "medium"
    assigned_to_id: Optional[str] = None
    auto_escalate: bool = True

class FollowUpResponse(BaseModel):
    follow_up_id: str
    success: bool
    due_date: str

class BulkImportRequest(BaseModel):
    source: Literal["email", "phone", "calendar"]
    config: Dict[str, Any]
    matter_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None

class BulkImportResponse(BaseModel):
    success: bool
    message: str
    job_id: str

class CommunicationStatsResponse(BaseModel):
    total_communications: int
    privileged_count: int
    email_count: Optional[int] = 0
    phone_count: Optional[int] = 0
    meeting_count: Optional[int] = 0
    inbound_count: Optional[int] = 0
    outbound_count: Optional[int] = 0

class CommunicationTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    communication_type: Literal["email", "letter", "sms"]
    subject_template: Optional[str] = None
    content_template: str
    available_variables: Optional[List[str]] = []
    tags: Optional[List[str]] = []

class CommunicationTemplateResponse(BaseModel):
    id: str
    name: str
    communication_type: str
    created_at: str

class MatterListResponse(BaseModel):
    matters: List[MatterResponse]
    total: int
    skip: int
    limit: int

class ConflictCheckRequest(BaseModel):
    client_name: str
    opposing_parties: List[Dict[str, Any]]

class ConflictCheckResponse(BaseModel):
    has_conflicts: bool
    conflicts: List[Dict[str, Any]] = []

class MCPContextResponse(BaseModel):
    matter: Dict[str, Any]
    mcp_data: Dict[str, Any]

class DeadlineResponse(BaseModel):
    id: str
    matter_id: str
    title: str
    description: Optional[str] = None
    due_date: datetime
    is_court_deadline: bool
    completed_at: Optional[datetime] = None
    created_at: datetime
    mcp_sync_source: Optional[str] = None
    mcp_sync_id: Optional[str] = None
    
    class Config:
        from_attributes = True

# Communication Management schemas
class CommunicationLogRequest(BaseModel):
    matter_id: str
    client_id: Optional[str] = None
    communication_type: Literal["email", "phone", "sms", "meeting", "letter", "fax", "portal_message"]
    direction: Literal["inbound", "outbound"]
    date: Optional[datetime] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    participants: List[Dict[str, Any]]
    attachments: Optional[List[Dict[str, Any]]] = []
    tags: Optional[List[str]] = []
    follow_up_required: bool = False
    privilege_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class CommunicationLogResponse(BaseModel):
    communication_id: str
    success: bool
    privileged: bool
    follow_ups_created: int

class CommunicationSearchRequest(BaseModel):
    search_query: Optional[str] = None
    matter_id: Optional[str] = None
    client_id: Optional[str] = None
    communication_type: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    privileged_only: bool = False
    offset: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)

class CommunicationSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int

class PrivilegeLogRequest(BaseModel):
    matter_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PrivilegeLogResponse(BaseModel):
    matter_id: str
    generated_date: str
    date_range: Dict[str, str]
    total_entries: int
    privileged_count: int
    entries: List[Dict[str, Any]]

class FollowUpRequest(BaseModel):
    communication_id: str
    due_date: datetime
    description: str
    priority: Optional[Literal["low", "medium", "high", "critical"]] = "medium"
    assigned_to_id: Optional[str] = None
    auto_escalate: bool = True

class FollowUpResponse(BaseModel):
    follow_up_id: str
    success: bool
    due_date: str

class BulkImportRequest(BaseModel):
    source: Literal["email", "phone", "calendar"]
    config: Dict[str, Any]
    matter_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None

class BulkImportResponse(BaseModel):
    success: bool
    message: str
    job_id: str

class CommunicationStatsResponse(BaseModel):
    total_communications: int
    privileged_count: int
    email_count: Optional[int] = 0
    phone_count: Optional[int] = 0
    meeting_count: Optional[int] = 0
    inbound_count: Optional[int] = 0
    outbound_count: Optional[int] = 0

class CommunicationTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    communication_type: Literal["email", "letter", "sms"]
    subject_template: Optional[str] = None
    content_template: str
    available_variables: Optional[List[str]] = []
    tags: Optional[List[str]] = []

class CommunicationTemplateResponse(BaseModel):
    id: str
    name: str
    communication_type: str
    created_at: str

class CommunicationResponse(BaseModel):
    id: str
    matter_id: str
    communication_type: str
    direction: str
    subject: Optional[str] = None
    content: Optional[str] = None
    participants: List[Dict[str, Any]]
    timestamp: datetime
    mcp_source: Optional[str] = None
    mcp_external_id: Optional[str] = None
    
    class Config:
        from_attributes = True

# Communication Management schemas
class CommunicationLogRequest(BaseModel):
    matter_id: str
    client_id: Optional[str] = None
    communication_type: Literal["email", "phone", "sms", "meeting", "letter", "fax", "portal_message"]
    direction: Literal["inbound", "outbound"]
    date: Optional[datetime] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    participants: List[Dict[str, Any]]
    attachments: Optional[List[Dict[str, Any]]] = []
    tags: Optional[List[str]] = []
    follow_up_required: bool = False
    privilege_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class CommunicationLogResponse(BaseModel):
    communication_id: str
    success: bool
    privileged: bool
    follow_ups_created: int

class CommunicationSearchRequest(BaseModel):
    search_query: Optional[str] = None
    matter_id: Optional[str] = None
    client_id: Optional[str] = None
    communication_type: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    privileged_only: bool = False
    offset: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)

class CommunicationSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int

class PrivilegeLogRequest(BaseModel):
    matter_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PrivilegeLogResponse(BaseModel):
    matter_id: str
    generated_date: str
    date_range: Dict[str, str]
    total_entries: int
    privileged_count: int
    entries: List[Dict[str, Any]]

class FollowUpRequest(BaseModel):
    communication_id: str
    due_date: datetime
    description: str
    priority: Optional[Literal["low", "medium", "high", "critical"]] = "medium"
    assigned_to_id: Optional[str] = None
    auto_escalate: bool = True

class FollowUpResponse(BaseModel):
    follow_up_id: str
    success: bool
    due_date: str

class BulkImportRequest(BaseModel):
    source: Literal["email", "phone", "calendar"]
    config: Dict[str, Any]
    matter_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None

class BulkImportResponse(BaseModel):
    success: bool
    message: str
    job_id: str

class CommunicationStatsResponse(BaseModel):
    total_communications: int
    privileged_count: int
    email_count: Optional[int] = 0
    phone_count: Optional[int] = 0
    meeting_count: Optional[int] = 0
    inbound_count: Optional[int] = 0
    outbound_count: Optional[int] = 0

class CommunicationTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    communication_type: Literal["email", "letter", "sms"]
    subject_template: Optional[str] = None
    content_template: str
    available_variables: Optional[List[str]] = []
    tags: Optional[List[str]] = []

class CommunicationTemplateResponse(BaseModel):
    id: str
    name: str
    communication_type: str
    created_at: str

# Document MCP Enhancement schemas
class DocumentMCPEnhanceRequest(BaseModel):
    document_id: str
    force_refresh: Optional[bool] = False

class DocumentMCPEnhanceResponse(BaseModel):
    document_id: str
    status: Literal["success", "already_enhanced", "error"]
    message: str
    enhancements: Optional[Dict[str, Any]] = None

class DocumentClassifyRequest(BaseModel):
    document_text: str
    metadata: Optional[Dict[str, Any]] = None

class DocumentClassifyResponse(BaseModel):
    document_type: str
    confidence: float
    scores: Dict[str, float]
    valid_types_used: List[str]

class DocumentSearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: Optional[int] = Field(20, ge=1, le=100)
    offset: Optional[int] = Field(0, ge=0)

class DocumentSearchResponse(BaseModel):
    query: str
    enhanced_terms: List[str]
    total_results: int
    documents: List[Dict[str, Any]]

class BulkEnhanceRequest(BaseModel):
    document_ids: Optional[List[str]] = []
    max_documents: Optional[int] = Field(50, ge=1, le=500)
    filter_criteria: Optional[Dict[str, Any]] = None

class BulkEnhanceResponse(BaseModel):
    total_documents: int
    queued: int
    message: str

class MCPDataResponse(BaseModel):
    document_id: str
    mcp_enhanced_at: Optional[str] = None
    mcp_data: Dict[str, Any]
    has_court_analysis: bool
    has_validated_citations: bool
    has_conflict_check: bool
    has_extracted_deadlines: bool

class EnhancedDocumentResponse(BaseModel):
    id: str
    filename: str
    upload_timestamp: datetime
    status: str
    summary: Optional[str] = None
    legal_metadata: Optional[Dict[str, Any]] = None
    mcp_enhancements: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

# Communication Management schemas
class CommunicationLogRequest(BaseModel):
    matter_id: str
    client_id: Optional[str] = None
    communication_type: Literal["email", "phone", "sms", "meeting", "letter", "fax", "portal_message"]
    direction: Literal["inbound", "outbound"]
    date: Optional[datetime] = None
    subject: Optional[str] = None
    content: Optional[str] = None
    participants: List[Dict[str, Any]]
    attachments: Optional[List[Dict[str, Any]]] = []
    tags: Optional[List[str]] = []
    follow_up_required: bool = False
    privilege_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class CommunicationLogResponse(BaseModel):
    communication_id: str
    success: bool
    privileged: bool
    follow_ups_created: int

class CommunicationSearchRequest(BaseModel):
    search_query: Optional[str] = None
    matter_id: Optional[str] = None
    client_id: Optional[str] = None
    communication_type: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    privileged_only: bool = False
    offset: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)

class CommunicationSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    offset: int
    limit: int

class PrivilegeLogRequest(BaseModel):
    matter_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class PrivilegeLogResponse(BaseModel):
    matter_id: str
    generated_date: str
    date_range: Dict[str, str]
    total_entries: int
    privileged_count: int
    entries: List[Dict[str, Any]]

class FollowUpRequest(BaseModel):
    communication_id: str
    due_date: datetime
    description: str
    priority: Optional[Literal["low", "medium", "high", "critical"]] = "medium"
    assigned_to_id: Optional[str] = None
    auto_escalate: bool = True

class FollowUpResponse(BaseModel):
    follow_up_id: str
    success: bool
    due_date: str

class BulkImportRequest(BaseModel):
    source: Literal["email", "phone", "calendar"]
    config: Dict[str, Any]
    matter_id: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None

class BulkImportResponse(BaseModel):
    success: bool
    message: str
    job_id: str

class CommunicationStatsResponse(BaseModel):
    total_communications: int
    privileged_count: int
    email_count: Optional[int] = 0
    phone_count: Optional[int] = 0
    meeting_count: Optional[int] = 0
    inbound_count: Optional[int] = 0
    outbound_count: Optional[int] = 0

class CommunicationTemplateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    communication_type: Literal["email", "letter", "sms"]
    subject_template: Optional[str] = None
    content_template: str
    available_variables: Optional[List[str]] = []
    tags: Optional[List[str]] = []

class CommunicationTemplateResponse(BaseModel):
    id: str
    name: str
    communication_type: str
    created_at: str