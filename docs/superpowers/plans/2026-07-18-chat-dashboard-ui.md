# Chat Dashboard UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 3-column Next.js chat dashboard (sessions sidebar / chat window / sources-conflicts panel) for the SHB deposit RAG assistant, styled dark-mode with a Synapse-Dribbble-inspired look, wired to the real `POST /api/v1/chat` backend.

**Architecture:** Next.js 14 App Router single-page client app. All chat/session state lives in one client component (`app/page.tsx`); sessions persist to `localStorage` (backend has no session-list API). Backend needs one small addition — CORS — to accept browser requests from the Next.js dev origin.

**Tech Stack:** Next.js 14.2, React 18.3, TypeScript 5.6, Tailwind CSS 3.4, Radix UI primitives (tabs/scroll-area/avatar) hand-wired in shadcn/ui style, class-variance-authority, FastAPI `CORSMiddleware` on the backend.

**Spec:** `docs/superpowers/specs/2026-07-18-chat-dashboard-ui-design.md`

## Global Constraints

- UI language: Vietnamese, all copy in Vietnamese.
- Theme: dark mode only, no light/dark toggle. Accent gradient violet→blue (`hsl(258 90% 66%)` → `hsl(217 91% 60%)`).
- Desktop-first; no dedicated mobile work.
- Sessions stored client-side only (`localStorage`), no new backend endpoints besides CORS.
- API base URL from `NEXT_PUBLIC_API_URL`, default `http://localhost:8000`. Request timeout: 30s.
- No automated frontend test suite (explicit spec decision) — each frontend task is gated by `npm run typecheck` (and `npm run build` at the end); the final task is manual verification against the running backend.
- Backend keeps its existing pytest suite; the one backend change in this plan (CORS) gets a real pytest test.
- `block_reason` values: `none | out_of_scope | pii_detected | unsafe_advice_request | prompt_injection | input_too_long | low_confidence_answer` — must map to the Vietnamese labels in `lib/blockReasons.ts` (Task 3).

---

### Task 1: Backend — enable CORS for the frontend origin

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_main.py` (new)

**Interfaces:**
- Produces: `Settings.cors_origins: list[str]` (default `["http://localhost:3000"]`), consumed only inside `main.py`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_main.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_cors_allows_frontend_origin():
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_main.py -v`
Expected: FAIL — status code is `405` (no CORS middleware, Starlette rejects the OPTIONS preflight).

- [ ] **Step 3: Add `cors_origins` setting**

In `backend/app/core/config.py`, add this field to the `Settings` class, right after the `top_k_retrieval`/`similarity_threshold` block:

```python
    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:3000"]
```

- [ ] **Step 4: Wire `CORSMiddleware` into the app**

Replace the full contents of `backend/app/main.py` with:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 6: Run full backend suite to check nothing broke**

Run: `cd backend && pytest -v`
Expected: all tests PASS (existing `test_document_relation.py`, `test_guardrails.py`, plus the new `test_main.py`).

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/config.py backend/app/main.py backend/tests/test_main.py
git commit -m "feat(backend): enable CORS for frontend dev origin"
```

---

### Task 2: Frontend project scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next-env.d.ts`
- Create: `frontend/next.config.js`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/app/globals.css`
- Create: `frontend/app/layout.tsx`
- Create: `frontend/app/page.tsx` (placeholder, replaced in Task 8)

**Interfaces:**
- Produces: Tailwind color tokens `background, foreground, card, card-foreground, border, muted, muted-foreground, accent, accent-foreground, primary, primary-foreground, destructive, destructive-foreground, warning, warning-foreground`; utility class `.glass-card`; background utility `bg-synapse-gradient`; path alias `@/*` → `frontend/*`.

- [ ] **Step 1: Create `package.json`**

```json
{
  "name": "shb-chat-dashboard",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "14.2.15",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "@radix-ui/react-tabs": "1.1.1",
    "@radix-ui/react-scroll-area": "1.2.1",
    "@radix-ui/react-avatar": "1.1.1",
    "class-variance-authority": "0.7.0",
    "clsx": "2.1.1",
    "tailwind-merge": "2.5.4"
  },
  "devDependencies": {
    "typescript": "5.6.3",
    "@types/node": "20.16.11",
    "@types/react": "18.3.11",
    "@types/react-dom": "18.3.1",
    "tailwindcss": "3.4.14",
    "postcss": "8.4.47",
    "autoprefixer": "10.4.20",
    "eslint": "8.57.1",
    "eslint-config-next": "14.2.15"
  }
}
```

- [ ] **Step 2: Create `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "baseUrl": ".",
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Create `next-env.d.ts`**

```ts
/// <reference types="next" />
/// <reference types="next/image-types/global" />

// NOTE: This file should not be edited
// see https://nextjs.org/docs/app/api-reference/config/typescript for more information.
```

- [ ] **Step 4: Create `next.config.js`**

```js
/** @type {import('next').NextConfig} */
const nextConfig = {};

