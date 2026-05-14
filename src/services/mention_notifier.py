"""Notifikation + email-udsending når en bruger @-mentions i en kommentar.

Flow:
  1. Når en evidens-kommentar oprettes parser vi body for @<email>
  2. Resolves mod users-tabellen — ukendte emails ignoreres stille
  3. For hver kendt + aktiv bruger:
     a) Opret en notification med deres email som actor + link tilbage til sagen
     b) Send email via SMTP hvis SMTP_HOST er konfigureret (best-effort)

Email-afsending er fire-and-forget — fejl skrives kun til log. Notification
forsøges altid (vigtigste mekanisme er bell-badge i UI'en).
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Optional

from sqlalchemy.orm import Session

from src.database import notifications as notif_svc
from src.database.users import User, resolve_mentions

logger = logging.getLogger("bifrost.mention_notifier")


def notify_mentions(
    db: Session,
    *,
    mentioned_emails: list[str],
    comment_body: str,
    author: Optional[str],
    case_id: str,
    artifact_id: str,
    section_key: Optional[str] = None,
) -> dict:
    """Notificér nævnte brugere via in-app notifikation + email (best-effort).

    Returns:
        dict med:
          - notified: liste af emails vi sendte til
          - skipped: liste af emails ikke fundet i users-tabel
          - emails_sent: count of successful email sends
          - emails_failed: count of failed
    """
    if not mentioned_emails:
        return {"notified": [], "skipped": [], "emails_sent": 0, "emails_failed": 0}

    resolved: list[User] = resolve_mentions(db, mentioned_emails)
    resolved_emails = {u.email.lower() for u in resolved}
    skipped = [e for e in mentioned_emails if e.lower() not in resolved_emails]

    preview = (comment_body[:120] + "…") if len(comment_body) > 120 else comment_body
    section_label = section_key or "hele dokumentet"
    artifact_label = artifact_id.replace("_", " ")
    link_url = f"/sag/{case_id}?tab=evidens"

    notified = []
    emails_sent = 0
    emails_failed = 0

    for user in resolved:
        # In-app notification (bell)
        try:
            notif_svc.emit(
                db,
                kind="evidens_mention",
                title=f"Du blev nævnt af {author or 'en kollega'}",
                message=f"På {artifact_label} ({section_label}): '{preview}'",
                case_id=case_id,
                link_url=link_url,
                severity="info",
                actor=user.email,  # actor = mention-modtager, så vi kan filtrere
            )
            notified.append(user.email)
        except Exception as exc:
            logger.warning("Mention-notification fejlede for %s: %s", user.email, exc)

        # Email (best-effort — kun hvis SMTP er konfigureret)
        if os.getenv("SMTP_HOST"):
            try:
                _send_mention_email(
                    to=user.email,
                    to_name=user.display_name,
                    author=author,
                    preview=preview,
                    artifact_label=artifact_label,
                    section_label=section_label,
                    case_id=case_id,
                )
                emails_sent += 1
            except Exception as exc:
                emails_failed += 1
                logger.warning("Mention-email fejlede for %s: %s", user.email, exc)

    return {
        "notified": notified,
        "skipped": skipped,
        "emails_sent": emails_sent,
        "emails_failed": emails_failed,
    }


def _send_mention_email(
    *,
    to: str,
    to_name: str,
    author: Optional[str],
    preview: str,
    artifact_label: str,
    section_label: str,
    case_id: str,
) -> None:
    """Send mention-notifikations-email via SMTP."""
    smtp_host = os.getenv("SMTP_HOST", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "25"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    use_tls = os.getenv("SMTP_USE_TLS", "false").lower() not in {"0", "false", "no"}
    sender = os.getenv("SMTP_FROM") or smtp_user or "no-reply@bifrost.local"

    base_url = os.getenv("BIFROST_BASE_URL", "http://localhost:8090").rstrip("/")
    full_link = f"{base_url}/sag/{case_id}?tab=evidens"

    message = EmailMessage()
    message["Subject"] = f"[Bifrost] Du blev nævnt: {artifact_label}"
    message["From"] = sender
    message["To"] = to

    body = (
        f"Hej {to_name},\n\n"
        f"{author or 'En kollega'} nævnte dig i en kommentar på {artifact_label} "
        f"({section_label}):\n\n"
        f"  \"{preview}\"\n\n"
        f"Åbn sagen: {full_link}\n\n"
        f"— Bifrost AI compliance\n"
        f"(Du modtager denne email fordi din email blev nævnt med @ i en kommentar. "
        f"Skriv til administrator hvis du ikke ønsker flere notifikationer.)\n"
    )
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        if use_tls:
            server.starttls()
        if smtp_user and smtp_password:
            server.login(smtp_user, smtp_password)
        server.send_message(message)
    logger.info("Sendte mention-email til %s om sag %s", to, case_id)
