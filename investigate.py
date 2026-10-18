"""CLI for a bounded app folder; does not generate or know expected outcomes."""
import argparse
import json
from datetime import datetime, timezone
from uuid import uuid4
from prototype_engine import run_investigation

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', required=True)
    parser.add_argument('--agent', action='store_true', help='Use the local Ollama model to select validated tools and graph targets.')
    args = parser.parse_args()
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8]
    result = run_investigation(args.folder, run_id, lambda message: print(message, flush=True), agent_mode=args.agent)
    print(json.dumps({'id':run_id,'verdict':result['verdict'],'selected':result['selected_checks']}, indent=2))
    raise SystemExit({'PASS':0,'FAIL':1,'INCOMPLETE':2,'NO_DEPENDENCY_SELECTED':3}[result['verdict']])
