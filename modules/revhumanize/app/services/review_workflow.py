"""
Manual Review Workflow
Handles Tier 2 content that needs human review and approval
Includes notification system and review queue management
"""
import asyncio
from datetime import datetime
from typing import List, Optional, Dict
from uuid import uuid4
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger

from ..models import (
    ManualReviewTask,
    ReviewAction,
    ReviewDecision,
    HumanizerValidationResult,
    ValidationStatus
)


class ManualReviewWorkflow:
    """
    Manages manual review queue and notifications
    for content that requires human approval
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.review_queue: Dict[str, ManualReviewTask] = {}
        
        # Email configuration (from environment)
        self.smtp_host = self.config.get('smtp_host', 'localhost')
        self.smtp_port = self.config.get('smtp_port', 587)
        self.smtp_user = self.config.get('smtp_user', '')
        self.smtp_password = self.config.get('smtp_password', '')
        self.from_email = self.config.get('from_email', 'noreply@revflow.app')
        
        # Admin notification settings
        self.admin_emails = self.config.get('admin_emails', [])
        self.slack_webhook = self.config.get('slack_webhook', None)
        
        logger.info("Manual Review Workflow initialized")
    
    async def queue_for_review(
        self,
        content_id: str,
        content: str,
        validation_result: HumanizerValidationResult,
        title: Optional[str] = None
    ) -> ManualReviewTask:
        """
        Add content to manual review queue and send notifications
        
        Args:
            content_id: Unique identifier for the content
            content: The actual content text
            validation_result: Validation results showing Tier 2 issues
            title: Optional title for the content
        
        Returns:
            ManualReviewTask that was queued
        """
        logger.info(f"Queueing content {content_id} for manual review")
        
        # Create task
        task = ManualReviewTask(
            task_id=str(uuid4()),
            content_id=content_id,
            content=content,
            validation_result=validation_result,
            tier2_issues_count=len(validation_result.tier2_issues),
            estimated_fix_time_minutes=self._estimate_fix_time(validation_result),
            priority=self._calculate_priority(validation_result),
            notes=f"Title: {title}" if title else None
        )
        
        # Add to queue
        self.review_queue[task.task_id] = task
        
        # Send notifications
        await self._notify_reviewers(task)
        
        logger.success(f"Task {task.task_id} queued for review (Priority: {task.priority})")
        
        return task
    
    def _estimate_fix_time(self, validation_result: HumanizerValidationResult) -> int:
        """
        Estimate time needed to fix issues (in minutes)
        """
        # Base time per Tier 2 issue: 5 minutes (to add proof/citations)
        tier2_time = len(validation_result.tier2_issues) * 5
        
        # Additional time for other issues
        tier3_time = len(validation_result.tier3_issues) * 1  # Quick fixes
        
        # E-E-A-T improvements
        eeat_time = 0
        if validation_result.eeat_score.total_score < 50:
            eeat_time = 10  # Need to add experience/expertise
        
        total = tier2_time + tier3_time + eeat_time
        
        return max(5, min(60, total))  # Cap between 5-60 minutes
    
    def _calculate_priority(self, validation_result: HumanizerValidationResult) -> int:
        """
        Calculate task priority (1 = highest, 5 = lowest)
        """
        # More Tier 2 issues = higher priority
        if len(validation_result.tier2_issues) >= 5:
            return 1  # Critical
        elif len(validation_result.tier2_issues) >= 3:
            return 2  # High
        elif len(validation_result.tier2_issues) >= 1:
            return 3  # Medium
        else:
            return 4  # Low
    
    async def _notify_reviewers(self, task: ManualReviewTask):
        """
        Send notifications to reviewers via multiple channels
        """
        # Email notification
        if self.admin_emails:
            await self._send_email_notification(task)
        
        # Slack notification (if configured)
        if self.slack_webhook:
            await self._send_slack_notification(task)
        
        # In-app notification would go here
        # (stored in database for UI to fetch)
        await self._create_in_app_notification(task)
    
    async def _send_email_notification(self, task: ManualReviewTask):
        """
        Send email notification to admins
        """
        try:
            subject = f"Content Review Required: {task.content_id} (Priority {task.priority})"
            
            # Build email body
            body = f"""
Content Review Needed

Content ID: {task.content_id}
Task ID: {task.task_id}
Priority: {task.priority} (1=highest, 5=lowest)
Estimated Fix Time: {task.estimated_fix_time_minutes} minutes

Issues Found:
- Tier 2 (Proof Required): {task.tier2_issues_count} issues
- Overall Quality Score: {task.validation_result.final_score}/100

