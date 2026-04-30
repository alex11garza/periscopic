"""
Server — connection descriptor for a PrivQ MPC server.

A ``Server`` captures everything the CLI might need to reach an MPC
server that another user spun up via the PrivQ Python library.
Fields are intentionally broad for now; unused ones can be dropped
once the real connection protocol is settled.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict


@dataclass
class Server:
    url: str
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    api_key: Optional[str] = None
    tls: bool = True
    ca_cert_path: Optional[str] = None
    client_cert_path: Optional[str] = None
    client_key_path: Optional[str] = None
    party_id: Optional[int] = None
    epsilon: Optional[float] = None
    timeout: Optional[float] = None
    extra: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def redacted(self) -> Dict[str, object]:
        d = self.to_dict()
        for k in ("password", "token", "api_key", "client_key_path"):
            if d.get(k):
                d[k] = "***"
        return d

    def __str__(self) -> str:
        label = self.name or self.url
        user = f"{self.username}@" if self.username else ""
        return f"{label} ({user}{self.url})"
