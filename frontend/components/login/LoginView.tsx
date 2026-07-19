"use client";

import { useState, type KeyboardEvent } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { login, AuthApiError } from "@/lib/api";
import type { LoginApiResponse } from "@/types/auth";

interface LoginViewProps {
  onLoginSuccess: (response: LoginApiResponse) => void;
  onBackToChat: () => void;
}

export function LoginView({ onLoginSuccess, onBackToChat }: LoginViewProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    if (!email.trim() || !password.trim()) {
      setError("Vui lòng nhập đầy đủ email và mật khẩu.");
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const response = await login(email.trim(), password);
      onLoginSuccess(response);
    } catch (err) {
      setError(err instanceof AuthApiError ? err.message : "Không kết nối được máy chủ");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") void handleSubmit();
  }

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background">
      <Card className="flex w-[380px] flex-col gap-5 p-9 shadow-sm">
        <div className="flex flex-col items-center gap-2.5 text-center">
          <div className="flex h-11 w-11 items-center justify-center rounded-[13px] bg-primary text-[15px] font-extrabold text-primary-foreground">
            NB
          </div>
          <span className="text-base font-bold">Đăng nhập quản trị</span>
          <span className="text-[12.5px] text-muted-foreground">
            Dành cho nhân viên quản trị hệ thống tư vấn
          </span>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-muted-foreground">Email / Tên đăng nhập</label>
          <input
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
              setError(null);
            }}
            onKeyDown={handleKeyDown}
            placeholder="admin@gmail.com"
            disabled={isSubmitting}
            className="rounded-[10px] border border-border px-3.5 py-2.5 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-semibold text-muted-foreground">Mật khẩu</label>
          <input
            type="password"
            value={password}
            onChange={(event) => {
              setPassword(event.target.value);
              setError(null);
            }}
            onKeyDown={handleKeyDown}
            placeholder="••••••••"
            disabled={isSubmitting}
            className="rounded-[10px] border border-border px-3.5 py-2.5 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
          />
        </div>

        {error && (
          <div className="rounded-lg bg-destructive/10 px-3 py-2 text-[12.5px] text-destructive">{error}</div>
        )}

        <Button onClick={handleSubmit} disabled={isSubmitting} className="w-full justify-center py-3">
          {isSubmitting ? "Đang đăng nhập..." : "Đăng nhập"}
        </Button>
        <button
          type="button"
          onClick={onBackToChat}
          className="cursor-pointer text-center text-[12.5px] text-muted-foreground hover:text-foreground"
        >
          ← Quay lại giao diện Chat
        </button>
      </Card>
    </div>
  );
}
