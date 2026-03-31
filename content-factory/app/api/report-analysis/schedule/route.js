import { NextResponse } from "next/server";
import { getReportConfig, saveReportConfig } from "../../../../lib/report-storage.mjs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";

const execFileAsync = promisify(execFile);

export async function GET() {
  try {
    const config = await getReportConfig();
    return NextResponse.json({ msg: "ok", data: config });
  } catch (error) {
    return NextResponse.json(
      {
        msg: error instanceof Error ? error.message : "读取调度配置失败。",
      },
      { status: 500 },
    );
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const config = await saveReportConfig({
      dailyRunTime: body?.dailyRunTime,
      enabled: typeof body?.enabled === "boolean" ? body.enabled : undefined,
    });

    const scriptPath = path.join(process.cwd(), "scripts", "register-daily-report-task.ps1");
    await execFileAsync("powershell.exe", [
      "-NoProfile",
      "-ExecutionPolicy",
      "Bypass",
      "-File",
      scriptPath,
      "-Time",
      config.dailyRunTime,
      "-Enabled",
      config.enabled ? "true" : "false",
    ]);

    return NextResponse.json({ msg: "ok", data: config });
  } catch (error) {
    return NextResponse.json(
      {
        msg: error instanceof Error ? error.message : "保存调度配置失败。",
      },
      { status: 500 },
    );
  }
}
