"""Pattern rule instantiation for IRBuilder.

Converts pattern rules (e.g., %.o: %.c) into concrete targets based on
discovered prerequisites and filesystem state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.ir.unknowns import UnknownConstructFactory
from gmake2cmake.make.evaluator import EvaluatedRule


@dataclass
class PatternMatch:
    """Result of matching a pattern rule against a source file."""

    source: str
    target: str
    pattern: str
    stem: str


@dataclass
class PatternInstantiationResult:
    """Result of pattern rule instantiation."""

    instantiated_rules: List[EvaluatedRule] = field(default_factory=list)
    pattern_mappings: Dict[str, List[str]] = field(default_factory=dict)
    """Maps pattern to list of generated targets."""
    unmappable_patterns: List[str] = field(default_factory=list)
    """Pattern rules that couldn't be mapped."""


def instantiate_patterns(
    rules: List[EvaluatedRule],
    source_dir: Path,
    diagnostics: DiagnosticCollector,
    unknown_factory: Optional[UnknownConstructFactory] = None,
) -> PatternInstantiationResult:
    """Instantiate pattern rules into concrete rules based on filesystem.

    Args:
        rules: List of rules (mixed regular and pattern rules)
        source_dir: Root directory for searching sources
        diagnostics: Diagnostic collector for error reporting
        unknown_factory: Factory for creating unknown constructs

    Returns:
        PatternInstantiationResult with instantiated rules
    """
    result = PatternInstantiationResult()
    pattern_rules = [r for r in rules if r.is_pattern]
    regular_rules = [r for r in rules if not r.is_pattern]

    # Process each pattern rule
    for pattern_rule in pattern_rules:
        if not _is_simple_pattern(pattern_rule):
            result.unmappable_patterns.append(str(pattern_rule.targets))
            if unknown_factory:
                unknown_factory.create(
                    category="pattern_rule",
                    file=pattern_rule.location.path,
                    raw_snippet=f"{pattern_rule.targets[0]}: {' '.join(pattern_rule.prerequisites)}",
                    line=pattern_rule.location.line,
                    context={"type": "complex_pattern"},
                )
            continue

        # Find sources matching the pattern
        matches = _find_pattern_matches(pattern_rule, source_dir, diagnostics)

        if not matches:
            add(
                diagnostics,
                "WARN",
                "IR_NO_PATTERN_MATCHES",
                f"Pattern rule {pattern_rule.targets[0]} found no matches",
            )
            continue

        # Instantiate concrete rules
        instantiated = _instantiate_from_matches(pattern_rule, matches)
        result.instantiated_rules.extend(instantiated)

        # Track pattern mappings
        pattern = pattern_rule.targets[0]
        result.pattern_mappings[pattern] = [m.target for m in matches]

    # Return regular rules plus instantiated rules
    result.instantiated_rules.extend(regular_rules)
    return result


def _is_simple_pattern(rule: EvaluatedRule) -> bool:
    """Check if pattern rule is simple enough to instantiate.

    Simple patterns:
    - Single target with one %
    - Single prerequisite with one %
    - Pattern like %.o: %.c or %.o: %.cpp

    Args:
        rule: Evaluated rule to check

    Returns:
        True if pattern is simple and instantiable
    """
    if len(rule.targets) != 1 or len(rule.prerequisites) == 0:
        return False

    target_pattern = rule.targets[0]
    if target_pattern.count("%") != 1:
        return False

    # For now, only handle single prerequisite patterns
    if len(rule.prerequisites) > 1:
        return False

    prereq_pattern = rule.prerequisites[0]
    if prereq_pattern.count("%") != 1:
        return False

    # Ensure patterns are simple (just a stem substitution)
    return ":" not in target_pattern and ":" not in prereq_pattern


