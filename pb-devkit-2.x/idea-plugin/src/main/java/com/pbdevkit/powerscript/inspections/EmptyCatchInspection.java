package com.pbdevkit.powerscript.inspections;

import com.intellij.codeInspection.*;
import com.intellij.openapi.project.Project;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.List;
import java.util.regex.Pattern;

public class EmptyCatchInspection extends LocalInspectionTool {
    private static final Pattern EMPTY_CATCH_RE = Pattern.compile(
            "catch\\s*\\([^)]*\\)\\s*\\n(\\s*(?:(?://|').*)?\\s*\\n)*\\s*end\\s+try",
            Pattern.CASE_INSENSITIVE
    );
    private static final ProblemDescriptor[] EMPTY = new ProblemDescriptor[0];

    @Override
    public @Nullable ProblemDescriptor[] checkFile(@NotNull PsiFile file, @NotNull InspectionManager manager, boolean isOnTheFly) {
        String text = file.getText();
        if (text.isEmpty()) return EMPTY;

        List<PSRoutineParser.Routine> routines = PSRoutineParser.parse(text);
        ProblemsHolder holder = new ProblemsHolder(manager, file, isOnTheFly);

        for (PSRoutineParser.Routine r : routines) {
            String body = r.getBodyText();
            if (EMPTY_CATCH_RE.matcher(body).find()) {
                PsiElement startElement = file.findElementAt(file.getTextOffset());
                if (startElement != null) {
                    holder.registerProblem(startElement,
                            "'" + r.name + "' has empty CATCH block — error silently swallowed");
                }
            }
        }

        return holder.getResultsArray();
    }
}
