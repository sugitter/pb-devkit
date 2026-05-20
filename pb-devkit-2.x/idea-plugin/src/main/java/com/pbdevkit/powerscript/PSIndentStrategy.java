package com.pbdevkit.powerscript;

import com.intellij.openapi.editor.IndentStrategy;
import org.jetbrains.annotations.NotNull;

/**
 * PowerScript auto-indent strategy.
 * Increases indent after if/for/do/try/choose case/else/elseif/catch/finally.
 * Decreases indent before end if/for/do/try/choose/next/loop/catch/finally/else/elseif.
 */
public class PSIndentStrategy implements IndentStrategy {
    @Override
    public int getIndent(@NotNull String text) {
        String trimmed = text.trim().toLowerCase();
        // Lines that decrease indent
        if (trimmed.startsWith("end if") || trimmed.startsWith("end for") ||
            trimmed.startsWith("end do") || trimmed.startsWith("end try") ||
            trimmed.startsWith("end choose") || trimmed.startsWith("next") ||
            trimmed.startsWith("loop") || trimmed.startsWith("catch") ||
            trimmed.startsWith("finally") || trimmed.startsWith("else") ||
            trimmed.startsWith("elseif") || trimmed.startsWith("end subroutine") ||
            trimmed.startsWith("end function") || trimmed.startsWith("end event") ||
            trimmed.startsWith("end on")) {
            return -1;
        }
        return 0;
    }
}
