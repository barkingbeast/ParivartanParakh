"""Read-only checks before rehearsing the local demo."""
import json
import os
import sys
import urllib.request
from falkordb import FalkorDB


def main():
    failures=[]
    def check(name,action):
        try: print('OK:',name,'-',action())
        except Exception as error:
            failures.append(name)
            print('UNAVAILABLE:',name,'-',type(error).__name__,str(error))
    def graph():
        result=FalkorDB(host=os.environ.get('FALKORDB_HOST','::1'),port=int(os.environ.get('FALKORDB_PORT','6379')),socket_timeout=5).select_graph('state_survival_preflight').query('RETURN 1').result_set
        assert result==[[1]],result
        return 'Cypher RETURN 1 succeeded'
    def dashboard():
        with urllib.request.urlopen('http://127.0.0.1:8772/api/samples',timeout=5) as response:
            assert json.load(response)
        return 'sample API reachable'
    def model():
        base=os.environ.get('OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')
        expected=os.environ.get('STATE_SURVIVAL_MODEL','qwen3:0.6b')
        with urllib.request.urlopen(base+'/api/tags',timeout=5) as response: models=json.load(response)['models']
        assert any(m['name']==expected for m in models),f'{expected} is not installed'
        return expected+' installed; generation is checked by verify_demo.py'
    def viewer():
        with urllib.request.urlopen('http://localhost:3000/login',timeout=5) as response: assert response.status==200
        return 'viewer reachable; sign in locally if needed'
    check('FalkorDB',graph);check('Dashboard',dashboard);check('Ollama model',model);check('Graph viewer',viewer)
    print('Ready for rehearsal.' if not failures else 'Restore unavailable services before presenting.')
    return bool(failures)


if __name__=='__main__':sys.exit(main())
