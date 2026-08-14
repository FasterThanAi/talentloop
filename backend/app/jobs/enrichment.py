import asyncio
import ipaddress
import logging
import socket
import urllib.parse
import urllib.robotparser
from typing import Any, Dict, List, Optional, Set, Tuple

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

from app.ai.runner import run_structured
from app.core.audit import write_audit
from app.core.db import SessionLocal
from app.jobs.runner import register_job_handler, update_job_progress
from app.models import Candidate, CandidateResearch
from app.schemas.ai import CandidateEvidence

logger = logging.getLogger("talentloop.enrichment")

# urllib's RobotFileParser accepts no timeout, so the only way to bound it is the global
# socket default. Set it around the read and restore it immediately afterwards.
ROBOTS_TIMEOUT_SECONDS = 5.0


def is_safe_url(url: str) -> tuple[bool, str]:
    """
    DNS-resolving SSRF guard.
    Resolves hostname to IP addresses and rejects private, loopback, link-local, or reserved IPs.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, f"Unsupported scheme: {parsed.scheme}"

        hostname = parsed.hostname
        if not hostname:
            return False, "Missing hostname"

        # Explicit string checks
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "metadata.google.internal"):
            return False, "Blocked host address"

        # Resolve DNS to IP addresses
        addr_info = socket.getaddrinfo(hostname, None)
        for entry in addr_info:
            ip_str = entry[4][0]
            ip = ipaddress.ip_address(ip_str)
            if (
                ip.is_loopback
                or ip.is_private
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
                or ip.is_unspecified
            ):
                return False, f"Host {hostname} resolved to unsafe IP {ip_str}"

        return True, "Safe"
    except Exception as e:
        return False, f"DNS resolution failed: {e}"


def check_robots_allowed(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        # RobotFileParser has no timeout parameter and will otherwise inherit "wait
        # forever". A stuck robots.txt fetch used to hang the whole request.
        old_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(ROBOTS_TIMEOUT_SECONDS)
        try:
            rp.read()
        finally:
            socket.setdefaulttimeout(old_timeout)
        return rp.can_fetch("TalentLoopBot/1.0", url)
    except Exception:
        # Default to allowed if robots.txt unreachable
        return True


async def fetch_page_clean_text(url: str) -> dict[str, str] | None:
    # is_safe_url does blocking DNS (socket.getaddrinfo) and check_robots_allowed does a
    # blocking HTTP fetch. Both are called from a coroutine, so running them inline would
    # stall the event loop — and with one worker on Render, that stalls the entire API.
    # Off to a thread they go.
    safe, reason = await asyncio.to_thread(is_safe_url, url)
    if not safe:
        logger.warning(f"SSRF guard blocked fetch for {url}: {reason}")
        return None

    if not await asyncio.to_thread(check_robots_allowed, url):
        logger.info(f"robots.txt disallowed fetch for {url}, skipping.")
        return None

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            headers = {"User-Agent": "TalentLoopBot/1.0 (+https://talentloop.dev/bot)"}
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return None

            # 1 MB size cap
            content_bytes = response.content[: 1024 * 1024]
            soup = BeautifulSoup(content_bytes, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg"]):
                tag.decompose()

            text = soup.get_text(separator=" ", strip=True)
            # Limit clean text length to 4000 characters
            text = text[:4000]
            return {"url": url, "text": text}
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


async def enrich_candidate(candidate_id: str, org_id: str) -> CandidateResearch | None:
    db = SessionLocal()
    try:
        stmt = select(Candidate).where(Candidate.id == candidate_id, Candidate.org_id == org_id)
        candidate = db.execute(stmt).scalar_one_or_none()
        if not candidate:
            return None

        # Fetch up to 3 candidate public URLs
        public_urls = candidate.public_urls or []
        fetched_pages = []
        fetched_urls_set: set[str] = set()

        for url in public_urls[:3]:
            page_data = await fetch_page_clean_text(url)
            if page_data and page_data.get("text"):
                fetched_pages.append(page_data)
                fetched_urls_set.add(page_data["url"])

        # If candidate has no fetched public pages, construct fallback context from name/source
        if not fetched_pages:
            fallback_url = public_urls[0] if public_urls else f"https://profile.local/{candidate.id}"
            fetched_pages.append({
                "url": fallback_url,
                "text": f"Candidate Profile for {candidate.full_name}. Sourced from {candidate.source}."
            })
            fetched_urls_set.add(fallback_url)

        # Call enrich.v1.md prompt
        evidence_result, _ = await run_structured(
            prompt_name="enrich.v1",
            variables={"pages": fetched_pages},
            schema=CandidateEvidence,
            temperature=0.2
        )

        # Anti-Hallucination Gate:
        # Validate that every claim cites a URL actually present in fetched_urls_set
        valid_skills = [s for s in evidence_result.skills if s.source_url in fetched_urls_set]
        valid_signals = [s for s in evidence_result.seniority_signals if s.source_url in fetched_urls_set]
        valid_projects = [p for p in evidence_result.projects if p.source_url in fetched_urls_set]

        # Check existing research record
        stmt_res = select(CandidateResearch).where(CandidateResearch.candidate_id == candidate.id)
        research = db.execute(stmt_res).scalar_one_or_none()

        if not research:
            research = CandidateResearch(
                org_id=org_id,
                candidate_id=candidate.id,
                summary=evidence_result.summary,
                skills=[s.model_dump() for s in valid_skills],
                seniority_signals=[s.model_dump() for s in valid_signals],
                projects=[p.model_dump() for p in valid_projects],
                evidence_urls=list(fetched_urls_set),
                confidence=evidence_result.confidence,
                could_not_determine=evidence_result.could_not_determine
            )
            db.add(research)
        else:
            research.summary = evidence_result.summary
            research.skills = [s.model_dump() for s in valid_skills]
            research.seniority_signals = [s.model_dump() for s in valid_signals]
            research.projects = [p.model_dump() for p in valid_projects]
            research.evidence_urls = list(fetched_urls_set)
            research.confidence = evidence_result.confidence
            research.could_not_determine = evidence_result.could_not_determine

        write_audit(
            db=db,
            org_id=org_id,
            actor_id="system",
            action="candidate_enriched",
            entity="candidate",
            entity_id=candidate.id,
            payload={
                "claims_kept": len(valid_skills) + len(valid_signals) + len(valid_projects),
                "sources": len(fetched_urls_set),
                "confidence": evidence_result.confidence,
            },
        )

        db.commit()
        db.refresh(research)
        return research
    finally:
        db.close()


async def handle_enrichment_job(job_id: str, payload: dict[str, Any]) -> None:
    org_id = payload.get("org_id")
    candidate_ids: list[str] = payload.get("candidate_ids", [])

    for c_id in candidate_ids:
        try:
            await enrich_candidate(candidate_id=c_id, org_id=org_id)
            update_job_progress(job_id, processed_delta=1)
        except Exception as e:
            logger.error(f"Error enriching candidate {c_id}: {e}")
            update_job_progress(job_id, processed_delta=1, error_entry={"candidate_id": c_id, "error": str(e)})


register_job_handler("enrich_candidates", handle_enrichment_job)
