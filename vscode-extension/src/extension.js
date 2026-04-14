/**
 * PowerScript VS Code Extension
 *
 * Features:
 * - Syntax highlighting (via TextMate grammar)
 * - Real-time linting / diagnostics
 * - Hover documentation for PB types and functions
 * - Code completion for keywords, types, and functions
 * - Commands: run lint on file / directory
 */

const vscode = require('vscode');

// ──────────────────────────────────────────────
// PowerScript Keywords & Types (for completion)
// ──────────────────────────────────────────────

const PS_KEYWORDS = [
    'if', 'then', 'else', 'elseif', 'end if',
    'choose case', 'case', 'end choose',
    'for', 'to', 'step', 'next',
    'do while', 'do until', 'loop', 'end loop',
    'try', 'catch', 'finally', 'end try', 'throw',
    'continue', 'exit', 'return', 'goto',
    'create', 'destroy', 'call', 'super', 'parent', 'this',
    'post', 'dynamic', 'not', 'and', 'or', 'is', 'null',
    'true', 'false', 'using', 'within', 'from',
    'global', 'type', 'end type', 'forward',
    'event', 'end event', 'on', 'end on',
    'prototype', 'end prototype', 'prototypes',
    'variables', 'end variables',
    'subroutine', 'end subroutine', 'function', 'end function',
    'constant', 'read-only', 'autoinstantiate',
];

const PS_TYPES = [
    'integer', 'int', 'long', 'longlong', 'ulong', 'uint',
    'dec', 'decimal', 'real', 'double',
    'string', 'blob', 'char', 'nchar',
    'date', 'time', 'datetime', 'boolean', 'any', 'unsigned',
    'window', 'menu', 'datawindow', 'datastore',
    'commandbutton', 'singlelineedit', 'multilineedit',
    'dropdownlistbox', 'picture', 'picturebutton',
    'graph', 'progressbar', 'tab',
    'userobject', 'nonvisualobject',
    'transaction', 'structure', 'enumeration',
    'treeview', 'listview', 'datawindowchild',
    'richtextedit', 'statictext', 'groupbox',
    'checkbox', 'radiobutton', 'editmask',
    'PowerObject', 'NonVisualObject',
    'oleobject', 'olestream',
    'mailsession', 'mailmessage',
    'inet', 'hyperlink', 'pipeline',
    'connection', 'internetresult',
    'corbaobject', 'mdiframe',
];

const PS_ACCESS = [
    'public', 'private', 'protected', 'shared', 'instance', 'global',
];

