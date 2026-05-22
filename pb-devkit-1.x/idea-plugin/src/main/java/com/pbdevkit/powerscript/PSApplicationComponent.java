package com.pbdevkit.powerscript;

import com.intellij.openapi.components.ApplicationComponent;
import org.jetbrains.annotations.NotNull;

public class PSApplicationComponent implements ApplicationComponent {
    @Override
    public void initComponent() {
        // Plugin initialized
    }

    @Override
    public void disposeComponent() {
    }

    @Override
    @NotNull
    public String getComponentName() {
        return "PowerScript";
    }
}
