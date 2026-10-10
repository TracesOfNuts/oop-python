"""Build the course notebooks from the plain-text sources, and verify them.

Usage (from the repository root):

    python tools/build.py              # build notebooks/ and verify everything
    python tools/build.py build        # only build notebooks/
    python tools/build.py verify       # build, then execute and check every notebook
    python tools/build.py verify 03 07 # only verify notebooks whose name starts with 03 or 07
    python tools/build.py build --force         # overwrite notebooks the student has edited
    python tools/build.py build --no-solutions  # hide solutions from the student notebooks

The source format is described in source/README.md.

"verify" does three things for every notebook:

1. Runs a copy where every exercise starter is replaced by its solution.
   Every cell must succeed, cells marked raises=X must raise X,
   and every "predict the output" cell must print exactly its stated output.
   The executed copy is saved to solutions/ for the tutor.
2. Runs the student version and checks that every check cell FAILS there.
   This proves the checks really catch unfinished work.
3. Checks the text for banned characters (the em dash).
"""

from __future__ import annotations

import hashlib
import re
import sys
import tempfile
import textwrap
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "source"
NOTEBOOK_DIR = ROOT / "notebooks"
SOLUTION_DIR = ROOT / "solutions"

BANNED_TEXT = {chr(0x2014): "em dash (use a plain dash '-')"}

CORRECT = "✅ Correct! Well done."
# Checks print a short message instead of raising, so the student sees one clear line
# (not a traceback), and "Run All" does not stop at the first unfinished exercise.
CHECK_TEMPLATE = '''\
# ✅ CHECK: run this cell to test your answer. You do not need to change it.
try:
{body}
    print("{correct}")
except AssertionError as problem:
    print(problem)
except Exception as problem:
    print(f"❌ Your code has an error: {{type(problem).__name__}}: {{problem}}")
    print("   Did you run your answer cell first? Is every name spelled correctly?")'''
GUESS_CELL = "✍️ **My guess:** *(double-click here and type your answer)*"
ANSWER_CELL = "✍️ **My answer:** *(double-click here and type your answer)*"

# Injected only into the notebooks that the verifier runs, never into student notebooks.
VERIFY_SETUP = '''\
# [verify-setup] fake input() and a non-blocking tkinter mainloop for automatic runs
_fake_inputs = []
def input(prompt=""):
    value = _fake_inputs.pop(0) if _fake_inputs else ""
    print(prompt + value)
    return value
try:
    import tkinter as _tk
    _tk.Misc.mainloop = lambda self, n=0: None
except ImportError:
    pass
'''

DIRECTIVE = re.compile(r"^@@\s*(\w+)\s*(.*)$")
GROUP_STARTS = {"exercise", "predict", "write"}
GROUP_PARTS = {
    "exercise": {"starter", "check", "hint", "solution"},
    "predict": {"run", "output", "explain"},
    "write": {"answer", "hint"},
}
STANDALONE = {"md", "code"}


class SourceError(Exception):
    pass


@dataclass
class Block:
    kind: str
    rest: str
    text: str
    line: int

    def option(self, key: str) -> str | None:
        """Read key=value from the directive line. inputs= takes the rest of the line."""
        if key == "inputs":
            match = re.search(r"\binputs=(.*)$", self.rest)
            return match.group(1) if match else None
        match = re.search(rf"\b{key}=(\S+)", self.rest)
        return match.group(1) if match else None

    def inputs(self) -> list[str] | None:
        raw = self.option("inputs")
        return None if raw is None else [part.strip() for part in raw.split("|")]


@dataclass
class Item:
    kind: str
    head: Block
    parts: dict[str, Block] = field(default_factory=dict)
    number: str = ""


def parse_blocks(path: Path) -> list[Block]:
    blocks: list[Block] = []
    current: Block | None = None
    lines: list[str] = []

    def close() -> None:
        if current is not None:
            current.text = "\n".join(lines).strip("\n")
            blocks.append(current)

    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = DIRECTIVE.match(line)
        if match:
            close()
            current = Block(match.group(1), match.group(2).strip(), "", lineno)
            lines = []
        elif current is None:
            if line.strip():
                raise SourceError(f"{path.name}:{lineno}: text before the first @@ directive")
        else:
            lines.append(line)
    close()
    return blocks


