"use client";

import { useState } from "react";
import { RadarIcon, SparkIcon, TrashIcon } from "./icons";
import { accountPlatformOptions, reportRanges } from "./mock-data";
import { getTimelineReportsByDate, getVisibleReportTimelineItems, shouldShowReportTimelineMore } from "../lib/report-timeline.js";

export function ContentTab({
  selectedDay,
  activePlatform,
  platformOptions,
  filteredItems,
  timelineFilterPlatform,
  timelineFilterKeyword,
  timelineFilterOptions,
  hasTimelineFilter,
  contentSearchDraft,
  contentSearchQuery,
  contentSearchLimitMode,
  contentSearchLimit,
  contentSearchResultCount,
  contentSearchDisplayedCount,
  contentSearchSourceLabel,
  contentSearchStatus,
  contentDays,
  contentMetrics,
  onSelectDate,
  onSelectPlatform,
  onTimelineFilterPlatformChange,
  onTimelineFilterKeywordChange,
  onContentSearchDraftChange,
  onContentSearchLimitModeChange,
  onContentSearchLimitChange,
  onContentSearchSubmit,
  onOpenReport,
}) {
  const isCustomContentSearchLimit = contentSearchLimitMode === "limited";
  const isSearching = contentSearchStatus === "loading";

  return (
    <section className="tab-body content-tab">
      <section className="trend-shell">
        <div className="trend-header">
          <div className="trend-header-main">
            <div className="trend-title-line">
              <h3>内容采集情况</h3>
              <p className="eyebrow trend-inline-eyebrow">最近 7 天趋势</p>
            </div>

            <div className="content-kpi-strip trend-kpi-strip">
              {contentMetrics.map((metric) => (
                <article key={metric.label} className="kpi-chip">
                  <span>{metric.label}</span>
                  <strong>{metric.value}</strong>
                </article>
              ))}
            </div>

            <div className="platform-select-wrap">
              <select value={activePlatform} onChange={(event) => onSelectPlatform(event.target.value)}>
                {platformOptions.map((platform) => (
                  <option key={platform} value={platform}>
                    {platform}
                  </option>
                ))}
              </select>
            </div>

            <div className="content-search-toolbar">
              <input
                value={contentSearchDraft}
                onChange={(event) => onContentSearchDraftChange(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    onContentSearchSubmit();
                  }
                }}
                placeholder="输入关键词后回车检索当前平台内容"
              />

              <select value={contentSearchLimitMode} onChange={(event) => onContentSearchLimitModeChange(event.target.value)}>
                <option value="all">不限量</option>
                <option value="limited">自定义</option>
              </select>

              <input
                className={`content-search-limit-input ${isCustomContentSearchLimit ? "" : "is-disabled"}`}
                inputMode="numeric"
                value={isCustomContentSearchLimit ? contentSearchLimit : ""}
                onChange={(event) => onContentSearchLimitChange(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    onContentSearchSubmit();
                  }
                }}
                placeholder={isCustomContentSearchLimit ? "输入数量" : "不限量"}
                disabled={!isCustomContentSearchLimit}
              />

              <button className="content-search-submit" type="button" onClick={onContentSearchSubmit} disabled={isSearching}>
                {isSearching ? "搜索中..." : "开始检索"}
              </button>
            </div>
          </div>
        </div>

        <div className="trend-card-row">
          {contentDays.map((day) => (
            <button
              key={day.date}
              type="button"
              className={`trend-card ${day.date === selectedDay.date ? "active" : ""}`}
              onClick={() => onSelectDate(day.date)}
            >
              <span>{day.label}</span>
              <strong>{day.total}篇</strong>
              <p>{shortenTopic(day.topic)}</p>
              <small>{day.reportReady ? "已出报告" : "未出报告"}</small>
            </button>
          ))}
        </div>
      </section>

      <div className="content-grid content-bottom-grid">
        <section className="panel scrolling-panel body-panel">
          <div className="section-head small-head">
            <div className={`content-timeline-headline search-status-${contentSearchStatus}`}>
              <span>{selectedDay.label} 内容时间线</span>
              {contentSearchQuery ? (
                <small className="content-search-result-copy">
                  检索词：{contentSearchQuery}
                  {contentSearchSourceLabel ? ` · 来源：${contentSearchSourceLabel}` : ""}
                  {contentSearchResultCount ? ` · 共 ${contentSearchResultCount} 条` : ""}
                  {contentSearchDisplayedCount ? ` · 当前展示 ${contentSearchDisplayedCount} 条` : ""}
                </small>
              ) : null}
              {hasTimelineFilter ? <small>已应用时间线筛选</small> : null}
            </div>

            <div className="content-timeline-toolbar">
              <select value={timelineFilterPlatform} onChange={(event) => onTimelineFilterPlatformChange(event.target.value)}>
                {timelineFilterOptions.map((platform) => (
                  <option key={platform} value={platform}>
                    {platform}
                  </option>
                ))}
              </select>
              <input
                value={timelineFilterKeyword}
                onChange={(event) => onTimelineFilterKeywordChange(event.target.value)}
                placeholder="筛选当前时间线关键词"
              />
            </div>

            <button className="pill ghost" type="button" onClick={onOpenReport}>
              查看对应报告
            </button>
          </div>

          <div className="timeline-stack">
            {filteredItems.length ? (
              filteredItems.map((item) => (
                <article key={item.id} className={`timeline-card ${String(item.tag || "").includes("爆") ? "hot" : ""}`}>
                  <div className="timeline-time">{item.time}</div>
                  <div className="timeline-content">
                    <div className="timeline-meta">
                      <span className={`platform-chip ${platformTone(item.platform)}`}>{item.platform}</span>
                      <span className="meta-line">热度 {item.heat}</span>
                      {item.tag ? <span className={`tag-chip ${item.isNewResult ? "new" : ""}`}>{item.tag}</span> : null}
                    </div>
                    <h4>{item.title}</h4>
                    <p>作者：{item.author} · {item.match}</p>
                    <p className="description">{item.description}</p>
                  </div>
                </article>
              ))
            ) : (
              <div className="empty-state">当前筛选条件下没有内容，可尝试切换平台、日期或关键词。</div>
            )}
          </div>
        </section>

        <aside className="summary-stack">
          <SummaryBlock title="今日关键词聚类">
            <div className="keyword-cloud">
              {(selectedDay.keywords || []).map((keyword) => (
                <span key={keyword}>{keyword}</span>
              ))}
            </div>
          </SummaryBlock>

          <SummaryBlock title="AI 判断">
            <p>{selectedDay.aiJudgement}</p>
          </SummaryBlock>

          <SummaryBlock title="建议动作">
            <ul>
              {(selectedDay.actions || []).map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </SummaryBlock>

          <SummaryBlock title="重点来源">
            <ul>
              {(selectedDay.authors || []).map((author) => (
                <li key={author}>{author}</li>
              ))}
            </ul>
          </SummaryBlock>
        </aside>
      </div>
    </section>
  );
}

