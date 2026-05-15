import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { HistoryDetail } from "@/lib/types";
import { resolveApiUrl } from "@/lib/api";

function renderValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function flattenPayload(payload: Record<string, unknown>, prefix = "") {
  const rows: { label: string; value: string }[] = [];
  for (const [key, value] of Object.entries(payload)) {
    if (key === "_meta") {
      continue;
    }
    const label = prefix ? `${prefix}.${key}` : key;
    if (Array.isArray(value)) {
      if (!value.length) {
        rows.push({ label, value: "[]" });
        continue;
      }
      value.forEach((item, index) => {
        if (item && typeof item === "object") {
          rows.push(...flattenPayload(item as Record<string, unknown>, `${label}[${index}]`));
        } else {
          rows.push({ label: `${label}[${index}]`, value: renderValue(item) });
        }
      });
      continue;
    }
    if (value && typeof value === "object") {
      rows.push(...flattenPayload(value as Record<string, unknown>, label));
      continue;
    }
    rows.push({ label, value: renderValue(value) });
  }
  return rows;
}

export function ResultDetail({
  detail,
  layout = "full",
}: {
  detail: HistoryDetail | null;
  layout?: "full" | "stacked";
}) {
  if (!detail) {
    return (
      <Card className="flex min-h-[360px] items-center justify-center">
        <div className="max-w-md text-center">
          <div className="proto-title text-xl font-bold text-[#1b2440] dark:text-white">
            Aucun document selectionne
          </div>
          <p className="mt-3 text-sm leading-6 text-[#7a83a2] dark:text-[#96a1c2]">
            Lance une extraction ou ouvre le detail d&apos;un document depuis Documents ou
            Historiques pour voir le fichier, les champs extraits et le JSON technique.
          </p>
        </div>
      </Card>
    );
  }

  const rows = flattenPayload(detail.payload);
  const sourceSuffix = detail.sourceFilename.split(".").pop()?.toLowerCase() ?? "";
  const previewUrl = detail.sourceAvailable ? resolveApiUrl(detail.sourceUrl) : null;
  const isImage = ["jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"].includes(sourceSuffix);
  const stackedLayout = layout === "stacked";

  return (
    <div className={stackedLayout ? "space-y-4" : "grid gap-4 xl:grid-cols-[1.05fr,0.95fr,0.7fr]"}>
      <Card className="p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="proto-title text-[14px] font-bold text-[#1b2440] dark:text-white">
            Document original
          </div>
          <Badge tone={detail.status === "ok" ? "success" : "danger"}>
            {detail.status === "ok" ? "Succes" : "Erreur"}
          </Badge>
        </div>
        <div className="overflow-hidden rounded-[18px] border border-[rgba(139,147,172,0.14)] bg-[#fbfcff] dark:border-white/10 dark:bg-[#0f1525]">
          {previewUrl ? (
            isImage ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={previewUrl}
                alt={detail.sourceFilename}
                className={stackedLayout ? "h-[320px] w-full object-contain" : "h-[500px] w-full object-contain"}
              />
            ) : (
              <iframe
                src={previewUrl}
                title={detail.sourceFilename}
                className={stackedLayout ? "h-[320px] w-full bg-white" : "h-[500px] w-full bg-white"}
              />
            )
          ) : (
            <div className={`flex items-center justify-center text-sm text-[#8d95ae] ${stackedLayout ? "h-[320px]" : "h-[500px]"}`}>
              Aucun document source archive.
            </div>
          )}
        </div>
      </Card>

      <Card className="p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="proto-title text-[14px] font-bold text-[#1b2440] dark:text-white">
            Champs extraits
          </div>
          <Badge tone="purple">{detail.kindLabel}</Badge>
        </div>
        <div className={`${stackedLayout ? "max-h-[360px]" : "max-h-[540px]"} space-y-2 overflow-auto pr-1`}>
          {rows.length ? (
            rows.map((row) => (
              <div
                key={`${row.label}-${row.value}`}
                className="grid gap-2 rounded-[16px] border border-[rgba(139,147,172,0.12)] bg-[#fbfcff] px-4 py-3 dark:border-white/10 dark:bg-[#0f1525] md:grid-cols-[minmax(220px,0.9fr)_minmax(0,1.1fr)]"
              >
                <div className="break-all text-[11px] font-semibold tracking-[0.08em] text-[#8d95ae]">
                  {row.label}
                </div>
                <div className="min-w-0 break-words text-[12px] leading-6 text-[#1b2440] dark:text-white">
                  {row.value}
                </div>
              </div>
            ))
          ) : (
            <div className="text-sm text-[#8d95ae]">Aucune donnee exploitable.</div>
          )}
        </div>
      </Card>

      <Card className="p-4">
        <div className="mb-3 proto-title text-[14px] font-bold text-[#1b2440] dark:text-white">
          JSON technique
        </div>
        <pre className={`${stackedLayout ? "max-h-[260px]" : "max-h-[540px]"} overflow-auto rounded-[18px] bg-[#111827] p-4 text-[11px] leading-5 text-[#98f5b7]`}>
          {JSON.stringify(detail.payload, null, 2)}
        </pre>
      </Card>
    </div>
  );
}
