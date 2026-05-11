"""Daglig email-digest for notifikationer.

I dag emitterer Bifrost notifikationer til klokken (in-app). For brugere
der ikke logger ind dagligt, eller for ledere der vil have et samlet overblik
hver morgen, sender denne service en daglig email-digest kl. 08:00.

Indhold:
  - Antal nye notifikationer sidste 24 timer
  - Grupperet pr. kind (evidens_completed, evidens_comment, deadline_warning)
  - Top-5 cases med mest aktivitet
  - Link til /sager + /portefolje

Konfiguration via env:
  NOTIFICATION_DIGEST_ENABLED=true|false (default false — opt-in)
  NOTIFICATION_DIGEST_RECIPIENT=pavi@kalundborg.dk (kommasepareret hvis flere)
  NOTIFICATION_DIGEST_BASE_URL=https://bifrost.kalundborg.dk (link-baseurl)
  SMTP_* (samme som case-reminder-service)

Schedule registreres i main.py lifespan (kører 08:00 dagligt).
"""

from __future__ import annotations

import logging
import os
import smtplib
from collections import defaultdict
from datetime import datetime, UTC, timedelta
from email.message import EmailMessage
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger("bifrost.notification_digest")


KIND_LABELS = {
    "evidens_completed": "evidens markeret færdig",
    "evidens_comment": "kommentar tilføjet",
    "evidens_started": "evidens påbegyndt",
    "vurdering": "vurdering kørt",
    "transition": "status-skift",
    "deadline_warning": "deadline-advarsel",
    "review_due": "review forfalden",
    "info": "info",
}


def _fmt_relative(then: datetime, now: datetime) -> str:
    diff = now - then
    if diff.total_seconds() < 3600:
        return f"{int(diff.total_seconds() / 60)} min siden"
    if diff.total_seconds() < 86400:
        return f"{int(diff.total_seconds() / 3600)} t siden"
    return f"{diff.days} d siden"


def build_digest_body(
    db: Session,
    since: datetime,
    base_url: str,
) -> Optional[tuple[str, str]]:
    """Bygger (subject, body_text) for digest.

    Returnerer None hvis der ikke er noget at rapportere (så vi ikke spammer).
    """
    from src.database.notifications import Notification

    now = datetime.now(UTC)
    stmt = (
        select(Notification)
        .where(Notification.created_at >= since)
        .order_by(Notification.created_at.desc())
    )
    rows = db.execute(stmt).scalars().all()

    if not rows:
        return None

    # Gruppér pr. kind og case_id
    by_kind: dict[str, int] = defaultdict(int)
    by_case: dict[str, list[Notification]] = defaultdict(list)
    for n in rows:
        by_kind[n.kind or "info"] += 1
        if n.case_id:
            by_case[n.case_id].append(n)

    total = len(rows)
    unread = sum(1 for n in rows if n.read_at is None)

    date_str = now.strftime("%-d. %B %Y")
    subject = f"Bifrost digest · {date_str} · {total} nye notifikationer"

    lines: list[str] = []
    lines.append(f"Bifrost — daglig digest for {date_str}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"De sidste 24 timer: {total} notifikationer ({unread} ulæste).")
    lines.append("")

    lines.append("FORDELT PÅ TYPE")
    lines.append("-" * 60)
    for kind, count in sorted(by_kind.items(), key=lambda x: x[1], reverse=True):
        label = KIND_LABELS.get(kind, kind)
        lines.append(f"  {count:>3}  {label}")
    lines.append("")

    if by_case:
        lines.append("MEST AKTIVE SAGER (TOP 5)")
        lines.append("-" * 60)
        top_cases = sorted(by_case.items(), key=lambda x: len(x[1]), reverse=True)[:5]
        for case_id, case_notifs in top_cases:
            count = len(case_notifs)
            lines.append(
                f"  {count:>3}  {case_id} — {base_url}/sag/{case_id}"
            )
            # Vis 2 seneste eksempler per sag
            for n in case_notifs[:2]:
                rel = _fmt_relative(n.created_at, now)
                title = (n.title or "")[:80]
                lines.append(f"          ↳ {rel}: {title}")
        lines.append("")

    lines.append("HURTIGE LINKS")
    lines.append("-" * 60)
    lines.append(f"  Alle sager:           {base_url}/sager")
    lines.append(f"  Portefølje-overblik:  {base_url}/portefolje")
    lines.append(f"  Lov-bibliotek:        {base_url}/ressourcer")
    lines.append("")
    lines.append("--")
    lines.append("Bifrost — Kalundborg Kommunes interne AI-compliance-platform")
    lines.append("Afmeld: sæt NOTIFICATION_DIGEST_ENABLED=false i .env")

    return subject, "\n".join(lines)


def send_digest_if_enabled(db: Session) -> dict:
    """Kører én digest-cyclus. Kaldes fra scheduler.

    Returnerer en summary-dict med status — bruges i logs + /drift.
    """
    enabled = os.getenv("NOTIFICATION_DIGEST_ENABLED", "false").lower() not in (
        "0", "false", "no", ""
    )
    if not enabled:
        return {"status": "disabled"}

    recipients_raw = os.getenv("NOTIFICATION_DIGEST_RECIPIENT", "").strip()
    if not recipients_raw:
        logger.warning("NOTIFICATION_DIGEST_RECIPIENT ikke sat — skip")
        return {"status": "no_recipient"}

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]

    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        logger.warning("SMTP_HOST ikke sat — skip digest")
        return {"status": "no_smtp"}

    base_url = os.getenv("NOTIFICATION_DIGEST_BASE_URL", "http://localhost:8090").rstrip("/")
    since = datetime.now(UTC) - timedelta(hours=24)

    result = build_digest_body(db, since=since, base_url=base_url)
    if result is None:
        return {"status": "no_notifications"}

    subject, body = result
    sender = os.getenv("SMTP_FROM", "no-reply@kalundborg.dk")

    sent = 0
    failed = 0
    for recipient in recipients:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient
        msg.set_content(body)

        try:
            smtp_port = int(os.getenv("SMTP_PORT", "25"))
            use_tls = os.getenv("SMTP_USE_TLS", "false").lower() not in {"0", "false", "no"}
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                if use_tls:
                    server.starttls()
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.send_message(msg, from_addr=sender, to_addrs=[recipient])
            sent += 1
        except Exception:
            logger.exception("Failed to send digest to %s", recipient)
            failed += 1

    logger.info("Notification digest sent — sent=%d failed=%d", sent, failed)
    return {
        "status": "sent",
        "recipients": len(recipients),
        "sent": sent,
        "failed": failed,
    }
