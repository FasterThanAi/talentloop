import argparse
import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.audit import write_audit
from app.core.db import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    AuditEvent,
    Candidate,
    CandidateResearch,
    CredentialRecord,
    FeedbackReport,
    InterviewSession,
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


SHOWCASE_CANDIDATES = [
    {
        "name": "Alex Rivera",
        "email": "alex.rivera@synth.dev",
        "phone": "+1 555-0101",
        "public_urls": [
            "https://github.com/alexrivera/async-fastapi-gateway",
            "https://alexrivera.dev/architecture"
        ],
        "summary": "Senior backend architect specializing in async Python/FastAPI microservices, high-throughput distributed systems, and PostgreSQL performance tuning.",
        "skills": [
            {"skill": "Python / FastAPI", "evidence_quote": "Engineered async REST API handling 15k req/s with Pydantic validation", "source_url": "https://github.com/alexrivera/async-fastapi-gateway"},
            {"skill": "PostgreSQL & SQLAlchemy", "evidence_quote": "Designed partitioned schema and optimized indexed queries for sub-5ms retrieval", "source_url": "https://alexrivera.dev/architecture"},
            {"skill": "Distributed Systems", "evidence_quote": "Built Redis cache clusters and resilient Celery worker pipelines", "source_url": "https://alexrivera.dev/architecture"}
        ],
        "seniority_signals": [
            {"signal": "System Architecture", "evidence_quote": "Architected core payment & ingestion pipelines end-to-end", "source_url": "https://alexrivera.dev/architecture"}
        ],
        "projects": [
            {"name": "AsyncGateway", "what_it_does": "High-throughput API gateway with token-bucket rate limiting", "evidence_quote": "Processes 20M requests/day in production", "source_url": "https://github.com/alexrivera/async-fastapi-gateway"}
        ],
        "confidence": "high",
        "could_not_determine": [],
        "fit_score": 91,
        "score_reason": "Exceptional production async FastAPI architecture and high-throughput PostgreSQL experience with verifiable public code.",
        "dimensions": [
            {"dimension": "must_have_coverage", "score": 94, "justification": "Production async FastAPI architecture handling 15k req/s with strict Pydantic validation.", "citations": ["https://github.com/alexrivera/async-fastapi-gateway"]},
            {"dimension": "depth_of_experience", "score": 90, "justification": "Over 5 years architecting scalable distributed backend services and database partitioning.", "citations": ["https://alexrivera.dev/architecture"]},
            {"dimension": "domain_relevance", "score": 88, "justification": "Extensive experience in high-concurrency B2B API gateway platforms.", "citations": ["https://github.com/alexrivera/async-fastapi-gateway"]},
            {"dimension": "nice_to_have_bonus", "score": 90, "justification": "Demonstrated Docker orchestration and hybrid vector retrieval implementations.", "citations": ["https://alexrivera.dev/architecture"]},
            {"dimension": "trajectory", "score": 92, "justification": "Clear progression from backend engineer to lead distributed systems architect.", "citations": ["https://alexrivera.dev/architecture"]}
        ],
        "stage": "replied"
    },
    {
        "name": "Elena Rostova",
        "email": "elena.rostova@synth.dev",
        "phone": "+1 555-0102",
        "public_urls": [
            "https://github.com/erostova/microservices-platform",
            "https://erostova.tech/posts/pg-tuning"
        ],
        "summary": "Backend engineer with strong production Python, async event broker integrations, and relational database schema design experience.",
        "skills": [
            {"skill": "Python / FastAPI", "evidence_quote": "Developed REST APIs for telemetry aggregation in Python 3.12", "source_url": "https://github.com/erostova/microservices-platform"},
            {"skill": "PostgreSQL & SQLAlchemy", "evidence_quote": "Wrote custom Alembic migration scripts and optimized composite indexes", "source_url": "https://erostova.tech/posts/pg-tuning"},
            {"skill": "System Architecture", "evidence_quote": "Implemented decoupled messaging with RabbitMQ and background workers", "source_url": "https://github.com/erostova/microservices-platform"}
        ],
        "seniority_signals": [
            {"signal": "Technical Ownership", "evidence_quote": "Maintained core data synchronization services with 99.99% uptime", "source_url": "https://erostova.tech/posts/pg-tuning"}
        ],
        "projects": [
            {"name": "EventStream", "what_it_does": "Async event streaming broker for financial microservices", "evidence_quote": "Maintained 99.99% uptime under high concurrency", "source_url": "https://github.com/erostova/microservices-platform"}
        ],
        "confidence": "high",
        "could_not_determine": [],
        "fit_score": 86,
        "score_reason": "Strong hands-on Python/FastAPI and PostgreSQL experience with well-documented public repositories.",
        "dimensions": [
            {"dimension": "must_have_coverage", "score": 88, "justification": "Comprehensive FastAPI endpoints with automated test suites and async handlers.", "citations": ["https://github.com/erostova/microservices-platform"]},
            {"dimension": "depth_of_experience", "score": 85, "justification": "4+ years of backend microservice development and query tuning.", "citations": ["https://erostova.tech/posts/pg-tuning"]},
            {"dimension": "domain_relevance", "score": 86, "justification": "Directly relevant background in async service boundaries and event streaming.", "citations": ["https://github.com/erostova/microservices-platform"]},
            {"dimension": "nice_to_have_bonus", "score": 82, "justification": "Strong Docker containerization workflows evidenced.", "citations": ["https://github.com/erostova/microservices-platform"]},
            {"dimension": "trajectory", "score": 88, "justification": "Consistent technical contributions and increasing service scope.", "citations": ["https://erostova.tech/posts/pg-tuning"]}
        ],
        "stage": "contacted"
    },
    {
        "name": "Priya Sharma",
        "email": "priya.sharma@synth.dev",
        "phone": "+1 555-0103",
        "public_urls": [
            "https://github.com/psharma/data-pipeline-engine",
            "https://priyasharma.io"
        ],
        "summary": "Backend data engineer proficient in Python async pipelines, relational modeling in PostgreSQL, and automated CI/CD deployments.",
        "skills": [
            {"skill": "Python / FastAPI", "evidence_quote": "Built ingestion REST microservice using FastAPI and asyncio", "source_url": "https://github.com/psharma/data-pipeline-engine"},
            {"skill": "PostgreSQL & SQLAlchemy", "evidence_quote": "Designed relational schema and automated migrations via Alembic", "source_url": "https://priyasharma.io"},
            {"skill": "Docker / DevOps", "evidence_quote": "Configured multi-stage Docker builds and automated GitHub Actions CI", "source_url": "https://github.com/psharma/data-pipeline-engine"}
        ],
        "seniority_signals": [
            {"signal": "Pipeline Optimization", "evidence_quote": "Reduced ETL processing latency by 45% through concurrent batching", "source_url": "https://priyasharma.io"}
        ],
        "projects": [
            {"name": "PipelineCore", "what_it_does": "Automated data ETL and validation pipeline", "evidence_quote": "Reduced ETL processing time by 45%", "source_url": "https://github.com/psharma/data-pipeline-engine"}
        ],
        "confidence": "high",
        "could_not_determine": ["Direct pgvector semantic search implementation"],
        "fit_score": 82,
        "score_reason": "Solid Python data service engineering with strong PostgreSQL foundation and clean containerized deployments.",
        "dimensions": [
            {"dimension": "must_have_coverage", "score": 84, "justification": "Solid Python API design with async request handling.", "citations": ["https://github.com/psharma/data-pipeline-engine"]},
            {"dimension": "depth_of_experience", "score": 80, "justification": "Demonstrated async pipeline architecture and SQL data modeling.", "citations": ["https://priyasharma.io"]},
            {"dimension": "domain_relevance", "score": 82, "justification": "Good alignment with automated data ingestion workflows.", "citations": ["https://github.com/psharma/data-pipeline-engine"]},
            {"dimension": "nice_to_have_bonus", "score": 80, "justification": "Docker and CI/CD pipelines fully implemented.", "citations": ["https://github.com/psharma/data-pipeline-engine"]},
            {"dimension": "trajectory", "score": 84, "justification": "Active open source contributor with growing backend ownership.", "citations": ["https://priyasharma.io"]}
        ],
        "stage": "contacted"
    },
    {
        "name": "Marcus Vance",
        "email": "marcus.vance@synth.dev",
        "phone": "+1 555-0104",
        "public_urls": [
            "https://github.com/mvance/auth-service-fastapi",
            "https://mvance.dev"
        ],
        "summary": "Backend developer focused on API authentication, OAuth2 flows, and relational database integrations in Python.",
        "skills": [
            {"skill": "Python / FastAPI", "evidence_quote": "Developed authentication service with OAuth2 Bearer token verification", "source_url": "https://github.com/mvance/auth-service-fastapi"},
            {"skill": "PostgreSQL & SQLAlchemy", "evidence_quote": "Managed user credentials and tenant associations in PostgreSQL", "source_url": "https://mvance.dev"}
        ],
        "seniority_signals": [
            {"signal": "Security Ownership", "evidence_quote": "Auth service adopted across multiple internal development squads", "source_url": "https://github.com/mvance/auth-service-fastapi"}
        ],
        "projects": [
            {"name": "AuthMatrix", "what_it_does": "OAuth2 and JWT authentication provider service", "evidence_quote": "Used by 12 internal microservices", "source_url": "https://github.com/mvance/auth-service-fastapi"}
        ],
        "confidence": "medium",
        "could_not_determine": ["High-throughput asynchronous queuing experience", "pgvector vector search"],
        "fit_score": 75,
        "score_reason": "Good FastAPI authentication service experience; moderate evidence on high-throughput distributed queues.",
        "dimensions": [
            {"dimension": "must_have_coverage", "score": 76, "justification": "Demonstrated FastAPI and SQLAlchemy authentication services.", "citations": ["https://github.com/mvance/auth-service-fastapi"]},
            {"dimension": "depth_of_experience", "score": 74, "justification": "3 years of backend development with emphasis on security.", "citations": ["https://mvance.dev"]},
            {"dimension": "domain_relevance", "score": 75, "justification": "Identity and security infrastructure aligns well with SaaS requirements.", "citations": ["https://github.com/mvance/auth-service-fastapi"]},
            {"dimension": "nice_to_have_bonus", "score": 70, "justification": "Containerized auth service with Docker Compose.", "citations": ["https://github.com/mvance/auth-service-fastapi"]},
            {"dimension": "trajectory", "score": 76, "justification": "Consistent development output in backend Python ecosystem.", "citations": ["https://mvance.dev"]}
        ],
        "stage": "outreach_drafted"
    },
    {
        "name": "David Kim",
        "email": "david.kim@synth.dev",
        "phone": "+1 555-0105",
        "public_urls": [
            "https://github.com/dkim-dev/rest-api-template",
            "https://davidkim.me"
        ],
        "summary": "Full-stack engineer with practical experience developing RESTful APIs in Python and relational data schemas.",
        "skills": [
            {"skill": "Python / FastAPI", "evidence_quote": "Built starter template for REST APIs with FastAPI and Pydantic", "source_url": "https://github.com/dkim-dev/rest-api-template"},
            {"skill": "PostgreSQL", "evidence_quote": "Basic relational schema design and query execution", "source_url": "https://davidkim.me"}
        ],
        "seniority_signals": [
            {"signal": "Full-Stack Breadth", "evidence_quote": "Maintained end-to-end web apps with React frontend and Python backend", "source_url": "https://davidkim.me"}
        ],
        "projects": [
            {"name": "TaskSync", "what_it_does": "Background worker management tool", "evidence_quote": "Simple task orchestration queue", "source_url": "https://github.com/dkim-dev/rest-api-template"}
        ],
        "confidence": "medium",
        "could_not_determine": ["Complex query optimization", "High-throughput microservices architecture"],
        "fit_score": 68,
        "score_reason": "Competent mid-level developer with clean FastAPI code, though lacking extensive production high-throughput evidence.",
        "dimensions": [
            {"dimension": "must_have_coverage", "score": 70, "justification": "Standard FastAPI template structure with REST endpoints.", "citations": ["https://github.com/dkim-dev/rest-api-template"]},
            {"dimension": "depth_of_experience", "score": 66, "justification": "2-3 years building web applications and API services.", "citations": ["https://davidkim.me"]},
            {"dimension": "domain_relevance", "score": 68, "justification": "General web backend experience, less focused on distributed systems.", "citations": ["https://github.com/dkim-dev/rest-api-template"]},
            {"dimension": "nice_to_have_bonus", "score": 65, "justification": "Docker setup present for local development.", "citations": ["https://github.com/dkim-dev/rest-api-template"]},
            {"dimension": "trajectory", "score": 70, "justification": "Expanding skill set from general full-stack to dedicated backend.", "citations": ["https://davidkim.me"]}
        ],
        "stage": "scored"
    },
    {
        "name": "Maya Lin",
        "email": "maya.lin@synth.dev",
        "phone": "+1 555-0106",
        "public_urls": [
            "https://github.com/mayalin/portfolio-projects",
            "https://mayalin.dev"
        ],
        "summary": "Junior-to-mid software engineer with foundational Python knowledge and initial experience building web services.",
        "skills": [
            {"skill": "Python", "evidence_quote": "Scripted telemetry collection and API data polling scripts in Python", "source_url": "https://github.com/mayalin/portfolio-projects"},
            {"skill": "PostgreSQL", "evidence_quote": "Basic relational queries and database setup", "source_url": "https://mayalin.dev"}
        ],
        "seniority_signals": [
            {"signal": "Learning Agility", "evidence_quote": "Completed modular projects demonstrating REST API concepts", "source_url": "https://mayalin.dev"}
        ],
        "projects": [
            {"name": "MetricsCollector", "what_it_does": "Basic server health telemetry script", "evidence_quote": "Automated daily reporting", "source_url": "https://github.com/mayalin/portfolio-projects"}
        ],
        "confidence": "medium",
        "could_not_determine": ["Production async FastAPI architecture", "High concurrency query optimization", "Alembic migrations"],
        "fit_score": 58,
        "score_reason": "Foundational Python skills demonstrated, but limited evidence of senior-level production FastAPI architecture.",
        "dimensions": [
            {"dimension": "must_have_coverage", "score": 58, "justification": "Basic Python scripts and introductory REST API knowledge.", "citations": ["https://github.com/mayalin/portfolio-projects"]},
            {"dimension": "depth_of_experience", "score": 56, "justification": "Early career / junior-mid level scope of backend experience.", "citations": ["https://mayalin.dev"]},
            {"dimension": "domain_relevance", "score": 60, "justification": "General software engineering background.", "citations": ["https://github.com/mayalin/portfolio-projects"]},
            {"dimension": "nice_to_have_bonus", "score": 55, "justification": "Limited containerization or advanced vector search evidence.", "citations": ["https://mayalin.dev"]},
            {"dimension": "trajectory", "score": 62, "justification": "Demonstrates rapid skill acquisition and clear project documentation.", "citations": ["https://github.com/mayalin/portfolio-projects"]}
        ],
        "stage": "scored"
    }
]


