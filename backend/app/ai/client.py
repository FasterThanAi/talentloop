import json
import logging
import os
import re
import time
from typing import Any, Dict, Optional, Type

import google.generativeai as genai
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("talentloop.ai")

_PROMPT_CACHE: dict[str, str] = {}


def ai_is_mocked() -> bool:
    """
    True when no real model is reachable and canned responses would be served.
    Surfaced at startup, on every AI response, and in /health — a demo must never be
    able to look real while running on mocks.
    """
    return not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "mock"


class AIResult(BaseModel):
    raw_text: str
    parsed: Any | None = None
    model: str
    prompt_name: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    mock: bool = False


def load_prompt_template(prompt_name: str) -> str:
    if prompt_name in _PROMPT_CACHE:
        return _PROMPT_CACHE[prompt_name]

    base_dir = os.path.dirname(__file__)
    prompt_path = os.path.join(base_dir, "prompts", f"{prompt_name}.md")
    if not os.path.exists(prompt_path):
        # Try direct name
        prompt_path = os.path.join(base_dir, "prompts", prompt_name)
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt template '{prompt_name}' not found at {prompt_path}")

    with open(prompt_path, encoding="utf-8") as f:
        template = f.read()

    _PROMPT_CACHE[prompt_name] = template
    return template


def render_prompt(template: str, variables: dict[str, Any]) -> str:
    content = template

    # Handle simple {{#each pages}} ... {{/each}} blocks
    each_pattern = re.compile(r"\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}", re.DOTALL)

    def replace_each(match: re.Match) -> str:
        key = match.group(1)
        body = match.group(2)
        items = variables.get(key, [])
        if not isinstance(items, list):
            return ""
        rendered_items = []
        for item in items:
            item_rendered = body
            if isinstance(item, dict):
                for sub_k, sub_v in item.items():
                    item_rendered = item_rendered.replace(f"{{{{{sub_k}}}}}", str(sub_v if sub_v is not None else ""))
            rendered_items.append(item_rendered)
        return "".join(rendered_items)

    content = each_pattern.sub(replace_each, content)

    # Handle standard {{key}} replacement
    for key, value in variables.items():
        if isinstance(value, (dict, list)):
            val_str = json.dumps(value, indent=2)
        else:
            val_str = str(value) if value is not None else ""
        content = content.replace(f"{{{{{key}}}}}", val_str)

    return content


def strip_markdown_fences(text: str) -> str:
    text = text.strip()
    # Match ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