def _find_pattern_matches(rule: EvaluatedRule, source_dir: Path, diagnostics: DiagnosticCollector) -> List[PatternMatch]:
    """Find source files matching a pattern rule.

    Searches for files matching the prerequisite pattern and creates
    matches for corresponding target files.

    Args:
        rule: Pattern rule to match
        source_dir: Root directory to search in
        diagnostics: For logging

    Returns:
        List of PatternMatch objects
    """
    pattern_str = rule.prerequisites[0]
    matches: List[PatternMatch] = []

    try:
        # Build a regex from the pattern
        # Pattern like "%.c" becomes regex r"(.+)\.c$"
        regex_pattern = _pattern_to_regex(pattern_str)
        regex = re.compile(regex_pattern)

        # Recursively search for matching files
        for source_file in _find_files_recursive(source_dir):
            match = regex.match(source_file.name)
            if match:
                stem = match.group(1)
                target_pattern = rule.targets[0]
                target_file = target_pattern.replace("%", stem)

                matches.append(
                    PatternMatch(
                        source=source_file.as_posix(),
                        target=target_file,
                        pattern=pattern_str,
                        stem=stem,
                    )
                )
    except Exception as e:
        add(
            diagnostics,
            "WARN",
            "IR_PATTERN_ERROR",
            f"Failed to process pattern {pattern_str}: {e}",
        )

    return matches


def _pattern_to_regex(pattern: str) -> str:
    """Convert makefile pattern to regex.

    Args:
        pattern: Pattern like "%.c" or "src/%.o"

    Returns:
        Regex pattern string
    """
    # If this is a full pattern like "%.o: %.c", extract just prerequisite
    if ":" in pattern:
        pattern = pattern.split(":", 1)[1].strip()

    # Replace % with temporary placeholder before escaping
    placeholder = "__PERCENT__"
    temp = pattern.replace("%", placeholder)

    # Escape special regex characters
    escaped = re.escape(temp)

    # Replace placeholder with capture group
    regex_pattern = escaped.replace(placeholder, "(.+)")

    # Anchor to end of string
    return f"^{regex_pattern}$"


def _find_files_recursive(directory: Path, max_depth: int = 10) -> List[Path]:
    """Find all files recursively up to a depth limit.

    Args:
        directory: Root directory to search
        max_depth: Maximum recursion depth

    Returns:
        List of file paths
    """
    files: List[Path] = []

    def _traverse(current_dir: Path, depth: int) -> None:
        if depth > max_depth or not current_dir.is_dir():
            return

        try:
            for entry in sorted(current_dir.iterdir()):
                if entry.is_file() and not entry.name.startswith("."):
                    files.append(entry)
                elif entry.is_dir() and not entry.name.startswith("."):
                    _traverse(entry, depth + 1)
        except (PermissionError, OSError):
            # Skip inaccessible directories
            pass

    _traverse(directory, 0)
    return files


def _instantiate_from_matches(rule: EvaluatedRule, matches: List[PatternMatch]) -> List[EvaluatedRule]:
    """Create concrete rules from pattern matches.

    Deterministically orders results by source filename.

    Args:
        rule: Pattern rule template
        matches: List of matches

    Returns:
        List of instantiated EvaluatedRule objects
    """
    instantiated: List[EvaluatedRule] = []

    # Sort by source file for deterministic ordering
    sorted_matches = sorted(matches, key=lambda m: m.source)

    for match in sorted_matches:
        # Create concrete rule from pattern template
        concrete_rule = EvaluatedRule(
            targets=[match.target],
            prerequisites=[match.source],
            commands=rule.commands,  # Copy commands from pattern
            is_pattern=False,
            location=rule.location,
        )
        instantiated.append(concrete_rule)

    return instantiated


def detect_pattern_priority(patterns: List[str], source_file: str) -> Optional[str]:
    """Detect which pattern has priority for a source file.

    When multiple patterns match (e.g., %.o: %.c and %.o: %.cpp),
    determine which should be used based on specificity and convention.

    Args:
        patterns: List of prerequisite patterns
        source_file: Source file to match

    Returns:
        Winning pattern or None if no match
    """
    matches: List[Tuple[str, int]] = []

    for pattern in patterns:
        regex = re.compile(_pattern_to_regex(pattern))
        if regex.match(source_file):
            # Score by specificity: longer non-% part is more specific
            specificity = len(pattern) - pattern.count("%")
            matches.append((pattern, specificity))

    if not matches:
        return None

    # Return pattern with highest specificity, ties broken by order
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[0][0]
