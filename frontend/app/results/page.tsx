import { Suspense } from "react";

import { ResultsPageClient } from "@/components/results-page-client";
import { Card } from "@/components/ui/card";

export default function ResultsPage() {
  return (
    <Suspense fallback={<Card>Chargement du resultat...</Card>}>
      <ResultsPageClient />
    </Suspense>
  );
}
