#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APPLICATIONS_DIR = ROOT / "applications"
TEMPLATES_DIR = ROOT / "templates"
UNSORTED_DIR = APPLICATIONS_DIR / "_unsorted"
APPLICATIONS_SHARED_DIR = APPLICATIONS_DIR / "_shared"
TEMPLATES_SHARED_DIR = TEMPLATES_DIR / "_shared"

SHARED_FILES = [
    "altacv.cls",
    "pubs-num.tex",
    "pubs-authoryear.tex",
    "sample.bib",
    "moi.jpeg",
    "orcid.svg",
    "6892(1).pdf",
    "Globe_High.png",
    "Suitcase_High.png",
    "Yacht_High.png",
]

PLACEHOLDER_PATTERNS = [
    re.compile(r"\[(Nom|Poste|Entreprise|Année|Lieu|Responsabilité)[^\]]*\]", re.IGNORECASE),
    re.compile(r"Nom de l['’]Entreprise", re.IGNORECASE),
    re.compile(r"Nom du Poste", re.IGNORECASE),
    re.compile(r"poste actuel", re.IGNORECASE),
]

IGNORE_FILES = {
    "pubs-num.tex",
    "pubs-authoryear.tex",
    "sample.tex",
    "sample_context.tex",
    "sample_french.tex",
}

TEMPLATE_BUCKETS = {
    "cv": "cv",
    "lm": "letters",
    "letter": "letters",
    "lettre": "letters",
}

PERSON_TOKENS = {"guillaume", "boileau", "updated", "respecte", "modele"}
PREFIX_TOKENS = {"cv", "lm", "letter", "lettre"}
COMPANY_ALIASES = {
    "pro": "pro-btp",
    "pcubed": "migso-pcubed",
    "intheair": "intheair",
    "ivvq": "scalian",
    "ivvl": "templates",
}


@dataclass
class ManagedFile:
    path: Path
    kind: str
    company: str
    offer: str
    target_dir: Path


@dataclass
class GitResult:
    committed: bool
    pushed: bool
    message: str


def decode_process_output(data: bytes) -> str:
    if not data:
        return ""
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = (
        value.replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ç", "c")
        .replace("&", "and")
    )
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "general"


def detect_kind(filename: str) -> str:
    lower = filename.lower()
    if lower.startswith("lm_"):
        return "lm"
    if lower.startswith("letter_"):
        return "letter"
    if lower.startswith("lettre_"):
        return "lettre"
    if lower.startswith("cv_") or lower.startswith("cv"):
        return "cv"
    return "misc"


def tokenize_stem(path: Path) -> list[str]:
    stem = path.stem
    stem = stem.replace("(", "_").replace(")", "_")
    stem = stem.replace("__", "_")
    tokens = [slugify(t) for t in stem.split("_")]
    return [t for t in tokens if t]


def infer_company_offer(path: Path, kind: str) -> tuple[str, str, bool]:
    tokens = tokenize_stem(path)
    filtered = [t for t in tokens if t not in PREFIX_TOKENS and t not in PERSON_TOKENS]
    if not filtered:
        return ("unsorted", slugify(path.stem), False)

    if kind == "misc":
        return ("unsorted", slugify(path.stem), False)

    if path.name in IGNORE_FILES:
        bucket = TEMPLATE_BUCKETS.get(kind, "misc")
        return ("templates", bucket, True)

    company = COMPANY_ALIASES.get(filtered[0], filtered[0])
    offer_tokens = filtered[1:] or ["general"]

    if company == "templates":
        bucket = TEMPLATE_BUCKETS.get(kind, "misc")
        return ("templates", bucket, True)

    if company == "pro-btp" and offer_tokens and offer_tokens[0] == "btp":
        offer_tokens = offer_tokens[1:]

    if not company:
        return ("unsorted", slugify(path.stem), False)

    return (company, slugify("-".join(offer_tokens)), False)


