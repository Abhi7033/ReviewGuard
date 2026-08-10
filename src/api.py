import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from pydantic import BaseModel

from .graph import build_graph

_graph = None
_checkpointer_cm = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph, _checkpointer_cm
    _checkpointer_cm = SqliteSaver.from_conn_string("data/graph_checkpoints.db")
    checkpointer = _checkpointer_cm.__enter__()
    _graph = build_graph(checkpointer)
    yield
    _checkpointer_cm.__exit__(None, None, None)


app = FastAPI(title="ReviewGuard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReviewRequest(BaseModel):
    review: str


class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
def analyze(payload: ReviewRequest):
    """Run a review through the graph. Routine reviews return a final resolution directly.
    Severe reviews return status='pending_approval' - call /approve with the returned
    thread_id to resume."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    result = _graph.invoke(
        {
            "review_id": thread_id,
            "review": payload.review,
            "analysis": None,
            "draft_response": None,
            "status": "new",
            "approved": None,
        },
        config=config,
    )
    analysis = result["analysis"].model_dump() if result.get("analysis") else None
    if "__interrupt__" in result:
        return {
            "thread_id": thread_id,
            "status": "pending_approval",
            "draft_response": result["draft_response"],
            "analysis": analysis,
        }
    return {
        "thread_id": thread_id,
        "status": result["status"],
        "draft_response": result.get("draft_response"),
        "analysis": analysis,
    }


@app.post("/approve")
def approve(payload: ApprovalRequest):
    """Resume a paused thread with a human's approve/reject decision."""
    config = {"configurable": {"thread_id": payload.thread_id}}
    result = _graph.invoke(Command(resume=payload.approved), config=config)
    return {
        "thread_id": payload.thread_id,
        "status": result["status"],
        "draft_response": result.get("draft_response"),
        "analysis": result["analysis"].model_dump() if result.get("analysis") else None,
    }
