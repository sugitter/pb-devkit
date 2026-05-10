package com.pbdevkit.powerscript.inspections;

import com.intellij.codeInspection.*;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class GlobalVariableInspection extends LocalInspectionTool {
    private static final ProblemDescriptor[] EMPTY = new ProblemDescriptor[0];
    private static final Pattern GLOBAL_VAR_RE = Pattern.compile(
            "(?:global\\s+)?(?:integer|long|decimal|real|double|string|blob|date|time|datetime|boolean|char|nchar|any|window|datawindow|datastore|userobject|nonvisualobject|transaction|powerobject)\\s+(g[a-zA-Z_]\\w+)",
            Pattern.CASE_INSENSITIVE
    );

    @Override
    public @Nullable ProblemDescriptor[] checkFile(@NotNull PsiFile file, @NotNull InspectionManager manager, boolean isOnTheFly) {
        String text = file.getText();
        if (text.isEmpty()) return EMPTY;

        ProblemsHolder holder = new ProblemsHolder(manager, file, isOnTheFly);
        String[] lines = text.split("\\r?\\n");

        for (int i = 0; i < lines.length; i++) {
            Matcher m = GLOBAL_VAR_RE.matcher(lines[i]);
            if (m.find()) {
                PsiElement elem = file.findElementAt(file.getTextOffset());
                if (elem != null) {
                    holder.registerProblem(elem,
                            "Global variable '" + m.group(1) + "' — potential coupling");
                }
            }
        }

        return holder.getResultsArray();
    }
}
