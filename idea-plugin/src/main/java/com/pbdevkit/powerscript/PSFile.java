package com.pbdevkit.powerscript;

import com.intellij.extapi.psi.PsiFileBase;
import com.intellij.openapi.fileTypes.FileType;
import com.intellij.psi.FileViewProvider;
import org.jetbrains.annotations.NotNull;

public class PSFile extends PsiFileBase {
    public PSFile(@NotNull FileViewProvider viewProvider) {
        super(viewProvider, PSLanguage.INSTANCE);
    }

    @Override
    @NotNull
    public FileType getFileType() {
        return PSFileType.INSTANCE;
    }

    @Override
    public String toString() {
        return "PowerScript File";
    }
}
