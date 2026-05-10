package com.pbdevkit.powerscript.inspections;

import com.intellij.codeInspection.*;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class DeprecatedFunctionInspection extends LocalInspectionTool {
    private static final ProblemDescriptor[] EMPTY = new ProblemDescriptor[0];

    private static final Pattern[][] DEPRECATED = {
            {Pattern.compile("\\bSetPointer\\s*\\("), "SetPointer is deprecated — use Pointer property"},
            {Pattern.compile("\\bYield\\s*\\(\\s*\\)"), "Yield() is deprecated — use Timer for async"},
            {Pattern.compile("\\bDoEvents\\b"), "DoEvents is deprecated — use Timer for async"},
            {Pattern.compile("\\bRGB\\b(?!\\s*\\()"), "RGB is deprecated — use Long color constants"},
            {Pattern.compile("\\bSetRedraw\\s*\\("), "SetRedraw is deprecated — use SetRedraw property"},
    };

    @Override
    public @Nullable ProblemDescriptor[] checkFile(@NotNull PsiFile file, @NotNull InspectionManager manager, boolean isOnTheFly) {
        String text = file.getText();
        if (text.isEmpty()) return EMPTY;

        List<PSRoutineParser.Routine> routines = PSRoutineParser.parse(text);
        ProblemsHolder holder = new ProblemsHolder(manager, file, isOnTheFly);

        for (PSRoutineParser.Routine r : routines) {
            String body = r.getBodyText();
            for (Pattern[] dep : DEPRECATED) {
                Matcher m = dep[0].matcher(body);
                if (m.find()) {
                    PsiElement elem = file.findElementAt(file.getTextOffset());
                    if (elem != null) {
                        holder.registerProblem(elem, (String) dep[1]);
                    }
                }
            }
        }

        return holder.getResultsArray();
    }
}
