import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { invoke } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';

interface SnapshotDiffEntry {
  file: string;
  status: string;
  lines_added: number;
  lines_removed: number;
}

interface SnapshotResult {
  success: boolean;
  snapshot_id: string;
  snapshot_dir: string;
  exported_files: number;
  diff: SnapshotDiffEntry[];
  total_added: number;
  total_modified: number;
  total_removed: number;
  manifest_path: string;
  message: string;
}

@Component({
  selector: 'app-snapshot-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="snapshot-panel">
      <div class="sp-header">
        <h2><span class="material-icons" style="vertical-align:middle;margin-right:6px">camera_alt</span> 版本快照</h2>
      </div>

      <!-- 配置 -->
      <div class="sp-config">
        <div class="sp-row">
          <span class="sp-label">源码目录</span>
          <input type="text" [(ngModel)]="sourceDir" readonly placeholder="选择源码目录" class="sp-input" />
          <button class="sp-browse" (click)="browseSource()"><span class="material-icons" style="font-size:15px">folder_open</span></button>
        </div>
        <div class="sp-row">
          <span class="sp-label">快照仓库</span>
          <input type="text" [(ngModel)]="snapshotBase" readonly placeholder="选择快照存储目录" class="sp-input" />
          <button class="sp-browse" (click)="browseBase()"><span class="material-icons" style="font-size:15px">folder_open</span></button>
        </div>
        <div class="sp-row">
          <span class="sp-label">标签</span>
          <input type="text" [(ngModel)]="label" placeholder="快照说明（可选）" class="sp-input" />
          <button class="sp-run" (click)="takeSnapshot()" [disabled]="!sourceDir || !snapshotBase || loading">
            <span class="material-icons" style="font-size:15px">add_a_photo</span>
            {{ loading ? '创建中...' : '创建快照' }}
          </button>
        </div>
      </div>

      @if (error) {
        <div class="sp-error"><span class="material-icons" style="font-size:14px">error</span> {{ error }}</div>
      }

      @if (result) {
        <!-- 快照信息 -->
        <div class="sp-info-bar">
          <div class="sp-info-item">
            <span class="sp-info-label">快照 ID</span>
            <span class="sp-info-val">{{ result.snapshot_id }}</span>
          </div>
          <div class="sp-info-item">
            <span class="sp-info-label">文件数</span>
            <span class="sp-info-val">{{ result.exported_files }}</span>
          </div>
          <div class="sp-badge added">+{{ result.total_added }} 新增</div>
          <div class="sp-badge modified">~{{ result.total_modified }} 修改</div>
          <div class="sp-badge removed">-{{ result.total_removed }} 删除</div>
        </div>

        <!-- 过滤 -->
        <div class="sp-filter-bar">
          <button class="f-btn" [class.active]="diffFilter==='all'" (click)="diffFilter='all'">全部 ({{ result.diff.length }})</button>
          <button class="f-btn" [class.active]="diffFilter==='added'" (click)="diffFilter='added'">新增</button>
          <button class="f-btn" [class.active]="diffFilter==='modified'" (click)="diffFilter='modified'">修改</button>
          <button class="f-btn" [class.active]="diffFilter==='removed'" (click)="diffFilter='removed'">删除</button>
        </div>

        <!-- 变更列表 -->
        <div class="sp-diff-list">
          @for (e of filteredDiff(); track e.file) {
            <div class="sp-diff-row" [class]="'status-' + e.status">
              <span class="sp-diff-icon">{{ statusIcon(e.status) }}</span>
              <span class="sp-diff-file">{{ e.file }}</span>
              <span class="sp-diff-lines">
                @if (e.lines_added > 0) { <span class="la">+{{ e.lines_added }}</span> }
                @if (e.lines_removed > 0) { <span class="lr">-{{ e.lines_removed }}</span> }
              </span>
            </div>
          }
          @if (result.diff.length === 0) {
            <div class="sp-no-change">
              <span class="material-icons" style="color:#059669;font-size:20px">check_circle</span>
              <span>与上一快照无差异</span>
            </div>
          }
        </div>

        <div class="sp-manifest-bar">
          <span class="material-icons" style="font-size:13px;color:#6b7280">article</span>
          <span class="sp-manifest-path">{{ result.manifest_path }}</span>
        </div>
      }

      @if (!result && !loading) {
        <div class="sp-placeholder">
          <span class="material-icons" style="font-size:48px;color:#d1d5db">camera_alt</span>
          <p>对源码目录创建版本快照</p>
          <p class="sp-hint">快照会与上一次快照对比，生成变更清单</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .snapshot-panel { display: flex; flex-direction: column; height: 100%; background: #fff; overflow: hidden; }

    .sp-header { padding: 0.6rem 1rem; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; }
    .sp-header h2 { margin: 0; font-size: 0.9rem; font-weight: 700; color: #111; display: flex; align-items: center; }

    .sp-config { padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; background: #f9fafb; flex-shrink: 0; display: flex; flex-direction: column; gap: 0.4rem; }
    .sp-row { display: flex; align-items: center; gap: 0.5rem; }
    .sp-label { width: 70px; font-size: 0.78rem; font-weight: 600; color: #374151; flex-shrink: 0; }
    .sp-input { flex: 1; padding: 0.35rem 0.6rem; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; color: #374151; background: #fff; }
    .sp-browse { padding: 0.35rem 0.6rem; background: #fff; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; color: #6b7280; display: flex; align-items: center; }
    .sp-browse:hover { background: #f3f4f6; }
    .sp-run { padding: 0.4rem 1rem; background: #2563eb; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8rem; display: flex; align-items: center; gap: 0.3rem; flex-shrink: 0; }
    .sp-run:hover { background: #1d4ed8; }
    .sp-run:disabled { background: #d1d5db; cursor: not-allowed; }

    .sp-error { padding: 0.5rem 1rem; margin: 0.5rem 1rem; background: #fee2e2; color: #dc2626; border-radius: 6px; font-size: 0.8rem; display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; }

    .sp-info-bar { display: flex; align-items: center; gap: 0.75rem; padding: 0.6rem 1rem; border-bottom: 1px solid #e5e7eb; background: #f9fafb; flex-shrink: 0; flex-wrap: wrap; }
    .sp-info-item { display: flex; align-items: center; gap: 0.3rem; }
    .sp-info-label { font-size: 0.72rem; color: #9ca3af; }
    .sp-info-val { font-size: 0.78rem; font-weight: 600; color: #374151; font-family: monospace; }
    .sp-badge { padding: 0.15rem 0.55rem; border-radius: 12px; font-size: 0.72rem; font-weight: 600; }
    .sp-badge.added { background: #dcfce7; color: #166534; }
    .sp-badge.modified { background: #fef3c7; color: #92400e; }
    .sp-badge.removed { background: #fee2e2; color: #991b1b; }

    .sp-filter-bar { display: flex; gap: 4px; padding: 0.45rem 1rem; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; }
    .f-btn { padding: 0.2rem 0.6rem; border: 1px solid #d1d5db; background: #fff; border-radius: 4px; cursor: pointer; font-size: 0.72rem; color: #6b7280; }
    .f-btn.active { background: #eff6ff; border-color: #93c5fd; color: #2563eb; font-weight: 600; }

    .sp-diff-list { flex: 1; overflow-y: auto; padding: 0.25rem 0; }
    .sp-diff-row { display: flex; align-items: center; gap: 0.5rem; padding: 0.3rem 1rem; font-size: 0.8rem; }
    .sp-diff-row:hover { background: #f9fafb; }
    .sp-diff-row.status-added { background: #f0fdf4; }
    .sp-diff-row.status-removed { background: #fef2f2; }
    .sp-diff-row.status-modified { background: #fffbeb; }
    .sp-diff-icon { width: 20px; text-align: center; font-size: 0.8rem; }
    .status-added .sp-diff-icon { color: #059669; }
    .status-modified .sp-diff-icon { color: #d97706; }
    .status-removed .sp-diff-icon { color: #dc2626; }
    .sp-diff-file { flex: 1; font-family: monospace; color: #374151; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .sp-diff-lines { display: flex; gap: 0.4rem; flex-shrink: 0; font-size: 0.72rem; font-family: monospace; }
    .la { color: #059669; }
    .lr { color: #dc2626; }
    .sp-no-change { display: flex; align-items: center; gap: 0.5rem; padding: 2rem; justify-content: center; color: #6b7280; font-size: 0.85rem; }

    .sp-manifest-bar { padding: 0.35rem 1rem; border-top: 1px solid #e5e7eb; background: #f9fafb; display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; }
    .sp-manifest-path { font-size: 0.7rem; color: #6b7280; font-family: monospace; }

    .sp-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; gap: 0.5rem; color: #9ca3af; text-align: center; padding: 2rem; }
    .sp-placeholder p { margin: 0; font-size: 0.85rem; }
    .sp-hint { font-size: 0.78rem; color: #d1d5db; }
  `]
})
export class SnapshotPanelComponent {
  @Input() projectPath = '';

  sourceDir = '';
  snapshotBase = '';
  label = '';
  result: SnapshotResult | null = null;
  error = '';
  loading = false;
  diffFilter = 'all';

  ngOnChanges() {
    if (this.projectPath && !this.sourceDir) {
      this.sourceDir = this.projectPath;
    }
  }

  async browseSource() {
    const s = await open({ directory: true, title: '选择源码目录' });
    if (s) this.sourceDir = s as string;
  }

  async browseBase() {
    const s = await open({ directory: true, title: '选择快照存储目录' });
    if (s) this.snapshotBase = s as string;
  }

  async takeSnapshot() {
    if (!this.sourceDir || !this.snapshotBase) return;
    this.loading = true;
    this.error = '';
    this.result = null;

    try {
      this.result = await invoke<SnapshotResult>('take_snapshot', {
        sourceDir: this.sourceDir,
        snapshotBase: this.snapshotBase,
        label: this.label || '快照',
      });
    } catch (e: any) {
      this.error = e?.message || String(e);
    } finally {
      this.loading = false;
    }
  }

  statusIcon(status: string): string {
    return { added: '+', modified: '~', removed: '-' }[status] ?? '?';
  }

  filteredDiff() {
    if (!this.result) return [];
    if (this.diffFilter === 'all') return this.result.diff;
    return this.result.diff.filter(e => e.status === this.diffFilter);
  }
}
