package com.pbdevkit.powerscript;

import com.intellij.psi.tree.IElementType;
import com.intellij.psi.impl.source.tree.LeafPsiElement;
import org.jetbrains.annotations.NotNull;

public class PSPsiElement extends LeafPsiElement {
    public PSPsiElement(@NotNull IElementType type, CharSequence text) {
        super(type, text);
    }
}