const PS_FUNCTIONS = [
    // String functions
    'Len', 'Left', 'Right', 'Mid', 'Upper', 'Lower', 'Trim', 'LeftTrim', 'RightTrim',
    'Replace', 'Pos', 'Match', 'LastPos', 'Reverse', 'Space', 'Fill', 'Asc', 'Char',
    'String', 'IsNumber', 'IsDate', 'IsTime', 'IsDateTime', 'IsNullOrEmpty',
    // Numeric functions
    'Abs', 'Ceiling', 'Floor', 'Int', 'Max', 'Min', 'Mod', 'Rand', 'Round', 'Sign',
    'Sqrt', 'Truncate', 'Real', 'Double', 'Dec', 'Integer', 'Long',
    // Date/Time functions
    'Today', 'Now', 'Year', 'Month', 'Day', 'Hour', 'Minute', 'Second',
    'RelativeDate', 'RelativeTime', 'Date', 'DateTime', 'Time', 'DaysAfter',
    'SecondsAfter', 'LastDay', 'DayNumber', 'DayName', 'MonthName',
    // DataWindow functions
    'SetItem', 'GetItemString', 'GetItemNumber', 'GetItemDecimal',
    'GetItemDate', 'GetItemDateTime', 'GetItemStatus',
    'InsertRow', 'DeleteRow', 'RowsCopy', 'RowsMove', 'RowsDiscard',
    'Retrieve', 'Update', 'Reset', 'SetFilter', 'SetSort', 'Sort',
    'SetTransObject', 'SetTrans', 'GetSQLSelect', 'SetSQLSelect',
    'GetChild', 'GetRow', 'GetClickedRow', 'GetSelectedRow',
    'IsSelected', 'SelectRow', 'GroupCalc', 'ShareData',
    'ImportString', 'ImportFile', 'ImportClipboard',
    'Describe', 'Modify', 'SetRedraw', 'SetFocus',
    'Object', 'Data', 'Buffer',
    'Print', 'Save', 'RowCount', 'ModifiedCount', 'DeletedCount', 'FilteredCount',
    // File functions
    'FileOpen', 'FileRead', 'FileWrite', 'FileClose', 'FileExists', 'FileLength',
    'FileDelete', 'FileCopy', 'FileMove', 'FileSeek', 'GetFileOpenName', 'GetFileSaveName',
    // MessageBox
    'MessageBox', 'Open', 'Close', 'OpenWithParm', 'OpenSheet', 'OpenSheetWithParm',
    'SetPointer', 'Yield', 'SetMicroHelp', 'SetStatus',
    // Misc
    'Create', 'Destroy', 'ClassName', 'TypeOf', 'IsValid', 'PostEvent', 'TriggerEvent',
    'SetDynamicType', 'SetNull', 'IsNull', 'SetProfileString', 'GetProfileString',
    'Run', 'Handle',
];

const PS_OBJECT_FUNCTIONS = [
    // Window object
    'Hide', 'Show', 'BringToFront', 'SetPosition', 'Move', 'Resize',
    'Center', 'SetTabOrder', 'GetActiveSheet', 'GetFirstSheet',
    // Control
    'GetParent', 'TriggerEvent', 'PostEvent', 'SetFocus',
    // DataWindow control
    'SetTransObject', 'Retrieve', 'Update', 'InsertRow', 'DeleteRow',
    'GetItemString', 'GetItemNumber', 'SetItem', 'SetFilter', 'SetSort',
    'Modify', 'Describe', 'GetSQLSelect', 'SetSQLSelect',
];

// ──────────────────────────────────────────────
// Lint Rules (mirrors pb-devkit sr_parser.py)
// ──────────────────────────────────────────────