def seed_showcase_data(db: Session | None = None) -> dict[str, Any]:
    """
    Idempotent showcase seeder that creates a clean, demo-ready state.
    MUST NOT call any AI provider (0 AI tokens used).
    Safe to run repeatedly against production databases.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # 1. Organization (Upsert)
        stmt_org = select(Organization).where(Organization.name == "Acme AI Technologies")
        org = db.execute(stmt_org).scalar_one_or_none()
        if not org:
            org = Organization(
                name="Acme AI Technologies",
                plan="enterprise"
            )
            db.add(org)
            db.flush()
            write_audit(
                db=db,
                org_id=org.id,
                actor_id="system",
                action="org_created",
                entity="organization",
                entity_id=org.id,
                payload={"name": org.name, "plan": org.plan}
            )
        else:
            org.plan = "enterprise"
            db.flush()

        # 2. Recruiter User (Upsert)
        stmt_rec = select(User).where(User.email == "demo@talentloop.dev")
        recruiter = db.execute(stmt_rec).scalar_one_or_none()
        if not recruiter:
            recruiter = User(
                org_id=org.id,
                email="demo@talentloop.dev",
                password_hash=hash_password("password123"),
                role="recruiter",
                gmail_email="demo@talentloop.dev"
            )
            db.add(recruiter)
            db.flush()
            write_audit(
                db=db,
                org_id=org.id,
                actor_id="system",
                action="user_created",
                entity="user",
                entity_id=recruiter.id,
                payload={"email": recruiter.email, "role": recruiter.role}
            )
        else:
            recruiter.org_id = org.id
            recruiter.role = "recruiter"
            recruiter.password_hash = hash_password("password123")
            db.flush()

        # Candidate User (Alex Rivera - for candidate portal demo)
        stmt_cand_user = select(User).where(User.email == "alex.rivera@synth.dev")
        cand_user = db.execute(stmt_cand_user).scalar_one_or_none()
        if not cand_user:
            cand_user = User(
                org_id=org.id,
                email="alex.rivera@synth.dev",
                password_hash=hash_password("password123"),
                role="candidate"
            )
            db.add(cand_user)
            db.flush()
            write_audit(
                db=db,
                org_id=org.id,
                actor_id=recruiter.id,
                action="user_created",
                entity="user",
                entity_id=cand_user.id,
                payload={"email": cand_user.email, "role": cand_user.role}
            )
        else:
            cand_user.org_id = org.id
            cand_user.password_hash = hash_password("password123")
            cand_user.role = "candidate"
            db.flush()

        # 3. Knowledge Chunks
        kb_specs = [
            ("salary_bands", "Senior Backend Engineer base compensation is $155,000 - $185,000 USD plus 0.15% equity grant, 401(k) matching up to 4%, and comprehensive health/dental coverage."),
            ("company_policy", "TalentLoop is a remote-first organization with flexible working hours across US, Canada, and European timezones. We provide a $2,500 home office setup stipend."),
            ("role_context", "The Senior Backend Engineer will lead the core matchmaking engine using Python 3.12, FastAPI, PostgreSQL, SQLAlchemy 2.0, and pgvector semantic retrieval.")
        ]
        created_chunks = []
        for src_type, content in kb_specs:
            stmt_k = select(KnowledgeChunk).where(KnowledgeChunk.org_id == org.id, KnowledgeChunk.source_type == src_type)
            chunk = db.execute(stmt_k).scalar_one_or_none()
            if not chunk:
                chunk = KnowledgeChunk(org_id=org.id, source_type=src_type, content=content)
                db.add(chunk)
                db.flush()
                write_audit(
                    db=db,
                    org_id=org.id,
                    actor_id=recruiter.id,
                    action="knowledge_chunk_created",
                    entity="knowledge_chunk",
                    entity_id=chunk.id,
                    payload={"source_type": src_type}
                )
            else:
                chunk.content = content
                db.flush()
            created_chunks.append(chunk)

        # 4. Requisition (Upsert in parsed status)
        req_title = "Senior Backend Engineer (Python / FastAPI)"
        stmt_req = select(Requisition).where(Requisition.org_id == org.id, Requisition.title == req_title)
        req = db.execute(stmt_req).scalar_one_or_none()
        parsed_profile = {
            "role_title": req_title,
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
        jd_raw = """We are looking for a Senior Backend Engineer to architect and scale our real-time matching API.
