'''
    技术面试辅助接口文件
        1. 给某个 technical session 选两道算法题
        2. 本地运行用户提交的代码。
'''
import json
import os
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter()

SUPPORTED_RUN_LANGUAGES = {"python", "javascript"}
RUN_TIMEOUT_SECONDS = int(os.getenv("CODE_RUN_TIMEOUT_SECONDS", "5"))


class RunCodeRequest(BaseModel):
    language: str
    code: str
    stdin: str = ""


# ── Dependency: cached problem loader ────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_problems() -> tuple[dict, ...]:
    """Read problems.json once and cache it for the process lifetime.

    Path is resolved from the PROBLEMS_DATA_PATH env var so it can be
    overridden in tests or different deployment environments without
    touching source code.  Falls back to 'data/problems.json' relative
    to the working directory (i.e. backend/).
    """
    data_path = Path(os.getenv("PROBLEMS_DATA_PATH", "data/problems.json"))
    with open(data_path, encoding="utf-8") as f:
        return tuple(json.load(f))


def get_problems() -> tuple[dict, ...]:
    """FastAPI dependency that returns the immutable problems collection."""
    return _load_problems()


# ── Problem selection logic ───────────────────────────────────────────────────

def _pick_two(session_id: str, all_problems: tuple[dict, ...]) -> list[dict]:
    """Deterministically pick 2 balanced problems seeded by session_id."""
    seed = sum(ord(c) for c in session_id)

    def _hash(problem_id: int) -> int:
        return (seed * problem_id * 2654435761) & 0xFFFFFFFF

    shuffled = sorted(all_problems, key=lambda p: _hash(p["id"]))

    easy = next((p for p in shuffled if p["difficulty"] != "Hard"), shuffled[0])
    hard = next(
        (p for p in shuffled if p is not easy and p["difficulty"] != "Easy"),
        shuffled[1],
    )
    return [easy, hard]


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get("/{session_id}/technical-problems")
async def get_technical_problems(
    session_id: str,
    problems: tuple[dict, ...] = Depends(get_problems),
) -> dict:
    """Return 2 balanced DSA problems for a technical interview session."""
    try:
        return {"problems": _pick_two(session_id, problems)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-code")
async def run_code(body: RunCodeRequest) -> dict:
    """Run interview code locally for development.

    This intentionally supports only the languages present in problems.json.
    It is suitable for local development, not for executing untrusted code in
    a shared production environment.
    """
    language = body.language.lower()
    if language not in SUPPORTED_RUN_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {body.language}",
        )

    with tempfile.TemporaryDirectory(prefix="friday-code-") as tmpdir:
        tmp_path = Path(tmpdir)
        if language == "python":
            source = tmp_path / "solution.py"
            source.write_text(body.code, encoding="utf-8")
            command = [sys.executable, str(source)]
        else:
            source = tmp_path / "solution.js"
            # The bundled JS harnesses were written for Linux runners. Make
            # them work on Windows by reading stdin from fd 0 instead.
            code = body.code.replace("readFileSync('/dev/stdin','utf8')", "readFileSync(0,'utf8')")
            code = code.replace('readFileSync("/dev/stdin","utf8")', 'readFileSync(0,"utf8")')
            source.write_text(code, encoding="utf-8")
            command = ["node", str(source)]

        try:
            result = subprocess.run(
                command,
                input=body.stdin,
                text=True,
                capture_output=True,
                timeout=RUN_TIMEOUT_SECONDS,
                cwd=tmpdir,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "stdout": exc.stdout or "",
                "stderr": f"Execution timed out after {RUN_TIMEOUT_SECONDS}s",
                "code": 124,
                "signal": "TIMEOUT",
            }
        except FileNotFoundError:
            raise HTTPException(
                status_code=500,
                detail=f"Runtime not found for {language}",
            )

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "code": result.returncode,
        "signal": None,
    }
