package com.pbdevkit.powerscript.actions;

import com.intellij.notification.NotificationGroupManager;
import com.intellij.notification.NotificationType;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.fileEditor.FileDocumentManager;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.vfs.VirtualFile;
import com.pbdevkit.powerscript.inspections.PSRoutineParser;
import org.jetbrains.annotations.NotNull;

import java.util.List;

public class RunLintFileAction extends AnAction {

    @Override
    public void actionPerformed(@NotNull AnActionEvent e) {
        VirtualFile file = e.getData(CommonDataKeys.VIRTUAL_FILE);
        Project project = e.getProject();
        if (file == null || project == null) return;

        String ext = file.getExtension();
        if (ext == null || !ext.matches("sr[a-z]")) {
            notify(project, NotificationType.WARNING, "Not a PowerBuilder source file.");
            return;
        }

        Document doc = FileDocumentManager.getInstance().getDocument(file);
        if (doc == null) return;

        String text = doc.getText();
        List<PSRoutineParser.Routine> routines = PSRoutineParser.parse(text);

        StringBuilder report = new StringBuilder();
        report.append("PowerScript Lint: ").append(file.getName()).append("\n");
        report.append("=".repeat(50)).append("\n");
        report.append("Routines: ").append(routines.size()).append("\n\n");

        int issues = 0;
        for (PSRoutineParser.Routine r : routines) {
            StringBuilder rIssues = new StringBuilder();
            if (!r.isEvent && r.lineEnd - r.lineStart > 200)
                rIssues.append("  [W] Too long (").append(r.lineEnd - r.lineStart).append(" lines)\n");
            if (r.maxNesting > 4)
                rIssues.append("  [W] Deep nesting (").append(r.maxNesting).append(")\n");
            if (r.complexity > 20)
                rIssues.append("  [W] High complexity (").append(r.complexity).append(")\n");
            if (!r.isEvent && !r.getBodyText().toLowerCase().contains("try"))
                rIssues.append("  [I] No error handling\n");
            if (rIssues.length() > 0) {
                report.append(r.name).append(":\n").append(rIssues);
                issues++;
            }
        }

        if (issues == 0)
            report.append("No issues found.");
        else
            report.append("\nTotal: ").append(issues).append(" routine(s) with issues.");

        notify(project, NotificationType.INFORMATION, report.toString());
    }

    @Override
    public void update(@NotNull AnActionEvent e) {
        VirtualFile file = e.getData(CommonDataKeys.VIRTUAL_FILE);
        boolean visible = file != null && file.getExtension() != null
                && file.getExtension().matches("sr[a-z]");
        e.getPresentation().setEnabledAndVisible(visible);
    }

    private void notify(Project project, NotificationType type, String message) {
        NotificationGroupManager.getInstance()
                .getNotificationGroup("PowerScript Notifications")
                .createNotification(message, type)
                .notify(project);
    }
}
