export const seedCategories = [
  {
    id: "claude-code",
    name: "Claude Code 选题监控",
    subtitle: "4 平台 · 18 关键词 · 12 博主",
    status: "今日已更新",
    runStatus: "正常",
    lastRun: "今天 09:02",
    platforms: [
      { id: "xiaohongshu", name: "小红书", short: "红", description: "内容种草", enabled: true },
      { id: "douyin", name: "抖音", short: "抖", description: "热视频", enabled: true },
      { id: "weibo", name: "微博", short: "微", description: "热点讨论", enabled: true },
      { id: "bilibili", name: "B站", short: "B", description: "长视频", enabled: true },
      { id: "zhihu", name: "知乎", short: "知", description: "问答观点", enabled: false }
    ],
    keywords: [
      "claude code",
      "cursor",
      "vibe coding",
      "agent workflow",
      "代码评审",
      "团队协作",
      "自动日报",
      "内容工厂"
    ],
    accounts: [
      {
        id: "ai-blackboard",
        name: "AI 产品黑板报",
        platform: "小红书",
        avatar: "AI",
        signal: "命中 4 条热点",
        status: "持续跟踪",
        lastFetched: "最近抓取 2 小时前"
      },
      {
        id: "old-han",
        name: "老韩聊 AI 开发",
        platform: "抖音",
        avatar: "韩",
        signal: "评论活跃高",
        status: "优先监控",
        lastFetched: "最近抓取 2 小时前"
      },
      {
        id: "code-factory",
        name: "代码制造局",
        platform: "B站",
        avatar: "码",
        signal: "长视频案例多",
        status: "已加入",
        lastFetched: "最近抓取 1 天前"
      }
    ],
    strategy: {
      runTime: "09:00",
      window: "最近 24 小时",
      topN: 10,
      output: "日报 + 选题库"
    },
    contentDays: [
      {
        date: "2026-03-24",
        label: "03/24 周二",
        total: 38,
        hotCount: 4,
        topic: "Claude Code 工作流",
        reportReady: true,
        keywords: ["工作流模板", "效率翻倍", "并行 agent", "代码评审", "团队协作"],
        aiJudgement:
          "今天的高热内容不再只讲工具本身，而是开始强调怎么接进团队工作流，这是更接近转化的内容方向。",
        actions: [
          "优先跟进“7 步工作流拆解”类选题",
          "补充一篇“Claude Code vs Cursor 使用边界”",
          "针对团队协作场景准备案例素材"
        ],
        authors: [
          "AI 产品黑板报：2 条高热内容",
          "老韩聊 AI 开发：评论区争议高",
          "代码制造局：视频带来新场景讨论"
        ],
        items: [
          {
            id: "cc-2401",
            time: "10:40",
            platform: "小红书",
            heat: 9.6,
            title: "Claude Code 工作流 7 步拆解，为什么团队效率翻倍",
            author: "AI 产品黑板报",
            match: "命中关键词：claude code、workflow、团队协作",
            tag: "爆款",
            description:
              "内容重点聚焦可复制流程和工具组合，评论区大量提到模板复用、团队提效、成本对比。"
          },
          {
            id: "cc-2402",
            time: "09:15",
            platform: "抖音",
            heat: 8.9,
            title: "Cursor 不香了？Claude Code 才是程序员新主场",
            author: "老韩聊 AI 开发",
            match: "命中关键词：cursor、claude code、对比测评",
            tag: "高互动",
            description: "采用冲突型标题加实测对比结构，用户更关心真实效率和适用场景。"
          },
          {
            id: "cc-2403",
            time: "08:05",
            platform: "B站",
            heat: 8.4,
            title: "我用 Claude Code 做了一个自动内容工厂，结果太夸张了",
            author: "代码制造局",
            match: "命中账号：代码制造局 · 关联词：内容工厂、自动化选题",
            tag: "新账号",
            description: "视频把自动跑选题展示得很具体，说明运营场景内容正在升温。"
          },
          {
            id: "cc-2404",
            time: "07:30",
            platform: "小红书",
            heat: 7.9,
            title: "程序员团队如何把 AI 选题接进日报机制",
            author: "运营自动化研究所",
            match: "命中关键词：日报、AI 选题、团队流程",
            tag: "高收藏",
            description: "把开发工具话题和运营落地场景连接起来，适合做方法论扩展。"
          }
        ]
      },
      {
        date: "2026-03-23",
        label: "03/23 周一",
        total: 31,
        hotCount: 3,
        topic: "并行 Agent 实战",
        reportReady: true,
        keywords: ["并行 agent", "自动评审", "提交流程", "团队规范"],
        aiJudgement: "并行 agent 和自动评审的实战内容更容易带来收藏，用户开始追求流程化能力。",
        actions: ["整理一篇并行 agent 工作流", "补一篇自动评审案例", "对比单 agent 与多 agent 收益"],
        authors: ["老韩聊 AI 开发：争议高", "代码制造局：案例强", "AI 产品黑板报：收藏高"],
        items: [
          {
            id: "cc-2301",
            time: "20:10",
            platform: "B站",
            heat: 9.1,
            title: "并行 Agent 到底怎么配？我踩了 3 个坑",
            author: "代码制造局",
            match: "命中关键词：agent workflow、并行协作",
            tag: "爆款",
            description: "案例讲得非常具体，用户会对执行顺序和成本更敏感。"
          },
          {
            id: "cc-2302",
            time: "16:45",
            platform: "微博",
            heat: 8.2,
            title: "让 Claude Code 自动做 Code Review，实际能省多少时间？",
            author: "DevOps 新鲜事",
            match: "命中关键词：代码评审、团队协作",
            tag: "高讨论",
            description: "用户会在评论区讨论准确率、误报率和团队接受度。"
          },
          {
            id: "cc-2303",
            time: "11:20",
            platform: "小红书",
            heat: 7.8,
            title: "我把 Claude Code 接进了提交流程，老板终于不催日报了",
            author: "AI 产品黑板报",
            match: "命中关键词：自动日报、团队协作",
            tag: "高收藏",
            description: "典型的工作流落地内容，偏管理和流程价值。"
          }
        ]
      },
      {
        date: "2026-03-22",
        label: "03/22 周日",
        total: 26,
        hotCount: 2,
        topic: "Codex vs Cursor",
        reportReady: true,
        keywords: ["工具对比", "成本", "适用场景", "效率差异"],
        aiJudgement: "工具对比内容仍有热度，但用户更看重场景拆分而不是简单站队。",
        actions: ["做一篇场景维度对比", "补充成本测算模板", "拆出不同角色的使用路径"],
        authors: ["AI 产品黑板报：收藏高", "开发者观察室：评论多"],
        items: [
          {
            id: "cc-2201",
            time: "18:30",
            platform: "小红书",
            heat: 8.6,
            title: "Claude Code 和 Cursor 我都用了 30 天，最终留下了谁？",
            author: "开发者观察室",
            match: "命中关键词：cursor、claude code、工具对比",
            tag: "高互动",
            description: "真实试用内容更能吸引点击，但必须有明确场景边界。"
          },
          {
            id: "cc-2202",
            time: "10:05",
            platform: "知乎",
            heat: 7.6,
            title: "为什么说别再问哪个 AI 编码工具最好，用例才是重点",
            author: "理性派工程师",
            match: "命中关键词：场景拆分、工具对比",
            tag: "高讨论",
            description: "用户会围绕不同团队规模和预算展开讨论。"
          }
        ]
      },
      {
        date: "2026-03-21",
        label: "03/21 周六",
        total: 18,
        hotCount: 1,
        topic: "Vibe Coding 案例",
        reportReady: false,
        keywords: ["vibe coding", "个人工作流", "案例演示"],
        aiJudgement: "更偏个人表达和案例展示，热度一般，但适合做概念教育型内容。",
        actions: ["保留为补充栏目", "观察是否出现新话题突破", "不作为本周主推方向"],
        authors: ["代码制造局：案例型", "AI 轻松学：概念介绍"],
        items: [
          {
            id: "cc-2101",
            time: "13:40",
            platform: "B站",
            heat: 7.1,
            title: "Vibe Coding 是不是程序员的下一站？",
            author: "代码制造局",
            match: "命中关键词：vibe coding、案例演示",
            tag: "观察中",
            description: "概念新鲜但落地深度不够，需要等更成熟的案例出现。"
          }
        ]
      },
      {
        date: "2026-03-20",
        label: "03/20 周五",
        total: 22,
        hotCount: 2,
        topic: "AI 日报模板",
        reportReady: true,
        keywords: ["日报模板", "自动汇总", "运营节奏"],
        aiJudgement: "日报模板类内容热度稳定，适合承接团队场景和工作流类话题。",
        actions: ["补一篇日报模板拆解", "增加日报字段说明", "加入团队协作案例"],
        authors: ["运营自动化研究所：模板收藏高", "AI 产品黑板报：转发率稳定"],
        items: [
          {
            id: "cc-2001",
            time: "15:10",
            platform: "小红书",
            heat: 7.7,
            title: "AI 日报模板怎么搭，团队每天少开一次会",
            author: "运营自动化研究所",
            match: "命中关键词：日报模板、自动汇总、团队流程",
            tag: "高收藏",
            description: "模板型内容更容易沉淀收藏，适合作为工作流内容的配套选题。"
          }
        ]
      },
      {
        date: "2026-03-19",
        label: "03/19 周四",
        total: 16,
        hotCount: 1,
        topic: "自动化选题",
        reportReady: false,
        keywords: ["自动化选题", "内容工厂", "监控流程"],
        aiJudgement: "自动化选题热度中等，但与内容工厂和监控话题结合后更容易形成完整叙事。",
        actions: ["观察内容工厂相关词", "准备选题流程图", "保留为次级选题"],
        authors: ["代码制造局：案例导向", "AI 轻松学：概念导向"],
        items: [
          {
            id: "cc-1901",
            time: "11:55",
            platform: "B站",
            heat: 6.9,
            title: "我把自动化选题接进内容工厂之后，选题速度翻倍",
            author: "代码制造局",
            match: "命中关键词：自动化选题、内容工厂",
            tag: "观察中",
            description: "案例完整但热度一般，适合和日报机制组合成更强的话题。"
          }
        ]
      },
      {
        date: "2026-03-18",
        label: "03/18 周三",
        total: 14,
        hotCount: 1,
        topic: "团队协作",
        reportReady: false,
        keywords: ["团队协作", "代码评审", "流程约束"],
        aiJudgement: "团队协作类内容热度不高，但很适合作为承接型选题，帮助解释工作流落地细节。",
        actions: ["作为配套说明选题", "补团队角色分工图", "延后主推优先级"],
        authors: ["老韩聊 AI 开发：评论偏争议", "理性派工程师：讨论偏深"],
        items: [
          {
            id: "cc-1801",
            time: "09:20",
            platform: "微博",
            heat: 6.5,
            title: "团队协作里最容易被忽略的，其实是 AI 代码评审边界",
            author: "理性派工程师",
            match: "命中关键词：团队协作、代码评审",
            tag: "讨论型",
            description: "偏观点讨论，适合在热点选题后补充方法论内容。"
          }
        ]
      }
    ],
    reports: [
      {
        date: "2026-03-24",
        label: "03/24",
        summary: "团队工作流类内容明显升温",
        hotSummary:
          "从哪个工具更强转向如何接入真实工作流。前 10 条高热内容中有 6 条强调团队流程、模板复用和代码评审衔接。",
        topicCount: 7,
        hotContentCount: 10,
        metrics: { hotContent: 10, topics: 7, highPriority: 3, suggestedPlatform: "小红书" },
        topics: [
          {
            id: "topic-2401",
            title: "Claude Code 团队工作流模板",
            reason: "高热内容持续证明具体流程模板比泛工具介绍更容易获得收藏和转发。",
            growth: "可直接给团队复制使用，天然带有实操价值，适合做系列内容和资料包引流。",
            priority: "高优先级",
            source: "03/24 · 适合平台：小红书 / B站"
          },
          {
            id: "topic-2402",
            title: "Claude Code 和 Cursor 到底怎么分工",
            reason: "争议型话题点击率高，评论区常出现到底怎么选的决策困惑。",
            growth: "通过场景拆分而不是简单对比，更容易沉淀成系列矩阵内容。",
            priority: "中优先级",
            source: "03/24, 03/22 · 争议度高"
          },
          {
            id: "topic-2403",
            title: "运营团队如何把 AI 选题接进日报机制",
            reason: "内容监控和 AI 生成报告本身就是用户想象空间很大的工作流话题。",
            growth: "兼具方法论和产品感，容易引发想看工具细节的后续需求。",
            priority: "高优先级",
            source: "03/24 · 运营应用场景强"
          }
        ]
      },
      {
        date: "2026-03-23",
        label: "03/23",
        summary: "并行 Agent 与自动评审成主热点",
        hotSummary: "用户对多 agent 的协作方式和自动评审的可靠性非常敏感，更爱看真实试验和踩坑内容。",
        topicCount: 5,
        hotContentCount: 10,
        metrics: { hotContent: 10, topics: 5, highPriority: 2, suggestedPlatform: "B站" },
        topics: [
          {
            id: "topic-2301",
            title: "并行 Agent 工作流到底怎么配",
            reason: "用户需要知道分工方式和执行顺序，而不是只听概念。",
            growth: "案例足够具体时，收藏和转发会明显提升。",
            priority: "高优先级",
            source: "03/23 · 适合平台：B站 / 小红书"
          },
          {
            id: "topic-2302",
            title: "自动 Code Review 到底能替你省多少时间",
            reason: "管理者和开发者都在关心它是不是值得接进团队流程。",
            growth: "具备天然讨论度，适合做测评和实践拆解。",
            priority: "中优先级",
            source: "03/23 · 评论区争议高"
          }
        ]
      },
      {
        date: "2026-03-22",
        label: "03/22",
        summary: "工具对比和成本讨论热度高",
        hotSummary: "用户希望看到清晰的场景边界、成本估算和角色差异，而不是简单站队。",
        topicCount: 4,
        hotContentCount: 10,
        metrics: { hotContent: 10, topics: 4, highPriority: 1, suggestedPlatform: "知乎" },
        topics: [
          {
            id: "topic-2201",
            title: "不同角色应该怎么选 AI 编码工具",
            reason: "开发、测试、运营对工具的需求明显不同，容易引发共鸣。",
            growth: "适合做矩阵型内容，每个角色都能拆成一篇。",
            priority: "中优先级",
            source: "03/22 · 适合平台：知乎 / 小红书"
          }
        ]
      },
      {
        date: "2026-03-21",
        label: "03/21",
        summary: "新账号用案例切入，互动不错",
        hotSummary: "Vibe Coding 的案例内容有一定新鲜度，但还未形成稳定的爆款模式。",
        topicCount: 3,
        hotContentCount: 8,
        metrics: { hotContent: 8, topics: 3, highPriority: 1, suggestedPlatform: "B站" },
        topics: [
          {
            id: "topic-2101",
            title: "Vibe Coding 到底适合哪些轻量项目",
            reason: "新概念有讨论空间，但用户需要案例锚点。",
            growth: "适合做补充类栏目，不建议作为本周主推方向。",
            priority: "观察中",
            source: "03/21 · 适合平台：B站"
          }
        ]
      }
    ]
  },
  {
    id: "vibe-coding",
    name: "Vibe Coding 选题监控",
    subtitle: "3 平台 · 11 关键词 · 8 博主",
    status: "08:30 运行",
    runStatus: "等待运行",
    lastRun: "今天 08:30",
    platforms: [
      { id: "xiaohongshu", name: "小红书", short: "红", description: "生活方式", enabled: true },
      { id: "douyin", name: "抖音", short: "抖", description: "短视频", enabled: true },
      { id: "bilibili", name: "B站", short: "B", description: "案例展示", enabled: true }
    ],
    keywords: ["vibe coding", "独立开发", "AI side project", "0 到 1 搭建", "产品验证"],
    accounts: [
      {
        id: "side-project-lab",
        name: "独立开发研究所",
        platform: "小红书",
        avatar: "独",
        signal: "标题收藏高",
        status: "持续跟踪",
        lastFetched: "最近抓取 1 小时前"
      }
    ],
    strategy: {
      runTime: "08:30",
      window: "最近 24 小时",
      topN: 10,
      output: "日报 + 选题库"
    },
    contentDays: [
      {
        date: "2026-03-24",
        label: "03/24 周二",
        total: 19,
        hotCount: 2,
        topic: "独立开发项目拆解",
        reportReady: true,
        keywords: ["side project", "启动速度", "赚钱案例"],
        aiJudgement: "用户对快速验证和赚钱路径更感兴趣，而不是抽象概念。",
        actions: ["强化案例拆解", "增加收入验证内容", "减少概念解释"],
        authors: ["独立开发研究所：收藏高"],
        items: [
          {
            id: "vc-2401",
            time: "12:10",
            platform: "小红书",
            heat: 8.7,
            title: "我用 Vibe Coding 做了个小工具，一周拿到第一笔收入",
            author: "独立开发研究所",
            match: "命中关键词：vibe coding、赚钱案例",
            tag: "爆款",
            description: "案例有结果闭环，更容易激发关注和模仿。"
          }
        ]
      }
    ],
    reports: [
      {
        date: "2026-03-24",
        label: "03/24",
        summary: "赚钱案例和验证速度是核心吸引点",
        hotSummary: "用户对 side project 的兴趣更偏实际结果，尤其关注收入、验证时间和成本。",
        topicCount: 3,
        hotContentCount: 8,
        metrics: { hotContent: 8, topics: 3, highPriority: 2, suggestedPlatform: "小红书" },
        topics: [
          {
            id: "v-topic-1",
            title: "7 天做出可收费工具的完整流程",
            reason: "用户更想看到结果闭环和执行路径。",
            growth: "适合做系列内容，天然带有转化价值。",
            priority: "高优先级",
            source: "03/24 · 适合平台：小红书"
          }
        ]
      }
    ]
  },
  {
    id: "ai-tools",
    name: "AI 工具资讯监控",
    subtitle: "5 平台 · 24 关键词 · 16 博主",
    status: "等待运行",
    runStatus: "待检查",
    lastRun: "昨天 09:00",
    platforms: [
      { id: "xiaohongshu", name: "小红书", short: "红", description: "工具测评", enabled: true },
      { id: "douyin", name: "抖音", short: "抖", description: "短视频资讯", enabled: true },
      { id: "weibo", name: "微博", short: "微", description: "实时热点", enabled: true },
      { id: "bilibili", name: "B站", short: "B", description: "深度测评", enabled: true },
      { id: "zhihu", name: "知乎", short: "知", description: "观点分析", enabled: true }
    ],
    keywords: ["AI 工具", "新模型", "Agent", "生产力", "自动化"],
    accounts: [],
    strategy: {
      runTime: "09:00",
      window: "最近 24 小时",
      topN: 10,
      output: "日报 + 选题库"
    },
    contentDays: [
      {
        date: "2026-03-24",
        label: "03/24 周二",
        total: 12,
        hotCount: 1,
        topic: "新模型发布",
        reportReady: false,
        keywords: ["新模型", "发布", "性能比较"],
        aiJudgement: "更适合做快讯和筛选，不适合作为主监控模板展示。",
        actions: ["保留占位数据"],
        authors: ["工具情报站：快讯类"],
        items: []
      }
    ],
    reports: [
      {
        date: "2026-03-24",
        label: "03/24",
        summary: "资讯聚合为主，适合快讯视角",
        hotSummary: "热点分散，更适合做工具快报而不是深度单选题。",
        topicCount: 2,
        hotContentCount: 6,
        metrics: { hotContent: 6, topics: 2, highPriority: 1, suggestedPlatform: "微博" },
        topics: [
          {
            id: "ai-tools-1",
            title: "本周 AI 工具上新快报",
            reason: "内容分散但时效性强，适合聚合式输出。",
            growth: "适合做栏目，不适合单点爆文。",
            priority: "中优先级",
            source: "03/24 · 适合平台：微博"
          }
        ]
      }
    ]
  }
];

export const reportRanges = [
  { id: "7", label: "近 7 天", days: 7 },
  { id: "14", label: "近 14 天", days: 14 },
  { id: "30", label: "近 30 天", days: 30 }
];

export const accountPlatformOptions = ["小红书", "抖音", "微博", "B站", "知乎"];
