import { Noto_Sans_SC } from "next/font/google";
import "./globals.css";

const notoSans = Noto_Sans_SC({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

export const metadata = {
  title: "内容监控台原型",
  description: "用于管理多平台内容监控、AI 报告和监控设置的前端原型。",
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN">
      <body className={notoSans.className}>{children}</body>
    </html>
  );
}
