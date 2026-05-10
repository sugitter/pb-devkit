package com.pbdevkit.powerscript;

import com.intellij.openapi.fileTypes.SyntaxHighlighter;
import com.intellij.openapi.fileTypes.SyntaxHighlighterFactory;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.vfs.VirtualFile;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

public class PSSyntaxHighlighterFactory extends SyntaxHighlighterFactory {
    @Override
    @NotNull
    public SyntaxHighlighter getSyntaxHighlighter(@Nullable Project project, @NotNull VirtualFile virtualFile) {
        return new PSSyntaxHighlighter();
    }
}
