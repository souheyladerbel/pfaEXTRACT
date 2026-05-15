"use client";

import { CalendarDays, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { ResultDetail } from "@/components/result-detail";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { deleteHistoryEntry, fetchHistory, fetchHistoryDetail } from "@/lib/api";
import type { HistoryDetail, HistoryItem, HistoryListPayload } from "@/lib/types";

function groupByDate(items: HistoryItem[]) {
  return items.reduce<Record<string, HistoryItem[]>>((acc, item) => {
    const key = item.savedDate ?? "Sans date";
    acc[key] = [...(acc[key] ?? []), item];
    return acc;
  }, {});
}

export default function HistoryPage() {
  const [kind, setKind] = useState("");
  const [search, setSearch] = useState("");
  const [typeQuery, setTypeQuery] = useState("");
  const [page, setPage] = useState(1);
  const [list, setList] = useState<HistoryListPayload | null>(null);
  const [selectedKey, setSelectedKey] = useState("");
  const [detail, setDetail] = useState<HistoryDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({
      page: String(page),
      pageSize: "8",
      kind,
      search,
      typeQuery
    });
    fetchHistory(params)
      .then((payload) => {
        setList(payload);
        if (payload.items[0] && !selectedKey) {
          setSelectedKey(payload.items[0].entryKey);
        }
      })
      .catch((err: Error) => setError(err.message));
  }, [page, kind, search, typeQuery]);

  useEffect(() => {
    if (!selectedKey) {
      return;
    }
    fetchHistoryDetail(selectedKey)
      .then(setDetail)
      .catch((err: Error) => setError(err.message));
  }, [selectedKey]);

  const grouped = useMemo(() => groupByDate(list?.items ?? []), [list]);

  const removeCurrentEntry = async () => {
    if (!selectedKey) {
      return;
    }
    try {
      await deleteHistoryEntry(selectedKey);
      setSelectedKey("");
      setDetail(null);
      const params = new URLSearchParams({
        page: String(page),
        pageSize: "8",
        kind,
        search,
        typeQuery
      });
      const payload = await fetchHistory(params);
      setList(payload);
      if (payload.items[0]) {
        setSelectedKey(payload.items[0].entryKey);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suppression impossible.");
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="5. HISTORIQUES"
        title="Historique des extractions"
        description="Chronologie des documents traites avec filtre rapide et acces detaille."
      />

      <Card className="space-y-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-1 items-center gap-3">
            <div className="relative w-full max-w-[320px]">
              <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-[#99a1bb]" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Rechercher dans l'historique..."
                className="pl-9"
              />
            </div>
            <Select value={kind} onChange={(event) => setKind(event.target.value)} className="max-w-[160px]">
              <option value="">Tous les types</option>
              {list?.filters.availableKinds.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </Select>
            <Input
              value={typeQuery}
              onChange={(event) => setTypeQuery(event.target.value)}
              placeholder="Patient / reference / facture"
              className="max-w-[220px]"
            />
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-[rgba(139,147,172,0.16)] bg-[#fbfcff] px-3 py-2 text-[12px] text-[#6b7594] dark:border-white/10 dark:bg-[#0f1525] dark:text-[#b1bcda]">
            <CalendarDays className="h-4 w-4 text-[#7c4dff]" />
            1 avr. 2026 - 10 mai 2026
          </div>
        </div>

        {error ? <div className="text-sm text-[#df4d64]">{error}</div> : null}

        {!list ? (
          <div className="text-sm text-[#7a83a2]">Chargement de l'historique...</div>
        ) : (
          <div className="grid gap-4 xl:grid-cols-[0.7fr,1.3fr]">
            <div className="rounded-[18px] border border-[rgba(139,147,172,0.14)] bg-[#fbfcff] p-4 dark:border-white/10 dark:bg-[#0f1525]">
              <div className="space-y-5">
                {Object.entries(grouped).map(([date, items]) => (
                  <div key={date} className="grid grid-cols-[18px,1fr] gap-3">
                    <div className="flex flex-col items-center">
                      <span className="mt-1 h-2.5 w-2.5 rounded-full bg-[#7c4dff]" />
                      <span className="mt-2 h-full w-px bg-[#e6eaf5] dark:bg-white/10" />
                    </div>
                    <div>
                      <div className="mb-2 text-[12px] font-semibold text-[#1b2440] dark:text-white">
                        {date}
                      </div>
                      <div className="space-y-2">
                        {items.map((item) => (
                          <button
                            key={item.entryKey}
                            type="button"
                            onClick={() => setSelectedKey(item.entryKey)}
                            className={`w-full rounded-[14px] border px-3 py-2 text-left text-[12px] transition ${
                              selectedKey === item.entryKey
                                ? "border-[#d6ccff] bg-[#f5f0ff] dark:border-[#47328c] dark:bg-[#1c1734]"
                                : "border-[rgba(139,147,172,0.1)] bg-white hover:bg-[#fafbff] dark:border-white/10 dark:bg-[#121829] dark:hover:bg-[#151c30]"
                            }`}
                          >
                            <div className="font-medium text-[#1b2440] dark:text-white">
                              {item.sourceFilename}
                            </div>
                            <div className="mt-1 text-[#8d95ae]">{item.kindLabel}</div>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[18px] border border-[rgba(139,147,172,0.14)] bg-white p-4 dark:border-white/10 dark:bg-[#121829]">
              <div className="space-y-2">
                {(list.items ?? []).map((item) => (
                  <button
                    key={item.entryKey}
                    type="button"
                    onClick={() => setSelectedKey(item.entryKey)}
                    className={`grid w-full grid-cols-[130px,1fr,120px,70px] items-center gap-3 rounded-[14px] px-3 py-3 text-left text-[12px] transition ${
                      selectedKey === item.entryKey
                        ? "bg-[#f7f4ff]"
                        : "hover:bg-[#fafbff] dark:hover:bg-white/5"
                    }`}
                  >
                    <div className="text-[#8d95ae]">{item.savedDate ?? "N/A"}</div>
                    <div>
                      <div className="font-medium text-[#1b2440] dark:text-white">
                        {item.sourceFilename}
                      </div>
                      <div className="text-[#8d95ae]">{item.kindLabel}</div>
                    </div>
                    <div className="text-[#606b89] dark:text-[#b1bcda]">{item.method}</div>
                    <div className="text-right">
                      <Badge tone={item.status === "ok" ? "success" : "danger"}>
                        {item.status === "ok" ? "Succes" : "Erreur"}
                      </Badge>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="text-[12px] text-[#8d95ae]">
            Page {list?.pagination.page ?? 1} / {list?.pagination.totalPages ?? 1}
          </div>
          {detail ? (
            <Button variant="danger" size="sm" onClick={removeCurrentEntry} className="gap-2">
              <Trash2 className="h-4 w-4" />
              Supprimer
            </Button>
          ) : null}
        </div>
      </Card>

      <ResultDetail detail={detail} />
    </div>
  );
}
