package com.pbdevkit.powerscript;

import com.intellij.lexer.LexerBase;
import com.intellij.psi.tree.IElementType;
import org.jetbrains.annotations.NotNull;

import java.util.HashSet;
import java.util.Set;

/**
 * PowerScript tokenizer - produces PSTokenTypes for syntax highlighting and parsing.
 */
public class PSLexer extends LexerBase {

    private CharSequence buffer;
    private int bufferEnd;
    private int tokenStart;
    private int tokenEnd;
    private IElementType currentToken;

    private int bufferStartOffset = 0;

    private static final Set<String> CONTROL_KEYWORDS = new HashSet<>();
    private static final Set<String> TYPE_KEYWORDS = new HashSet<>();
    private static final Set<String> ACCESS_MODIFIERS = new HashSet<>();
    private static final Set<String> PB_CONSTANTS = new HashSet<>();
    private static final Set<String> SQL_KEYWORDS = new HashSet<>();
    private static final Set<String> DW_FUNCTIONS = new HashSet<>();

    static {
        String[] controls = {
            "if", "then", "else", "elseif", "choose", "case",
            "for", "to", "step", "next", "do", "while", "until", "loop",
            "continue", "exit", "return", "goto", "try", "catch", "finally",
            "throw", "create", "destroy", "call", "super", "parent", "this", "post",
            "dynamic", "not", "and", "or", "is", "null", "true", "false",
            "using", "within", "from", "global", "type", "forward",
            "event", "on", "prototype", "prototypes", "variables",
            "subroutine", "function", "constant", "autoinstantiate",
        };
        for (String k : controls) CONTROL_KEYWORDS.add(k.toLowerCase());

        String[] types = {
            "integer", "int", "long", "longlong", "ulong", "uint", "dec", "decimal",
            "real", "double", "string", "blob", "char", "nchar", "date", "time",
            "datetime", "boolean", "any", "unsigned", "window", "menu", "datawindow",
            "datastore", "commandbutton", "singlelineedit", "multilineedit",
            "dropdownlistbox", "picture", "picturebutton", "graph", "progressbar",
            "tab", "userobject", "nonvisualobject", "transaction", "structure",
            "enumeration", "treeview", "listview", "datawindowchild", "richtextedit",
            "statictext", "groupbox", "checkbox", "radiobutton", "editmask",
            "powerobject", "oleobject", "olestream", "mailsession", "mailmessage",
            "inet", "hyperlink", "pipeline", "connection", "internetresult",
            "corbaobject", "mdiframe", "errorobject",
        };
        for (String t : types) TYPE_KEYWORDS.add(t.toLowerCase());

        String[] access = {"public", "private", "protected", "shared", "instance", "global", "readonly", "constant"};
        for (String a : access) ACCESS_MODIFIERS.add(a.toLowerCase());

        String[] constants = {
            "hourglass!", "arrow!", "cross!", "beam!", "size!", "sizens!", "sizewe!",
            "sizenwse!", "sizenesw!", "hyperlink!",
            "append!", "choose!", "create!", "delete!", "filter!", "insert!", "modify!",
            "retrieve!", "update!", "cancel!", "close!", "dbcancel!", "dbe!", "eof!",
            "notmodified!", "ok!", "prompt!", "setcode!", "setfocus!", "userdefined!",
            "any!", "char!", "date!", "datetime!", "decimal!", "double!", "integer!",
            "long!", "real!", "string!", "time!", "unsignedinteger!", "unsignedlong!",
            "yes!", "no!",
        };
        for (String c : constants) PB_CONSTANTS.add(c.toLowerCase());

        String[] sql = {
            "select", "from", "where", "into", "values", "set", "insert", "update",
            "delete", "join", "left", "right", "inner", "outer", "full", "cross",
            "and", "or", "not", "in", "exists", "between", "like", "order", "by",
            "group", "having", "union", "all", "distinct", "as", "asc", "desc",
            "null", "is", "count", "sum", "avg", "min", "max", "create", "drop",
            "alter", "table", "index", "view", "procedure", "trigger", "execute",
            "immediate", "using", "dynamic", "cursor", "for", "read", "only",
            "fetch", "next", "prior", "first", "last", "close", "open", "declare",
            "section", "connect", "disconnect", "commit", "rollback", "transaction",
            "database", "powerbuilder",
        };
        for (String s : sql) SQL_KEYWORDS.add(s.toLowerCase());

        String[] dwFuncs = {
            "Object", "Data", "Buffer", "Modify", "Describe", "InsertRow", "DeleteRow",
            "SetFilter", "SetSort", "Retrieve", "Update", "Reset", "RowsMove", "RowsCopy",
            "RowsDiscard", "GetItemString", "GetItemNumber", "GetItemDate", "GetItemDateTime",
            "SetItem", "SetColumn", "SetText", "GetText", "IsSelected", "SelectRow",
            "GroupCalc", "ShareData", "GetChild", "GetSQLSelect", "SetSQLSelect",
            "ImportString", "ImportFile", "Export", "Save", "Print", "SetTransObject",
            "SetTrans", "GetRow", "GetClickedRow", "GetSelectedRow", "RowCount",
            "ModifiedCount", "DeletedCount", "FilteredCount",
        };
        for (String d : dwFuncs) DW_FUNCTIONS.add(d.toLowerCase());
    }

