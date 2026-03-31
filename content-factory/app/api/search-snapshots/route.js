import { NextResponse } from "next/server";
import { listRecentSnapshotStates } from "../../../lib/report-storage.mjs";

export async function GET(request) {
  try {
    const categoryId = request.nextUrl.searchParams.get("categoryId");
    const limit = Number.parseInt(request.nextUrl.searchParams.get("limit") || "7", 10) || 7;
    const states = await listRecentSnapshotStates({ categoryId, limit });

    return NextResponse.json({
      msg: "ok",
      data: states,
    });
  } catch (error) {
    return NextResponse.json(
      {
        msg: error instanceof Error ? error.message : "读取抓取快照失败。",
      },
      { status: 500 },
    );
  }
}
