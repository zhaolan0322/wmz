const BUILD_VERSION = '20260317-EXEC-OPS-V3';
const STAR_OFFICE_URL = 'http://127.0.0.1:19000/';
const fmt = new Intl.NumberFormat('zh-CN');

let currentRange = '7d';
let selectedAgent = '';
let sortMetric = 'totalTokens';
let sortDirection = 'desc';
let projectLimit = '10';
let allAgentOptions = [];

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatDate(value) {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
  } catch (_err) {
    return String(value);
  }
}

function formatCompact(value) {
  return fmt.format(value || 0);
}

function pct(part, total) {
  if (!total) return 0;
  return Math.round((part / total) * 1000) / 10;
}

function metricValue(item, metric) {
  if (metric === 'latestActiveAt') {
    const parsed = Date.parse(item?.latestActiveAt || '');
    return Number.isNaN(parsed) ? 0 : parsed;
  }
  return item?.[metric] ?? 0;
}

function dashboardUrl() {
  const params = new URLSearchParams({ range: currentRange });
  if (selectedAgent) params.set('agents', selectedAgent);
  return `/api/dashboard?${params.toString()}`;
}

async function fetchJson(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function metricCard(label, value, sub, tone = 'default') {
  return `
    <article class="summary-card ${tone}">
      <div class="summary-label">${escapeHtml(label)}</div>
      <div class="summary-value">${escapeHtml(value)}</div>
      <div class="summary-sub">${escapeHtml(sub)}</div>
    </article>
  `;
}

function renderHeader(overview) {
  const alertLabel = overview.alert?.label || '状态未知';
  document.getElementById('statusLine').textContent =
    `Live · 更新 ${formatDate(overview.updatedAt)} · ${alertLabel}`;
  document.getElementById('metaLine').textContent =
    `Build ${BUILD_VERSION} · 节点 ${overview.sourcePath} · ${overview.env}`;
}

function renderRuntimePanel(overview) {
  const host = document.getElementById('runtimePanel');
  if (!host) return;

  const provider = overview.runtimeProvider || 'unknown';
  const model = overview.runtimeModel || 'unknown';
  const authAccount = overview.runtimeAuthAccount || '-';

  host.innerHTML = `
    <div class="runtime-kicker">当前模型</div>
    <div class="runtime-model">${escapeHtml(provider)} / ${escapeHtml(model)}</div>
    <div class="runtime-kicker">当前账号</div>
    <div class="runtime-account">${escapeHtml(authAccount)}</div>
  `;
}

function renderSummary(overview) {
  const total = overview.totalTokens || 0;
  const runtime = overview.observedRuntimeTokens || 0;
  const productiveShare = pct(overview.productiveTokens, total);
  const opsShare = pct(overview.opsTokens, total);
  const errorShare = pct(overview.errorTokens, runtime);
  const cacheHitRate = overview.cacheHitRate || 0;
  const cacheReadTokens = overview.cacheReadTokens || 0;
  const cacheNewTokens = overview.cacheWriteTokens || 0;
  const cacheAgent = overview.cacheAgentId || '-';
  const cacheTime = overview.cacheUpdatedAt ? formatDate(overview.cacheUpdatedAt) : '';
  const cacheScope = `当前活跃会话 · ${formatCompact(cacheReadTokens)} cached · ${formatCompact(cacheNewTokens)} new`;
  const cacheSub = cacheTime ? `${cacheScope} · ${cacheAgent} · ${cacheTime}` : cacheScope;
  const latestTurnSub = overview.latestTurnAt
    ? `${overview.latestTurnAgent || '-'} · ${formatDate(overview.latestTurnAt)}`
    : '当前筛选范围内暂无 assistant 对话';
  const previousTurnSub = overview.previousTurnAt
    ? `${overview.previousTurnAgent || '-'} · ${formatDate(overview.previousTurnAt)}`
    : '当前筛选范围内暂无上一轮 assistant 对话';

  document.getElementById('summaryCards').innerHTML = [
    metricCard('总 Token', formatCompact(total), `${formatCompact(overview.sessions)} 会话 · ${overview.activeAgents} Bot`),
    metricCard('总轮次', formatCompact(overview.assistantTurns), `平均每会话 ${formatCompact(Math.round((overview.assistantTurns || 0) / Math.max(overview.sessions || 1, 1)))}`),
    metricCard('Cache 命中率', `${cacheHitRate}%`, cacheSub),
    metricCard('最近一轮对话', formatCompact(overview.latestTurnTokens), latestTurnSub),
    metricCard('上一轮对话', formatCompact(overview.previousTurnTokens), previousTurnSub),
    metricCard('有效消耗', formatCompact(overview.productiveTokens), `${productiveShare}% 属于用户/项目交付`, 'good'),
    metricCard('内部消耗', formatCompact(overview.opsTokens), `${opsShare}% 属于自动任务/运维`, 'warning'),
    metricCard('错误损耗', formatCompact(overview.errorTokens), `${errorShare}% 占运行时观测消耗`, overview.alert?.level === 'critical' ? 'danger' : 'warning'),
  ].join('');
}

function sortRows(items, metric) {
  return [...items].sort((a, b) => {
    const av = metricValue(a, metric);
    const bv = metricValue(b, metric);
    return sortDirection === 'asc' ? av - bv : bv - av;
  });
}

function sortIcon(metric) {
  if (sortMetric !== metric) return '↕';
  return sortDirection === 'desc' ? '↓' : '↑';
}

function renderComparisonHeader(singleBotMode) {
  const entityLabel = singleBotMode ? '项目 / 成本中心' : 'Bot';
  const trailingLabel = singleBotMode ? '会话数' : '有效占比';
  document.getElementById('botCompareHeader').innerHTML = `
    <div class="compare-header-cell compare-header-name">${entityLabel}</div>
    <button class="compare-sort ${sortMetric === 'totalTokens' ? 'active' : ''}" data-sort-metric="totalTokens">
      Token <span class="sort-glyph">${sortIcon('totalTokens')}</span>
    </button>
    <button class="compare-sort ${sortMetric === 'assistantTurns' ? 'active' : ''}" data-sort-metric="assistantTurns">
      对话轮次 <span class="sort-glyph">${sortIcon('assistantTurns')}</span>
    </button>
    <button class="compare-sort ${sortMetric === 'latestActiveAt' ? 'active' : ''}" data-sort-metric="latestActiveAt">
      最近活跃 <span class="sort-glyph">${sortIcon('latestActiveAt')}</span>
    </button>
    <button class="compare-sort ${sortMetric === 'errorTokens' ? 'active' : ''}" data-sort-metric="errorTokens">
      错误损耗 <span class="sort-glyph">${sortIcon('errorTokens')}</span>
    </button>
    <div class="compare-header-cell compare-header-static">${trailingLabel}</div>
  `;

  document.querySelectorAll('#botCompareHeader .compare-sort').forEach(button => {
    button.onclick = async () => {
      const metric = button.dataset.sortMetric;
      if (sortMetric === metric) {
        sortDirection = sortDirection === 'desc' ? 'asc' : 'desc';
      } else {
        sortMetric = metric;
        sortDirection = 'desc';
      }
      await loadDashboard();
    };
  });
}

function botBarWidth(value, maxValue) {
  if (!maxValue) return 0;
  return Math.max(6, Math.round((value / maxValue) * 1000) / 10);
}

function renderBotComparison(agentItems, projectItems) {
  const singleBotMode = Boolean(selectedAgent);
  const sourceItems = singleBotMode ? projectItems : agentItems;
  const ordered = sortRows(sourceItems, sortMetric);
  const maxValue = Math.max(...ordered.map(item => metricValue(item, sortMetric)), 0);
  document.getElementById('compareSectionTitle').textContent = singleBotMode ? 'Bot 下项目对比' : 'Bot 消耗对比';
  renderComparisonHeader(singleBotMode);
  const rows = ordered.map(item => `
    <article class="compare-row">
      <div class="compare-main">
        <div class="compare-head">
          <div class="compare-title">
            ${escapeHtml(singleBotMode ? item.name : item.agentId)}
            ${singleBotMode ? `<span class="compare-sub">${escapeHtml(item.kind === 'project' ? item.source : '系统成本中心')}</span>` : ''}
          </div>
          <div class="compare-value compare-grid">
            <span>${formatCompact(item.totalTokens)} Token</span>
            <span>${formatCompact(item.assistantTurns)} 轮</span>
            <span>${escapeHtml(formatDate(item.latestActiveAt))}</span>
            <span>${formatCompact(item.errorTokens)} 错误</span>
            <span>${singleBotMode ? `${formatCompact(item.sessions)} 会话` : `${item.productiveShare}% 有效`}</span>
          </div>
        </div>
        <div class="compare-track">
          <div class="compare-fill" style="width:${botBarWidth(metricValue(item, sortMetric), maxValue)}%"></div>
        </div>
      </div>
    </article>
  `).join('');

  document.getElementById('botComparison').innerHTML = rows || `<div class="empty-state">${singleBotMode ? '当前 Bot 下没有可用项目或成本中心数据。' : '没有可用 Bot 数据。'}</div>`;
}

function riskState(level) {
  if (level === 'critical') return { cls: 'risk-critical', label: '红灯' };
  if (level === 'warning') return { cls: 'risk-warning', label: '黄灯' };
  return { cls: 'risk-normal', label: '稳定' };
}

function renderRisk(overview, risk) {
  const state = riskState(risk.level);
  const hotList = (risk.hotSessions || []).slice(0, 3);
  const hotHtml = hotList.length
    ? hotList.map(item => `
      <div class="risk-tile compact">
        <div class="risk-state"><span class="risk-dot ${state.cls}"></span>${escapeHtml(item.agentId)}</div>
        <div class="risk-title small">${item.recent5mTokens > 0 ? `${formatCompact(item.recent5mTokens)} / 5m` : `${formatCompact(item.errorTokens)} error`}</div>
        <div class="risk-copy">${escapeHtml(item.project || item.workstream)}</div>
      </div>
    `).join('')
    : '<div class="risk-tile compact"><div class="risk-title small">0</div><div class="risk-copy">最近 5 分钟无高消耗或错误暴露。</div></div>';

  document.getElementById('riskPanel').innerHTML = `
    <div class="risk-tile">
      <div class="risk-state"><span class="risk-dot ${state.cls}"></span>${escapeHtml(state.label)}</div>
      <div class="risk-title">${escapeHtml(overview.alert.label)}</div>
      <div class="risk-copy">${escapeHtml(risk.message || overview.alert.message)}</div>
    </div>
    <div class="risk-stats">
      <div class="mini-stat">
        <span class="mini-label">近 5m</span>
        <strong>${formatCompact(overview.recent5mTokens)}</strong>
      </div>
      <div class="mini-stat">
        <span class="mini-label">近 1h</span>
        <strong>${formatCompact(overview.recent1hTokens)}</strong>
      </div>
      <div class="mini-stat">
        <span class="mini-label">近 24h</span>
        <strong>${formatCompact(overview.recent24hTokens)}</strong>
      </div>
    </div>
    ${hotHtml}
  `;
}

function renderTable(hostId, headers, rows, emptyText) {
  const host = document.getElementById(hostId);
  if (!rows.length) {
    host.innerHTML = `<div class="empty-state">${escapeHtml(emptyText)}</div>`;
    return;
  }
  host.innerHTML = `
    <div class="table-shell">
      <table>
        <thead><tr>${headers.map(label => `<th>${escapeHtml(label)}</th>`).join('')}</tr></thead>
        <tbody>${rows.join('')}</tbody>
      </table>
    </div>
  `;
}

function renderProjects(items) {
  const ordered = sortRows(items, 'totalTokens');
  const visible = projectLimit === 'all' ? ordered : ordered.slice(0, Number(projectLimit));
  const rows = visible.map(item => `
    <tr>
      <td>
        <span class="table-accent">${escapeHtml(item.name)}</span>
        <span class="table-sub">${escapeHtml(item.kind === 'project' ? item.source : '系统成本中心')}</span>
      </td>
      <td>${formatCompact(item.totalTokens)}</td>
      <td>${formatCompact(item.assistantTurns)}</td>
      <td>${formatCompact(item.avgTokensPerTurn)}</td>
      <td>${escapeHtml(item.leadAgent)}</td>
      <td>${escapeHtml(formatDate(item.latestActiveAt))}</td>
    </tr>
  `);
  renderTable('projectTable', ['项目', 'Token', '轮次', '单轮成本', '主责 Bot', '最近活跃'], rows, '没有可用的项目归因数据。');
}

function renderAgents(items) {
  const ordered = sortRows(items, sortMetric);
  const rows = ordered.map(item => `
    <tr>
      <td>
        <span class="table-accent">${escapeHtml(item.agentId)}</span>
        <span class="table-sub">${escapeHtml(formatDate(item.latestActiveAt))}</span>
      </td>
      <td>${formatCompact(item.totalTokens)}</td>
      <td>${formatCompact(item.assistantTurns)}</td>
      <td>${formatCompact(item.avgTokensPerTurn)}</td>
      <td>${item.productiveShare}%</td>
      <td>${formatCompact(item.errorTokens)}</td>
    </tr>
  `);
  renderTable('agentTable', ['Bot', 'Token', '轮次', '单轮成本', '有效占比', '错误损耗'], rows, '没有可用的 Bot 数据。');
}

function renderModels(items) {
  const rows = items.slice(0, 8).map(item => `
    <tr>
      <td><span class="table-accent">${escapeHtml(item.model)}</span><span class="table-sub">${escapeHtml(item.provider)}</span></td>
      <td>${formatCompact(item.tokens)}</td>
      <td>${formatCompact(item.turns)}</td>
      <td>${formatCompact(item.avgTokensPerTurn)}</td>
    </tr>
  `);
  renderTable('modelTable', ['模型', 'Token', '轮次', '单轮成本'], rows, '当前窗口没有模型调用数据。');
}

function renderTopSessions(items) {
  const rows = items.slice(0, 10).map(item => `
    <tr>
      <td>
        <span class="table-accent">${escapeHtml(item.agentId)}</span>
        <span class="table-sub">${escapeHtml(item.project || item.workstream)}</span>
      </td>
      <td>${formatCompact(item.totalTokens)}</td>
      <td>${formatCompact(item.errorTokens)}</td>
      <td>${escapeHtml(item.workstream)}</td>
      <td>${escapeHtml(formatDate(item.lastActiveAt))}</td>
    </tr>
  `);
  renderTable('topTable', ['会话', 'Token', '错误', '类型', '最近活跃'], rows, '当前窗口没有高消耗会话。');
}

function barRow(item, index, totalKey = 'totalTokens') {
  const colors = ['fill-dark', 'fill-green', 'fill-blue', 'fill-amber', 'fill-red'];
  const color = colors[index % colors.length];
  return `
    <div class="bar-card">
      <div class="bar-head">
        <div class="bar-title">${escapeHtml(item.name)}</div>
        <div class="bar-meta">${formatCompact(item[totalKey])} · ${item.share || 0}%</div>
      </div>
      <div class="bar-track">
        <div class="bar-fill ${color}" style="width:${Math.max(item.share || 0, 1)}%"></div>
      </div>
    </div>
  `;
}

function renderEfficiency(overview) {
  const total = overview.totalTokens || 1;
  const runtime = overview.observedRuntimeTokens || 1;
  const rows = [
    { name: '生产交付', totalTokens: overview.productiveTokens, share: pct(overview.productiveTokens, total) },
    { name: '内部运维', totalTokens: overview.opsTokens, share: pct(overview.opsTokens, total) },
    { name: '错误暴露', totalTokens: overview.errorTokens, share: pct(overview.errorTokens, runtime) },
  ];
  document.getElementById('efficiencyBars').innerHTML = rows.map((row, index) => barRow(row, index)).join('');
}

function renderWorkstreams(items) {
  document.getElementById('workstreamBars').innerHTML = items.map((item, index) => barRow(item, index)).join('');
}

function renderInsights(items) {
  const host = document.getElementById('insightBox');
  if (!items.length) {
    host.innerHTML = '<div class="empty-state">暂无经营建议。</div>';
    return;
  }
  host.innerHTML = items.map(item => `
    <article class="insight-card">
      <h3>${escapeHtml(item.title)}</h3>
      <p>${escapeHtml(item.detail)}</p>
    </article>
  `).join('');
}

function renderAgentSelect(items) {
  if (!selectedAgent && items.length > 0) {
    allAgentOptions = [...items];
  } else if (!selectedAgent && items.length === 0) {
    allAgentOptions = [];
  } else if (!allAgentOptions.length && items.length > 0) {
    allAgentOptions = [...items];
  }

  const source = allAgentOptions.length ? allAgentOptions : items;
  const ordered = [...source].sort((a, b) => b.totalTokens - a.totalTokens);
  const picker = document.getElementById('agentSelect');
  const total = ordered.reduce((sum, item) => sum + (item.totalTokens || 0), 0);
  const options = [
    `<option value="" ${selectedAgent === '' ? 'selected' : ''}>全部 Bot · ${formatCompact(total)}</option>`,
    ...ordered.map(item => `
      <option value="${escapeHtml(item.agentId)}" ${item.agentId === selectedAgent ? 'selected' : ''}>
        ${escapeHtml(item.agentId)} · ${formatCompact(item.totalTokens)}
      </option>
    `),
  ];
  picker.innerHTML = options.join('');

  if (selectedAgent && !ordered.some(item => item.agentId === selectedAgent)) {
    selectedAgent = '';
    picker.value = '';
  }
}

async function loadDashboard() {
  try {
    const payload = await fetchJson(dashboardUrl());
    renderHeader(payload.overview);
    renderRuntimePanel(payload.overview);
    renderSummary(payload.overview);
    renderRisk(payload.overview, payload.risk);
    renderBotComparison(payload.agents || [], payload.projects || []);
    renderProjects(payload.projects || []);
    renderTopSessions(payload.topSessions || []);
    renderEfficiency(payload.overview);
    renderWorkstreams(payload.workstreams || []);
    renderAgents(payload.agents || []);
    renderModels(payload.models || []);
    renderInsights(payload.insights || []);
    renderAgentSelect(payload.agents || []);
  } catch (err) {
    console.error(err);
    document.getElementById('summaryCards').innerHTML = `<div class="empty-state">数据加载失败: ${escapeHtml(err.message)}</div>`;
  }
}

document.querySelectorAll('#rangeSwitcher button').forEach(button => {
  button.onclick = async () => {
    currentRange = button.dataset.range;
    document.querySelectorAll('#rangeSwitcher button').forEach(item => item.classList.toggle('active', item === button));
    await loadDashboard();
  };
});

document.getElementById('refreshNowBtn').onclick = () => loadDashboard();
document.getElementById('officeViewBtn').onclick = () => {
  window.open(STAR_OFFICE_URL, '_blank', 'noopener,noreferrer');
};

document.getElementById('agentSelect').onchange = async (event) => {
  selectedAgent = event.target.value;
  await loadDashboard();
};

document.querySelectorAll('#projectLimitGroup .chip-button').forEach(button => {
  button.onclick = async () => {
    projectLimit = button.dataset.projectLimit;
    document.querySelectorAll('#projectLimitGroup .chip-button').forEach(item => {
      item.classList.toggle('active', item === button);
    });
    await loadDashboard();
  };
});

setInterval(loadDashboard, 30000);
loadDashboard();
