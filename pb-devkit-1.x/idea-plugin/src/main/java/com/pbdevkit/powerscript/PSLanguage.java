package com.pbdevkit.powerscript;

import com.intellij.lang.Language;

public class PSLanguage extends Language {
    public static final PSLanguage INSTANCE = new PSLanguage();

    private PSLanguage() {
        super("PowerScript");
    }
}
