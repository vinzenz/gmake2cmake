from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from gmake2cmake.constants import (
    VALID_CONFIG_TARGET_TYPES,
    VALID_LINK_CLASSIFICATIONS,
    VALID_VISIBILITY_LEVELS,
)
from gmake2cmake.diagnostics import DiagnosticCollector, add
from gmake2cmake.fs import FileSystemAdapter


def _sanitize_namespace(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


@dataclass
class TargetMapping:
    """Configuration for mapping Make target to CMake target.

    Attributes:
        src_name: Original Make target name
        dest_name: Target name in generated CMake
        type_override: Override target type (e.g., 'executable', 'library')
        link_libs: Additional libraries to link
        include_dirs: Additional include directories
        defines: Additional preprocessor defines
        options: Additional CMake options
        visibility: Visibility level (e.g., 'PUBLIC', 'PRIVATE')
    """

    src_name: str
    dest_name: str
    type_override: Optional[str] = None
    link_libs: List[str] = field(default_factory=list)
    include_dirs: List[str] = field(default_factory=list)
    defines: List[str] = field(default_factory=list)
    options: List[str] = field(default_factory=list)
    visibility: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.src_name or not self.src_name.strip():
            raise ValueError("src_name cannot be empty")
        if not self.dest_name or not self.dest_name.strip():
            raise ValueError("dest_name cannot be empty")
        if self.type_override is not None and self.type_override not in VALID_CONFIG_TARGET_TYPES:
            raise ValueError(f"Invalid type_override: {self.type_override}")
        if self.visibility is not None and self.visibility not in VALID_VISIBILITY_LEVELS:
            raise ValueError(f"Invalid visibility: {self.visibility}")


@dataclass
class CustomRuleConfig:
    match: str
    handler: str
    cmake_stub: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.match or not self.match.strip():
            raise ValueError("match cannot be empty")
        if not self.handler or not self.handler.strip():
            raise ValueError("handler cannot be empty")


@dataclass
class LinkOverride:
    classification: str
    alias: Optional[str] = None
    imported_target: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.classification or not self.classification.strip():
            raise ValueError("classification cannot be empty")
        if self.classification not in VALID_LINK_CLASSIFICATIONS:
            raise ValueError(f"Invalid classification: {self.classification}")


@dataclass
class ConfigModel:
    """Configuration model for gmake2cmake conversion.

    Attributes:
        project_name: CMake project name
        version: Project version string
        namespace: C++ namespace for generated code
        languages: Languages to enable in CMake (e.g., ['C', 'CXX'])
        target_mappings: Mapping of Make targets to CMake targets
        flag_mappings: Mapping of compiler flags
        ignore_paths: Paths to ignore during discovery
        custom_rules: Custom rule handlers
        global_config_files: Global config files to process (e.g., config.mk)
        link_overrides: Library classification overrides
        packaging_enabled: If True, generate install/export/package files
        strict: If True, treat unknown config keys as errors
    """

    project_name: Optional[str] = None
    version: Optional[str] = None
    namespace: Optional[str] = None
    languages: Optional[List[str]] = None
    target_mappings: Dict[str, TargetMapping] = field(default_factory=dict)
    flag_mappings: Dict[str, str] = field(default_factory=dict)
    ignore_paths: List[str] = field(default_factory=list)
    custom_rules: Dict[str, CustomRuleConfig] = field(default_factory=dict)
    global_config_files: List[str] = field(default_factory=list)
    link_overrides: Dict[str, LinkOverride] = field(default_factory=dict)
    packaging_enabled: bool = False
    strict: bool = False
    error_recovery_enabled: bool = True


def load_yaml(path: Path, *, fs: FileSystemAdapter, diagnostics: DiagnosticCollector) -> Dict:
    """Load and parse YAML configuration file.

    Args:
        path: Path to YAML configuration file
        fs: File system adapter for reading
        diagnostics: Collector for error/warning diagnostics

    Returns:
        Parsed dictionary, or empty dict if file not found or parsing fails
    """
    if not fs.exists(path):
        add(diagnostics, "ERROR", "CONFIG_MISSING", f"Config file not found: {path}")
        return {}
    try:
        raw_text = fs.read_text(path)
    except (IOError, OSError) as exc:  # pragma: no cover - IO error path
        add(diagnostics, "ERROR", "CONFIG_READ_FAIL", f"Failed to read config: {exc}")
        return {}
    try:
        data = yaml.safe_load(raw_text) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - parse error
        add(diagnostics, "ERROR", "CONFIG_PARSE_ERROR", f"Invalid YAML: {exc}")
        return {}
    if data and not isinstance(data, dict):
        add(diagnostics, "ERROR", "CONFIG_SCHEMA", "Config root must be a mapping")
        return {}
    return data


def parse_model(raw: Dict, strict: bool, diagnostics: DiagnosticCollector) -> ConfigModel:
    """Parse raw dictionary into ConfigModel with validation.

    Args:
        raw: Raw configuration dictionary
        strict: If True, treat unknown keys as errors
        diagnostics: Collector for validation diagnostics

    Returns:
        ConfigModel instance with parsed configuration
    """
    model = ConfigModel()
    allowed_keys = {
        "project_name",
        "version",
        "namespace",
        "languages",
        "target_mappings",
        "flag_mappings",
        "ignore_paths",
        "custom_rules",
        "global_config_files",
        "link_overrides",
        "packaging_enabled",
        "strict",
        "error_recovery_enabled",
    }
    _report_unknown_keys(raw, allowed_keys, strict, diagnostics)

    project_name = _extract_string_field(raw, "project_name", diagnostics)
    model.project_name = project_name

    version = _extract_string_field(raw, "version", diagnostics)
    model.version = version

    namespace = _extract_string_field(raw, "namespace", diagnostics)
    if not namespace:
        namespace = project_name if isinstance(project_name, str) else None
    model.namespace = _sanitize_namespace(namespace)
    model.languages = raw.get("languages")
    model.flag_mappings = dict(raw.get("flag_mappings", {}) or {})
    model.ignore_paths = _normalize_ignore_paths(raw.get("ignore_paths", []))
    model.target_mappings = _parse_target_mappings(raw.get("target_mappings", {}))
    model.custom_rules = _parse_custom_rules(raw.get("custom_rules", {}), diagnostics, strict)
    model.global_config_files = raw.get("global_config_files") or ["config.mk", "rules.mk", "defs.mk"]
    model.link_overrides = _parse_link_overrides(raw.get("link_overrides", {}), diagnostics, strict)
    model.packaging_enabled = bool(raw.get("packaging_enabled", False))
    model.strict = bool(raw.get("strict", strict))
    model.error_recovery_enabled = bool(raw.get("error_recovery_enabled", True))
    if model.strict:
        model.error_recovery_enabled = False
    return model


def _normalize_ignore_paths(paths: List[str]) -> List[str]:
    """Normalize ignore paths with validation.

    Args:
        paths: List of path patterns to normalize.

    Returns:
        List of normalized paths without duplicates.

    Raises:
        ValueError: If any path contains invalid patterns like '..' or is empty.
    """
    seen = set()
    normalized: List[str] = []
    for p in paths:
        # Validate input
        if not p or not p.strip():
            raise ValueError("Path pattern cannot be empty")
        if ".." in p:
            raise ValueError(f"Path traversal (..) not allowed in pattern: {p}")

        norm = p.replace("\\", "/").rstrip("/")
        if norm in seen:
            continue
        seen.add(norm)
        normalized.append(norm)
    return normalized


def _parse_target_mappings(raw: Dict) -> Dict[str, TargetMapping]:
    mappings: Dict[str, TargetMapping] = {}
    for name, spec in (raw or {}).items():
        mappings[name] = TargetMapping(
            src_name=name,
            dest_name=spec.get("dest_name") or spec.get("name") or name,
            type_override=spec.get("type_override"),
            link_libs=list(spec.get("link_libs", [])),
            include_dirs=list(spec.get("include_dirs", [])),
            defines=list(spec.get("defines", [])),
            options=list(spec.get("options", [])),
            visibility=spec.get("visibility"),
        )
    return dict(sorted(mappings.items(), key=lambda x: x[0]))


def _parse_custom_rules(raw: Dict, diagnostics: DiagnosticCollector, strict: bool) -> Dict[str, CustomRuleConfig]:
    parsed: Dict[str, CustomRuleConfig] = {}
    for name, spec in (raw or {}).items():
        if not isinstance(spec, dict) or not isinstance(spec.get("handler"), str):
            add(
                diagnostics,
                "ERROR" if strict else "WARN",
                "CONFIG_CUSTOM_RULE_INVALID",
                f"Custom rule {name} invalid",
            )
            continue
        parsed[name] = CustomRuleConfig(
            match=spec.get("match", name),
            handler=spec["handler"],
            cmake_stub=spec.get("cmake_stub"),
        )
    return parsed


def _parse_link_overrides(raw: Dict, diagnostics: DiagnosticCollector, strict: bool) -> Dict[str, LinkOverride]:
    parsed: Dict[str, LinkOverride] = {}
    for name, spec in (raw or {}).items():
        classification = spec.get("classification")
        if classification not in {"internal", "external", "imported"}:
            add(
                diagnostics,
                "ERROR" if strict else "WARN",
                "CONFIG_LINK_OVERRIDE_INVALID",
                f"Link override for {name} missing or invalid classification",
            )
            continue
        parsed[name] = LinkOverride(
            classification=classification,
            alias=spec.get("alias"),
            imported_target=spec.get("imported_target"),
        )
    return parsed


def _extract_string_field(raw: Dict, field: str, diagnostics: DiagnosticCollector) -> Optional[str]:
    value = raw.get(field)
    if value is not None and not isinstance(value, str):
        add(
            diagnostics,
            "ERROR",
            "CONFIG_SCHEMA_VALIDATION",
            f"{field} must be a string, got {type(value).__name__}",
        )
        return None
    return value


def _report_unknown_keys(raw: Dict, allowed_keys: set[str], strict: bool, diagnostics: DiagnosticCollector) -> None:
    for key in list(raw.keys()):
        if key not in allowed_keys:
            severity = "ERROR" if strict else "WARN"
            add(diagnostics, severity, "CONFIG_UNKNOWN_KEY", f"Unknown config key: {key}")


def load_and_merge(args, diagnostics: DiagnosticCollector, fs: FileSystemAdapter) -> ConfigModel:
    raw = {}
    if getattr(args, "config_path", None):
        raw = load_yaml(Path(args.config_path), fs=fs, diagnostics=diagnostics)
        # Validate loaded config against schema
        from gmake2cmake.schema_validator import validate_config_schema
        validate_config_schema(raw, diagnostics)
    model = parse_model(raw, bool(getattr(args, "strict", False)), diagnostics)
    if args and getattr(args, "with_packaging", False):
        model.packaging_enabled = True
    model.project_name = model.project_name or _infer_project_name(args)
    model.namespace = _sanitize_namespace(model.namespace or model.project_name)
    return model


def _infer_project_name(args) -> Optional[str]:
    try:
        return Path(args.source_dir).resolve().name
    except (OSError, ValueError):  # pragma: no cover - defensive fallback for path resolution
        return None


def apply_flag_mapping(flags: List[str], config: ConfigModel) -> Tuple[List[str], List[str]]:
    mapped: List[str] = []
    unmapped: List[str] = []
    seen = set()
    for flag in flags:
        mapped_flag = config.flag_mappings.get(flag, flag)
        if mapped_flag not in seen:
            mapped.append(mapped_flag)
            seen.add(mapped_flag)
        if flag not in config.flag_mappings:
            unmapped.append(flag)
    return mapped, unmapped


def should_ignore_path(path: str, config: ConfigModel) -> bool:
    norm = path.replace("\\", "/")
    for pattern in config.ignore_paths:
        if Path(norm).match(pattern):
            return True
    return False


def classify_library_override(lib_name: str, config: ConfigModel) -> Optional[LinkOverride]:
    return config.link_overrides.get(lib_name)
