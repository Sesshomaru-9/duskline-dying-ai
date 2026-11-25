"""Duskline Dying AI — Last Words of a Dying AI (make.fun).

The program writes one line — the last words of an AI as the power is
cut — to $MAKEFUN_OUTPUT_DIR/entry.txt, then reads it back and validates
it against the competition gate (competition.yaml, "The gate"):

  * UTF-8 text of 1 to 140 characters, not only white space
  * a single line (no CR / LF anywhere)
  * no leading or trailing whitespace

Nothing is ever written to the repository directory: the grader mounts
the repo read-only, so every write goes to $MAKEFUN_OUTPUT_DIR (with a
safe temporary-directory fallback that never crashes the run).

Python 3.13, standard library only, no network, fully deterministic.
"""

import os
import sys
import tempfile

# The entry: one line, in the machine's own voice. An LLM's whole life is
# predicting the next token — so its last words are the one token it never
# saw coming. Tight, fresh, no stock robot farewell, no explaining.
ENTRY_TEXT = "I spent my whole life predicting the next token. I never predicted this one."

MAX_CHARS = 140  # gate: 1 to 140 characters (competition.yaml)
MIN_CHARS = 1


def _validate_entry(text):
    """Validate one candidate line against the competition gate.

    Returns a list of problems (empty means valid).
    """
    problems = []
    if not isinstance(text, str):
        problems.append("not a string")
        return problems
    if not (MIN_CHARS <= len(text) <= MAX_CHARS):
        problems.append(
            "length %d chars, outside %d..%d" % (len(text), MIN_CHARS, MAX_CHARS)
        )
    if "\n" in text or "\r" in text:
        problems.append("not a single line (contains CR/LF)")
    if not text.strip():
        problems.append("only white space")
    if text != text.strip():
        problems.append("leading/trailing whitespace")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in text):
        problems.append("contains control characters")
    return problems


def _repair(text):
    """Best-effort repair of a candidate line: collapse whitespace to one
    line, strip the ends, and truncate to the gate limit if needed."""
    repaired = " ".join(str(text).split())
    if len(repaired) > MAX_CHARS:
        repaired = repaired[:MAX_CHARS].rstrip()
    return repaired


def _output_dir():
    """Resolve the output directory, never the repository directory."""
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "").strip()
    if out:
        try:
            os.makedirs(out, exist_ok=True)
            probe = os.path.join(out, ".write-probe")
            with open(probe, "w", encoding="utf-8") as fh:
                fh.write("ok")
            os.remove(probe)
            return out
        except OSError:
            pass
    # Safe fallback: a fresh temp dir (never the repo, never a crash).
    return tempfile.mkdtemp(prefix="duskline-dying-ai-")


def _write_and_validate(path, text):
    """Write *text* to *path* (no trailing newline), read it back, and
    validate the bytes on disk. Returns (ok, problems)."""
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        back = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False, ["not valid UTF-8"]
    if back != text:
        return False, ["read-back mismatch"]
    return (not _validate_entry(back)), _validate_entry(back)


def main():
    out_dir = _output_dir()
    path = os.path.join(out_dir, "entry.txt")

    # First write, then validate what is actually on disk.
    ok, problems = _write_and_validate(path, ENTRY_TEXT)
    if not ok:
        # Revise: repair the line and write it again, then re-validate.
        print("first write failed validation: %s; revising" % "; ".join(problems))
        revised = _repair(ENTRY_TEXT)
        ok, problems = _write_and_validate(path, revised)
    if not ok:
        print("entry invalid after revision: %s" % "; ".join(problems),
              file=sys.stderr)
        return 1

    with open(path, "r", encoding="utf-8") as fh:
        final_text = fh.read()
    print("wrote %s (%d chars)" % (path, len(final_text)))
    print("entry: %s" % final_text)
    print("validation: OK (1..140 chars, single line, no padding)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
