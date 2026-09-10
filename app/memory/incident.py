"""Deterministic incident extraction and a separate Qdrant collection."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams, Filter, FieldCondition, MatchValue
from app.rag.indexer import BGEEncoder

class IncidentRecord(BaseModel):
    incident_id: str
    timestamp: str
    task_summary: str
    host: str | None = None
    service: str | None = None
    port: int | None = None
    symptom: str
    root_cause: str | None = None
    actions: list[str] = Field(default_factory=list)
    resolution_status: str
    resolution_summary: str
    source_task_id: str

    def text(self) -> str:
        return (f"Task: {self.task_summary}. Symptom: {self.symptom}. "
                f"Actions: {', '.join(self.actions)}. Resolution: {self.resolution_summary}. "
                f"Status: {self.resolution_status}.")

class IncidentExtractor:
    @staticmethod
    def extract(query: str, result: Any) -> IncidentRecord | None:
        actions=[s.tool for s in result.trajectory if s.tool in {'restart_service','create_ticket'}]
        if not actions and len(result.trajectory) < 2: return None
        status=result.resolution_status
        if status not in {'RESOLVED','ESCALATED'}: return None
        host=service= None; port=None; symptoms=[]; root=None; summary=result.answer[:400]
        for step in result.trajectory:
            args=step.arguments; obs=step.observation
            host=host or args.get('host'); service=service or args.get('service'); port=port or args.get('port')
            if obs.get('status') in {'stopped','closed','unreachable'}: symptoms.append(f"{step.tool} reported {obs['status']}")
            if step.tool=='restart_service' and obs.get('status')=='success': root=root or f"{service or 'service'} was unavailable"
        if not symptoms: symptoms=['operational issue required intervention']
        if status=='RESOLVED': resolution='; '.join(actions) + ' completed successfully'
        else: resolution='automatic action was blocked; incident ticket created'
        raw=f"{result.task_id}:{status}:{host}:{service}:{port}"
        return IncidentRecord(incident_id='INC-MEM-'+sha256(raw.encode()).hexdigest()[:12], timestamp=datetime.now(timezone.utc).isoformat(), task_summary=query[:500], host=host, service=service, port=port, symptom='; '.join(symptoms), root_cause=root, actions=actions, resolution_status=status, resolution_summary=resolution, source_task_id=result.task_id)

class IncidentMemoryStore:
    collection='opspilot_incidents'
    def __init__(self, path: str | Path, encoder=None): self.path=str(path); self.encoder=encoder or BGEEncoder()
    def _client(self): return QdrantClient(path=self.path)
    def save(self, record: IncidentRecord) -> bool:
        client=self._client()
        if client.collection_exists(self.collection):
            existing=client.scroll(self.collection, scroll_filter=Filter(must=[FieldCondition(key='source_task_id', match=MatchValue(value=record.source_task_id))]), limit=1)[0]
            if existing: return False
        elif not client.collection_exists(self.collection):
            client.create_collection(self.collection, vectors_config=VectorParams(size=self.encoder.dimension, distance=Distance.COSINE))
        vec=self.encoder.encode([record.text()])[0]
        client.upsert(self.collection,[PointStruct(id=int(record.incident_id[-12:],16),vector=vec,payload=record.model_dump())])
        return True
    def search(self, query: str, top_k: int=3) -> dict:
        try:
            client=self._client()
            if not client.collection_exists(self.collection): return {'status':'success','query':query,'results':[]}
            vec=self.encoder.encode([query])[0]
            hits=client.query_points(self.collection,query=vec,limit=max(1,min(top_k,20))).points
            return {'status':'success','query':query,'results':[{'incident_id':h.payload['incident_id'],'summary':h.payload['resolution_summary'],'resolution_status':h.payload['resolution_status'],'source_task_id':h.payload['source_task_id'],'score':h.score} for h in hits]}
        except Exception as exc: return {'status':'failed','error':str(exc)}
