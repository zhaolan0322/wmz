import { NextResponse } from "next/server";
import { runKeywordReportAnalysis } from "../../../../lib/report-analysis.mjs";

export async function POST(request) {
  try {
    const body = await request.json();
    const report = await runKeywordReportAnalysis({
      categoryId: body?.categoryId,
      keyword: body?.keyword,
      targetDate: body?.targetDate,
    });

    return NextResponse.json({
      msg: "ok",
      data: report,
    });
  } catch (error) {
    return NextResponse.json(
      {
        msg: error instanceof Error ? error.message : "定向报告分析失败。",
      },
      { status: 500 },
    );
  }
}
