package com.pbdevkit.powerscript;

import com.intellij.lang.ASTNode;
import com.intellij.lang.PsiBuilder;
import com.intellij.lang.PsiParser;
import com.intellij.psi.tree.IElementType;
import org.jetbrains.annotations.NotNull;

/**
 * Simple flat parser for PowerScript. Creates a parse tree for IDE navigation
 * (code folding, structure view) but the primary purpose is token-level support
 * for syntax highlighting, completion, and inspections.
 */
public class PSParser implements PsiParser {

    @Override
    @NotNull
    public ASTNode parse(IElementType root, PsiBuilder builder) {
        PsiBuilder.Marker rootMarker = builder.mark();
        while (!builder.eof()) {
            builder.advanceLexer();
        }
        rootMarker.done(root);
        return builder.getTreeBuilt();
    }
}
