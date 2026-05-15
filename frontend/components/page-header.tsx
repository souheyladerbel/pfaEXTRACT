import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  chips?: string[];
  action?: ReactNode;
};

export function PageHeader({
  eyebrow: _eyebrow,
  title,
  description,
  chips = [],
  action
}: PageHeaderProps) {
  return (
    <div className="space-y-2">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="max-w-4xl">
          <h1 className="proto-title text-[28px] font-bold leading-tight tracking-tight text-[#1b2440] dark:text-white md:text-[30px]">
            {title}
          </h1>
          <p className="mt-1.5 max-w-3xl text-sm leading-6 text-[#7a83a2] dark:text-[#96a1c2]">
            {description}
          </p>
          {chips.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {chips.map((chip) => (
                <Badge key={chip} tone="purple">
                  {chip}
                </Badge>
              ))}
            </div>
          ) : null}
        </div>
        {action ? <div className="w-full max-w-full xl:w-auto">{action}</div> : null}
      </div>
    </div>
  );
}
