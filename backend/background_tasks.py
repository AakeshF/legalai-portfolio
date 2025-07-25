# background_tasks.py - Simple background task system for document enhancement

import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading
import queue

from database import SessionLocal
from models import Document
from services.enhanced_document_processor import EnhancedDocumentProcessor
from services.mcp_manager import MCPManager

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """Simple background task manager for document processing"""

    def __init__(self):
        self.task_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.running = False
        self.worker_thread = None

    def start(self):
        """Start the background task processor"""
        if not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            logger.info("Background task manager started")

    def stop(self):
        """Stop the background task processor"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        self.executor.shutdown(wait=True)
        logger.info("Background task manager stopped")

    def add_task(self, task_type: str, data: Dict[str, Any]):
        """Add a task to the queue"""
        task = {
            "id": f"{task_type}_{datetime.utcnow().timestamp()}",
            "type": task_type,
            "data": data,
            "created_at": datetime.utcnow(),
        }
        self.task_queue.put(task)
        logger.info(f"Added task {task['id']} to queue")

    def _worker(self):
        """Worker thread that processes tasks"""
        while self.running:
            try:
                # Get task from queue with timeout
                task = self.task_queue.get(timeout=1)

                # Process task
                logger.info(f"Processing task {task['id']}")

                if task["type"] == "enhance_documents":
                    self._process_enhance_documents(task["data"])
                elif task["type"] == "bulk_classify":
                    self._process_bulk_classify(task["data"])
                else:
                    logger.warning(f"Unknown task type: {task['type']}")

                self.task_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing task: {str(e)}")

    def _process_enhance_documents(self, data: Dict[str, Any]):
        """Process document enhancement task"""
        document_ids = data.get("document_ids", [])
        organization_id = data.get("organization_id")

        if not document_ids or not organization_id:
            logger.error("Invalid enhance_documents task data")
            return

        # Run async enhancement in executor
        future = self.executor.submit(
            self._run_async_enhancement, document_ids, organization_id
        )

        try:
            result = future.result(timeout=300)  # 5 minute timeout
            logger.info(f"Enhancement task completed: {result}")
        except Exception as e:
            logger.error(f"Enhancement task failed: {str(e)}")

    def _run_async_enhancement(self, document_ids: List[str], organization_id: str):
        """Run async enhancement in a new event loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(
                self._enhance_documents_async(document_ids, organization_id)
            )
        finally:
            loop.close()

    async def _enhance_documents_async(
        self, document_ids: List[str], organization_id: str
    ):
        """Async function to enhance documents"""
        mcp_manager = MCPManager()
        processor = EnhancedDocumentProcessor(mcp_manager)

        db = SessionLocal()
        success_count = 0
        error_count = 0

        try:
            for doc_id in document_ids:
                try:
                    document = (
                        db.query(Document)
                        .filter(
                            Document.id == doc_id,
                            Document.organization_id == organization_id,
                        )
                        .first()
                    )

                    if document and document.processing_status == "completed":
                        await processor.process_document_with_mcp(
                            document, organization_id
                        )
                        success_count += 1
                        logger.info(f"Enhanced document {doc_id}")
                    else:
                        logger.warning(f"Document {doc_id} not found or not ready")

                except Exception as e:
                    error_count += 1
                    logger.error(f"Failed to enhance document {doc_id}: {str(e)}")

            return {
                "success": success_count,
                "errors": error_count,
                "total": len(document_ids),
            }

        finally:
            db.close()

    def _process_bulk_classify(self, data: Dict[str, Any]):
        """Process bulk classification task"""
        # Similar implementation for bulk classification
        logger.info("Processing bulk classification task")
        # Implementation would go here


# Global task manager instance
task_manager = BackgroundTaskManager()


# Convenience functions
def queue_document_enhancement(document_ids: List[str], organization_id: str):
    """Queue documents for enhancement"""
    task_manager.add_task(
        "enhance_documents",
        {"document_ids": document_ids, "organization_id": organization_id},
    )


def queue_bulk_classification(document_ids: List[str], organization_id: str):
    """Queue documents for classification"""
    task_manager.add_task(
        "bulk_classify",
        {"document_ids": document_ids, "organization_id": organization_id},
    )


# Start task manager when module is imported
task_manager.start()