def target_dir_for(path: Path) -> ManagedFile | None:
    if path.parent != ROOT:
        return None
    if path.name in IGNORE_FILES:
        kind = detect_kind(path.name)
        bucket = TEMPLATE_BUCKETS.get(kind, "misc")
        return ManagedFile(path, kind, "templates", bucket, TEMPLATES_DIR / bucket)

    kind = detect_kind(path.name)
    company, offer, is_template = infer_company_offer(path, kind)
    if is_template or company == "templates":
        bucket = offer if offer in {"cv", "letters", "research", "misc"} else TEMPLATE_BUCKETS.get(kind, "misc")
        return ManagedFile(path, kind, "templates", bucket, TEMPLATES_DIR / bucket)
    if company == "unsorted":
        return ManagedFile(path, kind, "unsorted", offer, UNSORTED_DIR / offer)
    return ManagedFile(path, kind, company, offer, APPLICATIONS_DIR / company / offer)


def ensure_shared(target_dir: Path) -> None:
    if target_dir.parts[-2] == "templates":
        shared_dir = TEMPLATES_SHARED_DIR
    elif "applications" in target_dir.parts:
        shared_dir = APPLICATIONS_SHARED_DIR
    else:
        return

    shared_dir.mkdir(parents=True, exist_ok=True)
    for name in SHARED_FILES:
        source = ROOT / name
        if source.exists():
            link = shared_dir / name
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(Path("../../") / name if shared_dir == TEMPLATES_SHARED_DIR else Path("../..") / name)


def texinputs_env(tex_path: Path) -> dict:
    env = os.environ.copy()
    extra_paths = []
    if "applications" in tex_path.parts:
        extra_paths.append(str(APPLICATIONS_SHARED_DIR.resolve()))
    if "templates" in tex_path.parts:
        extra_paths.append(str(TEMPLATES_SHARED_DIR.resolve()))
    extra_paths.append(str(ROOT.resolve()))
    current = env.get("TEXINPUTS", "")
    env["TEXINPUTS"] = os.pathsep.join(extra_paths) + os.pathsep + current
    return env


def patch_tex(tex_path: Path) -> None:
    text = tex_path.read_text(encoding="utf-8")
    shared_prefix = "../_shared"
    if "applications" in tex_path.parts:
        shared_prefix = "../../_shared"
    replacements = {
        r"\documentclass[11pt,a4paper]{../_shared/altacv}": r"\documentclass[11pt,a4paper]{altacv}",
        r"\documentclass[10pt,a4paper]{../_shared/altacv}": r"\documentclass[10pt,a4paper]{altacv}",
        r"\documentclass[8pt,a4paper,ragged2e,withhyper]{../_shared/altacv}": r"\documentclass[8pt,a4paper,ragged2e,withhyper]{altacv}",
        r"\documentclass[11pt,a4paper]{altacv}": r"\documentclass[11pt,a4paper]{altacv}",
        r"\documentclass[10pt,a4paper]{altacv}": r"\documentclass[10pt,a4paper]{altacv}",
        r"\documentclass[8pt,a4paper,ragged2e,withhyper]{altacv}": r"\documentclass[8pt,a4paper,ragged2e,withhyper]{altacv}",
        "{pubs-num.tex}": "{%s/pubs-num.tex}" % shared_prefix,
        "{pubs-authoryear.tex}": "{%s/pubs-authoryear.tex}" % shared_prefix,
        "{sample.bib}": "{%s/sample.bib}" % shared_prefix,
        "{moi}": "{%s/moi}" % shared_prefix,
        "{Globe_High}": "{%s/Globe_High}" % shared_prefix,
        "{Suitcase_High}": "{%s/Suitcase_High}" % shared_prefix,
        "{Yacht_High}": "{%s/Yacht_High}" % shared_prefix,
        "{orcid.svg}": "{%s/orcid.svg}" % shared_prefix,
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\\documentclass(\[[^\]]+\])\{[^}]*altacv\}", r"\\documentclass\1{altacv}", text)
    if "applications" in tex_path.parts:
        text = text.replace("{../_shared/", "{../../_shared/")
    tex_path.write_text(text, encoding="utf-8")


