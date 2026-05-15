"use client";

import { useEffect, useState } from "react";

import { ComboChart, DonutChart } from "@/components/charts";
import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { fetchAnalyses } from "@/lib/api";
import type { DashboardPayload } from "@/lib/types";

export default function AnalysesPage() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchAnalyses()
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="6. ANALYSES & IA (Analytics)"
        title="Analyses & IA"
        description="Vue d'ensemble analytique sur la qualite, les volumes et la performance du pipeline."
        action={
          <div className="flex items-center gap-2 rounded-xl border border-[rgba(139,147,172,0.16)] bg-[#fbfcff] px-3 py-2 text-[12px] text-[#6b7594] dark:border-white/10 dark:bg-[#0f1525] dark:text-[#b1bcda]">
            8 avr. 2026 - 10 mai 2026
          </div>
        }
      />

      {error ? (
        <Card className="text-[#df4d64]">{error}</Card>
      ) : !data ? (
        <Card>Chargement des analyses...</Card>
      ) : (
        <>
          <div className="flex flex-wrap gap-6 border-b border-[rgba(139,147,172,0.12)] pb-3 text-[12px] font-semibold text-[#7b84a0] dark:border-white/10 dark:text-[#b1bcda]">
            <span className="text-[#2eb764]">Vue d'ensemble</span>
            <span>Performance IA</span>
            <span>Qualite des donnees</span>
          </div>

          <section className="grid gap-4 xl:grid-cols-4">
            <Card>
              <div className="text-[12px] text-[#8d95ae]">AI Health Score</div>
              <div className="proto-title mt-3 text-[34px] font-bold text-[#1b2440] dark:text-white">
                {data.overview.aiHealthScore.toFixed(1)}
                <span className="ml-1 text-[18px] font-medium text-[#8d95ae]">/100</span>
              </div>
              <div className="mt-1 text-[12px] font-semibold text-[#2eb764]">Excellent</div>
            </Card>
            <Card>
              <div className="text-[12px] text-[#8d95ae]">Documents intelligents</div>
              <div className="proto-title mt-3 text-[34px] font-bold text-[#1b2440] dark:text-white">
                {data.overview.totalDocuments}
              </div>
              <div className="mt-1 text-[12px] font-semibold text-[#2eb764]">+12%</div>
            </Card>
            <Card>
              <div className="text-[12px] text-[#8d95ae]">Temps gagne</div>
              <div className="proto-title mt-3 text-[34px] font-bold text-[#1b2440] dark:text-white">
                12.4h
              </div>
              <div className="mt-1 text-[12px] font-semibold text-[#2eb764]">+10%</div>
            </Card>
            <Card>
              <div className="text-[12px] text-[#8d95ae]">Precision moyenne</div>
              <div className="proto-title mt-3 text-[34px] font-bold text-[#1b2440] dark:text-white">
                {data.overview.successRate.toFixed(1)}%
              </div>
              <div className="mt-1 text-[12px] font-semibold text-[#2eb764]">+2.3%</div>
            </Card>
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.35fr,0.65fr]">
            <Card>
              <div className="mb-4 proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
                Evolution des extractions
              </div>
              <ComboChart
                data={data.distributions.dailyVolume}
                successRate={data.overview.successRate}
              />
            </Card>

            <Card className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
                  Recommandations IA
                </div>
                <Badge tone="purple">Live</Badge>
              </div>
              <div className="space-y-3">
                {data.insights.map((item) => (
                  <div
                    key={item}
                    className="rounded-[14px] border border-[rgba(139,147,172,0.12)] bg-[#fbfcff] px-4 py-3 text-[12px] leading-6 text-[#66708e] dark:border-white/10 dark:bg-[#0f1525] dark:text-[#b1bcda]"
                  >
                    {item}
                  </div>
                ))}
              </div>
              <button className="text-left text-[12px] font-semibold text-[#7c4dff]">
                Voir toutes les recommandations
              </button>
            </Card>
          </section>

          <section className="grid gap-4 xl:grid-cols-[1.2fr,0.8fr]">
            <Card>
              <div className="mb-4 proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
                Repartition par type
              </div>
              <div className="grid gap-3">
                {data.distributions.byKind.map((item) => (
                  <div key={item.label} className="grid grid-cols-[1fr,180px,30px] items-center gap-3 text-[12px]">
                    <span className="text-[#4b5575] dark:text-[#b1bcda]">{item.label}</span>
                    <div className="h-2 rounded-full bg-[#eef1fa] dark:bg-white/8">
                      <div
                        className="h-2 rounded-full bg-gradient-to-r from-[#30c56f] to-[#7c4dff]"
                        style={{
                          width: `${(item.value / Math.max(...data.distributions.byKind.map((row) => row.value), 1)) * 100}%`
                        }}
                      />
                    </div>
                    <span className="text-right font-semibold text-[#1b2440] dark:text-white">{item.value}</span>
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <div className="mb-4 proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
                Repartition par methode IA
              </div>
              <DonutChart data={data.distributions.byMethod} />
            </Card>
          </section>
        </>
      )}
    </div>
  );
}
