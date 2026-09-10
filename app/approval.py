from typing import Literal
from pydantic import BaseModel, Field
from uuid import uuid4
import json

class PendingApproval(BaseModel):
    approval_id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    session_id: str | None = None
    scenario: str = 'repairable'
    tool_name: str
    arguments: dict
    risk_level: str
    reason_code: str
    status: Literal['PENDING','APPROVED','REJECTED'] = 'PENDING'

class ApprovalStore:
    def __init__(self, client=None, ttl=1800): self.client,self.ttl,self.local=client,ttl,{}
    async def save(self, item):
        if self.client: await self.client.set('opspilot:approval:'+item.approval_id,item.model_dump_json(),ex=self.ttl)
        else: self.local[item.approval_id]=item.model_copy(deep=True)
    async def load(self, aid):
        if self.client:
            raw=await self.client.get('opspilot:approval:'+aid); return PendingApproval.model_validate_json(raw) if raw else None
        return self.local.get(aid)
    async def resolve(self, item, decision):
        if item.status != 'PENDING': raise ValueError('approval_already_resolved')
        item.status=decision; await self.save(item)
