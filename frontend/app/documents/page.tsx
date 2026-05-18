"use client";

import { Download, Search, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { ResultDetail } from "@/components/result-detail";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { deleteHistoryEntry, fetchHistory, fetchHistoryDetail, resolveApiUrl } from "@/lib/api";
import type { HistoryDetail, HistoryListPayload } from "@/lib/types";

export default function DocumentsPage() {
  const [requestedEntryKey, setRequestedEntryKey] = useState("");
  const [search, setSearch] = useState("");
  const [kindFilter, setKindFilter] = useState("");
  const [data, setData] = useState<HistoryListPayload | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selectedEntryKeys, setSelectedEntryKeys] = useState<string[]>([]);
  const [focusedEntryKey, setFocusedEntryKey] = useState("");
  const [focusedDetail, setFocusedDetail] = useState<HistoryDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    setRequestedEntryKey(params.get("entry") ?? "");
  }, []);

  useEffect(() => {
    const params = new URLSearchParams({ page: "1", pageSize: "12" });
    if (search.trim()) {
      params.set("search", search.trim());
    }
    if (kindFilter) {
      params.set("kind", kindFilter);
    }

    fetchHistory(params)
      .then((payload) => {
        setData(payload);
        setSelectedEntryKeys((current) =>
          current.filter((entryKey) => payload.items.some((item) => item.entryKey === entryKey))
        );

        if (focusedEntryKey && !payload.items.some((item) => item.entryKey === focusedEntryKey)) {
          setFocusedEntryKey("");
          setFocusedDetail(null);
          setDetailError("");
        }
      })
      .catch((err: Error) => setError(err.message));
  }, [focusedEntryKey, kindFilter, search]);

  const visibleEntryKeys = useMemo(
    () => data?.items.map((item) => item.entryKey) ?? [],
    [data]
  );

  const allVisibleSelected =
    visibleEntryKeys.length > 0 && visibleEntryKeys.every((entryKey) => selectedEntryKeys.includes(entryKey));

  const selectedItems =
    data?.items.filter((item) => selectedEntryKeys.includes(item.entryKey)) ?? [];

  const toggleEntry = (entryKey: string) => {
    setSelectedEntryKeys((current) =>
      current.includes(entryKey)
        ? current.filter((item) => item !== entryKey)
        : [...current, entryKey]
    );
    setNotice("");
  };

  const toggleAllVisible = () => {
    if (!visibleEntryKeys.length) {
      return;
    }

    setSelectedEntryKeys((current) => {
      if (allVisibleSelected) {
        return current.filter((entryKey) => !visibleEntryKeys.includes(entryKey));
      }

      return Array.from(new Set([...current, ...visibleEntryKeys]));
    });
    setNotice("");
  };

  const openDocumentDetail = (entryKey: string) => {
    setFocusedEntryKey(entryKey);
    setDetailLoading(true);
    setDetailError("");
    setFocusedDetail(null);
    fetchHistoryDetail(entryKey)
      .then((payload) => {
        setFocusedDetail(payload);
      })
      .catch((err: Error) => {
        setFocusedDetail(null);
        setDetailError(err.message);
      })
      .finally(() => setDetailLoading(false));
  };

  useEffect(() => {
    if (!requestedEntryKey || requestedEntryKey === focusedEntryKey) {
      return;
    }

    openDocumentDetail(requestedEntryKey);
  }, [focusedEntryKey, requestedEntryKey]);

  const closeDocumentDetail = () => {
    setFocusedEntryKey("");
    setFocusedDetail(null);
    setDetailError("");
    setDetailLoading(false);
    setRequestedEntryKey("");

    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("entry");
      window.history.replaceState({}, "", url.pathname + url.search);
    }
  };

  const isDetailModalOpen =
    Boolean(focusedEntryKey) || detailLoading || Boolean(focusedDetail) || Boolean(detailError);

  useEffect(() => {
    if (!isDetailModalOpen || typeof window === "undefined") {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeDocumentDetail();
      }
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isDetailModalOpen]);

  const exportSelectedDocuments = () => {
    if (selectedEntryKeys.length > 1) {
      const params = new URLSearchParams();
      selectedEntryKeys.forEach((entryKey) => params.append("entryKey", entryKey));
      window.open(resolveApiUrl(`/api/history/export/zip?${params.toString()}`), "_blank", "noopener,noreferrer");
      setNotice(`${selectedEntryKeys.length} document(s) envoye(s) vers l'export ZIP.`);
      return;
    }

    const singleEntryKey = selectedEntryKeys[0] ?? focusedEntryKey;
    if (singleEntryKey) {
      window.open(
        resolveApiUrl(`/api/history/${singleEntryKey}/report.pdf`),
        "_blank",
        "noopener,noreferrer"
      );
      setNotice("Le rapport PDF du document selectionne a ete ouvert.");
      return;
    }

    setNotice("Clique sur un document pour afficher son detail, ou coche plusieurs documents pour un export ZIP.");
  };

  const exportFocusedDocument = () => {
    if (!focusedEntryKey) {
      setNotice("Clique d'abord sur un document pour afficher son detail.");
      return;
    }

    window.open(
      resolveApiUrl(`/api/history/${focusedEntryKey}/report.pdf`),
      "_blank",
      "noopener,noreferrer"
    );
    setNotice("Le rapport PDF du document affiche a ete ouvert.");
  };

  const trashFocusedDocument = async () => {
    if (!focusedEntryKey) {
      setNotice("Clique d'abord sur un document pour afficher son detail.");
      return;
    }

    try {
      const response = await deleteHistoryEntry(focusedEntryKey);
      setSelectedEntryKeys((current) => current.filter((entryKey) => entryKey !== focusedEntryKey));
      closeDocumentDetail();
      setNotice(response.message);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Mise en corbeille impossible.");
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="4. DOCUMENTS (Liste des documents)"
        title="Documents"
        description="Consulte, filtre et exporte la liste complete des documents deja traites."
      />

      <Card className="space-y-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-1 flex-wrap items-center gap-3">
            <div className="relative w-full max-w-[320px]">
              <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-[#99a1bb]" />
              <Input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setNotice("");
                }}
                placeholder="Rechercher un document..."
                className="pl-9"
              />
            </div>
            <Select
              className="max-w-[220px]"
              value={kindFilter}
              onChange={(event) => {
                setKindFilter(event.target.value);
                setNotice("");
              }}
            >
              <option value="">Tous les types</option>
              {data?.filters.availableKinds.map((kind) => (
                <option key={kind.value} value={kind.value}>
                  {kind.label}
                </option>
              ))}
            </Select>
          </div>
          <Button variant="success" className="gap-2" onClick={exportSelectedDocuments}>
            <Download className="h-4 w-4" />
            {selectedEntryKeys.length > 1
              ? "Exporter la selection"
              : focusedEntryKey || selectedEntryKeys.length === 1
                ? "Exporter le document"
                : "Exporter"}
          </Button>
        </div>

        {error ? (
          <div className="text-sm text-[#df4d64]">{error}</div>
        ) : !data ? (
          <div className="text-sm text-[#7a83a2]">Chargement des documents...</div>
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-2 text-[12px] text-[#7a83a2] dark:text-[#aeb7d2]">
              <span>
                {selectedItems.length
                  ? `${selectedItems.length} document(s) selectionne(s)`
                  : "Clique sur un document pour ouvrir son detail en popup, ou coche plusieurs documents pour un export ZIP."}
              </span>
              <span>
                Type filtre :{" "}
                {kindFilter
                  ? data.filters.availableKinds.find((kind) => kind.value === kindFilter)?.label ?? kindFilter
                  : "Tous les types"}
              </span>
            </div>

            <div className="space-y-2">
              <div className="grid grid-cols-[auto,minmax(0,1.4fr),auto,auto] gap-3 px-2 text-[11px] font-semibold uppercase tracking-[0.08em] text-[#8d95ae]">
                <button
                  type="button"
                  onClick={toggleAllVisible}
                  className="mt-0.5 flex h-4 w-4 items-center justify-center rounded border border-[rgba(139,147,172,0.28)]"
                  title={allVisibleSelected ? "Tout deselectionner" : "Tout selectionner"}
                >
                  {allVisibleSelected ? <span className="h-2 w-2 rounded-sm bg-[#7c4dff]" /> : null}
                </button>
                <span>Document</span>
                <span className="hidden xl:block">Date</span>
                <span className="text-right">Statut</span>
              </div>

              {data.items.map((item) => {
                const checked = selectedEntryKeys.includes(item.entryKey);
                const focused = focusedEntryKey === item.entryKey;

                return (
                  <div
                    key={item.entryKey}
                    role="button"
                    tabIndex={0}
                    onClick={() => openDocumentDetail(item.entryKey)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        openDocumentDetail(item.entryKey);
                      }
                    }}
                    className={`grid w-full grid-cols-[auto,minmax(0,1.4fr),auto,auto] items-center gap-3 rounded-[18px] border px-3 py-3 text-left transition ${
                      focused
                        ? "border-[#cfdcff] bg-[#eef4ff] shadow-[0_8px_24px_rgba(81,108,201,0.08)] dark:border-[#29406f] dark:bg-[#132038]"
                        : checked
                          ? "border-[#e1d5ff] bg-[#f6f2ff] dark:border-[#453071] dark:bg-[#1a1630]"
                          : "border-[rgba(139,147,172,0.12)] bg-[#fbfcff] hover:bg-[#fafbff] dark:border-white/10 dark:bg-[#0f1525] dark:hover:bg-white/5"
                    }`}
                  >
                    <div onClick={(event) => event.stopPropagation()}>
                      <button
                        type="button"
                        onClick={() => toggleEntry(item.entryKey)}
                        className={`flex h-5 w-5 items-center justify-center rounded border transition ${
                          checked
                            ? "border-[#7c4dff] bg-[#7c4dff]"
                            : "border-[rgba(139,147,172,0.28)] bg-white dark:bg-transparent"
                        }`}
                        title={checked ? "Deselectionner" : "Selectionner"}
                      >
                        {checked ? <span className="h-2 w-2 rounded-full bg-white" /> : null}
                      </button>
                    </div>

                    <div className="min-w-0">
                      <div className="truncate font-semibold text-[#1b2440] dark:text-white">
                        {item.sourceFilename}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-[12px] text-[#606b89] dark:text-[#b1bcda]">
                        <span className="truncate">{item.kindLabel}</span>
                        <Badge tone={item.method.includes("Gemini") ? "purple" : "default"}>
                          {item.method}
                        </Badge>
                        <span className="font-semibold text-[#2eb764]">
                          {item.qualityScore !== null ? `${item.qualityScore.toFixed(1)}%` : "N/A"}
                        </span>
                      </div>
                    </div>

                    <div className="hidden text-[12px] text-[#606b89] dark:text-[#b1bcda] xl:block">
                      {item.savedDate ?? "N/A"}
                    </div>

                    <div className="flex justify-end">
                      <Badge tone={item.status === "ok" ? "success" : "danger"}>
                        {item.status === "ok" ? "Succes" : "Erreur"}
                      </Badge>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="flex items-center justify-end gap-2 text-[12px] text-[#8d95ae]">
              <span>1</span>
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#f3efff] font-semibold text-[#7c4dff]">
                {data.pagination.page}
              </span>
              <span>{data.pagination.totalPages}</span>
            </div>
            {notice ? <div className="text-[12px] text-[#7455f2] dark:text-[#c7b7ff]">{notice}</div> : null}
          </>
        )}
      </Card>

      {isDetailModalOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(16,22,37,0.42)] px-4 py-6 backdrop-blur-[2px]"
          onClick={closeDocumentDetail}
        >
          <div
            className="max-h-[92vh] w-full max-w-[1400px] overflow-auto rounded-[28px] border border-[rgba(139,147,172,0.18)] bg-white p-5 shadow-[0_24px_80px_rgba(16,22,37,0.24)] dark:border-white/10 dark:bg-[#101625]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-[20px] font-bold text-[#1b2440] dark:text-white">
                  Detail du document
                </div>
                <div className="mt-1 text-[12px] text-[#7a83a2] dark:text-[#aeb7d2]">
                  Consulte le contenu extrait puis exporte directement le rapport du document.
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="danger" className="gap-2" onClick={trashFocusedDocument}>
                  <Trash2 className="h-4 w-4" />
                  Mettre a la corbeille
                </Button>
                <Button variant="success" className="gap-2" onClick={exportFocusedDocument}>
                  <Download className="h-4 w-4" />
                  Exporter ce document
                </Button>
                <button
                  type="button"
                  onClick={closeDocumentDetail}
                  className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[rgba(139,147,172,0.18)] bg-[#fbfcff] text-[#5f6888] transition hover:bg-[#f3f6ff] dark:border-white/10 dark:bg-[#0f1525] dark:text-[#b7c1de] dark:hover:bg-[#151c30]"
                  title="Fermer"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {detailError ? (
              <div className="rounded-[16px] border border-[rgba(223,77,100,0.18)] bg-[#fff5f7] px-4 py-3 text-sm text-[#df4d64] dark:border-[rgba(223,77,100,0.32)] dark:bg-[#2b1520]">
                {detailError}
              </div>
            ) : detailLoading ? (
              <Card>Chargement du detail du document...</Card>
            ) : focusedDetail ? (
              <>
                <div className="mb-4 grid gap-3 md:grid-cols-3">
                  <div className="rounded-[16px] border border-[rgba(139,147,172,0.14)] bg-[#fbfcff] px-4 py-3 text-[12px] dark:border-white/10 dark:bg-[#0f1525]">
                    <div className="font-semibold text-[#8d95ae]">Document</div>
                    <div className="mt-1 text-[#1b2440] dark:text-white">{focusedDetail.sourceFilename}</div>
                  </div>
                  <div className="rounded-[16px] border border-[rgba(139,147,172,0.14)] bg-[#fbfcff] px-4 py-3 text-[12px] dark:border-white/10 dark:bg-[#0f1525]">
                    <div className="font-semibold text-[#8d95ae]">Type detecte</div>
                    <div className="mt-1 text-[#1b2440] dark:text-white">{focusedDetail.kindLabel}</div>
                  </div>
                  <div className="rounded-[16px] border border-[rgba(139,147,172,0.14)] bg-[#fbfcff] px-4 py-3 text-[12px] dark:border-white/10 dark:bg-[#0f1525]">
                    <div className="font-semibold text-[#8d95ae]">Methode</div>
                    <div className="mt-1 text-[#1b2440] dark:text-white">{focusedDetail.method}</div>
                  </div>
                </div>
                <ResultDetail detail={focusedDetail} layout="stacked" />
              </>
            ) : (
              <Card>Aucun detail affiche pour le moment.</Card>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
