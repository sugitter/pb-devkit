package com.pbdevkit.powerscript.inspections;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Shared routine parser for PowerScript inspections.
 * Extracts routine boundaries, body, nesting depth, and complexity.
 */
public class PSRoutineParser {

    public static class Routine {
        public final String name;
        public final int startLine; // 0-based
        public final int endLine;   // 0-based
        public final boolean isEvent;
        public final int depth;     // max nesting depth
        public final int complexity; // cyclomatic complexity
        public final List<String> bodyLines;

        public Routine(String name, int startLine, int endLine, boolean isEvent,
                       int depth, int complexity, List<String> bodyLines) {
            this.name = name;
            this.startLine = startLine;
            this.endLine = endLine;
            this.isEvent = isEvent;
            this.depth = depth;
            this.complexity = complexity;
            this.bodyLines = bodyLines;
        }

        public int getCodeLineCount() {
            int count = 0;
            for (String line : bodyLines) {
                String t = line.trim();
                if (!t.isEmpty() && !t.startsWith("//") && !t.startsWith("'")) count++;
            }
            return count;
        }

        public String getBodyText() {
            return String.join("\n", bodyLines);
        }
    }

    private static final Pattern ROUTINE_START_RE = Pattern.compile(
            "^(?:forward\\s+)?(?:(?:public|private|protected|global)\\s+)?(?:subroutine|function)\\s+(?:\\w+\\s+)?(\\w+)",
            Pattern.CASE_INSENSITIVE
    );
    private static final Pattern EVENT_START_RE = Pattern.compile(
            "^(?:on\\s+)(\\w+)\\.(\\w+)",
            Pattern.CASE_INSENSITIVE
    );
    private static final Pattern ROUTINE_END_RE = Pattern.compile(
            "^\\s*end\\s+(?:subroutine|function|on)\\b",
            Pattern.CASE_INSENSITIVE
    );
    private static final Pattern BRANCH_RE = Pattern.compile(
            "^\\s*(?:if\\b|else\\b|elseif\\b|choose\\s+case\\b|case\\b|for\\b|do\\s+while\\b|do\\s+until\\b|continue\\b|exit\\b|return\\b|throw\\b|goto\\b)",
            Pattern.CASE_INSENSITIVE
    );
    private static final Pattern OPEN_BLOCK_RE = Pattern.compile(
            "^\\s*(?:if|for|do|try|choose\\s+case)\\b",
            Pattern.CASE_INSENSITIVE
    );
    private static final Pattern CLOSE_BLOCK_RE = Pattern.compile(
            "^\\s*end\\s+(?:if|for|do|try|choose)\\b",
            Pattern.CASE_INSENSITIVE
    );

    public static List<Routine> parse(String text) {
        List<Routine> routines = new ArrayList<>();
        String[] lines = text.split("\\r?\\n");

        int i = 0;
        while (i < lines.length) {
            String line = lines[i];
            Matcher routineMatch = ROUTINE_START_RE.matcher(line);
            Matcher eventMatch = EVENT_START_RE.matcher(line);

            if (routineMatch.find() || eventMatch.find()) {
                String name;
                boolean isEvent;
                if (routineMatch.find()) {
                    // Re-match since find() advances
                }
                routineMatch.reset(line);
                eventMatch.reset(line);

                if (routineMatch.find()) {
                    name = routineMatch.group(1);
                    isEvent = false;
                } else if (eventMatch.find()) {
                    name = eventMatch.group(1) + "." + eventMatch.group(2);
                    isEvent = true;
                } else {
                    i++;
                    continue;
                }

                int startLine = i;
                List<String> bodyLines = new ArrayList<>();
                int maxDepth = 0;
                int curDepth = 0;
                int cc = 1;
                int chooseCount = 0;
                i++;

                while (i < lines.length && !ROUTINE_END_RE.matcher(lines[i]).find()) {
                    String bodyLine = lines[i];
                    bodyLines.add(bodyLine);

                    String trimmed = bodyLine.trim();
                    if (OPEN_BLOCK_RE.matcher(trimmed).find()) {
                        curDepth++;
                        maxDepth = Math.max(maxDepth, curDepth);
                    }
                    if (CLOSE_BLOCK_RE.matcher(trimmed).find()) {
                        curDepth = Math.max(0, curDepth - 1);
                    }

                    if (BRANCH_RE.matcher(trimmed).find()) {
                        if (trimmed.toLowerCase().startsWith("case ")) chooseCount++;
                        else cc++;
                    }

                    i++;
                }
                if (chooseCount > 0) cc = cc - chooseCount + 1;

                int endLine = i < lines.length ? i : startLine;
                routines.add(new Routine(name, startLine, endLine, isEvent, maxDepth, cc, bodyLines));
            }
            i++;
        }

        return routines;
    }
}
