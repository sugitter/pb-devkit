import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { invoke } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';

interface RefactorIssue {
  file: string;
  line: number;
  kind: string;
  message: string;
  suggestion: string;
}

interface RefactorResult {
  success: boolean;
  files_scanned: number;
  issues: RefactorIssue[];
  applied: number;
  report_path: string;
  message: string;
}

@Component({
  selector: 'app-refactor-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="refactor-panel">
      <div class="rp-header">
        <h2><span class="material-icons" style="vertical-align:middle;margin-right:6px">auto_fix_high</span> 代码重构分析</h2>
      </div>

      <!-- 配置区 -->
      <div class="rp-config">
        <div class="rp-row">
          <span class="rp-label">源码目录</span>
          <input type="text" [(ngModel)]="sourceDir" placeholder="选择源码目录（.sr* 文件）" class="rp-input" readonly />
          <button class="rp-browse" (click)="browseSource()">
            <span class="material-icons" style="font-size:16px">folder_open</span>
          </button>
        </div>
        <div class="rp-row">
          <span class="rp-label">输出目录</span>
          <input type="text" [(ngModel)]="outputDir" placeholder="选择报告输出目录" class="rp-input" readonly />
          <button class="rp-browse" (click)="browseOutput()">
            <span class="material-icons" style="font-size:16px">folder_open</span>
          </button>
        </div>
        <div class="rp-row rp-options">
          <label class="rp-toggle">
            <input type="checkbox" [(ngModel)]="applyFix" />
            <span>应用样式自动修复（safe-only）</span>
          </label>
          <button class="rp-run" (click)="runRefactor()" [disabled]="!sourceDir || !outputDir || loading">
            <span class="material-icons" style="font-size:15px">{{ loading ? 'hourglass_empty' : 'play_arrow' }}</span>
            {{ loading ? '分析中...' : '开始分析' }}
          </button>
        </div>
      </div>

      @if (error) {
        <div class="rp-error">
          <span class="material-icons" style="font-size:15px">error</span> {{ error }}
        </div>
      }

      @if (result) {
        <!-- 统计卡片 -->
        <div class="rp-stats">
          <div class="stat-card">
            <span class="stat-num">{{ result.files_scanned }}</span>
            <span class="stat-label">文件扫描</span>
          </div>
          <div class="stat-card warn">
            <span class="stat-num">{{ result.issues.length }}</span>
            <span class="stat-label">问题发现</span>
          </div>
          <div class="stat-card ok">
            <span class="stat-num">{{ result.applied }}</span>
            <span class="stat-label">已自动修复</span>
          </div>
        </div>

        <!-- 过滤 -->
        <div class="rp-filter-bar">
          <button class="filter-btn" [class.active]="filterKind==='all'" (click)="filterKind='all'">
            全部 ({{ result.issues.length }})
          </button>
          @for (k of kindList(); track k) {
            <button class="filter-btn" [class.active]="filterKind===k" (click)="filterKind=k">
              <span class="dot" [class]="k"></span> {{ kindLabel(k) }} ({{ countByKind(k) }})
            </button>
          }
        </div>

        <!-- 问题列表 -->
        <div class="rp-issue-list">
          @for (issue of filteredIssues(); track issue.file + issue.line) {
            <div class="rp-issue" [class]="'issue-' + issue.kind">
              <div class="issue-header">
                <span class="issue-loc"><span class="material-icons" style="font-size:13px">code</span> {{ issue.file }} :{{ issue.line }}</span>
                <span class="issue-kind-badge" [class]="'badge-' + issue.kind">{{ kindLabel(issue.kind) }}</span>
              </div>
              <div class="issue-msg">{{ issue.message }}</div>
              <div class="issue-sugg"><span class="material-icons" style="font-size:12px;color:#7c3aed">lightbulb</span> {{ issue.suggestion }}</div>
            </div>
          }
          @if (filteredIssues().length === 0 && result.issues.length === 0) {
            <div class="rp-empty">
              <span class="material-icons" style="font-size:32px;color:#059669">check_circle</span>
              <p>未发现问题，代码质量良好！</p>
            </div>
          }
        </div>

        <div class="rp-report-bar">
          <span class="material-icons" style="font-size:14px;color:#6b7280">description</span>
          <span class="rp-report-path">{{ result.report_path }}</span>
        </div>
      }

      @if (!result && !loading) {
        <div class="rp-placeholder">
          <span class="material-icons" style="font-size:48px;color:#d1d5db">auto_fix_high</span>
          <p>选择源码目录，开始代码重构分析</p>
          <p class="rp-hint">扫描代码风格、复杂度、待办注释、废弃 API 等问题</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .refactor-panel { display: flex; flex-direction: column; height: 100%; background: #fff; overflow: hidden; }

    .rp-header { padding: 0.6rem 1rem; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; }
    .rp-header h2 { margin: 0; font-size: 0.9rem; font-weight: 700; color: #111; display: flex; align-items: center; }

    .rp-config { padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; background: #f9fafb; flex-shrink: 0; display: flex; flex-direction: column; gap: 0.4rem; }
    .rp-row { display: flex; align-items: center; gap: 0.5rem; }
    .rp-label { width: 70px; font-size: 0.78rem; font-weight: 600; color: #374151; flex-shrink: 0; }
    .rp-input { flex: 1; padding: 0.35rem 0.6rem; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; color: #374151; background: #fff; }
    .rp-browse { padding: 0.35rem 0.6rem; background: #fff; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; color: #6b7280; display: flex; align-items: center; }
    .rp-browse:hover { background: #f3f4f6; }
    .rp-options { justify-content: space-between; }
    .rp-toggle { display: flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; color: #374151; cursor: pointer; }
    .rp-run { padding: 0.4rem 1.2rem; background: #7c3aed; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.82rem; display: flex; align-items: center; gap: 0.3rem; }
    .rp-run:hover { background: #6d28d9; }
    .rp-run:disabled { background: #d1d5db; cursor: not-allowed; }

    .rp-error { padding: 0.5rem 1rem; margin: 0.5rem 1rem; background: #fee2e2; color: #dc2626; border-radius: 6px; font-size: 0.8rem; display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; }

    .rp-stats { display: flex; gap: 0.75rem; padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; background: #f9fafb; flex-shrink: 0; }
    .stat-card { flex: 1; text-align: center; padding: 0.6rem; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; }
    .stat-card.warn { border-color: #fbbf24; background: #fffbeb; }
    .stat-card.ok { border-color: #6ee7b7; background: #f0fdf4; }
    .stat-num { display: block; font-size: 1.6rem; font-weight: 700; color: #111; }
    .stat-card.warn .stat-num { color: #d97706; }
    .stat-card.ok .stat-num { color: #059669; }
    .stat-label { font-size: 0.72rem; color: #6b7280; }

    .rp-filter-bar { display: flex; flex-wrap: wrap; gap: 4px; padding: 0.5rem 1rem; border-bottom: 1px solid #e5e7eb; background: #fff; flex-shrink: 0; }
    .filter-btn { padding: 0.2rem 0.6rem; border: 1px solid #d1d5db; background: #fff; border-radius: 4px; cursor: pointer; font-size: 0.72rem; color: #6b7280; display: flex; align-items: center; gap: 0.25rem; }
    .filter-btn.active { background: #eff6ff; border-color: #93c5fd; color: #2563eb; font-weight: 600; }
    .dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
    .dot.style { background: #3b82f6; }
    .dot.complexity { background: #f59e0b; }
    .dot.dead_code { background: #6b7280; }
    .dot.naming { background: #ef4444; }

    .rp-issue-list { flex: 1; overflow-y: auto; padding: 0.5rem 1rem; display: flex; flex-direction: column; gap: 0.4rem; }
    .rp-issue { padding: 0.5rem 0.75rem; border-radius: 6px; border: 1px solid #e5e7eb; font-size: 0.8rem; }
    .rp-issue.issue-complexity { border-color: #fde68a; background: #fffbeb; }
    .rp-issue.issue-naming { border-color: #fecaca; background: #fef2f2; }
    .rp-issue.issue-dead_code { border-color: #e5e7eb; background: #f9fafb; }
    .rp-issue.issue-style { border-color: #bfdbfe; background: #eff6ff; }
    .issue-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.2rem; }
    .issue-loc { color: #374151; font-size: 0.75rem; display: flex; align-items: center; gap: 0.2rem; font-family: monospace; }
    .issue-kind-badge { font-size: 0.68rem; padding: 0.1rem 0.4rem; border-radius: 10px; font-weight: 600; }
    .badge-complexity { background: #fef3c7; color: #92400e; }
    .badge-naming { background: #fee2e2; color: #991b1b; }
    .badge-dead_code { background: #f3f4f6; color: #374151; }
    .badge-style { background: #dbeafe; color: #1d4ed8; }
    .issue-msg { color: #374151; margin-bottom: 0.2rem; }
    .issue-sugg { color: #6b7280; font-size: 0.75rem; display: flex; align-items: center; gap: 0.25rem; }

    .rp-empty { display: flex; flex-direction: column; align-items: center; padding: 3rem 1rem; gap: 0.5rem; color: #6b7280; }
    .rp-empty p { margin: 0; font-size: 0.85rem; }

    .rp-report-bar { padding: 0.4rem 1rem; border-top: 1px solid #e5e7eb; background: #f9fafb; display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; }
    .rp-report-path { font-size: 0.72rem; color: #6b7280; font-family: monospace; }

    .rp-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; gap: 0.5rem; color: #9ca3af; text-align: center; padding: 2rem; }
    .rp-placeholder p { margin: 0; font-size: 0.85rem; }
    .rp-hint { font-size: 0.78rem; color: #d1d5db; }
  `]
})
export class RefactorPanelComponent {
  @Input() projectPath = '';

  sourceDir = '';
  outputDir = '';
  applyFix = false;
  result: RefactorResult | null = null;
  error = '';
  loading = false;
  filterKind = 'all';

  ngOnChanges() {
    if (this.projectPath && !this.sourceDir) {
      this.sourceDir = this.projectPath;
    }
  }

  async browseSource() {
    const selected = await open({ directory: true, title: '选择源码目录' });
    if (selected) this.sourceDir = selected as string;
  }

  async browseOutput() {
    const selected = await open({ directory: true, title: '选择报告输出目录' });
    if (selected) this.outputDir = selected as string;
  }

  async runRefactor() {
    if (!this.sourceDir || !this.outputDir) return;
    this.loading = true;
    this.error = '';
    this.result = null;

    try {
      this.result = await invoke<RefactorResult>('run_refactor', {
        sourceDir: this.sourceDir,
        outputDir: this.outputDir,
        apply: this.applyFix,
      });
    } catch (e: any) {
      this.error = e?.message || String(e);
    } finally {
      this.loading = false;
    }
  }

  kindList(): string[] {
    if (!this.result) return [];
    const kinds = new Set(this.result.issues.map(i => i.kind));
    return Array.from(kinds);
  }

  kindLabel(kind: string): string {
    const map: Record<string, string> = {
      style: '代码风格',
      complexity: '复杂度',
      dead_code: '待办/死代码',
      naming: '命名/API',
    };
    return map[kind] ?? kind;
  }

  countByKind(kind: string): number {
    return this.result?.issues.filter(i => i.kind === kind).length ?? 0;
  }

  filteredIssues() {
    if (!this.result) return [];
    if (this.filterKind === 'all') return this.result.issues;
    return this.result.issues.filter(i => i.kind === this.filterKind);
  }
}
