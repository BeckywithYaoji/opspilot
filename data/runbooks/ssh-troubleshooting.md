# SSH Troubleshooting

Check DNS and network reachability, then confirm port 22 is open. Run `ssh -v user@host` and inspect authentication and host key errors.

## Verify

Confirm sshd is running on the server and review recent authentication logs. Escalate after collecting the command output and timestamps.
