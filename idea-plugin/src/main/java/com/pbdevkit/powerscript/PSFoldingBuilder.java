package com.pbdevkit.powerscript;

import com.intellij.lang.ASTNode;
import com.intellij.lang.folding.FoldingBuilderEx;
import com.intellij.lang.folding.FoldingDescriptor;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.util.TextRange;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import com.intellij.psi.util.PsiTreeUtil;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class PSFoldingBuilder extends FoldingBuilderEx {

    private static final Pattern ROUTINE_START = Pattern.compile(
            "^\\s*(?:(?:forward\\s+)?(?:public|private|protected|global)\\s+)?(?:subroutine|function)\\b.*$",
            Pattern.CASE_INSENSITIVE
    );
    private static final Pattern ROUTINE_END = Pattern.compile(
            "^\\s*end\\s+(?:subroutine|function)\\b",
            Pattern.CASE_INSENSITIVE
    );
    private static final Pattern EVENT_START = Pattern.compile(
            "^\\s*(?:on\\s+|event\\s+)\\w+",
            Pattern.CASE_INSENSITIVE
    );
    private static final Pattern EVENT_END = Pattern.compile(
            "^\\s*end\\s+(?:on|event)\\b",
            Pattern.CASE_INSENSITIVE
    );

    @Override
    public FoldingDescriptor @NotNull [] buildFoldRegions(@NotNull PsiElement root, @NotNull Document document, boolean quick) {
        List<FoldingDescriptor> descriptors = new ArrayList<>();
        if (!(root instanceof PsiFile)) return descriptors.toArray(new FoldingDescriptor[0]);

        String text = document.getText();
        String[] lines = text.split("\\r?\\n");

        int i = 0;
        while (i < lines.length) {
            String line = lines[i];

            // Function/subroutine folding
            if (ROUTINE_START.matcher(line).find()) {
                int startLine = i;
                int startOffset = document.getLineStartOffset(startLine);
                i++;
                while (i < lines.length && !ROUTINE_END.matcher(lines[i]).find()) i++;
                if (i < lines.length) {
                    int endOffset = document.getLineEndOffset(i) + 1;
                    if (endOffset > startOffset + 1) {
                        String placeholder = extractSignature(line);
                        descriptors.add(new FoldingDescriptor(root.getNode(), new TextRange(startOffset, endOffset), null, placeholder));
                    }
                }
                i++;
                continue;
            }

            // Event folding
            if (EVENT_START.matcher(line).find()) {
                int startLine = i;
                int startOffset = document.getLineStartOffset(startLine);
                i++;
                while (i < lines.length && !EVENT_END.matcher(lines[i]).find()) i++;
                if (i < lines.length) {
                    int endOffset = document.getLineEndOffset(i) + 1;
                    if (endOffset > startOffset + 1) {
                        descriptors.add(new FoldingDescriptor(root.getNode(), new TextRange(startOffset, endOffset), null, line.trim()));
                    }
                }
                i++;
                continue;
            }

            i++;
        }

        return descriptors.toArray(new FoldingDescriptor[0]);
    }

    private String extractSignature(String line) {
        // Extract function/subroutine name from declaration line
        String trimmed = line.trim();
        int funcIdx = trimmed.toLowerCase().lastIndexOf("function");
        int subIdx = trimmed.toLowerCase().lastIndexOf("subroutine");
        int idx = Math.max(funcIdx, subIdx);
        if (idx >= 0) {
            String rest = trimmed.substring(idx).trim();
            // Remove "function"/"subroutine" prefix
            rest = rest.replaceFirst("^(function|subroutine)\\s+", "", Pattern.CASE_INSENSITIVE).trim();
            // Take up to first '('
            int paren = rest.indexOf('(');
            if (paren > 0) {
                rest = rest.substring(0, paren).trim();
            }
            if (rest.length() > 0) return "... " + rest + " ...";
        }
        return "...";
    }

    @Override
    @Nullable
    public String getPlaceholderText(@NotNull ASTNode node) {
        return "...";
    }

    @Override
    public boolean isCollapsedByDefault(@NotNull ASTNode node) {
        return false;
    }
}