Tier 2 Issues Detail:
"""
            
            for issue in task.validation_result.tier2_issues:
                body += f"\n• {issue.trigger_word}: {issue.missing_proof}"
                body += f"\n  Context: {issue.context[:100]}..."
                body += f"\n  Suggestion: {issue.suggestion}\n"
            
            body += f"\n\nReview now: https://revflow.app/review/{task.task_id}"
            body += f"\n\nThis is an automated notification from RevFlow Humanization Pipeline."
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.admin_emails)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_user and self.smtp_password:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.success(f"Email notification sent to {len(self.admin_emails)} admin(s)")
        
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
    
    async def _send_slack_notification(self, task: ManualReviewTask):
        """
        Send Slack webhook notification
        """
        try:
            import httpx
            
            message = {
                "text": f"🔔 Content Review Needed (Priority {task.priority})",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"Content Review Required: {task.content_id}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Task ID:*\n{task.task_id}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Priority:*\n{task.priority}/5"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Tier 2 Issues:*\n{task.tier2_issues_count}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Est. Fix Time:*\n{task.estimated_fix_time_minutes} min"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Quality Score:* {task.validation_result.final_score}/100"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Review Now"
                                },
                                "url": f"https://revflow.app/review/{task.task_id}",
                                "style": "primary"
                            }
                        ]
                    }
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(self.slack_webhook, json=message)
                response.raise_for_status()
            
            logger.success("Slack notification sent")
        
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
    
    async def _create_in_app_notification(self, task: ManualReviewTask):
        """
        Create in-app notification (stored in database)
        This would typically insert into a notifications table
        """
        # Placeholder - would integrate with your database
        logger.info(f"In-app notification created for task {task.task_id}")
    
    async def get_pending_tasks(self, assigned_to: Optional[str] = None) -> List[ManualReviewTask]:
        """
        Get all pending review tasks, optionally filtered by assignee
        """
        tasks = [
            task for task in self.review_queue.values()
            if task.status == "PENDING" and 
            (assigned_to is None or task.assigned_to == assigned_to)
        ]
        
        # Sort by priority
        tasks.sort(key=lambda t: (t.priority, t.created_at))
        
        return tasks
    
    async def get_task(self, task_id: str) -> Optional[ManualReviewTask]:
        """
        Get specific review task
        """
        return self.review_queue.get(task_id)
    
    async def assign_task(self, task_id: str, reviewer: str) -> bool:
        """
        Assign task to a reviewer
        """
        task = self.review_queue.get(task_id)
        if task:
            task.assigned_to = reviewer
            task.status = "IN_PROGRESS"
            logger.info(f"Task {task_id} assigned to {reviewer}")
            return True
        return False
    
    async def process_decision(
        self,
        decision: ReviewDecision,
        validator = None
    ) -> bool:
        """
        Process a review decision
        
        Args:
            decision: The reviewer's decision
            validator: HumanizerValidator instance for revalidation
        
        Returns:
            True if decision processed successfully
        """
        task = self.review_queue.get(decision.task_id)
        if not task:
            logger.error(f"Task {decision.task_id} not found")
            return False
        
        logger.info(f"Processing {decision.action.value} decision for task {decision.task_id}")
        
        if decision.action == ReviewAction.APPROVE:
            # Content was approved
            if decision.edited_content and validator:
                # Revalidate edited content
                new_validation = await validator.validate(decision.edited_content)
                
                if new_validation.final_score >= 70:
                    task.status = "COMPLETED"
                    task.validation_result = new_validation
                    logger.success(f"Task {decision.task_id} approved (Score: {new_validation.final_score})")
                    
                    # TODO: Move to deployment queue
                    # await self.export_to_deployment(task, decision.edited_content)
                else:
                    logger.warning(f"Edited content still fails validation (Score: {new_validation.final_score})")
                    return False
            else:
                task.status = "COMPLETED"
                logger.success(f"Task {decision.task_id} approved")
        
        elif decision.action == ReviewAction.REQUEST_CHANGES:
            # Send back for revisions
            task.notes = decision.review_notes
            task.status = "PENDING"
            task.assigned_to = None
            logger.info(f"Task {decision.task_id} sent back for revisions")
        
        elif decision.action == ReviewAction.REGENERATE:
            # Request AI regeneration
            task.status = "REJECTED"
            logger.info(f"Task {decision.task_id} marked for regeneration")
            
            # TODO: Trigger regeneration workflow
            # await self.trigger_regeneration(task, decision.review_notes)
        
        elif decision.action == ReviewAction.REJECT:
            # Completely reject
            task.status = "REJECTED"
            logger.info(f"Task {decision.task_id} rejected")
        
        # Remove from active queue if completed/rejected
        if task.status in ["COMPLETED", "REJECTED"]:
            # TODO: Move to archive/history
            pass
        
        return True
    
    async def get_queue_stats(self) -> Dict:
        """
        Get statistics about the review queue
        """
        total = len(self.review_queue)
        pending = sum(1 for t in self.review_queue.values() if t.status == "PENDING")
        in_progress = sum(1 for t in self.review_queue.values() if t.status == "IN_PROGRESS")
        completed = sum(1 for t in self.review_queue.values() if t.status == "COMPLETED")
        
        avg_priority = sum(t.priority for t in self.review_queue.values()) / total if total > 0 else 0
        
        return {
            "total_tasks": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "avg_priority": avg_priority,
            "urgent_tasks": sum(1 for t in self.review_queue.values() if t.priority == 1)
        }
