"""Window object (.srw) parser."""
import re
from typing import Dict, List, Optional, Any


class WindowParser:
    """Parser for Window source files.

    Extracts controls, events, instance variables, and inheritance info.
    """

    def __init__(self, content: str):
        self.content = content
        self.lines = content.splitlines()

    def extract_classname(self) -> Optional[str]:
        """Extract window/class name."""
        patterns = [
            r'class\s+(\w+)\s+"(\w+)"',
            r'type\s+\w+\s+from\s+(\w+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def extract_controls(self) -> List[Dict[str, str]]:
        """Extract all controls on the window."""
        controls = []
        # Match: type xxx from yyy at ...
        pattern = r'type\s+(\w+)\s+from\s+(\w+)'
        for match in re.finditer(pattern, self.content, re.IGNORECASE):
            controls.append({
                "type": match.group(1),
                "class": match.group(2),
            })
        return controls

    def extract_events(self) -> List[str]:
        """Extract event definitions."""
        events = []
        # Match: event name ( ...
        pattern = r'event\s+(\w+)\s*\('
        for match in re.finditer(pattern, self.content, re.IGNORECASE):
            events.append(match.group(1))
        return events

    def extract_variables(self) -> List[Dict[str, str]]:
        """Extract instance variables."""
        vars_ = []
        in_variables = False
        for line in self.lines:
            if "instance variables" in line.lower():
                in_variables = True
                continue
            if in_variables and "end type" in line.lower():
                break
            if in_variables and line.strip().startswith("-"):
                # Variable declaration line
                parts = line.strip().split()
                if len(parts) >= 2:
                    vars_.append({"type": parts[0], "name": parts[-1]})
        return vars_

    def get_inheritance(self) -> Optional[str]:
        """Extract parent window class."""
        match = re.search(r'type\s+\w+\s+from\s+(\w+)', self.content, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "classname": self.extract_classname(),
            "inherits": self.get_inheritance(),
            "controls": self.extract_controls(),
            "events": self.extract_events(),
            "variables": self.extract_variables(),
        }