export function ReportTab({
  reports,
  selectedReportId,
  onSelectReportId,
  selectedReport,
  reportRange,
  onSelectRange,
  reportTopics,
  reportScheduleTime,
  reportScheduleEnabled,
  reportAnalysisDate,
  onReportScheduleTimeChange,
  onReportScheduleEnabledChange,
  onReportAnalysisDateChange,
  reportKeywordDraft,
  onReportKeywordDraftChange,
  onRunKeywordReport,
  reportRunStatus,
  reportRunMessage,
  onOpenSettings,
}) {
  const [timelineExpanded, setTimelineExpanded] = useState(false);
  const activeReport =
    selectedReport ?? {
      id: "empty-report",
      label: "--/--",
      summary: "当前还没有可展示的分析报告",
      hotSummary: "请先等待每日任务生成，或在顶部执行一次定向报告分析。",
      metrics: { hotContent: 0, topics: 0, highPriority: 0, suggestedPlatform: "--" },
      topics: [],
      articleSummaries: [],
      generatedAtLabel: "--",
      hotContentCount: 0,
      analyzedCount: 0,
      mode: "daily",
      keywordTarget: "",
    };
  const timelineReports = getTimelineReportsByDate(
    reports.map((report, index) => ({
      ...report,
      _safeId: report.id || `${report.reportDate || report.date || report.label || "report"}-${index}`,
      trendLabel: getReportTrendLabel(report),
    })),
  ).map((report, index) => ({
    ...report,
    relativeLabel: getReportRelativeLabel(index),
  }));
  const visibleTimelineReports = getVisibleReportTimelineItems(timelineReports, timelineExpanded);
  const showTimelineMore = shouldShowReportTimelineMore(timelineReports);
  const isKeywordAnalyzing = reportRunStatus === "loading";
  const activeReportDate = activeReport.reportDate || activeReport.date || "";

  return (
    <section className="tab-body report-v2">
      <section className="panel report-timeline-shell">
        <div className="report-timeline-head">
          <h3 className="report-timeline-title">报告时间线</h3>
          {showTimelineMore ? (
            <button
              type="button"
              className="pill ghost report-timeline-more"
              onClick={() => setTimelineExpanded((current) => !current)}
            >
              {timelineExpanded ? "收起" : "更多"}
            </button>
          ) : null}
        </div>

        <div className="report-timeline-row">
          {visibleTimelineReports.map((report) => (
            <button
              key={report._safeId}
              type="button"
              className={`report-timeline-card ${
                report._safeId === selectedReportId || report.id === selectedReportId || report.reportDate === activeReportDate
                  ? "active"
                  : ""
              }`}
              onClick={() => onSelectReportId(report.id || report._safeId)}
            >
              <div className="report-timeline-top">
                <div className="report-timeline-date">
                  <strong>{report.label}</strong>
                  <span>{report.relativeLabel}</span>
                </div>
                <em>{report.trendLabel}</em>
              </div>

              <p>{report.summary}</p>

              <div className="report-timeline-meta">
                <span>{report.topicCount} 个选题</span>
                <span>{report.hotContentCount} 条热点</span>
              </div>
            </button>
          ))}
        </div>
      </section>

      <div className="report-v2-grid">
        <section className="report-v2-main">
          <article className="panel report-detail-toolbar-panel">
            <div className="report-detail-toolbar">
              <div className="report-detail-toolbar-section report-detail-toolbar-single-row">
                <label className="report-toolbar-field report-toolbar-date-field">
                  <span>分析日期</span>
                  <input type="date" value={reportAnalysisDate} onChange={(event) => onReportAnalysisDateChange(event.target.value)} />
                </label>

                <label className="report-toolbar-field report-toolbar-time-field">
                  <span>每日分析时间</span>
                  <input type="time" value={reportScheduleTime} onChange={(event) => onReportScheduleTimeChange(event.target.value)} />
                </label>

                <div className="report-toolbar-toggle-field report-toolbar-toggle-col">
                  <span>定时分析</span>
                  <button
                    type="button"
                    className={`report-toolbar-switch ${reportScheduleEnabled ? "is-on" : "is-off"}`}
                    aria-pressed={reportScheduleEnabled}
                    aria-label="定时分析开关"
                    onClick={() => onReportScheduleEnabledChange(!reportScheduleEnabled)}
                  >
                    <span className="report-toolbar-switch-track">
                      <span className="report-toolbar-switch-thumb" />
                    </span>
                  </button>
                </div>

                <label className="report-toolbar-field report-toolbar-keyword-field keyword-field inline-field">
                  <span>定向报告分析</span>
                  <input
                    value={reportKeywordDraft}
                    onChange={(event) => onReportKeywordDraftChange(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        event.preventDefault();
                        onRunKeywordReport();
                      }
                    }}
                    placeholder="输入关键词后分析该关键词报告"
                  />
                </label>

                <div className="report-toolbar-action-field report-toolbar-action-col">
                  <span aria-hidden="true">分析操作</span>
                  <button className="pill primary" type="button" onClick={onRunKeywordReport} disabled={isKeywordAnalyzing}>
                    {isKeywordAnalyzing ? "正在分析中..." : "分析关键词"}
                  </button>
                </div>
              </div>
            </div>

            {reportRunMessage || isKeywordAnalyzing ? (
              <p className={`report-run-feedback ${reportRunStatus}`}>{isKeywordAnalyzing ? "正在分析中..." : reportRunMessage}</p>
            ) : null}
          </article>

          <article className="panel report-overview-panel">
            <p className="report-panel-kicker">昨日热点摘要</p>
            <h3>{activeReport.summary}</h3>
            <p className="report-overview-copy">{activeReport.hotSummary}</p>

            <div className="report-overview-meta">
              <span>{activeReport.mode === "keyword" ? "定向关键词报告" : "每日自动报告"}</span>
              {activeReport.keywordTarget ? <span>关键词：{activeReport.keywordTarget}</span> : null}
              <span>生成时间：{activeReport.generatedAtLabel || "--"}</span>
              <span>分析文章：{activeReport.analyzedCount || activeReport.hotContentCount || 0} 篇</span>
            </div>

            <div className="report-overview-metrics">
              <MetricCard label="热点内容数" value={activeReport.metrics.hotContent} />
              <MetricCard label="新增选题数" value={activeReport.metrics.topics} />
              <MetricCard label="高优先级选题" value={activeReport.metrics.highPriority} />
              <MetricCard label="适合平台" value={activeReport.metrics.suggestedPlatform} />
            </div>
          </article>

          <article className="panel report-topic-panel">
            <div className="report-topic-panel-head">
              <div>
                <h3>今日 AI 产出的选题方向</h3>
                <p>基于高热内容与热点变化自动生成</p>
              </div>
              <button className="pill ghost" type="button" onClick={onOpenSettings}>
                调整监控设置
              </button>
            </div>

            <div className="report-topic-stack">
              {activeReport.topics.length ? (
                activeReport.topics.map((topic) => (
                  <article key={topic.id} className="report-topic-card">
                    <div className="report-topic-card-head">
                      <div className="report-topic-title-block">
                        <strong>{topic.title}</strong>
                        <div className="report-topic-tags">
                          <span className={`status-chip ${String(topic.priority || "").includes("高") ? "good" : "neutral"}`}>
                            {topic.priority}
                          </span>
                          {buildSourceTags(topic.source).map((tag, index) => (
                            <span key={`${topic.id}-${tag}-${index}`} className="tag-chip subtle">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    <p className="report-topic-intro">{topic.source}</p>

                    <div className="report-topic-body">
                      <div className="report-topic-copy-block">
                        <span>为什么做</span>
                        <p>{topic.reason}</p>
                      </div>
                      <div className="report-topic-copy-block">
                        <span>爆点与增长空间</span>
                        <p>{topic.growth}</p>
                      </div>
                    </div>

                    <div className="report-topic-actions">
                      <button type="button" className="text-action">
                        查看详情
                      </button>
                      <button type="button" className="text-action">
                        加入选题池
                      </button>
                      <button type="button" className="text-action primary-link">
                        生成提纲
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <div className="empty-state">当前日期还没有生成选题方向，可先调整日期或执行一次关键词分析。</div>
              )}
            </div>
          </article>

          {activeReport.articleSummaries?.length ? (
            <article className="panel report-source-panel">
              <div className="report-topic-panel-head">
                <div>
                  <h3>Top 文章结构化摘录</h3>
                  <p>用于支撑本次选题分析的文章摘要、关键词和亮点信息。</p>
                </div>
              </div>

              <div className="report-source-stack">
                {activeReport.articleSummaries.map((article, index) => (
                  <article key={article.articleId || `${article.title}-${index}`} className="report-source-card">
                    <div className="report-source-card-head">
                      <strong>{article.title}</strong>
                      <span className="tag-chip subtle">{article.platform}</span>
                    </div>
                    <p className="report-source-summary">{article.summary}</p>
                    <div className="report-source-keywords">
                      {(article.keywords || []).map((keyword, keywordIndex) => (
                        <span key={`${article.articleId || article.title}-${keyword}-${keywordIndex}`} className="tag-chip subtle">
                          {keyword}
                        </span>
                      ))}
                    </div>
                    {article.highlights?.length ? (
                      <ul className="report-source-points">
                        {article.highlights.map((highlight, highlightIndex) => (
                          <li key={`${article.articleId || article.title}-${highlightIndex}`}>{highlight}</li>
                        ))}
                      </ul>
                    ) : null}
                  </article>
                ))}
              </div>
            </article>
          ) : null}
        </section>

        <aside className="report-v2-side">
          <section className="panel report-pool-panel">
            <p className="report-panel-kicker">选题维度汇总</p>
            <h3>最近一段时间内的所有选题</h3>
            <p className="report-pool-copy">按时间范围聚合近期高潜方向与重复出现的选题</p>

            <div className="report-range-group">
              {reportRanges.map((range) => (
                <button
                  key={range.id}
                  type="button"
                  className={`chip ${reportRange === range.id ? "active" : ""}`}
                  onClick={() => onSelectRange(range.id)}
                >
                  {range.label}
                </button>
              ))}
            </div>

            <p className="report-pool-hint">已聚合 {reportTopics.length} 个核心方向</p>

            <div className="report-pool-list">
              {reportTopics.length ? (
                reportTopics.map((topic, index) => (
                  <article key={topic.id || `${topic.title}-${index}`} className="report-pool-item">
                    <div className="report-pool-item-head">
                      <strong>{topic.title}</strong>
                      <span className={`status-chip ${String(topic.priority || "").includes("高") ? "good" : "neutral"}`}>
                        {topic.priority}
                      </span>
                    </div>

                    <div className="report-pool-tags">
                      {topic.targetPlatform ? <span className="tag-chip subtle">{topic.targetPlatform}</span> : null}
                      {buildSourceTags(topic.source).map((tag, tagIndex) => (
                        <span key={`${topic.id || topic.title}-pool-${tag}-${tagIndex}`} className="tag-chip subtle">
                          {tag}
                        </span>
                      ))}
                    </div>

                    <p>{topic.reason}</p>

                    <div className="report-pool-meta">
                      <span>{topic.source}</span>
                      <span>{getHeatLabel(topic.priority)}</span>
                    </div>
                  </article>
                ))
              ) : (
                <div className="empty-state">当前时间范围内还没有聚合选题，可先切换日期或执行分析。</div>
              )}
            </div>
          </section>
        </aside>
      </div>
    </section>
  );
}

export function SettingsTab({
  category,
  scheduleRunTime,
  keywordDraft,
  onKeywordDraftChange,
  onAddKeyword,
  onRemoveKeyword,
  accountDraft,
  onAccountDraftChange,
  onAddAccount,
  onRemoveAccount,
  onTogglePlatform,
  onStrategyChange,
  onSaveSettings,
  onBackToContent,
}) {
  const enabledPlatformCount = category.platforms.filter((platform) => platform.enabled).length;
  const strategySummary = `${scheduleRunTime} / ${category.strategy.window}`;
  const [accountInlineError, setAccountInlineError] = useState("");

  function handleKeywordRemove(keyword) {
    const confirmed = window.confirm(`确认删除关键词“${keyword}”吗？`);
    if (!confirmed) return;
    onRemoveKeyword(keyword);
  }

  function handleAccountSubmit() {
    if (!accountDraft.name.trim()) {
      setAccountInlineError("请输入账号名称后再添加");
      return;
    }

    setAccountInlineError("");
    onAddAccount();
  }

  return (
    <section className="tab-body settings-layout settings-layout-fixed">
      <div className="settings-toolbar">
        <button className="pill ghost" type="button" onClick={onBackToContent}>
          返回内容查看
        </button>
        <button className="pill primary" type="button" onClick={onSaveSettings}>
          保存当前配置
        </button>
      </div>

      <div className="settings-content-stack">
        <section className="panel settings-summary-strip">
          <article className="settings-summary-item">
            <span>已选平台</span>
            <strong>{enabledPlatformCount} 个</strong>
          </article>
          <article className="settings-summary-item">
            <span>关键词</span>
            <strong>{category.keywords.length} 个</strong>
          </article>
          <article className="settings-summary-item">
            <span>对标账号</span>
            <strong>{category.accounts.length} 个</strong>
          </article>
          <article className="settings-summary-item wide">
            <span>当前执行策略</span>
            <strong>每日 {strategySummary}</strong>
          </article>
        </section>

        <section className="panel settings-tier settings-tier-primary">
          <div className="settings-primary-grid">
            <section className="settings-module settings-platform-module">
              <div className="settings-module-head">
                <div className="settings-module-copy">
                  <h4>监控平台</h4>
                </div>
                <div className="settings-module-meta">
                  <span className="status-chip neutral">支持多选</span>
                  <span className="caption">已选择 {enabledPlatformCount} 个平台</span>
                </div>
              </div>

              <div className="settings-platform-grid">
                {category.platforms.map((platform) => (
                  <button
                    key={platform.id}
                    type="button"
                    className={`settings-platform-option ${platform.enabled ? "active" : ""}`}
                    onClick={() => onTogglePlatform(platform.id)}
                  >
                    <span className="platform-icon settings-platform-icon">{platform.short}</span>
                    <div className="settings-platform-copy">
                      <strong>{platform.name}</strong>
                      <span>{platform.description}</span>
                    </div>
                    <span className="settings-platform-check">{platform.enabled ? "✓" : ""}</span>
                  </button>
                ))}
              </div>
            </section>

            <section className="settings-module settings-keyword-module">
              <div className="settings-module-head">
                <div className="settings-module-copy">
                  <h4>对标关键词</h4>
                </div>
                <div className="settings-module-meta">
                  <span className="caption">已添加 {category.keywords.length} 个关键词</span>
                </div>
              </div>

              <div className="settings-input-row">
                <input
                  value={keywordDraft}
                  onChange={(event) => onKeywordDraftChange(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      onAddKeyword();
                    }
                  }}
                  placeholder="输入关键词后点击添加"
                />
                <button className="pill primary" type="button" onClick={onAddKeyword}>
                  添加
                </button>
              </div>

              <div className="settings-keyword-list">
                {category.keywords.map((keyword, index) => (
                  <span key={keyword} className={`settings-keyword-token ${getKeywordTone(index)}`}>
                    <span className={`settings-keyword-icon ${getKeywordTone(index)}`} aria-hidden="true">
                      {getKeywordTone(index) === "core" ? <SparkIcon /> : <RadarIcon />}
                    </span>
                    <strong>{keyword}</strong>
                    <button
                      type="button"
                      className="settings-keyword-remove"
                      onClick={() => handleKeywordRemove(keyword)}
                      aria-label={`删除关键词 ${keyword}`}
                    >
                      <TrashIcon />
                    </button>
                  </span>
                ))}
              </div>
            </section>

            <section className="settings-module settings-account-module">
              <div className="settings-module-head">
                <div className="settings-module-copy">
                  <h4>对标博主 / 账号</h4>
                </div>
                <div className="settings-module-meta">
                  <span className="caption">已添加 {category.accounts.length} 个账号</span>
                </div>
              </div>

              <div className="settings-account-toolbar">
                <input
                  value={accountDraft.name}
                  onChange={(event) => {
                    onAccountDraftChange((current) => ({ ...current, name: event.target.value }));
                    if (accountInlineError) {
                      setAccountInlineError("");
                    }
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      handleAccountSubmit();
                    }
                  }}
                  placeholder="搜索或输入账号名称"
                />
                <select
                  value={accountDraft.platform}
                  onChange={(event) => onAccountDraftChange((current) => ({ ...current, platform: event.target.value }))}
                >
                  {accountPlatformOptions.map((platform) => (
                    <option key={platform} value={platform}>
                      {platform}
                    </option>
                  ))}
                </select>
                <button className="pill primary" type="button" onClick={handleAccountSubmit}>
                  添加账号
                </button>
              </div>

              {accountInlineError ? <p className="settings-inline-error">{accountInlineError}</p> : null}

              <div className="settings-account-list">
                {category.accounts.length ? (
                  category.accounts.map((account) => (
                    <article key={account.id} className="settings-account-item">
                      <div className="settings-account-main">
                        <span className="avatar settings-account-avatar">{account.avatar}</span>
                        <div className="settings-account-copy">
                          <div className="settings-account-title-row">
                            <strong>{account.name}</strong>
                            <span className="tag-chip subtle">{account.platform}</span>
                          </div>
                          <p>{account.lastFetched}</p>
                        </div>
                      </div>

                      <div className="settings-account-tags">
                        <span className="status-chip neutral">{account.signal}</span>
                        <span className="status-chip good">{account.status}</span>
                      </div>

                      <div className="settings-account-actions">
                        <button className="settings-action-chip" type="button">
                          查看内容
                        </button>
                        <button className="settings-action-chip" type="button">
                          重新抓取
                        </button>
                        <button className="settings-danger-action" type="button" onClick={() => onRemoveAccount(account.id)}>
                          删除
                        </button>
                      </div>
                    </article>
                  ))
                ) : (
                  <div className="empty-state">当前还没有对标账号，可以先添加几个重点博主。</div>
                )}
              </div>
            </section>
          </div>
        </section>

        <section className="panel settings-tier settings-tier-secondary">
          <div className="settings-tier-head">
            <div>
              <p className="eyebrow">第二层配置</p>
              <h3>运行策略与 AI 输出</h3>
            </div>
            <span className="status-chip neutral">每日自动执行</span>
          </div>

          <div className="settings-strategy-grid">
            <label className="settings-field">
              <span>运行时间</span>
              <input type="time" value={scheduleRunTime} onChange={(event) => onStrategyChange("runTime", event.target.value)} />
            </label>
            <label className="settings-field">
              <span>采集范围</span>
              <input value={category.strategy.window} onChange={(event) => onStrategyChange("window", event.target.value)} />
            </label>
            <label className="settings-field">
              <span>分析规则</span>
              <input
                type="number"
                min="1"
                max="50"
                value={category.strategy.topN}
                onChange={(event) => onStrategyChange("topN", Number(event.target.value))}
              />
            </label>
            <label className="settings-field">
              <span>输出结果</span>
              <input value={category.strategy.output} onChange={(event) => onStrategyChange("output", event.target.value)} />
            </label>
          </div>
        </section>
      </div>
    </section>
  );
}

function MetricCard({ label, value }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function SummaryBlock({ title, children }) {
  return (
    <section className="summary-block">
      <p className="eyebrow">{title}</p>
      {children}
    </section>
  );
}

function shortenTopic(topic) {
  const normalized = String(topic || "").trim();
  if (!normalized) return "暂无主题";
  return normalized.length > 18 ? `${normalized.slice(0, 18)}...` : normalized;
}

function platformTone(platform) {
  if (platform === "公众号") return "wechat";
  if (platform === "小红书") return "xhs";
  if (platform === "抖音") return "douyin";
  if (platform === "B站") return "bilibili";
  if (platform === "微博") return "weibo";
  return "zhihu";
}

function getReportRelativeLabel(index) {
  if (index === 0) return "今天";
  if (index === 1) return "昨天";
  if (index === 2) return "前天";
  return "历史";
}

function getReportTrendLabel(report) {
  const summary = String(report?.summary || "");
  if (report?.mode === "keyword") return "定向分析";
  if (summary.includes("工作流")) return "工作流";
  if (summary.includes("Agent")) return "多 Agent";
  if (summary.includes("对比") || summary.includes("成本")) return "对比测评";
  if (summary.includes("案例")) return "案例向";
  return "日报";
}

function buildSourceTags(source) {
  return String(source || "")
    .replace("适合平台：", "")
    .split(/[·,/，]/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 3);
}

function getHeatLabel(priority) {
  const value = String(priority || "");
  if (value.includes("高")) return "高潜";
  if (value.includes("中")) return "中高";
  return "观察";
}

function getKeywordTone(index) {
  return index < 3 ? "core" : "expand";
}