module.exports = nextConfig;
```

- [ ] **Step 5: Create `tailwind.config.ts`**

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: "hsl(var(--card))",
        "card-foreground": "hsl(var(--card-foreground))",
        border: "hsl(var(--border))",
        muted: "hsl(var(--muted))",
        "muted-foreground": "hsl(var(--muted-foreground))",
        accent: "hsl(var(--accent))",
        "accent-foreground": "hsl(var(--accent-foreground))",
        primary: "hsl(var(--primary))",
        "primary-foreground": "hsl(var(--primary-foreground))",
        destructive: "hsl(var(--destructive))",
        "destructive-foreground": "hsl(var(--destructive-foreground))",
        warning: "hsl(var(--warning))",
        "warning-foreground": "hsl(var(--warning-foreground))",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      backgroundImage: {
        "synapse-gradient": "linear-gradient(135deg, hsl(258 90% 66%) 0%, hsl(217 91% 60%) 100%)",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 6: Create `postcss.config.js`**

```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 7: Create `app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 240 10% 6%;
    --foreground: 240 10% 96%;
    --card: 240 10% 10%;
    --card-foreground: 240 10% 96%;
    --border: 240 8% 20%;
    --muted: 240 8% 16%;
    --muted-foreground: 240 6% 65%;
    --accent: 258 90% 66%;
    --accent-foreground: 0 0% 100%;
    --primary: 258 90% 66%;
    --primary-foreground: 0 0% 100%;
    --destructive: 0 72% 51%;
    --destructive-foreground: 0 0% 100%;
    --warning: 38 92% 50%;
    --warning-foreground: 20 14% 10%;
    --radius: 0.75rem;
  }

  * {
    border-color: hsl(var(--border));
  }

  body {
    background-color: hsl(var(--background));
    color: hsl(var(--foreground));
  }
}

@layer utilities {
  .glass-card {
    background-color: hsl(var(--card) / 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid hsl(var(--border));
  }
}
```

- [ ] **Step 8: Create `app/layout.tsx`**

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "vietnamese"] });

export const metadata: Metadata = {
  title: "SHB Chat — Tư vấn tiền gửi",
  description: "Trợ lý RAG tra cứu quy định tiền gửi SHB Bank",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" className="dark">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
```

- [ ] **Step 9: Create placeholder `app/page.tsx`**

```tsx
export default function HomePage() {
  return (
    <main className="flex h-screen items-center justify-center">
      <p className="text-muted-foreground">Đang tải dashboard...</p>
    </main>
  );
}
```

- [ ] **Step 10: Install and run**

Run: `cd frontend && npm install`
Expected: install completes with no errors.

Run: `npm run typecheck`
Expected: no errors.

Run: `npm run dev`
Expected: server starts on `http://localhost:3000`. Open it in a browser — dark background, centered text "Đang tải dashboard...". Stop the server (Ctrl+C) after confirming.

- [ ] **Step 11: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/next-env.d.ts frontend/next.config.js frontend/tailwind.config.ts frontend/postcss.config.js frontend/app/globals.css frontend/app/layout.tsx frontend/app/page.tsx
git commit -m "feat(frontend): scaffold Next.js 14 project with dark Synapse theme tokens"
```

---

### Task 3: Shared types and utility libraries

**Files:**
- Create: `frontend/types/chat.ts`
- Create: `frontend/lib/utils.ts`
- Create: `frontend/lib/api.ts`
- Create: `frontend/lib/sessions.ts`
- Create: `frontend/lib/blockReasons.ts`

**Interfaces:**
- Consumes: nothing (leaf layer).
- Produces:
  - `types/chat.ts`: `BlockReason`, `Source`, `Conflict`, `ChatApiResponse`, `MessageRole = "user" | "assistant" | "blocked" | "error"`, `Message { id, role, content, createdAt, sources?, conflicts?, blockReason? }`.
  - `lib/utils.ts`: `cn(...inputs: ClassValue[]): string`.
  - `lib/api.ts`: `class ChatApiError extends Error`, `sendChatMessage(sessionId: string, message: string): Promise<ChatApiResponse>`.
  - `lib/sessions.ts`: `interface StoredSession { id, title, createdAt, messages: Message[] }`, `loadSessions(): StoredSession[]`, `saveSessions(sessions: StoredSession[]): void`, `createSessionId(): string`, `upsertSession(sessions, session): StoredSession[]`, `deriveTitle(text: string): string`.
  - `lib/blockReasons.ts`: `BLOCK_REASON_LABELS: Record<BlockReason, string>`.

- [ ] **Step 1: Create `types/chat.ts`**

```ts
export type BlockReason =
  | "none"
  | "out_of_scope"
  | "pii_detected"
  | "unsafe_advice_request"
  | "prompt_injection"
  | "input_too_long"
  | "low_confidence_answer";

export interface Source {
  doc_id: string;
  title: string;
  clause: string;
  effective_date: string;
}

export interface Conflict {
  description: string;
  conflicting_sources: string[];
}

export interface ChatApiResponse {
  session_id: string;
  answer: string;
  sources: Source[];
  conflicts: Conflict[];
  blocked: boolean;
  block_reason: BlockReason;
}

export type MessageRole = "user" | "assistant" | "blocked" | "error";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  sources?: Source[];
  conflicts?: Conflict[];
  blockReason?: BlockReason;
}
```

- [ ] **Step 2: Create `lib/utils.ts`**

```ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 3: Create `lib/api.ts`**

