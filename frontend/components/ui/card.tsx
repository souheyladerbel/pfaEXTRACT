import type { PropsWithChildren } from "react";

import { cn } from "@/lib/utils";

type CardProps = PropsWithChildren<{
  className?: string;
}>;

export function Card({ children, className }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-[20px] border border-[rgba(137,146,171,0.18)] bg-white p-5 shadow-[0_10px_32px_rgba(19,29,61,0.05)]",
        "dark:border-white/10 dark:bg-[#121829] dark:shadow-[0_12px_38px_rgba(0,0,0,0.24)]",
        className
      )}
    >
      {children}
    </div>
  );
}
