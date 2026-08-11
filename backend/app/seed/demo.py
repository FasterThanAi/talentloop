import argparse
import logging
from datetime import UTC, datetime, timezone

from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.core.db import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    AuditEvent,
    Candidate,
    CandidateResearch,
    CredentialRecord,
    FeedbackReport,
    InterviewSession,
    Job,
    KnowledgeChunk,
    Organization,
    OutreachMessage,
    PipelineEntry,
    Reply,
    Requisition,
    User,
)
from app.rubric.compute import compute_fit_score
from app.rubric.dimensions import RUBRIC_VERSION
from app.schemas.ai import DimensionScore, ScoreBreakdown

logger = logging.getLogger("talentloop.seed")


def utcnow() -> datetime:
    return datetime.now(UTC)


SYNTHETIC_CANDIDATE_NAMES = [
    # Top tier (80-100)
    ("Alex Rivera", "alex.rivera@synth.dev", 92, "High"),
    ("Elena Rostova", "elena.rostova@synth.dev", 88, "High"),
    ("Priya Sharma", "priya.sharma@synth.dev", 87, "High"),
    ("Marcus Vance", "marcus.vance@synth.dev", 85, "High"),
    ("Chen Wei", "chen.wei@synth.dev", 84, "High"),
    ("Hannah Abbott", "hannah.abbott@synth.dev", 81, "High"),

    # Mid tier (60-79)
    ("David Kim", "david.kim@synth.dev", 78, "Medium"),
    ("Sophia Zhang", "sophia.zhang@synth.dev", 76, "High"),
    ("Tariq Al-Mansoor", "tariq.mansoor@synth.dev", 75, "Medium"),
    ("Chloe Bennett", "chloe.bennett@synth.dev", 73, "Medium"),
    ("Mateo Hernandez", "mateo.hernandez@synth.dev", 72, "Medium"),
    ("Nia Adebayo", "nia.adebayo@synth.dev", 70, "Medium"),
    ("Lucas Silva", "lucas.silva@synth.dev", 69, "Medium"),
    ("Aisha Khan", "aisha.khan@synth.dev", 68, "Medium"),
    ("Devin O'Connor", "devin.oconnor@synth.dev", 66, "Medium"),
    ("Zoe Kravitz", "zoe.kravitz@synth.dev", 65, "Medium"),
    ("Liam Gallagher", "liam.gallagher@synth.dev", 64, "Medium"),
    ("Ananya Patel", "ananya.patel@synth.dev", 63, "Medium"),
    ("Gabriel Santos", "gabriel.santos@synth.dev", 62, "Medium"),
    ("Freja Lind", "freja.lind@synth.dev", 60, "Medium"),

    # Low-mid tier (40-59)
    ("Maya Lin", "maya.lin@synth.dev", 58, "Medium"),
    ("Jamal Washington", "jamal.washington@synth.dev", 56, "Medium"),
    ("Emily Watson", "emily.watson@synth.dev", 55, "Low"),
    ("Ethan Miller", "ethan.miller@synth.dev", 54, "Low"),
    ("Yuki Tanaka", "yuki.tanaka@synth.dev", 52, "Medium"),
    ("Carlos Mendez", "carlos.mendez@synth.dev", 50, "Low"),
    ("Amara Okafor", "amara.okafor@synth.dev", 48, "Low"),
    ("Felix Baum", "felix.baum@synth.dev", 47, "Low"),
    ("Dmitri Volkov", "dmitri.volkov@synth.dev", 45, "Low"),
    ("Layla Hassan", "layla.hassan@synth.dev", 44, "Low"),
    ("Oliver Smith", "oliver.smith@synth.dev", 42, "Low"),
    ("Jack Wilson", "jack.wilson@synth.dev", 40, "Low"),

    # Low tier (0-39)
    ("Samira Geller", "samira.geller@synth.dev", 38, "Low"),
    ("Toby Flenderson", "toby.flenderson@synth.dev", 35, "Low"),
    ("Oscar Martinez", "oscar.martinez@synth.dev", 33, "Low"),
    ("Kevin Malone", "kevin.malone@synth.dev", 30, "Low"),
    ("Angela Martin", "angela.martin@synth.dev", 28, "Low"),
    ("Stanley Hudson", "stanley.hudson@synth.dev", 25, "Low"),
    ("Phyllis Vance", "phyllis.vance@synth.dev", 22, "Low"),
    ("Creed Bratton", "creed.bratton@synth.dev", 18, "Low")
]