```ts
import type { ChatApiResponse } from "@/types/chat";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 30000;

export class ChatApiError extends Error {}

export async function sendChatMessage(sessionId: string, message: string): Promise<ChatApiResponse> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new ChatApiError(`Máy chủ trả lỗi: ${response.status}`);
    }

    return (await response.json()) as ChatApiResponse;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ChatApiError("Hết thời gian chờ phản hồi từ máy chủ");
    }
    if (error instanceof ChatApiError) throw error;
    throw new ChatApiError("Không kết nối được máy chủ");
  } finally {
    clearTimeout(timeout);
  }
}
```

- [ ] **Step 4: Create `lib/sessions.ts`**

```ts
import type { Message } from "@/types/chat";

export interface StoredSession {
  id: string;
  title: string;
  createdAt: string;
  messages: Message[];
}

const STORAGE_KEY = "shb-chat-sessions";

export function loadSessions(): StoredSession[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as StoredSession[];
  } catch {
    return [];
  }
}

export function saveSessions(sessions: StoredSession[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export function createSessionId(): string {
  return crypto.randomUUID();
}

export function upsertSession(sessions: StoredSession[], session: StoredSession): StoredSession[] {
  const index = sessions.findIndex((s) => s.id === session.id);
  if (index === -1) return [session, ...sessions];
  const next = [...sessions];
  next[index] = session;
  return next;
}

export function deriveTitle(firstMessage: string): string {
  const trimmed = firstMessage.trim();
  return trimmed.length > 40 ? `${trimmed.slice(0, 40)}...` : trimmed;
}
```

- [ ] **Step 5: Create `lib/blockReasons.ts`**

```ts
import type { BlockReason } from "@/types/chat";

export const BLOCK_REASON_LABELS: Record<BlockReason, string> = {
  none: "",
  out_of_scope: "Ngoài phạm vi",
  pii_detected: "Thông tin cá nhân nhạy cảm",
  unsafe_advice_request: "Yêu cầu tư vấn tài chính cá nhân",
  prompt_injection: "Yêu cầu không hợp lệ",
  input_too_long: "Câu hỏi quá dài",
  low_confidence_answer: "Không đủ dữ liệu",
};
```

- [ ] **Step 6: Verify types compile**

Run: `cd frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/types frontend/lib/utils.ts frontend/lib/api.ts frontend/lib/sessions.ts frontend/lib/blockReasons.ts
git commit -m "feat(frontend): add chat types, API client, session storage, block-reason labels"
```

---

### Task 4: UI primitives (shadcn-style)

**Files:**
- Create: `frontend/components/ui/button.tsx`
- Create: `frontend/components/ui/card.tsx`
- Create: `frontend/components/ui/badge.tsx`
- Create: `frontend/components/ui/tabs.tsx`
- Create: `frontend/components/ui/scroll-area.tsx`
- Create: `frontend/components/ui/avatar.tsx`
- Create: `frontend/components/ui/textarea.tsx`

**Interfaces:**
- Consumes: `cn` from `lib/utils.ts` (Task 3).
- Produces: `Button, buttonVariants`; `Card`; `Badge, badgeVariants` (variants: `default | destructive | warning`); `Tabs, TabsList, TabsTrigger, TabsContent`; `ScrollArea`; `Avatar, AvatarFallback`; `Textarea`.

- [ ] **Step 1: Create `components/ui/button.tsx`**

```tsx
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:opacity-90",
        outline: "border border-border bg-transparent hover:bg-muted",
        ghost: "hover:bg-muted",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-8 px-3 text-xs",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return <button ref={ref} className={cn(buttonVariants({ variant, size, className }))} {...props} />;
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
```

- [ ] **Step 2: Create `components/ui/card.tsx`**

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => <div ref={ref} className={cn("glass-card rounded-lg", className)} {...props} />
);
Card.displayName = "Card";

