package com.pbdevkit.powerscript.inspections;

import com.intellij.codeInspection.*;
import com.intellij.psi.PsiFile;
import com.intellij.psi.PsiElement;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.regex.Pattern;

public class SelectStarInspection extends LocalInspectionTool {
    private static final ProblemDescriptor[] EMPTY = new ProblemDescriptor[0];
    private static final Pattern SELECT_STAR_RE = Pattern.compile("\\bSELECT\\s+\\*", Pattern.CASE_INSENSITIVE);

    @Override
    public @Nullable ProblemDescriptor[] checkFile(@NotNull PsiFile file, @NotNull InspectionManager manager, boolean isOnTheFly) {
        // Only check .srd DataWindow files
        String name = file.getName().toLowerCase();
        if (!name.endsWith(".srd")) return EMPTY;

        String text = file.getText();
        if (text.isEmpty()) return EMPTY;

        ProblemsHolder holder = new ProblemsHolder(manager, file, isOnTheFly);
        String[] lines = text.split("\\r?\\n");

        for (int i = 0; i < lines.length; i++) {
            if (SELECT_STAR_RE.matcher(lines[i]).find()) {
                PsiElement elem = file.findElementAt(file.getTextOffset());
                if (elem != null) {
                    holder.registerProblem(elem,
                            "Uses SELECT * — explicitly list columns for better maintainability");
                }
            }
        }

        return holder.getResultsArray();
    }
}