Must-haves:
- 4+ years of Python with hands-on FastAPI in production.
- Production PostgreSQL query optimization and Alembic migrations.
- High-throughput asynchronous service architecture.
Nice-to-haves:
- Vector search with pgvector or hybrid search experience.
- Docker and cloud deployment."""

        if not req:
            req = Requisition(
                org_id=org.id,
                created_by=recruiter.id,
                title=req_title,
                jd_raw=jd_raw,
                seniority="senior",
                location="Remote",
                status="parsed",
                parsed_profile=parsed_profile
            )
            db.add(req)
            db.flush()
            write_audit(
                db=db,
                org_id=org.id,
                actor_id=recruiter.id,
                action="requisition_parsed",
                entity="requisition",
                entity_id=req.id,
                payload={"role_title": req.title, "status": req.status}
            )
        else:
            req.status = "parsed"
            req.seniority = "senior"
            req.location = "Remote"
            req.parsed_profile = parsed_profile
            req.jd_raw = jd_raw
            db.flush()
            write_audit(
                db=db,
                org_id=org.id,
                actor_id=recruiter.id,
                action="requisition_updated",
                entity="requisition",
                entity_id=req.id,
                payload={"role_title": req.title, "status": req.status}
            )

        # 5. Populate 6 Showcase Candidates & Pipeline
        seeded_pes = []
        for cand_data in SHOWCASE_CANDIDATES:
            stmt_cand = select(Candidate).where(Candidate.org_id == org.id, Candidate.email == cand_data["email"])
            cand = db.execute(stmt_cand).scalar_one_or_none()
            if not cand:
                cand = Candidate(
                    org_id=org.id,
                    full_name=cand_data["name"],
                    email=cand_data["email"],
                    phone=cand_data["phone"],
                    source="csv",
                    public_urls=cand_data["public_urls"],
                    consent_status="granted",
                    do_not_contact=False
                )
                db.add(cand)
                db.flush()
                write_audit(
                    db=db,
                    org_id=org.id,
                    actor_id=recruiter.id,
                    action="candidate_created",
                    entity="candidate",
                    entity_id=cand.id,
                    payload={"full_name": cand.full_name, "email": cand.email}
                )
            else:
                cand.full_name = cand_data["name"]
                cand.phone = cand_data["phone"]
                cand.public_urls = cand_data["public_urls"]
                cand.do_not_contact = False
                db.flush()

            # Research
            stmt_res = select(CandidateResearch).where(CandidateResearch.candidate_id == cand.id)
            research = db.execute(stmt_res).scalar_one_or_none()
            if not research:
                research = CandidateResearch(
                    org_id=org.id,
                    candidate_id=cand.id,
                    summary=cand_data["summary"],
                    skills=cand_data["skills"],
                    seniority_signals=cand_data["seniority_signals"],
                    projects=cand_data["projects"],
                    evidence_urls=cand_data["public_urls"],
                    confidence=cand_data["confidence"],
                    could_not_determine=cand_data["could_not_determine"]
                )
                db.add(research)
                db.flush()
                write_audit(
                    db=db,
                    org_id=org.id,
                    actor_id=recruiter.id,
                    action="candidate_enriched",
                    entity="candidate_research",
                    entity_id=research.id,
                    payload={"confidence": research.confidence}
                )
            else:
                research.summary = cand_data["summary"]
                research.skills = cand_data["skills"]
                research.seniority_signals = cand_data["seniority_signals"]
                research.projects = cand_data["projects"]
                research.evidence_urls = cand_data["public_urls"]
                research.confidence = cand_data["confidence"]
                research.could_not_determine = cand_data["could_not_determine"]
                db.flush()

            # Pipeline Entry
            stmt_pe = select(PipelineEntry).where(
                PipelineEntry.requisition_id == req.id,
                PipelineEntry.candidate_id == cand.id
            )
            pe = db.execute(stmt_pe).scalar_one_or_none()
            breakdown_dict = {
                "dimensions": cand_data["dimensions"],
                "could_not_determine": cand_data["could_not_determine"],
                "confidence": cand_data["confidence"],
                "risk_flags": []
            }
            if not pe:
                pe = PipelineEntry(
                    org_id=org.id,
                    requisition_id=req.id,
                    candidate_id=cand.id,
                    stage=cand_data["stage"],
                    fit_score=cand_data["fit_score"],
                    score_reason=cand_data["score_reason"],
                    score_breakdown=breakdown_dict,
                    rubric_version=RUBRIC_VERSION,
                    scored_at=utcnow()
                )
                db.add(pe)
                db.flush()
                write_audit(
                    db=db,
                    org_id=org.id,
                    actor_id=recruiter.id,
                    action="candidate_scored",
                    entity="pipeline_entry",
                    entity_id=pe.id,
                    payload={"fit_score": pe.fit_score, "stage": pe.stage}
                )
            else:
                pe.stage = cand_data["stage"]
                pe.fit_score = cand_data["fit_score"]
                pe.score_reason = cand_data["score_reason"]
                pe.score_breakdown = breakdown_dict
                pe.rubric_version = RUBRIC_VERSION
                pe.scored_at = utcnow()
                db.flush()
                write_audit(
                    db=db,
                    org_id=org.id,
                    actor_id=recruiter.id,
                    action="candidate_scored",
                    entity="pipeline_entry",
                    entity_id=pe.id,
                    payload={"fit_score": pe.fit_score, "stage": pe.stage}
                )
            seeded_pes.append((cand_data, pe))

        # 6. Outreach Messages
        # 1 Sent message (Alex Rivera)
        alex_pe = seeded_pes[0][1]
        stmt_out_sent = select(OutreachMessage).where(OutreachMessage.pipeline_entry_id == alex_pe.id)
        out_sent = db.execute(stmt_out_sent).scalar_one_or_none()
        if not out_sent:
            out_sent = OutreachMessage(
                org_id=org.id,
                pipeline_entry_id=alex_pe.id,
                channel="email",
                subject="Senior Backend Engineer role — your work on AsyncGateway",
                body="Hi Alex, I came across your AsyncGateway repository and was really impressed by how you structured the token-bucket rate limiting and async FastAPI architecture. We are building TalentLoop and are looking for someone with your backend depth to lead our core engine. Would you be open to a 15-minute introductory chat this week?",
                status="sent",
                approved_by=recruiter.id,
                approved_at=utcnow(),
                sent_at=utcnow(),
                gmail_message_id="msg_showcase_alex_sent"
            )
            db.add(out_sent)
            db.flush()
            write_audit(
                db=db,
                org_id=org.id,
                actor_id=recruiter.id,
                action="outreach_sent",
                entity="outreach_message",
                entity_id=out_sent.id,
                payload={"status": "sent"}
            )
        else:
            out_sent.status = "sent"
            out_sent.approved_by = recruiter.id
            out_sent.approved_at = utcnow()
            out_sent.sent_at = utcnow()
            db.flush()

        # Candidate reply for Alex Rivera
        stmt_rep = select(Reply).where(Reply.outreach_message_id == out_sent.id)
        reply = db.execute(stmt_rep).scalar_one_or_none()
        if not reply:
            reply = Reply(
                org_id=org.id,
                outreach_message_id=out_sent.id,
                raw_body="Hi! Thanks for reaching out. What is the compensation range and tech stack for this role?",
                intent="salary_question",
                sentiment="positive",
                priority="high",
                summary="Candidate inquired about compensation range and tech stack.",
                suggested_action="Provide verified $155k-$185k compensation range and schedule intro call.",
                response_draft={
                    "body": "Hi Alex, thanks for getting back to us! For the Senior Backend Engineer role, our base compensation range is $155,000 - $185,000 USD plus 0.15% equity. We use Python 3.12, FastAPI, and PostgreSQL with pgvector. Would Thursday at 2pm PT work for a quick introductory chat?",
                    "knowledge_used": [created_chunks[0].id, created_chunks[2].id],
                    "deferred_questions": []
                },
                received_at=utcnow()
            )
            db.add(reply)
            db.flush()
            write_audit(
                db=db,
                org_id=org.id,
                actor_id="system",
                action="reply_classified",
                entity="reply",
                entity_id=reply.id,
                payload={"intent": reply.intent}
            )

        # 1 Draft message (Marcus Vance - 4th candidate)
        marcus_pe = seeded_pes[3][1]
        stmt_out_draft = select(OutreachMessage).where(OutreachMessage.pipeline_entry_id == marcus_pe.id)
        out_draft = db.execute(stmt_out_draft).scalar_one_or_none()
        if not out_draft:
            out_draft = OutreachMessage(
                org_id=org.id,
                pipeline_entry_id=marcus_pe.id,
                channel="email",
                subject="Senior Backend Engineer role — your AuthMatrix microservice",
                body="Hi Marcus, I reviewed your AuthMatrix repository and noticed your clean implementation of JWT authorization and OAuth2 flows in FastAPI. We're scaling out our engineering team at TalentLoop and would love to discuss our backend architect opening with you.",
                status="draft",
                approved_by=None,
                approved_at=None,
                sent_at=None
            )
            db.add(out_draft)
            db.flush()
            write_audit(
                db=db,
                org_id=org.id,
                actor_id=recruiter.id,
                action="outreach_drafted",
                entity="outreach_message",
                entity_id=out_draft.id,
                payload={"status": "draft"}
            )
        else:
            out_draft.status = "draft"
            out_draft.approved_by = None
            out_draft.approved_at = None
            out_draft.sent_at = None
            db.flush()

        # 7. Released Feedback Report for Alex Rivera
        stmt_fb = select(FeedbackReport).where(FeedbackReport.pipeline_entry_id == alex_pe.id)
        fb = db.execute(stmt_fb).scalar_one_or_none()
        if not fb:
            fb = FeedbackReport(
                org_id=org.id,
                pipeline_entry_id=alex_pe.id,
                fit_summary="For this Senior Backend Engineer role, the evaluation identified exceptional demonstrated capabilities in async Python/FastAPI architecture and distributed system scaling.",
                strengths=[
                    {"point": "Demonstrated production experience designing and deploying async REST services in Python/FastAPI.", "dimension": "must_have_coverage"},
                    {"point": "Proven track record architecting high-throughput distributed architectures and database partitioning.", "dimension": "depth_of_experience"}
                ],
                gaps=[
                    {"point": "We found limited direct evidence of specialized pgvector index optimization at massive scale.", "dimension": "nice_to_have_bonus", "why_it_mattered": "Useful for extending AI retrieval features in our platform."}
                ],
                improve_advice=[
                    "Publish benchmarks on hybrid PostgreSQL full-text and vector indexing.",
                    "Document async query connection pooling strategies under extreme load."
                ],
                score_snapshot=91,
                released_at=utcnow()
            )
            db.add(fb)
            db.flush()
            write_audit(
                db=db,
                org_id=org.id,
                actor_id=recruiter.id,
                action="feedback_released",
                entity="feedback_report",
                entity_id=fb.id,
                payload={"score_snapshot": fb.score_snapshot, "released": True}
            )
        else:
            fb.score_snapshot = 91
            fb.released_at = utcnow()
            db.flush()

        # Credential Record for released feedback
        stmt_cred = select(CredentialRecord).where(CredentialRecord.feedback_report_id == fb.id)
        cred = db.execute(stmt_cred).scalar_one_or_none()
        if not cred:
            cred_hash = hashlib.sha256(f"report_{fb.id}_{fb.score_snapshot}".encode()).hexdigest()
            cred = CredentialRecord(
                org_id=org.id,
                feedback_report_id=fb.id,
                payload_hash=cred_hash,
                tx_hash=f"0x{cred_hash[:40]}",
                network="polygon-amoy",
                revoked=False
            )
            db.add(cred)
            db.flush()
            write_audit(
                db=db,
                org_id=org.id,
                actor_id="system",
                action="credential_issued",
                entity="credential_record",
                entity_id=cred.id,
                payload={"payload_hash": cred_hash}
            )

        db.commit()

        print("\n" + "=" * 70)
        print("TALENTLOOP SHOWCASE SEED COMPLETED (0 AI Calls Used)")
        print("=" * 70)
        print(f"  - Organization:    {org.name} ({org.plan})")
        print(f"  - Requisition:     {req.title} [Status: {req.status}]")
        print("  - Candidates (6):  Alex Rivera (91), Elena Rostova (86), Priya Sharma (82),")
        print("                     Marcus Vance (75), David Kim (68), Maya Lin (58)")
        print("  - Outreach:        1 Sent (Alex Rivera), 1 Draft (Marcus Vance)")
        print("  - Inbound Reply:   1 Verified salary inquiry & grounded draft response")
        print("  - Feedback Report: 1 Released report & verifiable credential (Alex Rivera)")
        print("-" * 70)
        print("Demo Login Credentials:")
        print("  - Recruiter Portal: demo@talentloop.dev / password123")
        print("  - Candidate Portal: alex.rivera@synth.dev / password123")
        print("=" * 70 + "\n")

        return {
            "organization_id": org.id,
            "requisition_id": req.id,
            "candidates_seeded": len(SHOWCASE_CANDIDATES),
            "recruiter_email": recruiter.email,
            "candidate_email": cand_user.email
        }

    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to seed showcase data: {e}")
        raise
    finally:
        if close_db:
            db.close()


def purge_placeholders(confirm: bool = False, db: Session | None = None) -> dict[str, int]:
    """
    Finds and deletes placeholder candidates ending in @sourced.talentloop.local
    along with their associated pipeline entries, research, outreach, replies, and feedback.
    Defaults to DRY-RUN mode. Requires confirm=True to execute.
    Audit log rows are strictly preserved.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        stmt = select(Candidate).where(Candidate.email.endswith("@sourced.talentloop.local"))
        placeholder_cands = db.execute(stmt).scalars().all()
        cand_ids = [c.id for c in placeholder_cands]

        if not cand_ids:
            print("\n✓ No placeholder candidates ending in @sourced.talentloop.local found.")
            return {
                "candidates": 0,
                "research": 0,
                "pipeline_entries": 0,
                "outreach": 0,
                "replies": 0,
                "feedback": 0,
                "credentials": 0,
                "interviews": 0,
            }

        # Find associated pipeline entries
        stmt_pe = select(PipelineEntry).where(PipelineEntry.candidate_id.in_(cand_ids))
        pes = db.execute(stmt_pe).scalars().all()
        pe_ids = [p.id for p in pes]

        # Find associated research
        stmt_res = select(CandidateResearch).where(CandidateResearch.candidate_id.in_(cand_ids))
        res_rows = db.execute(stmt_res).scalars().all()

        # Find outreach messages
        if pe_ids:
            stmt_out = select(OutreachMessage).where(OutreachMessage.pipeline_entry_id.in_(pe_ids))
            outreach_rows = db.execute(stmt_out).scalars().all()
        else:
            outreach_rows = []
        outreach_ids = [o.id for o in outreach_rows]

        # Find replies
        if outreach_ids:
            stmt_rep = select(Reply).where(Reply.outreach_message_id.in_(outreach_ids))
            reply_rows = db.execute(stmt_rep).scalars().all()
        else:
            reply_rows = []

        # Find feedback reports
        if pe_ids:
            stmt_fb = select(FeedbackReport).where(FeedbackReport.pipeline_entry_id.in_(pe_ids))
            fb_rows = db.execute(stmt_fb).scalars().all()
        else:
            fb_rows = []
        fb_ids = [f.id for f in fb_rows]

        # Find credential records
        if fb_ids:
            stmt_cred = select(CredentialRecord).where(CredentialRecord.feedback_report_id.in_(fb_ids))
            cred_rows = db.execute(stmt_cred).scalars().all()
        else:
            cred_rows = []

        # Find interview sessions
        if pe_ids:
            stmt_int = select(InterviewSession).where(InterviewSession.pipeline_entry_id.in_(pe_ids))
            int_rows = db.execute(stmt_int).scalars().all()
        else:
            int_rows = []

        counts = {
            "candidates": len(placeholder_cands),
            "research": len(res_rows),
            "pipeline_entries": len(pes),
            "outreach": len(outreach_rows),
            "replies": len(reply_rows),
            "feedback": len(fb_rows),
            "credentials": len(cred_rows),
            "interviews": len(int_rows),
        }

        if not confirm:
            print("\n" + "=" * 70)
            print("[DRY RUN] Found placeholder candidates ending in @sourced.talentloop.local:")
            print("=" * 70)
            for c in placeholder_cands:
                print(f"  - {c.full_name} ({c.email}) [ID: {c.id}]")
            print("-" * 70)
            print("Summary of records that WOULD be deleted:")
            print(f"  - Candidates:         {counts['candidates']}")
            print(f"  - Candidate Research: {counts['research']}")
            print(f"  - Pipeline Entries:   {counts['pipeline_entries']}")
            print(f"  - Outreach Messages:  {counts['outreach']}")
            print(f"  - Candidate Replies:  {counts['replies']}")
            print(f"  - Feedback Reports:   {counts['feedback']}")
            print(f"  - Credentials:        {counts['credentials']}")
            print(f"  - Interview Sessions: {counts['interviews']}")
            print("\nNOTE: Audit log entries will be PRESERVED.")
            print("To permanently delete these records, run with --confirm:")
            print("  python -m app.seed --purge-placeholders --confirm")
            print("=" * 70 + "\n")
            return counts

        # Execute deletion inside transaction
        if cred_rows:
            db.execute(delete(CredentialRecord).where(CredentialRecord.feedback_report_id.in_(fb_ids)))
        if fb_rows:
            db.execute(delete(FeedbackReport).where(FeedbackReport.pipeline_entry_id.in_(pe_ids)))
        if reply_rows:
            db.execute(delete(Reply).where(Reply.outreach_message_id.in_(outreach_ids)))
        if outreach_rows:
            db.execute(delete(OutreachMessage).where(OutreachMessage.pipeline_entry_id.in_(pe_ids)))
        if int_rows:
            db.execute(delete(InterviewSession).where(InterviewSession.pipeline_entry_id.in_(pe_ids)))
        if pes:
            db.execute(delete(PipelineEntry).where(PipelineEntry.candidate_id.in_(cand_ids)))
        if res_rows:
            db.execute(delete(CandidateResearch).where(CandidateResearch.candidate_id.in_(cand_ids)))
        db.execute(delete(Candidate).where(Candidate.id.in_(cand_ids)))

        db.commit()

        print("\n" + "=" * 70)
        print("✓ PURGE COMPLETED: Permanently deleted placeholder data:")
        print("=" * 70)
        print(f"  - Deleted {counts['candidates']} candidates")
        print(f"  - Deleted {counts['research']} candidate research records")
        print(f"  - Deleted {counts['pipeline_entries']} pipeline entries")
        print(f"  - Deleted {counts['outreach']} outreach messages")
        print(f"  - Deleted {counts['replies']} replies")
        print(f"  - Deleted {counts['feedback']} feedback reports")
        print(f"  - Deleted {counts['credentials']} credential records")
        print(f"  - Deleted {counts['interviews']} interview sessions")
        print("  - Audit logs: PRESERVED (0 audit logs deleted)")
        print("=" * 70 + "\n")
        return counts

    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to purge placeholder data: {e}")
        raise
    finally:
        if close_db:
            db.close()


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
    parser = argparse.ArgumentParser(description="TalentLoop Demo & Showcase Seeder CLI")
    parser.add_argument("--demo", action="store_true", help="Seed full 40-candidate synthetic dataset")
    parser.add_argument("--showcase", action="store_true", help="Seed clean, demo-ready 6-candidate showcase dataset (0 AI calls)")
    parser.add_argument("--purge-placeholders", action="store_true", help="Purge candidates with @sourced.talentloop.local emails (dry-run by default)")
    parser.add_argument("--confirm", action="store_true", help="Confirm destructive purge operation")
    parser.add_argument("--reset", action="store_true", help="Reset and truncate tables before seeding")
    args = parser.parse_args()

    if args.purge_placeholders:
        purge_placeholders(confirm=args.confirm)
    elif args.showcase:
        seed_showcase_data()
    else:
        seed_demo_data(reset=args.reset)


if __name__ == "__main__":
    main()
