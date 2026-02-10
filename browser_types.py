from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union
from enum import Enum
import time

class ActionType(Enum):
    CLICK = "click"
    TYPE = "type"
    NAVIGATE = "navigate"

class LocatorStrategy(Enum):
    DISTILLED_ID = "distilled_id"
    TEST_ID = "test_id"
    ARIA_ROLE = "aria_role"
    TEXT = "text"
    CSS = "css"

class FailureKind(Enum):
    TIMEOUT_OR_STUCK = "timeout_or_stuck"
    AMBIGUOUS_LOCATOR = "ambiguous_locator"
    UNSUPPORTED_SURFACE = "unsupported_surface"
    SECURITY_BLOCK = "security_block"
    GENERIC_ERROR = "generic_error"

@dataclass
class BrowserCommand:
    action_type: ActionType
    element_id: Optional[str] = None
    text_content: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class InteractionResult:
    success: bool
    action: ActionType
    element_id: Optional[str] = None
    locator_kind: Optional[LocatorStrategy] = None
    url_after: Optional[str] = None
    progress_signal: Optional[str] = None
    failure_kind: Optional[FailureKind] = None
    failure_reason: Optional[str] = None
    attempted_selectors: Optional[List[str]] = None

@dataclass
class DistilledElement:
    element_id: str
    tag_name: str
    role: Optional[str] = None
    name: Optional[str] = None
    text: Optional[str] = None
    attributes: Optional[Dict[str, str]] = None
    selector_hints: Optional[List[str]] = None