export { Card };
```

- [ ] **Step 3: Create `components/ui/badge.tsx`**

```tsx
import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", {
  variants: {
    variant: {
      default: "bg-primary/15 text-primary",
      destructive: "bg-destructive/15 text-destructive",
      warning: "bg-warning/15 text-warning",
    },
  },
  defaultVariants: { variant: "default" },
});

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
```

- [ ] **Step 4: Create `components/ui/tabs.tsx`**

```tsx
"use client";

import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List ref={ref} className={cn("inline-flex items-center rounded-md bg-muted p-1", className)} {...props} />
));
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "rounded-sm px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors data-[state=active]:bg-primary data-[state=active]:text-primary-foreground",
      className
    )}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => <TabsPrimitive.Content ref={ref} className={cn("mt-3", className)} {...props} />);
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
```

- [ ] **Step 5: Create `components/ui/scroll-area.tsx`**

```tsx
"use client";

import * as React from "react";
import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area";
import { cn } from "@/lib/utils";

const ScrollArea = React.forwardRef<
  React.ElementRef<typeof ScrollAreaPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root>
>(({ className, children, ...props }, ref) => (
  <ScrollAreaPrimitive.Root ref={ref} className={cn("relative overflow-hidden", className)} {...props}>
    <ScrollAreaPrimitive.Viewport className="h-full w-full">{children}</ScrollAreaPrimitive.Viewport>
    <ScrollAreaPrimitive.Scrollbar orientation="vertical" className="flex w-2 touch-none select-none bg-transparent p-0.5">
      <ScrollAreaPrimitive.Thumb className="relative flex-1 rounded-full bg-border" />
    </ScrollAreaPrimitive.Scrollbar>
  </ScrollAreaPrimitive.Root>
));
ScrollArea.displayName = ScrollAreaPrimitive.Root.displayName;

export { ScrollArea };
```

- [ ] **Step 6: Create `components/ui/avatar.tsx`**

```tsx
"use client";

import * as React from "react";
import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cn } from "@/lib/utils";

const Avatar = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Root
    ref={ref}
    className={cn("flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full", className)}
    {...props}
  />
));
Avatar.displayName = AvatarPrimitive.Root.displayName;

const AvatarFallback = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Fallback>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Fallback>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Fallback
    ref={ref}
    className={cn("flex h-full w-full items-center justify-center bg-synapse-gradient text-xs font-semibold text-white", className)}
    {...props}
  />
));
AvatarFallback.displayName = AvatarPrimitive.Fallback.displayName;

export { Avatar, AvatarFallback };
```

- [ ] **Step 7: Create `components/ui/textarea.tsx`**

```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex w-full resize-none rounded-md border border-border bg-muted/50 px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
);
Textarea.displayName = "Textarea";

export { Textarea };
```

- [ ] **Step 8: Verify**

Run: `cd frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 9: Commit**

```bash
git add frontend/components/ui
git commit -m "feat(frontend): add shadcn-style UI primitives (button, card, badge, tabs, scroll-area, avatar, textarea)"
```

---

### Task 5: Chat components

**Files:**
- Create: `frontend/components/chat/MessageBubble.tsx`
- Create: `frontend/components/chat/TypingIndicator.tsx`
- Create: `frontend/components/chat/MessageInput.tsx`
- Create: `frontend/components/chat/MessageList.tsx`
- Create: `frontend/components/chat/ChatWindow.tsx`

**Interfaces:**
- Consumes: `Message` type (Task 3), `BLOCK_REASON_LABELS` (Task 3), `cn` (Task 3), `Avatar/AvatarFallback/Badge/Button/Textarea/ScrollArea` (Task 4).
- Produces: `ChatWindow(props: { messages: Message[]; isSending: boolean; selectedMessageId: string | null; onSelectMessage: (id: string) => void; onSend: (text: string) => void; onRetry: () => void })`.

- [ ] **Step 1: Create `components/chat/MessageBubble.tsx`**

