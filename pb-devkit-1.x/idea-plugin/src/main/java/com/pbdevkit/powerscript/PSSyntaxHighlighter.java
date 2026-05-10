package com.pbdevkit.powerscript;

import com.intellij.lexer.Lexer;
import com.intellij.openapi.editor.DefaultLanguageHighlighterColors;
import com.intellij.openapi.editor.HighlighterColors;
import com.intellij.openapi.editor.colors.TextAttributesKey;
import com.intellij.openapi.fileTypes.SyntaxHighlighterBase;
import com.intellij.psi.tree.IElementType;
import org.jetbrains.annotations.NotNull;

import java.util.HashMap;
import java.util.Map;

/**
 * PowerScript syntax highlighter - maps token types to IDE color attributes.
 */
public class PSSyntaxHighlighter extends SyntaxHighlighterBase {

    public static final TextAttributesKey KEYWORD =
            createKey("PS_KEYWORD", DefaultLanguageHighlighterColors.KEYWORD);
    public static final TextAttributesKey TYPE =
            createKey("PS_TYPE", DefaultLanguageHighlighterColors.CLASS_NAME);
    public static final TextAttributesKey MODIFIER =
            createKey("PS_MODIFIER", DefaultLanguageHighlighterColors.METADATA);
    public static final TextAttributesKey CONSTANT =
            createKey("PS_CONSTANT", DefaultLanguageHighlighterColors.CONSTANT);
    public static final TextAttributesKey SQL_KEYWORD =
            createKey("PS_SQL_KEYWORD", DefaultLanguageHighlighterColors.METADATA);
    public static final TextAttributesKey DW_FUNCTION =
            createKey("PS_DW_FUNCTION", DefaultLanguageHighlighterColors.FUNCTION_DECLARATION);
    public static final TextAttributesKey IDENTIFIER =
            createKey("PS_IDENTIFIER", DefaultLanguageHighlighterColors.IDENTIFIER);
    public static final TextAttributesKey STRING =
            createKey("PS_STRING", DefaultLanguageHighlighterColors.STRING);
    public static final TextAttributesKey NUMBER =
            createKey("PS_NUMBER", DefaultLanguageHighlighterColors.NUMBER);
    public static final TextAttributesKey LINE_COMMENT =
            createKey("PS_LINE_COMMENT", DefaultLanguageHighlighterColors.LINE_COMMENT);
    public static final TextAttributesKey BLOCK_COMMENT =
            createKey("PS_BLOCK_COMMENT", DefaultLanguageHighlighterColors.BLOCK_COMMENT);
    public static final TextAttributesKey EXPORT_HEADER =
            createKey("PS_EXPORT_HEADER", DefaultLanguageHighlighterColors.BLOCK_COMMENT);
    public static final TextAttributesKey BAD_CHAR =
            createKey("PS_BAD_CHAR", HighlighterColors.BAD_CHARACTER);

    private static TextAttributesKey createKey(String externalName, TextAttributesKey fallback) {
        return TextAttributesKey.createTextAttributesKey(externalName, fallback);
    }

    private static final Map<IElementType, TextAttributesKey[]> ATTRIBUTES = new HashMap<>();

    static {
        ATTRIBUTES.put(PSTokenTypes.KEYWORD, new TextAttributesKey[]{KEYWORD});
        ATTRIBUTES.put(PSTokenTypes.TYPE, new TextAttributesKey[]{TYPE});
        ATTRIBUTES.put(PSTokenTypes.MODIFIER, new TextAttributesKey[]{MODIFIER});
        ATTRIBUTES.put(PSTokenTypes.CONSTANT, new TextAttributesKey[]{CONSTANT});
        ATTRIBUTES.put(PSTokenTypes.SQL_KEYWORD, new TextAttributesKey[]{SQL_KEYWORD});
        ATTRIBUTES.put(PSTokenTypes.DW_FUNCTION, new TextAttributesKey[]{DW_FUNCTION});
        ATTRIBUTES.put(PSTokenTypes.IDENTIFIER, new TextAttributesKey[]{IDENTIFIER});
        ATTRIBUTES.put(PSTokenTypes.STRING, new TextAttributesKey[]{STRING});
        ATTRIBUTES.put(PSTokenTypes.NUMBER, new TextAttributesKey[]{NUMBER});
        ATTRIBUTES.put(PSTokenTypes.LINE_COMMENT, new TextAttributesKey[]{LINE_COMMENT});
        ATTRIBUTES.put(PSTokenTypes.BLOCK_COMMENT, new TextAttributesKey[]{BLOCK_COMMENT});
        ATTRIBUTES.put(PSTokenTypes.EXPORT_HEADER, new TextAttributesKey[]{EXPORT_HEADER});
        ATTRIBUTES.put(PSTokenTypes.BAD_CHARACTER, new TextAttributesKey[]{BAD_CHAR});
        ATTRIBUTES.put(PSTokenTypes.LPAREN, new TextAttributesKey[]{DefaultLanguageHighlighterColors.PARENTHESES});
        ATTRIBUTES.put(PSTokenTypes.RPAREN, new TextAttributesKey[]{DefaultLanguageHighlighterColors.PARENTHESES});
        ATTRIBUTES.put(PSTokenTypes.LBRACKET, new TextAttributesKey[]{DefaultLanguageHighlighterColors.BRACKETS});
        ATTRIBUTES.put(PSTokenTypes.RBRACKET, new TextAttributesKey[]{DefaultLanguageHighlighterColors.BRACKETS});
        ATTRIBUTES.put(PSTokenTypes.DOT, new TextAttributesKey[]{DefaultLanguageHighlighterColors.DOT});
        ATTRIBUTES.put(PSTokenTypes.OPERATOR, new TextAttributesKey[]{DefaultLanguageHighlighterColors.OPERATION_SIGN});
        ATTRIBUTES.put(PSTokenTypes.SEMICOLON, new TextAttributesKey[]{DefaultLanguageHighlighterColors.SEMICOLON});
    }

    @NotNull
    @Override
    public Lexer getHighlightingLexer() {
        return new PSLexer();
    }

    @Override
    public TextAttributesKey @NotNull [] getTokenHighlights(IElementType tokenType) {
        TextAttributesKey[] attrs = ATTRIBUTES.get(tokenType);
        return attrs != null ? attrs : new TextAttributesKey[0];
    }
}
