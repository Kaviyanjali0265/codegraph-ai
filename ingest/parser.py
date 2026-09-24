import ast
import os
from pathlib import Path
from core.models import CodeChunk


def _extract_calls(node: ast.AST) -> list[str]:
    calls = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
    return list(set(calls))


def _extract_function(node: ast.FunctionDef, file_path: str, lines: list[str], prefix: str = "") -> CodeChunk:
    start = node.lineno - 1
    end = node.end_lineno
    code = "\n".join(lines[start:end])
    name = f"{prefix}{node.name}" if prefix else node.name
    return CodeChunk(
        id=f"{file_path}::{name}",
        file=file_path,
        name=name,
        type="method" if prefix else "function",
        code=code,
        docstring=ast.get_docstring(node) or "",
        lineno=node.lineno,
        calls=_extract_calls(node),
    )


def _extract_class(node: ast.ClassDef, file_path: str, lines: list[str]) -> CodeChunk:
    start = node.lineno - 1
    end = node.end_lineno
    code = "\n".join(lines[start:end])
    return CodeChunk(
        id=f"{file_path}::{node.name}",
        file=file_path,
        name=node.name,
        type="class",
        code=code,
        docstring=ast.get_docstring(node) or "",
        lineno=node.lineno,
        calls=[],
    )


def parse_file(file_path: str) -> list[CodeChunk]:
    source = Path(file_path).read_text()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    chunks = []
    lines = source.splitlines()

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunks.append(_extract_function(node, file_path, lines))
        elif isinstance(node, ast.ClassDef):
            chunks.append(_extract_class(node, file_path, lines))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    chunks.append(_extract_function(child, file_path, lines, prefix=f"{node.name}."))

    return chunks


def parse_directory(directory: str) -> list[CodeChunk]:
    chunks = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                chunks.extend(parse_file(file_path))
    return chunks
