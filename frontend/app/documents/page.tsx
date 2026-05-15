"use client";

import Link from "next/link";
import { Download, Filter, Search } from "lucide-react";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { fetchHistory } from "@/lib/api";
import type { HistoryListPayload } from "@/lib/types";

export default function DocumentsPage() {
  const [search, setSearch] = useState("");
  const [data, setData] = useState<HistoryListPayload | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ page: "1", pageSize: "12", search });
    fetchHistory(params)
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, [search]);

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="4. DOCUMENTS (Liste des documents)"
        title="Documents"
        description="Consulte, filtre et exporte la liste complete des documents deja traites."
      />

      <Card className="space-y-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-1 items-center gap-3">
            <div className="relative w-full max-w-[320px]">
              <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-[#99a1bb]" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Rechercher un document..."
                className="pl-9"
              />
            </div>
            <Select className="max-w-[140px]">
              <option>Tous les types</option>
            </Select>
            <Button variant="secondary" className="gap-2">
              <Filter className="h-4 w-4" />
              Filtrer
            </Button>
          </div>
          <Button variant="success" className="gap-2">
            <Download className="h-4 w-4" />
            Exporter
          </Button>
        </div>

        {error ? (
          <div className="text-sm text-[#df4d64]">{error}</div>
        ) : !data ? (
          <div className="text-sm text-[#7a83a2]">Chargement des documents...</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-[12px]">
                <thead className="border-b border-[rgba(139,147,172,0.14)] text-[#8d95ae]">
                  <tr>
                    <th className="pb-3 font-medium">Document</th>
                    <th className="pb-3 font-medium">Type</th>
                    <th className="pb-3 font-medium">Methode</th>
                    <th className="pb-3 font-medium">Statut</th>
                    <th className="pb-3 font-medium">Date</th>
                    <th className="pb-3 font-medium">Qualite</th>
                    <th className="pb-3 text-right font-medium">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr key={item.entryKey} className="border-b border-[rgba(139,147,172,0.08)]">
                      <td className="py-3 font-semibold text-[#1b2440] dark:text-white">
                        {item.sourceFilename}
                      </td>
                      <td className="py-3 text-[#606b89] dark:text-[#b1bcda]">{item.kindLabel}</td>
                      <td className="py-3">
                        <Badge tone={item.method.includes("Gemini") ? "purple" : "default"}>
                          {item.method}
                        </Badge>
                      </td>
                      <td className="py-3">
                        <Badge tone={item.status === "ok" ? "success" : "danger"}>
                          {item.status === "ok" ? "Succes" : "Erreur"}
                        </Badge>
                      </td>
                      <td className="py-3 text-[#606b89] dark:text-[#b1bcda]">
                        {item.savedDate ?? "N/A"}
                      </td>
                      <td className="py-3 font-semibold text-[#2eb764]">
                        {item.qualityScore !== null ? `${item.qualityScore.toFixed(1)}%` : "N/A"}
                      </td>
                      <td className="py-3 text-right">
                        <Link href={`/results?entry=${item.entryKey}`}>
                          <Button variant="ghost" size="sm">
                            Voir
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-end gap-2 text-[12px] text-[#8d95ae]">
              <span>1</span>
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#f3efff] font-semibold text-[#7c4dff]">
                2
              </span>
              <span>3</span>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
