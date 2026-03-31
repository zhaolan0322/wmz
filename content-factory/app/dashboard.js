"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { seedCategories } from "./mock-data";
import { ContentTab, ReportTab, SettingsTab } from "./tab-sections";
import { CogIcon, EditIcon, LayoutIcon, SparkIcon, TrashIcon } from "./icons";

const topTabs = [
  { id: "content", label: "内容", icon: LayoutIcon },
  { id: "report", label: "选题分析与报告", icon: SparkIcon },
  { id: "settings", label: "监控设置", icon: CogIcon },
];

const MANUAL_SEARCH_STORAGE_KEY = "content-factory-manual-search-results";
const SEARCH_CACHE_STORAGE_KEY = "content-factory-search-cache";
const SEARCH_READY_PLATFORMS = ["小红书", "公众号"];
const DEFAULT_BANNER_TEXT = "原型数据已预填充，可直接切换分类、平台、日期和设置项查看交互。";
const NEW_RESULT_VISIBLE_MS = 12 * 60 * 60 * 1000;

export default function Dashboard() {
  const [categories, setCategories] = useState(seedCategories);
  const [selectedCategoryId, setSelectedCategoryId] = useState(seedCategories[0].id);
  const [activeTab, setActiveTab] = useState("content");
  const [activePlatform, setActivePlatform] = useState(getDefaultSearchPlatform(seedCategories[0]));
  const [selectedDate, setSelectedDate] = useState("");
  const [selectedReportId, setSelectedReportId] = useState("");
  const [reportRange, setReportRange] = useState("7");
  const [persistedReportsByCategory, setPersistedReportsByCategory] = useState({});
  const [reportScheduleTime, setReportScheduleTime] = useState("08:30");
  const [reportScheduleEnabled, setReportScheduleEnabled] = useState(true);
  const [reportAnalysisDate, setReportAnalysisDate] = useState("");
  const [reportKeywordDraft, setReportKeywordDraft] = useState("");
  const [reportRunStatus, setReportRunStatus] = useState("idle");
  const [reportRunMessage, setReportRunMessage] = useState("");
  const [contentSearchDraft, setContentSearchDraft] = useState("");
  const [contentSearchLimitMode, setContentSearchLimitMode] = useState("all");
  const [contentSearchLimit, setContentSearchLimit] = useState("10");
  const [timelineFilterPlatform, setTimelineFilterPlatform] = useState("全部");
  const [timelineFilterKeyword, setTimelineFilterKeyword] = useState("");
  const [contentSearchStatus, setContentSearchStatus] = useState("idle");
  const [contentSearchFeedback, setContentSearchFeedback] = useState("");
  const [manualSearchResultsByScope, setManualSearchResultsByScope] = useState({});
  const [contentSearchCache, setContentSearchCache] = useState({});
  const [keywordDraft, setKeywordDraft] = useState("");
  const [accountDraft, setAccountDraft] = useState({ name: "", platform: "小红书" });
  const [banner, setBanner] = useState(DEFAULT_BANNER_TEXT);
  const [contentScrollTop, setContentScrollTop] = useState(0);
  const [trendExpanded, setTrendExpanded] = useState(false);
  const [isPending, startTransition] = useTransition();
  const scrollRegionRef = useRef(null);

  const categoryViews = categories.map((category) =>
    buildCategoryViewModel(category, persistedReportsByCategory[category.id], getSearchStatesForCategory(manualSearchResultsByScope, category.id)),
  );
  const selectedCategory = categoryViews.find((item) => item.id === selectedCategoryId) ?? categoryViews[0];
  const allContentDays = selectedCategory.contentDays;
  const displayContentDays = allContentDays.slice(0, 7);
  const selectedDay =
    displayContentDays.find((day) => day.date === selectedDate) ??
    displayContentDays[0] ??
    allContentDays[0] ??
    createEmptyContentDay(reportAnalysisDate || selectedDate || getTodayDateKey());
  const reportList = selectedCategory.reports;
  const selectedReport = reportList.find((report) => report.id === selectedReportId) ?? reportList[0];
  const enabledPlatforms = selectedCategory.platforms.filter((item) => item.enabled);
  const effectiveRunTime = normalizeTimeInput(reportScheduleTime || selectedCategory.strategy.runTime || "08:30");
  const currentSearchScopeKey = `${selectedCategoryId}:${selectedDate}`;
  const currentSearchState = manualSearchResultsByScope[currentSearchScopeKey] ?? {
    keyword: "",
    results: [],
    returnedCount: 0,
    totalCount: 0,
    sourceLabel: "",
  };
  const mergedDayItems = mergeTimelineItems(currentSearchState.results, selectedDay?.items ?? [], selectedDate);
  const platformOptions = buildPlatformOptions(enabledPlatforms);
  const contentDisplayItems = finalizeTimelineItems(mergedDayItems);
  const timelineFilterOptions = buildTimelineFilterOptions(contentDisplayItems);
  const filteredTimelineItems = filterTimelineItems(contentDisplayItems, timelineFilterPlatform, timelineFilterKeyword);
  const reportTopics = getTopicsInRange(reportList, reportRange);
  const contentMetrics = [
    { label: "今日采集", value: selectedDay.total },
    { label: "热点内容", value: selectedDay.hotCount },
    { label: "覆盖平台", value: enabledPlatforms.length },
    { label: "活跃博主", value: selectedCategory.accounts.length },
  ];
  const isToolBarPinned = contentScrollTop > 18;
  const isTrendCondensed = contentScrollTop > 120;

  useEffect(() => {
    setSelectedDate("");
    setSelectedReportId("");
    setActivePlatform(getDefaultSearchPlatform(selectedCategory));
    setReportAnalysisDate("");
    setReportScheduleEnabled(true);
    setReportKeywordDraft("");
    setReportRunStatus("idle");
    setReportRunMessage("");
    setContentSearchDraft("");
    setContentSearchLimitMode("all");
    setContentSearchLimit("10");
    setTimelineFilterPlatform("全部");
    setTimelineFilterKeyword("");
    setContentSearchStatus("idle");
    setContentSearchFeedback("");
    setTrendExpanded(false);
    setContentScrollTop(0);
    if (scrollRegionRef.current) {
      scrollRegionRef.current.scrollTo({ top: 0 });
    }
  }, [selectedCategoryId]);

  useEffect(() => {
    if (!displayContentDays.length) return;
    if (!selectedDate || !displayContentDays.some((day) => day.date === selectedDate)) {
      setSelectedDate(displayContentDays[0].date);
    }
  }, [displayContentDays, selectedDate]);

  useEffect(() => {
    if (!reportAnalysisDate && selectedDate) {
      setReportAnalysisDate(selectedDate);
    }
  }, [reportAnalysisDate, selectedDate]);

  useEffect(() => {
    if (!reportList.length) {
      if (selectedReportId) {
        setSelectedReportId("");
      }
      return;
    }

    if (!selectedReportId || !reportList.some((report) => report.id === selectedReportId)) {
      setSelectedReportId(reportList[0].id);
    }
  }, [reportList, selectedReportId]);

  useEffect(() => {
    let cancelled = false;

    async function loadReportData() {
      try {
        const [reportsResponse, scheduleResponse, snapshotsResponse] = await Promise.all([
          fetch(`/api/report-analysis/reports?categoryId=${encodeURIComponent(selectedCategoryId)}`),
          fetch("/api/report-analysis/schedule"),
          fetch(`/api/search-snapshots?categoryId=${encodeURIComponent(selectedCategoryId)}&limit=7`),
        ]);

        const [reportsPayload, schedulePayload, snapshotsPayload] = await Promise.all([
          reportsResponse.json(),
          scheduleResponse.json(),
          snapshotsResponse.json(),
        ]);

        if (!cancelled && reportsResponse.ok) {
          setPersistedReportsByCategory((current) => ({
            ...current,
            [selectedCategoryId]: Array.isArray(reportsPayload?.data) ? reportsPayload.data : [],
          }));
        }

        if (!cancelled && scheduleResponse.ok) {
          setReportScheduleTime(schedulePayload?.data?.dailyRunTime || "08:30");
          setReportScheduleEnabled(schedulePayload?.data?.enabled !== false);
        }

        if (!cancelled && snapshotsResponse.ok) {
          const snapshotStates = Array.isArray(snapshotsPayload?.data) ? snapshotsPayload.data : [];
          setManualSearchResultsByScope((current) => {
            const next = { ...current };

            Object.keys(next).forEach((scopeKey) => {
              if (scopeKey.startsWith(`${selectedCategoryId}:`)) {
                delete next[scopeKey];
              }
            });

            snapshotStates.forEach((state) => {
              next[`${selectedCategoryId}:${state.date}`] = state;
            });

            return next;
          });

          if (snapshotStates[0]?.date) {
            setSelectedDate(snapshotStates[0].date);
            setReportAnalysisDate(snapshotStates[0].date);
          }
        }
      } catch {}
    }

    loadReportData();

    return () => {
      cancelled = true;
    };
  }, [selectedCategoryId]);

  useEffect(() => {
    if (!platformOptions.includes(activePlatform)) {
      setActivePlatform(getDefaultSearchPlatform(selectedCategory));
    }
  }, [activePlatform, platformOptions, selectedCategory]);

  useEffect(() => {
    const node = scrollRegionRef.current;
    if (!node) return undefined;

    const onScroll = () => setContentScrollTop(node.scrollTop);
    node.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => node.removeEventListener("scroll", onScroll);
  }, [activeTab]);

  useEffect(() => {
    if (!isTrendCondensed) {
      setTrendExpanded(false);
    }
  }, [isTrendCondensed]);

  useEffect(() => {
    saveStoredJson(MANUAL_SEARCH_STORAGE_KEY, manualSearchResultsByScope);
  }, [manualSearchResultsByScope]);

  useEffect(() => {
    saveStoredJson(SEARCH_CACHE_STORAGE_KEY, contentSearchCache);
  }, [contentSearchCache]);

  useEffect(() => {
    setManualSearchResultsByScope(loadStoredJson(MANUAL_SEARCH_STORAGE_KEY, {}));
    setContentSearchCache(loadStoredJson(SEARCH_CACHE_STORAGE_KEY, {}));
  }, []);

  function updateSelectedCategory(updater) {
    setCategories((current) =>
      current.map((category) => (category.id === selectedCategoryId ? updater(category) : category)),
    );
  }

  function handleRunNow() {
    startTransition(() => {
      updateSelectedCategory((category) => ({
        ...category,
        lastRun: "刚刚完成模拟运行",
        status: "刚刚刷新",
      }));
    });
    setBanner("已模拟执行一次抓取和 AI 分析，当前分类的最近运行时间已更新。");
  }

  function handleCreateCategory() {
    const nextIndex = categories.length + 1;
    const newCategory = {
      id: `custom-${Date.now()}`,
      name: `新建监控分类 ${nextIndex}`,
      subtitle: "复制模板后可继续调整",
      status: "待配置",
      runStatus: "未启动",
      lastRun: "尚未运行",
      platforms: seedCategories[0].platforms.map((platform) => ({ ...platform })),
      keywords: [],
      accounts: [],
      strategy: { ...seedCategories[0].strategy },
      contentDays: [],
      reports: [],
    };
    setCategories((current) => [newCategory, ...current]);
    setSelectedCategoryId(newCategory.id);
    setActiveTab("settings");
    setBanner("已创建一个新的监控分类，先去监控设置里补充平台、关键词和账号。");
  }

  function handleDeleteCategory(categoryId) {
    if (categories.length === 1) {
      setBanner("至少需要保留一个监控分类，无法删除最后一个。");
      return;
    }

    const target = categories.find((category) => category.id === categoryId);
    const confirmed = window.confirm(`确认删除“${target?.name ?? "当前分类"}”？删除后当前原型中的该分类会立即移除。`);
    if (!confirmed) {
      return;
    }

    const remaining = categories.filter((category) => category.id !== categoryId);
    setCategories(remaining);
    if (selectedCategoryId === categoryId) {
      setSelectedCategoryId(remaining[0].id);
      setActiveTab("content");
    }
    setBanner("已删除一个监控分类。");
  }

  function handleRenameCategory(categoryId) {
    const target = categories.find((category) => category.id === categoryId);
    const nextName = window.prompt("请输入新的分类名称", target?.name ?? "");
    const value = nextName?.trim();

    if (!value || value === target?.name) {
      return;
    }

    setCategories((current) =>
      current.map((category) => (category.id === categoryId ? { ...category, name: value } : category)),
    );
    setBanner(`已重命名分类：${value}`);
  }

  function handleAddKeyword() {
    const value = keywordDraft.trim();
    if (!value) {
      setBanner("请输入关键词后再添加。");
      return;
    }
    if (selectedCategory.keywords.includes(value)) {
      setBanner("这个关键词已经存在。");
      return;
    }
    updateSelectedCategory((category) => ({
      ...category,
      keywords: [...category.keywords, value],
    }));
    setKeywordDraft("");
    setBanner(`已添加关键词：${value}`);
  }

  function handleRemoveKeyword(keyword) {
    updateSelectedCategory((category) => ({
      ...category,
      keywords: category.keywords.filter((item) => item !== keyword),
    }));
    setBanner(`已移除关键词：${keyword}`);
  }

  function handleTogglePlatform(platformId) {
    const targetName = selectedCategory.platforms.find((platform) => platform.id === platformId)?.name;
    updateSelectedCategory((category) => ({
      ...category,
      platforms: category.platforms.map((platform) =>
        platform.id === platformId ? { ...platform, enabled: !platform.enabled } : platform,
      ),
    }));
    if (targetName === activePlatform) {
      setActivePlatform(getDefaultSearchPlatform(selectedCategory, targetName));
    }
  }

  async function handleContentSearchSubmit() {
    const keyword = contentSearchDraft.trim();
    if (!keyword) {
      setBanner("请输入关键词后再检索。");
      setContentSearchFeedback("请输入关键词后再检索。");
      return;
    }

    if (!platformOptions.includes(activePlatform)) {
      const nextPlatform = getDefaultSearchPlatform(selectedCategory);
      setActivePlatform(nextPlatform);
      setContentSearchStatus("error");
      setContentSearchFeedback("error");
      setBanner(`当前仅允许检索已接通的平台，已切换为${nextPlatform}。`);
      return;
    }

    const requestLimit =
      contentSearchLimitMode === "limited" ? Math.max(1, Number.parseInt(contentSearchLimit || "1", 10) || 1) : null;
    const searchTargetDate = getTodayDateKey();
    const searchScopeKey = `${selectedCategoryId}:${searchTargetDate}`;
    const cacheKey = buildSearchCacheKey({
      platform: activePlatform,
      keyword,
      limitMode: contentSearchLimitMode,
      limit: requestLimit,
    });
    const cachedResult = contentSearchCache[cacheKey] ?? loadStoredJson(SEARCH_CACHE_STORAGE_KEY, {})[cacheKey];

    setContentSearchStatus("loading");
    setContentSearchFeedback(cachedResult ? "cache-hit" : "loading");

    if (cachedResult) {
      const nextResults = Array.isArray(cachedResult?.data?.items) ? cachedResult.data.items : [];
      const sourceLabel = cachedResult?.data?.sourceLabel || "公众号";
      const totalCount = Number(cachedResult?.data?.totalCount ?? nextResults.length);
      const searchScopeState = manualSearchResultsByScope[searchScopeKey] ?? {
        keyword: "",
        results: [],
        returnedCount: 0,
        totalCount: 0,
        sourceLabel: "",
      };
      const existingKeys = new Set(searchScopeState.results.map(getTimelineDedupKey));
      const uniqueNextResults = nextResults.filter((item) => !existingKeys.has(getTimelineDedupKey(item)));
      const mergedResults = mergeSearchResults(searchScopeState.results, nextResults);

      setContentSearchCache((current) => ({
        ...current,
        [cacheKey]: {
          data: {
            items: nextResults,
            sourceLabel,
            totalCount,
          },
          cachedAt: Date.now(),
        },
      }));

      setManualSearchResultsByScope((current) => ({
        ...current,
        [searchScopeKey]: {
          keyword,
          results: mergedResults,
          returnedCount: uniqueNextResults.length,
          totalCount,
          sourceLabel,
        },
      }));
      setSelectedDate(searchTargetDate);

      if (activePlatform !== sourceLabel && platformOptions.includes(sourceLabel)) {
        setActivePlatform(sourceLabel);
      }

      setBanner(DEFAULT_BANNER_TEXT);
      setContentSearchFeedback("cache-hit");
      setContentSearchStatus("success");
      return;
    }

    try {
      const response = await fetch("/api/platform-search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          categoryId: selectedCategoryId,
          keyword,
          activePlatform,
          limitMode: contentSearchLimitMode,
          limit: requestLimit,
        }),
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload?.msg || payload?.error || "检索失败，请稍后重试。");
      }

      const nextResults = Array.isArray(payload?.data?.items) ? payload.data.items : [];
      const sourceLabel = payload?.data?.sourceLabel || "公众号";
      const totalCount = Number(payload?.data?.totalCount ?? nextResults.length);
      const searchTargetDate = getTodayDateKey();
      const searchScopeKey = `${selectedCategoryId}:${searchTargetDate}`;
      const searchScopeState = manualSearchResultsByScope[searchScopeKey] ?? {
        keyword: "",
        results: [],
        returnedCount: 0,
        totalCount: 0,
        sourceLabel: "",
      };
      const existingKeys = new Set(searchScopeState.results.map(getTimelineDedupKey));
      const uniqueNextResults = nextResults.filter((item) => !existingKeys.has(getTimelineDedupKey(item)));
      const mergedResults = mergeSearchResults(searchScopeState.results, nextResults);

      setContentSearchCache((current) => ({
        ...current,
        [cacheKey]: {
          data: {
            items: nextResults,
            sourceLabel,
            totalCount,
          },
          cachedAt: Date.now(),
        },
      }));

      setManualSearchResultsByScope((current) => ({
        ...current,
        [searchScopeKey]: {
          keyword,
          results: mergedResults,
          returnedCount: uniqueNextResults.length,
          totalCount,
          sourceLabel,
        },
      }));
      setSelectedDate(searchTargetDate);

      if (activePlatform !== sourceLabel && platformOptions.includes(sourceLabel)) {
        setActivePlatform(sourceLabel);
      }

      setBanner(DEFAULT_BANNER_TEXT);
      setContentSearchFeedback("success");
      setContentSearchStatus("success");
    } catch (error) {
      setContentSearchStatus("error");
      const errorMessage = error instanceof Error ? error.message : "检索失败，请稍后重试。";
      setBanner(errorMessage);
      setContentSearchFeedback("error");
    }
  }

  function handleContentSearchLimitModeChange(value) {
    const normalizedMode = value === "limited" || value === "自定义" ? "limited" : "all";
    setContentSearchLimitMode(normalizedMode);
  }

  function handleContentSearchLimitChange(value) {
    const sanitized = value.replace(/[^\d]/g, "");
    setContentSearchLimit(sanitized);
  }

  function handleSelectDate(date) {
    setSelectedDate(date);
    setReportAnalysisDate(date);
    setTimelineFilterPlatform("全部");
    setTimelineFilterKeyword("");
    markSearchResultsAsSeen(selectedCategoryId, date, setManualSearchResultsByScope);
  }

  function handleAddAccount() {
    const value = accountDraft.name.trim();
    if (!value) {
      setBanner("请输入博主或账号名称。");
      return;
    }
    updateSelectedCategory((category) => ({
      ...category,
      accounts: [
        {
          id: `account-${Date.now()}`,
          name: value,
          platform: accountDraft.platform,
          avatar: value.slice(0, 1),
          signal: "新加入观察",
          status: "已加入",
          lastFetched: "等待首次抓取",
        },
        ...category.accounts,
        ],
      }));
    setAccountDraft((current) => ({ ...current, name: "" }));
    setBanner(`已添加账号：${value}`);
  }

  function handleRemoveAccount(accountId) {
    updateSelectedCategory((category) => ({
      ...category,
      accounts: category.accounts.filter((account) => account.id !== accountId),
    }));
    setBanner("已移除一个对标账号。");
  }

  function handleStrategyChange(field, value) {
    if (field === "runTime") {
      setReportScheduleTime(normalizeTimeInput(value));
    }

    updateSelectedCategory((category) => ({
      ...category,
      strategy: {
        ...category.strategy,
        [field]: value,
      },
    }));
  }

  function handleReportScheduleTimeChange(value) {
    const normalizedTime = normalizeTimeInput(value);
    setReportScheduleTime(normalizedTime);
    updateSelectedCategory((category) => ({
      ...category,
      strategy: {
        ...category.strategy,
        runTime: normalizedTime,
      },
    }));
  }

  function handleReportAnalysisDateChange(value) {
    setReportAnalysisDate(value);

    if (allContentDays.some((day) => day.date === value)) {
      setSelectedDate(value);
    }

    const matchedReportId = reportList.find((report) => report.reportDate === value)?.id;
    if (matchedReportId) {
      setSelectedReportId(matchedReportId);
    }
  }

  function handleSaveSettings() {
    setBanner("当前分类配置已保存。该原型会保留你当前的交互状态，便于继续预览。");
  }

  function getReportIdForContentDate(contentDate = selectedDate) {
    if (!reportList.length) return "";
    return reportList.find((report) => report.reportDate === contentDate)?.id ?? reportList[0].id;
  }

  function handleOpenReportTab(contentDate) {
    if (contentDate) {
      setSelectedReportId(getReportIdForContentDate(contentDate));
      setReportAnalysisDate(contentDate);
    } else if (!selectedReportId) {
      setSelectedReportId(getReportIdForContentDate(selectedDate));
    }
    setActiveTab("report");
  }

  function handleSelectReportId(reportId) {
    setSelectedReportId(reportId);
    const nextReport = reportList.find((report) => report.id === reportId);

    if (!nextReport?.reportDate) {
      return;
    }

    if (allContentDays.some((day) => day.date === nextReport.reportDate)) {
      setSelectedDate(nextReport.reportDate);
    }

    setReportAnalysisDate(nextReport.reportDate);
  }

  async function refreshPersistedReports(categoryId = selectedCategoryId) {
    const response = await fetch(`/api/report-analysis/reports?categoryId=${encodeURIComponent(categoryId)}`);
    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload?.msg || "读取报告失败。");
    }

    const reports = Array.isArray(payload?.data) ? payload.data : [];
    setPersistedReportsByCategory((current) => ({
      ...current,
      [categoryId]: reports,
    }));
    return reports;
  }

  async function handleSaveReportSchedule() {
    const normalizedTime = normalizeTimeInput(reportScheduleTime);
    setReportRunStatus("loading");
    setReportRunMessage("");

    try {
      const response = await fetch("/api/report-analysis/schedule", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          dailyRunTime: normalizedTime,
          enabled: reportScheduleEnabled,
        }),
      });
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload?.msg || "保存定时配置失败。");
      }

      const nextRunTime = payload?.data?.dailyRunTime || normalizedTime;
      setReportScheduleTime(nextRunTime);
      updateSelectedCategory((category) => ({
        ...category,
        strategy: {
          ...category.strategy,
          runTime: nextRunTime,
        },
      }));
      setReportScheduleEnabled(payload?.data?.enabled !== false);
      setReportRunStatus("success");
      setReportRunMessage(reportScheduleEnabled ? "定时分析配置已保存。" : "定时分析已关闭。");
    } catch (error) {
      setReportRunStatus("error");
      setReportRunMessage(error instanceof Error ? error.message : "保存定时配置失败。");
    }
  }

  async function handleRunDailyReport() {
    setReportRunStatus("loading");
    setReportRunMessage("");

    try {
      const analysisDate = reportAnalysisDate || selectedDate || getPreviousDateKey();
      const response = await fetch("/api/report-analysis/daily", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          categoryId: selectedCategoryId,
          targetDate: analysisDate,
        }),
      });
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload?.msg || "日报分析失败。");
      }

      const reports = await refreshPersistedReports(selectedCategoryId);
      const createdReport = reports.find((report) => report.mode === "daily" && report.reportDate === analysisDate);
      if (createdReport) {
        setSelectedReportId(createdReport.id);
      }

      const skippedCount = Array.isArray(payload?.data?.skipped) ? payload.data.skipped.length : 0;
      if (createdReport) {
        setReportRunStatus("success");
        setReportRunMessage(`${analysisDate} 的全量分析已完成，报告已更新。`);
      } else if (skippedCount) {
        setReportRunStatus("idle");
        setReportRunMessage(`${analysisDate} 没有可分析数据，已跳过。`);
      } else {
        setReportRunStatus("success");
        setReportRunMessage(`${analysisDate} 的全量分析已完成。`);
      }
    } catch (error) {
      setReportRunStatus("error");
      setReportRunMessage(error instanceof Error ? error.message : "日报分析失败。");
    }
  }

  async function handleRunKeywordReport() {
    const keyword = reportKeywordDraft.trim();
    if (!keyword) {
      setReportRunStatus("error");
      setReportRunMessage("请输入关键词后再执行定向报告分析。");
      return;
    }

    setReportRunStatus("loading");
    setReportRunMessage("");

    try {
      const response = await fetch("/api/report-analysis/keyword", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          categoryId: selectedCategoryId,
          keyword,
          targetDate: reportAnalysisDate || selectedDate,
        }),
      });
      const payload = await response.json();

      if (!response.ok) {
        throw new Error(payload?.msg || "定向报告分析失败。");
      }

      const reports = await refreshPersistedReports(selectedCategoryId);
      const createdReportId = payload?.data?.id;
      const createdReport = reports.find((report) => report.id === createdReportId) ?? reports[0];

      if (createdReport) {
        setSelectedReportId(createdReport.id);
      }

      setReportRunStatus("success");
      setReportRunMessage(`已生成 ${reportAnalysisDate || selectedDate || "--"} “${keyword}”的定向报告。`);
      setActiveTab("report");
    } catch (error) {
      setReportRunStatus("error");
      setReportRunMessage(error instanceof Error ? error.message : "定向报告分析失败。");
    }
  }

  return (
    <main className="app-shell">
      <div className="window">
        <div className="window-dots">
          <span />
          <span />
          <span />
        </div>

        <div className="workspace">
          <aside className="sidebar">
            <div className="brand">
              <div className="brand-mark">CM</div>
              <div>
                <p className="eyebrow">Content Monitor</p>
                <h1>内容监控台</h1>
              </div>
            </div>

            <section className="panel soft sidebar-section-panel">
              <div className="section-head">
                <span>监控分类</span>
                <button className="pill ghost" type="button" onClick={handleCreateCategory}>
                  + 新建
                </button>
              </div>

              <div className="category-list">
                {categoryViews.map((category) => (
                  <div
                    key={category.id}
                    className={`category-card ${category.id === selectedCategoryId ? "active" : ""}`}
                    onClick={() => setSelectedCategoryId(category.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        setSelectedCategoryId(category.id);
                      }
                    }}
                  >
                    <div className="category-card-top">
                      <div className="category-card-title">
                        <strong>{category.name}</strong>
                      </div>
                      <div className="category-actions">
                        <button
                          type="button"
                          className="icon-action"
                          aria-label={`重命名 ${category.name}`}
                          onClick={(event) => {
                            event.stopPropagation();
                            handleRenameCategory(category.id);
                          }}
                        >
                          <EditIcon />
                        </button>
                        <button
                          type="button"
                          className="icon-action"
                          aria-label={`删除 ${category.name}`}
                          onClick={(event) => {
                            event.stopPropagation();
                            handleDeleteCategory(category.id);
                          }}
                        >
                          <TrashIcon />
                        </button>
                      </div>
                    </div>
                    <span className={`status-chip ${category.id === selectedCategoryId ? "good" : "neutral"}`}>
                      {category.status}
                    </span>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel soft sidebar-summary-panel">
              <p className="eyebrow">本日概览</p>
              <div className="mini-metrics">
                <MetricCard label="新增内容" value={sumContent(selectedCategory.contentDays)} />
                <MetricCard label="爆款信号" value={sumHotContent(selectedCategory.contentDays)} />
                <MetricCard label="AI 选题" value={sumTopicCount(selectedCategory.reports)} />
                <MetricCard label="每日运行" value={effectiveRunTime} />
              </div>
            </section>
          </aside>

          <section className="main-panel">
            <div className="main-top-shell">
              <header className="top-bar top-header-bar">
                <div className="top-header-title">
                  <h2>{selectedCategory.name}</h2>
                </div>

                <nav className="top-tab-bar top-tab-inline">
                  {topTabs.map((tab) => {
                    const Icon = tab.icon;
                    return (
                      <button
                        key={tab.id}
                        type="button"
                        className={`tab ${activeTab === tab.id ? "active" : ""}`}
                        onClick={() => {
                          if (tab.id === "report") {
                            handleOpenReportTab();
                            return;
                          }
                          setActiveTab(tab.id);
                        }}
                      >
                        <Icon />
                        {tab.label}
                      </button>
                    );
                  })}
                </nav>

                <div className="header-actions">
                  <button
                    className="pill ghost action-button"
                    type="button"
                    onClick={() => setBanner("这里会展示抓取日志、运行历史和分析状态。")}
                  >
                    查看日志
                  </button>
                  <button className="pill primary action-button" type="button" onClick={handleRunNow} disabled={isPending}>
                    {isPending ? "运行中..." : "立即运行一次"}
                  </button>
                </div>
              </header>
            </div>

            <div ref={scrollRegionRef} className="main-scroll-region">
              {activeTab === "content" ? (
                <ContentTab
                  selectedDay={selectedDay}
                  selectedCategory={selectedCategory}
                  activePlatform={activePlatform}
                  platformOptions={platformOptions}
                  filteredItems={filteredTimelineItems}
                  timelineFilterPlatform={timelineFilterPlatform}
                  timelineFilterKeyword={timelineFilterKeyword}
                  timelineFilterOptions={timelineFilterOptions}
                  hasTimelineFilter={timelineFilterPlatform !== "全部" || Boolean(timelineFilterKeyword.trim())}
                  contentSearchDraft={contentSearchDraft}
                  contentSearchQuery={currentSearchState.keyword}
                  contentSearchLimitMode={contentSearchLimitMode}
                  contentSearchLimit={contentSearchLimit}
                  contentSearchResultCount={currentSearchState.totalCount}
                  contentSearchDisplayedCount={currentSearchState.returnedCount}
                  contentSearchSourceLabel={currentSearchState.sourceLabel}
                  contentSearchStatus={contentSearchStatus}
                  contentDays={displayContentDays}
                  contentMetrics={contentMetrics}
                  isToolBarPinned={isToolBarPinned}
                  isTrendCondensed={isTrendCondensed}
                  trendExpanded={trendExpanded}
                  onToggleTrendExpanded={() => setTrendExpanded((current) => !current)}
                  onSelectDate={handleSelectDate}
                  onSelectPlatform={setActivePlatform}
                  onTimelineFilterPlatformChange={setTimelineFilterPlatform}
                  onTimelineFilterKeywordChange={setTimelineFilterKeyword}
                  onContentSearchDraftChange={setContentSearchDraft}
                  onContentSearchLimitModeChange={handleContentSearchLimitModeChange}
                  onContentSearchLimitChange={handleContentSearchLimitChange}
                  onContentSearchSubmit={handleContentSearchSubmit}
                  onOpenReport={() => {
                    setSelectedReportId(getReportIdForContentDate(selectedDay.date));
                    setActiveTab("report");
                    setBanner(`已切换到 ${selectedDay.label} 的 AI 日报。`);
                  }}
                />
              ) : null}

              {activeTab === "report" ? (
                <ReportTab
                  reports={reportList}
                  selectedReportId={selectedReportId}
                  onSelectReportId={handleSelectReportId}
                  selectedReport={selectedReport}
                  reportRange={reportRange}
                  onSelectRange={setReportRange}
                  reportTopics={reportTopics}
                  reportScheduleTime={effectiveRunTime}
                  reportScheduleEnabled={reportScheduleEnabled}
                  reportAnalysisDate={reportAnalysisDate || selectedDate || getPreviousDateKey()}
                  onReportScheduleTimeChange={handleReportScheduleTimeChange}
                  onReportScheduleEnabledChange={setReportScheduleEnabled}
                  onReportAnalysisDateChange={handleReportAnalysisDateChange}
                  onSaveReportSchedule={handleSaveReportSchedule}
                  reportKeywordDraft={reportKeywordDraft}
                  onReportKeywordDraftChange={setReportKeywordDraft}
                  onRunDailyReport={handleRunDailyReport}
                  onRunKeywordReport={handleRunKeywordReport}
                  reportRunStatus={reportRunStatus}
                  reportRunMessage={reportRunMessage}
                  onOpenSettings={() => {
                    setActiveTab("settings");
                    setBanner("已从报告页切到监控设置，可继续调整平台、关键词和账号。");
                  }}
                />
              ) : null}

              {activeTab === "settings" ? (
                <SettingsTab
                  category={selectedCategory}
                  scheduleRunTime={effectiveRunTime}
                  keywordDraft={keywordDraft}
                  onKeywordDraftChange={setKeywordDraft}
                  onAddKeyword={handleAddKeyword}
                  onRemoveKeyword={handleRemoveKeyword}
                  accountDraft={accountDraft}
                  onAccountDraftChange={setAccountDraft}
                  onAddAccount={handleAddAccount}
                  onRemoveAccount={handleRemoveAccount}
                  onTogglePlatform={handleTogglePlatform}
                  onStrategyChange={handleStrategyChange}
                  onSaveSettings={handleSaveSettings}
                  onBackToContent={() => {
                    setActiveTab("content");
                    setBanner("已返回内容页，可以继续查看采集结果与当天摘要。");
                  }}
                />
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </main>
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

function normalizeReportsForView(persistedReports = [], fallbackReports = []) {
  const normalizedPersisted = Array.isArray(persistedReports)
    ? persistedReports.map((report) => ({
        ...report,
        reportDate: report.reportDate || report.date,
        date: report.reportDate || report.date,
        label: report.label || formatReportLabel(report.reportDate || report.date),
        generatedAtLabel: formatGeneratedAtLabel(report.generatedAt),
      }))
    : [];

  const normalizedFallback = Array.isArray(fallbackReports)
    ? fallbackReports.map((report) => ({
        ...report,
        id: report.id || `fallback-${report.date}`,
        mode: report.mode || "daily",
        reportDate: report.date,
        generatedAt: report.generatedAt || null,
        generatedAtLabel: formatGeneratedAtLabel(report.generatedAt),
        keywordTarget: report.keywordTarget || "",
        analyzedCount: report.analyzedCount || report.hotContentCount || report.metrics?.hotContent || 0,
        articleSummaries: report.articleSummaries || [],
      }))
    : [];

  const deduped = new Map();
  [...normalizedPersisted, ...normalizedFallback].forEach((report) => {
    if (!report?.id || deduped.has(report.id)) {
      return;
    }
    deduped.set(report.id, report);
  });

  return [...deduped.values()].sort((left, right) => {
    const leftTime = getReportSortTimestamp(left);
    const rightTime = getReportSortTimestamp(right);
    if (rightTime !== leftTime) return rightTime - leftTime;
    return String(right.reportDate ?? "").localeCompare(String(left.reportDate ?? ""));
  });
}

function buildCategoryViewModel(category, persistedReports = [], searchStates = []) {
  const reports = normalizeReportsForView(persistedReports, category.reports);
  const contentDays = buildContentDaysWithSearchResults(category.contentDays, searchStates, reports);

  return {
    ...category,
    reports,
    contentDays,
    status: deriveCategoryStatus(category, contentDays, reports),
  };
}

function buildPlatformOptions(enabledPlatforms) {
  return SEARCH_READY_PLATFORMS.filter((platform) => {
    if (platform === "公众号") return true;
    return enabledPlatforms.some((item) => item.name === platform);
  });
}

function getDefaultSearchPlatform(category, excludedPlatform = "") {
  const candidates = buildPlatformOptions(category.platforms.filter((item) => item.enabled)).filter(
    (name) => name !== excludedPlatform,
  );
  return candidates[0] || SEARCH_READY_PLATFORMS[0];
}

async function requestPlatformSearch(payload) {
  const response = await fetch("/api/platform-search", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const result = await response.json();

  if (!response.ok) {
    throw new Error(result?.msg || result?.error || "检索失败，请稍后重试。");
  }

  return result;
}

function buildSearchCacheKey({ platform, keyword, limitMode, limit }) {
  return [platform || "", keyword || "", limitMode || "all", limit ?? "all"]
    .map((value) => String(value).trim().toLowerCase())
    .join("|");
}

function loadStoredJson(key, fallbackValue) {
  if (typeof window === "undefined") return fallbackValue;

  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallbackValue;
  } catch {
    return fallbackValue;
  }
}

function saveStoredJson(key, value) {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {}
}

function mergeSearchResults(existingItems, nextItems) {
  const deduped = new Map();

  [...nextItems, ...existingItems].forEach((item) => {
    const normalizedItem = normalizeTimelineItem(item);
    const key = getTimelineDedupKey(normalizedItem);
    if (!deduped.has(key)) {
      deduped.set(key, normalizedItem);
      return;
    }

    deduped.set(key, mergeTimelineItemState(deduped.get(key), normalizedItem));
  });

  return [...deduped.values()].sort((left, right) => (right.sortTimestamp ?? 0) - (left.sortTimestamp ?? 0));
}

function mergeTimelineItems(searchItems, baseItems, selectedDate) {
  return [...searchItems, ...baseItems].sort(
    (left, right) => getTimelineSortValue(right, selectedDate) - getTimelineSortValue(left, selectedDate),
  );
}

function getSearchStatesForCategory(manualSearchResultsByScope, categoryId) {
  return Object.entries(manualSearchResultsByScope)
    .filter(([scopeKey]) => scopeKey.startsWith(`${categoryId}:`))
    .map(([scopeKey, state]) => ({
      date: scopeKey.slice(categoryId.length + 1),
      state,
    }));
}

function buildContentDaysWithSearchResults(baseDays = [], searchStates = [], reports = []) {
  const daysByDate = new Map(baseDays.map((day) => [day.date, { ...day }]));
  const reportsByDate = new Map();

  reports.forEach((report) => {
    if (!report?.reportDate) return;
    const current = reportsByDate.get(report.reportDate) ?? [];
    current.push(report);
    reportsByDate.set(report.reportDate, current);
  });

  searchStates.forEach(({ date, state }) => {
    if (!state?.results?.length) {
      return;
    }

    const existingDay = daysByDate.get(date);
    const searchAuthors = [...new Set(state.results.map((item) => item.author).filter(Boolean))];
    const nextKeywords = [...new Set([...(existingDay?.keywords ?? []), state.keyword].filter(Boolean))];

    daysByDate.set(date, {
      date,
      label: existingDay?.label ?? formatDayLabel(date),
      total: (existingDay?.total ?? 0) + state.results.length,
      hotCount: (existingDay?.hotCount ?? 0) + state.results.length,
      topic: existingDay?.topic ?? "手动检索结果",
      reportReady: Boolean(existingDay?.reportReady ?? reportsByDate.has(date)),
      keywords: nextKeywords,
      aiJudgement: existingDay?.aiJudgement ?? "当前时间线包含手动检索追加内容。",
      actions: existingDay?.actions ?? ["继续补充关键词检索，观察新增内容趋势。"],
      authors: existingDay ? existingDay.authors : searchAuthors.map((author) => `${author}：手动检索新增内容`),
      items: existingDay?.items ?? [],
    });
  });

  reportsByDate.forEach((dateReports, date) => {
    const existingDay = daysByDate.get(date);
    const primaryReport = dateReports[0];

    if (existingDay) {
      daysByDate.set(date, {
        ...existingDay,
        reportReady: true,
        topic: existingDay.topic || primaryReport?.summary || "已生成分析报告",
        aiJudgement: existingDay.aiJudgement || primaryReport?.hotSummary || "该日期已生成分析报告。",
      });
      return;
    }

    const fallbackActions = (primaryReport?.topics ?? []).slice(0, 3).map((topic) => sanitizeTimelineText(topic.title, 40));
    const fallbackAuthors = (primaryReport?.articleSummaries ?? [])
      .slice(0, 3)
      .map((article) => `${sanitizeTimelineText(article.author, 24)}：报告分析来源`);

    daysByDate.set(date, {
      ...createEmptyContentDay(date),
      label: formatDayLabel(date),
      total: Number(primaryReport?.analyzedCount ?? primaryReport?.hotContentCount ?? primaryReport?.metrics?.hotContent ?? 0),
      hotCount: Number(primaryReport?.hotContentCount ?? primaryReport?.metrics?.hotContent ?? 0),
      topic: primaryReport?.summary || "已生成分析报告",
      reportReady: true,
      keywords: [primaryReport?.keywordTarget].filter(Boolean),
      aiJudgement: primaryReport?.hotSummary || "该日期已生成分析报告，可切换查看详情。",
      actions: fallbackActions.length ? fallbackActions : ["查看分析报告详情。"],
      authors: fallbackAuthors,
    });
  });

  return [...daysByDate.values()].sort((left, right) => new Date(right.date).getTime() - new Date(left.date).getTime());
}

function getTimelineDedupKey(item) {
  return [item.platform, item.author, item.title].map((value) => String(value ?? "").trim().toLowerCase()).join("|");
}

function getTimelineSortValue(item, selectedDate) {
  if (item.sortTimestamp) return item.sortTimestamp;
  if (!item.time) return 0;

  const [hours = "0", minutes = "0"] = String(item.time).split(":");
  const isoDate = `${selectedDate}T${hours.padStart(2, "0")}:${minutes.padStart(2, "0")}:00`;
  const timestamp = new Date(isoDate).getTime();
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function finalizeTimelineItems(items) {
  return items.map((item) => {
    const normalizedItem = normalizeTimelineItem(item);

    if (!normalizedItem?.isNewResult) {
      return normalizedItem;
    }

    const shouldShowNew = shouldShowNewBadge(normalizedItem);
    return {
      ...normalizedItem,
      isNewResult: shouldShowNew,
      tag: shouldShowNew ? "NEW" : "",
    };
  });
}

function shouldShowNewBadge(item) {
  if (!item?.isNewResult) return false;
  if (item.seenAt) return false;

  const fetchedAt = Number(item.firstFetchedAt ?? item.sortTimestamp ?? 0);
  if (!fetchedAt) return false;

  return Date.now() - fetchedAt < NEW_RESULT_VISIBLE_MS;
}

function mergeTimelineItemState(primaryItem, secondaryItem) {
  return normalizeTimelineItem({
    ...primaryItem,
    seenAt: primaryItem?.seenAt ?? secondaryItem?.seenAt ?? null,
    firstFetchedAt:
      Number(primaryItem?.firstFetchedAt ?? 0) ||
      Number(secondaryItem?.firstFetchedAt ?? 0) ||
      Number(primaryItem?.sortTimestamp ?? 0) ||
      Number(secondaryItem?.sortTimestamp ?? 0),
  });
}

function markSearchResultsAsSeen(categoryId, date, setManualSearchResultsByScope) {
  const searchScopeKey = `${categoryId}:${date}`;

  setManualSearchResultsByScope((current) => {
    const state = current[searchScopeKey];
    if (!state?.results?.some((item) => item?.isNewResult && !item?.seenAt)) {
      return current;
    }

    return {
      ...current,
      [searchScopeKey]: {
        ...state,
        results: state.results.map((item) =>
          item?.isNewResult && !item?.seenAt ? { ...item, seenAt: Date.now() } : item,
        ),
      },
    };
  });
}

function sanitizeTimelineText(value, maxLength = 120) {
  const normalized = String(value ?? "")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/\r?\n/g, " ")
    .replace(/\\n/g, " ")
    .replace(/\\r|\\t/g, " ")
    .replace(/^\s*---+\s*/g, "")
    .replace(/\s+---+\s+/g, " ")
    .replace(/^\s*#+\s*/g, "")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1")
    .replace(/\s{2,}/g, " ")
    .trim();

  if (!normalized) {
    return "";
  }

  return normalized.length > maxLength ? `${normalized.slice(0, maxLength)}...` : normalized;
}

function normalizeTimelineItem(item) {
  if (!item) return item;

  return {
    ...item,
    time: sanitizeTimelineText(item.time, 32),
    platform: sanitizeTimelineText(item.platform, 20),
    title: sanitizeTimelineText(item.title, 88),
    author: sanitizeTimelineText(item.author, 40),
    match: sanitizeTimelineText(item.match, 80),
    description: sanitizeTimelineText(item.description, 120),
    tag: sanitizeTimelineText(item.tag, 12),
  };
}

function buildTimelineFilterOptions(items) {
  return ["全部", ...new Set(items.map((item) => item.platform).filter(Boolean))];
}

function filterTimelineItems(items, platform, keyword) {
  const normalizedKeyword = String(keyword ?? "").trim().toLowerCase();

  return items.filter((item) => {
    if (platform && platform !== "全部" && item.platform !== platform) {
      return false;
    }

    if (!normalizedKeyword) {
      return true;
    }

    const haystack = [item.title, item.author, item.match, item.description]
      .map((value) => String(value ?? "").toLowerCase())
      .join(" ");

    return haystack.includes(normalizedKeyword);
  });
}

function getTodayDateKey() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDayLabel(dateKey) {
  const date = new Date(`${dateKey}T00:00:00`);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${month}/${day} ${getChineseWeekday(date)}`;
}

function formatReportLabel(dateKey) {
  const date = new Date(`${dateKey}T00:00:00`);
  if (Number.isNaN(date.getTime())) return "--/--";
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${month}/${day}`;
}

function formatGeneratedAtLabel(value) {
  if (!value) return "";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${month}/${day} ${hours}:${minutes}`;
}

function getReportSortTimestamp(report) {
  if (Number.isFinite(report?.generatedAtTs)) {
    return Number(report.generatedAtTs);
  }

  const parsed = Date.parse(report?.generatedAt || report?.reportDate || 0);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function normalizeTimeInput(value) {
  const [hours = "08", minutes = "30"] = String(value ?? "08:30").split(":");
  return `${hours.padStart(2, "0").slice(0, 2)}:${minutes.padStart(2, "0").slice(0, 2)}`;
}

function getPreviousDateKey() {
  const date = new Date();
  date.setDate(date.getDate() - 1);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function getChineseWeekday(date) {
  return ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][date.getDay()] || "周";
}

function getTopicsInRange(reports, rangeId) {
  if (rangeId === "7") return reports.slice(0, 2).flatMap((report) => report.topics);
  if (rangeId === "14") return reports.slice(0, 3).flatMap((report) => report.topics);
  return reports.flatMap((report) => report.topics);
}

function deriveCategoryStatus(category, contentDays, reports) {
  const enabledPlatformCount = category.platforms.filter((platform) => platform.enabled).length;
  const hasTargets = category.keywords.length > 0 || category.accounts.length > 0;
  const hasActivity = reports.length > 0 || contentDays.some((day) => day.total > 0 || day.reportReady);

  if (!enabledPlatformCount || !hasTargets) {
    return "待配置";
  }

  if (hasActivity) {
    return "今日已更新";
  }

  return category.status || "已配置";
}

function sumContent(contentDays) {
  return contentDays.reduce((sum, day) => sum + day.total, 0);
}

function sumHotContent(contentDays) {
  return contentDays.reduce((sum, day) => sum + day.hotCount, 0);
}

function sumTopicCount(reports) {
  return reports.reduce((sum, report) => sum + report.topicCount, 0);
}

function createEmptyContentDay(date) {
  return {
    date,
    label: formatDayLabel(date),
    total: 0,
    hotCount: 0,
    topic: "暂无采集内容",
    reportReady: false,
    keywords: [],
    aiJudgement: "当前分类还没有可展示的采集内容或分析结果。",
    actions: ["先去监控设置补充平台、关键词和账号。"],
    authors: [],
    items: [],
  };
}
