import { NextResponse } from "next/server";
import { listGeneratedReports } from "../../../../lib/report-storage.mjs";

export async function GET(request) {
  try {
    const categoryId = request.nextUrl.searchParams.get("categoryId");
    const reports = await listGeneratedReports(categoryId);

    return NextResponse.json({
      msg: "ok",
      data: reports,
    });
  } catch (error) {
    return NextResponse.json(
      {
        msg: error instanceof Error ? error.message : "读取报告失败。",
      },
      { status: 500 },
    );
  }
}
