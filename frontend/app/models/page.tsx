"use client";

import { useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { fetchModels } from "@/lib/api";
import {
  readStoredJson,
  readStoredValue,
  storageKeys,
  writeStoredJson,
  writeStoredValue,
} from "@/lib/storage";
import type { ModelsPayload } from "@/lib/types";

type CatalogRow = ModelsPayload["models"][number];

const TOGGLEABLE_MODEL_IDS = new Set(["gemini-api", "ocr-local"]);

function getAvailableToggleIds(models: CatalogRow[]) {
  return models
    .filter((model) => model.toggleable && model.available && TOGGLEABLE_MODEL_IDS.has(model.id))
    .map((model) => model.id);
}

function getDefaultActiveIds(models: CatalogRow[]) {
  const available = getAvailableToggleIds(models);
  if (!available.length) {
    return [];
  }
  if (available.includes("gemini-api") && available.includes("ocr-local")) {
    return ["gemini-api", "ocr-local"];
  }
  return available;
}

function methodFromModelId(modelId: string) {
  if (modelId === "gemini-api") {
    return "gemini";
  }
  if (modelId === "ocr-local") {
    return "ocr";
  }
  return "";
}

export default function ModelsPage() {
  const [data, setData] = useState<ModelsPayload | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [activeIds, setActiveIds] = useState<string[]>([]);

  useEffect(() => {
    fetchModels()
      .then((payload) => {
        setData(payload);
        const stored = readStoredJson<string[]>(storageKeys.activeModels, []);
        const allowed = new Set(getAvailableToggleIds(payload.models));
        const filtered = stored.filter((item) => allowed.has(item));
        const next = filtered.length ? filtered : getDefaultActiveIds(payload.models);
        setActiveIds(next);
        writeStoredJson(storageKeys.activeModels, next);

        const defaultMethod = readStoredValue(storageKeys.defaultMethod, "");
        if (!defaultMethod || !next.some((item) => methodFromModelId(item) === defaultMethod)) {
          const fallbackMethod = next.includes("gemini-api") ? "gemini" : next.includes("ocr-local") ? "ocr" : "";
          if (fallbackMethod) {
            writeStoredValue(storageKeys.defaultMethod, fallbackMethod);
          }
        }
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  const activeMethods = useMemo(() => {
    return activeIds.map(methodFromModelId).filter(Boolean);
  }, [activeIds]);

  const applyToggle = (row: CatalogRow) => {
    if (!row.toggleable || !row.available) {
      setNotice(row.reason ?? "Ce modele n'est pas encore activable dans cette version.");
      return;
    }

    const enabled = activeIds.includes(row.id);
    const next = enabled ? activeIds.filter((item) => item !== row.id) : [...activeIds, row.id];
    const validNext = next.filter((item) =>
      data?.models.some((model) => model.id === item && model.toggleable && model.available)
    );

    if (!validNext.length) {
      setNotice("Garde au moins un moteur actif pour pouvoir lancer des extractions.");
      return;
    }

    setActiveIds(validNext);
    writeStoredJson(storageKeys.activeModels, validNext);

    const rowMethod = row.methodValue ?? methodFromModelId(row.id);
    const currentDefault = readStoredValue(storageKeys.defaultMethod, "");
    const fallbackMethod =
      validNext.includes("gemini-api") ? "gemini" : validNext.includes("ocr-local") ? "ocr" : "";

    if (!enabled && rowMethod) {
      writeStoredValue(storageKeys.defaultMethod, rowMethod);
      setNotice(`${row.name} est maintenant actif et devient la methode par defaut pour Extraction.`);
      return;
    }

    if (enabled && currentDefault === rowMethod && fallbackMethod) {
      writeStoredValue(storageKeys.defaultMethod, fallbackMethod);
    }

    setNotice(
      enabled
        ? `${row.name} est desactive. La page Extraction utilisera l'autre moteur actif.`
        : `${row.name} est active.`
    );
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="7. MODELES IA (Gestion des modeles)"
        title="Gestion des modeles IA"
        description="Catalogue visuel des moteurs actifs et de la couverture actuelle de la plateforme."
        action={
          <Button
            size="sm"
            onClick={() =>
              setNotice(
                "La version actuelle supporte Gemini API et OCR local. GPT-4o et Claude sont affiches comme references visuelles."
              )
            }
          >
            Ajouter un modele
          </Button>
        }
      />

      {error ? (
        <Card className="text-[#df4d64]">{error}</Card>
      ) : !data ? (
        <Card>Chargement des modeles...</Card>
      ) : (
        <>
          <Card className="space-y-4 overflow-x-auto">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={activeMethods.includes("gemini") ? "success" : "default"}>
                Gemini {activeMethods.includes("gemini") ? "actif" : "inactif"}
              </Badge>
              <Badge tone={activeMethods.includes("ocr") ? "success" : "default"}>
                OCR local {activeMethods.includes("ocr") ? "actif" : "inactif"}
              </Badge>
              <Badge tone="purple">
                Defaut extraction: {readStoredValue(storageKeys.defaultMethod, "gemini") === "ocr" ? "OCR local" : "Gemini API"}
              </Badge>
            </div>

            <table className="min-w-full text-left text-[12px]">
              <thead className="border-b border-[rgba(139,147,172,0.14)] text-[#8d95ae]">
                <tr>
                  <th className="pb-3 font-medium">Modele</th>
                  <th className="pb-3 font-medium">Fournisseur</th>
                  <th className="pb-3 font-medium">Version</th>
                  <th className="pb-3 font-medium">Precision</th>
                  <th className="pb-3 font-medium">Statut</th>
                  <th className="pb-3 font-medium">Derniere utilisation</th>
                  <th className="pb-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {data.models.map((row) => {
                  const active = row.toggleable
                    ? activeIds.includes(row.id)
                    : Boolean(row.methodValue && activeMethods.includes(row.methodValue));
                  const badgeTone = active
                    ? "success"
                    : row.available
                      ? row.toggleable
                        ? "default"
                        : "purple"
                      : "warning";
                  const badgeLabel = active
                    ? "Actif"
                    : row.available
                      ? row.toggleable
                        ? "Inactif"
                        : "Reference"
                      : "Indisponible";

                  return (
                    <tr key={row.id} className="border-b border-[rgba(139,147,172,0.08)]">
                      <td className="py-3">
                        <div className="font-semibold text-[#1b2440] dark:text-white">{row.name}</div>
                        <div className="mt-1 text-[11px] text-[#8d95ae]">{row.description}</div>
                      </td>
                      <td className="py-3 text-[#606b89] dark:text-[#b1bcda]">{row.provider}</td>
                      <td className="py-3 text-[#606b89] dark:text-[#b1bcda]">{row.version ?? "-"}</td>
                      <td className="py-3 font-semibold text-[#2eb764]">
                        {row.precision !== null && row.precision !== undefined ? `${row.precision}%` : "N/A"}
                      </td>
                      <td className="py-3">
                        <Badge tone={badgeTone}>{badgeLabel}</Badge>
                      </td>
                      <td className="py-3 text-[#606b89] dark:text-[#b1bcda]">{row.lastUsed ?? "Jamais"}</td>
                      <td className="py-3 text-right">
                        <button
                          type="button"
                          onClick={() => applyToggle(row)}
                          disabled={!row.toggleable && !row.reason}
                          className={`inline-flex h-6 w-11 items-center rounded-full px-1 transition ${
                            active
                              ? "bg-[#30c56f]"
                              : "bg-[#d4dae9] dark:bg-[#2a3450]"
                          } ${row.toggleable || row.reason ? "" : "cursor-not-allowed opacity-60"}`}
                          title={
                            row.toggleable
                              ? active
                                ? `Desactiver ${row.name}`
                                : `Activer ${row.name}`
                              : row.reason ?? "Modele non activable"
                          }
                        >
                          <span
                            className={`h-4 w-4 rounded-full bg-white transition ${
                              active ? "ml-auto" : ""
                            }`}
                          />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>

          <Card className="space-y-2">
            <div className="proto-title text-[14px] font-bold text-[#1b2440] dark:text-white">
              Conseil
            </div>
            <div className="text-[12px] text-[#66708e] dark:text-[#b1bcda]">
              Active Gemini API pour les tickets et factures fournisseur. OCR local reste utile en fallback pour medical et STEG.
            </div>
            {notice ? <div className="text-[12px] text-[#7455f2] dark:text-[#c7b7ff]">{notice}</div> : null}
          </Card>
        </>
      )}
    </div>
  );
}