def parse_items(path: Path) -> list[Item]:
    items: list[Item] = []
    group: Item | None = None
    for block in parse_blocks(path):
        where = f"{path.name}:{block.line}"
        if block.kind in STANDALONE:
            if not block.text.strip():
                raise SourceError(f"{where}: empty @@ {block.kind} block")
            group = None
            items.append(Item(block.kind, block))
        elif block.kind in GROUP_STARTS:
            group = Item(block.kind, block)
            items.append(group)
        elif group is not None and block.kind in GROUP_PARTS[group.kind]:
            if block.kind in group.parts:
                raise SourceError(f"{where}: duplicate @@ {block.kind}")
            group.parts[block.kind] = block
        else:
            raise SourceError(f"{where}: unexpected @@ {block.kind}")

    number = int(path.name[:2])
    count = 0
    for item in items:
        where = f"{path.name}:{item.head.line}"
        if item.kind in GROUP_STARTS:
            count += 1
            item.number = f"{number}.{count}"
            if not item.head.rest:
                raise SourceError(f"{where}: @@ {item.kind} needs a title")
        required = {"exercise": {"starter", "solution"}, "predict": {"run", "explain"}, "write": {"answer"}}
        missing = required.get(item.kind, set()) - item.parts.keys()
        if missing:
            raise SourceError(f"{where}: {item.kind} is missing {sorted(missing)}")
        check = item.parts.get("check")
        if check and ('"""' in check.text or "'''" in check.text):
            # The check is indented into a try block, which would change a multi-line string.
            raise SourceError(f"{path.name}:{check.line}: do not use triple-quoted strings in a check")
        if item.kind == "predict":
            raises = item.parts["run"].option("raises")
            if raises is None and "output" not in item.parts:
                raise SourceError(f"{where}: predict needs @@ output (or raises= on @@ run)")
    return items


def details(summary: str, body: str) -> str:
    return f"<details>\n<summary>{summary}</summary>\n\n{body}\n\n</details>"


def python_block(code: str) -> str:
    return f"```python\n{code}\n```"


def code_cell(source: str, *, raises: str | None = None, role: str | None = None, inputs=None):
    cell = new_code_cell(source)
    if raises:
        cell.metadata["tags"] = ["raises-exception"]
    meta = {}
    if raises:
        meta["raises"] = raises
    if role:
        meta["role"] = role
    if inputs is not None:
        meta["inputs"] = inputs
    if meta:
        cell.metadata["course"] = meta
    return cell


def render(items: list[Item], *, mode: str, show_solutions: bool = True):
    """mode is 'student' or 'verify'. In verify mode starters are replaced by solutions."""
    cells = []
    for item in items:
        head, parts = item.head, item.parts
        if item.kind == "md":
            cells.append(new_markdown_cell(head.text))
        elif item.kind == "code":
            cells.append(code_cell(head.text, raises=head.option("raises"), inputs=head.inputs()))
        elif item.kind == "exercise":
            cells.append(new_markdown_cell(f"### 🏋️ Exercise {item.number}: {head.rest}\n\n{head.text}".rstrip()))
            solution = parts["solution"]
            body = solution if mode == "verify" else parts["starter"]
            cells.append(code_cell(body.text, role="answer", inputs=solution.inputs()))
            if "check" in parts:
                check = parts["check"]
                body = textwrap.indent(check.text, "    ", lambda line: True)
                source = CHECK_TEMPLATE.format(body=body, correct=CORRECT)
                cells.append(code_cell(source, role="check", inputs=check.inputs()))
            reveal = []
            if "hint" in parts:
                reveal.append(details("💡 Hint (click to open)", parts["hint"].text))
            if show_solutions:
                reveal.append(details("👀 Solution (try first, then click to check)", python_block(solution.text)))
            if reveal:
                cells.append(new_markdown_cell("\n\n".join(reveal)))
        elif item.kind == "predict":
            run = parts["run"]
            intro = f"### 🔮 Exercise {item.number}: Predict - {head.rest}\n\n"
            if head.text:
                intro += head.text + "\n\n"
            intro += python_block(run.text) + "\n\n"
            intro += "**Read the code and decide what it prints (or which error it raises) BEFORE you run it.**"
            cells.append(new_markdown_cell(intro))
            cells.append(new_markdown_cell(GUESS_CELL))
            cells.append(code_cell(run.text, raises=run.option("raises"), role="predict", inputs=run.inputs()))
            cells[-1].metadata["course"]["id"] = item.number
            if "output" in parts and run.option("raises"):
                answer = (f"It prints:\n\n```text\n{parts['output'].text}\n```\n\n"
                          f"Then it stops with a **{run.option('raises')}**.\n\n")
            elif "output" in parts:
                answer = f"It prints:\n\n```text\n{parts['output'].text}\n```\n\n"
            else:
                answer = f"It stops with a **{run.option('raises')}**.\n\n"
            cells.append(new_markdown_cell(details("👀 Answer (click to open)", answer + parts["explain"].text)))
        elif item.kind == "write":
            cells.append(new_markdown_cell(f"### ✍️ Exercise {item.number}: {head.rest}\n\n{head.text}".rstrip()))
            cells.append(new_markdown_cell(ANSWER_CELL))
            reveal = []
            if "hint" in parts:
                reveal.append(details("💡 Hint (click to open)", parts["hint"].text))
            reveal.append(details("👀 Model answer (click to open)", parts["answer"].text))
            cells.append(new_markdown_cell("\n\n".join(reveal)))
    nb = new_notebook(cells=cells)
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.metadata["language_info"] = {"name": "python"}
    return nb


