import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PblService, PblFileInfo, ProjectReport, ReportSummary } from '../../services/pbl.service';

@Component({
  selector: 'app-project-stats',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="project-stats">
      <div class="ps-header">
        <span class="material-icons" style="font-size:18px;color:#7c3aed">analytics</span>
        <span class="ps-title">项目统计</span>
      </div>

      @if (loading) {
        <div class="ps-loading">
          <div class="spinner"></div>
          <span>分析中...</span>
        </div>
      }

      @if (error) {
        <div class="ps-error">{{ error }}</div>
      }

      @if (report) {
        <!-- 摘要卡片 -->
        <div class="ps-summary">
          <div class="ps-card">
            <span class="material-icons" style="font-size:20px;color:#7c3aed">inventory_2</span>
            <div class="ps-card-data">
              <span class="ps-card-value">{{ report.summary.total_pbl_files }}</span>
              <span class="ps-card-label">PBL 文件</span>
            </div>
          </div>
          <div class="ps-card">
            <span class="material-icons" style="font-size:20px;color:#2563eb">widgets</span>
            <div class="ps-card-data">
              <span class="ps-card-value">{{ report.summary.total_objects }}</span>
              <span class="ps-card-label">总对象</span>
            </div>
          </div>
          <div class="ps-card">
            <span class="material-icons" style="font-size:20px;color:#059669">description</span>
            <div class="ps-card-data">
              <span class="ps-card-value">{{ report.summary.source_objects }}</span>
              <span class="ps-card-label">源码对象</span>
            </div>
          </div>
          <div class="ps-card">
            <span class="material-icons" style="font-size:20px;color:#d97706">build</span>
            <div class="ps-card-data">
              <span class="ps-card-value">{{ report.summary.compiled_objects }}</span>
              <span class="ps-card-label">编译对象</span>
            </div>
          </div>
        </div>

        <!-- 对象类型分布 -->
        <div class="ps-section">
          <h4><span class="material-icons" style="font-size:16px;vertical-align:middle">pie_chart</span> 对象类型分布</h4>
          <div class="ps-chart-area">
            @for (item of topTypes; track item[0]) {
              <div class="ps-bar-row">
                <span class="bar-label">{{ item[0] }}</span>
                <div class="bar-track">
                  <div class="bar-fill" [style.width.%]="barPercent(item[1])" [style.background]="typeColor(item[0])"></div>
                </div>
                <span class="bar-value">{{ item[1] }}</span>
              </div>
            }
          </div>
        </div>

        <!-- PBL 文件列表 -->
        <div class="ps-section">
          <h4><span class="material-icons" style="font-size:16px;vertical-align:middle">folder</span> PBL 文件明细</h4>
          <div class="ps-table-wrap">
            <table class="ps-table">
              <thead>
                <tr>
                  <th>文件名</th>
                  <th>对象数</th>
                  <th>源码</th>
                  <th>编译</th>
                  <th>大小</th>
                  <th>版本</th>
                  <th>编码</th>
                </tr>
              </thead>
              <tbody>
                @for (f of report.pbl_files; track f.path) {
                  <tr>
                    <td class="td-name" [title]="f.path">{{ f.name }}</td>
                    <td>{{ f.total_entries }}</td>
                    <td class="td-source">{{ f.source_entries }}</td>
                    <td class="td-compiled">{{ f.compiled_entries }}</td>
                    <td>{{ formatSize(f.size_bytes) }}</td>
                    <td>{{ f.pb_version }}</td>
                    <td>
                      <span class="encode-badge" [class.unicode]="f.is_unicode">
                        {{ f.is_unicode ? 'Unicode' : 'ANSI' }}
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

        <!-- 文件统计 -->
        <div class="ps-section">
          <h4><span class="material-icons" style="font-size:16px;vertical-align:middle">storage</span> 文件统计</h4>
          <div class="ps-file-stats">
            <div class="fs-item">
              <span class="fs-label">总大小</span>
              <span class="fs-value">{{ formatSize(report.file_stats.total_size_bytes) }}</span>
            </div>
            <div class="fs-item">
              <span class="fs-label">平均大小</span>
              <span class="fs-value">{{ formatSize(report.file_stats.average_size_bytes) }}</span>
            </div>
            <div class="fs-item">
              <span class="fs-label">最大文件</span>
              <span class="fs-value">{{ getLargestFileDesc() }}</span>
            </div>
            <div class="fs-item">
              <span class="fs-label">编码分布</span>
              <span class="fs-value">
                <span class="encode-badge unicode">Unicode {{ report.summary.unicode_pbls }}</span>
                <span class="encode-badge">ANSI {{ report.summary.ansi_pbls }}</span>
              </span>
            </div>
          </div>
        </div>
      }

      @if (!loading && !report && !error) {
        <div class="ps-empty">
          <span class="material-icons" style="font-size:36px;color:#d1d5db">analytics</span>
          <p>打开项目后查看统计信息</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .project-stats { display: flex; flex-direction: column; height: 100%; background: #fff; overflow-y: auto; }
    .ps-header { display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; flex-shrink: 0; }
    .ps-title { font-size: 0.9rem; font-weight: 600; color: #111; }

    .ps-loading { display: flex; align-items: center; gap: 0.5rem; padding: 2rem; justify-content: center; color: #6b7280; }
    .spinner { width: 18px; height: 18px; border: 2px solid #e5e7eb; border-top-color: #7c3aed; border-radius: 50%; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
    .ps-error { padding: 0.75rem 1rem; margin: 0.5rem; background: #fee2e2; color: #dc2626; border-radius: 6px; font-size: 0.85rem; }

    /* 摘要卡片 */
    .ps-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; padding: 0.75rem 1rem; }
    .ps-card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 0.75rem; display: flex; align-items: center; gap: 0.6rem; }
    .ps-card-data { display: flex; flex-direction: column; }
    .ps-card-value { font-size: 1.2rem; font-weight: 700; color: #111; line-height: 1.2; }
    .ps-card-label { font-size: 0.7rem; color: #6b7280; }

    /* 区块 */
    .ps-section { padding: 0.75rem 1rem; border-top: 1px solid #e5e7eb; }
    .ps-section h4 { margin: 0 0 0.5rem; font-size: 0.82rem; color: #374151; display: flex; align-items: center; gap: 0.3rem; }

    /* 柱状图 */
    .ps-chart-area { display: flex; flex-direction: column; gap: 0.35rem; }
    .ps-bar-row { display: flex; align-items: center; gap: 0.5rem; }
    .bar-label { width: 80px; font-size: 0.75rem; color: #374151; text-align: right; flex-shrink: 0; }
    .bar-track { flex: 1; height: 16px; background: #f3f4f6; border-radius: 3px; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 3px; transition: width 0.3s ease; min-width: 2px; }
    .bar-value { width: 36px; font-size: 0.75rem; color: #6b7280; text-align: right; flex-shrink: 0; }

    /* 表格 */
    .ps-table-wrap { overflow-x: auto; }
    .ps-table { width: 100%; border-collapse: collapse; font-size: 0.78rem; }
    .ps-table th { padding: 0.4rem 0.6rem; background: #f9fafb; border-bottom: 1px solid #e5e7eb; text-align: left; color: #6b7280; font-weight: 600; white-space: nowrap; }
    .ps-table td { padding: 0.35rem 0.6rem; border-bottom: 1px solid #f3f4f6; color: #374151; }
    .td-name { max-width: 160px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .td-source { color: #059669; }
    .td-compiled { color: #d97706; }

    .encode-badge { font-size: 0.68rem; padding: 0.1rem 0.4rem; border-radius: 8px; background: #fef3c7; color: #92400e; }
    .encode-badge.unicode { background: #dbeafe; color: #1d4ed8; }

    /* 文件统计 */
    .ps-file-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem; }
    .fs-item { display: flex; justify-content: space-between; align-items: center; padding: 0.4rem 0.6rem; background: #f9fafb; border-radius: 4px; }
    .fs-label { font-size: 0.78rem; color: #6b7280; }
    .fs-value { font-size: 0.78rem; color: #374151; font-weight: 500; display: flex; gap: 0.3rem; align-items: center; }

    .ps-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #9ca3af; padding: 2rem; text-align: center; }
    .ps-empty p { margin: 0.5rem 0 0; font-size: 0.85rem; }
  `]
})
export class ProjectStatsComponent implements OnChanges {
  @Input() projectPath = '';

  report: ProjectReport | null = null;
  loading = false;
  error = '';

  constructor(private pblService: PblService) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes['projectPath'] && this.projectPath) {
      this.loadReport();
    }
  }

  async loadReport() {
    this.loading = true;
    this.error = '';
    try {
      this.report = await this.pblService.generateReport(this.projectPath);
    } catch (e: any) {
      this.error = e.message || '生成报告失败';
    } finally {
      this.loading = false;
    }
  }

  get topTypes(): [string, number][] {
    if (!this.report?.object_stats?.top_types) return [];
    return this.report.object_stats.top_types;
  }

  barPercent(count: number): number {
    if (!this.report?.object_stats?.top_types?.length) return 0;
    const max = this.report.object_stats.top_types[0][1];
    if (!max) return 0;
    return (count / max) * 100;
  }

  typeColor(type: string): string {
    const colors: Record<string, string> = {
      window: '#2563eb', datawindow: '#7c3aed', menu: '#059669',
      function: '#d97706', structure: '#dc2626', userobject: '#0891b2',
      application: '#8b5cf6', query: '#6366f1', pipeline: '#0d9488',
      project: '#4f46e5', proxy: '#a855f7', binary: '#6b7280', unknown: '#9ca3af'
    };
    return colors[type.toLowerCase()] ?? '#6b7280';
  }

  getLargestFileDesc(): string {
    if (!this.report?.file_stats?.largest_file) return '-';
    const [path, size] = this.report.file_stats.largest_file;
    const name = path.split(/[/\\]/).pop() ?? path;
    return name + ' (' + this.formatSize(size) + ')';
  }

  formatSize(bytes: number): string {
    if (!bytes) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }
}
