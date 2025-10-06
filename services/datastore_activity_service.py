"""
Datastore Activity Logging Service
Compatible with both Firestore Native Mode and Datastore Mode
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from google.cloud import datastore
from models.activity_log import (
    ActivityLog,
    ActivityLogCreate,
    ActivityLogFilter,
    ActivityLogResponse,
)
import logging

logger = logging.getLogger(__name__)


class DatastoreActivityService:
    """Service for managing user activity logs using Cloud Datastore"""

    def __init__(self):
        """Initialize the activity log service"""
        self.client = datastore.Client()
        self.kind = "ActivityLog"

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

            # Create Datastore entity
            key = self.client.key(self.kind, log_id)
            entity = datastore.Entity(key=key)

            # Convert to dict and handle datetime serialization
            log_dict = log_doc.dict()
            log_dict["timestamp"] = log_doc.timestamp  # Keep as datetime for Datastore

            # Set entity properties
            entity.update(log_dict)

            # Save to Datastore
            self.client.put(entity)

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
            query = self.client.query(kind=self.kind)

            # Apply filters
            if filters.user_id:
                query.add_filter("user_id", "=", filters.user_id)
            if filters.username:
                query.add_filter("username", "=", filters.username)
            if filters.activity_type:
                query.add_filter("activity_type", "=", filters.activity_type.value)
            if filters.start_date:
                query.add_filter("timestamp", ">=", filters.start_date)
            if filters.end_date:
                query.add_filter("timestamp", "<=", filters.end_date)

            # Order by timestamp (newest first)
            query.order = ["-timestamp"]

            # Get total count (approximate)
            total_count = len(list(query.fetch()))

            # Apply pagination
            offset = (filters.page - 1) * filters.limit
            query.offset = offset
            query.limit = filters.limit

            # Execute query
            entities = list(query.fetch())

            # Convert to ActivityLog objects
            logs = []
            for entity in entities:
                log_data = dict(entity)
                log_data["id"] = entity.key.id_or_name
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
            query = self.client.query(kind=self.kind)
            query.add_filter("user_id", "=", user_id)
            query.add_filter("timestamp", ">=", start_date)
            query.add_filter("timestamp", "<=", end_date)

            entities = list(query.fetch())

            # Process logs
            activity_counts = {}
            daily_activity = {}
            error_count = 0

            for entity in entities:
                log_data = dict(entity)
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
            query = self.client.query(kind=self.kind)
            query.add_filter("timestamp", "<", cutoff_date)

            entities = list(query.fetch())

            # Delete old logs in batches
            deleted_count = 0
            batch = self.client.batch()
            batch_count = 0

            for entity in entities:
                batch.delete(entity.key)
                deleted_count += 1
                batch_count += 1

                # Datastore batch limit is 500
                if batch_count >= 500:
                    batch.commit()
                    batch = self.client.batch()
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
datastore_activity_service = DatastoreActivityService()