const DEPRECATED_FUNCTIONS = [
    { pattern: /\bSetPointer\s*\(/, message: 'SetPointer is deprecated — use Pointer property' },
    { pattern: /\bYield\s*\(\s*\)/, message: 'Yield() is deprecated — use Timer for async' },
    { pattern: /\bDoEvents\b/, message: 'DoEvents is deprecated — use Timer for async' },
    { pattern: /\bRGB\b(?!\s*\()/, message: 'RGB is deprecated — use Long color constants' },
    { pattern: /\bSetRedraw\s*\(/, message: 'SetRedraw is deprecated — use SetRedraw property' },
];

const SQL_PATTERNS = [
    /\bSELECT\s+\*/i,
    /\bEXEC(?:UTE)?\s+IMMEDIATE\s+['"]/i,
    /\bSQLCA\.(?:SQLCode|DBCode)/i,
];

const MAGIC_NUMBERS_RE = /(?<![.\w])(\d+)(?![.\w])/g;
const SAFE_NUMBERS = new Set([
    0, 1, -1, 2, 4, 8, 10, 16, 32, 64, 100,
    128, 256, 512, 1000, 1024, 2048, 8192, 32767, 65536
]);

/**
 * Lint a single PowerScript file and return diagnostics.
 */
function lintDocument(document, config) {
    const diagnostics = [];
    const text = document.getText();
    const lines = text.split(/\r?\n/);

    if (!config.enableLinting) return diagnostics;

    // ── Parse routines (simplified) ──
    const routines = [];
    let currentRoutine = null;
    let routineDepth = 0;
    let inHeader = true;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Detect routine start
        const routineMatch = line.match(
            /^(?:forward\s+)?(?:public|private|protected|global)?\s*(subroutine|function)\s+(?:\w+\s+)?(\w+)/i
        );
        const eventMatch = line.match(/^on\s+(\w+)\.(\w+)/i);

        if (routineMatch || eventMatch) {
            inHeader = false;
            if (currentRoutine) {
                routines.push(currentRoutine);
            }
            currentRoutine = {
                name: routineMatch ? routineMatch[2] : `${eventMatch[1]}.${eventMatch[2]}`,
                startLine: i,
                endLine: i,
                body: [],
                isEvent: !!eventMatch,
                depth: 0,
            };
            routineDepth = 0;
            continue;
        }

        // Detect routine end
        if (currentRoutine && /^\s*end\s+(subroutine|function|on)\b/i.test(line)) {
            currentRoutine.endLine = i;
            routines.push(currentRoutine);
            currentRoutine = null;
            routineDepth = 0;
            continue;
        }

        // Collect body
        if (currentRoutine) {
            currentRoutine.body.push({ line: i, text: line });
            // Track nesting
            if (/^(if|for|do|try|choose\s+case)\b/i.test(line)) {
                routineDepth++;
                currentRoutine.depth = Math.max(currentRoutine.depth, routineDepth);
            }
            if (/^end\s+(if|for|do|try|choose)\b/i.test(line)) {
                routineDepth = Math.max(0, routineDepth - 1);
            }
        }
    }
    if (currentRoutine) {
        routines.push(currentRoutine);
    }

    // ── Check each routine ──
    for (const routine of routines) {
        const codeLines = routine.body.filter(
            l => l.text && !l.text.startsWith('//') && !l.text.startsWith("'")
        );
        const fullScript = routine.body.map(l => l.text).join('\n');

        // routine_too_long
        if (codeLines.length > config.maxRoutineLines) {
            diagnostics.push({
                severity: vscode.DiagnosticSeverity.Warning,
                range: new vscode.Range(routine.startLine, 0, routine.startLine, 80),
                message: `'${routine.name}' has ${codeLines.length} lines (recommend <${config.maxRoutineLines})`,
                code: 'routine_too_long',
                source: 'PowerScript',
                tags: [vscode.DiagnosticTag.Unnecessary],
            });
        }

        // deep_nesting
        if (routine.depth > config.maxNesting) {
            diagnostics.push({
                severity: vscode.DiagnosticSeverity.Warning,
                range: new vscode.Range(routine.startLine, 0, routine.startLine, 80),
                message: `'${routine.name}' has nesting depth ${routine.depth} (recommend <${config.maxNesting})`,
                code: 'deep_nesting',
                source: 'PowerScript',
            });
        }

        // empty_catch
        if (config.enableEmptyCatchCheck) {
            const catchRe = /catch\s*\([^)]*\)\s*\n(\s*(?:(?:\/\/|').*)?\s*\n)*\s*end\s+try/i;
            if (catchRe.test(fullScript)) {
                diagnostics.push({
                    severity: vscode.DiagnosticSeverity.Error,
                    range: new vscode.Range(routine.startLine, 0, routine.startLine, 80),
                    message: `'${routine.name}' has empty CATCH block — error silently swallowed`,
                    code: 'empty_catch',
                    source: 'PowerScript',
                });
            }
        }

        // no_error_handling (functions only, not events)
        if (routine.isEvent === false && !/try\b/i.test(fullScript)) {
            diagnostics.push({
                severity: vscode.DiagnosticSeverity.Information,
                range: new vscode.Range(routine.startLine, 0, routine.startLine, 80),
                message: `'${routine.name}' lacks try-catch error handling`,
                code: 'no_error_handling',
                source: 'PowerScript',
            });
        }

        // deprecated functions
        if (config.enableDeprecatedCheck) {
            for (const dep of DEPRECATED_FUNCTIONS) {
                const m = fullScript.match(dep.pattern);
                if (m) {
                    const idx = fullScript.indexOf(m[0]);
                    const lineIdx = fullScript.substring(0, idx).split('\n').length - 1;
                    const diagLine = routine.body[Math.max(0, lineIdx)];
                    if (diagLine) {
                        diagnostics.push({
                            severity: vscode.DiagnosticSeverity.Warning,
                            range: new vscode.Range(diagLine.line, 0, diagLine.line, 80),
                            message: dep.message,
                            code: 'deprecated_function',
                            source: 'PowerScript',
                        });
                    }
                }
            }
        }

        // hardcoded SQL
        if (config.enableHardcodedSqlCheck) {
            for (const sqlRe of SQL_PATTERNS) {
                if (sqlRe.test(fullScript)) {
                    diagnostics.push({
                        severity: vscode.DiagnosticSeverity.Warning,
                        range: new vscode.Range(routine.startLine, 0, routine.startLine, 80),
                        message: `'${routine.name}' uses hardcoded SQL — consider using DataWindow`,
                        code: 'hardcoded_sql',
                        source: 'PowerScript',
                    });
                    break; // Only report once per routine
                }
            }
        }

        // magic numbers
        const magicNums = new Set();
        let magicMatch;
        MAGIC_NUMBERS_RE.lastIndex = 0;
        while ((magicMatch = MAGIC_NUMBERS_RE.exec(fullScript)) !== null) {
            const num = parseInt(magicMatch[1]);
            if (!SAFE_NUMBERS.has(num) && num > 2 && num < 100000) {
                // Check not in a comment
                const prefix = fullScript.substring(
                    Math.max(0, fullScript.lastIndexOf('\n', magicMatch.index)),
                    magicMatch.index
                );
                if (!prefix.includes('//') && !prefix.includes("'")) {
                    magicNums.add(num);
                }
            }
            if (magicNums.size >= 10) break;
        }
        if (magicNums.size > 0) {
            const nums = [...magicNums].slice(0, 5).join(', ');
            diagnostics.push({
                severity: vscode.DiagnosticSeverity.Information,
                range: new vscode.Range(routine.startLine, 0, routine.startLine, 80),
                message: `'${routine.name}' uses magic numbers: ${nums}`,
                code: 'magic_numbers',
                source: 'PowerScript',
            });
        }

        // Cyclomatic complexity (simplified)
        const branchKwRe = /^\s*(?:if\b|else\b|elseif\b|choose\s+case\b|case\b|for\b|do\s+while\b|do\s+until\b|continue\b|exit\b|return\b|throw\b|goto\b)/i;
        let cc = 1;
        let chooseCount = 0;
        for (const cl of routine.body) {
            const t = cl.text.trim();
            if (branchKwRe.test(t)) {
                if (/^case\s+/i.test(t)) chooseCount++;
                else cc++;
            }
        }
        if (chooseCount > 0) cc = cc - chooseCount + 1;
        if (cc > config.maxComplexity) {
            const rating = cc <= 5 ? 'A' : cc <= 10 ? 'B' : cc <= 20 ? 'C' : cc <= 50 ? 'D' : 'F';
            diagnostics.push({
                severity: vscode.DiagnosticSeverity.Warning,
                range: new vscode.Range(routine.startLine, 0, routine.startLine, 80),
                message: `'${routine.name}' complexity=${cc} (rating=${rating}, recommend <${config.maxComplexity})`,
                code: 'high_complexity',
                source: 'PowerScript',
            });
        }
    }

    // ── File-level checks ──

    // Global variables
    if (config.enableGlobalVariableCheck) {
        const globalVarRe = /^(?:global\s+)?(?:integer|long|decimal|real|double|string|blob|date|time|datetime|boolean|char|nchar|any|window|datawindow|datastore|userobject|nonvisualobject|transaction|powerobject)\s+(g[a-z]_\w+)/im;
        for (let i = 0; i < lines.length; i++) {
            const m = lines[i].match(globalVarRe);
            if (m) {
                diagnostics.push({
                    severity: vscode.DiagnosticSeverity.Information,
                    range: new vscode.Range(i, 0, i, lines[i].length),
                    message: `Global variable '${m[1]}' — potential coupling`,
                    code: 'global_variable',
                    source: 'PowerScript',
                });
            }
        }
    }

    // SELECT * in DataWindow files (.srd)
    if (config.enableSelectStarCheck && document.fileName.toLowerCase().endsWith('.srd')) {
        for (let i = 0; i < lines.length; i++) {
            if (/\bSELECT\s+\*/i.test(lines[i])) {
                diagnostics.push({
                    severity: vscode.DiagnosticSeverity.Warning,
                    range: new vscode.Range(i, 0, i, lines[i].length),
                    message: 'Uses SELECT * — explicitly list columns for better maintainability',
                    code: 'select_star',
                    source: 'PowerScript',
                });
            }
        }
    }

    return diagnostics;
}

// ──────────────────────────────────────────────
// Completion Provider
// ──────────────────────────────────────────────

class PSCompletionProvider {
    provideCompletionItems(document, position, token, context) {
        const items = [];

        for (const kw of PS_KEYWORDS) {
            items.push(new vscode.CompletionItem(kw, vscode.CompletionItemKind.Keyword));
        }
        for (const t of PS_TYPES) {
            const item = new vscode.CompletionItem(t, vscode.CompletionItemKind.Class);
            item.detail = 'PowerScript Type';
            items.push(item);
        }
        for (const a of PS_ACCESS) {
            items.push(new vscode.CompletionItem(a, vscode.CompletionItemKind.Keyword));
        }
        for (const fn of PS_FUNCTIONS) {
            const item = new vscode.CompletionItem(fn, vscode.CompletionItemKind.Function);
            item.detail = 'PowerScript Function';
            item.insertText = fn;
            items.push(item);
        }
        for (const fn of PS_OBJECT_FUNCTIONS) {
            const item = new vscode.CompletionItem(fn, vscode.CompletionItemKind.Method);
            item.detail = 'Object Method';
            items.push(item);
        }

        return items;
    }
}

// ──────────────────────────────────────────────
// Hover Provider
// ──────────────────────────────────────────────

const HOVER_DOCS = {
    // Types
    'integer': 'A 16-bit signed integer (-32768 to 32767).',
    'long': 'A 32-bit signed integer (-2,147,483,648 to 2,147,483,647).',
    'longlong': 'A 64-bit signed integer (PB10+).',
    'string': 'Variable-length character string (up to 2GB in PB10+).',
    'decimal': 'Signed decimal number with up to 18 digits of precision.',
    'real': 'A single-precision floating-point number.',
    'double': 'A double-precision floating-point number.',
    'boolean': 'Boolean value: TRUE or FALSE.',
    'date': 'A date value (year, month, day).',
    'time': 'A time value (hour, minute, second, microsecond).',
    'datetime': 'Combined date and time value.',
    'blob': 'Binary Large Object — unstructured data up to 2GB.',
    'any': 'Can hold any datatype — resolved at runtime.',
    'datawindow': 'PowerBuilder DataWindow control.',
    'datastore': 'Non-visual DataWindow — no UI, for background data access.',
    'userobject': 'Custom visual or non-visual object.',
    'nonvisualobject': 'Base class for non-visual custom objects.',
    'transaction': 'Database transaction object (default: SQLCA).',
    // SQLCA
    'SQLCA': 'Default global Transaction object for database communication.\n\nProperties:\n  SQLCode — 0=success, 100=not found, -1=error\n  SQLDBCode — Database-specific error code\n  SQLErrText — Database error message text\n  SQLNRows — Number of rows affected',
    // Functions
    'Retrieve': 'Retrieves rows from the database into a DataWindow or DataStore.\n\nReturns: long (number of rows retrieved, -1 on error)',
    'Update': 'Sends all insert/delete/modify changes to the database.\n\nReturns: 1=success, -1=error',
    'InsertRow': 'Inserts a new row in the DataWindow.\n\nReturns: 1=success, -1=error',
    'DeleteRow': 'Deletes a row from the DataWindow.\n\nReturns: 1=success, -1=error',
    'SetItem': 'Sets the value of a cell in the DataWindow buffer.\n\nSyntax: dw.SetItem(row, column, value)',
    'GetItemString': 'Gets the string value of a cell.',
    'GetItemNumber': 'Gets the numeric value of a cell.',
    'Describe': 'Reports the value of a DataWindow property.\n\nSyntax: dw.Describe("property")',
    'Modify': 'Modifies a DataWindow property.\n\nSyntax: dw.Modify("property=value")',
    'MessageBox': 'Displays a message box.\n\nReturns: 1=OK, 2=Cancel, 3=Yes, 4=No, etc.',
    'SetPointer': 'Changes the mouse pointer (deprecated — use Pointer property).',
    'SetFilter': 'Sets the filter criteria for a DataWindow.',
    'SetSort': 'Sets the sort criteria for a DataWindow.',
    'ShareData': 'Shares data between two DataWindow controls.',
    'Create': 'Creates an object instance.\n\nSyntax: obj = CREATE classname\nRemember to DESTROY when done.',
    'Destroy': 'Destroys an object instance and frees memory.',
    'TriggerEvent': 'Triggers an event synchronously.',
    'PostEvent': 'Posts an event to the event queue (asynchronous).',
    'Open': 'Opens a window.\n\nSyntax: Open(windowvar {, parent})',
    'Close': 'Closes a window.',
};

class PSHoverProvider {
    provideHover(document, position) {
        const range = document.getWordRangeAtPosition(position, /[a-zA-Z_]\w*/);
        if (!range) return null;

        const word = document.getText(range);
        const key = word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();

        // Try exact match first, then case-insensitive
        let doc = HOVER_DOCS[word] || HOVER_DOCS[key];
        if (!doc) {
            // Case-insensitive lookup
            const lower = word.toLowerCase();
            for (const [k, v] of Object.entries(HOVER_DOCS)) {
                if (k.toLowerCase() === lower) {
                    doc = v;
                    break;
                }
            }
        }

        if (doc) {
            return new vscode.Hover({
                language: 'powerscript',
                value: doc,
            }, range);
        }

        return null;
    }
}

// ──────────────────────────────────────────────
// Activation
// ──────────────────────────────────────────────

let diagnosticCollection;

function getConfig() {
    const cfg = vscode.workspace.getConfiguration('powerscript');
    return {
        enableLinting: cfg.get('enableLinting', true),
        maxRoutineLines: cfg.get('maxRoutineLines', 200),
        maxComplexity: cfg.get('maxComplexity', 20),
        maxNesting: cfg.get('maxNesting', 4),
        enableEmptyCatchCheck: cfg.get('enableEmptyCatchCheck', true),
        enableSelectStarCheck: cfg.get('enableSelectStarCheck', true),
        enableGlobalVariableCheck: cfg.get('enableGlobalVariableCheck', true),
        enableDeprecatedCheck: cfg.get('enableDeprecatedCheck', true),
        enableHardcodedSqlCheck: cfg.get('enableHardcodedSqlCheck', true),
    };
}

function refreshDiagnostics() {
    diagnosticCollection.clear();
    const config = getConfig();

    for (const editor of vscode.window.visibleTextEditors) {
        if (editor.document.languageId === 'powerscript') {
            const diagnostics = lintDocument(editor.document, config);
            diagnosticCollection.set(editor.document.uri, diagnostics);
        }
    }
}

async function lintFile(uri) {
    const doc = await vscode.workspace.openTextDocument(uri);
    const config = getConfig();
    const diagnostics = lintDocument(doc, config);
    diagnosticCollection.set(doc.uri, diagnostics);

    const errors = diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Error).length;
    const warnings = diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Warning).length;
    const infos = diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Information).length;
    vscode.window.showInformationMessage(
        `PowerScript Lint: ${errors} errors, ${warnings} warnings, ${infos} info`
    );
}

async function lintDirectory() {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders) {
        vscode.window.showErrorMessage('No workspace folder open');
        return;
    }
    const config = getConfig();
    let totalErrors = 0, totalWarnings = 0, totalInfos = 0;

    for (const folder of folders) {
        const files = await vscode.workspace.findFiles(
            new vscode.RelativePattern(folder, '**/*.sr*')
        );
        for (const fileUri of files) {
            const doc = await vscode.workspace.openTextDocument(fileUri);
            const diagnostics = lintDocument(doc, config);
            diagnosticCollection.set(doc.uri, diagnostics);
            totalErrors += diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Error).length;
            totalWarnings += diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Warning).length;
            totalInfos += diagnostics.filter(d => d.severity === vscode.DiagnosticSeverity.Information).length;
        }
    }
    vscode.window.showInformationMessage(
        `PowerScript Lint (all files): ${totalErrors} errors, ${totalWarnings} warnings, ${totalInfos} info`
    );
}

