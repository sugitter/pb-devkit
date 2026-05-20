import { Component, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { open } from '@tauri-apps/plugin-dialog';
import { SourceViewerComponent } from './components/source-viewer/source-viewer.component';
import { SearchPanelComponent } from './components/search-panel/search-panel.component';
import { SearchRegexPanelComponent } from './components/search-regex-panel/search-regex-panel.component';
import { DwAnalyzerComponent } from './components/dw-analyzer/dw-analyzer.component';
import { DecompilePanelComponent } from './components/decompile-panel/decompile-panel.component';
import { DoctorPanelComponent } from './components/doctor-panel/doctor-panel.component';
import { PeViewComponent } from './components/pe-view/pe-view.component';
import { ReportViewComponent } from './components/report-view/report-view.component';
import { SettingsPanelComponent } from './components/settings-panel/settings-panel.component';
import { PblListComponent } from './components/pbl-list/pbl-list.component';
import { ObjectBrowserComponent } from './components/object-browser/object-browser.component';
import { ProjectStatsComponent } from './components/project-stats/project-stats.component';
import { DiffPanelComponent } from './components/diff-panel/diff-panel.component';
import { WorkflowPanelComponent } from './components/workflow-panel/workflow-panel.component';
import { PblService, ProjectInfo, PblFileInfo } from './services/pbl.service';

type Tab = 'explorer' | 'search' | 'dw' | 'doctor' | 'pe' | 'report' | 'stats' | 'diff' | 'workflow' | 'settings';
type ContentMode = 'welcome' | 'source' | 'loading';
type SearchMode = 'text' | 'regex';

/** 项目类型检测结果 */
type ProjectMode = 'pbl' | 'exe_pbd' | 'exe_dll' | 'mixed' | 'none';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    PblListComponent,
    SourceViewerComponent,
    SearchPanelComponent,
    SearchRegexPanelComponent,
    DwAnalyzerComponent,
    DecompilePanelComponent,
    DoctorPanelComponent,
    PeViewComponent,
    ReportViewComponent,
    SettingsPanelComponent,
    ObjectBrowserComponent,
    ProjectStatsComponent,
    DiffPanelComponent,
    WorkflowPanelComponent,
  ],
  template: `
    <div class="app-layout">

      <!-- 侧边栏图标 -->
      <nav class="sidebar">
        <div class="sidebar-logo" title="PB DevKit 2.0"><span class="material-icons mi-lg">bolt</span></div>
        <button class="nav-btn" [class.active]="activeTab==='explorer'" (click)="activeTab='explorer'" title="资源管理器"><span class="material-icons">folder</span></button>
        <button class="nav-btn" [class.active]="activeTab==='search'" (click)="activeTab='search'" title="全文搜索"><span class="material-icons">search</span></button>
        <button class="nav-btn" [class.active]="activeTab==='dw'" (click)="activeTab='dw'" title="DataWindow"><span class="material-icons">bar_chart</span></button>
        <button class="nav-btn" [class.active]="activeTab==='doctor'" (click)="activeTab='doctor'" title="环境诊断"><span class="material-icons">build</span></button>
        <button class="nav-btn" [class.active]="activeTab==='pe'" (click)="activeTab='pe'" title="PE 分析"><span class="material-icons">description</span></button>
        <button class="nav-btn" [class.active]="activeTab==='report'" (click)="activeTab='report'" title="项目报告"><span class="material-icons">assessment</span></button>
        <button class="nav-btn" [class.active]="activeTab==='stats'" (click)="activeTab='stats'" title="项目统计"><span class="material-icons">analytics</span></button>
        <button class="nav-btn" [class.active]="activeTab==='diff'" (click)="activeTab='diff'" title="代码对比"><span class="material-icons">compare</span></button>
        <button class="nav-btn" [class.active]="activeTab==='workflow'" (click)="activeTab='workflow'" title="工作流"><span class="material-icons">account_tree</span></button>
        <button class="nav-btn" [class.active]="activeTab==='settings'" (click)="activeTab='settings'" title="设置"><span class="material-icons">settings</span></button>
        <div class="sidebar-spacer"></div>
        <button class="nav-btn" (click)="showAbout=!showAbout" title="关于"><span class="material-icons">info</span></button>
      </nav>

      <!-- ============================================================
           Explorer Tab: 三栏布局
           左栏 (file-tree) | 中栏 (object-list) | 右栏 (source)
           ============================================================ -->
      @if (activeTab === 'explorer') {
        <div class="explorer-layout">

          <!-- 左栏：文件树 -->
          <aside class="file-tree-panel">
            <div class="ft-toolbar">
              <span class="ft-title">资源管理器</span>
              <div class="ft-actions">
                <button class="ft-btn" (click)="selectFolder()" title="选择项目文件夹">
                  <span class="material-icons">folder_open</span>
                </button>
                <button class="ft-btn" (click)="selectSingleFile()" title="选择单个文件 (PBL/PBD/EXE/DLL)">
                  <span class="material-icons">insert_drive_file</span>
                </button>
                @if (projectPath) {
                  <button class="ft-btn" (click)="clearAll()" title="关闭项目">
                    <span class="material-icons">close</span>
                  </button>
                }
              </div>
            </div>

            @if (ftLoading) {
              <div class="ft-loading">
                <div class="spinner"></div>
                <span>扫描项目...</span>
              </div>
            }

            @if (!projectPath && !ftLoading) {
              <div class="ft-empty">
                <span class="material-icons ft-empty-icon">folder_open</span>
                <p>选择项目文件夹</p>
                <p class="ft-hint">支持 PBL 源码项目、EXE+PBD 或 EXE+DLL 部署目录</p>
                <button class="ft-open-btn" (click)="selectFolder()">
                  <span class="material-icons">folder</span> 打开文件夹
                </button>
                <div class="ft-divider">或</div>
                <button class="ft-open-btn ft-open-btn-sec" (click)="selectSingleFile()">
                  <span class="material-icons">insert_drive_file</span> 直接选文件
                </button>
              </div>
            }

            @if (projectPath && !ftLoading) {
              <!-- 项目根路径 -->
              <div class="ft-project-root" [title]="projectPath">
                <span class="material-icons ft-root-icon">{{ projectIcon }}</span>
                <span class="ft-root-name">{{ projectName }}</span>
              </div>

              <!-- PBL 区块 -->
              @if (pblFiles.length > 0) {
                <div class="ft-section">
                  <div class="ft-section-header" (click)="pblExpanded=!pblExpanded">
                    <span class="material-icons ft-chevron">{{ pblExpanded ? 'expand_more' : 'chevron_right' }}</span>
                    <span class="material-icons ft-section-icon" style="color:#7c3aed">inventory_2</span>
                    <span class="ft-section-label">PBL 源码库</span>
                    <span class="ft-count">{{ pblFiles.length }}</span>
                  </div>
                  @if (pblExpanded) {
                    @for (f of pblFiles; track f.path) {
                      <div class="ft-file-item"
                           [class.active]="selectedFilePath === f.path"
                           (click)="selectPblFile(f)">
                        <span class="material-icons ft-file-icon">inventory_2</span>
                        <span class="ft-file-name" [title]="f.path">{{ f.name }}</span>
                        <span class="ft-file-size">{{ formatSize(f.size) }}</span>
                      </div>
                    }
                  }
                </div>
              }

              <!-- EXE/PBD/DLL 区块 -->
              @if (exeFiles.length > 0) {
                <div class="ft-section">
                  <div class="ft-section-header" (click)="exeExpanded=!exeExpanded">
                    <span class="material-icons ft-chevron">{{ exeExpanded ? 'expand_more' : 'chevron_right' }}</span>
                    <span class="material-icons ft-section-icon" style="color:#d97706">settings</span>
                    <span class="ft-section-label">可执行文件</span>
                    <span class="ft-count">{{ exeFiles.length }}</span>
                  </div>
                  @if (exeExpanded) {
                    @for (f of exeFiles; track f) {
                      <div class="ft-file-item"
                           [class.active]="selectedFilePath === f"
                           (click)="selectBinaryFile(f)">
                        <span class="material-icons ft-file-icon">{{ binaryIcon(f) }}</span>
                        <span class="ft-file-name" [title]="f">{{ getFileName(f) }}</span>
                      </div>
                    }
                  }
                </div>
              }

              @if (pblFiles.length === 0 && exeFiles.length === 0) {
                <div class="ft-no-files">
                  <span class="material-icons" style="color:#f59e0b">warning</span>
                  <span>未检测到 PB 项目文件</span>
                </div>
              }
            }
          </aside>

          <!-- 中栏：对象列表 -->
          <div class="object-panel" [class.has-file]="!!selectedFilePath">
            @if (!selectedFilePath) {
              <div class="obj-empty">
                <span class="material-icons obj-empty-icon">list_alt</span>
                <p>选择左侧文件查看对象列表</p>
              </div>
            } @else if (isPblFile(selectedFilePath)) {
              <app-pbl-list
                [pblPath]="selectedFilePath"
                (entrySelected)="onEntrySelected($event)"
              />
            } @else {
              <app-decompile-panel
                [filePath]="selectedFilePath"
                (entrySelected)="onEntrySelected($event)"
              />
            }
          </div>

          <!-- 右栏：源码查看器 -->
          <main class="source-panel">
            @if (contentMode === 'source' || contentMode === 'loading') {
              <app-source-viewer
                [entryName]="viewerEntryName"
                [source]="viewerSource"
                [loadError]="viewerError"
              />
            } @else {
              <div class="welcome-screen">
                <div class="welcome-icon"><span class="material-icons mi-2xl">bolt</span></div>
                <h2>PB DevKit 2.1</h2>
                <p class="welcome-sub">PowerBuilder Legacy System Toolkit</p>
                <p class="welcome-hint">← 选择左侧文件，在中栏双击对象查看源码</p>
              </div>
            }
          </main>
        </div>
      }

      <!-- 其他 Tab：Search 用双栏，其余单栏 -->
      @if (activeTab !== 'explorer') {
        <div class="other-tab-layout">
          @if (activeTab === 'search') {
            <!-- 搜索 Tab：左侧搜索面板 + 右侧空间（搜索结果在面板内部滚动） -->
            <div class="search-tab-wrapper">
              <div class="search-mode-bar">
                <button class="search-mode-btn" [class.active]="searchMode==='text'" (click)="searchMode='text'">
                  <span class="material-icons" style="font-size:15px">search</span> 全文搜索
                </button>
                <button class="search-mode-btn" [class.active]="searchMode==='regex'" (click)="searchMode='regex'">
                  <span class="material-icons" style="font-size:15px">code</span> 正则搜索
                </button>
              </div>
              @if (searchMode === 'text') {
                <app-search-panel [rootPath]="searchRootPath" (fileSelected)="onSearchFileSelected($event)" />
              } @else {
                <app-search-regex-panel [rootPath]="searchRootPath" (fileSelected)="onSearchFileSelected($event)" />
              }
            </div>
          }
          @if (activeTab === 'dw') {
            <app-dw-analyzer [rootPath]="searchRootPath" />
          }
          @if (activeTab === 'doctor') {
            <app-doctor-panel />
          }
          @if (activeTab === 'pe') {
            <app-pe-view
              [filePath]="selectedFilePath"
              [data]="peViewData"
              (onClose)="activeTab='explorer'"
              (onExtract)="doExtractPbd()"
            />
          }
          @if (activeTab === 'report') {
            <app-report-view
              [data]="reportViewData"
              (onClose)="activeTab='explorer'"
              (onExport)="doExportReport()"
            />
          }
          @if (activeTab === 'settings') {
            <app-settings-panel />
          }
          @if (activeTab === 'stats') {
            <app-project-stats [projectPath]="projectPath" />
          }
          @if (activeTab === 'diff') {
            <app-diff-panel (close)="activeTab='explorer'" />
          }
          @if (activeTab === 'workflow') {
            <app-workflow-panel [projectPath]="projectPath" />
          }
        </div>
      }

      <!-- 关于浮层 -->
      @if (showAbout) {
        <div class="overlay" (click)="showAbout=false">
          <div class="about-card" (click)="$event.stopPropagation()">
            <h2><span class="material-icons mi-lg">bolt</span> PB DevKit 2.1</h2>
            <p>PowerBuilder Legacy System Toolkit</p>
            <ul>
              <li><span class="material-icons" style="color:#dea584;font-size:16px;vertical-align:middle">terminal</span> Rust 核心引擎（零依赖 PBL/PBD/PE 解析）</li>
              <li><span class="material-icons" style="color:#dd0031;font-size:16px;vertical-align:middle">code</span> Angular 前端（standalone + 控制流语法）</li>
              <li><span class="material-icons" style="color:#24c8d8;font-size:16px;vertical-align:middle">computer</span> Tauri 2.x 桌面框架</li>
              <li><span class="material-icons" style="font-size:16px;vertical-align:middle">inventory_2</span> PBL/PBD/EXE 全格式支持</li>
              <li><span class="material-icons" style="font-size:16px;vertical-align:middle">search</span> 全文搜索 + <span class="material-icons" style="font-size:16px;vertical-align:middle">bar_chart</span> DataWindow 分析</li>
              <li><span class="material-icons" style="font-size:16px;vertical-align:middle">keyboard</span> CLI 命令行工具（pbdk 命令）</li>
            </ul>
            <p class="version">v2.1.0</p>
            <button (click)="showAbout=false">关闭</button>
          </div>
        </div>
      }

    </div>
  `,
  styles: [`
    /* ── 整体布局 ── */
    .app-layout { display: flex; height: 100vh; overflow: hidden; background: #f3f4f6; }

    /* ── 侧边栏 ── */
    .sidebar { width: 48px; background: #1e1e2e; display: flex; flex-direction: column; align-items: center; padding: 0.5rem 0; gap: 0.25rem; flex-shrink: 0; }
    .sidebar-logo { padding: 0.4rem; margin-bottom: 0.25rem; color: #cba6f7; }
    .sidebar-logo .material-icons { font-size: 22px; color: #cba6f7; }
    .nav-btn { width: 40px; height: 40px; border: none; background: transparent; cursor: pointer; border-radius: 6px; display: flex; align-items: center; justify-content: center; transition: background 0.15s; color: #a6adc8; }
    .nav-btn .material-icons { font-size: 20px; }
    .nav-btn:hover { background: #313244; color: #cdd6f4; }
    .nav-btn.active { background: #313244; color: #cba6f7; box-shadow: 2px 0 0 0 #cba6f7 inset; }
    .sidebar-spacer { flex: 1; }

    /* ── Explorer 三栏布局 ── */
    .explorer-layout { display: flex; flex: 1; overflow: hidden; min-width: 0; }

    /* 左栏：文件树 */
    .file-tree-panel {
      width: 220px;
      min-width: 180px;
      flex-shrink: 0;
      background: #1e1e2e;
      color: #cdd6f4;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border-right: 1px solid #313244;
    }
    .ft-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.4rem 0.6rem;
      border-bottom: 1px solid #313244;
      flex-shrink: 0;
    }
    .ft-title { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #a6adc8; }
    .ft-actions { display: flex; gap: 2px; }
    .ft-btn { width: 24px; height: 24px; border: none; background: transparent; cursor: pointer; border-radius: 4px; color: #a6adc8; display: flex; align-items: center; justify-content: center; }
    .ft-btn .material-icons { font-size: 16px; }
    .ft-btn:hover { background: #313244; color: #cdd6f4; }
    .ft-loading { display: flex; align-items: center; gap: 0.5rem; padding: 1rem; font-size: 0.8rem; color: #a6adc8; }
    .spinner { width: 14px; height: 14px; border: 2px solid #313244; border-top-color: #cba6f7; border-radius: 50%; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .ft-empty {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 1rem;
      gap: 0.4rem;
      text-align: center;
    }
    .ft-empty-icon { font-size: 36px; color: #45475a; }
    .ft-empty p { margin: 0; font-size: 0.8rem; color: #a6adc8; }
    .ft-hint { font-size: 0.7rem !important; color: #6c7086 !important; margin-top: -0.2rem !important; }
    .ft-open-btn {
      margin-top: 0.5rem;
      padding: 0.4rem 0.9rem;
      background: #2563eb;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.78rem;
      display: flex;
      align-items: center;
      gap: 0.3rem;
      width: 100%;
      justify-content: center;
    }
    .ft-open-btn:hover { background: #1d4ed8; }
    .ft-open-btn-sec { background: #313244; color: #cdd6f4; }
    .ft-open-btn-sec:hover { background: #45475a; }
    .ft-divider { font-size: 0.7rem; color: #6c7086; margin: 0.1rem 0; }

    .ft-project-root {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.45rem 0.6rem;
      border-bottom: 1px solid #313244;
      flex-shrink: 0;
      background: #181825;
    }
    .ft-root-icon { font-size: 16px; color: #cba6f7; flex-shrink: 0; }
    .ft-root-name { font-size: 0.8rem; font-weight: 600; color: #cdd6f4; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    .ft-section { flex-shrink: 0; }
    .ft-section-header {
      display: flex;
      align-items: center;
      gap: 0.3rem;
      padding: 0.35rem 0.6rem;
      cursor: pointer;
      user-select: none;
    }
    .ft-section-header:hover { background: #313244; }
    .ft-chevron { font-size: 14px; color: #6c7086; }
    .ft-section-icon { font-size: 14px; }
    .ft-section-label { font-size: 0.75rem; font-weight: 600; color: #a6adc8; flex: 1; text-transform: uppercase; letter-spacing: 0.04em; }
    .ft-count { font-size: 0.7rem; color: #6c7086; background: #313244; padding: 0.1rem 0.35rem; border-radius: 8px; }

    .ft-file-item {
      display: flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.3rem 0.6rem 0.3rem 1.4rem;
      cursor: pointer;
      font-size: 0.8rem;
    }
    .ft-file-item:hover { background: #313244; }
    .ft-file-item.active { background: #45475a; color: #cba6f7; }
    .ft-file-item.active .ft-file-icon { color: #cba6f7; }
    .ft-file-icon { font-size: 14px; color: #6c7086; flex-shrink: 0; }
    .ft-file-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .ft-file-size { font-size: 0.68rem; color: #6c7086; flex-shrink: 0; }
    .ft-no-files { display: flex; align-items: center; gap: 0.4rem; padding: 0.75rem 0.6rem; font-size: 0.78rem; color: #a6adc8; }

    /* 中栏：对象列表 */
    .object-panel {
      width: 280px;
      min-width: 220px;
      flex-shrink: 0;
      background: #fff;
      border-right: 1px solid #e5e7eb;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .obj-empty {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: #9ca3af;
      padding: 1.5rem;
      text-align: center;
    }
    .obj-empty-icon { font-size: 36px; color: #d1d5db; margin-bottom: 0.5rem; }
    .obj-empty p { margin: 0; font-size: 0.82rem; }

    /* 右栏：源码 */
    .source-panel { flex: 1; overflow: hidden; min-width: 0; background: #1e1e2e; }
    .welcome-screen { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #a6adc8; padding: 2rem; background: #1e1e2e; text-align: center; }
    .welcome-icon { margin-bottom: 1rem; color: #cba6f7; }
    .welcome-icon .material-icons { font-size: 48px; }
    .welcome-screen h2 { margin: 0 0 0.5rem; color: #cdd6f4; font-size: 1.4rem; }
    .welcome-sub { margin: 0 0 0.5rem; font-size: 0.85rem; color: #6c7086; }
    .welcome-hint { margin: 0; font-size: 0.8rem; color: #45475a; }

    /* 其他 Tab 全宽布局 */
    .other-tab-layout { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; background: #f3f4f6; }
    .other-tab-layout > * { flex: 1; overflow: hidden; }

    /* Search Tab 专属 */
    .search-tab-wrapper { display: flex; flex-direction: column; flex: 1; overflow: hidden; background: #fff; }
    .search-mode-bar { display: flex; gap: 0; border-bottom: 1px solid #e5e7eb; background: #f9fafb; flex-shrink: 0; }
    .search-mode-btn { flex: 1; padding: 0.45rem 1rem; border: none; background: transparent; cursor: pointer; font-size: 0.8rem; color: #6b7280; display: flex; align-items: center; justify-content: center; gap: 0.3rem; border-bottom: 2px solid transparent; transition: all 0.15s; }
    .search-mode-btn:hover { background: #f3f4f6; color: #374151; }
    .search-mode-btn.active { color: #2563eb; border-bottom-color: #2563eb; background: #fff; font-weight: 600; }
    .search-tab-wrapper > app-search-panel,
    .search-tab-wrapper > app-search-regex-panel { flex: 1; display: block; overflow: hidden; }

    /* 关于浮层 */
    .overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
    .about-card { background: #fff; border-radius: 12px; padding: 2rem; max-width: 400px; width: 90%; }
    .about-card h2 { margin: 0 0 0.5rem; display: flex; align-items: center; gap: 0.4rem; }
    .about-card h2 .material-icons { color: #7c3aed; }
    .about-card ul { list-style: none; padding-left: 0; }
    .about-card li { margin-bottom: 0.5rem; font-size: 0.9rem; display: flex; align-items: center; gap: 0.4rem; }
    .about-card li .material-icons { flex-shrink: 0; }
    .version { color: #9ca3af; font-size: 0.85rem; }
    .about-card button { padding: 0.5rem 1.5rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; margin-top: 0.5rem; }

    /* 通用 Material Icons 尺寸 */
    .mi-lg .material-icons, .material-icons.mi-lg { font-size: 22px; }
    .mi-2xl .material-icons, .material-icons.mi-2xl { font-size: 48px; }
    .material-icons.mi-xl { font-size: 32px; }
  `]
})
export class AppComponent {
  activeTab: Tab = 'explorer';
  contentMode: ContentMode = 'welcome';
  searchMode: SearchMode = 'text';

