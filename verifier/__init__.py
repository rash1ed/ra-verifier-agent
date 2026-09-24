"""RA Verifier Agent."""
__version__ = "0.1.0"

from .models import Criteria, CheckResult, VerifyResult
from .verifier import verify

__all__ = ["Criteria", "CheckResult", "VerifyResult", "verify"]
