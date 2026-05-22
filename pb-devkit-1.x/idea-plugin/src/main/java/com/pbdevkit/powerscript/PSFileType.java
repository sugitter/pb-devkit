package com.pbdevkit.powerscript;

import com.intellij.openapi.fileTypes.FileType;
import com.intellij.openapi.fileTypes.LanguageFileType;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;

public class PSFileType extends LanguageFileType {
    public static final PSFileType INSTANCE = new PSFileType();

    private PSFileType() {
        super(PSLanguage.INSTANCE);
    }

    @Override
    @NotNull
    public String getName() {
        return "PowerScript";
    }

    @Override
    @NotNull
    public String getDescription() {
        return "PowerBuilder PowerScript source file";
    }

    @Override
    @NotNull
    public String getDefaultExtension() {
        return "srw";
    }

    @Override
    @Nullable
    public Icon getIcon() {
        return PBIcons.FILE;
    }
}
