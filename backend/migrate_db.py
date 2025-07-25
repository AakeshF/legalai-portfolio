# migrate_db_complete.py - Complete database migration fixing all schema issues
import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Import from your actual file structure
from models import Base, Document, ChatSession, ChatMessage
from database import engine


def migrate_database():
    """Update database schema with new fields and fix existing issues"""

    print("🔄 Starting COMPLETE database migration...")

    try:
        # Create connection
        with engine.connect() as conn:

            # 1. FIX DOCUMENTS TABLE
            print("📊 Checking documents table structure...")

            result = conn.execute(text("PRAGMA table_info(documents)"))
            existing_doc_columns = {row[1] for row in result.fetchall()}

            print(f"📊 Existing document columns: {existing_doc_columns}")

            # Add missing columns to documents table
            doc_columns = [
                ("content_type", "VARCHAR"),
                ("extracted_content", "TEXT"),
                ("page_count", "INTEGER"),
                ("error_message", "VARCHAR"),
                ("processed_timestamp", "DATETIME"),
            ]

            for column_name, column_type in doc_columns:
                if column_name not in existing_doc_columns:
                    print(f"➕ Adding documents column: {column_name}")
                    try:
                        conn.execute(
                            text(
                                f"ALTER TABLE documents ADD COLUMN {column_name} {column_type}"
                            )
                        )
                        conn.commit()
                        print(f"✅ Added documents column: {column_name}")
                    except Exception as e:
                        print(
                            f"⚠️ Documents column {column_name} might already exist: {e}"
                        )
                else:
                    print(f"✅ Documents column {column_name} already exists")

            # 2. FIX CHAT_SESSIONS TABLE
            print("\n📊 Checking chat_sessions table structure...")

            try:
                result = conn.execute(text("PRAGMA table_info(chat_sessions)"))
                existing_session_columns = {row[1] for row in result.fetchall()}
                print(f"📊 Existing chat_sessions columns: {existing_session_columns}")

                # Check if we need to add missing columns
                session_columns = [
                    ("session_name", "VARCHAR"),
                    ("created_timestamp", "DATETIME"),
                    ("last_activity", "DATETIME"),
                ]

                for column_name, column_type in session_columns:
                    if column_name not in existing_session_columns:
                        print(f"➕ Adding chat_sessions column: {column_name}")
                        try:
                            conn.execute(
                                text(
                                    f"ALTER TABLE chat_sessions ADD COLUMN {column_name} {column_type}"
                                )
                            )
                            conn.commit()
                            print(f"✅ Added chat_sessions column: {column_name}")
                        except Exception as e:
                            print(
                                f"⚠️ Chat_sessions column {column_name} might already exist: {e}"
                            )
                    else:
                        print(f"✅ Chat_sessions column {column_name} already exists")

                # If we have created_at but not created_timestamp, copy the data
                if (
                    "created_at" in existing_session_columns
                    and "created_timestamp" not in existing_session_columns
                ):
                    print("🔄 Copying created_at to created_timestamp...")
                    try:
                        conn.execute(
                            text(
                                "UPDATE chat_sessions SET created_timestamp = created_at WHERE created_timestamp IS NULL"
                            )
                        )
                        conn.commit()
                        print("✅ Copied created_at to created_timestamp")
                    except Exception as e:
                        print(f"⚠️ Error copying created_at: {e}")

            except Exception as e:
                print(f"⚠️ Chat_sessions table might not exist yet: {e}")

            # 3. FIX CHAT_MESSAGES TABLE
            print("\n📊 Checking chat_messages table structure...")

            try:
                result = conn.execute(text("PRAGMA table_info(chat_messages)"))
                existing_message_columns = {row[1] for row in result.fetchall()}
                print(f"📊 Existing chat_messages columns: {existing_message_columns}")

                # Add missing columns to chat_messages table
                message_columns = [
                    ("model_used", "VARCHAR"),
                    ("processing_time", "INTEGER"),
                ]

                for column_name, column_type in message_columns:
                    if column_name not in existing_message_columns:
                        print(f"➕ Adding chat_messages column: {column_name}")
                        try:
                            conn.execute(
                                text(
                                    f"ALTER TABLE chat_messages ADD COLUMN {column_name} {column_type}"
                                )
                            )
                            conn.commit()
                            print(f"✅ Added chat_messages column: {column_name}")
                        except Exception as e:
                            print(
                                f"⚠️ Chat_messages column {column_name} might already exist: {e}"
                            )
                    else:
                        print(f"✅ Chat_messages column {column_name} already exists")

            except Exception as e:
                print(f"⚠️ Chat_messages table might not exist yet: {e}")

        # 4. CREATE ALL TABLES (this will create missing tables without affecting existing ones)
        print("\n📊 Creating/updating all tables...")
        Base.metadata.create_all(bind=engine)

        print("\n✅ COMPLETE database migration finished successfully!")
        print("🎯 All tables updated and ready for document processing and chat!")

        # 5. VERIFY THE FINAL SCHEMA
        print("\n🔍 Final schema verification:")
        with engine.connect() as conn:
            for table_name in ["documents", "chat_sessions", "chat_messages"]:
                try:
                    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                    columns = [row[1] for row in result.fetchall()]
                    print(f"✅ {table_name}: {columns}")
                except Exception as e:
                    print(f"⚠️ Could not verify {table_name}: {e}")

    except Exception as e:
        print(f"❌ Migration error: {str(e)}")
        raise


if __name__ == "__main__":
    migrate_database()
