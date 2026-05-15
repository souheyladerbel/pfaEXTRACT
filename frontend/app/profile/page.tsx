"use client";

import { ShieldCheck } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function ProfilePage() {
  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="9. PROFIL UTILISATEUR"
        title="Profil utilisateur"
        description="Informations personnelles et acces rapide aux reglages du compte."
      />

      <div className="grid gap-4 xl:grid-cols-[0.65fr,1.35fr]">
        <Card className="space-y-4 text-center">
          <div className="mx-auto mt-3 flex h-28 w-28 items-center justify-center rounded-full bg-[linear-gradient(145deg,#edf1ff,#ffe8ef)]">
            <span className="proto-title text-[30px] font-bold text-[#7c4dff]">AU</span>
          </div>
          <div>
            <div className="proto-title text-[26px] font-bold text-[#1b2440] dark:text-white">
              Admin User
            </div>
            <div className="mt-1 text-[13px] text-[#7a83a2] dark:text-[#96a1c2]">
              admin@docuai.com
            </div>
          </div>
          <div className="mx-auto inline-flex rounded-full bg-[#edf9f1] px-4 py-2 text-[12px] font-semibold text-[#2eb764] dark:bg-[#11271d] dark:text-[#86f7b6]">
            Administrateur
          </div>
          <div className="grid gap-3 rounded-[16px] border border-[rgba(139,147,172,0.12)] bg-[#fbfcff] p-4 text-left text-[12px] text-[#66708e] dark:border-white/10 dark:bg-[#0f1525] dark:text-[#b1bcda]">
            <div className="flex items-center justify-between">
              <span>Membre depuis</span>
              <span className="font-semibold text-[#1b2440] dark:text-white">15 Jan 2026</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Derniere connexion</span>
              <span className="font-semibold text-[#1b2440] dark:text-white">10 Mai 2026 - 14:32</span>
            </div>
          </div>
          <Button variant="secondary">Modifier la photo</Button>
        </Card>

        <Card className="space-y-5">
          <div className="flex flex-wrap gap-6 border-b border-[rgba(139,147,172,0.12)] pb-3 text-[12px] font-semibold text-[#7b84a0] dark:border-white/10 dark:text-[#b1bcda]">
            <span className="text-[#2eb764]">Informations personnelles</span>
            <span>Securite</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-2">
              <div className="text-[12px] font-semibold text-[#687292]">Nom complet</div>
              <div className="rounded-xl border border-[rgba(139,147,172,0.16)] px-3 py-2 text-[13px]">Admin User</div>
            </div>
            <div className="space-y-2">
              <div className="text-[12px] font-semibold text-[#687292]">Email</div>
              <div className="rounded-xl border border-[rgba(139,147,172,0.16)] px-3 py-2 text-[13px]">admin@docuai.com</div>
            </div>
            <div className="space-y-2">
              <div className="text-[12px] font-semibold text-[#687292]">Telephone</div>
              <div className="rounded-xl border border-[rgba(139,147,172,0.16)] px-3 py-2 text-[13px]">+33 6 12 34 56 78</div>
            </div>
            <div className="space-y-2">
              <div className="text-[12px] font-semibold text-[#687292]">Role</div>
              <div className="rounded-xl border border-[rgba(139,147,172,0.16)] px-3 py-2 text-[13px]">Administrateur</div>
            </div>
          </div>
          <div className="rounded-[16px] border border-[rgba(139,147,172,0.14)] bg-[#fbfcff] p-4 text-[12px] text-[#66708e] dark:border-white/10 dark:bg-[#0f1525] dark:text-[#b1bcda]">
            <div className="mb-2 flex items-center gap-2 font-semibold text-[#1b2440] dark:text-white">
              <ShieldCheck className="h-4 w-4 text-[#2eb764]" />
              Securite du compte
            </div>
            Double verification recommandee pour les comptes administrateurs.
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <Button>Enregistrer les modifications</Button>
            <Button variant="danger">Se deconnecter</Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
