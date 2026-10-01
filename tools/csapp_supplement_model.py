"""Shared model and source registry for the CS:APP deepening layer."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Term:
    name: str
    plain: str
    example: str


@dataclass(frozen=True)
class Supplement:
    section_id: str
    number: int
    title: str
    question: str
    contract: tuple[str, str, str]
    terms: tuple[Term, ...]
    blueprint: str
    narrative: str
    experiment: str
    pitfalls: tuple[str, ...]
    qa: tuple[tuple[str, str], ...]
    sources: tuple[str, ...]


SOURCES: dict[str, tuple[str, str]] = {
    "csapp-students": (
        "CS:APP3e Student Site",
        "https://csapp.cs.cmu.edu/3e/students.html",
    ),
    "csapp-courses": (
        "Courses Based on CS:APP",
        "https://csapp.cs.cmu.edu/3e/courses.html",
    ),
    "csapp-labs": (
        "CS:APP3e Lab Assignments",
        "https://csapp.cs.cmu.edu/3e/labs.html",
    ),
    "csapp-asides": (
        "CS:APP3e Web Asides",
        "https://csapp.cs.cmu.edu/3e/waside.html",
    ),
    "csapp-errata": (
        "CS:APP3e Errata",
        "https://csapp.cs.cmu.edu/3e/errata.html",
    ),
    "csapp-changes": (
        "Changes from CS:APP2e to CS:APP3e",
        "https://csapp.cs.cmu.edu/3e/changes3e.html",
    ),
    "sysv-abi": (
        "System V Application Binary Interface — AMD64",
        "https://gitlab.com/x86-psABIs/x86-64-ABI",
    ),
    "intel-sdm": (
        "Intel 64 and IA-32 Software Developer Manuals",
        "https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html",
    ),
    "gcc": (
        "GCC Online Documentation",
        "https://gcc.gnu.org/onlinedocs/",
    ),
    "gdb": (
        "GNU GDB Manual",
        "https://sourceware.org/gdb/current/onlinedocs/gdb.html/",
    ),
    "binutils": (
        "GNU Binutils Documentation",
        "https://sourceware.org/binutils/docs/",
    ),
    "linux-man": (
        "Linux man-pages",
        "https://man7.org/linux/man-pages/",
    ),
    "elf": (
        "Linux Standard Base — ELF",
        "https://refspecs.linuxfoundation.org/elf/elf.pdf",
    ),
    "posix": (
        "The Open Group Base Specifications",
        "https://pubs.opengroup.org/onlinepubs/9799919799/",
    ),
    "clang-asan": (
        "Clang AddressSanitizer",
        "https://clang.llvm.org/docs/AddressSanitizer.html",
    ),
    "clang-ubsan": (
        "Clang UndefinedBehaviorSanitizer",
        "https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html",
    ),
    "clang-tsan": (
        "Clang ThreadSanitizer",
        "https://clang.llvm.org/docs/ThreadSanitizer.html",
    ),
    "stanford-cs107": (
        "Stanford CS107 — Computer Organization & Systems",
        "https://web.stanford.edu/class/cs107/",
    ),
    "stanford-work": (
        "Stanford CS107 — Working on Assignments",
        "https://web.stanford.edu/class/cs107/working-on-assignments.html",
    ),
    "notes-open213": (
        "openCS 15-213 self-learning record",
        "https://github.com/zennlyu/openCS_15.213.CSAPP",
    ),
    "notes-akiyama": (
        "AkiyamaKunka CS:APP reading notes",
        "https://github.com/AkiyamaKunka/csapp-notes",
    ),
    "notes-yewentao": (
        "CSAPP 15-213 learning notes and lab map",
        "https://github.com/yewentao256/CSAPP_15213",
    ),
}


def S(
    section_id: str,
    number: int,
    title: str,
    question: str,
    contract: tuple[str, str, str],
    terms: list[tuple[str, str, str]],
    blueprint: str,
    narrative: str,
    experiment: str,
    pitfalls: list[str],
    qa: list[tuple[str, str]],
    sources: list[str],
) -> Supplement:
    supplement = Supplement(
        section_id=section_id,
        number=number,
        title=title,
        question=question,
        contract=contract,
        terms=tuple(Term(*term) for term in terms),
        blueprint=blueprint.strip(),
        narrative=narrative.strip(),
        experiment=experiment.strip(),
        pitfalls=tuple(pitfalls),
        qa=tuple(qa),
        sources=tuple(sources),
    )
    assert len(supplement.terms) >= 4
    assert len(supplement.blueprint) >= 80
    assert len(supplement.narrative) >= 1_800
    assert len(supplement.experiment) >= 280
    assert len(supplement.pitfalls) >= 4
    assert len(supplement.qa) >= 7
    assert len(supplement.sources) >= 2
    for key in supplement.sources:
        assert key in SOURCES, f"unknown source: {key}"
    return supplement
