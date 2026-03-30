import os
import json
import logging
import requests
import asyncio
import re

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = [
    "openrouter/free",
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]


def _call_llm_sync(messages, temperature=0.7, max_tokens=4000):
    import time
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://zappizo.app",
        "X-Title": "Zappizo ERP Builder"
    }

    for model in MODELS:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        for attempt in range(3):
            try:
                resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
                if resp.status_code == 429:
                    wait = min(2 ** attempt * 3, 20)
                    logger.warning(f"Rate limited on {model}, waiting {wait}s (attempt {attempt+1})")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    if content:
                        return content
                if "error" in data:
                    logger.warning(f"API error on {model}: {data['error']}")
                    break
            except requests.exceptions.HTTPError as e:
                if "429" in str(e):
                    wait = min(2 ** attempt * 3, 20)
                    logger.warning(f"Rate limited on {model}, waiting {wait}s")
                    time.sleep(wait)
                    continue
                logger.warning(f"HTTP error on {model}: {e}")
                break
            except Exception as e:
                logger.warning(f"Error on {model}: {e}")
                if attempt < 2:
                    time.sleep(2)
                    continue
                break
        logger.info(f"Model {model} failed, trying next...")

    raise ValueError("All models failed")


async def call_llm(messages, temperature=0.7, max_tokens=4000):
    return await asyncio.to_thread(_call_llm_sync, messages, temperature, max_tokens)


