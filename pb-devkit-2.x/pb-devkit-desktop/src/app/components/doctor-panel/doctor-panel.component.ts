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
        <h3>🔧 环境诊断</h3>
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

      @if (!result && !loading && !error) {
        <div class="empty-hint">
          <p>点击「运行诊断」检查环境状态</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .doctor-panel {
      display: flex;
      flex-direction: column;
      height: 100%;
      overflow-y: auto;
    }
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 1rem;
      border-bottom: 1px solid #e5e7eb;
    }
    .panel-header h3 {
      margin: 0;
      font-size: 0.9rem;
      color: #374151;
    }
    .btn-run {
      padding: 0.35rem 0.75rem;
      background: #3b82f6;
      color: #fff;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.8rem;
    }
    .btn-run:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-run:hover:not(:disabled) { background: #2563eb; }
    .error-state {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.6rem 0.75rem;
      margin: 0.75rem 1rem;
      background: #fee2e2;
      border-radius: 6px;
      color: #dc2626;
      font-size: 0.8rem;
    }
    .btn-dismiss {
      margin-left: auto;
      background: none;
      border: none;
      color: #dc2626;
      cursor: pointer;
      font-size: 0.9rem;
    }
    .doctor-result {
      background: #f9fafb;
      border: 1px solid #e5e7eb;
      border-radius: 6px;
      padding: 0.75rem;
      margin: 0.75rem 1rem;
    }
    .result-header {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.85rem;
      font-weight: 600;
      color: #111;
      margin-bottom: 0.75rem;
    }
    .check-list {
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
      margin-bottom: 0.75rem;
    }
    .check-item {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.5rem 0.6rem;
      border-radius: 4px;
      font-size: 0.8rem;
    }
    .check-item.ok {
      background: #dcfce7;
      color: #166534;
    }
    .check-item.fail {
      background: #fee2e2;
      color: #991b1b;
    }
    .check-icon { width: 20px; text-align: center; }
    .check-label { font-weight: 600; min-width: 100px; }
    .check-detail { color: #6b7280; font-size: 0.75rem; }
    .issue-section, .warning-section { margin-top: 0.5rem; }
    .issue-section h4 { margin: 0 0 0.3rem; font-size: 0.8rem; color: #dc2626; }
    .warning-section h4 { margin: 0 0 0.3rem; font-size: 0.8rem; color: #d97706; }
    .issue-section ul, .warning-section ul { padding-left: 1.2rem; margin: 0; }
    .issue-item { color: #991b1b; font-size: 0.8rem; margin-bottom: 0.2rem; }
    .warning-item { color: #92400e; font-size: 0.8rem; margin-bottom: 0.2rem; }
    .all-ok {
      padding: 0.6rem;
      background: #dcfce7;
      border-radius: 4px;
      color: #166534;
      font-size: 0.8rem;
      text-align: center;
    }
    .empty-hint {
      padding: 2rem 1rem;
      text-align: center;
      color: #9ca3af;
      font-size: 0.85rem;
    }
    .empty-hint p { margin: 0; }
  `]
})
export class DoctorPanelComponent implements OnInit {
  result: DoctorResult | null = null;
  loading = false;
  error = '';

  constructor(private pblService: PblService) {}

  ngOnInit() {
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
