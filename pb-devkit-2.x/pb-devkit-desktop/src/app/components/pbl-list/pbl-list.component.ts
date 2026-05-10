import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { open } from '@tauri-apps/plugin-dialog';
import { PblService, PblEntry, ParseResult } from '../../services/pbl.service';

type FilterType = 'all' | 'source' | 'compiled';

@Component({
  selector: 'app-pbl-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="pbl-list">
      <div class="pbl-header">
        <div class="pbl-title">
          <span class="pbl-icon">📦</span>
          <div>
            <h3>{{ fileName }}</h3>
            @if (parseResult) {
              <span class="meta">{{ parseResult.pb_version }} · {{ parseResult.total_count }} 个对象</span>
            }
          </div>
        </div>
        <div class="pbl-actions">
          <button class="btn-icon" (click)="exportAll()" title="导出全部" [disabled]="loading">
            ⬇ 导出
          </button>
          <button class="btn-icon" (click)="reload()" title="刷新" [disabled]="loading">
            🔄
          </button>
        </div>
      </div>

      @if (parseResult) {
        <div class="stats-bar">
          <span class="stat source" (click)="filter='source'" [class.active]="filter==='source'">
            📝 源码 {{ parseResult.source_count }}
          </span>
          <span class="stat compiled" (click)="filter='compiled'" [class.active]="filter==='compiled'">
            🔧 编译 {{ parseResult.compiled_count }}
          </span>
          <span class="stat all" (click)="filter='all'" [class.active]="filter==='all'">
            全部 {{ parseResult.total_count }}
          </span>
        </div>
      }

      <div class="search-box">
        <input [(ngModel)]="searchQuery" placeholder="过滤对象名..." class="filter-input" />
      </div>

      @if (loading) {
        <div class="loading-spinner">
          <div class="spinner"></div>
          <span>解析中...</span>
        </div>
      }

      @if (error) {
        <div class="error-msg">{{ error }}</div>
      }

      <div class="entries-list">
        @for (entry of filteredEntries; track entry.name) {
          <div class="entry-item" [class.selected]="selectedEntry?.name === entry.name"
               (click)="selectEntry(entry)">
            <span class="type-badge" [class]="'type-' + entry.entry_type_name">
              {{ typeIcon(entry.entry_type_name) }}
            </span>
            <div class="entry-info">
              <span class="entry-name">{{ entry.name }}</span>
              <span class="entry-meta">{{ entry.entry_type_name }} · {{ formatSize(entry.size) }}</span>
            </div>
            @if (entry.is_source) {
              <button class="btn-view" (click)="viewSource(entry, $event)">查看</button>
            }
          </div>
        }

        @if (filteredEntries.length === 0 && !loading) {
          <div class="empty">暂无对象</div>
        }
      </div>
    </div>
  `,
  styles: [`
    .pbl-list { display: flex; flex-direction: column; height: 100%; background: #fff; }
    .pbl-header { display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; }
    .pbl-title { display: flex; align-items: center; gap: 0.75rem; }
    .pbl-icon { font-size: 1.5rem; }
    .pbl-title h3 { margin: 0; font-size: 0.9rem; color: #111; }
    .meta { font-size: 0.75rem; color: #6b7280; }
    .pbl-actions { display: flex; gap: 0.5rem; }
    .btn-icon { padding: 0.3rem 0.75rem; border: 1px solid #d1d5db; background: #f9fafb; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
    .btn-icon:hover { background: #f3f4f6; }
    .btn-icon:disabled { opacity: 0.5; cursor: not-allowed; }
    .stats-bar { display: flex; gap: 0.5rem; padding: 0.5rem 1rem; background: #f9fafb; border-bottom: 1px solid #e5e7eb; }
    .stat { padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.8rem; cursor: pointer; color: #374151; }
    .stat:hover, .stat.active { background: #dbeafe; color: #1d4ed8; }
    .search-box { padding: 0.5rem 1rem; border-bottom: 1px solid #e5e7eb; }
    .filter-input { width: 100%; padding: 0.4rem 0.75rem; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.875rem; box-sizing: border-box; }
    .loading-spinner { display: flex; align-items: center; gap: 0.75rem; padding: 2rem; justify-content: center; color: #6b7280; }
    .spinner { width: 20px; height: 20px; border: 2px solid #e5e7eb; border-top-color: #3b82f6; border-radius: 50%; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .error-msg { padding: 1rem; margin: 0.5rem 1rem; background: #fee2e2; color: #dc2626; border-radius: 6px; font-size: 0.875rem; }
    .entries-list { flex: 1; overflow-y: auto; }
    .entry-item { display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem 1rem; cursor: pointer; border-bottom: 1px solid #f3f4f6; }
    .entry-item:hover { background: #f9fafb; }
    .entry-item.selected { background: #eff6ff; }
    .type-badge { width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; border-radius: 4px; font-size: 0.9rem; }
    .entry-info { flex: 1; min-width: 0; }
    .entry-name { display: block; font-size: 0.875rem; color: #111; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .entry-meta { display: block; font-size: 0.75rem; color: #9ca3af; }
    .btn-view { padding: 0.2rem 0.5rem; border: 1px solid #bfdbfe; background: #eff6ff; color: #2563eb; border-radius: 4px; font-size: 0.75rem; cursor: pointer; }
    .btn-view:hover { background: #dbeafe; }
    .empty { padding: 2rem; text-align: center; color: #9ca3af; font-size: 0.875rem; }
  `]
})
export class PblListComponent implements OnChanges {
  @Input() pblPath = '';
  @Output() entrySelected = new EventEmitter<{ path: string; name: string; source: string }>();

  parseResult: ParseResult | null = null;
  selectedEntry: PblEntry | null = null;
  filter: FilterType = 'all';
  searchQuery = '';
  loading = false;
  error = '';

  constructor(private pblService: PblService) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['pblPath'] && this.pblPath) {
      this.loadPbl();
    }
  }

  async loadPbl() {
    this.loading = true;
    this.error = '';
    this.parseResult = null;
    try {
      this.parseResult = await this.pblService.parsePbl(this.pblPath);
    } catch (e: any) {
      this.error = e.message || '解析失败';
    } finally {
      this.loading = false;
    }
  }

  reload() { this.loadPbl(); }

  get filteredEntries(): PblEntry[] {
    if (!this.parseResult) return [];
    let list = this.parseResult.entries;
    if (this.filter === 'source') list = list.filter(e => e.is_source);
    if (this.filter === 'compiled') list = list.filter(e => e.is_compiled);
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase();
      list = list.filter(e => e.name.toLowerCase().includes(q));
    }
    return list;
  }

  get fileName(): string {
    return this.pblPath.split(/[\\/]/).pop() ?? this.pblPath;
  }

  selectEntry(entry: PblEntry) {
    this.selectedEntry = entry;
  }

  async viewSource(entry: PblEntry, event: Event) {
    event.stopPropagation();
    try {
      const source = await this.pblService.exportEntry(this.pblPath, entry.name);
      this.entrySelected.emit({ path: this.pblPath, name: entry.name, source });
    } catch (e: any) {
      this.error = e.message || '读取源码失败';
    }
  }

  async exportAll() {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: '选择源码导出目录'
      });
      if (!selected) return;

      this.loading = true;
      const msg = await this.pblService.exportPbl(this.pblPath, selected as string, false);
      this.error = '';
      // 简单 Toast 提示（用 error 字段借用，稍后 2 秒清除）
      this.error = '✅ ' + msg;
      setTimeout(() => { if (this.error.startsWith('✅')) this.error = ''; }, 3000);
    } catch (e: any) {
      this.error = e.message ?? '导出失败';
    } finally {
      this.loading = false;
    }
  }

  typeIcon(type: string): string {
    const icons: Record<string, string> = {
      window: '🪟', datawindow: '📊', menu: '☰', function: 'ƒ',
      structure: '🔷', userobject: '🧩', application: '🚀',
      query: '🔍', pipeline: '🔗', project: '📋', proxy: '🔁',
      binary: '🔢', unknown: '❓'
    };
    return icons[type.toLowerCase()] ?? '📄';
  }

  formatSize(bytes: number): string {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }
}