import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PblService, DoctorResult } from '../../services/pbl.service';

@Component({
  selector: 'app-doctor-panel',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="doctor-panel">
      <div class="panel-header">
        <h3>⚕️ 环境诊断</h3>
        <button class="btn-run" (click)="runDoctor()" [disabled]="loading">
          {{ loading ? '检测中...' : '运行诊断' }}
        </button>
      </div>

      @if (error) {
        <div class="error-state">
          <span>⚠ {{ error }}</span>
          <button class="btn-dismiss" (click)="error = ''">✕</button>
        </div>
      }

      @if (result) {
        <div class="doctor-result">
          <div class="result-header">
            <span class="status-icon">{{ result.success ? '✅' : '❌' }}</span>
            <span>环境诊断结果</span>
          </div>

          <div class="check-list">
            <!-- Python -->
            <div class="check-item" [class.ok]="result.python_version"
                 [class.fail]="!result.python_version">
              <span class="check-icon">{{ result.python_version ? '✅' : '❌' }}</span>
              <span class="check-label">Python</span>
              <span class="check-detail">
                {{ result.python_version ?? '未安装 / 未找到' }}
              </span>
            </div>

            <!-- Rust -->
            <div class="check-item" [class.ok]="result.rust_available"
                 [class.fail]="!result.rust_available">
              <span class="check-icon">{{ result.rust_available ? '✅' : '❌' }}</span>
              <span class="check-label">Rust</span>
              <span class="check-detail">
                {{ result.rust_available ? '已安装' : '未安装' }}
              </span>
            </div>

            <!-- ORCA DLL -->
            <div class="check-item" [class.ok]="result.orca_dll_found"
                 [class.fail]="!result.orca_dll_found">
              <span class="check-icon">{{ result.orca_dll_found ? '✅' : '⚠' }}</span>
              <span class="check-label">PBSpyORCA.dll</span>
              <span class="check-detail">
                {{ result.orca_dll_found ? '已找到' : '未找到（import/build 功能不可用）' }}
              </span>
            </div>
          </div>

          <!-- Issues -->
          @if (result.issues.length > 0) {
            <div class="issue-section">
              <h4>❌ 问题</h4>
              <ul>
                @for (issue of result.issues; track issue) {
                  <li class="issue-item">{{ issue }}</li>
                }
              </ul>
            </div>
          }

          <!-- Warnings -->
          @if (result.warnings.length > 0) {
            <div class="warning-section">
              <h4>⚠ 警告</h4>
              <ul>
                @for (warn of result.warnings; track warn) {
                  <li class="warning-item">{{ warn }}</li>
                }
              </ul>
            </div>
          }

          @if (result.issues.length === 0 && result.warnings.length === 0) {
            <div class="all-ok">🎉 所有环境检查通过，无问题。</div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .doctor-panel {
      padding: 16px;
      border-bottom: 1px solid #334155;
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .panel-header h3 {
      margin: 0;
      font-size: 15px;
      color: #e2e8f0;
    }
    .btn-run {
      padding: 6px 14px;
      background: #3b82f6;
      color: #fff;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
    }
    .btn-run:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .btn-run:hover:not(:disabled) {
      background: #2563eb;
    }
    .error-state {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      background: #451a1a;
      border: 1px solid #ef4444;
      border-radius: 6px;
      color: #fca5a5;
      font-size: 13px;
      margin-bottom: 12px;
    }
    .btn-dismiss {
      margin-left: auto;
      background: none;
      border: none;
      color: #fca5a5;
      cursor: pointer;
      font-size: 16px;
    }
    .doctor-result {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 14px;
    }
    .result-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      font-weight: 600;
      color: #e2e8f0;
      margin-bottom: 12px;
    }
    .check-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 12px;
    }
    .check-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 13px;
    }
    .check-item.ok {
      background: #052e16;
      color: #4ade80;
    }
    .check-item.fail {
      background: #451a1a;
      color: #fca5a5;
    }
    .check-icon {
      font-size: 16px;
      width: 24px;
      text-align: center;
    }
    .check-label {
      font-weight: 600;
      min-width: 120px;
    }
    .check-detail {
      color: #94a3b8;
      font-size: 12px;
    }
    .issue-section, .warning-section {
      margin-top: 8px;
    }
    .issue-section h4, .warning-section h4 {
      margin: 0 0 6px;
      font-size: 13px;
    }
    .issue-section h4 { color: #fca5a5; }
    .warning-section h4 { color: #fcd34d; }
    .issue-item {
      color: #fca5a5;
      font-size: 13px;
      margin-bottom: 4px;
    }
    .warning-item {
      color: #fcd34d;
      font-size: 13px;
      margin-bottom: 4px;
    }
    .all-ok {
      padding: 10px;
      background: #052e16;
      border-radius: 6px;
      color: #4ade80;
      font-size: 13px;
      text-align: center;
    }
  `]
})
export class DoctorPanelComponent implements OnInit {
  result: DoctorResult | null = null;
  loading = false;
  error = '';

  constructor(private pblService: PblService) {}

  ngOnInit() {
    // 组件加载时自动运行一次诊断
    this.runDoctor();
  }

  async runDoctor() {
    this.loading = true;
    this.error = '';
    this.result = null;

    try {
      this.result = await this.pblService.runDoctor();
    } catch (e: any) {
      this.error = e?.toString() ?? '诊断失败';
    } finally {
      this.loading = false;
    }
  }
}
