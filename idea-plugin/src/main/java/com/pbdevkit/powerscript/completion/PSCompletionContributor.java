package com.pbdevkit.powerscript.completion;

import com.intellij.codeInsight.completion.*;
import com.intellij.codeInsight.lookup.LookupElementBuilder;
import com.intellij.patterns.PlatformPatterns;
import com.intellij.util.ProcessingContext;
import com.pbdevkit.powerscript.PSLanguage;
import org.jetbrains.annotations.NotNull;

public class PSCompletionContributor extends CompletionContributor {

    private static final String[] KEYWORDS = {
        "if", "then", "else", "elseif", "end if",
        "choose case", "case", "end choose",
        "for", "to", "step", "next",
        "do while", "do until", "loop", "end loop",
        "try", "catch", "finally", "end try", "throw",
        "continue", "exit", "return", "goto",
        "create", "destroy", "call", "super", "parent", "this",
        "post", "dynamic", "not", "and", "or", "is", "null",
        "true", "false", "using", "within", "from",
        "global", "type", "end type", "forward",
        "event", "end event", "on", "end on",
        "prototype", "end prototype", "prototypes",
        "variables", "end variables",
        "subroutine", "end subroutine", "function", "end function",
        "constant", "read-only", "autoinstantiate",
    };

    private static final String[] TYPES = {
        "integer", "int", "long", "longlong", "ulong", "uint",
        "dec", "decimal", "real", "double",
        "string", "blob", "char", "nchar",
        "date", "time", "datetime", "boolean", "any", "unsigned",
        "window", "menu", "datawindow", "datastore",
        "commandbutton", "singlelineedit", "multilineedit",
        "dropdownlistbox", "picture", "picturebutton",
        "graph", "progressbar", "tab",
        "userobject", "nonvisualobject",
        "transaction", "structure", "enumeration",
        "treeview", "listview", "datawindowchild",
        "richtextedit", "statictext", "groupbox",
        "checkbox", "radiobutton", "editmask",
        "PowerObject", "NonVisualObject",
        "oleobject", "olestream",
        "mailsession", "mailmessage",
        "inet", "hyperlink", "pipeline",
        "connection", "internetresult",
    };

    private static final String[] ACCESS = {
        "public", "private", "protected", "shared", "instance", "global",
    };

    private static final String[] FUNCTIONS = {
        // String
        "Len", "Left", "Right", "Mid", "Upper", "Lower", "Trim", "LeftTrim", "RightTrim",
        "Replace", "Pos", "Match", "LastPos", "Reverse", "Space", "Fill", "Asc", "Char",
        "String", "IsNumber", "IsDate", "IsTime", "IsDateTime", "IsNullOrEmpty",
        // Numeric
        "Abs", "Ceiling", "Floor", "Int", "Max", "Min", "Mod", "Rand", "Round", "Sign",
        "Sqrt", "Truncate", "Real", "Double", "Dec", "Integer", "Long",
        // Date/Time
        "Today", "Now", "Year", "Month", "Day", "Hour", "Minute", "Second",
        "RelativeDate", "RelativeTime", "Date", "DateTime", "Time", "DaysAfter",
        "SecondsAfter", "LastDay", "DayNumber", "DayName", "MonthName",
        // DataWindow
        "SetItem", "GetItemString", "GetItemNumber", "GetItemDecimal",
        "GetItemDate", "GetItemDateTime", "GetItemStatus",
        "InsertRow", "DeleteRow", "RowsCopy", "RowsMove", "RowsDiscard",
        "Retrieve", "Update", "Reset", "SetFilter", "SetSort", "Sort",
        "SetTransObject", "SetTrans", "GetSQLSelect", "SetSQLSelect",
        "GetChild", "GetRow", "GetClickedRow", "GetSelectedRow",
        "IsSelected", "SelectRow", "GroupCalc", "ShareData",
        "ImportString", "ImportFile", "ImportClipboard",
        "Describe", "Modify", "SetRedraw", "SetFocus",
        "Object", "Data", "Buffer",
        "Print", "Save", "RowCount", "ModifiedCount", "DeletedCount", "FilteredCount",
        // File
        "FileOpen", "FileRead", "FileWrite", "FileClose", "FileExists", "FileLength",
        "FileDelete", "FileCopy", "FileMove", "FileSeek", "GetFileOpenName", "GetFileSaveName",
        // UI
        "MessageBox", "Open", "Close", "OpenWithParm", "OpenSheet", "OpenSheetWithParm",
        "SetPointer", "Yield", "SetMicroHelp", "SetStatus",
        // Misc
        "ClassName", "TypeOf", "IsValid", "PostEvent", "TriggerEvent",
        "SetNull", "IsNull", "SetProfileString", "GetProfileString",
        "Run", "Handle",
    };

    private static final String[] OBJECT_METHODS = {
        "Hide", "Show", "BringToFront", "SetPosition", "Move", "Resize",
        "Center", "SetTabOrder", "GetActiveSheet", "GetFirstSheet",
        "GetParent", "TriggerEvent", "PostEvent", "SetFocus",
    };

    public PSCompletionContributor() {
        extend(CompletionType.BASIC,
                PlatformPatterns.psiElement().withLanguage(PSLanguage.INSTANCE),
                new CompletionProvider<>() {
                    @Override
                    protected void addCompletions(@NotNull CompletionParameters parameters,
                                                  @NotNull ProcessingContext context,
                                                  @NotNull CompletionResultSet result) {
                        // Keywords
                        for (String kw : KEYWORDS) {
                            result.addElement(LookupElementBuilder.create(kw)
                                    .withBoldness(true)
                                    .withTypeText("keyword"));
                        }
                        // Access modifiers
                        for (String a : ACCESS) {
                            result.addElement(LookupElementBuilder.create(a)
                                    .withTypeText("modifier"));
                        }
                        // Types
                        for (String t : TYPES) {
                            result.addElement(LookupElementBuilder.create(t)
                                    .withTypeText("type"));
                        }
                        // Functions
                        for (String fn : FUNCTIONS) {
                            result.addElement(LookupElementBuilder.create(fn)
                                    .withTypeText("function")
                                    .withIcon(com.intellij.openapi.util.IconLoader.getIcon("/icons/powerscript.svg",
                                            PSCompletionContributor.class)));
                        }
                        // Object methods
                        for (String m : OBJECT_METHODS) {
                            result.addElement(LookupElementBuilder.create(m)
                                    .withTypeText("method"));
                        }
                        result.stopHere();
                    }
                });
    }
}
