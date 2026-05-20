import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { open } from '@tauri-apps/plugin-dialog';
import { PblService, PblEntry, ParseResult } from '../../services/pbl.service';

interface TypeGroup {
  typeName: string;
  icon: string;
  color: string;
  entries: PblEntry[];
  expanded: boolean;
}

@Component({
  selector: 'app-pbl-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="pbl-tree">

      <!-- 工具栏 -->
      <div class="tree-toolbar">
        <div class="tree-title">
          <span class="material-icons tree-title-icon">inventory_2</span>
          <span class="tree-title-text" [title]="pblPath">{{ fileName }}</span>
        </div>
        <div class="tree-actions">
          <button class="tbtn" (click)="expandAll()" title="展开全部"><span class="material-icons">unfold_more</span></button>
          <button class="tbtn" (click)="collapseAll()" title="折叠全部"><span class="material-icons">unfold_less</span></button>
          <button class="tbtn" (click)="exportAll()" title="导出全部" [disabled]="loading || !parseResult">
            <span class="material-icons">download</span>
          </button>
          <button class="tbtn" (click)="reload()" title="刷新" [disabled]="loading">
            <span class="material-icons">refresh</span>
          </button>
        </div>
      </div>

      <!-- 搜索框 -->
      <div class="tree-search">
        <span class="material-icons search-ic">search</span>
        <input [(ngModel)]="searchQuery" (ngModelChange)="rebuildGroups()" placeholder="过滤对象..." class="search-input" />
        @if (searchQuery) {
          <button class="search-clear" (click)="searchQuery=''; rebuildGroups()">
            <span class="material-icons">close</span>
          </button>
        }
      </div>

      <!-- 统计 -->
      @if (parseResult && !loading) {
        <div class="tree-stats">
          <span class="badge badge-src" title="有源码">
            <span class="material-icons">description</span> {{ parseResult.source_count }}
          </span>
          <span class="badge badge-bin" title="仅编译">
            <span class="material-icons">build</span> {{ parseResult.compiled_count }}
          </span>
          <span class="badge badge-all">共 {{ parseResult.total_count }}</span>
        </div>
      }

      <!-- 加载 -->
      @if (loading) {
        <div class="tree-loading">
          <div class="spinner"></div><span>解析中...</span>
        </div>
      }

      <!-- 消息 -->
      @if (statusMsg) {
        <div class="tree-msg" [class.success]="statusMsg.startsWith('✓')">{{ statusMsg }}</div>
      }

      <!-- 树体 -->
      @if (!loading && groups.length > 0) {
        <div class="tree-body">
          @for (group of groups; track group.typeName) {

            <!-- 类型分组行 -->
            <div class="tree-group-row" (click)="toggleGroup(group)">
              <span class="material-icons chevron">{{ group.expanded ? 'expand_more' : 'chevron_right' }}</span>
              <span class="material-icons type-ic" [style.color]="group.color">{{ group.icon }}</span>
              <span class="group-label">{{ group.typeName }}</span>
              <span class="group-count">{{ group.entries.length }}</span>
            </div>

            <!-- 对象子节点 -->
            @if (group.expanded) {
              @for (entry of group.entries; track entry.name) {
                <div class="tree-leaf"
                     [class.selected]="selectedEntry?.name === entry.name"
                     (click)="selectEntry(entry)"
                     (dblclick)="dblClickEntry(entry)">
                  <span class="leaf-indent"></span>
                  <span class="material-icons leaf-ic"
                        [style.color]="entry.is_source ? '#4ade80' : '#f59e0b'">
                    {{ entry.is_source ? 'article' : 'lock' }}
                  </span>
                  <span class="leaf-name" [title]="entry.name">{{ entry.name }}</span>
                  @if (entry.is_source) {
                    <button class="btn-code" (click)="viewSource(entry, $event)" title="查看源码">
                      <span class="material-icons">code</span>
                    </button>
                  }
                </div>
              }
            }

          }
        </div>
      }

      @if (!loading && parseResult && groups.length === 0) {
        <div class="tree-empty">
          <span class="material-icons" style="font-size:30px;color:#45475a">search_off</span>
          <p>无匹配对象</p>
        </div>
      }

    </div>
  `,
  styles: [`
    .pbl-tree {
      display: flex; flex-direction: column; height: 100%;
      background: #1e1e2e; color: #cdd6f4; font-size: 0.82rem; overflow: hidden;
    }

    /* 工具栏 */
    .tree-toolbar {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.3rem 0.4rem 0.3rem 0.6rem;
      border-bottom: 1px solid #313244; flex-shrink: 0; gap: 0.3rem;
    }
    .tree-title { display: flex; align-items: center; gap: 0.3rem; min-width: 0; flex: 1; }
    .tree-title-icon { font-size: 14px; color: #cba6f7; flex-shrink: 0; }
    .tree-title-text {
      font-size: 0.75rem; font-weight: 600; color: #cdd6f4;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .tree-actions { display: flex; gap: 1px; flex-shrink: 0; }
    .tbtn {
      width: 22px; height: 22px; border: none; background: transparent;
      cursor: pointer; border-radius: 3px; color: #6c7086;
      display: flex; align-items: center; justify-content: center;
    }
    .tbtn .material-icons { font-size: 14px; }
    .tbtn:hover:not(:disabled) { background: #313244; color: #cdd6f4; }
    .tbtn:disabled { opacity: 0.35; cursor: not-allowed; }

    /* 搜索 */
    .tree-search {
      display: flex; align-items: center; gap: 0.3rem;
      padding: 0.28rem 0.5rem; border-bottom: 1px solid #313244; flex-shrink: 0;
    }
    .search-ic { font-size: 13px; color: #45475a; flex-shrink: 0; }
    .search-input {
      flex: 1; background: #181825; border: 1px solid #313244; border-radius: 3px;
      color: #cdd6f4; font-size: 0.76rem; padding: 0.18rem 0.4rem; outline: none;
    }
    .search-input::placeholder { color: #45475a; }
    .search-input:focus { border-color: #7c3aed; }
    .search-clear {
      background: none; border: none; cursor: pointer; color: #6c7086;
      display: flex; align-items: center; padding: 1px;
    }
    .search-clear .material-icons { font-size: 13px; }
    .search-clear:hover { color: #cdd6f4; }

    /* 统计 */
    .tree-stats {
      display: flex; gap: 0.3rem; padding: 0.2rem 0.5rem;
      border-bottom: 1px solid #313244; flex-shrink: 0; background: #181825;
    }
    .badge {
      display: flex; align-items: center; gap: 0.2rem;
      padding: 0.08rem 0.4rem; border-radius: 10px; font-size: 0.68rem;
    }
    .badge .material-icons { font-size: 10px; }
    .badge-src { background: #14532d; color: #86efac; }
    .badge-bin { background: #451a03; color: #fcd34d; }
    .badge-all { background: #1e1b4b; color: #a5b4fc; font-weight: 600; }

    /* 状态 */
    .tree-loading {
      display: flex; align-items: center; gap: 0.5rem;
      padding: 1.5rem; justify-content: center; color: #6c7086;
    }
    .spinner {
      width: 14px; height: 14px; border: 2px solid #313244;
      border-top-color: #cba6f7; border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .tree-msg {
      margin: 0.25rem 0.4rem; padding: 0.3rem 0.5rem;
      border-radius: 4px; font-size: 0.74rem;
      background: #3b0764; color: #e9d5ff;
    }
    .tree-msg.success { background: #14532d; color: #bbf7d0; }
    .tree-empty {
      flex: 1; display: flex; flex-direction: column;
      align-items: center; justify-content: center; color: #45475a;
    }
    .tree-empty p { margin: 0.3rem 0 0; font-size: 0.78rem; }

    /* 树体 */
    .tree-body { flex: 1; overflow-y: auto; }

    /* 分组行 */
    .tree-group-row {
      display: flex; align-items: center; gap: 0.2rem;
      padding: 0.26rem 0.4rem; cursor: pointer; user-select: none;
      border-bottom: 1px solid #181825;
    }
    .tree-group-row:hover { background: #313244; }
    .chevron { font-size: 14px; color: #6c7086; flex-shrink: 0; }
    .type-ic { font-size: 14px; flex-shrink: 0; }
    .group-label { flex: 1; font-size: 0.76rem; font-weight: 600; color: #a6adc8; }
    .group-count {
      font-size: 0.66rem; color: #6c7086;
      background: #313244; padding: 0.06rem 0.3rem; border-radius: 8px;
    }

    /* 对象行 */
    .tree-leaf {
      display: flex; align-items: center; gap: 0.2rem;
      padding: 0.2rem 0.4rem; cursor: pointer;
      border-bottom: 1px solid #181825;
    }
    .tree-leaf:hover { background: #2a2a3e; }
    .tree-leaf.selected {
      background: #2a2a3e; border-left: 2px solid #cba6f7;
    }
    .leaf-indent { width: 20px; flex-shrink: 0; }
    .leaf-ic { font-size: 13px; flex-shrink: 0; }
    .leaf-name {
      flex: 1; font-size: 0.79rem; color: #cdd6f4;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .tree-leaf.selected .leaf-name { color: #cba6f7; }

    .btn-code {
      background: none; border: none; cursor: pointer; color: #45475a;
      display: flex; align-items: center; padding: 1px; border-radius: 3px;
      opacity: 0; transition: opacity 0.1s;
    }
    .tree-leaf:hover .btn-code,
    .tree-leaf.selected .btn-code { opacity: 1; }
    .btn-code .material-icons { font-size: 13px; }
    .btn-code:hover { color: #cba6f7; background: #313244; }
  `]
})
export class PblListComponent implements OnChanges {
  @Input() pblPath = '';
  @Output() entrySelected = new EventEmitter<{ path: string; name: string; source: string; error?: string }>();

  parseResult: ParseResult | null = null;
  selectedEntry: PblEntry | null = null;
  searchQuery = '';
  loading = false;
  statusMsg = '';

  /** 当前展示的分组列表（可直接操作 expanded） */
  groups: TypeGroup[] = [];

  /** 记录每个类型上次的展开状态，切换搜索后保留 */
  private expandMap = new Map<string, boolean>();

  constructor(private pblService: PblService) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['pblPath'] && this.pblPath) {
      this.loadPbl();
    }
  }

  async loadPbl() {
    this.loading = true;
    this.statusMsg = '';
    this.parseResult = null;
    this.selectedEntry = null;
    this.groups = [];
    this.expandMap.clear();
    try {
      this.parseResult = await this.pblService.parsePbl(this.pblPath);
      this.rebuildGroups();
    } catch (e: any) {
      this.statusMsg = e.message || '解析失败';
    } finally {
      this.loading = false;
    }
  }

  reload() { this.loadPbl(); }

  get fileName(): string {
    return this.pblPath.split(/[\\/]/).pop() ?? this.pblPath;
  }

  rebuildGroups() {
    if (!this.parseResult) { this.groups = []; return; }

    let list = this.parseResult.entries;
    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase();
      list = list.filter(e => e.name.toLowerCase().includes(q));
    }

    const map = new Map<string, PblEntry[]>();
    for (const e of list) {
      const tn = e.entry_type_name || 'unknown';
      if (!map.has(tn)) map.set(tn, []);
      map.get(tn)!.push(e);
    }

    const newGroups: TypeGroup[] = [];
    for (const [typeName, entries] of map) {
      const expanded = this.expandMap.has(typeName) ? this.expandMap.get(typeName)! : true;
      newGroups.push({ typeName, icon: this.typeIcon(typeName), color: this.typeColor(typeName), entries, expanded });
    }
    newGroups.sort((a, b) => b.entries.length - a.entries.length);
    this.groups = newGroups;
  }

  toggleGroup(group: TypeGroup) {
    group.expanded = !group.expanded;
    this.expandMap.set(group.typeName, group.expanded);
  }

  expandAll() {
    for (const g of this.groups) { g.expanded = true; this.expandMap.set(g.typeName, true); }
  }

  collapseAll() {
    for (const g of this.groups) { g.expanded = false; this.expandMap.set(g.typeName, false); }
  }

  selectEntry(entry: PblEntry) { this.selectedEntry = entry; }

  async dblClickEntry(entry: PblEntry) {
    if (!entry.is_source) return;
    await this.loadSource(entry);
  }

  async viewSource(entry: PblEntry, event: Event) {
    event.stopPropagation();
    await this.loadSource(entry);
  }

  private async loadSource(entry: PblEntry) {
    try {
      const source = await this.pblService.exportEntry(this.pblPath, entry.name);
      this.entrySelected.emit({ path: this.pblPath, name: entry.name, source });
    } catch (e: any) {
      const errMsg = e.message || '读取源码失败';
      this.statusMsg = errMsg;
      // 也把错误传给右栏显示，让用户知道出了什么问题
      this.entrySelected.emit({ path: this.pblPath, name: entry.name, source: '', error: errMsg });
      setTimeout(() => { this.statusMsg = ''; }, 4000);
    }
  }

  async exportAll() {
    try {
      const selected = await open({ directory: true, multiple: false, title: '选择源码导出目录' });
      if (!selected) return;
      this.loading = true;
      const msg = await this.pblService.exportPbl(this.pblPath, selected as string, false);
      this.statusMsg = '✓ ' + msg;
      setTimeout(() => { this.statusMsg = ''; }, 3000);
    } catch (e: any) {
      this.statusMsg = e.message ?? '导出失败';
    } finally {
      this.loading = false;
    }
  }

  typeIcon(type: string): string {
    const m: Record<string, string> = {
      window: 'web_asset', datawindow: 'table_chart', menu: 'menu',
      function: 'functions', structure: 'schema', userobject: 'widgets',
      application: 'rocket_launch', query: 'manage_search',
      pipeline: 'account_tree', project: 'folder_special',
      proxy: 'swap_horiz', binary: 'memory', unknown: 'help_outline'
    };
    return m[type.toLowerCase()] ?? 'description';
  }

  typeColor(type: string): string {
    const m: Record<string, string> = {
      window: '#60a5fa', datawindow: '#a78bfa', menu: '#34d399',
      function: '#fbbf24', structure: '#f87171', userobject: '#22d3ee',
      application: '#c084fc', query: '#818cf8', pipeline: '#2dd4bf',
      project: '#6366f1', proxy: '#8b5cf6', binary: '#9ca3af', unknown: '#6b7280'
    };
    return m[type.toLowerCase()] ?? '#6b7280';
  }
}