  // 文件树状态
  projectPath = '';
  projectName = '';
  projectIcon = 'folder';
  pblFiles: PblFileInfo[] = [];
  exeFiles: string[] = [];
  pblExpanded = true;
  exeExpanded = true;
  ftLoading = false;

  // 当前选中文件（用于中栏对象列表）
  selectedFilePath = '';

  // 源码查看器
  viewerEntryName = '';
  viewerSource = '';
  viewerError = '';

  showAbout = false;

  // PE View 数据
  peViewData: any = null;
  peLoading = false;

  // Report View 数据
  reportViewData: any = null;
  reportLoading = false;

  constructor(private pblService: PblService) {}

  // ──── 项目 / 文件选择 ────

  async selectFolder() {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: '选择 PowerBuilder 项目文件夹'
      });
      if (!selected) return;

      this.ftLoading = true;
      this.clearAll();

      const info = await this.pblService.detectProject(selected as string);
      this.projectPath = info.path;
      this.projectName = info.name;
      this.pblFiles = info.pbl_files ?? [];
      this.exeFiles = info.exe_files ?? [];

      // 判断项目图标
      if (this.pblFiles.length > 0 && this.exeFiles.length === 0) {
        this.projectIcon = 'inventory_2';       // 纯 PBL 源码项目
      } else if (this.pblFiles.length === 0 && this.exeFiles.length > 0) {
        this.projectIcon = 'settings';          // 纯 EXE/PBD/DLL 部署目录
      } else {
        this.projectIcon = 'folder';            // 混合
      }

      // 自动展开
      this.pblExpanded = this.pblFiles.length > 0;
      this.exeExpanded = this.exeFiles.length > 0 && this.pblFiles.length === 0;

      // 自动选中第一个文件
      if (this.pblFiles.length > 0) {
        this.selectPblFile(this.pblFiles[0]);
      } else if (this.exeFiles.length > 0) {
        this.selectBinaryFile(this.exeFiles[0]);
      }
    } catch (e: any) {
      console.error('selectFolder error:', e);
    } finally {
      this.ftLoading = false;
    }
  }

  async selectSingleFile() {
    try {
      const selected = await open({
        multiple: false,
        filters: [{ name: 'PB Files', extensions: ['pbl', 'pbd', 'exe', 'dll'] }],
        title: '选择 PBL / PBD / EXE / DLL 文件'
      });
      if (!selected) return;

      const path = selected as string;
      const name = this.getFileName(path);
      const ext = name.split('.').pop()?.toLowerCase() ?? '';

      this.clearAll();
      this.projectPath = path;
      this.projectName = name;

      if (ext === 'pbl') {
        this.projectIcon = 'inventory_2';
        const fake: PblFileInfo = { path, name, size: 0, is_unicode: false };
        this.pblFiles = [fake];
        this.pblExpanded = true;
        this.selectPblFile(fake);
      } else {
        this.projectIcon = 'settings';
        this.exeFiles = [path];
        this.exeExpanded = true;
        this.selectBinaryFile(path);
      }
    } catch (e: any) {
      console.error('selectSingleFile error:', e);
    }
  }

  selectPblFile(f: PblFileInfo) {
    this.selectedFilePath = f.path;
    this.contentMode = 'welcome';
    this.viewerSource = '';
  }

  selectBinaryFile(path: string) {
    this.selectedFilePath = path;
    this.contentMode = 'welcome';
    this.viewerSource = '';
  }

  // ──── 对象选择（来自中栏） ────

  onEntrySelected(e: { path: string; name: string; source: string; error?: string }) {
    this.viewerEntryName = e.name;
    this.viewerSource = e.source ?? '';
    this.viewerError = e.error ?? '';
    this.contentMode = 'source';
  }

  // ──── 清空 ────

  clearAll() {
    this.projectPath = '';
    this.projectName = '';
    this.pblFiles = [];
    this.exeFiles = [];
    this.selectedFilePath = '';
    this.viewerSource = '';
    this.viewerEntryName = '';
    this.viewerError = '';
    this.contentMode = 'welcome';
  }

  // ──── 工具方法 ────

  /** 搜索根路径：优先用项目目录，其次用选中文件的父目录 */
  get searchRootPath(): string {
    if (this.projectPath) return this.projectPath;
    if (this.selectedFilePath) {
      const parts = this.selectedFilePath.replace(/\\/g, '/').split('/');
      parts.pop();
      return parts.join('/');
    }
    return '';
  }

  isPblFile(path: string): boolean {
    return path.toLowerCase().endsWith('.pbl');
  }

  binaryIcon(path: string): string {
    const p = path.toLowerCase();
    if (p.endsWith('.exe')) return 'settings';
    if (p.endsWith('.pbd')) return 'lock_open';
    if (p.endsWith('.dll')) return 'build';
    return 'description';
  }

  getFileName(path: string): string {
    return path.split(/[\\/]/).pop() || path;
  }

  formatSize(bytes: number): string {
    if (!bytes) return '';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  extractPbd() {
    console.log('Extract PBD from:', this.selectedFilePath);
  }

  async doExtractPbd() {
    if (!this.selectedFilePath) return;
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: '选择 PBD 提取输出目录'
      });
      if (!selected) return;
      // TODO: 调用后端 API
      console.log('Extracting PBD from:', this.selectedFilePath, 'to', selected);
    } catch (e: any) {
      console.error('Extract PBD error:', e);
    }
  }

  exportReport() {
    console.log('Export report for:', this.projectPath);
  }

  async doExportReport() {
    if (!this.projectPath) return;
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: '选择报告输出目录'
      });
      if (!selected) return;
      await this.pblService.exportReport(this.projectPath, selected as string);
      console.log('Report exported to:', selected);
    } catch (e: any) {
      console.error('Export report error:', e);
    }
  }

  /** 从搜索结果点击文件时，跳转到 Explorer 并选中该 PBL */
  onSearchFileSelected(filePath: string) {
    this.activeTab = 'explorer';
    if (this.pblFiles.some(f => f.path === filePath)) {
      // 已经是项目中的 PBL，直接选中
      const pbl = this.pblFiles.find(f => f.path === filePath);
      if (pbl) this.selectPblFile(pbl);
    } else if (this.exeFiles.includes(filePath)) {
      // EXE/DLL 文件
      this.selectBinaryFile(filePath);
    } else {
      // 不在当前项目中，尝试作为独立文件打开
      const name = this.getFileName(filePath);
      const ext = name.split('.').pop()?.toLowerCase() ?? '';
      if (ext === 'pbl') {
        this.projectPath = filePath;
        this.projectName = name;
        this.projectIcon = 'inventory_2';
        const fake: PblFileInfo = { path: filePath, name, size: 0, is_unicode: false };
        this.pblFiles = [fake];
        this.pblExpanded = true;
        this.selectPblFile(fake);
      }
    }
  }
}
