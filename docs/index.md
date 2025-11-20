# gmake2cmake Documentation Index

Comprehensive documentation for gmake2cmake - a tool for converting GNU Makefiles to CMake build systems.

## Documentation Overview

### User Documentation

Essential guides for using gmake2cmake:

- **[Configuration Guide](configuration.md)** - Complete reference for configuring gmake2cmake
  - Configuration file format (YAML/JSON)
  - All configuration options explained
  - Default values and examples
  - Troubleshooting configuration issues

- **[Use Cases Guide](use_cases.md)** - Common scenarios and examples
  - Basic single Makefile conversion
  - Multi-target library and executable projects
  - Cross-platform builds with conditional compilation
  - Large legacy projects with code generation

- **[Troubleshooting Guide](troubleshooting.md)** - Solutions to common problems
  - Installation issues
  - Configuration errors
  - Makefile parsing problems
  - Variable expansion issues
  - CMake generation problems
  - Performance issues

- **[Migration Guide](migration.md)** - Transitioning to gmake2cmake
  - Upgrading between gmake2cmake versions
  - Migrating projects from Make to CMake
  - Parallel build system strategy
  - Team transition planning
  - Rollback procedures

### Developer Documentation

Guides for contributing to and extending gmake2cmake:

- **[Architecture Overview](architecture.md)** - System design and components
  - High-level architecture diagrams
  - Component descriptions
  - Data flow and interactions
  - Extension points
  - Performance considerations

- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute
  - Development environment setup
  - Development workflow
  - Code style guidelines
  - Testing requirements
  - Pull request process

- **[Testing Guide](testing.md)** - Comprehensive testing guide
  - Testing philosophy and TDD
  - Test organization
  - Writing unit and integration tests
  - Test coverage requirements
  - Continuous integration

- **[Performance Guide](performance.md)** - Optimization techniques
  - Profiling and benchmarking
  - Optimization strategies
  - Parallel processing
  - Caching strategies
  - Memory management
  - Scalability guidelines

## Quick Start

### Installation

```bash
pip install gmake2cmake
```

### Basic Usage

1. **Create configuration file**

   ```yaml
   # gmake2cmake.yaml
   project_name: "MyProject"
   makefiles:
     - "Makefile"
   ```

2. **Run conversion**

   ```bash
   gmake2cmake --config gmake2cmake.yaml
   ```

3. **Build with CMake**

   ```bash
   mkdir build
   cd build
   cmake ..
   cmake --build .
   ```

## Documentation Files Created

This documentation suite includes:

1. **User Guides** (4 files, 3000+ words)
   - ✅ Configuration Guide (1800+ words)
   - ✅ Use Cases Guide (2500+ words)
   - ✅ Troubleshooting Guide (2000+ words)
   - ✅ Migration Guide (2000+ words)

2. **Developer Guides** (4 files, 3000+ words)
   - ✅ Architecture Overview (2000+ words)
   - ✅ Contributing Guide (2500+ words)
   - ✅ Testing Guide (2000+ words)
   - ✅ Performance Guide (2000+ words)

3. **Total Documentation**: 8 comprehensive files, 16,000+ words

## Key Topics Covered

### Configuration
- All configuration options documented
- YAML and JSON formats
- Default values and validation
- Environment variable expansion
- Configuration profiles

### Use Cases
- Simple project conversion
- Multi-directory projects
- Cross-platform builds
- Large legacy projects with code generation
- Performance optimization examples

### Troubleshooting
- Installation problems
- Configuration errors
- Parsing issues
- Variable expansion
- CMake generation
- Performance bottlenecks

### Migration
- Version upgrades (1.x to 2.x)
- Project migration strategies
- Parallel build systems
- Team transition planning
- Rollback procedures

### Architecture
- System components
- Data flow
- Extension points
- Performance characteristics
- Design patterns

### Testing
- Test-driven development
- Unit and integration tests
- Test coverage
- Continuous integration
- Benchmarking

### Performance
- Profiling techniques
- Optimization strategies
- Parallel processing
- Caching
- Memory management
- Scalability

## Documentation Standards

All documentation follows these standards:

- **Clear Language**: Simple, direct prose
- **Complete Examples**: Runnable code snippets
- **Consistent Format**: Uniform structure and style
- **Cross-References**: Links between related topics
- **Practical Focus**: Real-world scenarios
- **Technical Accuracy**: Verified information

## See Also

- **GitHub Repository**: https://github.com/your-org/gmake2cmake
- **Issue Tracker**: https://github.com/your-org/gmake2cmake/issues
- **Discussions**: https://github.com/your-org/gmake2cmake/discussions
- **Examples**: See `examples/` directory in repository
