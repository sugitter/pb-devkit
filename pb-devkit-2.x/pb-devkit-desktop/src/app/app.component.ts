import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ProjectSelectorComponent } from './components/project-selector/project-selector.component';
import { PblListComponent } from './components/pbl-list/pbl-list.component';
import { SourceViewerComponent } from './components/source-viewer/source-viewer.component';
import { SearchPanelComponent } from './components/search-panel/search-panel.component';
import { DwAnalyzerComponent } from './components/dw-analyzer/dw-analyzer.component';
import { DecompilePanelComponent } from './components/decompile-panel/decompile-panel.component';
import { DoctorPanelComponent } from './components/doctor-panel/doctor-panel.component';
import { PblService, ProjectInfo } from './services/pbl.service';

type Tab = 'explorer' | 'search' | 'dw' | 'doctor';
type ContentMode = 'welcome' | 'source';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    ProjectSelectorComponent,
    PblListComponent,
    SourceViewerComponent,
    SearchPanelComponent,
    DwAnalyzerComponent,
    DecompilePanelComponent,
    DoctorPanelComponent,
  ],
  template: `
    <div class="app-layout">

      <!-- 侧边栏图标 -->
      <nav class="sidebar">
        <div class="sidebar-logo" title="PB DevKit 2.0">⚡</div>
        <button class="nav-btn" [class.active]="activeTab==='explorer'" (click)="activeTab='explorer'" title="资源管理器">📁</button>
        <button class="nav-btn" [class.active]="activeTab==='search'" (click)="activeTab='search'" title="全文搜索">🔍</button>
        <button class="nav-btn" [class.active]="activeTab==='dw'" (click)="activeTab='dw'" title="DataWindow">📊</button>
        <button class="nav-btn" [class.active]="activeTab==='doctor'" (click)="activeTab='doctor'" title="环境诊断">🔧</button>
        <div class="sidebar-spacer"></div>
        <button class="nav-btn" (click)="showAbout=!showAbout" title="关于">ℹ️</button>
      </nav>

      <!-- 左侧面板 -->
      <aside class="panel-left">
        @if (activeTab === 'explorer') {

          @if (!currentPblPath && !exePath && !projectPath) {
            <app-project-selector
              (pblSelected)="onPblSelected($event)"
              (exeSelected)="onExeSelected($event)"
              (projectDetected)="onProjectDetected($event)"
            />
          } @else {
            <div class="panel-actions">
              <button class="btn-back" (click)="clearSelection()">← 返回</button>
              @if (projectPath) {
                <span class="project-name" title="{{ projectPath }}">{{ projectName }}</span>
              }
            </div>

            @if (exePath) {
              <app-decompile-panel
                [filePath]="exePath"
                (entrySelected)="onEntrySelected($event)"
              />
            } @else {
              <app-pbl-list
                [pblPath]="currentPblPath"
                (entrySelected)="onEntrySelected($event)"
              />
            }
          }

        }

        @if (activeTab === 'search') {
          <app-search-panel [rootPath]="projectPath || currentPblPath || exePath" />
        }

        @if (activeTab === 'dw') {
          <app-dw-analyzer [rootPath]="projectPath || currentPblPath" />
        }

        @if (activeTab === 'doctor') {
          <app-doctor-panel />
        }
      </aside>

      <!-- 主内容区 -->
      <main class="content-area">
        @if (contentMode === 'source' && viewerSource) {
          <app-source-viewer
            [entryName]="viewerEntryName"
            [source]="viewerSource"
          />
        } @else {
          <div class="welcome-screen">
            <div class="welcome-icon">⚡</div>
            <h2>PB DevKit 2.0</h2>
            <p>PowerBuilder Legacy System Toolkit</p>
            <div class="feature-grid">
              <div class="feature-card" (click)="activeTab='explorer'">
                <span class="feat-icon">📦</span>
                <h4>PBL 解析</h4>
                <p>解析 PB5-PB12.6 全版本库文件</p>
              </div>
              <div class="feature-card" (click)="activeTab='explorer'">
                <span class="feat-icon">🔓</span>
                <h4>反编译</h4>
                <p>从 EXE/PBD 还原 PowerScript 源码</p>
              </div>
              <div class="feature-card" (click)="activeTab='search'">
                <span class="feat-icon">🔍</span>
                <h4>全文搜索</h4>
                <p>快速定位代码中的任意内容</p>
              </div>
              <div class="feature-card" (click)="activeTab='dw'">
                <span class="feat-icon">📊</span>
                <h4>DataWindow</h4>
                <p>分析 SQL、表结构、列引用关系</p>
              </div>
              <div class="feature-card" (click)="activeTab='doctor'">
                <span class="feat-icon">🔧</span>
                <h4>环境诊断</h4>
                <p>检查 Python/Rust/ORCA 依赖状态</p>
              </div>
            </div>
          </div>
        }
      </main>

      <!-- 关于浮层 -->
      @if (showAbout) {
        <div class="overlay" (click)="showAbout=false">
          <div class="about-card" (click)="$event.stopPropagation()">
            <h2>⚡ PB DevKit 2.0</h2>
            <p>PowerBuilder Legacy System Toolkit</p>
            <ul>
              <li>🦀 Rust 核心引擎（零依赖 PBL/PBD/PE 解析）</li>
              <li>🅰 Angular 20 前端（standalone + 控制流语法）</li>
              <li>🖥 Tauri 2.x 桌面框架</li>
              <li>📦 PBL/PBD/EXE 全格式支持</li>
              <li>🔍 全文搜索 + 📊 DataWindow 分析</li>
              <li>⌨️ CLI 命令行工具（pbdk 命令）</li>
            </ul>
            <p class="version">v2.0.0</p>
            <button (click)="showAbout=false">关闭</button>
          </div>
        </div>
      }

    </div>
  `,
  styles: [`
    .app-layout { display: flex; height: 100vh; overflow: hidden; background: #f3f4f6; }
    .sidebar { width: 48px; background: #1e1e2e; display: flex; flex-direction: column; align-items: center; padding: 0.5rem 0; gap: 0.25rem; flex-shrink: 0; }
    .sidebar-logo { font-size: 1.5rem; padding: 0.5rem; margin-bottom: 0.5rem; }
    .nav-btn { width: 36px; height: 36px; border: none; background: transparent; cursor: pointer; border-radius: 6px; font-size: 1.1rem; display: flex; align-items: center; justify-content: center; transition: background 0.15s; }
    .nav-btn:hover { background: #313244; }
    .nav-btn.active { background: #313244; box-shadow: 2px 0 0 0 #cba6f7 inset; }
    .sidebar-spacer { flex: 1; }
    .panel-left { width: 280px; background: #fff; border-right: 1px solid #e5e7eb; display: flex; flex-direction: column; overflow: hidden; flex-shrink: 0; }
    .panel-actions { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.75rem; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; }
    .btn-back { padding: 0.25rem 0.5rem; background: transparent; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; font-size: 0.8rem; color: #374151; }
    .btn-back:hover { background: #f9fafb; }
    .project-name { font-size: 0.8rem; color: #6b7280; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
    .content-area { flex: 1; overflow: hidden; }
    .welcome-screen { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #6b7280; }
    .welcome-icon { font-size: 4rem; margin-bottom: 1rem; }
    .welcome-screen h2 { margin: 0 0 0.5rem; color: #111; font-size: 1.5rem; }
    .welcome-screen > p { margin: 0 0 2rem; font-size: 0.9rem; }
    .feature-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; max-width: 500px; }
    .feature-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1.25rem; text-align: center; cursor: pointer; transition: border-color 0.15s, box-shadow 0.15s; }
    .feature-card:hover { border-color: #93c5fd; box-shadow: 0 2px 8px rgba(59,130,246,0.1); }
    .feat-icon { font-size: 1.75rem; display: block; margin-bottom: 0.5rem; }
    .feature-card h4 { margin: 0 0 0.25rem; color: #111; font-size: 0.9rem; }
    .feature-card p { margin: 0; font-size: 0.8rem; color: #9ca3af; }
    .overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
    .about-card { background: #fff; border-radius: 12px; padding: 2rem; max-width: 400px; width: 90%; }
    .about-card h2 { margin: 0 0 0.5rem; }
    .about-card ul { padding-left: 1.5rem; }
    .about-card li { margin-bottom: 0.4rem; font-size: 0.9rem; }
    .version { color: #9ca3af; font-size: 0.85rem; }
    .about-card button { padding: 0.5rem 1.5rem; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; margin-top: 0.5rem; }
  `]
})
export class AppComponent {
  activeTab: Tab = 'explorer';
  contentMode: ContentMode = 'welcome';

  currentPblPath = '';
  exePath = '';
  projectPath = '';
  projectName = '';

  viewerEntryName = '';
  viewerSource = '';

  showAbout = false;

  constructor(private pblService: PblService) {}

  onProjectDetected(info: ProjectInfo) {
    this.projectPath = info.path;
    this.projectName = info.name;
  }

  onPblSelected(path: string) {
    this.currentPblPath = path;
    this.exePath = '';
    this.contentMode = 'welcome';
    this.viewerSource = '';
  }

  onExeSelected(path: string) {
    this.exePath = path;
    this.currentPblPath = '';
    this.contentMode = 'welcome';
    this.viewerSource = '';
  }

  onEntrySelected(e: { path: string; name: string; source: string }) {
    this.viewerEntryName = e.name;
    this.viewerSource = e.source;
    this.contentMode = 'source';
  }

  clearSelection() {
    this.currentPblPath = '';
    this.exePath = '';
    this.projectPath = '';
    this.projectName = '';
    this.viewerSource = '';
    this.viewerEntryName = '';
    this.contentMode = 'welcome';
  }
}
