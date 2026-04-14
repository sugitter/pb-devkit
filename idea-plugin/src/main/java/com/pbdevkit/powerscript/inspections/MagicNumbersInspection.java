package com.pbdevkit.powerscript.inspections;

import com.intellij.codeInspection.*;
import com.intellij.psi.PsiFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class MagicNumbersInspection extends LocalInspectionTool {
    private static final ProblemDescriptor[] EMPTY = new ProblemDescriptor[0];
    private static final Pattern MAGIC_NUM_RE = Pattern.compile("(?<![.\\w])(\\d+)(?![.\\w])");

    private static final Set<Integer> SAFE_NUMBERS = new HashSet<>(Arrays.asList(
            0, 1, -1, 2, 4, 8, 10, 16, 32, 64, 100,
            128, 256, 512, 1000, 1024, 2048, 8192, 32767, 65536
    ));

    @Override
    public @Nullable ProblemDescriptor[] checkFile(@NotNull PsiFile file, @NotNull InspectionManager manager, boolean isOnTheFly) {
        String text = file.getText();
        if (text.isEmpty()) return EMPTY;

        List<PSRoutineParser.Routine> routines = PSRoutineParser.parse(text);
        ProblemsHolder holder = new ProblemsHolder(manager, file, isOnTheFly);

        for (PSRoutineParser.Routine r : routines) {
            String body = r.getBodyText();
            Set<Integer> magicNums = new LinkedHashSet<>();
            Matcher m = MAGIC_NUM_RE.matcher(body);

            while (m.find()) {
                try {
                    int num = Integer.parseInt(m.group(1));
                    if (!SAFE_NUMBERS.contains(num) && num > 2 && num < 100000) {
                        // Check not in a comment
                        String prefix = body.substring(Math.max(0, body.lastIndexOf('\n', m.start())), m.start());
                        if (!prefix.contains("//") && !prefix.contains("'")) {
                            magicNums.add(num);
                        }
                    }
                } catch (NumberFormatException ignored) {}
                if (magicNums.size() >= 10) break;
            }

            if (!magicNums.isEmpty()) {
                StringBuilder nums = new StringBuilder();
                int count = 0;
                for (int n : magicNums) {
                    if (count > 0) nums.append(", ");
                    nums.append(n);
                    count++;
                    if (count >= 5) break;
                }

                PsiElement elem = file.findElementAt(file.getTextOffset());
                if (elem != null) {
                    holder.registerProblem(elem,
                            "'" + r.name + "' uses magic numbers: " + nums);
                }
            }
        }

        return holder.getResultsArray();
    }
}
