import type { Metadata } from 'next';
import './globals.css';

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000';

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: '词流 LexiFlow — 把英语用进对话里',
  description: '面向英语口语与雅思的高频词汇学习工具。',
  openGraph: {
    title: '词流 LexiFlow — 把英语用进对话里',
    description: '口语高频词与雅思核心词，学完立刻能开口。',
    type: 'website',
    images: [{ url: '/og.png', width: 1200, height: 630, alt: '词流 LexiFlow — 把英语用进对话里' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: '词流 LexiFlow — 把英语用进对话里',
    description: '口语高频词与雅思核心词，学完立刻能开口。',
    images: ['/og.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
