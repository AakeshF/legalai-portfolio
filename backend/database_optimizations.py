"""
Database optimizations: indexes and connection pooling
"""

from sqlalchemy import create_engine, event, Index, text
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker
import logging

from database import Base
from models import Document, ChatSession, ChatMessage, User, Organization
from config import settings

logger = logging.getLogger(__name__)


def create_optimized_engine(database_url: str = None):
    """Create database engine with connection pooling."""
    url = database_url or settings.database_url

    # Connection pool settings
    pool_config = {
        "poolclass": QueuePool,
        "pool_size": 20,  # Number of connections to maintain
        "max_overflow": 10,  # Maximum overflow connections
        "pool_timeout": 30,  # Timeout for getting connection from pool
        "pool_recycle": 3600,  # Recycle connections after 1 hour
        "pool_pre_ping": True,  # Test connections before using
    }

    # For SQLite, use different settings
    if url.startswith("sqlite"):
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
            echo=False,
        )
    else:
        # PostgreSQL or other databases
        engine = create_engine(url, **pool_config, echo=False)

    # Add connection event listeners
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for better performance."""
        if url.startswith("sqlite"):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            cursor.execute("PRAGMA synchronous=NORMAL")  # Faster writes
            cursor.execute("PRAGMA cache_size=10000")  # Larger cache
            cursor.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
            cursor.close()

    return engine


def create_indexes(engine):
    """Create database indexes for common queries."""

    # Define indexes
    indexes = [
        # Document indexes
        Index("idx_document_org_status", Document.organization_id, Document.status),
        Index(
            "idx_document_org_type", Document.organization_id, Document.document_type
        ),
        Index(
            "idx_document_org_uploaded",
            Document.organization_id,
            Document.uploaded_at.desc(),
        ),
        Index("idx_document_filename", Document.filename),
        Index("idx_document_uploaded_by", Document.uploaded_by_id),
        # ChatSession indexes
        Index("idx_chat_session_user", ChatSession.user_id),
        Index("idx_chat_session_org", ChatSession.organization_id),
        Index("idx_chat_session_created", ChatSession.created_at.desc()),
        # ChatMessage indexes
        Index("idx_chat_message_session", ChatMessage.session_id),
        Index("idx_chat_message_timestamp", ChatMessage.timestamp.desc()),
        # User indexes
        Index("idx_user_email", User.email, unique=True),
        Index("idx_user_org", User.organization_id),
        Index("idx_user_active", User.is_active),
        # Organization indexes
        Index("idx_org_active", Organization.is_active),
        Index("idx_org_billing_email", Organization.billing_email),
    ]

    # Create indexes
    with engine.connect() as conn:
        for index in indexes:
            try:
                index.create(conn, checkfirst=True)
                logger.info(f"Created index: {index.name}")
            except Exception as e:
                logger.error(f"Failed to create index {index.name}: {e}")

    # Create full-text search indexes for PostgreSQL
    if not engine.url.database.endswith(".db"):  # Not SQLite
        try:
            with engine.connect() as conn:
                # Full-text search on document content
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_document_content_fts 
                    ON documents USING gin(to_tsvector('english', content_extracted))
                """
                    )
                )

                # Full-text search on chat messages
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_chat_message_content_fts 
                    ON chat_messages USING gin(to_tsvector('english', content))
                """
                    )
                )

                conn.commit()
                logger.info("Created PostgreSQL full-text search indexes")
        except Exception as e:
            logger.warning(f"Could not create full-text indexes: {e}")


def optimize_queries():
    """Return common query optimizations."""

    return {
        "document_list": """
            SELECT d.id, d.filename, d.file_type, d.file_size, 
                   d.document_type, d.status, d.uploaded_at, d.updated_at
            FROM documents d
            WHERE d.organization_id = :org_id
            ORDER BY d.uploaded_at DESC
            LIMIT :limit OFFSET :offset
        """,
        "document_search": """
            SELECT d.* FROM documents d
            WHERE d.organization_id = :org_id
            AND (
                d.filename LIKE :search_term
                OR d.content_extracted LIKE :search_term
                OR d.document_type = :doc_type
            )
            ORDER BY d.uploaded_at DESC
        """,
        "recent_chat_sessions": """
            SELECT cs.*, COUNT(cm.id) as message_count
            FROM chat_sessions cs
            LEFT JOIN chat_messages cm ON cs.id = cm.session_id
            WHERE cs.user_id = :user_id
            GROUP BY cs.id
            ORDER BY cs.updated_at DESC
            LIMIT :limit
        """,
        "organization_stats": """
            SELECT 
                COUNT(DISTINCT d.id) as total_documents,
                COUNT(DISTINCT cs.id) as total_sessions,
                COUNT(DISTINCT u.id) as total_users,
                SUM(d.file_size) as total_storage_bytes
            FROM organizations o
            LEFT JOIN documents d ON o.id = d.organization_id
            LEFT JOIN chat_sessions cs ON o.id = cs.organization_id
            LEFT JOIN users u ON o.id = u.organization_id
            WHERE o.id = :org_id
            GROUP BY o.id
        """,
    }


class OptimizedSession:
    """Session manager with query optimizations."""

    def __init__(self, engine):
        self.engine = engine
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            expire_on_commit=False,  # Don't expire objects after commit
        )

    def get_db(self):
        """Get database session with optimizations."""
        db = self.SessionLocal()

        # Set session-level optimizations
        if self.engine.url.database.endswith(".db"):  # SQLite
            db.execute(text("PRAGMA read_uncommitted = true"))

        try:
            yield db
        finally:
            db.close()

    def bulk_insert(self, objects):
        """Optimized bulk insert."""
        db = self.SessionLocal()
        try:
            db.bulk_insert_mappings(type(objects[0]), objects)
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    def bulk_update(self, model, mappings):
        """Optimized bulk update."""
        db = self.SessionLocal()
        try:
            db.bulk_update_mappings(model, mappings)
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()


# Initialize optimizations
def init_database_optimizations():
    """Initialize all database optimizations."""
    logger.info("Initializing database optimizations...")

    # Create optimized engine
    engine = create_optimized_engine()

    # Create tables if needed
    Base.metadata.create_all(bind=engine)

    # Create indexes
    create_indexes(engine)

    logger.info("Database optimizations complete")

    return engine


if __name__ == "__main__":
    # Run optimizations
    init_database_optimizations()