```tsx
"use client";

import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { BLOCK_REASON_LABELS } from "@/lib/blockReasons";
import type { Message } from "@/types/chat";

interface MessageBubbleProps {
  message: Message;
  isSelected: boolean;
  onSelect: (messageId: string) => void;
  onRetry: () => void;
}

export function MessageBubble({ message, isSelected, onSelect, onRetry }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isBlocked = message.role === "blocked";
  const isError = message.role === "error";
  const isAssistant = message.role === "assistant";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <Avatar>
        <AvatarFallback>{isUser ? "B" : "AI"}</AvatarFallback>
      </Avatar>
      <div className={cn("flex max-w-[75%] flex-col gap-1", isUser && "items-end")}>
        <button
          type="button"
          disabled={!isAssistant}
          onClick={() => isAssistant && onSelect(message.id)}
          className={cn(
            "rounded-lg px-4 py-2.5 text-left text-sm leading-relaxed",
            isUser && "bg-synapse-gradient text-white",
            isAssistant && "glass-card cursor-pointer text-foreground",
            isAssistant && isSelected && "ring-1 ring-primary",
            isBlocked && "border border-warning/40 bg-warning/10 text-warning-foreground",
            isError && "border border-destructive/40 bg-destructive/10 text-destructive"
          )}
        >
          {isBlocked && message.blockReason && (
            <Badge variant="warning" className="mb-2">
              {BLOCK_REASON_LABELS[message.blockReason]}
            </Badge>
          )}
          <p>{message.content}</p>
        </button>
        {isError && (
          <Button size="sm" variant="outline" onClick={onRetry}>
            Thử lại
          </Button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `components/chat/TypingIndicator.tsx`**

```tsx
export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-2.5">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground" />
    </div>
  );
}
```

- [ ] **Step 3: Create `components/chat/MessageInput.tsx`**

```tsx
"use client";

import { useState, type KeyboardEvent } from "react";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";

interface MessageInputProps {
  disabled: boolean;
  onSend: (message: string) => void;
}

export function MessageInput({ disabled, onSend }: MessageInputProps) {
  const [value, setValue] = useState("");

  function handleSubmit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="flex items-end gap-2 border-t border-border p-4">
      <Textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder="Hỏi về quy định tiền gửi SHB..."
        rows={2}
        className="flex-1"
      />
      <Button onClick={handleSubmit} disabled={disabled || !value.trim()}>
        Gửi
      </Button>
    </div>
  );
}
```

- [ ] **Step 4: Create `components/chat/MessageList.tsx`**

```tsx
"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import type { Message } from "@/types/chat";

interface MessageListProps {
  messages: Message[];
  isSending: boolean;
  selectedMessageId: string | null;
  onSelectMessage: (messageId: string) => void;
  onRetry: () => void;
}

