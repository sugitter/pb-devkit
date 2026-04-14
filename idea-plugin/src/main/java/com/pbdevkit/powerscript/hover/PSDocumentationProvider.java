package com.pbdevkit.powerscript.hover;

import com.intellij.lang.documentation.DocumentationProviderEx;
import com.intellij.openapi.editor.Editor;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.LinkedHashMap;
import java.util.Map;

public class PSDocumentationProvider extends DocumentationProviderEx {

    private static final Map<String, String> DOCS = new LinkedHashMap<>();

    static {
        // Types
        DOCS.put("integer", "<b>integer</b> — A 16-bit signed integer (-32768 to 32767).");
        DOCS.put("long", "<b>long</b> — A 32-bit signed integer (-2,147,483,648 to 2,147,483,647).");
        DOCS.put("longlong", "<b>longlong</b> — A 64-bit signed integer (PB10+).");
        DOCS.put("string", "<b>string</b> — Variable-length character string (up to 2GB in PB10+).");
        DOCS.put("decimal", "<b>decimal</b> — Signed decimal number with up to 18 digits of precision.");
        DOCS.put("real", "<b>real</b> — A single-precision floating-point number.");
        DOCS.put("double", "<b>double</b> — A double-precision floating-point number.");
        DOCS.put("boolean", "<b>boolean</b> — Boolean value: TRUE or FALSE.");
        DOCS.put("date", "<b>date</b> — A date value (year, month, day).");
        DOCS.put("time", "<b>time</b> — A time value (hour, minute, second, microsecond).");
        DOCS.put("datetime", "<b>datetime</b> — Combined date and time value.");
        DOCS.put("blob", "<b>blob</b> — Binary Large Object — unstructured data up to 2GB.");
        DOCS.put("any", "<b>any</b> — Can hold any datatype — resolved at runtime.");
        DOCS.put("datawindow", "<b>datawindow</b> — PowerBuilder DataWindow control.");
        DOCS.put("datastore", "<b>datastore</b> — Non-visual DataWindow — no UI, for background data access.");
        DOCS.put("userobject", "<b>userobject</b> — Custom visual or non-visual object.");
        DOCS.put("nonvisualobject", "<b>nonvisualobject</b> — Base class for non-visual custom objects.");
        DOCS.put("transaction", "<b>transaction</b> — Database transaction object (default: SQLCA).");

        // SQLCA
        DOCS.put("SQLCA", "<b>SQLCA</b> — Default global Transaction object for database communication.<br/>" +
                "Properties:<br/>" +
                "&nbsp;&nbsp;<code>SQLCode</code> — 0=success, 100=not found, -1=error<br/>" +
                "&nbsp;&nbsp;<code>SQLDBCode</code> — Database-specific error code<br/>" +
                "&nbsp;&nbsp;<code>SQLErrText</code> — Database error message text<br/>" +
                "&nbsp;&nbsp;<code>SQLNRows</code> — Number of rows affected");

        // Functions
        DOCS.put("Retrieve", "<b>Retrieve</b> — Retrieves rows from the database into a DataWindow or DataStore.<br/>Returns: long (number of rows retrieved, -1 on error)");
        DOCS.put("Update", "<b>Update</b> — Sends all insert/delete/modify changes to the database.<br/>Returns: 1=success, -1=error");
        DOCS.put("InsertRow", "<b>InsertRow</b> — Inserts a new row in the DataWindow.<br/>Returns: 1=success, -1=error");
        DOCS.put("DeleteRow", "<b>DeleteRow</b> — Deletes a row from the DataWindow.<br/>Returns: 1=success, -1=error");
        DOCS.put("SetItem", "<b>SetItem</b> — Sets the value of a cell in the DataWindow buffer.<br/>Syntax: <code>dw.SetItem(row, column, value)</code>");
        DOCS.put("GetItemString", "<b>GetItemString</b> — Gets the string value of a cell.");
        DOCS.put("GetItemNumber", "<b>GetItemNumber</b> — Gets the numeric value of a cell.");
        DOCS.put("Describe", "<b>Describe</b> — Reports the value of a DataWindow property.<br/>Syntax: <code>dw.Describe(\"property\")</code>");
        DOCS.put("Modify", "<b>Modify</b> — Modifies a DataWindow property.<br/>Syntax: <code>dw.Modify(\"property=value\")</code>");
        DOCS.put("MessageBox", "<b>MessageBox</b> — Displays a message box.<br/>Returns: 1=OK, 2=Cancel, 3=Yes, 4=No, etc.");
        DOCS.put("SetPointer", "<b>SetPointer</b> — Changes the mouse pointer (deprecated — use Pointer property).");
        DOCS.put("SetFilter", "<b>SetFilter</b> — Sets the filter criteria for a DataWindow.");
        DOCS.put("SetSort", "<b>SetSort</b> — Sets the sort criteria for a DataWindow.");
        DOCS.put("ShareData", "<b>ShareData</b> — Shares data between two DataWindow controls.");
        DOCS.put("Create", "<b>Create</b> — Creates an object instance.<br/>Syntax: <code>obj = CREATE classname</code><br/>Remember to DESTROY when done.");
        DOCS.put("Destroy", "<b>Destroy</b> — Destroys an object instance and frees memory.");
        DOCS.put("TriggerEvent", "<b>TriggerEvent</b> — Triggers an event synchronously.");
        DOCS.put("PostEvent", "<b>PostEvent</b> — Posts an event to the event queue (asynchronous).");
        DOCS.put("Open", "<b>Open</b> — Opens a window.<br/>Syntax: <code>Open(windowvar {, parent})</code>");
        DOCS.put("Close", "<b>Close</b> — Closes a window.");
    }

    @Override
    @Nullable
    public String generateDoc(PsiElement element, @Nullable PsiElement originalElement) {
        if (element == null) return null;
        String text = element.getText();
        if (text == null || text.isEmpty()) return null;

        // Case-insensitive lookup
        String key = null;
        for (Map.Entry<String, String> entry : DOCS.entrySet()) {
            if (entry.getKey().equalsIgnoreCase(text)) {
                key = entry.getKey();
                break;
            }
        }
        if (key == null) return null;

        return DOCS.get(key);
    }

    @Override
    @Nullable
    public PsiElement getDocumentationElementForLookupItem(PsiElement psiElement, Object lookupElement, PsiElement contextElement) {
        return contextElement;
    }

    @Override
    @Nullable
    public PsiElement getDocumentationElementForLink(PsiElement psiElement, String link, PsiElement contextElement) {
        return contextElement;
    }
}
