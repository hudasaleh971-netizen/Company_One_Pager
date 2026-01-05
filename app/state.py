from typing import Optional

class AppState:
    """A class to hold the shared state of the application across different agents and callbacks."""
    def __init__(self):
        self.company_name: Optional[str] = None
        self.annual_report_filename: Optional[str] = None
        self.vector_store_name: Optional[str] = None
        self.compiled_report: Optional[str] = None
        self.gaps: Optional[str] = None

    def get(self, key: str, default: Optional[any] = None) -> Optional[any]:
        return getattr(self, key, default)

    def __setitem__(self, key: str, value: any):
        setattr(self, key, value)

    def __getitem__(self, key: str):
        return getattr(self, key)
