"""Function object (.srf) parser."""
import re
from typing import Dict, List, Optional, Any


class FunctionParser:
    """Parser for Function object source files.

    Extracts function signatures, parameters, return type, and body.
    """

    def __init__(self, content: str):
        self.content = content
        self.lines = content.splitlines()

    def extract_function_name(self) -> Optional[str]:
        """Extract function name."""
        patterns = [
            r'function\s+(\w+)\s+(\w+)\s*\(',
            r'subroutine\s+(\w+)\s*\(',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.content, re.IGNORECASE)
            if match:
                return match.group(2) if "subroutine" not in pattern else match.group(1)
        return None

    def extract_return_type(self) -> Optional[str]:
        """Extract return type."""
        match = re.search(r'function\s+(\w+)\s+\w+\s*\(', self.content, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def extract_parameters(self) -> List[Dict[str, str]]:
        """Extract function parameters."""
        params = []
        # Match: (type name, ...)
        match = re.search(r'\((.+?)\)', self.content, re.DOTALL)
        if match:
            param_str = match.group(1)
            # Split by comma, handling nested parentheses
            for param in param_str.split(","):
                parts = [p.strip() for p in param.split()]
                if len(parts) >= 2:
                    params.append({
                        "type": parts[0],
                        "name": parts[1],
                    })
        return params

    def extract_calls(self) -> List[str]:
        """Extract function calls within the function body."""
        calls = []
        pattern = r'(\w+)\s*\('
        for match in re.finditer(pattern, self.content):
            func_name = match.group(1)
            if func_name.lower() not in ["if", "for", "while", "select", "return"]:
                calls.append(func_name)
        return list(set(calls))  # Deduplicate

    def has_return(self) -> bool:
        """Check if function has return statement."""
        return "return " in self.content.lower()

    def get_complexity(self) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity
        keywords = ["if", "else", "elseif", "for", "while", "do", "choose"]
        for kw in keywords:
            complexity += self.content.lower().count(kw)
        return complexity

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.extract_function_name(),
            "return_type": self.extract_return_type(),
            "parameters": self.extract_parameters(),
            "calls": self.extract_calls(),
            "has_return": self.has_return(),
            "complexity": self.get_complexity(),
        }