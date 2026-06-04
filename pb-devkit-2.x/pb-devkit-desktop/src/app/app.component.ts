import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { open } from '@tauri-apps/plugin-dialog';
import { invoke } from '@tauri-apps/api/core';
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
import { RefactorPanelComponent } from './components/refactor-panel/refactor-panel.component';
import { SnapshotPanelComponent } from './components/snapshot-panel/snapshot-panel.component';
import { ReviewPanelComponent } from './components/review-panel/review-panel.component';
import { AutoexportPanelComponent } from './components/autoexport-panel/autoexport-panel.component';
import { MigratePanelComponent } from './components/migrate-panel/migrate-panel.component';
import { BuildPanelComponent } from './components/build-panel/build-panel.component';
import { PblService, ProjectInfo, PblFileInfo } from './services/pbl.service';

type Tab = 'explorer' | 'search' | 'dw' | 'doctor' | 'pe' | 'report' | 'stats' | 'diff' | 'workflow' | 'refactor' | 'snapshot' | 'review' | 'autoexport' | 'migrate' | 'build' | 'settings';
type ContentMode = 'welcome' | 'source' | 'loading';
type SearchMode = 'text' | 'regex';
type ProjectMode = 'pbl' | 'exe_pbd' | 'exe_dll' | 'mixed' | 'none';

