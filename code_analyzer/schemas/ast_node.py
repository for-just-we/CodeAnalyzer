from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class ASTNode:
    node_type: str
    node_text: str
    start_point: Tuple[int, int]
    end_point: Tuple[int, int]
    children: List['ASTNode'] = field(default_factory=list)
    parent: 'ASTNode' = None

    @property
    def child_count(self) -> int:
        return len(self.children)