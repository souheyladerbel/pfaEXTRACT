"use client";

import {
  Bot,
  Check,
  CircleHelp,
  FolderArchive,
  Globe,
  Info,
  LayoutGrid,
  Monitor,
  MoonStar,
  RotateCcw,
  Shield,
  SlidersHorizontal,
  Sparkles,
  SunMedium
} from "lucide-react";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { useTheme } from "@/components/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { fetchMeta } from "@/lib/api";
import {
  readStoredJson,
  readStoredValue,
  storageKeys,
  writeStoredJson,
  writeStoredValue
} from "@/lib/storage";
import { cn } from "@/lib/utils";
import type { MetaPayload } from "@/lib/types";

type SettingsTab = "general" | "extraction" | "ai" | "security" | "storage";

type UiSettings = {
  appName: string;
  version: string;
  language: string;
  timezone: string;
  dateFormat: string;
  numberFormat: string;
  density: "comfortable" | "compact" | "spacious";
  animations: boolean;
  autoVerify: boolean;
  autoSaveResults: boolean;
  confirmDeletion: boolean;
  advancedMode: boolean;
};

const settingsDefaults: UiSettings = {
  appName: "DocuAI",
  version: "v2.1.0",
  language: "Francais",
  timezone: "(UTC+01:00) Europe/Paris",
  dateFormat: "10 mai 2026 (DD MMMM YYYY)",
  numberFormat: "1 234,56",
  density: "comfortable",
  animations: true,
  autoVerify: true,
  autoSaveResults: true,
  confirmDeletion: true,
  advancedMode: false,
};

const tabItems: Array<{ value: SettingsTab; label: string; icon: typeof Globe }> = [
  { value: "general", label: "General", icon: Globe },
  { value: "extraction", label: "Extraction OCR", icon: Sparkles },
  { value: "ai", label: "IA & Modeles", icon: Bot },
  { value: "security", label: "Securite", icon: Shield },
  { value: "storage", label: "Stockage & Exports", icon: FolderArchive },
];

