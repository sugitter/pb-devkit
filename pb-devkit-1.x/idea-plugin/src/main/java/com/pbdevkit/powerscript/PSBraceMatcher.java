package com.pbdevkit.powerscript;

import com.intellij.lang.BracePair;
import com.intellij.lang.PairedBraceMatcher;
import com.intellij.psi.PsiFile;
import com.intellij.psi.tree.IElementType;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

public class PSBraceMatcher implements PairedBraceMatcher {
    private static final BracePair[] PAIRS = {
            new BracePair(PSTokenTypes.LPAREN, PSTokenTypes.RPAREN, false),
            new BracePair(PSTokenTypes.LBRACKET, PSTokenTypes.RBRACKET, false),
    };

    @Override
    public BracePair @NotNull [] getPairs() {
        return PAIRS;
    }

    @Override
    public boolean isLBraceToken(@NotNull IElementType tokenType, @Nullable PsiFile file) {
        return tokenType == PSTokenTypes.LPAREN || tokenType == PSTokenTypes.LBRACKET;
    }

    @Override
    public boolean isRBraceToken(@NotNull IElementType tokenType, @Nullable PsiFile file) {
        return tokenType == PSTokenTypes.RPAREN || tokenType == PSTokenTypes.RBRACKET;
    }
}
