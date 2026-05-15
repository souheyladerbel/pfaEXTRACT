"use client";

import { CalendarDays, Plus, ShieldAlert, Sparkles, Trophy, WalletCards, Workflow } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { DonutChart, SimpleBars, TrendLineChart } from "@/components/charts";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetchDashboard } from "@/lib/api";
import type { DashboardPayload } from "@/lib/types";

function scoreLabel(score: number | null) {
  if (score === null || Number.isNaN(score)) {
    return "N/A";
  }
  return `${score.toFixed(1)}%`;
}

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState("");
  const todayLabel = useMemo(
    () =>
      new Intl.DateTimeFormat("fr-FR", {
        day: "numeric",
        month: "short",
        year: "numeric",
      }).format(new Date()),
    []
  );

  useEffect(() => {
    fetchDashboard()
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, []);

  const recentRows = data?.recentActivity ?? [];

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="1. TABLEAU DE BORD (Dashboard)"
        title="Bonjour, Admin !"
        description="Voici un apercu complet de vos extractions et performances."
        action={
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex h-10 items-center gap-2 rounded-xl border border-[rgba(139,147,172,0.2)] bg-white px-3 text-sm text-[#1b2440] dark:border-white/10 dark:bg-[#0f1525] dark:text-white">
              <CalendarDays className="h-4 w-4 text-[#7c4dff]" />
              {todayLabel}
            </div>
            <Button className="gap-2" onClick={() => router.push("/extractions")}>
              <Plus className="h-4 w-4" />
              Nouvelle extraction
            </Button>
          </div>
        }
      />

      {error ? (
        <Card className="text-[#df4d64]">{error}</Card>
      ) : !data ? (
        <Card>Chargement du dashboard...</Card>
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            <StatCard
              icon={<Workflow className="h-4 w-4" />}
              title="Documents traites"
              value={String(data.overview.totalDocuments)}
              helper="+12% vs periode precedente"
              sparkColor="#7c4dff"
            />
            <StatCard
              icon={<Trophy className="h-4 w-4" />}
              title="Succes"
              value={String(data.overview.successCount)}
              helper="100% de reussite"
              sparkColor="#30c56f"
            />
            <StatCard
              icon={<ShieldAlert className="h-4 w-4" />}
              title="Erreurs"
              value={String(data.overview.errorCount)}
              helper="0% d'echec"
              sparkColor="#ff9a3d"
            />
            <StatCard
              icon={<Sparkles className="h-4 w-4" />}
              title="Taux de succes"
              value={`${data.overview.successRate.toFixed(0)}%`}
              helper="Excellente performance"
              sparkColor="#a764ff"
            />
            <StatCard
              icon={<WalletCards className="h-4 w-4" />}
              title="Types detectes"
              value={String(data.distributions.byKind.length)}
              helper="Familles de documents"
              sparkColor="#5987ff"
            />
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.08fr,0.92fr]">
            <Card className="p-0">
              <div className="flex items-center justify-between border-b border-[rgba(139,147,172,0.14)] px-5 py-4">
                <div className="proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
                  Activite recente
                </div>
                <Button variant="ghost" size="sm" onClick={() => router.push("/documents")}>
                  Voir tous les documents
                </Button>
              </div>
              <div className="overflow-x-auto px-5 py-3">
                <table className="min-w-full text-left text-[12px]">
                  <thead className="text-[#8d95ae]">
                    <tr>
                      <th className="pb-3 font-medium">Document</th>
                      <th className="pb-3 font-medium">Type</th>
                      <th className="pb-3 font-medium">Methode</th>
                      <th className="pb-3 font-medium">Statut</th>
                      <th className="pb-3 font-medium">Date</th>
                      <th className="pb-3 text-right font-medium">Qualite</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentRows.map((item) => (
                      <tr key={item.entryKey} className="border-t border-[rgba(139,147,172,0.08)]">
                        <td className="py-3 font-semibold text-[#1b2440] dark:text-white">
                          {item.sourceFilename}
                        </td>
                        <td className="py-3 text-[#5f6888] dark:text-[#b7c0dc]">{item.kindLabel}</td>
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
                        <td className="py-3 text-[#5f6888] dark:text-[#b7c0dc]">
                          {item.savedDate ?? "N/A"}
                        </td>
                        <td className="py-3 text-right font-semibold text-[#2eb764]">
                          {scoreLabel(item.qualityScore)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card>
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <div className="proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
                    Performance des extractions
                  </div>
                  <div className="mt-1 text-[12px] text-[#8d95ae]">
                    Evolution des extractions par type
                  </div>
                </div>
              </div>
              <TrendLineChart series={data.distributions.trendSeries} />
            </Card>
          </section>

          <section className="grid gap-4 xl:grid-cols-[0.82fr,0.95fr,1.05fr]">
            <Card>
              <div className="proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
                Insights IA
              </div>
              <div className="mt-5 space-y-4">
                <div className="text-sm text-[#55617f] dark:text-[#b7c0dc]">
                  {data.insights[0] ?? "Vos extractions sont plus rapides cette semaine."}
                </div>
                <div className="text-sm text-[#55617f] dark:text-[#b7c0dc]">
                  Continuez comme ca.
                </div>
                <div className="mt-6 h-2 rounded-full bg-[#efeafe] dark:bg-white/10">
                  <div className="h-2 w-[72%] rounded-full bg-gradient-to-r from-[#7c4dff] to-[#b873ff]" />
                </div>
                <div className="text-right text-[12px] font-semibold text-[#7c4dff]">
                  23% plus rapide
                </div>
              </div>
            </Card>

            <Card>
              <div className="mb-4 proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
                Repartition par methode IA
              </div>
              <DonutChart data={data.distributions.byMethod} />
            </Card>

            <Card>
              <div className="mb-4 proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
                Documents par type
              </div>
              <SimpleBars data={data.distributions.byKind} />
            </Card>
          </section>
        </>
      )}
    </div>
  );
}