def inject_layout_tuning(tex_path: Path) -> bool:
    text = tex_path.read_text(encoding="utf-8")
    marker = "% auto_tex_manager layout tuning"
    if marker in text:
        return False

    tuning = (
        marker + "\n"
        "\\emergencystretch=3em\n"
        "\\hfuzz=60pt\n"
        "\\hbadness=9999\n"
        "\\sloppy\n\n"
    )
    if "\\begin{document}" not in text:
        return False

    text = text.replace("\\begin{document}", tuning + "\\begin{document}", 1)
    tex_path.write_text(text, encoding="utf-8")
    return True


def build_xmpdata(tex_path: Path) -> Path:
    xmp_path = tex_path.with_suffix(".xmpdata")
    if xmp_path.exists():
        return xmp_path

    stem = tex_path.stem.replace("_", " ").strip()
    title = stem
    subject = f"Document LaTeX gere automatiquement pour {stem}"
    keywords = ", ".join([w for w in stem.split() if w][:8])
    content = (
        f"\\Title{{{title}}}\n"
        "\\Author{Guillaume Boileau}\n"
        "\\Language{fr-FR}\n"
        f"\\Subject{{{subject}}}\n"
        f"\\Keywords{{{keywords}}}\n"
    )
    xmp_path.write_text(content, encoding="utf-8")
    return xmp_path


def companion_files(tex_path: Path) -> list[Path]:
    files = [tex_path]
    for ext in (".pdf", ".xmpdata"):
        candidate = tex_path.with_suffix(ext)
        if candidate.exists():
            files.append(candidate)
    return files


def compile_tex(tex_path: Path) -> tuple[bool, str]:
    cmd = [
        "latexmk",
        "-pdf",
        "-g",
        "-interaction=nonstopmode",
        "-file-line-error",
        tex_path.name,
    ]
    result = subprocess.run(
        cmd,
        cwd=str(tex_path.parent),
        capture_output=True,
        env=texinputs_env(tex_path),
    )
    log = decode_process_output(result.stdout) + decode_process_output(result.stderr)
    return (result.returncode == 0, log)


def run_biber(tex_path: Path) -> tuple[bool, str]:
    cmd = ["biber", tex_path.stem]
    result = subprocess.run(
        cmd,
        cwd=str(tex_path.parent),
        capture_output=True,
    )
    log = decode_process_output(result.stdout) + decode_process_output(result.stderr)
    return (result.returncode == 0, log)


def placeholder_hits(tex_path: Path) -> list[str]:
    text = tex_path.read_text(encoding="utf-8")
    hits = []
    for pattern in PLACEHOLDER_PATTERNS:
        for match in pattern.findall(text):
            if match not in hits:
                hits.append(match)
    return hits[:20]