function activate(context) {
    console.log('PowerScript extension activated');

    diagnosticCollection = vscode.languages.createDiagnosticCollection('powerscript');
    context.subscriptions.push(diagnosticCollection);

    // Register providers
    const completionProvider = vscode.languages.registerCompletionItemProvider(
        { scheme: 'file', language: 'powerscript' },
        new PSCompletionProvider()
    );
    context.subscriptions.push(completionProvider);

    const hoverProvider = vscode.languages.registerHoverProvider(
        { scheme: 'file', language: 'powerscript' },
        new PSHoverProvider()
    );
    context.subscriptions.push(hoverProvider);

    // Lint on save and on change (debounced)
    let lintTimeout = null;
    const changeListener = vscode.workspace.onDidChangeTextDocument((e) => {
        if (e.document.languageId !== 'powerscript') return;
        clearTimeout(lintTimeout);
        lintTimeout = setTimeout(() => {
            const config = getConfig();
            const diagnostics = lintDocument(e.document, config);
            diagnosticCollection.set(e.document.uri, diagnostics);
        }, 500); // 500ms debounce
    });
    context.subscriptions.push(changeListener);

    const saveListener = vscode.workspace.onDidSaveTextDocument((doc) => {
        if (doc.languageId !== 'powerscript') return;
        const config = getConfig();
        const diagnostics = lintDocument(doc, config);
        diagnosticCollection.set(doc.uri, diagnostics);
    });
    context.subscriptions.push(saveListener);

    // Lint on open
    vscode.workspace.onDidOpenTextDocument((doc) => {
        if (doc.languageId !== 'powerscript') return;
        const config = getConfig();
        const diagnostics = lintDocument(doc, config);
        diagnosticCollection.set(doc.uri, diagnostics);
    });

    // Commands
    const lintFileCmd = vscode.commands.registerCommand('powerscript.runLint', async () => {
        if (vscode.window.activeTextEditor) {
            await lintFile(vscode.window.activeTextEditor.document.uri);
        }
    });
    context.subscriptions.push(lintFileCmd);

    const lintDirCmd = vscode.commands.registerCommand('powerscript.runLintDirectory', lintDirectory);
    context.subscriptions.push(lintDirCmd);

    // Config change listener
    const configListener = vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration('powerscript')) {
            refreshDiagnostics();
        }
    });
    context.subscriptions.push(configListener);
}

function deactivate() {
    console.log('PowerScript extension deactivated');
}

module.exports = { activate, deactivate };
