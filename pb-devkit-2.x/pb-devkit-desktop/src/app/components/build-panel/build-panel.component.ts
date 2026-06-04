import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { invoke } from '@tauri-apps/api/core';
import { open } from '@tauri-apps/plugin-dialog';

interface PbgenStatus {
  found: boolean;
  path: string;
  version: string;
}

interface BuildResult {
  success: boolean;
  exe_path: string;
  exe_size_kb: number;
  mode: string;
  log: string;
  errors: string[];
}

type Stage = 'idle' | 'building' | 'done' | 'error';

@Component({
  selector: 'app-build-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="build-panel">
      <div class="panel-header">
        <div class="header-left">
          <span class="material-icons header-icon">construction</span>
          <div>
            <h3>构建面板 / Build Panel</h3>
            <p class="header-sub">PowerBuilder PBGen.exe 编译工具</p>
          </div>
        </div>
        @if (stage !== 'building') {
          <button class="btn-close" (click)="onClose.emit()" title="关闭">
            <span class="material-icons">close</span>
          </button>
        }
      </div>

      <!-- PBGen 状态栏 -->
      <div class="pbgen-status" [class.found]="pbgen.found" [class.missing]="!pbgen.found && pbgenChecked">
        @if (!pbgenChecked) {
          <span class="spinner-sm"></span>
          <span>正在检测 PBGen.exe ...</span>
        } @else if (pbgen.found) {
          <span class="material-icons" style="color:#a6e3a1;font-size:18px">check_circle</span>
          <div class="pbgen-info">
            <span class="pbgen-ok">PBGen.exe 已检测到</span>
            <span class="pbgen-path">{{ pbgen.path }}</span>
          </div>
        } @else {
          <span class="material-icons" style="color:#f38ba8;font-size:18px">error</span>
          <div class="pbgen-info">
            <span class="pbgen-missing">PBGen.exe 未找到</span>
            <span class="pbgen-path">需要安装 PowerBuilder IDE，或手动指定路径</span>
          </div>
          <button class="btn-browse-sm" (click)="selectPbgen()">指定路径</button>
        }
      </div>

      <!-- 配置区 -->
      @if (stage === 'idle') {
        <div class="config-area">
          <!-- 应用 PBL -->
          <div class="config-group">
            <div class="group-title">
              <span class="material-icons">inventory_2</span>
              PBL 文件
            </div>
            <div class="field-row">
              <label>应用 PBL 文件</label>
              <div class="input-group">
                <input type="text" [(ngModel)]="pblPath" placeholder="选择主 PBL 文件..." class="path-input" />
                <button class="btn-browse" (click)="selectPbl()">
                  <span class="material-icons">folder_open</span>
                </button>
              </div>
            </div>
            <div class="field-row">
              <label>应用对象名称 (App Object)</label>
              <input type="text" [(ngModel)]="appName" placeholder="如 myapp" class="text-input" />
            </div>
          </div>

          <!-- 编译选项 -->
          <div class="config-group">
            <div class="group-title">
              <span class="material-icons">tune</span>
              编译选项
            </div>
            <div class="field-row">
              <label>编译模式</label>
              <div class="mode-select">
                <label class="mode-option" [class.active]="buildMode === 'exe'" (click)="buildMode = 'exe'">
                  <div class="mode-radio" [class.checked]="buildMode === 'exe'"></div>
                  <div>
                    <div class="mode-label">单 EXE</div>
                    <div class="mode-desc">所有代码内嵌，无外部 PBD</div>
                  </div>
                </label>
                <label class="mode-option" [class.active]="buildMode === 'exe+pbd'" (click)="buildMode = 'exe+pbd'">
                  <div class="mode-radio" [class.checked]="buildMode === 'exe+pbd'"></div>
                  <div>
                    <div class="mode-label">EXE + PBD</div>
                    <div class="mode-desc">主 EXE + 外挂 PBD 模块</div>
                  </div>
                </label>
                <label class="mode-option" [class.active]="buildMode === 'exe+dll'" (click)="buildMode = 'exe+dll'">
                  <div class="mode-radio" [class.checked]="buildMode === 'exe+dll'"></div>
                  <div>
                    <div class="mode-label">EXE + DLL</div>
                    <div class="mode-desc">主 EXE + DLL 库文件</div>
                  </div>
                </label>
              </div>
            </div>

            <div class="field-row">
              <label>输出目录</label>
              <div class="input-group">
                <input type="text" [(ngModel)]="outputDir" placeholder="选择 EXE 输出目录..." class="path-input" />
                <button class="btn-browse" (click)="selectOutput()">
                  <span class="material-icons">folder_open</span>
                </button>
              </div>
            </div>

            <div class="field-row">
              <label>代码生成方式</label>
              <div class="checkbox-row">
                <label class="checkbox-label">
                  <input type="checkbox" [(ngModel)]="machineCode" />
                  <span>机器码（Machine Code）— 速度更快，体积更大</span>
                </label>
              </div>
              @if (!machineCode) {
                <div class="field-hint">默认：Pcode（p-code，跨 PB 版本兼容性更好）</div>
              }
            </div>

            @if (!pbgen.found && pbgenChecked) {
              <div class="field-row">
                <label>手动指定 PBGen.exe</label>
                <div class="input-group">
                  <input type="text" [(ngModel)]="pbgenOverride" placeholder="C:\Program Files\Appeon\PB22\PBGen.exe" class="path-input" />
                  <button class="btn-browse" (click)="selectPbgen()">
                    <span class="material-icons">folder_open</span>
                  </button>
                </div>
              </div>
            }
          </div>

          <div class="action-row">
            <button class="btn-build"
              (click)="doBuild()"
              [disabled]="!pblPath || !appName || !outputDir">
              <span class="material-icons">build</span>
              开始编译
            </button>
            @if (!pbgen.found && pbgenChecked) {
              <div class="no-pbgen-hint">
                <span class="material-icons" style="font-size:14px;color:#fab387">warning</span>
                PBGen.exe 未找到。仍可尝试指定路径后编译。
              </div>
            }
          </div>

          <!-- 无 IDE 时的替代方案提示 -->
          @if (!pbgen.found && pbgenChecked) {
            <div class="alt-note">
              <div class="alt-title">
                <span class="material-icons" style="font-size:16px">lightbulb</span>
                没有 PowerBuilder IDE？
              </div>
              <p>可使用 <strong>迁移向导</strong> 将 PB 项目转为 Angular Web 项目，无需 IDE。</p>
              <button class="btn-go-migrate" (click)="onGotoMigrate.emit()">
                <span class="material-icons">transform</span>
                前往迁移向导
              </button>
            </div>
          }
        </div>
      }

      <!-- 编译中 -->
      @if (stage === 'building') {
        <div class="building-area">
          <div class="building-anim">
            <span class="spinner-lg"></span>
            <div class="building-text">
              <div class="building-title">正在编译...</div>
              <div class="building-sub">PBGen.exe 运行中，请耐心等待</div>
            </div>
          </div>
          <div class="build-log-header">实时日志</div>
          <pre class="build-log">{{ buildLog }}</pre>
        </div>
      }

      <!-- 编译完成 -->
      @if (stage === 'done' && buildResult) {
        <div class="done-area">
          <div class="done-banner">
            <span class="material-icons">check_circle</span>
            <div>
              <h4>编译成功</h4>
              <p>{{ buildResult.exe_path }}</p>
            </div>
            <div class="exe-meta">
              <span class="exe-size">{{ buildResult.exe_size_kb }} KB</span>
              <span class="exe-mode">{{ buildResult.mode }}</span>
            </div>
          </div>

          <div class="log-section">
            <div class="log-header">
              <span class="material-icons" style="font-size:14px">terminal</span>
              编译日志
            </div>
            <pre class="build-log">{{ buildResult.log }}</pre>
          </div>

          <div class="done-actions">
            <button class="btn-reset" (click)="reset()">
              <span class="material-icons">refresh</span>
              重新编译
            </button>
          </div>
        </div>
      }

      <!-- 编译失败 -->
      @if (stage === 'error') {
        <div class="error-area">
          <span class="material-icons" style="font-size:32px;color:#f38ba8">error</span>
          <h4>编译失败</h4>
          <pre class="error-log">{{ errorMsg }}</pre>
          <button class="btn-reset" (click)="reset()">
            <span class="material-icons">refresh</span>
            重试
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    .build-panel {
      height: 100%; display: flex; flex-direction: column;
      background: #1e1e2e; color: #cdd6f4; overflow: hidden;
    }

    /* ── Header ── */
    .panel-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.75rem 1rem; border-bottom: 1px solid #313244; flex-shrink: 0;
    }
    .header-left { display: flex; align-items: center; gap: 0.75rem; }
    .header-icon { font-size: 24px; color: #fab387; }
    .panel-header h3 { margin: 0; font-size: 1rem; font-weight: 600; color: #cdd6f4; }
    .header-sub { margin: 0; font-size: 0.75rem; color: #6c7086; }
    .btn-close { background: transparent; border: none; cursor: pointer; color: #6c7086; border-radius: 6px; padding: 0.25rem; display: flex; align-items: center; }
    .btn-close:hover { background: #313244; color: #cdd6f4; }

    /* ── PBGen Status ── */
    .pbgen-status {
      display: flex; align-items: center; gap: 0.6rem;
      padding: 0.55rem 1rem; border-bottom: 1px solid #313244;
      background: #181825; flex-shrink: 0; font-size: 0.8rem; color: #a6adc8;
    }
    .pbgen-status.found { background: rgba(166,227,161,0.04); }
    .pbgen-status.missing { background: rgba(243,139,168,0.04); }
    .pbgen-info { display: flex; flex-direction: column; gap: 0.1rem; flex: 1; }
    .pbgen-ok { font-weight: 600; color: #a6e3a1; font-size: 0.8rem; }
    .pbgen-missing { font-weight: 600; color: #f38ba8; font-size: 0.8rem; }
    .pbgen-path { font-size: 0.7rem; color: #6c7086; word-break: break-all; }
    .btn-browse-sm { padding: 0.3rem 0.6rem; background: #313244; border: 1px solid #45475a; border-radius: 5px; cursor: pointer; color: #a6adc8; font-size: 0.75rem; flex-shrink: 0; }
    .btn-browse-sm:hover { background: #45475a; color: #cdd6f4; }

    /* ── Config Area ── */
    .config-area { flex: 1; overflow-y: auto; padding: 0.75rem 1rem; display: flex; flex-direction: column; gap: 0.75rem; }
    .config-group { background: #181825; border: 1px solid #313244; border-radius: 10px; padding: 0.75rem 1rem; display: flex; flex-direction: column; gap: 0.6rem; }
    .group-title { display: flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; font-weight: 700; color: #fab387; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.1rem; }
    .group-title .material-icons { font-size: 15px; }
    .field-row { display: flex; flex-direction: column; gap: 0.3rem; }
    .field-row label { font-size: 0.76rem; color: #a6adc8; }
    .input-group { display: flex; gap: 0.35rem; }
    .path-input { flex: 1; background: #1e1e2e; border: 1px solid #313244; border-radius: 6px; padding: 0.4rem 0.6rem; color: #cdd6f4; font-size: 0.82rem; }
    .path-input::placeholder { color: #45475a; }
    .path-input:focus { outline: none; border-color: #fab387; }
    .text-input { background: #1e1e2e; border: 1px solid #313244; border-radius: 6px; padding: 0.4rem 0.6rem; color: #cdd6f4; font-size: 0.82rem; width: 100%; box-sizing: border-box; }
    .text-input:focus { outline: none; border-color: #fab387; }
    .btn-browse { background: #313244; border: 1px solid #45475a; border-radius: 6px; padding: 0.4rem 0.6rem; cursor: pointer; color: #a6adc8; display: flex; align-items: center; }
    .btn-browse:hover { background: #45475a; color: #cdd6f4; }
    .btn-browse .material-icons { font-size: 18px; }
    .field-hint { font-size: 0.7rem; color: #6c7086; padding: 0.1rem 0.1rem; }

    /* Mode select */
    .mode-select { display: flex; flex-direction: column; gap: 0.4rem; }
    .mode-option {
      display: flex; align-items: flex-start; gap: 0.6rem;
      padding: 0.5rem 0.65rem; border: 1px solid #313244; border-radius: 7px;
      cursor: pointer; transition: all 0.15s; background: #1e1e2e;
    }
    .mode-option:hover { border-color: #45475a; background: #2a2a3e; }
    .mode-option.active { border-color: #fab387; background: rgba(250,179,135,0.06); }
    .mode-radio { width: 14px; height: 14px; border-radius: 50%; border: 2px solid #45475a; flex-shrink: 0; margin-top: 3px; transition: all 0.15s; }
    .mode-radio.checked { border-color: #fab387; background: #fab387; }
    .mode-label { font-size: 0.8rem; font-weight: 600; color: #cdd6f4; }
    .mode-desc { font-size: 0.7rem; color: #6c7086; }
    .mode-option.active .mode-label { color: #fab387; }

    /* Checkbox */
    .checkbox-row { display: flex; align-items: center; }
    .checkbox-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-size: 0.8rem; color: #a6adc8; }
    .checkbox-label input[type="checkbox"] { width: 14px; height: 14px; cursor: pointer; accent-color: #fab387; }

    /* Action Row */
    .action-row { display: flex; flex-direction: column; gap: 0.4rem; }
    .btn-build {
      display: flex; align-items: center; justify-content: center; gap: 0.5rem;
      padding: 0.65rem 1.5rem; background: linear-gradient(135deg, #fab387, #fe640b);
      color: #11111b; border: none; border-radius: 8px; cursor: pointer;
      font-size: 0.9rem; font-weight: 700; transition: all 0.2s;
    }
    .btn-build:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(250,179,135,0.35); }
    .btn-build:disabled { opacity: 0.35; cursor: not-allowed; transform: none; }
    .btn-build .material-icons { font-size: 18px; }
    .no-pbgen-hint { display: flex; align-items: center; gap: 0.3rem; font-size: 0.72rem; color: #fab387; }

    /* Alt Note */
    .alt-note {
      background: rgba(137,180,250,0.05); border: 1px solid rgba(137,180,250,0.15);
      border-radius: 8px; padding: 0.75rem 1rem;
    }
    .alt-title { display: flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; font-weight: 700; color: #89b4fa; margin-bottom: 0.35rem; }
    .alt-note p { margin: 0 0 0.5rem; font-size: 0.78rem; color: #a6adc8; line-height: 1.5; }
    .btn-go-migrate { display: flex; align-items: center; gap: 0.4rem; padding: 0.4rem 0.85rem; background: transparent; border: 1px solid #89b4fa; border-radius: 6px; cursor: pointer; color: #89b4fa; font-size: 0.78rem; }
    .btn-go-migrate:hover { background: rgba(137,180,250,0.1); }

    /* Building Area */
    .building-area { flex: 1; display: flex; flex-direction: column; padding: 1rem; gap: 0.75rem; overflow: hidden; }
    .building-anim { display: flex; align-items: center; gap: 1rem; padding: 1rem; background: rgba(250,179,135,0.05); border: 1px solid rgba(250,179,135,0.2); border-radius: 10px; }
    .building-title { font-size: 1rem; font-weight: 600; color: #fab387; }
    .building-sub { font-size: 0.78rem; color: #6c7086; margin-top: 0.2rem; }
    .build-log-header { font-size: 0.72rem; font-weight: 700; color: #6c7086; text-transform: uppercase; letter-spacing: 0.06em; }
    .build-log { flex: 1; background: #11111b; border: 1px solid #313244; border-radius: 8px; padding: 0.75rem 1rem; color: #a6adc8; font-size: 0.75rem; font-family: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace; overflow-y: auto; white-space: pre-wrap; word-break: break-all; margin: 0; }

    /* Done Area */
    .done-area { flex: 1; display: flex; flex-direction: column; padding: 1rem; gap: 0.75rem; overflow: hidden; }
    .done-banner { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; background: rgba(166,227,161,0.08); border: 1px solid rgba(166,227,161,0.2); border-radius: 10px; }
    .done-banner .material-icons { font-size: 28px; color: #a6e3a1; flex-shrink: 0; }
    .done-banner h4 { margin: 0; color: #a6e3a1; font-size: 0.95rem; }
    .done-banner p { margin: 0; font-size: 0.72rem; color: #6c7086; word-break: break-all; }
    .exe-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 0.2rem; margin-left: auto; flex-shrink: 0; }
    .exe-size { font-size: 0.85rem; font-weight: 700; color: #89b4fa; }
    .exe-mode { font-size: 0.68rem; color: #6c7086; background: #313244; padding: 0.1rem 0.4rem; border-radius: 4px; }
    .log-section { flex: 1; display: flex; flex-direction: column; gap: 0.35rem; overflow: hidden; }
    .log-header { display: flex; align-items: center; gap: 0.35rem; font-size: 0.72rem; font-weight: 700; color: #6c7086; text-transform: uppercase; letter-spacing: 0.06em; flex-shrink: 0; }
    .done-actions { flex-shrink: 0; }
    .btn-reset { display: flex; align-items: center; gap: 0.4rem; padding: 0.5rem 1rem; background: #313244; border: 1px solid #45475a; border-radius: 6px; cursor: pointer; color: #a6adc8; font-size: 0.82rem; }
    .btn-reset:hover { background: #45475a; color: #cdd6f4; }

    /* Error Area */
    .error-area { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0.75rem; padding: 2rem; text-align: center; }
    .error-area h4 { margin: 0; color: #f38ba8; }
    .error-log { background: #11111b; border: 1px solid #313244; border-radius: 8px; padding: 0.75rem 1rem; color: #f38ba8; font-size: 0.75rem; font-family: monospace; max-width: 100%; overflow: auto; text-align: left; white-space: pre-wrap; word-break: break-all; margin: 0; max-height: 300px; }

    /* Spinners */
    .spinner-sm { display: inline-block; width: 14px; height: 14px; flex-shrink: 0; border: 2px solid #313244; border-top-color: #fab387; border-radius: 50%; animation: spin 0.8s linear infinite; }
    .spinner-lg { width: 36px; height: 36px; flex-shrink: 0; border: 3px solid #313244; border-top-color: #fab387; border-radius: 50%; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
  `]
})
export class BuildPanelComponent implements OnInit {
  @Input() projectPath = '';
  @Output() onClose = new EventEmitter<void>();
  @Output() onGotoMigrate = new EventEmitter<void>();

  stage: Stage = 'idle';
  pbgen: PbgenStatus = { found: false, path: '', version: '' };
  pbgenChecked = false;

  pblPath = '';
  appName = '';
  buildMode = 'exe';
  outputDir = '';
  machineCode = false;
  pbgenOverride = '';

  buildLog = '';
  buildResult: BuildResult | null = null;
  errorMsg = '';

  async ngOnInit() {
    if (this.projectPath) {
      this.pblPath = this.projectPath;
    }
    await this.checkPbgen();
  }

  async checkPbgen() {
    try {
      this.pbgen = await invoke<PbgenStatus>('check_pbgen');
      this.pbgenChecked = true;
    } catch {
      this.pbgen = { found: false, path: '', version: '' };
      this.pbgenChecked = true;
    }
  }

  async selectPbl() {
    try {
      const selected = await open({
        multiple: false,
        filters: [{ name: 'PBL Files', extensions: ['pbl'] }],
        title: '选择主 PBL 文件',
      });
      if (selected) {
        this.pblPath = selected as string;
        if (!this.appName) {
          const name = (selected as string).split(/[\\/]/).pop() ?? '';
          this.appName = name.replace(/\.pbl$/i, '');
        }
      }
    } catch (e) { console.error(e); }
  }

  async selectOutput() {
    try {
      const selected = await open({ directory: true, multiple: false, title: '选择 EXE 输出目录' });
      if (selected) this.outputDir = selected as string;
    } catch (e) { console.error(e); }
  }

  async selectPbgen() {
    try {
      const selected = await open({
        multiple: false,
        filters: [{ name: 'PBGen', extensions: ['exe'] }],
        title: '选择 PBGen.exe',
      });
      if (selected) {
        this.pbgenOverride = selected as string;
        this.pbgen = { found: true, path: this.pbgenOverride, version: 'manual' };
      }
    } catch (e) { console.error(e); }
  }

  async doBuild() {
    if (!this.pblPath || !this.appName || !this.outputDir) return;
    this.stage = 'building';
    this.buildLog = '正在调用 PBGen.exe...\n';
    this.errorMsg = '';
    this.buildResult = null;

    try {
      const result: BuildResult = await invoke('build_pb_application', {
        pblPath: this.pblPath,
        appName: this.appName,
        mode: this.buildMode,
        outputDir: this.outputDir,
        machineCode: this.machineCode,
        pbgenPath: this.pbgenOverride || null,
      });

      this.buildResult = result;
      this.stage = 'done';
    } catch (e: any) {
      this.errorMsg = String(e?.message ?? e);
      this.stage = 'error';
    }
  }

  reset() {
    this.stage = 'idle';
    this.buildLog = '';
    this.buildResult = null;
    this.errorMsg = '';
  }
}
