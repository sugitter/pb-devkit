# PowerScript Plugin for JetBrains IDE

PowerScript (PowerBuilder) language support for IntelliJ IDEA and other JetBrains IDEs.

## Features

| Feature | Description |
|---------|-------------|
| **Syntax Highlighting** | Keywords, types, strings, comments, embedded SQL, DataWindow expressions, PB constants |
| **Lint Diagnostics** | 10 rules (same as pb-devkit CLI): empty_catch(E), routine_too_long/deep_nesting/high_complexity/deprecated_function/hardcoded_sql/select_star(W), global_variable/no_error_handling/magic_numbers(I) |
| **Code Completion** | 130+ items: keywords, types, PB built-in functions, object methods |
| **Hover Documentation** | Type info, SQLCA properties, function syntax |
| **Code Folding** | Routine/event blocks, comment blocks, $PBExportHeader regions |
| **Smart Editing** | Auto-indent, brace matching, `//` and `'` comment toggle |
| **File Types** | .srw .sru .srd .srf .srm .sra .srs .srq .srp .srj .srx .sre .src (13 types) |
| **Tools Menu** | Run PowerScript Lint on current file |

## Build

```bash
cd idea-plugin
./gradlew buildPlugin
```

The built plugin zip will be at `build/distributions/powerscript-1.0.0.zip`.

## Install

1. **From disk**: Settings → Plugins → ⚙️ → Install from disk → select the `.zip`
2. **From source**: `./gradlew runIde` to launch a sandbox IDE with the plugin

## Compatible IDEs

- IntelliJ IDEA 2023.2+ (IC/UE)
- WebStorm 2023.2+
- PyCharm 2023.2+
- DataGrip 2023.2+
- Any JetBrains IDE built on IntelliJ Platform 232+

## Requirements

- JDK 17+
- IntelliJ Platform Plugin SDK (managed by Gradle)

## Lint Rules

| Rule | Level | Description |
|------|-------|-------------|
| Empty CATCH block | ERROR | `catch` block is empty (no logging) |
| Routine too long | WARNING | Function/subroutine exceeds 200 lines |
| Deep nesting | WARNING | Nesting depth exceeds 4 levels |
| High complexity | WARNING | Cyclomatic complexity exceeds 20 |
| Deprecated function | WARNING | Uses deprecated PB functions |
| Hardcoded SQL | WARNING | SQL embedded directly in scripts |
| SELECT * | WARNING | Uses `SELECT *` instead of explicit columns |
| Global variable | INFO | Uses global variables (coupling risk) |
| No error handling | INFO | Function lacks try-catch |
| Magic numbers | INFO | Unnamed numeric literals |

## Project Structure

```
src/main/java/com/pbdevkit/powerscript/
├── PSLanguage.java              # Language definition
├── PSFileType.java              # File type registration
├── PSLexer.java                 # JFlex-style lexer (hand-written)
├── PSParser.java                # Psi parser
├── PSParserDefinition.java      # Parser definition
├── PSTokenTypes.java            # Token types
├── PSSyntaxHighlighter.java     # Syntax highlighting colors
├── PSSyntaxHighlighterFactory.java
├── PSCommenter.java             # Comment toggle
├── PSBraceMatcher.java          # Bracket matching
├── PSIndentStrategy.java        # Auto-indent
├── PSFoldingBuilder.java        # Code folding
├── PBIcons.java                 # Plugin icons
├── PSApplicationComponent.java  # Application lifecycle
├── completion/
│   └── PSCompletionContributor.java
├── hover/
│   └── PSDocumentationProvider.java
├── inspections/
│   ├── PSRoutineParser.java     # Shared routine parser for inspections
│   ├── EmptyCatchInspection.java
│   ├── RoutineTooLongInspection.java
│   ├── DeepNestingInspection.java
│   ├── HighComplexityInspection.java
│   ├── DeprecatedFunctionInspection.java
│   ├── HardcodedSqlInspection.java
│   ├── SelectStarInspection.java
│   ├── GlobalVariableInspection.java
│   ├── NoErrorHandlingInspection.java
│   └── MagicNumbersInspection.java
└── actions/
    └── RunLintFileAction.java   # Tools menu action
```

## License

MIT
