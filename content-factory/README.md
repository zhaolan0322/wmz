# Content Factory

Content Factory is a Next.js prototype for monitoring creator topics, collecting platform content, and generating AI-assisted topic reports.

## Features

- Multi-tab dashboard for content monitoring, report analysis, and settings
- Manual keyword search for WeChat and Xiaohongshu
- SiliconFlow-backed daily and keyword-based topic analysis
- Local report persistence and timeline views
- UI mockups for content, report, and settings workflows

## Tech Stack

- Next.js
- React
- Node.js route handlers
- SiliconFlow API

## Setup

1. Install dependencies:

```bash
npm install
```

2. Copy `.env.example` to `.env.local` and fill in your own credentials.

3. Start the app:

```bash
npm run dev
```

## Notes

- This public version removes hardcoded credentials and excludes local runtime data, build caches, and logs.
- Scheduled task scripts are included as examples and may need adjustment for your local Windows environment.
