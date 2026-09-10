class LangfuseAdapter:
    """Best-effort optional exporter; local tracing never depends on it."""
    def __init__(self, *args, **kwargs): self.enabled=False
    def export(self, record): return False