class AIClient:
    def __init__(self):
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)

    async def generate(
        self,
        prompt_name: str,
        variables: dict[str, Any],
        *,
        temperature: float = 0.0,
        json_schema: type[BaseModel] | None = None
    ) -> AIResult:
        template = load_prompt_template(prompt_name)
        prompt_text = render_prompt(template, variables)

        # Version extracted from filename (e.g. jd_parse.v1 -> v1)
        version_match = re.search(r"\.v(\d+)", prompt_name)
        version = f"v{version_match.group(1)}" if version_match else "v1"

        start_time = time.time()
        raw_output = ""
        input_tokens = len(prompt_text.split())
        output_tokens = 0

        # If no GEMINI_API_KEY or offline testing mode, provide mock responses based on prompt
        mocked = ai_is_mocked()
        if mocked:
            logger.warning(
                "AI MOCK MODE: serving a canned response for '%s'. No Gemini call was made. "
                "Set GEMINI_API_KEY to run against the real model.",
                prompt_name,
            )
            raw_output = self._mock_generate(prompt_name, variables)
            output_tokens = len(raw_output.split())
        else:
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                generation_config={
                    "temperature": temperature,
                    "response_mime_type": "application/json" if json_schema else "text/plain"
                }
            )

            max_retries = 3
            backoff = 1.0
            last_error = None

            for attempt in range(max_retries):
                try:
                    response = model.generate_content(prompt_text)
                    raw_output = response.text or ""
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        input_tokens = getattr(response.usage_metadata, "prompt_token_count", input_tokens)
                        output_tokens = getattr(response.usage_metadata, "candidates_token_count", len(raw_output.split()))
                    break
                except Exception as e:
                    last_error = e
                    logger.warning(f"Gemini API attempt {attempt+1} failed: {e}. Retrying in {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2
            else:
                raise RuntimeError(f"Gemini API failed after {max_retries} attempts: {last_error}")

        latency_ms = int((time.time() - start_time) * 1000)
        clean_text = strip_markdown_fences(raw_output)

        logger.info(
            f"AI Call: model={settings.GEMINI_MODEL} prompt={prompt_name} version={version} "
            f"in_tokens={input_tokens} out_tokens={output_tokens} latency={latency_ms}ms"
        )

        return AIResult(
            raw_text=clean_text,
            model="MOCK" if mocked else settings.GEMINI_MODEL,
            prompt_name=prompt_name,
            prompt_version=version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            mock=mocked
        )

    async def embed(self, content: str) -> list[float] | None:
        """
        Generate an embedding vector for RAG. Returns None when no model is configured,
        so callers degrade to keyword search rather than storing a fake vector.
        """
        if ai_is_mocked():
            logger.warning("AI MOCK MODE: embedding requested but no model configured; returning None.")
            return None
        try:
            resp = genai.embed_content(
                model=f"models/{settings.EMBEDDING_MODEL}",
                content=content,
                task_type="retrieval_document",
            )
            vec = resp["embedding"] if isinstance(resp, dict) else resp.embedding
            return list(vec)
        except Exception as e:
            logger.warning("Embedding call failed: %s", e)
            return None

    def _mock_generate(self, prompt_name: str, variables: dict[str, Any]) -> str:
        """Deterministic mock generator for offline tests and evaluation harness."""
        if "jd_parse" in prompt_name:
            jd_raw = variables.get("jd_raw", "")
            title = "Backend Engineer"
            if "FastAPI" in jd_raw or "Python" in jd_raw:
                title = "Senior Backend Engineer (Python/FastAPI)"
            return json.dumps({
                "role_title": title,
                "seniority": "senior",
                "must_have_skills": [
                    {"skill": "Python / FastAPI", "why_required": "Core backend stack", "evidence_of": "Production APIs with automated tests and traffic"},
                    {"skill": "PostgreSQL & SQLAlchemy", "why_required": "Data persistence and queries", "evidence_of": "Schema designs and migration scripts"},
                    {"skill": "System Architecture", "why_required": "Scalable service boundaries", "evidence_of": "High-throughput microservices or monolithic modular designs"}
                ],
                "nice_to_have_skills": [
                    {"skill": "pgvector / Semantic Search", "why_required": "AI retrieval features", "evidence_of": "Implemented vector similarity search"},
                    {"skill": "Docker / Cloud Deployment", "why_required": "DevOps workflows", "evidence_of": "Containerized setups"}
                ],
                "domain_context": "B2B SaaS / Intelligent Recruiting Assistant",
                "location_constraint": "Remote",
                "implicit_signals": ["High autonomy required", "Strong ownership of reliability and latency", "Small agile team"],
                "ambiguities": ["Exact on-call expectation not specified in JD"]
            })

        if "enrich" in prompt_name:
            pages = variables.get("pages", [])
            primary_url = pages[0]["url"] if pages else "https://github.com/alexrivera"
            return json.dumps({
                "summary": "Full-stack engineer with demonstrable production Python, FastAPI, and data pipeline experience.",
                "skills": [
                    {"skill": "Python", "evidence_quote": "Lead developer for payments engine in Python 3.11", "source_url": primary_url},
                    {"skill": "FastAPI", "evidence_quote": "Built high-performance async REST API using FastAPI", "source_url": primary_url},
                    {"skill": "PostgreSQL", "evidence_quote": "Optimized SQL queries and managed schema migrations", "source_url": primary_url}
                ],
                "seniority_signals": [
                    {"signal": "Technical Ownership", "evidence_quote": "Architected payments service end-to-end", "source_url": primary_url}
                ],
                "projects": [
                    {"name": "AsyncPay", "what_it_does": "High-volume payment processor", "evidence_quote": "Processed 2M+ transactions monthly", "source_url": primary_url}
                ],
                "confidence": "high",
                "could_not_determine": ["Experience with pgvector semantic search"]
            })

        if "score" in prompt_name:
            evidence = variables.get("candidate_evidence", {})
            evidence_urls = []
            if isinstance(evidence, dict):
                for sk in evidence.get("skills", []):
                    if isinstance(sk, dict) and "source_url" in sk:
                        evidence_urls.append(sk["source_url"])
            if not evidence_urls:
                evidence_urls = ["https://github.com/candidate"]
            ref_url = evidence_urls[0]

            return json.dumps({
                "dimensions": [
                    {"dimension": "must_have_coverage", "score": 85, "justification": "Candidate has demonstrated solid Python and FastAPI production experience.", "citations": [ref_url]},
                    {"dimension": "depth_of_experience", "score": 80, "justification": "Built and maintained async payment service in production.", "citations": [ref_url]},
                    {"dimension": "domain_relevance", "score": 75, "justification": "Relevant B2B backend engineering background.", "citations": [ref_url]},
                    {"dimension": "nice_to_have_bonus", "score": 70, "justification": "Demonstrated containerization and testing skills.", "citations": [ref_url]},
                    {"dimension": "trajectory", "score": 85, "justification": "Progression into core architecture and system ownership.", "citations": [ref_url]}
                ],
                "could_not_determine": ["Direct experience with pgvector vector extensions"],
                "confidence": "high",
                "risk_flags": []
            })

        if "outreach" in prompt_name:
            return json.dumps({
                "subject": "Role: Backend Engineer — your work on AsyncPay",
                "body": "Hi there, I reviewed your work on the AsyncPay payments service and was impressed by your clean FastAPI architecture handling high-throughput transaction flows. We are building TalentLoop and are looking for someone with your depth in async Python and database design to lead our core engine. Would you be open to a 15-minute chat this Thursday?",
                "specific_reference_used": "AsyncPay payment processor"
            })

        if "reply" in prompt_name:
            reply_text = variables.get("reply_body", "").lower()
            intent = "interested"
            sentiment = "positive"
            priority = "high"
            summary = "Candidate expressed interest in learning more about the role."
            action = "Schedule introductory screening call."

            if "salary" in reply_text or "compensation" in reply_text or "range" in reply_text:
                intent = "salary_question"
                priority = "high"
                summary = "Candidate asked for the compensation range."
                action = "Provide confirmed salary band context."
            elif "not interested" in reply_text or "decline" in reply_text or "unsub" in reply_text:
                intent = "not_interested"
                sentiment = "neutral"
                priority = "low"
                summary = "Candidate politely declined the opportunity."
                action = "Acknowledge and mark pipeline entry closed."
            elif "out of office" in reply_text or "auto" in reply_text:
                intent = "auto_reply"
                sentiment = "neutral"
                priority = "low"
                summary = "Automated out of office response."
                action = "Follow up after return date."

            return json.dumps({
                "intent": intent,
                "sentiment": sentiment,
                "priority": priority,
                "summary": summary,
                "suggested_action": action
            })

        if "respond" in prompt_name:
            facts = variables.get("knowledge_chunks", "")
            if "salary" in variables.get("reply_body", "").lower() and ("$" not in facts and "salary" not in facts.lower()):
                return json.dumps({
                    "body": "Thank you for getting back to us. I will verify the exact compensation band with the hiring team and follow up with you by tomorrow.",
                    "knowledge_used": [],
                    "deferred_questions": ["Compensation range"]
                })
            return json.dumps({
                "body": "Thank you for your interest! We'd love to connect for a brief 15-minute chat to discuss the role and share more details about the team.",
                "knowledge_used": ["chunk-001"] if facts else [],
                "deferred_questions": []
            })

        if "feedback" in prompt_name:
            return json.dumps({
                "fit_summary": "For this Backend Engineer role, the evaluation identified strong demonstrated capabilities in Python API development and system architecture.",
                "strengths": [
                    {"point": "Demonstrated production experience designing and deploying async REST services in Python/FastAPI.", "dimension": "must_have_coverage"}
                ],
                "gaps": [
                    {"point": "For this role, we found no public evidence of direct pgvector or embedding index optimization.", "dimension": "nice_to_have_bonus", "why_it_mattered": "Important for advanced AI retrieval features in our platform."}
                ],
                "improve_advice": [
                    "Document a project demonstrating vector similarity search or hybrid Postgres full-text indexing.",
                    "Publish benchmark benchmarks for async database queries under concurrency."
                ]
            })

        if "interview" in prompt_name:
            return json.dumps({
                "questions": [
                    {"id": "q1", "question": "Can you describe a scenario where you had to debug an unexpected database bottleneck in production?", "targeting_gap": "production database debugging"},
                    {"id": "q2", "question": "What is your approach to handling graceful degradation in third-party API integrations?", "targeting_gap": "resilient service design"}
                ]
            })

        return "{}"


ai_client = AIClient()