def seed_demo_data(reset: bool = False) -> None:
    db: Session = SessionLocal()
    try:
        if reset:
            print("Resetting existing database tables...")
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)

        # 1. Create Organization
        org = Organization(
            name="Acme AI Technologies",
            plan="enterprise"
        )
        db.add(org)
        db.flush()

        # 2. Create Users
        # Recruiter
        recruiter = User(
            org_id=org.id,
            email="demo@talentloop.dev",
            password_hash=hash_password("password123"),
            role="recruiter",
            gmail_email="demo@talentloop.dev"
        )
        # Candidate 1 (Top Fit)
        candidate_user1 = User(
            org_id=org.id,
            email="alex.rivera@synth.dev",
            password_hash=hash_password("password123"),
            role="candidate"
        )
        # Candidate 2 (Mid Fit with released report)
        candidate_user2 = User(
            org_id=org.id,
            email="david.kim@synth.dev",
            password_hash=hash_password("password123"),
            role="candidate"
        )
        db.add_all([recruiter, candidate_user1, candidate_user2])
        db.flush()

        # 3. Create Organization Knowledge Base Chunks
        k1 = KnowledgeChunk(
            org_id=org.id,
            source_type="salary_bands",
            content="Senior Backend Engineer base compensation is $155,000 - $185,000 USD plus 0.15% equity grant, 401(k) matching up to 4%, and comprehensive health/dental coverage."
        )
        k2 = KnowledgeChunk(
            org_id=org.id,
            source_type="company_policy",
            content="TalentLoop is a remote-first organization with flexible working hours across US, Canada, and European timezones. We provide a $2,500 home office setup stipend."
        )
        k3 = KnowledgeChunk(
            org_id=org.id,
            source_type="role_context",
            content="The Senior Backend Engineer will lead the core matchmaking engine using Python 3.12, FastAPI, PostgreSQL, SQLAlchemy 2.0, and pgvector semantic retrieval."
        )
        db.add_all([k1, k2, k3])
        db.flush()

        # 4. Create Requisition with Parsed Profile
        req = Requisition(
            org_id=org.id,
            created_by=recruiter.id,
            title="Senior Backend Engineer (Python / FastAPI)",
            jd_raw="""We are looking for a Senior Backend Engineer to architect and scale our real-time matching API.
Must-haves:
- 4+ years of Python with hands-on FastAPI in production.
- Production PostgreSQL query optimization and Alembic migrations.
- High-throughput asynchronous service architecture.
Nice-to-haves:
- Vector search with pgvector or hybrid search experience.
- Docker and cloud deployment.""",
            seniority="senior",
            location="Remote",
            status="active",
            parsed_profile={
                "role_title": "Senior Backend Engineer (Python / FastAPI)",
                "seniority": "senior",
                "must_have_skills": [
                    {"skill": "Python / FastAPI", "why_required": "Core API engine", "evidence_of": "Deployed async REST APIs"},
                    {"skill": "PostgreSQL & SQLAlchemy", "why_required": "Relational data modeling and migrations", "evidence_of": "Complex schema designs"},
                    {"skill": "System Architecture", "why_required": "Scalable service boundaries", "evidence_of": "High-throughput microservices or modular monoliths"}
                ],
                "nice_to_have_skills": [
                    {"skill": "pgvector / Vector Search", "why_required": "AI retrieval capabilities", "evidence_of": "Implemented semantic search"},
                    {"skill": "Docker / DevOps", "why_required": "Deployment automation", "evidence_of": "Containerized setups"}
                ],
                "domain_context": "B2B SaaS / Agentic Hiring Platform",
                "location_constraint": "Remote",
                "implicit_signals": ["High engineering autonomy", "Ownership of latency and reliability", "Strong async programming fundamentals"],
                "ambiguities": ["On-call rotation frequency"]
            }
        )
        db.add(req)
        db.flush()

        # 5. Populate 40 Synthetic Candidates spanning score bands
        for idx, (c_name, c_email, target_score, conf_level) in enumerate(SYNTHETIC_CANDIDATE_NAMES):
            cand = Candidate(
                org_id=org.id,
                full_name=c_name,
                email=c_email,
                phone=f"+1 555-01{idx:02d}",
                source="csv",
                public_urls=[f"https://github.com/{c_name.lower().replace(' ', '')}"],
                consent_status="granted",
                do_not_contact=False
            )
            db.add(cand)
            db.flush()

            # Research
            research = CandidateResearch(
                org_id=org.id,
                candidate_id=cand.id,
                summary="Software engineer with demonstrated background in backend development and distributed services.",
                skills=[
                    {"skill": "Python", "evidence_quote": "Core language for backend microservices", "source_url": cand.public_urls[0]},
                    {"skill": "FastAPI", "evidence_quote": "Built REST endpoints with Pydantic validation", "source_url": cand.public_urls[0]},
                    {"skill": "PostgreSQL", "evidence_quote": "Database schema management and optimization", "source_url": cand.public_urls[0]}
                ],
                seniority_signals=[
                    {"signal": "Production Ownership", "evidence_quote": "Maintained customer-facing APIs", "source_url": cand.public_urls[0]}
                ],
                projects=[
                    {"name": "AsyncGateway", "what_it_does": "Reverse proxy and rate limiting gateway", "evidence_quote": "Handled 10k req/s", "source_url": cand.public_urls[0]}
                ],
                evidence_urls=cand.public_urls,
                confidence=conf_level.lower(),
                could_not_determine=["Vector search experience with pgvector"] if target_score < 80 else []
            )
            db.add(research)
            db.flush()

            # Calculate individual rubric dimension scores to hit target_score
            # Weights: must_have 0.40, depth 0.25, domain 0.15, nice_to_have 0.10, trajectory 0.10
            base_dim = target_score
            breakdown = ScoreBreakdown(
                dimensions=[
                    DimensionScore(dimension="must_have_coverage", score=min(100, max(0, base_dim + 2)), justification="Evidence for core Python/FastAPI in public repo.", citations=cand.public_urls),
                    DimensionScore(dimension="depth_of_experience", score=min(100, max(0, base_dim - 2)), justification="Demonstrated production service ownership.", citations=cand.public_urls),
                    DimensionScore(dimension="domain_relevance", score=min(100, max(0, base_dim)), justification="Relevant B2B backend architecture.", citations=cand.public_urls),
                    DimensionScore(dimension="nice_to_have_bonus", score=min(100, max(0, base_dim - 5)), justification="Docker and automated testing evidenced.", citations=cand.public_urls),
                    DimensionScore(dimension="trajectory", score=min(100, max(0, base_dim + 3)), justification="Increasing scope and responsibility.", citations=cand.public_urls),
                ],
                could_not_determine=research.could_not_determine,
                confidence=conf_level.lower(),
                risk_flags=[]
            )
            computed_score, reason = compute_fit_score(breakdown)

            # Determine stage based on index
            stage = "scored"
            if idx < 3:
                stage = "replied"
            elif idx < 8:
                stage = "contacted"
            elif idx < 12:
                stage = "outreach_drafted"

            pe = PipelineEntry(
                org_id=org.id,
                requisition_id=req.id,
                candidate_id=cand.id,
                stage=stage,
                fit_score=computed_score,
                score_reason=reason,
                score_breakdown=breakdown.model_dump(),
                rubric_version=RUBRIC_VERSION,
                scored_at=utcnow()
            )
            db.add(pe)
            db.flush()

            # Feedback Report
            is_released = idx in (0, 6)  # Release for Alex Rivera and David Kim for demo portal
            fb = FeedbackReport(
                org_id=org.id,
                pipeline_entry_id=pe.id,
                fit_summary="For this Senior Backend Engineer role, the evaluation identified strong demonstrated capabilities in Python API development.",
                strengths=[
                    {"point": "Demonstrated production experience designing and deploying async REST services in Python/FastAPI.", "dimension": "must_have_coverage"}
                ],
                gaps=[
                    {"point": "For this role, we found no public evidence of direct pgvector or embedding index optimization.", "dimension": "nice_to_have_bonus", "why_it_mattered": "Important for advanced AI retrieval features in our platform."}
                ],
                improve_advice=[
                    "Document a project demonstrating vector similarity search or hybrid Postgres full-text indexing.",
                    "Publish benchmarks for async database queries under concurrency."
                ],
                score_snapshot=computed_score,
                released_at=utcnow() if is_released else None
            )
            db.add(fb)
            db.flush()

            # If released, issue credential hash record
            if is_released:
                import hashlib
                cred_hash = hashlib.sha256(f"report_{fb.id}_{computed_score}".encode()).hexdigest()
                cred_record = CredentialRecord(
                    org_id=org.id,
                    feedback_report_id=fb.id,
                    payload_hash=cred_hash,
                    tx_hash=f"0x{cred_hash[:40]}",
                    network="polygon-amoy",
                    revoked=False
                )
                db.add(cred_record)

            # Outreach messages & Replies for top candidates
            if idx < 8:
                msg_status = "sent" if idx < 3 else ("approved" if idx < 5 else "draft")
                outreach = OutreachMessage(
                    org_id=org.id,
                    pipeline_entry_id=pe.id,
                    channel="email",
                    subject="Senior Backend Engineer role — your work on AsyncGateway",
                    body=f"Hi {c_name.split()[0]}, I reviewed your work on the AsyncGateway repository and was impressed by your clean async FastAPI architecture. We are building TalentLoop and are looking for someone with your backend depth to lead our core engine. Would you be open to a 15-minute chat this Thursday?",
                    status=msg_status,
                    approved_by=recruiter.id if msg_status in ("approved", "sent") else None,
                    approved_at=utcnow() if msg_status in ("approved", "sent") else None,
                    sent_at=utcnow() if msg_status == "sent" else None,
                    gmail_message_id=f"msg_synth_{idx}" if msg_status == "sent" else None
                )
                db.add(outreach)
                db.flush()

                # Add real replies for sent messages
                if idx == 0:
                    reply1 = Reply(
                        org_id=org.id,
                        outreach_message_id=outreach.id,
                        raw_body="Hi! Thanks for reaching out. What is the compensation range and tech stack for this role?",
                        intent="salary_question",
                        sentiment="positive",
                        priority="high",
                        summary="Candidate asked about compensation band and tech stack.",
                        suggested_action="Provide verified $155k-$185k range and schedule intro call.",
                        response_draft={
                            "body": "Hi Alex, thanks for getting back to us! For the Senior Backend Engineer role, our base compensation range is $155,000 - $185,000 USD plus 0.15% equity. We use Python 3.12, FastAPI, and PostgreSQL with pgvector. Would Thursday at 2pm PT work for a quick introductory chat?",
                            "knowledge_used": [k1.id, k3.id],
                            "deferred_questions": []
                        },
                        received_at=utcnow()
                    )
                    db.add(reply1)
                elif idx == 1:
                    reply2 = Reply(
                        org_id=org.id,
                        outreach_message_id=outreach.id,
                        raw_body="Hello! I would love to chat. Thursday 3pm EST works great for me.",
                        intent="interested",
                        sentiment="positive",
                        priority="high",
                        summary="Candidate agreed to intro call on Thursday at 3pm EST.",
                        suggested_action="Send Google Meet invite for Thursday 3pm EST.",
                        response_draft={
                            "body": "Wonderful, Elena! I have scheduled a 15-minute introductory video call for Thursday at 3pm EST. Looking forward to speaking!",
                            "knowledge_used": [],
                            "deferred_questions": []
                        },
                        received_at=utcnow()
                    )
                    db.add(reply2)

        # 6. Audit Trail Initialization
        audit1 = AuditEvent(
            org_id=org.id,
            actor_id=recruiter.id,
            action="requisition_parsed",
            entity="requisition",
            entity_id=req.id,
            payload={"role_title": req.title, "must_haves_count": 3}
        )
        audit2 = AuditEvent(
            org_id=org.id,
            actor_id=recruiter.id,
            action="candidate_scored",
            entity="requisition",
            entity_id=req.id,
            payload={"candidates_scored": 40, "average_score": 58}
        )
        db.add_all([audit1, audit2])

        db.commit()
        print("✓ Successfully seeded 1 org, 1 recruiter, 2 candidate logins, 1 requisition, and 40 scored candidates!")
        print("  - Recruiter Login: demo@talentloop.dev / password123")
        print("  - Candidate Login: alex.rivera@synth.dev / password123")
        print("  - Candidate Login: david.kim@synth.dev / password123")

    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to seed demo data: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="TalentLoop Demo Seeder")
    parser.add_argument("--demo", action="store_true", help="Seed realistic demo data")
    parser.add_argument("--reset", action="store_true", help="Reset and truncate tables before seeding")
    args = parser.parse_args()

    seed_demo_data(reset=args.reset)


if __name__ == "__main__":
    main()
