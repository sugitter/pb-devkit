package com.pbdevkit.powerscript;

import com.intellij.lang.ASTNode;
import com.intellij.lang.ParserDefinition;
import com.intellij.lang.PsiParser;
import com.intellij.lexer.Lexer;
import com.intellij.openapi.project.Project;
import com.intellij.psi.FileViewProvider;
import com.intellij.psi.PsiElement;
import com.intellij.psi.PsiFile;
import com.intellij.psi.tree.IFileElementType;
import com.intellij.psi.tree.TokenSet;
import org.jetbrains.annotations.NotNull;

public class PSParserDefinition implements ParserDefinition {

    public static final IFileElementType FILE = new IFileElementType(PSLanguage.INSTANCE);

    @Override
    @NotNull
    public Lexer createLexer(Project project) {
        return new PSLexer();
    }

    @Override
    @NotNull
    public PsiParser createParser(Project project) {
        return new PSParser();
    }

    @Override
    @NotNull
    public IFileElementType getFileNodeType() {
        return FILE;
    }

    @Override
    @NotNull
    public TokenSet getCommentTokens() {
        return TokenSet.create(PSTokenTypes.LINE_COMMENT, PSTokenTypes.BLOCK_COMMENT, PSTokenTypes.EXPORT_HEADER);
    }

    @Override
    @NotNull
    public TokenSet getStringLiteralElements() {
        return TokenSet.create(PSTokenTypes.STRING);
    }

    @Override
    @NotNull
    public PsiElement createElement(ASTNode node) {
        return new PSPsiElement(node);
    }

    @Override
    public PsiFile createFile(@NotNull FileViewProvider viewProvider) {
        return new PSFile(viewProvider);
    }

    @Override
    public SpaceRequirements spaceExistenceTypeBetweenTokens(ASTNode left, ASTNode right) {
        return SpaceRequirements.MAY;
    }
}
