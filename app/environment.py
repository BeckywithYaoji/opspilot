"""Request-local, stateful simulation; never executes operating-system commands."""
from copy import deepcopy
from uuid import uuid4


class MockEnvironment:
    def __init__(self, scenario: str):
        permissions = {'repairable': True, 'permission_denied': False}
        self.servers = {
            'dev-server': {
                'reachable': True,
                'ports': {22: False},
                'services': {'sshd': 'stopped'},
                'restart_permission': permissions[scenario],
            }
        }
        self.tickets: list[dict] = []

    def snapshot(self) -> dict:
        return deepcopy(self.servers)

    def check_port(self, host: str, port: int) -> dict:
        server = self.servers.get(host)
        if server is None:
            return {'status': 'failed', 'error': 'unknown host'}
        status = 'unreachable' if not server['reachable'] else (
            'open' if server['ports'].get(port, False) else 'closed'
        )
        return {'host': host, 'port': port, 'status': status}

    def check_service(self, host: str, service: str) -> dict:
        server = self.servers.get(host)
        if server is None:
            return {'status': 'failed', 'error': 'unknown host'}
        if not server['reachable']:
            return {'status': 'failed', 'error': 'host unreachable'}
        if service not in server['services']:
            return {'status': 'failed', 'error': 'unknown service'}
        return {'host': host, 'service': service, 'status': server['services'][service]}

    def restart_service(self, host: str, service: str) -> dict:
        observation = self.check_service(host, service)
        if observation['status'] == 'failed':
            return observation
        server = self.servers[host]
        if not server['restart_permission']:
            return {'status': 'failed', 'error': 'permission denied'}
        server['services'][service] = 'running'
        if service == 'sshd':
            server['ports'][22] = True
        return {'status': 'success', 'message': f'{service} restarted successfully'}

    def create_ticket(self, title: str, description: str) -> dict:
        ticket_id = f'INC-{uuid4().hex[:12]}'
        self.tickets.append({'ticket_id': ticket_id, 'title': title, 'description': description})
        return {'status': 'created', 'ticket_id': ticket_id}

    @property
    def ssh_restored(self) -> bool:
        server = self.servers['dev-server']
        return bool(server['reachable'] and server['ports'][22]
                    and server['services']['sshd'] == 'running')
