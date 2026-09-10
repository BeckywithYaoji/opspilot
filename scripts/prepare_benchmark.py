"""Inspect input collections, or explicitly restore saved incidents via normal store API."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--restore-incidents',action='store_true');args=parser.parse_args()
    if args.restore_incidents:
        from app.memory.incident import IncidentMemoryStore,IncidentRecord
        saved=json.loads((ROOT/'data/benchmark/expected/collection-snapshot.json').read_text())
        store=IncidentMemoryStore(ROOT/'data/qdrant-incidents')
        for row in saved['opspilot_incidents']['records']:
            record=IncidentRecord.model_validate(row['payload'])
            print(record.incident_id,store.save(record))
    else:
        from qdrant_client import QdrantClient
        for name,path in [('runbooks','data/qdrant'),('opspilot_incidents','data/qdrant-incidents')]:
            client=QdrantClient(path=str(ROOT/path))
            try: print(name,client.count(name).count)
            finally: client.close()
if __name__=='__main__':main()