/** 一键操作状态 */
interface QuickAction {
  running: boolean;
  done: boolean;
  error: string;
  message: string;
}

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
    RefactorPanelComponent,
    SnapshotPanelComponent,
    ReviewPanelComponent,
    AutoexportPanelComponent,
    MigratePanelComponent,
    BuildPanelComponent,
  ],
  template: `
    <div class="app-layout">

      <!-- 侧边栏图标 -->
      <nav class="sidebar">
        <div class="sidebar-logo" title="PB DevKit 2.2"><span class="material-icons mi-lg">bolt</span></div>
        <button class="nav-btn" [class.active]="activeTab==='explorer'" (click)="activeTab='explorer'" title="资源管理器"><span class="material-icons">folder</span></button>
        <button class="nav-btn" [class.active]="activeTab==='search'" (click)="activeTab='search'" title="全文搜索"><span class="material-icons">search</span></button>
        <button class="nav-btn" [class.active]="activeTab==='dw'" (click)="activeTab='dw'" title="DataWindow"><span class="material-icons">bar_chart</span></button>
        <button class="nav-btn" [class.active]="activeTab==='doctor'" (click)="activeTab='doctor'" title="环境诊断"><span class="material-icons">build</span></button>
        <button class="nav-btn" [class.active]="activeTab==='pe'" (click)="activeTab='pe'" title="PE 分析"><span class="material-icons">description</span></button>
        <button class="nav-btn" [class.active]="activeTab==='report'" (click)="activeTab='report'" title="项目报告"><span class="material-icons">assessment</span></button>
        <button class="nav-btn" [class.active]="activeTab==='stats'" (click)="activeTab='stats'" title="项目统计"><span class="material-icons">analytics</span></button>
        <button class="nav-btn" [class.active]="activeTab==='diff'" (click)="activeTab='diff'" title="代码对比"><span class="material-icons">compare</span></button>
        <button class="nav-btn" [class.active]="activeTab==='workflow'" (click)="activeTab='workflow'" title="工作流"><span class="material-icons">account_tree</span></button>
        <button class="nav-btn" [class.active]="activeTab==='refactor'" (click)="activeTab='refactor'" title="重构分析"><span class="material-icons">auto_fix_high</span></button>
        <button class="nav-btn" [class.active]="activeTab==='snapshot'" (click)="activeTab='snapshot'" title="快照管理"><span class="material-icons">camera</span></button>
        <button class="nav-btn" [class.active]="activeTab==='review'" (click)="activeTab='review'" title="项目评审"><span class="material-icons">fact_check</span></button>
        <button class="nav-btn" [class.active]="activeTab==='autoexport'" (click)="activeTab='autoexport'" title="一键导出"><span class="material-icons">download</span></button>
        <button class="nav-btn" [class.active]="activeTab==='migrate'" (click)="activeTab='migrate'" title="迁移向导 (PB→Web)"><span class="material-icons">transform</span></button>
        <button class="nav-btn" [class.active]="activeTab==='build'" (click)="activeTab='build'" title="构建/编译 (PBGen)"><span class="material-icons">construction</span></button>
        <button class="nav-btn" [class.active]="activeTab==='settings'" (click)="activeTab='settings'" title="设置"><span class="material-icons">settings</span></button>
        <div class="sidebar-spacer"></div>
        <button class="nav-btn" (click)="showAbout=!showAbout" title="关于"><span class="material-icons">info</span></button>
      </nav>

      <!-- ============================================================
           Explorer Tab: 三栏布局（全暗色主题）
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
                    <span class="material-icons ft-section-icon" style="color:#cba6f7">inventory_2</span>
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
                    <span class="material-icons ft-section-icon" style="color:#f9a825">settings</span>
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

              <!-- ── 一键操作区 ── -->
              <div class="quick-actions-section">
                <div class="qa-section-title">
                  <span class="material-icons" style="font-size:12px;color:#6c7086">bolt</span>
                  <span>一键操作</span>
                </div>

                <!-- 一键导出源码 -->
                <button class="qa-btn"
                  [class.qa-running]="qaExport.running"
                  [class.qa-done]="qaExport.done"
                  [class.qa-error]="!!qaExport.error"
                  [disabled]="qaExport.running || !projectPath"
                  (click)="doQuickExport()"
                  title="将所有 PBL 源码导出为文本文件到指定目录">
                  <span class="material-icons qa-icon">
                    {{ qaExport.running ? 'hourglass_top' : qaExport.done ? 'check_circle' : 'download' }}
                  </span>
                  <div class="qa-text">
                    <span class="qa-label">导出源码</span>
                    <span class="qa-hint">{{ qaExport.message || 'Export → src/' }}</span>
                  </div>
                </button>

                <!-- 一键转Web项目 -->
                <button class="qa-btn"
                  [class.qa-running]="qaMigrate.running"
                  [class.qa-done]="qaMigrate.done"
                  [class.qa-error]="!!qaMigrate.error"
                  [disabled]="qaMigrate.running || !projectPath || pblFiles.length === 0"
                  (click)="doQuickMigrate()"
                  title="将 PB 项目一键转化为 Angular Web 脚手架">
                  <span class="material-icons qa-icon">
                    {{ qaMigrate.running ? 'hourglass_top' : qaMigrate.done ? 'check_circle' : 'transform' }}
                  </span>
                  <div class="qa-text">
                    <span class="qa-label">转 Web 项目</span>
                    <span class="qa-hint">{{ qaMigrate.message || 'Migrate → Angular' }}</span>
                  </div>
                </button>

                <!-- 一键重打包 PBL -->
                <button class="qa-btn"
                  [class.qa-running]="qaPack.running"
                  [class.qa-done]="qaPack.done"
                  [class.qa-error]="!!qaPack.error"
                  [disabled]="qaPack.running || !projectPath || pblFiles.length === 0"
                  (click)="doQuickPack()"
                  title="将导出的源码目录重新打包为 PBL 文件">
                  <span class="material-icons qa-icon">
                    {{ qaPack.running ? 'hourglass_top' : qaPack.done ? 'check_circle' : 'inventory_2' }}
                  </span>
                  <div class="qa-text">
                    <span class="qa-label">重打包 PBL</span>
                    <span class="qa-hint">{{ qaPack.message || 'Pack src/ → .pbl' }}</span>
                  </div>
                </button>

                <!-- 操作结果消息 -->
                @if (qaResultMsg) {
                  <div class="qa-result-msg" [class.qa-result-error]="qaResultIsError">
                    <span class="material-icons" style="font-size:13px">
                      {{ qaResultIsError ? 'error_outline' : 'check_circle_outline' }}
                    </span>
                    {{ qaResultMsg }}
                  </div>
                }
              </div>
            }
          </aside>

          <!-- 中栏：对象列表（暗色主题） -->
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
                <h2>PB DevKit 2.2</h2>
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
          @if (activeTab === 'refactor') {
            <app-refactor-panel />
          }
          @if (activeTab === 'snapshot') {
            <app-snapshot-panel />
          }
          @if (activeTab === 'review') {
            <app-review-panel />
          }
          @if (activeTab === 'autoexport') {
            <app-autoexport-panel
              [projectPath]="projectPath"
              (onClose)="activeTab='explorer'" />
          }
          @if (activeTab === 'migrate') {
            <app-migrate-panel
              [projectPath]="projectPath"
              (onClose)="activeTab='explorer'" />
          }
          @if (activeTab === 'build') {
            <app-build-panel
              [projectPath]="selectedFilePath"
              (onClose)="activeTab='explorer'"
              (onGotoMigrate)="activeTab='migrate'" />
          }
        </div>
      }

      <!-- 关于浮层 -->
      @if (showAbout) {
        <div class="overlay" (click)="showAbout=false">
          <div class="about-card" (click)="$event.stopPropagation()">
            <h2><span class="material-icons mi-lg">bolt</span> PB DevKit 2.2</h2>
            <p>PowerBuilder Legacy System Toolkit</p>
            <ul>
              <li><span class="material-icons" style="color:#dea584;font-size:16px;vertical-align:middle">terminal</span> Rust 核心引擎（零依赖 PBL/PBD/PE 解析）</li>
              <li><span class="material-icons" style="color:#dd0031;font-size:16px;vertical-align:middle">code</span> Angular 前端（standalone + 控制流语法）</li>
              <li><span class="material-icons" style="color:#24c8d8;font-size:16px;vertical-align:middle">computer</span> Tauri 2.x 桌面框架</li>
              <li><span class="material-icons" style="font-size:16px;vertical-align:middle">inventory_2</span> PBL/PBD/EXE 全格式支持</li>
              <li><span class="material-icons" style="font-size:16px;vertical-align:middle">search</span> 全文搜索 + <span class="material-icons" style="font-size:16px;vertical-align:middle">bar_chart</span> DataWindow 分析</li>
              <li><span class="material-icons" style="font-size:16px;vertical-align:middle">keyboard</span> CLI 命令行工具（pbdevkit 命令）</li>
              <li><span class="material-icons" style="color:#4ade80;font-size:16px;vertical-align:middle">bolt</span> 一键导出 / 转Web / 重打包</li>
            </ul>
            <p class="version">v2.2.1</p>
            <button (click)="showAbout=false">关闭</button>
          </div>
        </div>
      }

    </div>
  `,
  styles: [`
    /* ── 整体布局 ── */
    .app-layout { display: flex; height: 100vh; overflow: hidden; background: #181825; }

    /* ── 侧边栏 ── */
    .sidebar { width: 48px; background: #11111b; display: flex; flex-direction: column; align-items: center; padding: 0.5rem 0; gap: 0.25rem; flex-shrink: 0; border-right: 1px solid #313244; }
    .sidebar-logo { padding: 0.4rem; margin-bottom: 0.25rem; color: #cba6f7; }
    .sidebar-logo .material-icons { font-size: 22px; color: #cba6f7; }
    .nav-btn { width: 40px; height: 40px; border: none; background: transparent; cursor: pointer; border-radius: 6px; display: flex; align-items: center; justify-content: center; transition: background 0.15s; color: #585b70; }
    .nav-btn .material-icons { font-size: 20px; }
    .nav-btn:hover { background: #1e1e2e; color: #cdd6f4; }
    .nav-btn.active { background: #1e1e2e; color: #cba6f7; box-shadow: 2px 0 0 0 #cba6f7 inset; }
    .sidebar-spacer { flex: 1; }

    /* ── Explorer 三栏布局 ── */
    .explorer-layout { display: flex; flex: 1; overflow: hidden; min-width: 0; }

    /* ── 左栏：文件树（暗色） ── */
    .file-tree-panel {
      width: 230px;
      min-width: 190px;
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
    .ft-title { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #6c7086; }
    .ft-actions { display: flex; gap: 2px; }
    .ft-btn { width: 24px; height: 24px; border: none; background: transparent; cursor: pointer; border-radius: 4px; color: #6c7086; display: flex; align-items: center; justify-content: center; }
    .ft-btn .material-icons { font-size: 16px; }
    .ft-btn:hover { background: #313244; color: #cdd6f4; }
    .ft-loading { display: flex; align-items: center; gap: 0.5rem; padding: 1rem; font-size: 0.8rem; color: #a6adc8; }
    .spinner { width: 14px; height: 14px; border: 2px solid #313244; border-top-color: #cba6f7; border-radius: 50%; animation: spin 0.8s linear infinite; flex-shrink: 0; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .ft-empty {
      flex: 1; display: flex; flex-direction: column; align-items: center;
      justify-content: center; padding: 1rem; gap: 0.4rem; text-align: center;
    }
    .ft-empty-icon { font-size: 36px; color: #313244; }
    .ft-empty p { margin: 0; font-size: 0.8rem; color: #6c7086; }
    .ft-hint { font-size: 0.7rem !important; color: #45475a !important; margin-top: -0.2rem !important; }
    .ft-open-btn {
      margin-top: 0.5rem; padding: 0.4rem 0.9rem; background: #7c3aed;
      color: white; border: none; border-radius: 6px; cursor: pointer;
      font-size: 0.78rem; display: flex; align-items: center; gap: 0.3rem;
      width: 100%; justify-content: center;
    }
    .ft-open-btn:hover { background: #6d28d9; }
    .ft-open-btn-sec { background: #313244; color: #a6adc8; }
    .ft-open-btn-sec:hover { background: #45475a; }
    .ft-divider { font-size: 0.7rem; color: #45475a; margin: 0.1rem 0; }

    .ft-project-root {
      display: flex; align-items: center; gap: 0.4rem;
      padding: 0.45rem 0.6rem; border-bottom: 1px solid #313244;
      flex-shrink: 0; background: #181825;
    }
    .ft-root-icon { font-size: 16px; color: #cba6f7; flex-shrink: 0; }
    .ft-root-name { font-size: 0.8rem; font-weight: 600; color: #cdd6f4; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    .ft-section { flex-shrink: 0; }
    .ft-section-header {
      display: flex; align-items: center; gap: 0.3rem;
      padding: 0.35rem 0.6rem; cursor: pointer; user-select: none;
    }
    .ft-section-header:hover { background: #2a2a3e; }
    .ft-chevron { font-size: 14px; color: #45475a; }
    .ft-section-icon { font-size: 14px; }
    .ft-section-label { font-size: 0.7rem; font-weight: 700; color: #6c7086; flex: 1; text-transform: uppercase; letter-spacing: 0.06em; }
    .ft-count { font-size: 0.68rem; color: #6c7086; background: #313244; padding: 0.1rem 0.35rem; border-radius: 8px; }

    .ft-file-item {
      display: flex; align-items: center; gap: 0.35rem;
      padding: 0.3rem 0.6rem 0.3rem 1.4rem;
      cursor: pointer; font-size: 0.8rem; color: #a6adc8;
    }
    .ft-file-item:hover { background: #2a2a3e; }
    .ft-file-item.active { background: #313244; color: #cba6f7; }
    .ft-file-item.active .ft-file-icon { color: #cba6f7; }
    .ft-file-icon { font-size: 14px; color: #45475a; flex-shrink: 0; }
    .ft-file-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .ft-file-size { font-size: 0.68rem; color: #45475a; flex-shrink: 0; }
    .ft-no-files { display: flex; align-items: center; gap: 0.4rem; padding: 0.75rem 0.6rem; font-size: 0.78rem; color: #6c7086; }

    /* ── 一键操作区 ── */
    .quick-actions-section {
      border-top: 1px solid #313244;
      padding: 0.5rem 0.5rem 0.6rem;
      flex-shrink: 0;
    }
    .qa-section-title {
      display: flex; align-items: center; gap: 0.3rem;
      font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
      letter-spacing: 0.08em; color: #45475a; padding: 0 0.1rem 0.35rem;
    }
    .qa-btn {
      display: flex; align-items: center; gap: 0.5rem;
      width: 100%; padding: 0.42rem 0.55rem; margin-bottom: 0.3rem;
      background: #2a2a3e; border: 1px solid #313244; border-radius: 7px;
      cursor: pointer; color: #a6adc8; transition: all 0.15s; text-align: left;
    }
    .qa-btn:hover:not(:disabled) { background: #313244; border-color: #585b70; color: #cdd6f4; }
    .qa-btn:disabled { opacity: 0.4; cursor: not-allowed; }
    .qa-btn.qa-running { border-color: #cba6f7; color: #cba6f7; background: #1e1e2e; }
    .qa-btn.qa-done { border-color: #a6e3a1; color: #a6e3a1; background: #1a2e22; }
    .qa-btn.qa-error { border-color: #f38ba8; color: #f38ba8; background: #2e1a1e; }
    .qa-icon { font-size: 16px; flex-shrink: 0; }
    .qa-text { display: flex; flex-direction: column; }
    .qa-label { font-size: 0.78rem; font-weight: 600; line-height: 1.2; }
    .qa-hint { font-size: 0.68rem; color: #45475a; line-height: 1.2; }
    .qa-btn.qa-running .qa-hint,
    .qa-btn.qa-done .qa-hint,
    .qa-btn.qa-error .qa-hint { color: inherit; opacity: 0.75; }
    .qa-result-msg {
      display: flex; align-items: center; gap: 0.3rem;
      font-size: 0.72rem; color: #a6e3a1; padding: 0.3rem 0.1rem 0;
      line-height: 1.3;
    }
    .qa-result-msg.qa-result-error { color: #f38ba8; }

    /* ── 中栏：对象列表（暗色主题，与左右栏一致） ── */
    .object-panel {
      width: 280px; min-width: 220px; flex-shrink: 0;
      background: #1e1e2e;
      border-right: 1px solid #313244;
      display: flex; flex-direction: column; overflow: hidden;
    }
    .obj-empty {
      flex: 1; display: flex; flex-direction: column; align-items: center;
      justify-content: center; color: #45475a; padding: 1.5rem; text-align: center;
    }
    .obj-empty-icon { font-size: 36px; color: #313244; margin-bottom: 0.5rem; }
    .obj-empty p { margin: 0; font-size: 0.82rem; }

    /* ── 右栏：源码 ── */
    .source-panel { flex: 1; overflow: hidden; min-width: 0; background: #181825; }
    .welcome-screen {
      height: 100%; display: flex; flex-direction: column; align-items: center;
      justify-content: center; color: #45475a; padding: 2rem; background: #181825; text-align: center;
    }
    .welcome-icon { margin-bottom: 1rem; color: #313244; }
    .welcome-icon .material-icons { font-size: 48px; }
    .welcome-screen h2 { margin: 0 0 0.5rem; color: #585b70; font-size: 1.4rem; }
    .welcome-sub { margin: 0 0 0.5rem; font-size: 0.85rem; color: #313244; }
    .welcome-hint { margin: 0; font-size: 0.8rem; color: #313244; }

    /* ── 其他 Tab 全宽布局（暗色） ── */
    .other-tab-layout { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; background: #1e1e2e; }
    .other-tab-layout > * { flex: 1; overflow: hidden; }

    /* ── Search Tab 专属（暗色） ── */
    .search-tab-wrapper { display: flex; flex-direction: column; flex: 1; overflow: hidden; background: #1e1e2e; }
    .search-mode-bar {
      display: flex; gap: 0; border-bottom: 1px solid #313244;
      background: #181825; flex-shrink: 0;
    }
    .search-mode-btn {
      flex: 1; padding: 0.45rem 1rem; border: none; background: transparent;
      cursor: pointer; font-size: 0.8rem; color: #6c7086;
      display: flex; align-items: center; justify-content: center; gap: 0.3rem;
      border-bottom: 2px solid transparent; transition: all 0.15s;
    }
    .search-mode-btn:hover { background: #1e1e2e; color: #a6adc8; }
    .search-mode-btn.active { color: #cba6f7; border-bottom-color: #cba6f7; background: #1e1e2e; font-weight: 600; }
    .search-tab-wrapper > app-search-panel,
    .search-tab-wrapper > app-search-regex-panel { flex: 1; display: block; overflow: hidden; }

    /* ── 关于浮层（暗色卡片） ── */
    .overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 100; }
    .about-card {
      background: #1e1e2e; border: 1px solid #313244; border-radius: 12px;
      padding: 2rem; max-width: 400px; width: 90%; color: #cdd6f4;
    }
    .about-card h2 { margin: 0 0 0.5rem; display: flex; align-items: center; gap: 0.4rem; color: #cdd6f4; }
    .about-card h2 .material-icons { color: #cba6f7; }
    .about-card p { color: #a6adc8; font-size: 0.9rem; }
    .about-card ul { list-style: none; padding-left: 0; }
    .about-card li { margin-bottom: 0.5rem; font-size: 0.88rem; display: flex; align-items: center; gap: 0.4rem; color: #a6adc8; }
    .about-card li .material-icons { flex-shrink: 0; }
    .version { color: #585b70 !important; font-size: 0.85rem; }
    .about-card button {
      padding: 0.5rem 1.5rem; background: #7c3aed; color: white;
      border: none; border-radius: 6px; cursor: pointer; margin-top: 0.5rem;
    }
    .about-card button:hover { background: #6d28d9; }

    /* ── 通用 Material Icons 尺寸 ── */
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

  // 当前选中文件
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

  // ── 一键操作状态 ──
  qaExport: QuickAction  = { running: false, done: false, error: '', message: '' };
  qaMigrate: QuickAction = { running: false, done: false, error: '', message: '' };
  qaPack: QuickAction    = { running: false, done: false, error: '', message: '' };
  qaResultMsg = '';
  qaResultIsError = false;

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

      if (this.pblFiles.length > 0 && this.exeFiles.length === 0) {
        this.projectIcon = 'inventory_2';
      } else if (this.pblFiles.length === 0 && this.exeFiles.length > 0) {
        this.projectIcon = 'settings';
      } else {
        this.projectIcon = 'folder';
      }

      this.pblExpanded = this.pblFiles.length > 0;
      this.exeExpanded = this.exeFiles.length > 0 && this.pblFiles.length === 0;

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
    this._resetQa();
  }

  private _resetQa() {
    this.qaExport  = { running: false, done: false, error: '', message: '' };
    this.qaMigrate = { running: false, done: false, error: '', message: '' };
    this.qaPack    = { running: false, done: false, error: '', message: '' };
    this.qaResultMsg = '';
    this.qaResultIsError = false;
  }

  private _setQaResult(msg: string, isError = false) {
    this.qaResultMsg = msg;
    this.qaResultIsError = isError;
    if (!isError) setTimeout(() => { if (this.qaResultMsg === msg) this.qaResultMsg = ''; }, 5000);
  }

  // ──── 一键导出源码 ────
  async doQuickExport() {
    if (!this.projectPath) return;
    try {
      const outputDir = await open({ directory: true, multiple: false, title: '选择源码导出目录' });
      if (!outputDir) return;

      this.qaExport = { running: true, done: false, error: '', message: '正在导出...' };
      const result: any = await invoke('scan_project', {
        projectPath: this.projectPath,
        outputDir: outputDir as string,
      });
      const count = result?.exported_count ?? result?.entry_count ?? '?';
      this.qaExport = { running: false, done: true, error: '', message: `已导出 ${count} 个对象` };
      this._setQaResult(`✓ 源码已导出至 ${outputDir}`);
    } catch (e: any) {
      const msg = String(e?.message ?? e);
      this.qaExport = { running: false, done: false, error: msg, message: '导出失败' };
      this._setQaResult(`导出失败: ${msg}`, true);
    }
  }

  // ──── 一键转 Web 项目 ────
  async doQuickMigrate() {
    if (!this.projectPath || this.pblFiles.length === 0) return;
    try {
      const outputDir = await open({ directory: true, multiple: false, title: '选择 Web 项目输出目录' });
      if (!outputDir) return;

      this.qaMigrate = { running: true, done: false, error: '', message: '正在转化...' };
      const result: any = await invoke('migrate_project', {
        projectPath: this.projectPath,
        outputDir: outputDir as string,
        template: 'angular',
      });
      const count = result?.components ?? result?.generated_files ?? '?';
      this.qaMigrate = { running: false, done: true, error: '', message: `已生成 ${count} 个组件` };
      this._setQaResult(`✓ Web 项目已生成至 ${outputDir}`);
    } catch (e: any) {
      const msg = String(e?.message ?? e);
      this.qaMigrate = { running: false, done: false, error: msg, message: '转化失败' };
      this._setQaResult(`转化失败: ${msg}`, true);
    }
  }

  // ──── 一键重打包 PBL ────
  async doQuickPack() {
    if (!this.projectPath || this.pblFiles.length === 0) return;
    try {
      const srcDir = await open({ directory: true, multiple: false, title: '选择源码目录（将打包为 PBL）' });
      if (!srcDir) return;
      const outputDir = await open({ directory: true, multiple: false, title: '选择 PBL 输出目录' });
      if (!outputDir) return;

      this.qaPack = { running: true, done: false, error: '', message: '正在打包...' };
      // 调用 Tauri pack_to_pbl 命令
      const result: any = await invoke('pack_to_pbl', {
        srcDir: srcDir as string,
        outputDir: outputDir as string,
      });
      this.qaPack = { running: false, done: true, error: '', message: '打包完成' };
      const engine = result.engine ?? 'unknown';
      const count = result.packed_count ?? 0;
      const engineLabel = engine === 'python' ? '🐍 Python 1.x 引擎' : '📋 Manifest 模式';
      this._setQaResult(`✓ PBL 已重打包 (${engineLabel}, ${count} 对象) → ${outputDir}`);
    } catch (e: any) {
      const msg = String(e?.message ?? e);
      this.qaPack = { running: false, done: false, error: msg, message: '打包失败' };
      this._setQaResult(`打包失败: ${msg}`, true);
    }
  }

  // ──── 工具方法 ────

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

  async doExtractPbd() {
    if (!this.selectedFilePath) return;
    try {
      const selected = await open({ directory: true, multiple: false, title: '选择 PBD 提取输出目录' });
      if (!selected) return;
      console.log('Extracting PBD from:', this.selectedFilePath, 'to', selected);
    } catch (e: any) {
      console.error('Extract PBD error:', e);
    }
  }

  async doExportReport() {
    if (!this.projectPath) return;
    try {
      const selected = await open({ directory: true, multiple: false, title: '选择报告输出目录' });
      if (!selected) return;
      await this.pblService.exportReport(this.projectPath, selected as string);
    } catch (e: any) {
      console.error('Export report error:', e);
    }
  }

  onSearchFileSelected(filePath: string) {
    this.activeTab = 'explorer';
    if (this.pblFiles.some(f => f.path === filePath)) {
      const pbl = this.pblFiles.find(f => f.path === filePath);
      if (pbl) this.selectPblFile(pbl);
    } else if (this.exeFiles.includes(filePath)) {
      this.selectBinaryFile(filePath);
    } else {
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
