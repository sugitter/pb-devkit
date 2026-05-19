import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { invoke } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';

interface DiffChange {
  line_number: number;
  line1: string | null;
  line2: string | null;
  change_type: 'modified' | 'added' | 'removed';
}

interface DiffResult {
  file1: string;
  file2: string;
  total_changes: number;
  changes: DiffChange[];
}

@Component({
  selector: 'app-diff-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="diff-panel">
      <div class="dp-header">
        <h2><span class="material-icons" style="vertical-align:middle;margin-right:6px">compare</span> 代码对比</h2>
        <button class="btn-close" (click)="close.emit()">
          <span class="material-icons">close</span>
        </button>
      </div>

      <!-- 文件选择区 -->
      <div class="dp-selector">
        <div class="dp-file-row">
          <span class="dp-label">A (原始)</span>
          <input type="text" [(ngModel)]="path1" readonly placeholder="选择原始文件" class="dp-input" />
          <button class="dp-browse" (click)="browseFile(1)">
            <span class="material-icons" style="font-size:16px">folder_open</span>
          </button>
        </div>
        <div class="dp-file-row">
          <span class="dp-label">B (修改)</span>
          <input type="text" [(ngModel)]="path2" readonly placeholder="选择修改后文件" class="dp-input" />
          <button class="dp-browse" (click)="browseFile(2)">
            <span class="material-icons" style="font-size:16px">folder_open</span>
          </button>
        </div>
        <button class="dp-run" (click)="runDiff()" [disabled]="!path1 || !path2 || loading">
          <span class="material-icons" style="font-size:16px">play_arrow</span>
          {{ loading ? '对比中...' : '执行对比' }}
        </button>
      </div>

      @if (loading) {
        <div class="dp-loading">
          <div class="spinner"></div>
          <span>正在对比...</span>
        </div>
      }

      @if (error) {
        <div class="dp-error">
          <span class="material-icons" style="font-size:16px">error</span> {{ error }}
        </div>
      }

      <!-- 对比结果 -->
      @if (result) {
        <div class="dp-result-header">
          <span class="dp-summary">
            共 <strong>{{ result.total_changes }}</strong> 处差异
          </span>
          <div class="dp-filter">
            <button class="filter-btn" [class.active]="diffFilter==='all'" (click)="diffFilter='all'">全部</button>
            <button class="filter-btn" [class.active]="diffFilter==='modified'" (click)="diffFilter='modified'">
              <span class="dot modified"></span> 修改 {{ countByType('modified') }}
            </button>
            <button class="filter-btn" [class.active]="diffFilter==='added'" (click)="diffFilter='added'">
              <span class="dot added"></span> 新增 {{ countByType('added') }}
            </button>
            <button class="filter-btn" [class.active]="diffFilter==='removed'" (click)="diffFilter='removed'">
              <span class="dot removed"></span> 删除 {{ countByType('removed') }}
            </button>
          </div>
        </div>

        <div class="dp-diff-view">
          @for (change of filteredChanges(); track change.line_number + '_' + change.change_type) {
            <div class="diff-line" [class]="'diff-' + change.change_type">
              <span class="line-num">{{ change.line_number }}</span>
              <span class="diff-marker">{{ change.change_type === 'added' ? '+' : change.change_type === 'removed' ? '-' : '~' }}</span>
              <div class="diff-content">
                @if (change.change_type === 'removed' || change.change_type === 'modified') {
                  <div class="line-old">{{ change.line1 }}</div>
                }
                @if (change.change_type === 'added' || change.change_type === 'modified') {
                  <div class="line-new">{{ change.line2 }}</div>
                }
              </div>
            </div>
          }
          @if (filteredChanges().length === 0) {
            <div class="dp-no-diff">
              <span class="material-icons" style="font-size:24px;color:#059669">check_circle</span>
              <span>无差异</span>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .diff-panel { display: flex; flex-direction: column; height: 100%; background: #fff; }

    .dp-header { display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 1rem; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; }
    .dp-header h2 { margin: 0; font-size: 0.9rem; display: flex; align-items: center; }
    .btn-close { background: none; border: none; cursor: pointer; padding: 4px; color: #6b7280; }
    .btn-close:hover { color: #111; }

    /* 文件选择 */
    .dp-selector { padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; background: #f9fafb; flex-shrink: 0; }
    .dp-file-row { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem; }
    .dp-label { width: 70px; font-size: 0.78rem; font-weight: 600; color: #374151; flex-shrink: 0; }
    .dp-input { flex: 1; padding: 0.4rem 0.6rem; border: 1px solid #d1d5db; border-radius: 4px; background: #fff; font-size: 0.8rem; color: #374151; }
    .dp-browse { padding: 0.4rem 0.6rem; background: #fff; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; color: #6b7280; display: flex; align-items: center; }
    .dp-browse:hover { background: #f3f4f6; }
    .dp-run { width: 100%; margin-top: 0.4rem; padding: 0.5rem 1rem; background: #7c3aed; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.82rem; display: flex; align-items: center; justify-content: center; gap: 0.3rem; }
    .dp-run:hover { background: #6d28d9; }
    .dp-run:disabled { background: #d1d5db; cursor: not-allowed; }

    .dp-loading { display: flex; align-items: center; gap: 0.5rem; padding: 1.5rem; justify-content: center; color: #6b7280; font-size: 0.85rem; }
    .spinner { width: 16px; height: 16px; border: 2px solid #e5e7eb; border-top-color: #7c3aed; border-radius: 50%; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .dp-error { padding: 0.6rem 1rem; margin: 0.5rem; background: #fee2e2; color: #dc2626; border-radius: 6px; font-size: 0.82rem; display: flex; align-items: center; gap: 0.3rem; }

    /* 结果 */
    .dp-result-header { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 1rem; border-bottom: 1px solid #e5e7eb; background: #f9fafb; flex-shrink: 0; }
    .dp-summary { font-size: 0.8rem; color: #374151; }
    .dp-summary strong { color: #7c3aed; }
    .dp-filter { display: flex; gap: 2px; }
    .filter-btn { padding: 0.2rem 0.5rem; border: 1px solid #d1d5db; background: #fff; border-radius: 4px; cursor: pointer; font-size: 0.72rem; color: #6b7280; display: flex; align-items: center; gap: 0.2rem; }
    .filter-btn:hover { background: #f3f4f6; }
    .filter-btn.active { background: #eff6ff; border-color: #93c5fd; color: #2563eb; }
    .dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
    .dot.modified { background: #d97706; }
    .dot.added { background: #059669; }
    .dot.removed { background: #dc2626; }

    /* Diff 视图 */
    .dp-diff-view { flex: 1; overflow-y: auto; font-family: 'Consolas', 'Courier New', monospace; font-size: 0.8rem; }
    .diff-line { display: flex; border-bottom: 1px solid #f3f4f6; }
    .diff-line.diff-removed { background: #fef2f2; }
    .diff-line.diff-added { background: #f0fdf4; }
    .diff-line.diff-modified { background: #fffbeb; }
    .line-num { width: 40px; text-align: right; padding: 0.15rem 0.4rem; color: #9ca3af; flex-shrink: 0; font-size: 0.75rem; user-select: none; }
    .diff-marker { width: 16px; text-align: center; font-weight: 700; flex-shrink: 0; font-size: 0.8rem; }
    .diff-removed .diff-marker { color: #dc2626; }
    .diff-added .diff-marker { color: #059669; }
    .diff-modified .diff-marker { color: #d97706; }
    .diff-content { flex: 1; padding: 0.15rem 0.4rem; min-width: 0; overflow-x: auto; }
    .line-old { color: #991b1b; text-decoration: line-through; white-space: pre; }
    .line-new { color: #166534; white-space: pre; }

    .dp-no-diff { display: flex; align-items: center; gap: 0.5rem; padding: 2rem; justify-content: center; color: #059669; font-size: 0.85rem; }
  `]
})
export class DiffPanelComponent {
  @Output() close = new EventEmitter<void>();

  path1 = '';
  path2 = '';
  result: DiffResult | null = null;
  error = '';
  loading = false;
  diffFilter: 'all' | 'modified' | 'added' | 'removed' = 'all';

  async browseFile(num: 1 | 2) {
    try {
      const selected = await open({
        multiple: false,
        filters: [{ name: 'All Files', extensions: ['*'] }, { name: 'PB Source', extensions: ['srw', 'srd', 'srm', 'srf', 'sru', 'srq', 'srs', 'srj'] }],
        title: num === 1 ? '选择原始文件' : '选择修改后文件'
      });
      if (selected) {
        if (num === 1) this.path1 = selected as string;
        else this.path2 = selected as string;
      }
    } catch (e) {
      this.error = String(e);
    }
  }

  async runDiff() {
    if (!this.path1 || !this.path2) return;

    this.loading = true;
    this.error = '';
    this.result = null;

    try {
      this.result = await invoke<DiffResult>('diff_files', {
        file1: this.path1,
        file2: this.path2,
      });
    } catch (e: any) {
      this.error = e?.message || String(e);
    } finally {
      this.loading = false;
    }
  }

  filteredChanges(): DiffChange[] {
    if (!this.result) return [];
    if (this.diffFilter === 'all') return this.result.changes;
    return this.result.changes.filter(c => c.change_type === this.diffFilter);
  }

  countByType(type: string): number {
    if (!this.result) return 0;
    return this.result.changes.filter(c => c.change_type === type).length;
  }
}