def uses_bibliography(tex_path: Path) -> bool:
    text = tex_path.read_text(encoding="utf-8")
    patterns = [
        r"\\cite[a-zA-Z*]*\{",
        r"\\parencite[a-zA-Z*]*\{",
        r"\\textcite[a-zA-Z*]*\{",
        r"\\autocite[a-zA-Z*]*\{",
        r"\\footcite[a-zA-Z*]*\{",
        r"\\nocite\{",
        r"\\printbibliography\b",
        r"\\fullcite\{",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def remove_unused_bibresource(tex_path: Path) -> bool:
    if uses_bibliography(tex_path):
        return False
    text = tex_path.read_text(encoding="utf-8")
    updated = re.sub(r"(?m)^.*\\addbibresource\{[^}]+\}.*\n?", "", text)
    if updated == text:
        return False
    tex_path.write_text(updated, encoding="utf-8")
    for suffix in (".bcf", ".bbl", ".blg", ".run.xml"):
        artifact = tex_path.with_suffix(suffix)
        if artifact.exists():
            artifact.unlink()
    return True


def extract_warnings(log: str) -> list[str]:
    warnings = []
    for line in log.splitlines():
        if any(token in line for token in ["Warning", "Overfull", "Underfull", "LaTeX Error"]):
            line = line.strip()
            if line and line not in warnings:
                warnings.append(line)
    return warnings


def auto_fix_known_issues(tex_path: Path, log: str) -> list[str]:
    fixes = []
    xmp_path = tex_path.with_suffix(".xmpdata")
    if "Metadata will be incomplete!" in log and not xmp_path.exists():
        build_xmpdata(tex_path)
        fixes.append("created_xmpdata")

    content = tex_path.read_text(encoding="utf-8")
    patched = content
    patched = re.sub(r"\\documentclass(\[[^\]]+\])\{[^}]*altacv\}", r"\\documentclass\1{altacv}", patched)
    if patched != content:
        tex_path.write_text(patched, encoding="utf-8")
        fixes.append("normalized_documentclass")

    if "rerunfilecheck Warning" in log:
        fixes.append("rerun_for_outlines")

    if ("Please (re)run Biber on the file:" in log or "undefined references" in log.lower()) and not uses_bibliography(tex_path):
        if remove_unused_bibresource(tex_path):
            fixes.append("removed_unused_bibresource")

    return fixes


def compile_with_fixes(tex_path: Path, max_rounds: int = 4) -> tuple[bool, str, str, list[str], list[str]]:
    applied_fixes: list[str] = []
    combined_logs: list[str] = []
    last_ok = False
    last_log = ""

    for _ in range(max_rounds):
        ok, log = compile_tex(tex_path)
        last_ok = ok
        last_log = log
        combined_logs.append(log)

        biber_needed = (
            "Please (re)run Biber on the file:" in log or "There were undefined references." in log
        ) and uses_bibliography(tex_path)
        if biber_needed and "ran_biber" not in applied_fixes:
            biber_ok, biber_log = run_biber(tex_path)
            combined_logs.append(biber_log)
            applied_fixes.append("ran_biber" if biber_ok else "biber_failed")
            if biber_ok:
                continue

        has_layout_warnings = "Overfull \\hbox" in log or "Underfull \\hbox" in log
        if has_layout_warnings and "layout_tuning" not in applied_fixes:
            if inject_layout_tuning(tex_path):
                applied_fixes.append("layout_tuning")
                continue

        fixes = auto_fix_known_issues(tex_path, log)
        new_fixes = [fix for fix in fixes if fix not in applied_fixes]
        applied_fixes.extend(new_fixes)
        if not new_fixes:
            break

    final_warnings = extract_warnings(last_log)
    return last_ok, "\n".join(combined_logs), last_log, applied_fixes, final_warnings


def classify_warnings(warnings: list[str]) -> tuple[list[str], list[str]]:
    actionable = []
    layout = []
    for line in warnings:
        if "Overfull" in line or "Underfull" in line:
            if line not in layout:
                layout.append(line)
            continue
        if line not in actionable:
            actionable.append(line)
    return actionable, layout


def summarize_log(log: str) -> list[str]:
    lines = []
    for pattern in [
        r"Warning:.*",
        r".*Overfull.*",
        r".*Underfull.*",
        r".*undefined references.*",
        r".*LaTeX Error:.*",
        r".*Metadata file .* read successfully\..*",
        r".*Please \(re\)run Biber on the file:.*",
        r".*INFO - This is Biber.*",
        r".*WARN - .*",
        r".*ERROR - .*",
    ]:
        for match in re.findall(pattern, log):
            if match not in lines:
                lines.append(match.strip())
    return lines[:20]


def filter_summary_for_tex(tex_path: Path, summary: list[str]) -> list[str]:
    if uses_bibliography(tex_path):
        return summary
    filtered = []
    for line in summary:
        if "Biber" in line or "biber" in line:
            continue
        filtered.append(line)
    return filtered


def run_git_command(args: list[str]) -> tuple[bool, str]:
    result = subprocess.run(
        ["git"] + args,
        cwd=str(ROOT),
        capture_output=True,
    )
    output = decode_process_output(result.stdout) + decode_process_output(result.stderr)
    return (result.returncode == 0, output.strip())


def conventional_commit_message(reports: list[dict], custom_message: str | None = None) -> str:
    if custom_message:
        return custom_message
    if len(reports) == 1:
        report = reports[0]
        scope = report.get("company") or "repo"
        desc = f"organize {report['file']} into {report['target']}"
        return f"feat({scope}): {desc}"
    return f"feat(repo): automate tex organization and compilation"


def maybe_commit_and_push(reports: list[dict], should_push: bool, custom_message: str | None = None) -> GitResult:
    message = conventional_commit_message(reports, custom_message)
    ok, output = run_git_command(["add", "-A"])
    if not ok:
        raise RuntimeError(f"git add failed: {output}")

    ok, diff_output = run_git_command(["diff", "--cached", "--quiet"])
    if ok:
        return GitResult(False, False, message)

    ok, output = run_git_command(["commit", "-m", message])
    if not ok:
        raise RuntimeError(f"git commit failed: {output}")

    pushed = False
    if should_push:
        ok, branch = run_git_command(["branch", "--show-current"])
        if not ok or not branch:
            raise RuntimeError(f"git branch --show-current failed: {branch}")
        ok, output = run_git_command(["push", "origin", branch.strip()])
        if not ok:
            raise RuntimeError(f"git push failed: {output}")
        pushed = True

    return GitResult(True, pushed, message)


def process_tex(tex_path: Path, compile_after: bool) -> dict:
    managed = target_dir_for(tex_path)
    if managed is None:
        return {"file": str(tex_path), "status": "skipped", "reason": "not managed"}

    created_dirs = []
    for directory in [APPLICATIONS_DIR, TEMPLATES_DIR]:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created_dirs.append(str(directory.relative_to(ROOT)))
    if not managed.target_dir.exists():
        managed.target_dir.mkdir(parents=True, exist_ok=True)
        created_dirs.append(str(managed.target_dir.relative_to(ROOT)))
    else:
        managed.target_dir.mkdir(parents=True, exist_ok=True)

    ensure_shared(managed.target_dir)
    build_xmpdata(tex_path)

    moved = []
    for item in companion_files(tex_path):
        destination = managed.target_dir / item.name
        shutil.move(str(item), str(destination))
        moved.append(destination)

    moved_tex = managed.target_dir / tex_path.name
    patch_tex(moved_tex)
    remove_unused_bibresource(moved_tex)

    report = {
        "file": tex_path.name,
        "status": "moved",
        "target": str(managed.target_dir.relative_to(ROOT)),
        "kind": managed.kind,
        "company": managed.company,
        "offer": managed.offer,
        "created_dirs": created_dirs,
    }

    report["placeholders"] = placeholder_hits(moved_tex)

    if compile_after:
        ok, combined_log, final_log, fixes, final_warnings = compile_with_fixes(moved_tex)
        actionable_warnings, layout_warnings = classify_warnings(final_warnings)
        report["compile_ok"] = ok
        report["log_summary"] = filter_summary_for_tex(moved_tex, summarize_log(final_log))
        report["combined_log_summary"] = filter_summary_for_tex(moved_tex, summarize_log(combined_log))
        report["auto_fixes"] = fixes
        report["final_warnings"] = actionable_warnings[:20]
        report["layout_warnings"] = layout_warnings[:20]

    return report


def candidate_tex_files() -> list[Path]:
    files = []
    for path in ROOT.glob("*.tex"):
        if path.name in IGNORE_FILES:
            continue
        files.append(path)
    return sorted(files)


def print_report(report: dict) -> None:
    if report["status"] != "moved":
        print(f"[skip] {report['file']}: {report.get('reason', 'unknown')}")
        return
    print(f"[move] {report['file']} -> {report['target']}")
    if report.get("created_dirs"):
        print(f"       created: {', '.join(report['created_dirs'])}")
    if report.get("placeholders"):
        print(f"       placeholders: {', '.join(report['placeholders'])}")
    if "compile_ok" in report:
        compile_status = "ok" if report["compile_ok"] else "error"
        print(f"       compile: {compile_status}")
        if report.get("auto_fixes"):
            print(f"       fixes: {', '.join(report['auto_fixes'])}")
        for line in report.get("log_summary", []):
            print(f"       {line}")
        if report.get("final_warnings"):
            print("       remaining warnings:")
            for line in report["final_warnings"][:8]:
                print(f"       {line}")
        if report.get("layout_warnings"):
            print(f"       layout warnings: {len(report['layout_warnings'])}")
            for line in report["layout_warnings"][:4]:
                print(f"       {line}")


def run_once(compile_after: bool, git_commit: bool = False, git_push: bool = False, commit_message: str | None = None) -> int:
    reports = []
    for tex_path in candidate_tex_files():
        reports.append(process_tex(tex_path, compile_after))
    if not reports:
        print("Aucun .tex nouveau a traiter a la racine.")
        return 0
    for report in reports:
        print_report(report)
    if git_commit or git_push:
        git_result = maybe_commit_and_push(reports, should_push=git_push, custom_message=commit_message)
        if git_result.committed:
            print(f"[git] commit: {git_result.message}")
        else:
            print("[git] aucun changement a commit")
        if git_result.pushed:
            print("[git] push: ok")
    return 0


def watch(
    interval: float,
    compile_after: bool,
    git_commit: bool = False,
    git_push: bool = False,
    commit_message: str | None = None,
) -> int:
    seen = set()
    print(f"Watching {ROOT} every {interval:.1f}s")
    while True:
        current = {p.resolve() for p in candidate_tex_files()}
        new_files = sorted(p for p in current if p not in seen)
        reports = []
        for resolved in new_files:
            report = process_tex(Path(resolved), compile_after)
            print_report(report)
            reports.append(report)
        if reports and (git_commit or git_push):
            git_result = maybe_commit_and_push(reports, should_push=git_push, custom_message=commit_message)
            if git_result.committed:
                print(f"[git] commit: {git_result.message}")
            else:
                print("[git] aucun changement a commit")
            if git_result.pushed:
                print("[git] push: ok")
        seen = current
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-manage TeX files dropped at repo root.")
    parser.add_argument("--watch", action="store_true", help="Watch the repo root and auto-process new .tex files.")
    parser.add_argument("--interval", type=float, default=2.0, help="Watch polling interval in seconds.")
    parser.add_argument("--no-compile", action="store_true", help="Move and patch without running latexmk.")
    parser.add_argument("--git-commit", action="store_true", help="Stage and commit repo changes after processing.")
    parser.add_argument("--git-push", action="store_true", help="Stage, commit, and push repo changes after processing.")
    parser.add_argument("--commit-message", help="Use a custom Conventional Commit message.")
    args = parser.parse_args()

    compile_after = not args.no_compile
    try:
        if args.watch:
            return watch(
                args.interval,
                compile_after,
                git_commit=args.git_commit or args.git_push,
                git_push=args.git_push,
                commit_message=args.commit_message,
            )
        return run_once(
            compile_after,
            git_commit=args.git_commit or args.git_push,
            git_push=args.git_push,
            commit_message=args.commit_message,
        )
    except Exception as exc:
        print(f"[fatal] {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
