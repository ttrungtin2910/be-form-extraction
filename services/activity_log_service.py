"""
User Activity Logging Service
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from google.cloud import firestore
from models.activity_log import (
    ActivityLog,
    ActivityLogCreate,
    ActivityLogFilter,
    ActivityLogResponse,
)
from properties.config import Configuration
import logging

logger = logging.getLogger(__name__)


class ActivityLogService:
    """Service for managing user activity logs"""

    def __init__(self):
        """Initialize the activity log service"""
        self.db = firestore.Client()
        self.collection_name = "activity_logs"

    async def create_log(self, log_data: ActivityLogCreate) -> ActivityLog:
        """Create a new activity log entry"""
        try:
            # Generate unique ID
            log_id = str(uuid.uuid4())

            # Create log document
            log_doc = ActivityLog(
                id=log_id,
                user_id=log_data.user_id,
                username=log_data.username,
                activity_type=log_data.activity_type,
                description=log_data.description,
                endpoint=log_data.endpoint,
                method=log_data.method,
                status_code=log_data.status_code,
                ip_address=log_data.ip_address,
                user_agent=log_data.user_agent,
                metadata=log_data.metadata or {},
                timestamp=datetime.utcnow(),
                duration_ms=log_data.duration_ms,
            )

            # Save to Firestore
            doc_ref = self.db.collection(self.collection_name).document(log_id)
            doc_ref.set(log_doc.dict())

            logger.info(
                f"Activity log created: {log_data.activity_type} by {log_data.username}"
            )
            return log_doc

        except Exception as e:
            logger.error(f"Failed to create activity log: {str(e)}")
            raise

    async def get_logs(self, filters: ActivityLogFilter) -> ActivityLogResponse:
        """Get activity logs with filtering and pagination"""
        try:
            # Build query
            query = self.db.collection(self.collection_name)

            # Apply filters
            if filters.user_id:
                query = query.where("user_id", "==", filters.user_id)
            if filters.username:
                query = query.where("username", "==", filters.username)
            if filters.activity_type:
                query = query.where("activity_type", "==", filters.activity_type.value)
            if filters.start_date:
                query = query.where("timestamp", ">=", filters.start_date)
            if filters.end_date:
                query = query.where("timestamp", "<=", filters.end_date)

            # Order by timestamp (newest first)
            query = query.order_by("timestamp", direction=firestore.Query.DESCENDING)

            # Get total count
            total_docs = query.stream()
            total_count = sum(1 for _ in total_docs)

            # Apply pagination
            offset = (filters.page - 1) * filters.limit
            query = query.offset(offset).limit(filters.limit)

            # Execute query
            docs = query.stream()

            # Convert to ActivityLog objects
            logs = []
            for doc in docs:
                log_data = doc.to_dict()
                log_data["id"] = doc.id
                logs.append(ActivityLog(**log_data))

            # Calculate total pages
            total_pages = (total_count + filters.limit - 1) // filters.limit

            return ActivityLogResponse(
                logs=logs,
                total=total_count,
                page=filters.page,
                limit=filters.limit,
                total_pages=total_pages,
            )

        except Exception as e:
            logger.error(f"Failed to get activity logs: {str(e)}")
            raise

    async def get_user_activity_summary(
        self, user_id: str, days: int = 7
    ) -> Dict[str, Any]:
        """Get activity summary for a user over the last N days"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Query logs for the user in the date range
            query = (
                self.db.collection(self.collection_name)
                .where("user_id", "==", user_id)
                .where("timestamp", ">=", start_date)
                .where("timestamp", "<=", end_date)
            )

            docs = query.stream()

            # Process logs
            activity_counts = {}
            daily_activity = {}
            error_count = 0

            for doc in docs:
                log_data = doc.to_dict()
                activity_type = log_data.get("activity_type", "unknown")
                timestamp = log_data.get("timestamp")

                # Count by activity type
                activity_counts[activity_type] = (
                    activity_counts.get(activity_type, 0) + 1
                )

                # Count by day
                if timestamp:
                    day = timestamp.strftime("%Y-%m-%d")
                    daily_activity[day] = daily_activity.get(day, 0) + 1

                # Count errors
                if activity_type == "error":
                    error_count += 1

            return {
                "user_id": user_id,
                "period_days": days,
                "total_activities": sum(activity_counts.values()),
                "activity_counts": activity_counts,
                "daily_activity": daily_activity,
                "error_count": error_count,
                "most_active_day": (
                    max(daily_activity.items(), key=lambda x: x[1])[0]
                    if daily_activity
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get user activity summary: {str(e)}")
            raise

    async def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Clean up activity logs older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            # Query old logs
            query = self.db.collection(self.collection_name).where(
                "timestamp", "<", cutoff_date
            )

            docs = query.stream()

            # Delete old logs
            deleted_count = 0
            batch = self.db.batch()
            batch_count = 0

            for doc in docs:
                batch.delete(doc.reference)
                deleted_count += 1
                batch_count += 1

                # Firestore batch limit is 500
                if batch_count >= 500:
                    batch.commit()
                    batch = self.db.batch()
                    batch_count = 0

            # Commit remaining deletes
            if batch_count > 0:
                batch.commit()

            logger.info(f"Cleaned up {deleted_count} old activity logs")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {str(e)}")
            raise


# Global instance
activity_log_service = ActivityLogService()
