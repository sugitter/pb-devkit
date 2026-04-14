package com.pbdevkit.powerscript;

import com.intellij.psi.tree.IElementType;
import com.intellij.psi.PsiElement;
import com.intellij.lang.ASTNode;

/**
 * Token types for the PowerScript lexer.
 */
public class PSTokenTypes {
    public static final IElementType KEYWORD = new IElementType("PS_KEYWORD", PSLanguage.INSTANCE);
    public static final IElementType TYPE = new IElementType("PS_TYPE", PSLanguage.INSTANCE);
    public static final IElementType MODIFIER = new IElementType("PS_MODIFIER", PSLanguage.INSTANCE);
    public static final IElementType CONSTANT = new IElementType("PS_CONSTANT", PSLanguage.INSTANCE);
    public static final IElementType SQL_KEYWORD = new IElementType("PS_SQL_KEYWORD", PSLanguage.INSTANCE);
    public static final IElementType DW_FUNCTION = new IElementType("PS_DW_FUNCTION", PSLanguage.INSTANCE);
    public static final IElementType IDENTIFIER = new IElementType("PS_IDENTIFIER", PSLanguage.INSTANCE);
    public static final IElementType STRING = new IElementType("PS_STRING", PSLanguage.INSTANCE);
    public static final IElementType NUMBER = new IElementType("PS_NUMBER", PSLanguage.INSTANCE);
    public static final IElementType LINE_COMMENT = new IElementType("PS_LINE_COMMENT", PSLanguage.INSTANCE);
    public static final IElementType BLOCK_COMMENT = new IElementType("PS_BLOCK_COMMENT", PSLanguage.INSTANCE);
    public static final IElementType EXPORT_HEADER = new IElementType("PS_EXPORT_HEADER", PSLanguage.INSTANCE);
    public static final IElementType WHITE_SPACE = new IElementType("PS_WHITE_SPACE", PSLanguage.INSTANCE);
    public static final IElementType BAD_CHARACTER = new IElementType("PS_BAD_CHARACTER", PSLanguage.INSTANCE);
    public static final IElementType LPAREN = new IElementType("PS_LPAREN", PSLanguage.INSTANCE);
    public static final IElementType RPAREN = new IElementType("PS_RPAREN", PSLanguage.INSTANCE);
    public static final IElementType LBRACKET = new IElementType("PS_LBRACKET", PSLanguage.INSTANCE);
    public static final IElementType RBRACKET = new IElementType("PS_RBRACKET", PSLanguage.INSTANCE);
    public static final IElementType DOT = new IElementType("PS_DOT", PSLanguage.INSTANCE);
    public static final IElementType SEMICOLON = new IElementType("PS_SEMICOLON", PSLanguage.INSTANCE);
    public static final IElementType COLON = new IElementType("PS_COLON", PSLanguage.INSTANCE);
    public static final IElementType OPERATOR = new IElementType("PS_OPERATOR", PSLanguage.INSTANCE);
    public static final IElementType ESCAPE = new IElementType("PS_ESCAPE", PSLanguage.INSTANCE);

    private PSTokenTypes() {}
}
