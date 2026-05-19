import { Component, EventEmitter, Output, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

/** 全局设置服务（单例） */
export class SettingsService {
  private static instance: SettingsService;
  private settings: any = {};
  private listeners: ((settings: any) => void)[] = [];

  private constructor() {
    this.load();
  }

  static getInstance(): SettingsService {
    if (!SettingsService.instance) {
      SettingsService.instance = new SettingsService();
    }
    return SettingsService.instance;
  }

  load() {
    const saved = localStorage.getItem('pbdevkit_settings');
    if (saved) {
      try {
        this.settings = JSON.parse(saved);
      } catch { this.settings = {}; }
    }
    // 默认值
    this.settings = {
      autoParse: true,
      showCompiled: true,
      showSource: true,
      searchThreads: 4,
      caseSensitive: false,
      useCache: true,
      exportFormat: 'txt',
      exportByType: false,
      encoding: 'utf-8',
      pageSize: 100,
      darkMode: false,
      ...this.settings
    };
    this.notify();
  }

  get(): any { return { ...this.settings }; }

  set(settings: any) {
    this.settings = { ...this.settings, ...settings };
    localStorage.setItem('pbdevkit_settings', JSON.stringify(this.settings));
    this.notify();
  }

  subscribe(listener: (settings: any) => void): () => void {
    listener(this.settings);
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  get darkMode(): boolean { return this.settings.darkMode ?? false; }
  get pageSize(): number { return this.settings.pageSize ?? 100; }
  get caseSensitive(): boolean { return this.settings.caseSensitive ?? false; }

  private notify() {
    this.listeners.forEach(l => l(this.settings));
  }
}

@Component({
  selector: 'app-settings-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="settings-panel">
      <div class="settings-header">
        <h2><span class="material-icons" style="vertical-align:middle">settings</span> 设置</h2>
      </div>

      <div class="settings-content">
        <!-- 解析设置 -->
        <div class="settings-section">
          <h3>解析设置</h3>
          <label class="setting-item">
            <input type="checkbox" [(ngModel)]="settings.autoParse" />
            <span>选择 PBL 后自动解析</span>
          </label>
          <label class="setting-item">
            <input type="checkbox" [(ngModel)]="settings.showCompiled" />
            <span>显示编译对象</span>
          </label>
          <label class="setting-item">
            <input type="checkbox" [(ngModel)]="settings.showSource" />
            <span>显示源码对象</span>
          </label>
        </div>

        <!-- 搜索设置 -->
        <div class="settings-section">
          <h3>搜索设置</h3>
          <label class="setting-item">
            <span>搜索线程数</span>
            <select [(ngModel)]="settings.searchThreads" class="setting-select">
              <option [value]="1">1</option>
              <option [value]="2">2</option>
              <option [value]="4">4</option>
              <option [value]="8">8</option>
            </select>
          </label>
          <label class="setting-item">
            <input type="checkbox" [(ngModel)]="settings.caseSensitive" />
            <span>默认区分大小写</span>
          </label>
          <label class="setting-item">
            <input type="checkbox" [(ngModel)]="settings.useCache" />
            <span>启用搜索缓存</span>
          </label>
        </div>

        <!-- 导出设置 -->
        <div class="settings-section">
          <h3>导出设置</h3>
          <label class="setting-item">
            <span>默认导出格式</span>
            <select [(ngModel)]="settings.exportFormat" class="setting-select">
              <option value="txt">文本 (.txt)</option>
              <option value="srx">PowerScript (.srx)</option>
              <option value="json">JSON (.json)</option>
            </select>
          </label>
          <label class="setting-item">
            <input type="checkbox" [(ngModel)]="settings.exportByType" />
            <span>按对象类型分目录导出</span>
          </label>
          <label class="setting-item">
            <span>编码</span>
            <select [(ngModel)]="settings.encoding" class="setting-select">
              <option value="utf-8">UTF-8</option>
              <option value="gbk">GBK</option>
              <option value="ansi">ANSI</option>
            </select>
          </label>
        </div>

        <!-- 显示设置 -->
        <div class="settings-section">
          <h3>显示设置</h3>
          <label class="setting-item">
            <span>每页显示条数</span>
            <select [(ngModel)]="settings.pageSize" class="setting-select">
              <option [value]="50">50</option>
              <option [value]="100">100</option>
              <option [value]="200">200</option>
              <option [value]="500">500</option>
            </select>
          </label>
          <label class="setting-item">
            <input type="checkbox" [(ngModel)]="settings.darkMode" />
            <span>深色模式</span>
          </label>
        </div>
      </div>

      <div class="settings-footer">
        <button class="btn-reset" (click)="resetSettings()">重置默认</button>
        <button class="btn-save" (click)="saveSettings()">保存设置</button>
      </div>
    </div>
  `,
  styles: [`
    .settings-panel { display: flex; flex-direction: column; height: 100%; background: #fff; }
    .settings-header { padding: 1rem; border-bottom: 1px solid #e5e7eb; }
    .settings-header h2 { margin: 0; font-size: 1rem; color: #111; display: flex; align-items: center; gap: 0.5rem; }
    .settings-content { flex: 1; overflow-y: auto; padding: 1rem; }
    .settings-section { margin-bottom: 1.5rem; }
    .settings-section h3 { margin: 0 0 0.75rem; font-size: 0.85rem; color: #374151; font-weight: 600; }
    .setting-item { display: flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0; font-size: 0.85rem; color: #374151; cursor: pointer; }
    .setting-item input[type="checkbox"] { width: 16px; height: 16px; accent-color: #2563eb; }
    .setting-select { margin-left: auto; padding: 0.25rem 0.5rem; border: 1px solid #d1d5db; border-radius: 4px; font-size: 0.8rem; background: #fff; }
    .settings-footer { display: flex; gap: 0.5rem; padding: 1rem; border-top: 1px solid #e5e7eb; }
    .btn-reset, .btn-save { flex: 1; padding: 0.5rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem; }
    .btn-reset { background: #f3f4f6; color: #374151; }
    .btn-reset:hover { background: #e5e7eb; }
    .btn-save { background: #2563eb; color: white; }
    .btn-save:hover { background: #1d4ed8; }
  `]
})
export class SettingsPanelComponent implements OnInit {
  @Output() settingsChanged = new EventEmitter<any>();
  private settingsService = SettingsService.getInstance();
  settings: any = this.settingsService.get();

  resetSettings() {
    this.settings = {
      autoParse: true,
      showCompiled: true,
      showSource: true,
      searchThreads: 4,
      caseSensitive: false,
      useCache: true,
      exportFormat: 'txt',
      exportByType: false,
      encoding: 'utf-8',
      pageSize: 100,
      darkMode: false
    };
    this.saveSettings();
  }

  saveSettings() {
    this.settingsService.set(this.settings);
    this.settingsChanged.emit(this.settings);
  }

  ngOnInit() {
    this.settings = this.settingsService.get();
  }
}