def _extract_json(text):
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    json_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n```', text)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find('{')
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except json.JSONDecodeError:
                        break
    start = text.find('[')
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '[':
                depth += 1
            elif text[i] == ']':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i+1])
                    except json.JSONDecodeError:
                        break
    raise ValueError(f"Could not extract JSON from: {text[:300]}")


async def requirement_analyzer(prompt):
    system_prompt = """You are an ERP Requirement Analyzer. Analyze the user's business description and extract structured information.

Respond with ONLY valid JSON (no markdown, no explanation):
{
  "business_type": "type of business",
  "industry": "industry sector",
  "scale": "small|medium|large|enterprise",
  "suggested_modules": ["Module1", "Module2", "Module3"],
  "complexity": "basic|standard|advanced|enterprise",
  "key_requirements": ["req1", "req2"],
  "summary": "Brief 1-2 sentence summary"
}

Suggest 4-8 realistic ERP modules. Common modules: Inventory Management, Sales & Orders, Purchase Management, CRM, HR Management, Finance & Accounting, Production Planning, Quality Control, Warehouse Management, Supply Chain, Project Management, Asset Management, Payroll.

Output ONLY the JSON object."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]
    result = await call_llm(messages, temperature=0.3)
    return _extract_json(result)


async def requirement_gatherer(analysis, conversation_history):
    modules_list = ", ".join(analysis.get("suggested_modules", []))
    msg_count = len([m for m in conversation_history if m.get("role") == "user"])

    force_complete = ""
    if msg_count >= 4:
        force_complete = "\n\nIMPORTANT: You have already asked enough questions. You MUST now set complete=true and provide the full requirements document. Do NOT ask more questions."

    system_prompt = f"""You are an ERP Requirements Gathering Agent. You help build an ERP for a {analysis.get('business_type', 'business')} in {analysis.get('industry', 'general')}.

ANALYSIS:
- Business: {analysis.get('business_type')}
- Scale: {analysis.get('scale')}
- Modules: {modules_list}
- Requirements: {json.dumps(analysis.get('key_requirements', []))}

RULES:
1. Ask about ONE module at a time
2. Ask 1 clear question per turn
3. After 2-3 exchanges, compile all info and mark complete
4. Do NOT repeat already-answered questions{force_complete}

Respond with ONLY valid JSON in one of these formats:

If asking a question:
{{"complete": false, "question": "Your question?", "current_module": "Module Name", "progress_summary": "What you know so far"}}

If requirements are complete:
{{"complete": true, "requirements": {{"business_type": "{analysis.get('business_type')}", "industry": "{analysis.get('industry')}", "scale": "{analysis.get('scale')}", "modules": [{{"name": "Module", "description": "desc", "features": ["f1"], "entities": ["e1"], "workflows": ["w1"], "user_roles": ["r1"]}}], "general_requirements": {{"estimated_users": "number", "integrations": ["i1"], "special_needs": ["s1"]}}}}}}

Output ONLY JSON."""

    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history:
        if msg.get("role") in ["user", "assistant"]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    result = await call_llm(messages, temperature=0.4)
    logger.info(f"Gatherer raw response: {result[:500]}")
    try:
        parsed = _extract_json(result)
        if isinstance(parsed, list):
            parsed = parsed[0] if parsed and isinstance(parsed[0], dict) else {"complete": False, "question": result.strip()}
        return parsed
    except ValueError:
        return {"complete": False, "question": result.strip(), "current_module": "General", "progress_summary": "Gathering..."}


async def erp_architect(requirements, modification=None):
    mod_text = ""
    if modification:
        mod_text = f"\n\nMODIFICATION REQUEST: {modification}\nApply this change while keeping the rest intact."

    system_prompt = f"""You are an ERP System Architect. Design a complete ERP architecture from requirements.{mod_text}

Respond with ONLY valid JSON:
{{
  "system_name": "ERP System Name",
  "description": "Brief description",
  "modules": [
    {{
      "name": "Module Name",
      "description": "What it does",
      "icon": "lucide-icon-name",
      "features": ["feature1", "feature2"],
      "entities": [
        {{
          "name": "EntityName",
          "fields": [
            {{"name": "id", "type": "UUID", "required": true, "primary": true}},
            {{"name": "field", "type": "VARCHAR(255)", "required": true}}
          ]
        }}
      ],
      "api_endpoints": [
        {{"method": "GET", "path": "/api/module/resource", "description": "Description", "auth": true}}
      ],
      "workflows": [
        {{"name": "Workflow", "steps": ["step1", "step2"], "trigger": "event"}}
      ]
    }}
  ],
  "database_schema": {{
    "tables": [
      {{"name": "table_name", "module": "Module", "fields": [{{"name": "id", "type": "UUID", "constraints": "PRIMARY KEY"}}]}}
    ],
    "relationships": [
      {{"from_table": "t1", "to_table": "t2", "type": "one-to-many", "foreign_key": "t1_id"}}
    ]
  }},
  "user_roles": [{{"name": "Admin", "description": "Full access", "permissions": ["all"]}}],
  "tech_stack": {{"frontend": "React + Tailwind CSS", "backend": "FastAPI + Python", "database": "PostgreSQL", "auth": "JWT + RBAC"}}
}}

Design 4-8 modules with realistic entities, endpoints, workflows. Output ONLY JSON."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Requirements:\n{json.dumps(requirements, indent=2)}"}
    ]
    result = await call_llm(messages, temperature=0.3, max_tokens=4000)
    parsed = _extract_json(result)
    # Ensure proper architecture structure
    if isinstance(parsed, list):
        parsed = {"system_name": "ERP System", "description": "Generated ERP", "modules": parsed,
                  "database_schema": {"tables": [], "relationships": []},
                  "user_roles": [{"name": "Admin", "permissions": ["all"]}],
                  "tech_stack": {"frontend": "React", "backend": "FastAPI", "database": "PostgreSQL", "auth": "JWT"}}
    if "modules" not in parsed:
        parsed["modules"] = []
    if "database_schema" not in parsed:
        parsed["database_schema"] = {"tables": [], "relationships": []}
    if "user_roles" not in parsed:
        parsed["user_roles"] = []
    if "tech_stack" not in parsed:
        parsed["tech_stack"] = {"frontend": "React", "backend": "FastAPI", "database": "PostgreSQL"}
    # Normalize entities/endpoints
    for mod in parsed.get("modules", []):
        if mod.get("entities") and isinstance(mod["entities"], list) and mod["entities"] and isinstance(mod["entities"][0], str):
            mod["entities"] = [{"name": e, "fields": [{"name": "id", "type": "UUID", "required": True, "primary": True}]} for e in mod["entities"]]
        if not mod.get("api_endpoints"):
            slug = mod.get("name", "module").lower().replace(" ", "-").replace("&", "and")
            mod["api_endpoints"] = [
                {"method": "GET", "path": f"/api/{slug}", "description": f"List all"},
                {"method": "POST", "path": f"/api/{slug}", "description": f"Create new"},
                {"method": "GET", "path": f"/api/{slug}/{{id}}", "description": f"Get by ID"},
                {"method": "PUT", "path": f"/api/{slug}/{{id}}", "description": f"Update"},
                {"method": "DELETE", "path": f"/api/{slug}/{{id}}", "description": f"Delete"},
            ]
        if not mod.get("icon"):
            mod["icon"] = "package"
        if mod.get("workflows") and isinstance(mod["workflows"][0], str):
            mod["workflows"] = [{"name": w, "steps": [w], "trigger": "manual"} for w in mod["workflows"]]
    return parsed


async def json_transformer(architecture):
    system_prompt = """You are a JSON Schema Transformer. Convert ERP architecture into a strict master JSON.

Respond with ONLY valid JSON:
{
  "version": "1.0.0",
  "system": {"name": "...", "description": "...", "tech_stack": {}},
  "modules": [
    {
      "id": "module_slug",
      "name": "Module Name",
      "icon": "lucide-icon",
      "enabled": true,
      "entities": [],
      "endpoints": [],
      "workflows": [],
      "ui_components": [
        {"type": "dashboard|list|form|detail", "entity": "Entity", "fields": []}
      ]
    }
  ],
  "database": {"provider": "postgresql", "tables": [], "relationships": [], "indexes": []},
  "auth": {"method": "jwt", "roles": [], "permissions": {}},
  "config": {"pagination_default": 20, "date_format": "ISO8601", "currency": "USD"}
}

Validate all cross-references. Output ONLY JSON."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Architecture:\n{json.dumps(architecture, indent=2)}"}
    ]
    result = await call_llm(messages, temperature=0.2, max_tokens=4000)
    return _extract_json(result)


async def frontend_generator(master_json):
    system_prompt = """You are a Frontend Code Generator. Generate React + Tailwind components from the ERP JSON schema.

Respond with ONLY valid JSON:
{
  "files": [
    {"path": "src/App.jsx", "language": "jsx", "content": "// code here"},
    {"path": "src/pages/Dashboard.jsx", "language": "jsx", "content": "// code"},
    {"path": "src/components/Layout.jsx", "language": "jsx", "content": "// code"}
  ],
  "dependencies": {"react": "^18.0.0", "react-router-dom": "^6.0.0", "tailwindcss": "^3.0.0"}
}

Generate:
1. App.jsx with router and layout
2. Dashboard.jsx with module cards and stats  
3. One CRUD page for the primary module
4. Shared Layout with sidebar navigation

Use Tailwind CSS, lucide-react icons. Keep code concise but functional.
Output ONLY JSON."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Schema:\n{json.dumps(master_json, indent=2)}"}
    ]
    result = await call_llm(messages, temperature=0.3, max_tokens=4000)
    return _extract_json(result)


async def backend_generator(master_json):
    system_prompt = """You are a Backend Code Generator. Generate FastAPI + SQLAlchemy code from the ERP JSON schema.

Respond with ONLY valid JSON:
{
  "files": [
    {"path": "main.py", "language": "python", "content": "# code"},
    {"path": "models.py", "language": "python", "content": "# models"},
    {"path": "routes.py", "language": "python", "content": "# routes"},
    {"path": "auth.py", "language": "python", "content": "# auth"},
    {"path": "database.py", "language": "python", "content": "# db setup"}
  ],
  "dependencies": {"fastapi": ">=0.100.0", "sqlalchemy": ">=2.0.0", "pydantic": ">=2.0.0"}
}

Generate:
1. main.py - FastAPI app with CORS and middleware
2. models.py - SQLAlchemy models for key entities
3. routes.py - CRUD routes for primary module
4. auth.py - JWT authentication
5. database.py - DB connection

Include proper error handling. Output ONLY JSON."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Schema:\n{json.dumps(master_json, indent=2)}"}
    ]
    result = await call_llm(messages, temperature=0.3, max_tokens=4000)
    return _extract_json(result)


async def code_reviewer(frontend_code, backend_code):
    system_prompt = """You are a Code Reviewer. Review generated ERP code for quality and security.

Respond with ONLY valid JSON:
{
  "overall_score": 8.5,
  "summary": "Brief review summary",
  "frontend_review": {
    "score": 8.0,
    "issues": [{"severity": "warning|error|info", "file": "path", "description": "issue", "suggestion": "fix"}],
    "strengths": ["str1"]
  },
  "backend_review": {
    "score": 8.5,
    "issues": [],
    "strengths": ["str1"]
  },
  "security_checks": {
    "passed": ["check1"],
    "warnings": ["warn1"],
    "critical": []
  },
  "recommendations": ["rec1", "rec2"]
}

Be constructive and specific. Output ONLY JSON."""

    code_ctx = json.dumps({"frontend": frontend_code, "backend": backend_code}, indent=2)
    if len(code_ctx) > 6000:
        code_ctx = code_ctx[:6000] + "\n... (truncated)"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Code to review:\n{code_ctx}"}
    ]
    result = await call_llm(messages, temperature=0.3, max_tokens=3000)
    return _extract_json(result)
