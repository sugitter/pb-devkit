import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PblService, PblEntry, PblFileInfo, DecompileEntry } from '../../services/pbl.service';

/** 按类型分组的对象节点 */
interface TypeGroup {
  typeName: string;
  icon: string;
  color: string;
  entries: PblEntry[];
  expanded: boolean;
}

@Component({
  selector: 'app-object-browser',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="object-browser">
      <div class="ob-header">
        <span class="material-icons" style="font-size:18px;color:#7c3aed">account_tree</span>
        <span class="ob-title">对象浏览器</span>
      </div>

      <!-- 视图切换 -->
      <div class="ob-view-toggle">
        <button class="vt-btn" [class.active]="viewMode==='flat'" (click)="viewMode='flat'">
          <span class="material-icons" style="font-size:14px">list</span> 列表
        </button>
        <button class="vt-btn" [class.active]="viewMode==='group'" (click)="viewMode='group'">
          <span class="material-icons" style="font-size:14px">folder</span> 分组
        </button>
      </div>

      <!-- 搜索过滤 -->
      <div class="ob-search">
        <input [(ngModel)]="searchQuery" placeholder="过滤对象..." class="ob-filter-input" />
        @if (searchQuery) {
          <button class="ob-clear-btn" (click)="searchQuery=''">
            <span class="material-icons" style="font-size:14px">close</span>
          </button>
        }
      </div>

      @if (loading) {
        <div class="ob-loading">
          <div class="spinner"></div>
          <span>加载中...</span>
        </div>
      }

      @if (error) {
        <div class="ob-error">{{ error }}</div>
      }

      <!-- 统计信息 -->
      @if (!loading && allEntries.length > 0) {
        <div class="ob-stats">
          <span class="stat-chip source">
            <span class="material-icons" style="font-size:12px">description</span>
            {{ sourceCount }}
          </span>
          <span class="stat-chip compiled">
            <span class="material-icons" style="font-size:12px">build</span>
            {{ compiledCount }}
          </span>
          <span class="stat-chip total">{{ allEntries.length }}</span>
        </div>
      }

      <!-- 列表视图 -->
      @if (viewMode === 'flat') {
        <div class="ob-list">
          @for (entry of filteredEntries; track entry.name) {
            <div class="ob-entry"
                 [class.selected]="selectedEntry?.name === entry.name"
                 (click)="selectEntry(entry)"
                 (dblclick)="viewSource(entry)">
              <span class="type-icon" [style.color]="typeColor(entry.entry_type_name)">
                <span class="material-icons" style="font-size:16px">{{ typeIcon(entry.entry_type_name) }}</span>
              </span>
              <div class="entry-info">
                <span class="entry-name">{{ entry.name }}</span>
                <span class="entry-meta">{{ entry.entry_type_name }}</span>
              </div>
              @if (entry.is_source) {
                <button class="btn-view" (click)="viewSource(entry); $event.stopPropagation()" title="查看源码">
                  <span class="material-icons" style="font-size:13px">code</span>
                </button>
              }
            </div>
          }
          @if (filteredEntries.length === 0 && !loading) {
            <div class="ob-empty">{{ searchQuery ? '无匹配对象' : '暂无对象' }}</div>
          }
        </div>
      }

      <!-- 分组视图 -->
      @if (viewMode === 'group') {
        <div class="ob-groups">
          @for (group of typeGroups; track group.typeName) {
            <div class="ob-group">
              <div class="ob-group-header" (click)="group.expanded=!group.expanded">
                <span class="material-icons" style="font-size:14px">{{ group.expanded ? 'expand_more' : 'chevron_right' }}</span>
                <span class="material-icons" style="font-size:14px" [style.color]="group.color">{{ group.icon }}</span>
                <span class="group-label">{{ group.typeName }}</span>
                <span class="group-count">{{ group.entries.length }}</span>
              </div>
              @if (group.expanded) {
                @for (entry of group.entries; track entry.name) {
                  <div class="ob-entry ob-entry-indent"
                       [class.selected]="selectedEntry?.name === entry.name"
                       (click)="selectEntry(entry)"
                       (dblclick)="viewSource(entry)">
                    <span class="material-icons" style="font-size:13px;color:#9ca3af">description</span>
                    <span class="entry-name-flat">{{ entry.name }}</span>
                    @if (entry.is_source) {
                      <button class="btn-view-sm" (click)="viewSource(entry); $event.stopPropagation()">
                        <span class="material-icons" style="font-size:12px">code</span>
                      </button>
                    }
                  </div>
                }
              }
            </div>
          }
          @if (typeGroups.length === 0 && !loading) {
            <div class="ob-empty">{{ searchQuery ? '无匹配对象' : '暂无对象' }}</div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .object-browser { display: flex; flex-direction: column; height: 100%; background: #fff; }
    .ob-header { display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 0.75rem; border-bottom: 1px solid #e5e7eb; }
    .ob-title { font-size: 0.85rem; font-weight: 600; color: #111; }

    .ob-view-toggle { display: flex; gap: 2px; padding: 0.4rem 0.75rem; border-bottom: 1px solid #e5e7eb; background: #f9fafb; }
    .vt-btn { flex: 1; padding: 0.3rem 0; border: 1px solid #d1d5db; background: #fff; cursor: pointer; font-size: 0.75rem; border-radius: 4px; display: flex; align-items: center; justify-content: center; gap: 0.25rem; color: #6b7280; }
    .vt-btn:hover { background: #f3f4f6; }
    .vt-btn.active { background: #eff6ff; border-color: #93c5fd; color: #2563eb; font-weight: 600; }

    .ob-search { padding: 0.4rem 0.75rem; border-bottom: 1px solid #e5e7eb; position: relative; }
    .ob-filter-input { width: 100%; padding: 0.35rem 0.65rem; padding-right: 24px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; box-sizing: border-box; }
    .ob-clear-btn { position: absolute; right: calc(0.75rem + 4px); top: 50%; transform: translateY(-50%); background: none; border: none; cursor: pointer; color: #9ca3af; padding: 2px; }
    .ob-clear-btn:hover { color: #374151; }

    .ob-loading { display: flex; align-items: center; gap: 0.5rem; padding: 1.5rem; justify-content: center; color: #6b7280; font-size: 0.85rem; }
    .spinner { width: 16px; height: 16px; border: 2px solid #e5e7eb; border-top-color: #7c3aed; border-radius: 50%; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .ob-error { padding: 0.6rem 0.75rem; margin: 0.4rem; background: #fee2e2; color: #dc2626; border-radius: 4px; font-size: 0.8rem; }

    .ob-stats { display: flex; gap: 0.4rem; padding: 0.4rem 0.75rem; border-bottom: 1px solid #e5e7eb; background: #f9fafb; }
    .stat-chip { padding: 0.15rem 0.5rem; border-radius: 10px; font-size: 0.72rem; display: flex; align-items: center; gap: 0.2rem; }
    .stat-chip.source { background: #dcfce7; color: #166534; }
    .stat-chip.compiled { background: #fef3c7; color: #92400e; }
    .stat-chip.total { background: #eff6ff; color: #1d4ed8; font-weight: 600; }

    .ob-list { flex: 1; overflow-y: auto; }
    .ob-entry { display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.75rem; cursor: pointer; border-bottom: 1px solid #f3f4f6; }
    .ob-entry:hover { background: #f9fafb; }
    .ob-entry.selected { background: #eff6ff; }
    .ob-entry-indent { padding-left: 1.5rem; }

    .type-icon { flex-shrink: 0; }
    .entry-info { flex: 1; min-width: 0; }
    .entry-name { display: block; font-size: 0.82rem; color: #111; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .entry-meta { display: block; font-size: 0.7rem; color: #9ca3af; }
    .entry-name-flat { flex: 1; font-size: 0.8rem; color: #374151; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    .btn-view { padding: 0.15rem 0.4rem; border: 1px solid #bfdbfe; background: #eff6ff; color: #2563eb; border-radius: 3px; cursor: pointer; }
    .btn-view:hover { background: #dbeafe; }
    .btn-view-sm { background: none; border: none; cursor: pointer; color: #93c5fd; padding: 2px; }
    .btn-view-sm:hover { color: #2563eb; }

    .ob-groups { flex: 1; overflow-y: auto; }
    .ob-group-header { display: flex; align-items: center; gap: 0.3rem; padding: 0.4rem 0.75rem; cursor: pointer; user-select: none; }
    .ob-group-header:hover { background: #f9fafb; }
    .group-label { flex: 1; font-size: 0.8rem; font-weight: 500; color: #374151; }
    .group-count { font-size: 0.7rem; color: #6b7280; background: #f3f4f6; padding: 0.1rem 0.35rem; border-radius: 8px; }

    .ob-empty { padding: 2rem; text-align: center; color: #9ca3af; font-size: 0.82rem; }
  `]
})
export class ObjectBrowserComponent implements OnChanges {
  @Input() pblFiles: PblFileInfo[] = [];
  @Input() exeFiles: string[] = [];
  @Output() entrySelected = new EventEmitter<{ path: string; name: string; source: string }>();

  allEntries: PblEntry[] = [];
  selectedEntry: PblEntry | null = null;
  searchQuery = '';
  viewMode: 'flat' | 'group' = 'flat';
  loading = false;
  error = '';

  constructor(private pblService: PblService) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['pblFiles'] || changes['exeFiles']) {
      this.loadAllEntries();
    }
  }

  async loadAllEntries() {
    this.loading = true;
    this.error = '';
    this.allEntries = [];
    const seen = new Set<string>();

    try {
      // 加载所有 PBL 文件的对象
      for (const pbl of this.pblFiles) {
        try {
          const result = await this.pblService.parsePbl(pbl.path);
          for (const entry of result.entries) {
            if (!seen.has(entry.name)) {
              seen.add(entry.name);
              this.allEntries.push({ ...entry, _pblPath: pbl.path } as any);
            }
          }
        } catch (e: any) {
          console.warn(`Failed to parse ${pbl.name}:`, e.message);
        }
      }

      // 加载 EXE/PBD/DLL 的反编译条目
      for (const exe of this.exeFiles) {
        try {
          const result = await this.pblService.listDecompileEntries(exe);
          if (result.success && result.entries) {
            for (const de of result.entries) {
              const key = de.name + '_' + de.entry_type;
              if (!seen.has(key)) {
                seen.add(key);
                this.allEntries.push({
                  name: de.name,
                  entry_type: 0,
                  entry_type_name: de.entry_type,
                  size: de.size,
                  is_source: de.is_source,
                  is_compiled: !de.is_source,
                  version: '',
                  _binaryPath: exe,
                } as any);
              }
            }
          }
        } catch (e: any) {
          console.warn(`Failed to list decompile entries:`, e.message);
        }
      }
    } catch (e: any) {
      this.error = e.message || '加载失败';
    } finally {
      this.loading = false;
    }
  }

  get filteredEntries(): PblEntry[] {
    if (!this.searchQuery.trim()) return this.allEntries;
    const q = this.searchQuery.toLowerCase();
    return this.allEntries.filter(e => e.name.toLowerCase().includes(q) || e.entry_type_name.toLowerCase().includes(q));
  }

  get sourceCount(): number {
    return this.allEntries.filter(e => e.is_source).length;
  }

  get compiledCount(): number {
    return this.allEntries.filter(e => e.is_compiled).length;
  }

  get typeGroups(): TypeGroup[] {
    const map = new Map<string, PblEntry[]>();
    for (const e of this.filteredEntries) {
      const tn = e.entry_type_name;
      if (!map.has(tn)) map.set(tn, []);
      map.get(tn)!.push(e);
    }
    const groups: TypeGroup[] = [];
    for (const [typeName, entries] of map) {
      groups.push({
        typeName,
        icon: this.typeIcon(typeName),
        color: this.typeColor(typeName),
        entries,
        expanded: true,
      });
    }
    // 按数量排序
    groups.sort((a, b) => b.entries.length - a.entries.length);
    return groups;
  }

  selectEntry(entry: PblEntry) {
    this.selectedEntry = entry;
  }

  async viewSource(entry: PblEntry) {
    try {
      // 优先从 PBL 导出
      const pblPath = (entry as any)._pblPath;
      if (pblPath && entry.is_source) {
        const source = await this.pblService.exportEntry(pblPath, entry.name);
        this.entrySelected.emit({ path: pblPath, name: entry.name, source });
        return;
      }
      // 从二进制文件反编译
      const binaryPath = (entry as any)._binaryPath;
      if (binaryPath) {
        const result = await this.pblService.decompileEntry(binaryPath, entry.name);
        if (result.success && result.source) {
          this.entrySelected.emit({ path: binaryPath, name: entry.name, source: result.source });
          return;
        }
        throw new Error(result.error || '反编译失败');
      }
    } catch (e: any) {
      this.error = e.message || '读取源码失败';
      setTimeout(() => { this.error = ''; }, 3000);
    }
  }

  typeIcon(type: string): string {
    const icons: Record<string, string> = {
      window: 'window', datawindow: 'bar_chart', menu: 'menu',
      function: 'functions', structure: 'diamond', userobject: 'extension',
      application: 'rocket_launch', query: 'search', pipeline: 'link',
      project: 'assignment', proxy: 'sync', binary: 'pin', unknown: 'help'
    };
    return icons[type.toLowerCase()] ?? 'description';
  }

  typeColor(type: string): string {
    const colors: Record<string, string> = {
      window: '#2563eb', datawindow: '#7c3aed', menu: '#059669',
      function: '#d97706', structure: '#dc2626', userobject: '#0891b2',
      application: '#7c3aed', query: '#6366f1', pipeline: '#0d9488',
      project: '#4f46e5', proxy: '#8b5cf6', binary: '#6b7280', unknown: '#9ca3af'
    };
    return colors[type.toLowerCase()] ?? '#6b7280';
  }
}