def content_hash(nb) -> str:
    digest = hashlib.sha256()
    for cell in nb.cells:
        digest.update(cell.cell_type.encode())
        digest.update(cell.source.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def sources(filters: list[str]) -> list[Path]:
    paths = sorted(SOURCE_DIR.glob("[0-9][0-9]_*.txt"))
    if filters:
        paths = [p for p in paths if any(p.name.startswith(f) for f in filters)]
    if not paths:
        raise SourceError("no source files matched")
    return paths


def check_text(path: Path) -> list[str]:
    problems = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for char, name in BANNED_TEXT.items():
            if char in line:
                problems.append(f"{path.name}:{lineno}: contains an {name}")
    return problems


def build(paths: list[Path], *, force: bool, show_solutions: bool) -> bool:
    NOTEBOOK_DIR.mkdir(exist_ok=True)
    ok = True
    for path in paths:
        nb = render(parse_items(path), mode="student", show_solutions=show_solutions)
        new_hash = content_hash(nb)
        nb.metadata["course"] = {"build_hash": new_hash}
        target = NOTEBOOK_DIR / f"{path.stem}.ipynb"
        if target.exists() and not force:
            old = nbformat.read(target, as_version=4)
            stored = old.metadata.get("course", {}).get("build_hash")
            if stored != content_hash(old):
                print(f"SKIPPED {target.name}: the student has edited it (use --force to overwrite)")
                ok = False
                continue
            if stored == new_hash:
                continue
        nbformat.write(nb, target)
        print(f"built   {target.relative_to(ROOT)}")
    return ok


def prepare_for_run(nb):
    """Add the verify setup cell and feed fake input() values. Returns the original sources."""
    originals = []
    for cell in nb.cells:
        originals.append(cell.source)
        inputs = cell.get("metadata", {}).get("course", {}).get("inputs")
        if cell.cell_type == "code" and inputs is not None:
            cell.source = f"_fake_inputs[:] = {inputs!r}\n" + cell.source
    nb.cells.insert(0, new_code_cell(VERIFY_SETUP))
    return originals


def execute(nb, workdir: str):
    import subprocess
    import warnings

    from nbclient import NotebookClient

    # zmq warns about the Windows event loop. It is harmless, and the noise hides real failures.
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="zmq")
    client = NotebookClient(nb, timeout=60, kernel_name="python3", allow_errors=True,
                            resources={"metadata": {"path": workdir}})
    # Kernel start-up chatter goes to stderr. Errors inside cells are still captured as outputs.
    client.execute(stderr=subprocess.DEVNULL)


def cell_error(cell) -> str | None:
    for output in cell.get("outputs", []):
        if output.output_type == "error":
            return output.ename
    return None


def cell_stdout(cell) -> str:
    return "".join(o.get("text", "") for o in cell.get("outputs", [])
                   if o.output_type == "stream" and o.name == "stdout")


def normalise(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip("\n").splitlines())