function SectionShell({
  icon,
  title,
  description,
  children
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-[22px] border border-[rgba(139,147,172,0.12)] bg-white p-4 shadow-[0_10px_28px_rgba(18,27,52,0.04)] dark:border-white/10 dark:bg-[#121829]">
      <div className="grid gap-4 lg:grid-cols-[170px,minmax(0,1fr)]">
        <div className="space-y-4">
          <div>
            <div className="text-[15px] font-bold text-[#1b2440] dark:text-white">{title}</div>
            <div className="mt-1 text-[12px] leading-6 text-[#7a83a2] dark:text-[#aeb7d2]">
              {description}
            </div>
          </div>
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[linear-gradient(145deg,#f4fff8,#edf5ff)] text-[#30c56f] shadow-[inset_0_0_0_1px_rgba(48,197,111,0.08)] dark:bg-[linear-gradient(145deg,#11271d,#101625)] dark:text-[#86f7b6]">
            {icon}
          </div>
        </div>
        <div>{children}</div>
      </div>
    </div>
  );
}

function SegmentButton({
  active,
  icon,
  label,
  onClick
}: {
  active: boolean;
  icon?: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex h-11 items-center justify-center gap-2 rounded-xl border px-4 text-sm font-medium transition",
        active
          ? "border-[#9de0b8] bg-[#f1fcf5] text-[#27b665] shadow-[0_10px_20px_rgba(48,197,111,0.08)] dark:border-[#226a44] dark:bg-[#10271c] dark:text-[#8ef8b8]"
          : "border-[rgba(139,147,172,0.16)] bg-white text-[#55607f] hover:bg-[#fafcff] dark:border-white/10 dark:bg-[#0f1525] dark:text-[#b1bcda] dark:hover:bg-[#141b2c]"
      )}
    >
      {icon}
      {label}
    </button>
  );
}

function ToggleRow({
  label,
  description,
  checked,
  onChange
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-2">
      <div className="min-w-0">
        <div className="text-sm font-medium text-[#1b2440] dark:text-white">{label}</div>
        <div className="text-[12px] leading-5 text-[#7a83a2] dark:text-[#aeb7d2]">{description}</div>
      </div>
      <button
        type="button"
        aria-pressed={checked}
        onClick={() => onChange(!checked)}
        className={`relative h-6 w-11 shrink-0 rounded-full transition ${
          checked ? "bg-[#30c56f]" : "bg-[#d5dbec] dark:bg-[#2a3450]"
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${
            checked ? "left-5" : "left-0.5"
          }`}
        />
      </button>
    </div>
  );
}

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [meta, setMeta] = useState<MetaPayload | null>(null);
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");
  const [uiSettings, setUiSettings] = useState<UiSettings>(settingsDefaults);
  const [aiProvider, setAiProvider] = useState("gemini");
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [openaiModel, setOpenaiModel] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [anthropicModel, setAnthropicModel] = useState("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchMeta().then((payload) => {
      setMeta(payload);
      setUiSettings(readStoredJson(storageKeys.uiSettings, settingsDefaults));
      setAiProvider(readStoredValue(storageKeys.aiProvider, "gemini"));
      setGeminiKey(readStoredValue(storageKeys.geminiKey, ""));
      setGeminiModel(readStoredValue(storageKeys.geminiModel, payload.defaultGeminiModel));
      setOpenaiKey(readStoredValue(storageKeys.openaiKey, ""));
      setOpenaiModel(readStoredValue(storageKeys.openaiModel, "gpt-4o"));
      setAnthropicKey(readStoredValue(storageKeys.anthropicKey, ""));
      setAnthropicModel(readStoredValue(storageKeys.anthropicModel, "claude-3-5-sonnet-latest"));
    });
  }, []);

  const saveSettings = () => {
    writeStoredJson(storageKeys.uiSettings, uiSettings);
    writeStoredValue(storageKeys.aiProvider, aiProvider);
    writeStoredValue(storageKeys.geminiKey, geminiKey);
    writeStoredValue(storageKeys.geminiModel, geminiModel);
    writeStoredValue(storageKeys.openaiKey, openaiKey);
    writeStoredValue(storageKeys.openaiModel, openaiModel);
    writeStoredValue(storageKeys.anthropicKey, anthropicKey);
    writeStoredValue(storageKeys.anthropicModel, anthropicModel);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1800);
  };

  const resetSettings = () => {
    setUiSettings(settingsDefaults);
    setAiProvider("gemini");
    setGeminiKey("");
    setGeminiModel(meta?.defaultGeminiModel ?? "gemini-2.5-flash");
    setOpenaiKey("");
    setOpenaiModel("gpt-4o");
    setAnthropicKey("");
    setAnthropicModel("claude-3-5-sonnet-latest");
    setTheme("system");
    setSaved(false);
  };

  const updateSetting = <K extends keyof UiSettings>(key: K, value: UiSettings[K]) => {
    setUiSettings((current) => ({ ...current, [key]: value }));
    setSaved(false);
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="7. PARAMETRES"
        title="Parametres"
        description="Personnalisez l'application selon vos besoins."
        action={
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="secondary" onClick={resetSettings} className="gap-2">
              <RotateCcw className="h-4 w-4" />
              Reinitialiser les parametres
            </Button>
            <Button variant="success" onClick={saveSettings} className="gap-2">
              <Check className="h-4 w-4" />
              Enregistrer les modifications
            </Button>
          </div>
        }
      />

      <Card className="space-y-5">
        <div className="flex flex-wrap items-center gap-2 border-b border-[rgba(139,147,172,0.12)] pb-3 dark:border-white/10">
          {tabItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.value}
                type="button"
                onClick={() => setActiveTab(item.value)}
                className={cn(
                  "inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-[12px] font-semibold transition",
                  activeTab === item.value
                    ? "border-[#9de0b8] bg-[#f1fcf5] text-[#27b665] dark:border-[#226a44] dark:bg-[#10271c] dark:text-[#8ef8b8]"
                    : "border-transparent text-[#697390] hover:border-[rgba(139,147,172,0.12)] hover:bg-[#fbfcff] dark:text-[#b1bcda] dark:hover:border-white/10 dark:hover:bg-[#141b2c]"
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </div>

        {saved ? (
          <div className="flex items-center justify-end">
            <Badge tone="success">Modifications enregistrees</Badge>
          </div>
        ) : null}

        {activeTab === "general" ? (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
            <div className="space-y-4">
              <SectionShell
                icon={<Info className="h-5 w-5" />}
                title="Informations generales"
                description="Configurez les informations de base de votre application."
              >
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <div className="text-[12px] font-semibold text-[#687292]">Nom de l'application</div>
                    <Input
                      value={uiSettings.appName}
                      onChange={(event) => updateSetting("appName", event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="text-[12px] font-semibold text-[#687292]">Fuseau horaire</div>
                    <Select
                      value={uiSettings.timezone}
                      onChange={(event) => updateSetting("timezone", event.target.value)}
                    >
                      <option>(UTC+01:00) Europe/Paris</option>
                      <option>(UTC+01:00) Africa/Lagos</option>
                      <option>(UTC+00:00) UTC</option>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <div className="text-[12px] font-semibold text-[#687292]">Version</div>
                    <Input
                      value={uiSettings.version}
                      onChange={(event) => updateSetting("version", event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <div className="text-[12px] font-semibold text-[#687292]">Format de date</div>
                    <Select
                      value={uiSettings.dateFormat}
                      onChange={(event) => updateSetting("dateFormat", event.target.value)}
                    >
                      <option>10 mai 2026 (DD MMMM YYYY)</option>
                      <option>2026-05-10 (YYYY-MM-DD)</option>
                      <option>10/05/2026 (DD/MM/YYYY)</option>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <div className="text-[12px] font-semibold text-[#687292]">Langue</div>
                    <Select
                      value={uiSettings.language}
                      onChange={(event) => updateSetting("language", event.target.value)}
                    >
                      <option>Francais</option>
                      <option>Anglais</option>
                      <option>Arabe</option>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <div className="text-[12px] font-semibold text-[#687292]">Format de nombre</div>
                    <Select
                      value={uiSettings.numberFormat}
                      onChange={(event) => updateSetting("numberFormat", event.target.value)}
                    >
                      <option>1 234,56</option>
                      <option>1,234.56</option>
                      <option>1234.56</option>
                    </Select>
                  </div>
                </div>
              </SectionShell>

              <SectionShell
                icon={<Monitor className="h-5 w-5" />}
                title="Preferences d'affichage"
                description="Personnalisez l'interface selon vos preferences."
              >
                <div className="space-y-5">
                  <div className="space-y-2">
                    <div className="text-[12px] font-semibold text-[#687292]">Theme</div>
                    <div className="flex flex-wrap gap-2">
                      <SegmentButton
                        active={theme === "light"}
                        label="Clair"
                        icon={<SunMedium className="h-4 w-4" />}
                        onClick={() => setTheme("light")}
                      />
                      <SegmentButton
                        active={theme === "dark"}
                        label="Sombre"
                        icon={<MoonStar className="h-4 w-4" />}
                        onClick={() => setTheme("dark")}
                      />
                      <SegmentButton
                        active={theme === "system"}
                        label="Systeme"
                        icon={<Monitor className="h-4 w-4" />}
                        onClick={() => setTheme("system")}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="text-[12px] font-semibold text-[#687292]">Densite de l'interface</div>
                    <div className="flex flex-wrap gap-2">
                      <SegmentButton
                        active={uiSettings.density === "comfortable"}
                        label="Confortable"
                        icon={<LayoutGrid className="h-4 w-4" />}
                        onClick={() => updateSetting("density", "comfortable")}
                      />
                      <SegmentButton
                        active={uiSettings.density === "compact"}
                        label="Compacte"
                        icon={<LayoutGrid className="h-4 w-4" />}
                        onClick={() => updateSetting("density", "compact")}
                      />
                      <SegmentButton
                        active={uiSettings.density === "spacious"}
                        label="Spacieuse"
                        icon={<LayoutGrid className="h-4 w-4" />}
                        onClick={() => updateSetting("density", "spacious")}
                      />
                    </div>
                  </div>

                  <ToggleRow
                    label="Animations"
                    description="Activer les animations et transitions."
                    checked={uiSettings.animations}
                    onChange={(next) => updateSetting("animations", next)}
                  />
                </div>
              </SectionShell>

              <SectionShell
                icon={<SlidersHorizontal className="h-5 w-5" />}
                title="Comportement de l'application"
                description="Definissez le comportement par defaut de l'application."
              >
                <div className="divide-y divide-[rgba(139,147,172,0.12)] dark:divide-white/10">
                  <ToggleRow
                    label="Verification automatique des nouveaux documents"
                    description="Verifier automatiquement les nouveaux documents importes."
                    checked={uiSettings.autoVerify}
                    onChange={(next) => updateSetting("autoVerify", next)}
                  />
                  <ToggleRow
                    label="Sauvegarde automatique des resultats"
                    description="Enregistrer automatiquement les resultats d'extraction."
                    checked={uiSettings.autoSaveResults}
                    onChange={(next) => updateSetting("autoSaveResults", next)}
                  />
                  <ToggleRow
                    label="Confirmer avant suppression"
                    description="Demander une confirmation avant de supprimer un document."
                    checked={uiSettings.confirmDeletion}
                    onChange={(next) => updateSetting("confirmDeletion", next)}
                  />
                  <ToggleRow
                    label="Mode avance"
                    description="Afficher les options avancees pour les utilisateurs experimentes."
                    checked={uiSettings.advancedMode}
                    onChange={(next) => updateSetting("advancedMode", next)}
                  />
                </div>
              </SectionShell>
            </div>

            <div className="space-y-4">
              <Card className="space-y-4 bg-[linear-gradient(180deg,#fbfff9,white)] dark:bg-[linear-gradient(180deg,#12201a,#101625)]">
                <div>
                  <div className="text-[15px] font-bold text-[#1b2440] dark:text-white">Besoin d'aide ?</div>
                  <div className="mt-1 text-[12px] leading-6 text-[#7a83a2] dark:text-[#aeb7d2]">
                    Consultez notre documentation ou contactez notre equipe.
                  </div>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between rounded-xl border border-[rgba(139,147,172,0.12)] bg-white px-4 py-3 text-sm font-medium text-[#27b665] dark:border-white/10 dark:bg-[#0f1525]">
                    <span>Voir la documentation</span>
                    <span>&gt;</span>
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-[rgba(139,147,172,0.12)] bg-white px-4 py-3 text-sm font-medium text-[#27b665] dark:border-white/10 dark:bg-[#0f1525]">
                    <span>Contacter le support</span>
                    <span>&gt;</span>
                  </div>
                </div>
              </Card>

              <Card className="space-y-3">
                <div className="text-[15px] font-bold text-[#1b2440] dark:text-white">A propos</div>
                <div className="text-[12px] leading-6 text-[#7a83a2] dark:text-[#aeb7d2]">
                  DocuAI est une solution d'extraction intelligente de documents basee sur l'IA.
                </div>
                <div className="text-[12px] text-[#9aa3bf]">© 2026 DocuAI. Tous droits reserves.</div>
              </Card>
            </div>
          </div>
        ) : null}

        {activeTab === "extraction" ? (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <SectionShell
              icon={<Sparkles className="h-5 w-5" />}
              title="Extraction OCR"
              description="Ajustez les preferences d'extraction et le moteur utilise par defaut."
            >
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <div className="text-[12px] font-semibold text-[#687292]">Fournisseur IA par defaut</div>
                  <Select value={aiProvider} onChange={(event) => setAiProvider(event.target.value)}>
                    <option value="gemini">Gemini</option>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                  </Select>
                </div>
                <div className="space-y-2">
                  <div className="text-[12px] font-semibold text-[#687292]">Mode OCR local</div>
                  <Select defaultValue="Tesseract + EasyOCR">
                    <option>Tesseract + EasyOCR</option>
                    <option>Tesseract uniquement</option>
                  </Select>
                </div>
              </div>
            </SectionShell>

            <Card className="space-y-3">
              <div className="text-[15px] font-bold text-[#1b2440] dark:text-white">Conseil</div>
              <div className="text-[12px] leading-6 text-[#7a83a2] dark:text-[#aeb7d2]">
                Utilisez `Gemini` pour les factures et tickets complexes, et `OCR local` comme fallback sans API.
              </div>
            </Card>
          </div>
        ) : null}

        {activeTab === "ai" ? (
          <div className="space-y-4">
            <div className="grid gap-4 xl:grid-cols-3">
              <Card className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-[15px] font-bold text-[#1b2440] dark:text-white">Gemini</div>
                  <Badge tone="success">Actif</Badge>
                </div>
                <Input
                  type="password"
                  value={geminiKey}
                  onChange={(event) => setGeminiKey(event.target.value)}
                  placeholder="GEMINI_API_KEY"
                />
                <Input
                  value={geminiModel}
                  onChange={(event) => setGeminiModel(event.target.value)}
                  placeholder="gemini-2.5-flash"
                />
                <div className="text-[12px] leading-6 text-[#7a83a2] dark:text-[#aeb7d2]">
                  Supporte l'extraction reelle dans cette version.
                </div>
              </Card>

              <Card className="space-y-3">
                <div className="text-[15px] font-bold text-[#1b2440] dark:text-white">OpenAI</div>
                <Input
                  type="password"
                  value={openaiKey}
                  onChange={(event) => setOpenaiKey(event.target.value)}
                  placeholder="OPENAI_API_KEY"
                />
                <Input
                  value={openaiModel}
                  onChange={(event) => setOpenaiModel(event.target.value)}
                  placeholder="gpt-4o"
                />
                <div className="text-[12px] leading-6 text-[#7a83a2] dark:text-[#aeb7d2]">
                  Cle et modele prepares ici. L'integration backend reste a brancher.
                </div>
              </Card>

              <Card className="space-y-3">
                <div className="text-[15px] font-bold text-[#1b2440] dark:text-white">Anthropic</div>
                <Input
                  type="password"
                  value={anthropicKey}
                  onChange={(event) => setAnthropicKey(event.target.value)}
                  placeholder="ANTHROPIC_API_KEY"
                />
                <Input
                  value={anthropicModel}
                  onChange={(event) => setAnthropicModel(event.target.value)}
                  placeholder="claude-3-5-sonnet-latest"
                />
                <div className="text-[12px] leading-6 text-[#7a83a2] dark:text-[#aeb7d2]">
                  Cle et modele prepares ici. L'integration backend reste a brancher.
                </div>
              </Card>
            </div>

            <Card className="space-y-3">
              <div className="text-[15px] font-bold text-[#1b2440] dark:text-white">Emplacement recommande</div>
              <div className="text-[12px] leading-6 text-[#7a83a2] dark:text-[#aeb7d2]">
                {meta?.geminiInstructions.server}
              </div>
              <div className="rounded-xl bg-[#111827] px-3 py-2 font-mono text-[11px] text-[#9bf5b7]">
                {meta?.geminiInstructions.pathHint}
              </div>
            </Card>
          </div>
        ) : null}

        {activeTab === "security" ? (
          <SectionShell
            icon={<Shield className="h-5 w-5" />}
            title="Securite"
            description="Controlez les confirmations et le niveau d'acces aux options sensibles."
          >
            <div className="divide-y divide-[rgba(139,147,172,0.12)] dark:divide-white/10">
              <ToggleRow
                label="Confirmer avant suppression"
                description="Eviter les suppressions accidentelles dans les listes de documents et historiques."
                checked={uiSettings.confirmDeletion}
                onChange={(next) => updateSetting("confirmDeletion", next)}
              />
              <ToggleRow
                label="Mode avance"
                description="Afficher les options sensibles reservees aux utilisateurs experimentes."
                checked={uiSettings.advancedMode}
                onChange={(next) => updateSetting("advancedMode", next)}
              />
            </div>
          </SectionShell>
        ) : null}

        {activeTab === "storage" ? (
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <SectionShell
              icon={<FolderArchive className="h-5 w-5" />}
              title="Stockage & Exports"
              description="Configurez le comportement des exports et l'archivage des documents."
            >
              <div className="divide-y divide-[rgba(139,147,172,0.12)] dark:divide-white/10">
                <ToggleRow
                  label="Sauvegarde automatique des resultats"
                  description="Conserver automatiquement les rapports et sorties structures."
                  checked={uiSettings.autoSaveResults}
                  onChange={(next) => updateSetting("autoSaveResults", next)}
                />
                <ToggleRow
                  label="Verification automatique des nouveaux documents"
                  description="Verifier chaque nouveau document avant stockage final."
                  checked={uiSettings.autoVerify}
                  onChange={(next) => updateSetting("autoVerify", next)}
                />
              </div>
            </SectionShell>

            <Card className="space-y-3">
              <div className="text-[15px] font-bold text-[#1b2440] dark:text-white">Chemin backend</div>
              <div className="rounded-xl bg-[#111827] px-3 py-2 font-mono text-[11px] text-[#9bf5b7]">
                {meta?.geminiInstructions.pathHint}
              </div>
            </Card>
          </div>
        ) : null}
      </Card>
    </div>
  );
}