export function MessageList({ messages, isSending, selectedMessageId, onSelectMessage, onRetry }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isSending]);

  return (
    <ScrollArea className="flex-1 px-4">
      <div className="flex flex-col gap-4 py-4">
        {messages.length === 0 && (
          <p className="mt-10 text-center text-sm text-muted-foreground">
            Bắt đầu hỏi về lãi suất, kỳ hạn, điều khoản tiền gửi SHB.
          </p>
        )}
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            isSelected={message.id === selectedMessageId}
            onSelect={onSelectMessage}
            onRetry={onRetry}
          />
        ))}
        {isSending && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
```

- [ ] **Step 5: Create `components/chat/ChatWindow.tsx`**

```tsx
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import type { Message } from "@/types/chat";

interface ChatWindowProps {
  messages: Message[];
  isSending: boolean;
  selectedMessageId: string | null;
  onSelectMessage: (messageId: string) => void;
  onSend: (message: string) => void;
  onRetry: () => void;
}

export function ChatWindow({ messages, isSending, selectedMessageId, onSelectMessage, onSend, onRetry }: ChatWindowProps) {
  return (
    <section className="flex h-full flex-1 flex-col">
      <MessageList
        messages={messages}
        isSending={isSending}
        selectedMessageId={selectedMessageId}
        onSelectMessage={onSelectMessage}
        onRetry={onRetry}
      />
      <MessageInput disabled={isSending} onSend={onSend} />
    </section>
  );
}
```

- [ ] **Step 6: Verify**

Run: `cd frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/chat
git commit -m "feat(frontend): add chat window components (bubble, input, list, typing indicator)"
```

---

### Task 6: Sidebar components

**Files:**
- Create: `frontend/components/sidebar/NewChatButton.tsx`
- Create: `frontend/components/sidebar/SessionList.tsx`
- Create: `frontend/components/sidebar/Sidebar.tsx`

**Interfaces:**
- Consumes: `StoredSession` type (Task 3), `cn` (Task 3), `Button/ScrollArea` (Task 4).
- Produces: `Sidebar(props: { sessions: StoredSession[]; activeSessionId: string | null; onNewChat: () => void; onSelectSession: (id: string) => void })`.

- [ ] **Step 1: Create `components/sidebar/NewChatButton.tsx`**

```tsx
import { Button } from "@/components/ui/button";

interface NewChatButtonProps {
  onClick: () => void;
}

export function NewChatButton({ onClick }: NewChatButtonProps) {
  return (
    <Button onClick={onClick} className="w-full justify-start">
      + Cuộc trò chuyện mới
    </Button>
  );
}
```

- [ ] **Step 2: Create `components/sidebar/SessionList.tsx`**

```tsx
"use client";

import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { StoredSession } from "@/lib/sessions";

interface SessionListProps {
  sessions: StoredSession[];
  activeSessionId: string | null;
  onSelect: (sessionId: string) => void;
}

export function SessionList({ sessions, activeSessionId, onSelect }: SessionListProps) {
  return (
    <ScrollArea className="flex-1">
      <div className="flex flex-col gap-1 p-2">
        {sessions.map((session) => (
          <button
            key={session.id}
            type="button"
            onClick={() => onSelect(session.id)}
            className={cn(
              "rounded-md px-3 py-2 text-left text-sm text-muted-foreground transition-colors hover:bg-muted",
              session.id === activeSessionId && "bg-muted text-foreground"
            )}
          >
            <p className="truncate font-medium">{session.title || "Cuộc trò chuyện mới"}</p>
            <p className="text-xs text-muted-foreground">{new Date(session.createdAt).toLocaleString("vi-VN")}</p>
          </button>
        ))}
      </div>
    </ScrollArea>
  );
}
```

- [ ] **Step 3: Create `components/sidebar/Sidebar.tsx`**

```tsx
import { NewChatButton } from "./NewChatButton";
import { SessionList } from "./SessionList";
import type { StoredSession } from "@/lib/sessions";

interface SidebarProps {
  sessions: StoredSession[];
  activeSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
}

export function Sidebar({ sessions, activeSessionId, onNewChat, onSelectSession }: SidebarProps) {
  return (
    <aside className="glass-card flex h-full w-72 flex-col gap-3 rounded-none border-r border-border p-3">
      <div className="flex items-center gap-2 px-1 py-2">
        <div className="h-8 w-8 rounded-lg bg-synapse-gradient" />
        <span className="text-sm font-semibold">SHB Trợ lý tiền gửi</span>
      </div>
      <NewChatButton onClick={onNewChat} />
      <SessionList sessions={sessions} activeSessionId={activeSessionId} onSelect={onSelectSession} />
    </aside>
  );
}
```

- [ ] **Step 4: Verify**

Run: `cd frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/sidebar
git commit -m "feat(frontend): add sidebar session list and new-chat button"
```

---

### Task 7: Insights panel components

**Files:**
- Create: `frontend/components/insights/SourcesTab.tsx`
- Create: `frontend/components/insights/ConflictsTab.tsx`
- Create: `frontend/components/insights/InsightsPanel.tsx`

**Interfaces:**
- Consumes: `Source, Conflict, Message` types (Task 3), `Card/Badge/Tabs/TabsList/TabsTrigger/TabsContent` (Task 4).
- Produces: `InsightsPanel(props: { selectedMessage: Message | null })`.

- [ ] **Step 1: Create `components/insights/SourcesTab.tsx`**

```tsx
import { Card } from "@/components/ui/card";
import type { Source } from "@/types/chat";

interface SourcesTabProps {
  sources: Source[];
}

export function SourcesTab({ sources }: SourcesTabProps) {
  if (sources.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">Chưa có nguồn trích dẫn nào.</p>;
  }

  return (
    <div className="flex flex-col gap-3 p-4">
      {sources.map((source, index) => (
        <Card key={`${source.doc_id}-${index}`} className="p-3">
          <p className="text-sm font-medium">{source.title}</p>
          <p className="text-xs text-muted-foreground">{source.clause}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Hiệu lực: {source.effective_date} · Mã: {source.doc_id}
          </p>
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create `components/insights/ConflictsTab.tsx`**

```tsx
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Conflict } from "@/types/chat";

interface ConflictsTabProps {
  conflicts: Conflict[];
}

export function ConflictsTab({ conflicts }: ConflictsTabProps) {
  if (conflicts.length === 0) {
    return <p className="p-4 text-sm text-muted-foreground">Không phát hiện mâu thuẫn nào.</p>;
  }

  return (
    <div className="flex flex-col gap-3 p-4">
      {conflicts.map((conflict, index) => (
        <Card key={index} className="p-3">
          <Badge variant="destructive" className="mb-2">
            Mâu thuẫn
          </Badge>
          <p className="text-sm">{conflict.description}</p>
          <p className="mt-1 text-xs text-muted-foreground">Nguồn xung đột: {conflict.conflicting_sources.join(", ")}</p>
        </Card>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Create `components/insights/InsightsPanel.tsx`**

```tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { SourcesTab } from "./SourcesTab";
import { ConflictsTab } from "./ConflictsTab";
import type { Message } from "@/types/chat";

interface InsightsPanelProps {
  selectedMessage: Message | null;
}

export function InsightsPanel({ selectedMessage }: InsightsPanelProps) {
  const sources = selectedMessage?.sources ?? [];
  const conflicts = selectedMessage?.conflicts ?? [];

  return (
    <aside className="glass-card flex h-full w-80 flex-col rounded-none border-l border-border p-3">
      <p className="px-1 py-2 text-sm font-semibold">Thông tin trích dẫn</p>
      <Tabs defaultValue="sources" className="flex flex-1 flex-col">
        <TabsList>
          <TabsTrigger value="sources">Nguồn trích dẫn</TabsTrigger>
          <TabsTrigger value="conflicts" className="relative">
            Mâu thuẫn
            {conflicts.length > 0 && (
              <Badge variant="destructive" className="ml-1.5 px-1.5 py-0">
                {conflicts.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>
        <TabsContent value="sources" className="flex-1 overflow-y-auto">
          <SourcesTab sources={sources} />
        </TabsContent>
        <TabsContent value="conflicts" className="flex-1 overflow-y-auto">
          <ConflictsTab conflicts={conflicts} />
        </TabsContent>
      </Tabs>
    </aside>
  );
}
```

- [ ] **Step 4: Verify**

Run: `cd frontend && npm run typecheck`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/insights
git commit -m "feat(frontend): add insights panel with sources and conflicts tabs"
```

---

### Task 8: Dashboard wiring (replace placeholder page)

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `Sidebar` (Task 6), `ChatWindow` (Task 5), `InsightsPanel` (Task 7), `sendChatMessage`/`ChatApiError` (Task 3), `createSessionId`/`deriveTitle`/`loadSessions`/`saveSessions`/`upsertSession`/`StoredSession` (Task 3), `Message` (Task 3).

- [ ] **Step 1: Replace `app/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { InsightsPanel } from "@/components/insights/InsightsPanel";
import { sendChatMessage, ChatApiError } from "@/lib/api";
import {
  createSessionId,
  deriveTitle,
  loadSessions,
  saveSessions,
  upsertSession,
  type StoredSession,
} from "@/lib/sessions";
import type { Message } from "@/types/chat";

function lastMessageOfRole(session: StoredSession | undefined, role: Message["role"]) {
  if (!session) return null;
  return [...session.messages].reverse().find((m) => m.role === role) ?? null;
}

export default function HomePage() {
  const [sessions, setSessions] = useState<StoredSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    const stored = loadSessions();
    setSessions(stored);
    if (stored.length > 0) {
      setActiveSessionId(stored[0].id);
      setSelectedMessageId(lastMessageOfRole(stored[0], "assistant")?.id ?? null);
    }
  }, []);

  function updateSessions(updater: (prev: StoredSession[]) => StoredSession[]) {
    setSessions((prev) => {
      const next = updater(prev);
      saveSessions(next);
      return next;
    });
  }

  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const selectedMessage = activeSession?.messages.find((m) => m.id === selectedMessageId) ?? null;

  function handleNewChat() {
    setActiveSessionId(createSessionId());
    setSelectedMessageId(null);
  }

  function handleSelectSession(sessionId: string) {
    setActiveSessionId(sessionId);
    const session = sessions.find((s) => s.id === sessionId);
    setSelectedMessageId(lastMessageOfRole(session, "assistant")?.id ?? null);
  }

  function appendMessage(sessionId: string, message: Message, seedTitle: string) {
    updateSessions((prev) => {
      const existing = prev.find((s) => s.id === sessionId);
      const updatedSession: StoredSession = existing
        ? { ...existing, messages: [...existing.messages, message] }
        : { id: sessionId, title: deriveTitle(seedTitle), createdAt: new Date().toISOString(), messages: [message] };
      return upsertSession(prev, updatedSession);
    });
  }

  async function callApiAndAppend(sessionId: string, text: string) {
    setIsSending(true);
    try {
      const response = await sendChatMessage(sessionId, text);
      const replyMessage: Message = response.blocked
        ? {
            id: crypto.randomUUID(),
            role: "blocked",
            content: response.answer,
            createdAt: new Date().toISOString(),
            blockReason: response.block_reason,
          }
        : {
            id: crypto.randomUUID(),
            role: "assistant",
            content: response.answer,
            createdAt: new Date().toISOString(),
            sources: response.sources,
            conflicts: response.conflicts,
          };
      appendMessage(sessionId, replyMessage, text);
      if (!response.blocked) setSelectedMessageId(replyMessage.id);
    } catch (error) {
      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: "error",
        content: error instanceof ChatApiError ? error.message : "Đã có lỗi không xác định xảy ra",
        createdAt: new Date().toISOString(),
      };
      appendMessage(sessionId, errorMessage, text);
    } finally {
      setIsSending(false);
    }
  }

  async function handleSend(text: string) {
    const sessionId = activeSessionId ?? createSessionId();
    setActiveSessionId(sessionId);

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      createdAt: new Date().toISOString(),
    };
    appendMessage(sessionId, userMessage, text);

    await callApiAndAppend(sessionId, text);
  }

  async function handleRetry() {
    if (!activeSession) return;
    const lastUserMessage = lastMessageOfRole(activeSession, "user");
    if (!lastUserMessage) return;
    await callApiAndAppend(activeSession.id, lastUserMessage.content);
  }

  return (
    <main className="flex h-screen overflow-hidden">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
      />
      <ChatWindow
        messages={activeSession?.messages ?? []}
        isSending={isSending}
        selectedMessageId={selectedMessageId}
        onSelectMessage={setSelectedMessageId}
        onSend={handleSend}
        onRetry={handleRetry}
      />
      <InsightsPanel selectedMessage={selectedMessage} />
    </main>
  );
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npm run typecheck`
Expected: no errors.

Run: `npm run build`
Expected: production build succeeds.

- [ ] **Step 3: Manual smoke check (no backend needed yet)**

Run: `npm run dev`, open `http://localhost:3000`.
Expected: 3-column dark dashboard renders — sidebar (empty, "+ Cuộc trò chuyện mới" button), empty chat window with placeholder text, insights panel showing "Chưa có nguồn trích dẫn nào." Type a message and press Enter — a user bubble appears, typing indicator shows, then either an assistant/blocked bubble or a network-error bubble (backend not running yet is fine — expect the error bubble with "Thử lại" button). Stop the server after confirming.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat(frontend): wire dashboard state — sessions, chat send/retry, blocked handling"
```

---

### Task 9: End-to-end manual verification against the real backend

**Files:** none (verification only).

- [ ] **Step 1: Prepare backend `.env`**

Confirm `backend/.env` has `OPENROUTER_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY` set (per root `README.md` run instructions). If data hasn't been ingested yet, run `cd backend && python -m scripts.ingest` first.

- [ ] **Step 2: Start backend**

Run: `cd backend && uvicorn app.main:app --reload`
Expected: server on `http://localhost:8000`, `GET /api/v1/health` returns `{"status": "ok"}`.

- [ ] **Step 3: Start frontend**

Run (new terminal): `cd frontend && npm run dev`
Expected: server on `http://localhost:3000`.

- [ ] **Step 4: Case 1 — normal answer with sources**

In the browser, send: `Lãi suất gửi tiết kiệm 6 tháng hiện nay là bao nhiêu?`
Expected: assistant bubble appears with an answer; it's auto-selected; the right panel's "Nguồn trích dẫn" tab lists at least one source (doc_id/title/clause/effective_date).

- [ ] **Step 5: Case 2 — conflicting sources (if ingested test data includes a conflict case)**

Send a question known to hit two conflicting clauses in the ingested data.
Expected: assistant bubble's answer mentions the conflict; "Mâu thuẫn" tab shows a red badge with count ≥ 1 and lists `description` + `conflicting_sources`.
If no conflict test data is loaded, skip this case and note it — not a plan blocker.

- [ ] **Step 6: Case 3 — blocked request**

Send a question containing PII (e.g. a fake CMND/CCCD number) or clearly out of scope (e.g. "Thời tiết hôm nay thế nào?").
Expected: a yellow/warning bubble appears instead of a normal answer, showing the Vietnamese label from `BLOCK_REASON_LABELS` matching the returned `block_reason`.

- [ ] **Step 7: Case 4 — network error and retry**

Stop the backend (Ctrl+C in its terminal). Send any message.
Expected: red error bubble "Không kết nối được máy chủ" with a "Thử lại" button. Restart the backend, click "Thử lại".
Expected: the retry succeeds and an assistant bubble appears, without a duplicate user bubble.

- [ ] **Step 8: Case 5 — session persistence**

Refresh the browser page.
Expected: the sidebar still lists the session(s) just created; clicking one restores its full message history including sources/conflicts on the previously selected message.

- [ ] **Step 9: Record result**

No commit needed for this task — it's verification only. If any case fails, fix the relevant component from Tasks 5-8 and re-run the failing case before considering the plan complete.

---

## Self-Review Notes

- **Spec coverage:** architecture/stack (Task 2), 3-column layout (Tasks 5-8), session localStorage (Task 3, 8), sources/conflicts panel (Task 7), blocked-bubble styling (Task 5), error+retry (Task 5, 8), CORS gap found during research and fixed (Task 1), manual 3-case testing from spec's Testing section covered plus persistence and error cases (Task 9).
- **Type consistency checked:** `Message["role"]` used consistently across `MessageBubble`, `MessageList`, `page.tsx`; `StoredSession` shape identical in `lib/sessions.ts` and all consumers; `ChatApiResponse` field names (`session_id`, `answer`, `sources`, `conflicts`, `blocked`, `block_reason`) match `doc/API_CONTRACT.md` and the actual Pydantic schema in `backend/app/models/schemas.py`.
- **No placeholders:** every step has complete, runnable code.
