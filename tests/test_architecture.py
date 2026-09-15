import ast
import importlib.metadata
from pathlib import Path


def test_standalone_boundary_has_no_upstream_auditor_dependency():
    banned = {"repoauditor", "scorecard"}
    for path in Path("src/reporemedy").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules = (
                [n.name for n in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            assert not any(m.split(".")[0].lower() in banned for m in modules), path
    requirements = importlib.metadata.requires("reporemedy") or []
    assert not any(r.lower().startswith(tuple(banned)) for r in requirements)


def test_domain_contract_does_not_depend_on_io_layers():
    tree = ast.parse(Path("src/reporemedy/models.py").read_text(encoding="utf-8"))
    forbidden = {"httpx", "subprocess", "reporemedy.github", "reporemedy.providers"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert not forbidden.intersection(n.name for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module not in forbidden
