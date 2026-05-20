package com.pbdevkit.powerscript.inspections;

import com.intellij.codeInspection.*;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.List;

public class NoErrorHandlingInspection extends LocalInspectionTool {
    private static final ProblemDescriptor[] EMPTY = new ProblemDescriptor[0];

    @Override
    public @Nullable ProblemDescriptor[] checkFile(@NotNull PsiFile file, @NotNull InspectionManager manager, boolean isOnTheFly) {
        String text = file.getText();
        if (text.isEmpty()) return EMPTY;

        List<PSRoutineParser.Routine> routines = PSRoutineParser.parse(text);
        ProblemsHolder holder = new ProblemsHolder(manager, file, isOnTheFly);

        for (PSRoutineParser.Routine r : routines) {
            // Only check functions/subroutines, not events
            if (r.isEvent) continue;

            String body = r.getBodyText();
            if (!body.toLowerCase().contains("try")) {
                PsiElement elem = file.findElementAt(file.getTextOffset());
                if (elem != null) {
                    holder.registerProblem(elem,
                            "'" + r.name + "' lacks try-catch error handling");
                }
            }
        }

        return holder.getResultsArray();
    }
}