    @Override
    public void start(@NotNull CharSequence buffer, int startOffset, int endOffset, int initialState) {
        this.buffer = buffer;
        this.bufferStartOffset = startOffset;
        this.bufferEnd = endOffset;
        this.tokenStart = startOffset;
        this.tokenEnd = startOffset;
        this.currentToken = null;
        advance();
    }

    @Override
    public int getState() { return 0; }

    @Override
    @NotNull
    public IElementType getTokenType() {
        return currentToken != null ? currentToken : PSTokenTypes.BAD_CHARACTER;
    }

    @Override
    public int getTokenStart() { return tokenStart; }

    @Override
    public int getTokenEnd() { return tokenEnd; }

    @Override
    public void advance() {
        tokenStart = tokenEnd;
        if (tokenStart >= bufferEnd) {
            currentToken = null;
            return;
        }

        char c = buffer.charAt(tokenStart);

        // PB Export Header line
        if (tokenStart == bufferStartOffset && bufferStartOffset < bufferEnd - 16) {
            String prefix = "$PBExportHeader$";
            int end = bufferStartOffset + prefix.length();
            if (end <= bufferEnd && buffer.subSequence(bufferStartOffset, end).toString().equals(prefix)) {
                int lineEnd = tokenStart + 1;
                while (lineEnd < bufferEnd && buffer.charAt(lineEnd) != '\n') lineEnd++;
                if (lineEnd < bufferEnd) lineEnd++;
                tokenEnd = lineEnd;
                currentToken = PSTokenTypes.EXPORT_HEADER;
                return;
            }
        }

        // Whitespace
        if (Character.isWhitespace(c)) {
            tokenEnd = tokenStart + 1;
            while (tokenEnd < bufferEnd && Character.isWhitespace(buffer.charAt(tokenEnd))) tokenEnd++;
            currentToken = PSTokenTypes.WHITE_SPACE;
            return;
        }

        // Line comment //
        if (c == '/' && tokenStart + 1 < bufferEnd && buffer.charAt(tokenStart + 1) == '/') {
            tokenEnd = tokenStart + 2;
            while (tokenEnd < bufferEnd && buffer.charAt(tokenEnd) != '\n') tokenEnd++;
            currentToken = PSTokenTypes.LINE_COMMENT;
            return;
        }

        // Block comment /* */
        if (c == '/' && tokenStart + 1 < bufferEnd && buffer.charAt(tokenStart + 1) == '*') {
            tokenEnd = tokenStart + 2;
            while (tokenEnd < bufferEnd - 1) {
                if (buffer.charAt(tokenEnd) == '*' && buffer.charAt(tokenEnd + 1) == '/') {
                    tokenEnd += 2;
                    break;
                }
                tokenEnd++;
            }
            if (tokenEnd >= bufferEnd - 1) tokenEnd = bufferEnd;
            currentToken = PSTokenTypes.BLOCK_COMMENT;
            return;
        }

        // String literal " with ~ escape
        if (c == '"') {
            tokenEnd = tokenStart + 1;
            while (tokenEnd < bufferEnd) {
                char ch = buffer.charAt(tokenEnd);
                if (ch == '~' && tokenEnd + 1 < bufferEnd) { tokenEnd += 2; continue; }
                if (ch == '"') { tokenEnd++; break; }
                tokenEnd++;
            }
            currentToken = PSTokenTypes.STRING;
            return;
        }

        // String literal ' with ~ escape
        if (c == '\'') {
            tokenEnd = tokenStart + 1;
            while (tokenEnd < bufferEnd) {
                char ch = buffer.charAt(tokenEnd);
                if (ch == '~' && tokenEnd + 1 < bufferEnd) { tokenEnd += 2; continue; }
                if (ch == '\'') { tokenEnd++; break; }
                tokenEnd++;
            }
            currentToken = PSTokenTypes.STRING;
            return;
        }

        // Number (including hex, negative)
        if (Character.isDigit(c) || (c == '-' && tokenStart + 1 < bufferEnd && Character.isDigit(buffer.charAt(tokenStart + 1)))) {
            tokenEnd = tokenStart;
            if (c == '-') tokenEnd++;
            while (tokenEnd < bufferEnd && Character.isDigit(buffer.charAt(tokenEnd))) tokenEnd++;
            if (tokenEnd < bufferEnd && buffer.charAt(tokenEnd) == '.') {
                tokenEnd++;
                while (tokenEnd < bufferEnd && Character.isDigit(buffer.charAt(tokenEnd))) tokenEnd++;
            }
            if (tokenEnd < bufferEnd && (buffer.charAt(tokenEnd) == 'e' || buffer.charAt(tokenEnd) == 'E')) {
                tokenEnd++;
                if (tokenEnd < bufferEnd && (buffer.charAt(tokenEnd) == '+' || buffer.charAt(tokenEnd) == '-')) tokenEnd++;
                while (tokenEnd < bufferEnd && Character.isDigit(buffer.charAt(tokenEnd))) tokenEnd++;
            }
            currentToken = PSTokenTypes.NUMBER;
            return;
        }

        // Identifier or keyword
        if (Character.isLetter(c) || c == '_') {
            tokenEnd = tokenStart;
            while (tokenEnd < bufferEnd) {
                char ch = buffer.charAt(tokenEnd);
                if (Character.isLetterOrDigit(ch) || ch == '_' || ch == '!' || ch == '#') {
                    tokenEnd++;
                } else if (ch == ' ' || ch == '\t') {
                    // Check for multi-word keywords
                    int spaceEnd = tokenEnd;
                    while (spaceEnd < bufferEnd && (buffer.charAt(spaceEnd) == ' ' || buffer.charAt(spaceEnd) == '\t')) spaceEnd++;
                    if (spaceEnd < bufferEnd && Character.isLetter(buffer.charAt(spaceEnd))) {
                        String twoWord = buffer.subSequence(tokenStart, spaceEnd + 1).toString().toLowerCase();
                        String[] multiWord = {
                            "end if", "end choose", "end try", "end type", "end event", "end on",
                            "end prototype", "end variables", "end loop", "end subroutine",
                            "end function", "end forward", "choose case", "do while", "do until",
                            "read-only",
                        };
                        for (String mw : multiWord) {
                            if (mw.equals(twoWord)) {
                                tokenEnd = spaceEnd + 1;
                                if (CONTROL_KEYWORDS.contains(mw)) currentToken = PSTokenTypes.KEYWORD;
                                else if (ACCESS_MODIFIERS.contains(mw)) currentToken = PSTokenTypes.MODIFIER;
                                return;
                            }
                        }
                    }
                    break;
                } else {
                    break;
                }
            }

            String word = buffer.subSequence(tokenStart, tokenEnd).toString();
            String lower = word.toLowerCase();

            if (CONTROL_KEYWORDS.contains(lower)) {
                currentToken = PSTokenTypes.KEYWORD;
            } else if (TYPE_KEYWORDS.contains(lower)) {
                currentToken = PSTokenTypes.TYPE;
            } else if (ACCESS_MODIFIERS.contains(lower)) {
                currentToken = PSTokenTypes.MODIFIER;
            } else if (PB_CONSTANTS.contains(lower)) {
                currentToken = PSTokenTypes.CONSTANT;
            } else if (SQL_KEYWORDS.contains(lower)) {
                currentToken = PSTokenTypes.SQL_KEYWORD;
            } else if (DW_FUNCTIONS.contains(lower)) {
                currentToken = PSTokenTypes.DW_FUNCTION;
            } else {
                currentToken = PSTokenTypes.IDENTIFIER;
            }
            return;
        }

        // Brackets
        if (c == '(') { tokenEnd = tokenStart + 1; currentToken = PSTokenTypes.LPAREN; return; }
        if (c == ')') { tokenEnd = tokenStart + 1; currentToken = PSTokenTypes.RPAREN; return; }
        if (c == '[') { tokenEnd = tokenStart + 1; currentToken = PSTokenTypes.LBRACKET; return; }
        if (c == ']') { tokenEnd = tokenStart + 1; currentToken = PSTokenTypes.RBRACKET; return; }

        // Dot / semicolon / colon / escape
        if (c == '.') { tokenEnd = tokenStart + 1; currentToken = PSTokenTypes.DOT; return; }
        if (c == ';') { tokenEnd = tokenStart + 1; currentToken = PSTokenTypes.SEMICOLON; return; }
        if (c == ':') { tokenEnd = tokenStart + 1; currentToken = PSTokenTypes.COLON; return; }
        if (c == '~' && tokenEnd + 1 < bufferEnd) { tokenEnd = tokenStart + 2; currentToken = PSTokenTypes.ESCAPE; return; }

        // Operators
        if (c == '=' || c == '+' || c == '-' || c == '*' || c == '/' || c == '^' || c == '&' ||
                c == '<' || c == '>') {
            tokenEnd = tokenStart + 1;
            if (tokenEnd < bufferEnd) {
                char next = buffer.charAt(tokenEnd);
                if ((c == '<' && (next == '>' || next == '=')) || (c == '>' && next == '=') ||
                        (next == '=' && "+-*/^".indexOf(c) >= 0)) {
                    tokenEnd++;
                }
            }
            currentToken = PSTokenTypes.OPERATOR;
            return;
        }

        tokenEnd = tokenStart + 1;
        currentToken = PSTokenTypes.BAD_CHARACTER;
    }

    @Override
    @NotNull
    public CharSequence getBufferSequence() { return buffer; }

    @Override
    public int getBufferEnd() { return bufferEnd; }
}
