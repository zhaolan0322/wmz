import { NextResponse } from "next/server";

const PLATFORM_ROUTE_MAP = {
  公众号: "/api/wechat-search",
  小红书: "/api/xhs-search",
};

export async function POST(request) {
  try {
    const body = await request.json();
    const platform = String(body?.activePlatform ?? "全部").trim();
    const targetRoute = resolveTargetRoute(platform);

    if (!targetRoute) {
      return NextResponse.json(
        {
          msg:
            platform === "全部"
              ? "请选择具体平台后再检索。"
              : `当前仅接入了公众号和小红书检索 API，${platform} 的检索接口尚未配置。`,
        },
        { status: 400 },
      );
    }

    const targetUrl = new URL(targetRoute, request.url);
    const response = await fetch(targetUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const payload = await response.json();
    return NextResponse.json(payload, { status: response.status });
  } catch (error) {
    return NextResponse.json(
      {
        msg: error instanceof Error ? error.message : "平台检索失败，请稍后重试。",
      },
      { status: 502 },
    );
  }
}

function resolveTargetRoute(platform) {
  if (PLATFORM_ROUTE_MAP[platform]) {
    return PLATFORM_ROUTE_MAP[platform];
  }

  return null;
}
