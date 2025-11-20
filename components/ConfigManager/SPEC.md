<component_spec name="ConfigManager">
<package>gmake2cmake.config</package>
<purpose>Load, validate, and merge YAML configuration with CLI defaults; expose mapping helpers for flags/targets/paths.</purpose>
<dependencies>
- DiagnosticsReporter for validation findings.
- yaml loader (safe_load) only; no network.
</dependencies>
<data>
- class ConfigModel: project_name(str|None), version(str|None), namespace(str|None), languages(list[str]|None), target_mappings(dict[str, TargetMapping]), flag_mappings(dict[str, str]), ignore_paths(list[str]), custom_rules(dict[str, CustomRuleConfig]), global_config_files(list[str]), link_overrides(dict[str, LinkOverride]), packaging_enabled(bool), strict(bool).
- class TargetMapping: src_name(str), dest_name(str), type_override(str|None), link_libs(list[str]), include_dirs(list[str]), defines(list[str]), options(list[str]), visibility(str|None) for usage requirements.
- class CustomRuleConfig: match(pattern str), handler(str), cmake_stub(str|None).
- class LinkOverride: classification(enum{'internal','external','imported'}), alias(str|None), imported_target(str|None).
</data>
<functions>
  <function name="load_yaml" signature="load_yaml(path: Path, *, fs: FileSystemAdapter) -> dict">
  - Reads file as UTF-8; on missing file adds ERROR diagnostic code=CONFIG_MISSING; returns empty dict on failure.
  - Rejects YAML documents with non-mapping root (ERROR CONFIG_SCHEMA).</function>
  <function name="parse_model" signature="parse_model(raw: dict, strict: bool, diagnostics: DiagnosticCollector) -> ConfigModel">
  - Validates allowed keys; unknown keys -> WARN or ERROR when strict.
  - Normalizes ignore_paths to posix with no trailing slashes; deduplicates entries.
  - Normalizes target, flag, and link overrides to deterministic ordering.
  - Sets default global_config_files to ['config.mk','rules.mk','defs.mk'] when absent.
  - Sets default namespace to sanitized project_name if not provided.</function>
  <function name="load_and_merge" signature="load_and_merge(args: CLIArgs, diagnostics: DiagnosticCollector, fs: FileSystemAdapter) -> ConfigModel">
  - Resolves config from args.config_path if provided; else empty config.
  - Merges CLI-provided project metadata (if supplied later) and defaults for strict flag; ensures output_dir present in model.
  - Merges CLI with_packaging flag into packaging_enabled.
  - Emits INFO diagnostic when config loaded; WARN on optional config missing but path provided.</function>
  <function name="apply_flag_mapping" signature="apply_flag_mapping(flags: list[str], config: ConfigModel) -> tuple[list[str], list[str]]">
  - Returns (mapped_flags, unmapped_flags); mapped_flags include replacements from config.flag_mappings; unmapped_flags preserves original ordering; duplicates removed while preserving first occurrence.</function>
  <function name="should_ignore_path" signature="should_ignore_path(path: str, config: ConfigModel) -> bool">
  - Path normalized posix; returns True if matches any ignore entry via glob-style matching.</function>
  <function name="classify_library_override" signature="classify_library_override(lib_name: str, config: ConfigModel) -> LinkOverride|None">
  - Returns explicit override when provided to force internal/external/imported classification and alias/imported target name.</function>
</functions>
<contracts>
- Always return ConfigModel instance; never None; diagnostics capture errors.
- Strict flag propagates to schema validation; invalid entries must not silently drop.
- No mutable global state; all helpers pure functions except load_yaml/file I/O.
</contracts>
<testing>
- Load missing file -> ERROR CONFIG_MISSING.
- Unknown key with strict=True -> ERROR; strict=False -> WARN.
- Flag mapping deduplication and preservation order.
- Ignore path globbing covering nested dirs and relative/absolute inputs.
- Custom rule parsing ensures only str handlers accepted; invalid types -> ERROR.
- Global_config_files default applied when missing; override respected.
- Link overrides classification honored; packaging_enabled mirrors CLI flag.</testing>
</component_spec>
