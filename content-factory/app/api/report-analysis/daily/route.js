import { NextResponse } from "next/server";
import { runDailyReportAnalysis } from "../../../../lib/report-analysis.mjs";

export async function POST(request) {
  try {
    const body = await request.json().catch(() => ({}));
    const targetDate = body?.targetDate;
    const categoryId = body?.categoryId;
    const result = await runDailyReportAnalysis({ categoryId, targetDate });

    return NextResponse.json({
      msg: "ok",
      data: result,
    });
  } catch (error) {
    return NextResponse.json(
      {
        msg: error instanceof Error ? error.message : "日报分析失败。",
      },
      { status: 500 },
    );
  }
}
