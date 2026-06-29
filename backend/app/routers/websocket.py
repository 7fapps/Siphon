import asyncio
import json
import logging
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from celery.result import AsyncResult

from app.celery_app import celery_app, JOB_STATES
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["websocket"])
settings = get_settings()

class ConnectionManager:
    """Manages WebSocket connections grouped by job_id."""
    
    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._polling_tasks: Dict[str, asyncio.Task] = {}
    
    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self._connections:
            self._connections[job_id] = set()
            # Start background poller for this job
            self._polling_tasks[job_id] = asyncio.create_task(self._poll_job(job_id))
        self._connections[job_id].add(websocket)
        logger.info(f"[ws] Client connected to job {job_id}. Total: {len(self._connections[job_id])}")
    
    async def disconnect(self, job_id: str, websocket: WebSocket):
        self._connections[job_id].discard(websocket)
        if not self._connections[job_id]:
            del self._connections[job_id]
            if job_id in self._polling_tasks:
                self._polling_tasks[job_id].cancel()
                del self._polling_tasks[job_id]
        logger.info(f"[ws] Client disconnected from job {job_id}")
    
    async def _poll_job(self, job_id: str):
        """Background task that polls Celery and broadcasts to all sockets."""
        try:
            while job_id in self._connections:
                result = AsyncResult(job_id, app=celery_app)
                if not result:
                    break
                
                state = JOB_STATES.get(result.state, "unknown")
                meta = result.info or {}
                progress = meta.get("progress") if isinstance(meta, dict) else None
                message = meta.get("message") if isinstance(meta, dict) else None
                error = meta.get("error") if isinstance(meta, dict) else None
                file_path = meta.get("file_path") if isinstance(meta, dict) else None
                
                payload = {
                    "type": "status",
                    "job_id": job_id,
                    "status": state,
                    "progress": progress,
                    "message": message,
                    "error": error,
                    "file_path": file_path,
                }
                await self._broadcast(job_id, payload)
                
                if state in ("completed", "failed"):
                    # Send final update then disconnect
                    await self._broadcast(job_id, {"type": "final", **payload})
                    # Give clients time to receive before we stop polling
                    await asyncio.sleep(3)
                    break
                
                await asyncio.sleep(1.5)
        except asyncio.CancelledError:
            logger.info(f"[ws] Poller for {job_id} cancelled")
        except Exception as e:
            logger.error(f"[ws] Poller error for {job_id}: {e}")
    
    async def _broadcast(self, job_id: str, payload: dict):
        if job_id not in self._connections:
            return
        dead = set()
        for ws in self._connections[job_id]:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._connections[job_id].discard(ws)

manager = ConnectionManager()

@router.websocket("/job/{job_id}")
async def websocket_job(job_id: str, websocket: WebSocket):
    if not settings.enable_websocket:
        await websocket.close(code=1001, reason="WebSocket disabled")
        return
    
    await manager.connect(job_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await websocket.send_json({"type": "pong", "job_id": job_id})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        await manager.disconnect(job_id, websocket)
    except Exception:
        await manager.disconnect(job_id, websocket)
