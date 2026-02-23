"""Seed the knowledge_base table with 15+ articles and their embeddings.

Usage:
    python -m database.migrations.002_seed_knowledge_base

Requires:
    - DATABASE_URL env var pointing to a PostgreSQL instance with the schema
      from 001_initial_schema.sql already applied.
    - OPENAI_API_KEY env var for embedding generation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

import asyncpg
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Articles — each has a distinct topic for strong semantic differentiation
# ---------------------------------------------------------------------------
ARTICLES: list[dict[str, str]] = [
    {
        "title": "Getting Started with Our Platform",
        "category": "getting-started",
        "content": (
            "Welcome to our platform! To get started, create an account at "
            "app.example.com/signup using your work email. After verifying your "
            "email you will be taken to the onboarding wizard which walks you "
            "through creating your first project, inviting team members, and "
            "configuring your workspace settings. The whole process takes about "
            "5 minutes."
        ),
    },
    {
        "title": "How to Reset Your Password",
        "category": "account-management",
        "content": (
            "To reset your password, go to the login page and click 'Forgot "
            "Password'. Enter the email address associated with your account. "
            "You will receive a password reset link within 2 minutes. The link "
            "expires after 24 hours. Your new password must be at least 12 "
            "characters and include a mix of letters, numbers, and symbols. If "
            "you do not receive the email, check your spam folder or contact "
            "support."
        ),
    },
    {
        "title": "Managing Your Account Settings",
        "category": "account-management",
        "content": (
            "Access your account settings by clicking the gear icon in the top "
            "right corner. From there you can update your display name, profile "
            "picture, timezone, language preference, and notification settings. "
            "To change your email address, go to Account > Security and follow "
            "the verification process. You can also enable two-factor "
            "authentication (2FA) using an authenticator app for added security."
        ),
    },
    {
        "title": "Billing and Subscription Plans",
        "category": "billing",
        "content": (
            "We offer three subscription plans: Free, Pro ($29/month), and "
            "Enterprise (custom pricing). The Free plan includes up to 3 "
            "projects and 5 team members. Pro unlocks unlimited projects, "
            "advanced analytics, and priority support. Enterprise adds SSO, "
            "audit logs, and a dedicated account manager. You can upgrade or "
            "downgrade at any time from Settings > Billing. Changes take "
            "effect at the start of your next billing cycle."
        ),
    },
    {
        "title": "Understanding Your Invoice",
        "category": "billing",
        "content": (
            "Invoices are generated on the first of each month and sent to "
            "the billing email on file. Each invoice shows the plan name, "
            "billing period, per-seat charges, any add-on costs, applicable "
            "taxes, and the total amount. You can download past invoices from "
            "Settings > Billing > Invoice History. If you spot an error on "
            "your invoice, contact our billing team within 30 days."
        ),
    },
    {
        "title": "Troubleshooting Login Issues",
        "category": "troubleshooting",
        "content": (
            "If you cannot log in, first make sure you are using the correct "
            "email address and password. Clear your browser cache and cookies, "
            "then try again. If you have 2FA enabled, ensure your "
            "authenticator app is synced. If your account has been locked due "
            "to too many failed attempts, wait 15 minutes before trying again. "
            "If you still cannot access your account, use the 'Forgot "
            "Password' flow or contact support."
        ),
    },
    {
        "title": "Troubleshooting Slow Performance",
        "category": "troubleshooting",
        "content": (
            "If the platform feels slow, check your internet connection first. "
            "Try a different browser or disable browser extensions that may "
            "interfere. Clear your browser cache. If the issue persists, check "
            "our status page at status.example.com for any ongoing incidents. "
            "For large workspaces (1000+ items), enabling pagination in "
            "Settings > Performance can improve load times."
        ),
    },
    {
        "title": "How to Create and Manage Projects",
        "category": "feature-how-to",
        "content": (
            "To create a new project, click the '+' button on your dashboard "
            "and choose a template or start from scratch. Give your project a "
            "name, description, and assign a team. Projects can be organized "
            "into folders for better structure. You can archive completed "
            "projects from the project settings menu. Archived projects remain "
            "accessible but do not count toward your plan limits."
        ),
    },
    {
        "title": "Using the Task Management Feature",
        "category": "feature-how-to",
        "content": (
            "Each project contains a task board with customizable columns "
            "(e.g., To Do, In Progress, Done). Create tasks by clicking "
            "'+ Add Task' in any column. Tasks support descriptions, due "
            "dates, assignees, labels, attachments, and sub-tasks. Drag and "
            "drop tasks between columns to update their status. Use filters "
            "and sorting to find tasks quickly in large projects."
        ),
    },
    {
        "title": "Configuring Notification Settings",
        "category": "notifications",
        "content": (
            "Control your notifications from Settings > Notifications. You "
            "can choose to receive notifications via email, in-app, or both. "
            "Set preferences per event type: task assignments, mentions, "
            "project updates, and due date reminders. You can also set quiet "
            "hours during which no notifications are sent. Team admins can "
            "configure default notification settings for new team members."
        ),
    },
    {
        "title": "Integrations Overview",
        "category": "integrations",
        "content": (
            "Our platform integrates with popular tools including Slack, "
            "Microsoft Teams, Jira, GitHub, Google Drive, and Zapier. To "
            "set up an integration, go to Settings > Integrations, find the "
            "tool you want to connect, and follow the authorization flow. "
            "Each integration has specific permissions you can configure. "
            "Use Zapier for custom workflows connecting to 5000+ apps."
        ),
    },
    {
        "title": "API Documentation and Access",
        "category": "api",
        "content": (
            "Our REST API is available at api.example.com/v1. To get started, "
            "generate an API key from Settings > Developer > API Keys. The "
            "API uses Bearer token authentication. Rate limits are 100 "
            "requests per minute for Pro plans and 1000 for Enterprise. Full "
            "API documentation with interactive examples is available at "
            "docs.example.com/api. SDKs are provided for Python, JavaScript, "
            "and Go."
        ),
    },
    {
        "title": "Security and Data Privacy",
        "category": "security",
        "content": (
            "We take security seriously. All data is encrypted at rest "
            "(AES-256) and in transit (TLS 1.3). We are SOC 2 Type II "
            "certified and GDPR compliant. Two-factor authentication is "
            "available for all accounts and mandatory for Enterprise plans. "
            "We perform regular penetration testing and security audits. "
            "You can review our security whitepaper at example.com/security."
        ),
    },
    {
        "title": "How to Export Your Data",
        "category": "data-export",
        "content": (
            "You can export your data at any time from Settings > Data "
            "Management > Export. Choose what to export: projects, tasks, "
            "comments, attachments, or everything. Export formats include "
            "CSV, JSON, and PDF. Large exports are processed in the "
            "background and you will receive an email with a download link "
            "when ready. Exports are available for download for 7 days."
        ),
    },
    {
        "title": "Team Management and Roles",
        "category": "account-management",
        "content": (
            "Manage your team from Settings > Team. You can invite members "
            "by email and assign one of four roles: Viewer (read-only), "
            "Member (create and edit), Admin (manage settings and members), "
            "and Owner (full control including billing). Each role has "
            "specific permissions. You can change a member's role at any "
            "time. Removing a member revokes their access immediately but "
            "preserves their contributions."
        ),
    },
    {
        "title": "Using Webhooks for Automation",
        "category": "api",
        "content": (
            "Webhooks let you receive real-time HTTP POST notifications when "
            "events occur in your workspace. Go to Settings > Developer > "
            "Webhooks to create a webhook endpoint. Supported events include "
            "task.created, task.updated, project.created, and member.joined. "
            "Each webhook delivery includes a signature header for "
            "verification. Failed deliveries are retried up to 3 times with "
            "exponential backoff."
        ),
    },
    {
        "title": "How to Delete Your Account",
        "category": "account-management",
        "content": (
            "To delete your account, go to Settings > Account > Delete "
            "Account. You will be asked to confirm by typing your email "
            "address. Account deletion is permanent and cannot be undone. "
            "All your personal data, projects you own, and associated files "
            "will be permanently removed within 30 days. If you are the "
            "sole Owner of a team, you must transfer ownership before "
            "deleting your account. We recommend exporting your data first "
            "using Settings > Data Management > Export."
        ),
    },
]


async def _generate_embeddings(
    client: AsyncOpenAI,
    texts: list[str],
    model: str = "text-embedding-3-small",
) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    response = await client.embeddings.create(input=texts, model=model)
    return [item.embedding for item in response.data]


async def seed(dsn: str | None = None) -> int:
    """Insert seed articles with embeddings into the knowledge_base table.

    Returns the number of articles inserted.
    """
    dsn = dsn or os.environ["DATABASE_URL"]
    client = AsyncOpenAI()  # reads OPENAI_API_KEY from env

    logger.info("Generating embeddings for %d articles …", len(ARTICLES))
    texts = [f"{a['title']}\n\n{a['content']}" for a in ARTICLES]
    embeddings = await _generate_embeddings(client, texts)

    conn: asyncpg.Connection = await asyncpg.connect(dsn)
    try:
        # Register vector codec for this connection
        await conn.set_type_codec(
            "vector",
            encoder=lambda v: json.dumps(v),
            decoder=lambda v: json.loads(v),
            schema="public",
            format="text",
        )

        inserted = 0
        for article, embedding in zip(ARTICLES, embeddings):
            await conn.execute(
                """
                INSERT INTO knowledge_base (title, content, category, embedding)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT DO NOTHING
                """,
                article["title"],
                article["content"],
                article["category"],
                embedding,
            )
            inserted += 1
            logger.info("Inserted: %s", article["title"])

        logger.info("Seeded %d articles into knowledge_base.", inserted)
        return inserted
    finally:
        await conn.close()


async def main() -> None:
    from dotenv import load_dotenv

    load_dotenv()
    await seed()


if __name__ == "__main__":
    asyncio.run(main())