def label(nb, index: int) -> str:
    """Describe a cell by the nearest exercise heading above it."""
    for cell in reversed(nb.cells[:index]):
        if cell.cell_type == "markdown" and cell.source.startswith("### "):
            return cell.source.splitlines()[0][4:]
    return f"cell {index}"


def verify_one(path_str: str) -> tuple[str, list[str], dict]:
    path = Path(path_str)
    problems = check_text(path)
    items = parse_items(path)
    stats = {kind: sum(1 for i in items if i.kind == kind) for kind in ("exercise", "predict", "write")}
    stats["checks"] = sum(1 for i in items if i.kind == "exercise" and "check" in i.parts)

    with tempfile.TemporaryDirectory() as workdir:
        # 1. Solutions must pass.
        nb = render(items, mode="verify")
        originals = prepare_for_run(nb)
        execute(nb, workdir)
        for index, cell in enumerate(nb.cells[1:], start=1):
            if cell.cell_type != "code":
                continue
            meta = cell.metadata.get("course", {})
            error = cell_error(cell)
            expected = meta.get("raises")
            where = f"{path.name} [{label(nb, index)}]"
            if expected and error != expected:
                problems.append(f"{where}: expected {expected} but got {error or 'no error'}")
            elif not expected and error:
                trace = "\n".join(next(o for o in cell.outputs if o.output_type == "error").traceback[-3:])
                trace = re.sub(r"\x1b\[[0-9;]*m", "", trace)
                problems.append(f"{where}: unexpected {error}\n{trace}")
            elif meta.get("role") == "check" and CORRECT not in cell_stdout(cell):
                problems.append(f"{where}: check fails on the solution:\n{cell_stdout(cell).strip()}")
        for item in items:
            if item.kind == "predict" and "output" in item.parts:
                cell = next(c for c in nb.cells if c.cell_type == "code"
                            and c.metadata.get("course", {}).get("id") == item.number)
                actual, wanted = normalise(cell_stdout(cell)), normalise(item.parts["output"].text)
                if actual != wanted:
                    problems.append(f"{path.name} [Exercise {item.number}]: stated output differs.\n"
                                    f"--- stated ---\n{wanted}\n--- actual ---\n{actual}")
        nb.cells.pop(0)
        for cell, source in zip(nb.cells, originals):
            cell.source = source
        SOLUTION_DIR.mkdir(exist_ok=True)
        nbformat.write(nb, SOLUTION_DIR / f"{path.stem}_SOLUTIONS.ipynb")

        # 2. Every check must fail on the untouched student version.
        nb = render(items, mode="student")
        prepare_for_run(nb)
        execute(nb, workdir)
        for index, cell in enumerate(nb.cells[1:], start=1):
            if cell.metadata.get("course", {}).get("role") == "check" and CORRECT in cell_stdout(cell):
                problems.append(f"{path.name} [{label(nb, index)}]: check passes on the empty starter")
    return path.name, problems, stats


def verify(paths: list[Path]) -> bool:
    total = {"exercise": 0, "predict": 0, "write": 0, "checks": 0}
    all_ok = True
    with ProcessPoolExecutor(max_workers=4) as pool:
        for name, problems, stats in pool.map(verify_one, [str(p) for p in paths]):
            for key in total:
                total[key] += stats[key]
            status = "OK  " if not problems else "FAIL"
            print(f"{status} {name}: {stats['exercise']} coding ({stats['checks']} auto-checked), "
                  f"{stats['predict']} predict, {stats['write']} written")
            for problem in problems:
                print("     " + problem.replace("\n", "\n     "))
            all_ok = all_ok and not problems
    print(f"\nTotal: {sum(total[k] for k in ('exercise', 'predict', 'write'))} exercises "
          f"({total['exercise']} coding, {total['predict']} predict, {total['write']} written)")
    return all_ok


def main(argv: list[str]) -> int:
    flags = {a for a in argv if a.startswith("--")}
    args = [a for a in argv if not a.startswith("--")]
    command = args.pop(0) if args and args[0] in {"build", "verify"} else "all"
    try:
        paths = sources(args)
        ok = build(paths, force="--force" in flags, show_solutions="--no-solutions" not in flags)
        if command in {"verify", "all"}:
            ok = verify(paths) and ok
    except SourceError as error:
        print(f"ERROR: {error}")
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
