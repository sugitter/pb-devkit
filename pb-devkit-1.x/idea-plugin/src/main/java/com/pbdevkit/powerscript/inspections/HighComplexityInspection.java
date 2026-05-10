package com.pbdevkit.powerscript.inspections;

import com.intellij.codeInspection.*;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.List;

public class HighComplexityInspection extends LocalInspectionTool {
    private static final int DEFAULT_THRESHOLD = 20;
    private static final ProblemDescriptor[] EMPTY = new ProblemDescriptor[0];

    private static String getRating(int cc) {
        if (cc <= 5) return "A";
        if (cc <= 10) return "B";
        if (cc <= 20) return "C";
        if (cc <= 50) return "D";
        return "F";
    }

    @Override
    public @Nullable ProblemDescriptor[] checkFile(@NotNull PsiFile file, @NotNull InspectionManager manager, boolean isOnTheFly) {
        String text = file.getText();
        if (text.isEmpty()) return EMPTY;

        List<PSRoutineParser.Routine> routines = PSRoutineParser.parse(text);
        ProblemsHolder holder = new ProblemsHolder(manager, file, isOnTheFly);

        for (PSRoutineParser.Routine r : routines) {
            if (r.complexity > DEFAULT_THRESHOLD) {
                PsiElement elem = file.findElementAt(file.getTextOffset());
                if (elem != null) {
                    holder.registerProblem(elem,
                            "'" + r.name + "' complexity=" + r.complexity +
                            " (rating=" + getRating(r.complexity) + ", recommend <" + DEFAULT_THRESHOLD + ")");
                }
            }
        }

        return holder.getResultsArray();
    }
}
