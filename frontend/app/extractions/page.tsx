"use client";

import { Check, CloudUpload, FileStack, Info, LoaderCircle, Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { fetchMeta, uploadExtractions } from "@/lib/api";
import {
  readStoredJson,
  readStoredValue,
  storageKeys,
  writeStoredValue,
} from "@/lib/storage";
import type { ExtractionBatchPayload, MetaPayload } from "@/lib/types";

const modeVisuals: Record<string, { title: string; hint: string }> = {
  auto: { title: "Auto", hint: "Detection intelligente" },
  medical: { title: "Analyse medicale", hint: "Labo & comptes rendus" },
  steg: { title: "Facture STEG", hint: "Electricite & facture" },
  supplier: { title: "Facture fournisseur", hint: "B2B generique" },
  receipt: { title: "Ticket de caisse", hint: "Recu & ticket" }
};

function resolveAllowedMethods(meta: MetaPayload, activeModelIds: string[]) {
  const allowed = new Set<string>();
  if (activeModelIds.includes("gemini-api") || !activeModelIds.length) {
    allowed.add("gemini");
  }
  if (activeModelIds.includes("ocr-local") || !activeModelIds.length) {
    allowed.add("ocr");
  }
  return meta.methods.filter((item) => allowed.has(item.value));
}

function resolveInitialMethod(meta: MetaPayload, activeModelIds: string[]) {
  const allowedMethods = resolveAllowedMethods(meta, activeModelIds);
  const stored = readStoredValue(storageKeys.defaultMethod, "");
  if (stored && allowedMethods.some((item) => item.value === stored)) {
    return stored;
  }
  if (allowedMethods.some((item) => item.value === "gemini")) {
    return "gemini";
  }
  return allowedMethods[0]?.value ?? "gemini";
}

export default function ExtractionsPage() {
  const router = useRouter();
  const [meta, setMeta] = useState<MetaPayload | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [mode, setMode] = useState("auto");
  const [method, setMethod] = useState("gemini");
  const [geminiApiKey, setGeminiApiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("gemini-2.5-flash");
  const [advanced, setAdvanced] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [result, setResult] = useState<ExtractionBatchPayload | null>(null);
  const [activeModelIds, setActiveModelIds] = useState<string[]>([]);

  useEffect(() => {
    fetchMeta().then((payload) => {
      const storedModels = readStoredJson<string[]>(storageKeys.activeModels, []);
      setMeta(payload);
      setActiveModelIds(storedModels);
      setGeminiModel(readStoredValue(storageKeys.geminiModel, payload.defaultGeminiModel));
      setGeminiApiKey(readStoredValue(storageKeys.geminiKey, ""));
      setMethod(resolveInitialMethod(payload, storedModels));
    });
  }, []);

  const availableMethods = useMemo(
    () => (meta ? resolveAllowedMethods(meta, activeModelIds) : []),
    [activeModelIds, meta]
  );

  useEffect(() => {
    if (!meta) {
      return;
    }

    if (availableMethods.length && !availableMethods.some((item) => item.value === method)) {
      const fallback = resolveInitialMethod(meta, activeModelIds);
      setMethod(fallback);
      setInfo("La methode precedente n'est plus active. Extraction a bascule sur le moteur disponible.");
      return;
    }

    if (method === "ocr" && (mode === "receipt" || mode === "supplier")) {
      if (availableMethods.some((item) => item.value === "gemini")) {
        setMethod("gemini");
        setInfo("Ticket de caisse et facture fournisseur exigent Gemini. La methode a ete rebasculee automatiquement.");
      } else {
        setInfo("Ce type de document exige Gemini. Reactive Gemini API dans l'onglet Modeles IA.");
      }
      return;
    }
    setInfo(
      mode === "auto" && method === "ocr"
        ? "En mode Auto avec OCR local, les tickets et factures fournisseur ne pourront pas etre extraits."
        : ""
    );
  }, [activeModelIds, availableMethods, meta, method, mode]);

  const handleFileChange = (selected: FileList | null) => {
    if (!selected) {
      return;
    }
    setFiles(Array.from(selected));
  };

  const runExtraction = async () => {
    if (!files.length) {
      setError("Ajoute au moins un document avant de lancer l'extraction.");
      return;
    }

    setLoading(true);
    setError("");

    const form = new FormData();
    const origins = files.map((file) => {
      const relative = (file as File & { webkitRelativePath?: string }).webkitRelativePath;
      return relative ? relative.split("/").slice(0, -1).join("/") || "upload" : "upload";
    });

    files.forEach((file) => {
      form.append("files", file, file.name);
    });
    form.append("mode", mode);
    form.append("method", method);
    form.append("geminiApiKey", geminiApiKey);
    form.append("geminiModel", geminiModel);
    form.append("retries", "5");
    form.append("retryDelay", "2");
    form.append("originsJson", JSON.stringify(origins));

    try {
      const response = await uploadExtractions(form);
      setResult(response);
      writeStoredValue(storageKeys.lastExtraction, JSON.stringify(response));
      writeStoredValue(storageKeys.geminiKey, geminiApiKey);
      writeStoredValue(storageKeys.geminiModel, geminiModel);
      writeStoredValue(storageKeys.defaultMethod, method);
      if (response.latestSuccess?.historyEntryKey) {
        router.push(`/results?entry=${response.latestSuccess.historyEntryKey}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="2. EXTRACTION (Nouvelle extraction)"
        title="Nouvelle extraction"
        description="Importe tes documents, configure Gemini ou OCR local puis lance le meme pipeline metier dans une interface plus guidee."
      />

      <div className="flex flex-wrap items-center gap-4 rounded-[18px] border border-[rgba(139,147,172,0.14)] bg-[#fbfcff] px-4 py-3 text-[12px] text-[#5e6888] dark:border-white/10 dark:bg-[#0f1525] dark:text-[#b1bcda]">
        {["Importer", "Configurer", "Traiter", "Resultats"].map((step, index) => (
          <div key={step} className="flex items-center gap-3">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full border text-[11px] font-bold ${
                index === 0
                  ? "border-[#89d9ac] bg-[#edf9f1] text-[#2eb764] dark:border-[#1f6b41] dark:bg-[#11271d] dark:text-[#86f7b6]"
                  : "border-[rgba(139,147,172,0.18)] bg-white text-[#8d95ae] dark:border-white/10 dark:bg-[#101625] dark:text-[#9ca6c6]"
              }`}
            >
              {index + 1}
            </span>
            <span className="font-semibold">{step}</span>
            {index < 3 ? <span className="text-[#ccd2e3]"> </span> : null}
          </div>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.06fr,0.64fr]">
        <div className="space-y-4">
          <Card>
            <div className="mb-4 proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
              Importer vos documents
            </div>
            <div className="mb-4 text-[12px] text-[#8d95ae]">
              Glissez-deposez vos fichiers ici ou parcourez.
            </div>
            <label className="flex min-h-[240px] cursor-pointer flex-col items-center justify-center gap-4 rounded-[18px] border border-dashed border-[rgba(124,77,255,0.28)] bg-[#fcfbff] px-6 py-8 text-center dark:border-[#4a3f78] dark:bg-[#0f1525]">
              <div className="flex h-14 w-14 items-center justify-center rounded-full border border-[rgba(139,147,172,0.16)] bg-white text-[#7c4dff] dark:border-white/10 dark:bg-[#121829]">
                <CloudUpload className="h-7 w-7" />
              </div>
              <div>
                <div className="proto-title text-[18px] font-bold text-[#1b2440] dark:text-white">
                  Glissez vos fichiers ici
                </div>
                <div className="mt-1 text-[12px] text-[#8d95ae]">ou</div>
              </div>
              <input
                className="hidden"
                type="file"
                accept=".jpg,.jpeg,.png,.tif,.tiff,.pdf"
                multiple
                onChange={(event) => handleFileChange(event.target.files)}
              />
              <span className="inline-flex h-10 items-center rounded-xl bg-gradient-to-r from-[#7c4dff] to-[#6d43f0] px-4 text-sm font-semibold text-white">
                Parcourir les fichiers
              </span>
            </label>

            <div className="mt-5">
              <div className="mb-3 text-[12px] font-semibold text-[#687292]">Type de documents</div>
              <div className="grid gap-3 sm:grid-cols-5">
                {meta?.modes.map((item) => {
                  const visual = modeVisuals[item.value] ?? { title: item.label, hint: "" };
                  const active = mode === item.value;
                  return (
                    <button
                      key={item.value}
                      type="button"
                      onClick={() => setMode(item.value)}
                      className={`rounded-[16px] border p-3 text-left transition ${
                        active
                          ? "border-[#89d9ac] bg-[#edf9f1] shadow-[0_8px_20px_rgba(46,183,100,0.1)] dark:border-[#1f6b41] dark:bg-[#11271d]"
                          : "border-[rgba(139,147,172,0.14)] bg-white hover:bg-[#fafbff] dark:border-white/10 dark:bg-[#121829] dark:hover:bg-[#141c2e]"
                      }`}
                    >
                      <div className="proto-title text-[13px] font-bold text-[#1b2440] dark:text-white">
                        {visual.title}
                      </div>
                      <div className="mt-1 text-[11px] text-[#8d95ae]">{visual.hint}</div>
                    </button>
                  );
                })}
              </div>
            </div>
          </Card>

          <Card>
            <div className="mb-3 flex items-center gap-2 text-[13px] font-semibold text-[#1b2440] dark:text-white">
              <Info className="h-4 w-4 text-[#7c4dff]" />
              Informations
            </div>
            <ul className="space-y-2 text-[12px] text-[#6b7594] dark:text-[#b1bcda]">
              <li>Formats supportes : JPG, PNG, PDF</li>
              <li>Taille max : 20 Mo par fichier</li>
              <li>Extraction avec IA (Gemini) ou OCR</li>
            </ul>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="space-y-4">
            <div className="proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
              Configuration
            </div>

            <div className="space-y-2">
              <div className="text-[12px] font-semibold text-[#687292]">Methode d'extraction</div>
              <Select
                value={method}
                onChange={(event) => {
                  setMethod(event.target.value);
                  writeStoredValue(storageKeys.defaultMethod, event.target.value);
                }}
              >
                {availableMethods.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </Select>
              <div className="rounded-xl bg-[#eef9f0] px-3 py-2 text-[11px] text-[#2eb764] dark:bg-[#11271d] dark:text-[#86f7b6]">
                Recommande pour une meilleure precision
              </div>
            </div>

            <Switch
              checked={advanced}
              onChange={setAdvanced}
              label="Extraction avancee"
            />

            <div className="space-y-2">
              <div className="text-[12px] font-semibold text-[#687292]">Langue du document</div>
              <Select defaultValue="Francais">
                <option>Francais</option>
                <option>Anglais</option>
                <option>Mixte</option>
              </Select>
            </div>

            <div className="space-y-2">
              <div className="text-[12px] font-semibold text-[#687292]">Cle Gemini</div>
              <Input
                type="password"
                value={geminiApiKey}
                onChange={(event) => setGeminiApiKey(event.target.value)}
                placeholder="GEMINI_API_KEY"
              />
              <Input
                value={geminiModel}
                onChange={(event) => setGeminiModel(event.target.value)}
                placeholder="Modele Gemini"
              />
            </div>

            <div className="rounded-[16px] border border-[rgba(139,147,172,0.14)] bg-[#fbfcff] p-3 text-[12px] text-[#6b7594] dark:border-white/10 dark:bg-[#0f1525] dark:text-[#b1bcda]">
              <div className="mb-1 font-semibold text-[#1b2440] dark:text-white">Ou mettre la cle Gemini ?</div>
              <div className="mb-2">
                Modeles actifs :{" "}
                {activeModelIds.includes("gemini-api") ? "Gemini" : ""}
                {activeModelIds.includes("gemini-api") && activeModelIds.includes("ocr-local") ? " + " : ""}
                {activeModelIds.includes("ocr-local") ? "OCR local" : ""}
                {!activeModelIds.length ? "Configuration par defaut" : ""}
              </div>
              <div>{meta?.geminiInstructions.session}</div>
              <div className="mt-2">{meta?.geminiInstructions.server}</div>
            </div>
          </Card>

          <Card className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-[12px] font-semibold text-[#687292]">Fichiers charges</div>
              <Badge tone="purple">{files.length}</Badge>
            </div>
            <div className="space-y-2">
              {files.length ? (
                files.map((file) => (
                  <div
                    key={`${file.name}-${file.size}`}
                    className="flex items-center justify-between rounded-xl border border-[rgba(139,147,172,0.12)] bg-[#fbfcff] px-3 py-2 dark:border-white/10 dark:bg-[#0f1525]"
                  >
                    <div className="flex items-center gap-2">
                      <FileStack className="h-4 w-4 text-[#7c4dff]" />
                      <span className="text-[12px] font-medium text-[#1b2440] dark:text-white">
                        {file.name}
                      </span>
                    </div>
                    <span className="text-[11px] text-[#8d95ae]">{(file.size / 1024).toFixed(0)} Ko</span>
                  </div>
                ))
              ) : (
                <div className="text-[12px] text-[#8d95ae]">Aucun document charge.</div>
              )}
            </div>
            <Button onClick={runExtraction} className="w-full justify-between" disabled={loading}>
              <span>{loading ? "Traitement..." : "Suivant"}</span>
              {loading ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            </Button>
            {error ? <div className="text-[12px] text-[#df4d64]">{error}</div> : null}
            {info ? <div className="text-[12px] text-[#b88607]">{info}</div> : null}
            {result ? (
              <div className="rounded-[16px] border border-[rgba(139,147,172,0.14)] bg-[#fbfcff] p-3 dark:border-white/10 dark:bg-[#0f1525]">
                <div className="mb-2 flex items-center justify-between">
                  <div className="text-[12px] font-semibold text-[#1b2440] dark:text-white">Resume batch</div>
                  <Badge tone={result.summary.errorCount ? "warning" : "success"}>
                    {result.summary.okCount}/{result.summary.total}
                  </Badge>
                </div>
                <div className="space-y-2">
                  {result.items.map((item) => (
                    <div key={`${item.filename}-${item.status}`} className="flex items-start justify-between gap-3 text-[12px]">
                      <div>
                        <div className="font-medium text-[#1b2440] dark:text-white">{item.filename}</div>
                        <div className="text-[#8d95ae]">{item.summary.headline}</div>
                      </div>
                      {item.status === "ok" ? (
                        <Check className="h-4 w-4 text-[#2eb764]" />
                      ) : (
                        <span className="text-[#df4d64]">!</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </Card>
        </div>
      </div>
    </div>
  );
}
