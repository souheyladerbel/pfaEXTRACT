"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { useTheme } from "@/components/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { fetchMeta } from "@/lib/api";
import { readStoredValue, storageKeys, writeStoredValue } from "@/lib/storage";
import type { MetaPayload } from "@/lib/types";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [meta, setMeta] = useState<MetaPayload | null>(null);
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchMeta().then((payload) => {
      setMeta(payload);
      setGeminiKey(readStoredValue(storageKeys.geminiKey, ""));
      setGeminiModel(readStoredValue(storageKeys.geminiModel, payload.defaultGeminiModel));
    });
  }, []);

  const saveSettings = () => {
    writeStoredValue(storageKeys.geminiKey, geminiKey);
    writeStoredValue(storageKeys.geminiModel, geminiModel);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1800);
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="8. PARAMETRES"
        title="Parametres"
        description="Preferences de l'application, theme et configuration Gemini."
      />

      <div className="flex flex-wrap gap-6 border-b border-[rgba(139,147,172,0.12)] pb-3 text-[12px] font-semibold text-[#7b84a0] dark:border-white/10 dark:text-[#b1bcda]">
        <span className="text-[#2eb764]">General</span>
        <span>Extraction</span>
        <span>IA & Modeles</span>
        <span>Securite</span>
        <span>Notifications</span>
        <span>Integrations</span>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr,1fr]">
        <Card className="space-y-4">
          <div className="proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
            Informations generales
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-[12px] font-semibold text-[#687292]">Nom de l'application</div>
              <Input defaultValue="DocuAI" />
            </div>
            <div className="space-y-2">
              <div className="text-[12px] font-semibold text-[#687292]">Version</div>
              <Input defaultValue="v2.1.0" />
            </div>
            <div className="space-y-2">
              <div className="text-[12px] font-semibold text-[#687292]">Langue</div>
              <Select defaultValue="Francais">
                <option>Francais</option>
                <option>Anglais</option>
              </Select>
            </div>
            <div className="space-y-2">
              <div className="text-[12px] font-semibold text-[#687292]">Fuseau horaire</div>
              <Input defaultValue="(UTC+01:00) Europe/Paris" />
            </div>
          </div>
        </Card>

        <Card className="space-y-4">
          <div className="proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
            Preferences d'affichage
          </div>
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="text-[12px] font-semibold text-[#687292]">Theme</div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setTheme("light")}
                  className={`rounded-full border px-4 py-2 text-[12px] ${
                    theme === "light"
                      ? "border-[#7c4dff] bg-[#f5f0ff] text-[#7c4dff]"
                      : "border-[rgba(139,147,172,0.16)]"
                  }`}
                >
                  Clair
                </button>
                <button
                  type="button"
                  onClick={() => setTheme("dark")}
                  className={`rounded-full border px-4 py-2 text-[12px] ${
                    theme === "dark"
                      ? "border-[#2eb764] bg-[#edf9f1] text-[#2eb764]"
                      : "border-[rgba(139,147,172,0.16)]"
                  }`}
                >
                  Sombre
                </button>
                <button
                  type="button"
                  className="rounded-full border border-[rgba(139,147,172,0.16)] px-4 py-2 text-[12px]"
                >
                  Systeme
                </button>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <div className="text-[12px] font-semibold text-[#687292]">Densite</div>
                <Select defaultValue="Confortable">
                  <option>Confortable</option>
                  <option>Compacte</option>
                </Select>
              </div>
              <div className="space-y-2">
                <div className="text-[12px] font-semibold text-[#687292]">Affichage des resultats</div>
                <Select defaultValue="Par defaut">
                  <option>Par defaut</option>
                  <option>JSON</option>
                  <option>Document</option>
                </Select>
              </div>
            </div>
          </div>
        </Card>

        <Card className="space-y-4 xl:col-span-2">
          <div className="flex items-center justify-between">
            <div className="proto-title text-[15px] font-bold text-[#1b2440] dark:text-white">
              Integration Gemini
            </div>
            {saved ? <Badge tone="success">Enregistre</Badge> : null}
          </div>
          <div className="grid gap-3 xl:grid-cols-[1fr,1fr]">
            <Input
              type="password"
              value={geminiKey}
              onChange={(event) => setGeminiKey(event.target.value)}
              placeholder="GEMINI_API_KEY"
            />
            <Input
              value={geminiModel}
              onChange={(event) => setGeminiModel(event.target.value)}
              placeholder="Modele Gemini"
            />
          </div>
          <div className="rounded-[16px] border border-[rgba(139,147,172,0.14)] bg-[#fbfcff] p-4 text-[12px] text-[#66708e] dark:border-white/10 dark:bg-[#0f1525] dark:text-[#b1bcda]">
            <div className="font-semibold text-[#1b2440] dark:text-white">Emplacement recommande</div>
            <div className="mt-2">{meta?.geminiInstructions.server}</div>
            <div className="mt-3 rounded-xl bg-[#111827] px-3 py-2 font-mono text-[11px] text-[#9bf5b7]">
              {meta?.geminiInstructions.pathHint}
            </div>
          </div>
          <div className="flex justify-end">
            <Button variant="success" onClick={saveSettings}>
              Enregistrer les modifications
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
