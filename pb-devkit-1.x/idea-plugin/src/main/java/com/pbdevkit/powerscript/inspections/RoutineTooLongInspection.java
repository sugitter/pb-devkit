package com.pbdevkit.powerscript.inspections;

import com.intellij.codeInspection.*;
import com.intellij.openapi.project.Project;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.List;

public class RoutineTooLongInspection extends LocalInspectionTool {
    private static final int DEFAULT_THRESHOLD = 200;
    private static final ProblemDescriptor[] EMPTY = new ProblemDescriptor[0];

    @Override
    public @Nullable ProblemDescriptor[] checkFile(@NotNull PsiFile file, @NotNull InspectionManager manager, boolean isOnTheFly) {
        String text = file.getText();
        if (text.isEmpty()) return EMPTY;

        List<PSRoutineParser.Routine> routines = PSRoutineParser.parse(text);
        ProblemsHolder holder = new ProblemsHolder(manager, file, isOnTheFly);

        for (PSRoutineParser.Routine r : routines) {
            int lines = r.getCodeLineCount();
            if (lines > DEFAULT_THRESHOLD) {
                PsiElement elem = file.findElementAt(file.getTextOffset());
                if (elem != null) {
                    holder.registerProblem(elem,
                            "'" + r.name + "' has " + lines + " lines (recommend <" + DEFAULT_THRESHOLD + ")");
                }
            }
        }

        return holder.getResultsArray();
    }
}
