from fastapi import FastAPI, APIRouter, BackgroundTasks, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional
import uuid
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from agents import (
    requirement_analyzer,
    requirement_gatherer,
    erp_architect,
    json_transformer,
    frontend_generator,
    backend_generator,
    code_reviewer,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")


# --- Pydantic Models ---
class CreateProjectRequest(BaseModel):
    name: str
    prompt: str

class ChatRequest(BaseModel):
    message: str


# --- Helpers ---
def now_iso():
    return datetime.now(timezone.utc).isoformat()

def make_pipeline():
    stages = ["requirement_analysis", "requirement_gathering", "architecture",
              "json_transform", "frontend_generation", "backend_generation", "code_review"]
    return {s: {"status": "pending", "output": None} for s in stages}

async def save_message(project_id, role, content, agent=None):
    msg = {"id": str(uuid.uuid4()), "project_id": project_id, "role": role,
           "content": content, "agent": agent, "created_at": now_iso()}
    await db.messages.insert_one(msg)

async def get_messages(project_id):
    return await db.messages.find({"project_id": project_id}, {"_id": 0}).sort("created_at", 1).to_list(200)

async def update_pipeline(project_id, stage, status, output=None):
    update = {f"pipeline.{stage}.status": status, "updated_at": now_iso()}
    if output is not None:
        update[f"pipeline.{stage}.output"] = output
    await db.projects.update_one({"id": project_id}, {"$set": update})

async def update_status(project_id, status):
    await db.projects.update_one({"id": project_id}, {"$set": {"status": status, "updated_at": now_iso()}})


# --- Pipeline Logic ---
async def handle_init(project_id, prompt, background_tasks):
    await update_pipeline(project_id, "requirement_analysis", "running")
    await update_status(project_id, "ANALYZING")
    try:
        analysis = await requirement_analyzer(prompt)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        await update_pipeline(project_id, "requirement_analysis", "failed")
        await update_status(project_id, "INIT")
        err = "I had trouble analyzing your requirements. Could you try rephrasing?"
        await save_message(project_id, "assistant", err, agent="system")
        return {"response": err, "status": "INIT"}

    await update_pipeline(project_id, "requirement_analysis", "complete", analysis)
    await update_pipeline(project_id, "requirement_gathering", "running")
    await update_status(project_id, "GATHERING")

    messages = await get_messages(project_id)
    try:
        result = await requirement_gatherer(analysis, messages)
    except Exception as e:
        logger.error(f"Gatherer failed: {e}")
        result = {"complete": False, "question": "What specific features do you need most?", "current_module": "General"}

    # Handle unexpected formats
    if isinstance(result, list):
        result = result[0] if result and isinstance(result[0], dict) else {"complete": False, "question": "What features do you need?"}
    if not isinstance(result, dict):
        result = {"complete": False, "question": str(result), "current_module": "General"}

    if result.get("complete"):
        return await finish_gathering(project_id, result, background_tasks)

    modules = ", ".join(analysis.get("suggested_modules", []))
    summary = (
        f"I've analyzed your request and identified the following:\n\n"
        f"**Business Type:** {analysis.get('business_type', 'N/A')}\n"
        f"**Industry:** {analysis.get('industry', 'N/A')}\n"
        f"**Scale:** {analysis.get('scale', 'N/A')}\n"
        f"**Suggested Modules:** {modules}\n\n"
        f"Let me ask a few questions to refine the requirements.\n\n"
        f"{result.get('question', '')}"
    )
    await save_message(project_id, "assistant", summary, agent="requirement_gatherer")
    return {"response": summary, "status": "GATHERING", "analysis": analysis}


async def handle_gathering(project_id, project, background_tasks):
    analysis = project.get("pipeline", {}).get("requirement_analysis", {}).get("output", {})
    messages = await get_messages(project_id)
    try:
        result = await requirement_gatherer(analysis, messages)
    except Exception as e:
        logger.error(f"Gatherer failed: {e}")
        result = {"complete": False, "question": "Could you provide more details?", "current_module": "General"}

    # Handle unexpected formats
    if isinstance(result, list):
        result = result[0] if result and isinstance(result[0], dict) else {"complete": False, "question": "Could you provide more details?"}
    if not isinstance(result, dict):
        result = {"complete": False, "question": str(result), "current_module": "General"}

    if result.get("complete"):
        return await finish_gathering(project_id, result, background_tasks)

    question = result.get("question", "Could you tell me more?")
    await save_message(project_id, "assistant", question, agent="requirement_gatherer")
    return {"response": question, "status": "GATHERING",
            "current_module": result.get("current_module"), "progress": result.get("progress_summary")}


async def finish_gathering(project_id, result, background_tasks):
    requirements = result.get("requirements", {})
    await update_pipeline(project_id, "requirement_gathering", "complete", requirements)
    msg = "Requirements gathered successfully! Now designing your ERP system architecture. This may take a minute..."
    await save_message(project_id, "assistant", msg, agent="orchestrator")
    await update_status(project_id, "ARCHITECTING")
    background_tasks.add_task(run_auto_pipeline, project_id)
    return {"response": msg, "status": "ARCHITECTING", "requirements": requirements, "auto_advance": True}


async def handle_modification(project_id, message, project, background_tasks):
    requirements = project.get("pipeline", {}).get("requirement_gathering", {}).get("output", {})
    msg = f"Processing your modification. Regenerating affected components..."
    await save_message(project_id, "assistant", msg, agent="orchestrator")
    await update_status(project_id, "ARCHITECTING")
    for stage in ["architecture", "json_transform", "frontend_generation", "backend_generation", "code_review"]:
        await update_pipeline(project_id, stage, "pending", None)
    background_tasks.add_task(run_auto_pipeline, project_id, message)
    return {"response": msg, "status": "ARCHITECTING", "auto_advance": True}


async def run_auto_pipeline(project_id, modification=None):
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    requirements = project.get("pipeline", {}).get("requirement_gathering", {}).get("output", {})

    # Architecture
    try:
        await update_pipeline(project_id, "architecture", "running")
        architecture = await erp_architect(requirements, modification)
        await update_pipeline(project_id, "architecture", "complete", architecture)
        await save_message(project_id, "assistant", "ERP architecture designed successfully.", agent="erp_architect")
    except Exception as e:
        logger.error(f"Architecture failed: {e}")
        await update_pipeline(project_id, "architecture", "failed")
        await update_status(project_id, "ERROR")
        await save_message(project_id, "assistant", "Architecture generation failed. You can try modifying your request.", agent="system")
        return

    # JSON Transform
    try:
        await update_pipeline(project_id, "json_transform", "running")
        await update_status(project_id, "TRANSFORMING")
        master_json = await json_transformer(architecture)
        await update_pipeline(project_id, "json_transform", "complete", master_json)
    except Exception as e:
        logger.error(f"JSON transform failed: {e}")
        await update_pipeline(project_id, "json_transform", "failed")
        await update_status(project_id, "ERROR")
        return

    # Frontend Generation
    try:
        await update_pipeline(project_id, "frontend_generation", "running")
        await update_status(project_id, "GENERATING_FRONTEND")
        frontend_code = await frontend_generator(master_json)
        await update_pipeline(project_id, "frontend_generation", "complete", frontend_code)
        await save_message(project_id, "assistant", "Frontend code generated.", agent="frontend_generator")
    except Exception as e:
        logger.error(f"Frontend gen failed: {e}")
        await update_pipeline(project_id, "frontend_generation", "failed")
        await update_status(project_id, "ERROR")
        return

    # Backend Generation
    try:
        await update_pipeline(project_id, "backend_generation", "running")
        await update_status(project_id, "GENERATING_BACKEND")
        backend_code = await backend_generator(master_json)
        await update_pipeline(project_id, "backend_generation", "complete", backend_code)
        await save_message(project_id, "assistant", "Backend code generated.", agent="backend_generator")
    except Exception as e:
        logger.error(f"Backend gen failed: {e}")
        await update_pipeline(project_id, "backend_generation", "failed")
        await update_status(project_id, "ERROR")
        return

    # Code Review
    try:
        await update_pipeline(project_id, "code_review", "running")
        await update_status(project_id, "REVIEWING")
        review = await code_reviewer(frontend_code, backend_code)
        await update_pipeline(project_id, "code_review", "complete", review)
        await save_message(project_id, "assistant", "Code review complete.", agent="code_reviewer")
    except Exception as e:
        logger.error(f"Code review failed: {e}")
        await update_pipeline(project_id, "code_review", "failed")
        await update_status(project_id, "ERROR")
        return

    await update_status(project_id, "COMPLETE")
    score = review.get("overall_score", "N/A") if isinstance(review, dict) else "N/A"
    final_msg = (
        f"Your ERP system has been fully generated! Code review score: {score}/10.\n\n"
        f"Explore the architecture, database schema, API endpoints, and generated code in the preview panel. "
        f"You can ask me to modify any part of the system."
    )
    await save_message(project_id, "assistant", final_msg, agent="orchestrator")


# --- Routes ---
@api_router.get("/")
async def root():
    return {"message": "Zappizo API"}

@api_router.post("/projects")
async def create_project(req: CreateProjectRequest):
    project = {
        "id": str(uuid.uuid4()), "name": req.name, "prompt": req.prompt,
        "status": "INIT", "pipeline": make_pipeline(),
        "created_at": now_iso(), "updated_at": now_iso()
    }
    await db.projects.insert_one(project)
    project.pop("_id", None)
    return project

@api_router.get("/projects")
async def list_projects():
    # Exclude pipeline outputs for listing
    return await db.projects.find(
        {}, {"_id": 0, "pipeline.requirement_analysis.output": 0, "pipeline.requirement_gathering.output": 0,
             "pipeline.architecture.output": 0, "pipeline.json_transform.output": 0,
             "pipeline.frontend_generation.output": 0, "pipeline.backend_generation.output": 0,
             "pipeline.code_review.output": 0}
    ).sort("created_at", -1).to_list(100)

@api_router.get("/projects/{project_id}")
async def get_project(project_id: str):
    # Return project with pipeline statuses but without large outputs
    project = await db.projects.find_one(
        {"id": project_id},
        {"_id": 0, "pipeline.frontend_generation.output": 0, "pipeline.backend_generation.output": 0,
         "pipeline.json_transform.output": 0, "pipeline.code_review.output": 0}
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@api_router.get("/projects/{project_id}/pipeline/{stage}")
async def get_pipeline_stage(project_id: str, stage: str):
    valid_stages = ["requirement_analysis", "requirement_gathering", "architecture",
                    "json_transform", "frontend_generation", "backend_generation", "code_review"]
    if stage not in valid_stages:
        raise HTTPException(status_code=400, detail="Invalid stage")
    project = await db.projects.find_one({"id": project_id}, {"_id": 0, f"pipeline.{stage}": 1})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.get("pipeline", {}).get(stage, {"status": "pending", "output": None})

@api_router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    await db.projects.delete_one({"id": project_id})
    await db.messages.delete_many({"project_id": project_id})
    return {"status": "deleted"}

@api_router.get("/projects/{project_id}/messages")
async def get_project_messages(project_id: str):
    return await get_messages(project_id)

@api_router.post("/projects/{project_id}/chat")
async def chat(project_id: str, req: ChatRequest, background_tasks: BackgroundTasks):
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await save_message(project_id, "user", req.message)
    status = project["status"]
    if status == "INIT":
        return await handle_init(project_id, req.message, background_tasks)
    elif status == "GATHERING":
        return await handle_gathering(project_id, project, background_tasks)
    elif status == "COMPLETE":
        return await handle_modification(project_id, req.message, project, background_tasks)
    elif status == "ERROR":
        for stage in ["architecture", "json_transform", "frontend_generation", "backend_generation", "code_review"]:
            await update_pipeline(project_id, stage, "pending", None)
        await update_status(project_id, "ARCHITECTING")
        background_tasks.add_task(run_auto_pipeline, project_id, req.message)
        return {"response": "Retrying with your input...", "status": "ARCHITECTING", "auto_advance": True}
    else:
        return {"response": "System is processing. Please wait.", "status": status}


app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
