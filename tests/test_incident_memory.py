from app.memory.incident import IncidentExtractor, IncidentMemoryStore
from app.models import RunResponse, TrajectoryStep


def result(task='task-a', escalated=False):
    steps=[TrajectoryStep(step=1,tool='check_service',arguments={'host':'alpha','service':'database'},observation={'status':'stopped'}),TrajectoryStep(step=2,tool='restart_service',arguments={'host':'alpha','service':'database'},observation={'status':'failed','error':'permission denied'} if escalated else {'status':'success'})]
    if escalated: steps.append(TrajectoryStep(step=3,tool='create_ticket',arguments={'title':'repair'},observation={'status':'created'}))
    return RunResponse(task_id=task,status='COMPLETED',answer='done',success=not escalated,environment={},trajectory=steps,tickets=[{'ticket_id':'1'}] if escalated else [])


def test_extract_operational_incident():
    record=IncidentExtractor.extract('Database unavailable',result())
    assert record.host=='alpha' and record.service=='database'
    assert record.resolution_status=='RESOLVED' and record.root_cause=='database was unavailable'
    assert 'stopped' in record.symptom
    assert 'observation' not in record.model_dump()


def test_escalation_qualifies_but_status_check_does_not():
    assert IncidentExtractor.extract('Recover',result(escalated=True)).resolution_status=='ESCALATED'
    r=result();r.trajectory=r.trajectory[:1]
    assert IncidentExtractor.extract('Check status',r) is None

class Encoder:
    dimension=3
    def encode(self,texts):
        return [[float('ssh' in t.lower()),float('disk' in t.lower()),float('permission' in t.lower())] for t in texts]


def test_qdrant_idempotency_and_cross_session_search(tmp_path):
    store=IncidentMemoryStore(tmp_path,encoder=Encoder())
    record=IncidentExtractor.extract('SSH connection failure',result())
    assert store.save(record) is True
    assert store.save(record) is False
    for i,query in enumerate(['disk full','permission problem']): store.save(IncidentExtractor.extract(query,result(str(i))))
    found=IncidentMemoryStore(tmp_path,encoder=Encoder()).search('previous SSH connection failure',3)
    assert found['results'][0]['source_task_id']==record.source_task_id
    assert len(found['results'])==3
