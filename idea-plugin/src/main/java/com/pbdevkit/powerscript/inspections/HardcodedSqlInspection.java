package com.pbdevkit.powerscript.inspections;

import com.intellij.codeInspection.*;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.List;
import java.util.regex.Pattern;

public class HardcodedSqlInspection extends LocalInspectionTool {
    private static final ProblemDescriptor[] EMPTY = new ProblemDescriptor[0];
    private static final Pattern[] SQL_PATTERNS = {
            Pattern.compile("\\bSELECT\\s+\\*", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\bEXEC(?:UTE)?\\s+IMMEDIATE\\s+['\"]", Pattern.CASE_INSENSITIVE),
            Pattern.compile("\\bSQLCA\\.(?:SQLCode|DBCode)", Pattern.CASE_INSENSITIVE),
    };

    @Override
    public @Nullable ProblemDescriptor[] checkFile(@NotNull PsiFile file, @NotNull InspectionManager manager, boolean isOnTheFly) {
        String text = file.getText();
        if (text.isEmpty()) return EMPTY;

        List<PSRoutineParser.Routine> routines = PSRoutineParser.parse(text);
        ProblemsHolder holder = new ProblemsHolder(manager, file, isOnTheFly);

        for (PSRoutineParser.Routine r : routines) {
            String body = r.getBodyText();
            for (Pattern p : SQL_PATTERNS) {
                if (p.matcher(body).find()) {
                    PsiElement elem = file.findElementAt(file.getTextOffset());
                    if (elem != null) {
                        holder.registerProblem(elem,
                                "'" + r.name + "' uses hardcoded SQL — consider using DataWindow");
                    }
                    break;
                }
            }
        }

        return holder.getResultsArray();
    }
}
