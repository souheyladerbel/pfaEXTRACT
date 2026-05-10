from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from pdf2image import convert_from_path
from pypdf import PdfReader

from src.extraction.medical_analysis_extractor import (
    extract_combined_ocr_text,
    extract_fields_from_medical,
)
from src.models.schemas import (
    DocumentMetadata,
    LabInfo,
    LabTest,
    MedicalDocumentResult,
    PatientInfo,
    ProcessingWarning,
    ReferenceRange,
)
from src.services.gemini_llm import analyze_medical_document_gemini


def _to_float(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    txt = str(value).strip().replace(" ", "").replace(",", ".")
    try:
        return float(txt)
    except ValueError:
        return None


def _parse_reference_range(raw: Optional[str]) -> Optional[ReferenceRange]:
    if not raw:
        return None
    txt = raw.replace(",", ".")
    nums: List[float] = []
    for token in txt.replace("a", " ").replace("à", " ").replace("-", " ").split():
        try:
            nums.append(float(token))
        except ValueError:
            pass
    if len(nums) >= 2:
        return ReferenceRange(min=min(nums), max=max(nums), raw_text=raw)
    return ReferenceRange(raw_text=raw)


def _normalize_name(raw_name: str) -> str:
    n = raw_name.lower()
    mapping: Dict[str, List[str]] = {
        "tsh": ["tsh", "thyreostimuline"],
        "vitamin_d": ["vitamine d", "hydroxy", "25-oh"],
        "glucose": ["glycem", "glucose"],
        "cholesterol_total": ["cholesterol total"],
        "hdl_cholesterol": ["hdl"],
        "ldl_cholesterol": ["ldl"],
        "triglycerides": ["triglycer"],
        "creatinine": ["creatinin"],
        "urea": ["uree", "urée"],
        "hemoglobin": ["hemoglob", "hémoglob"],
        "hematocrit": ["hematocrit", "hématocrit"],
        "leukocytes": ["leucocyt", "leukocyt"],
        "platelets": ["plaquette", "platelet"],
        "crp": ["crp", "c reactive"],
    }
    for canonical, keys in mapping.items():
        if any(k in n for k in keys):
            return canonical
    return "unknown"


def _map_category(raw_name: str) -> str:
    n = raw_name.lower()
    if any(k in n for k in ["hemoglob", "hémoglob", "leucocyt", "plaquette", "hematocrit"]):
        return "hematology"
    if any(k in n for k in ["tsh", "thyre", "vitamine d"]):
        return "hormonology"
    if any(k in n for k in ["crp", "anticorps", "hiv", "hbs", "serolog"]):
        return "serology"
    if any(k in n for k in ["glycem", "glucose", "creatinin", "uree", "cholesterol", "hdl", "ldl"]):
        return "biochemistry"
    return "other"


def _compute_status(value: Optional[float], rr: Optional[ReferenceRange]) -> str:
    if value is None or rr is None or rr.min is None or rr.max is None:
        return "unknown"
    if value < rr.min:
        return "low"
    if value > rr.max:
        return "high"
    return "normal"


def _rows_to_tests(rows: List[Dict[str, Optional[str]]]) -> List[LabTest]:
    tests: List[LabTest] = []
    for row in rows:
        raw_name = (row.get("parametre") or "unknown").strip()
        val = _to_float(row.get("valeur"))
        vraw = row.get("valeur")
        vtxt = None if val is not None else (str(vraw).strip() if vraw else None)
        rr = _parse_reference_range(row.get("valeurs_normales"))
        tests.append(
            LabTest(
                raw_test_name=raw_name,
                normalized_name=_normalize_name(raw_name),
                category=_map_category(raw_name),
                value_text=vtxt,
                value=val,
                unit=row.get("unite"),
                reference_range=rr,
                status=_compute_status(val, rr),
                raw_line=row.get("ligne_complete") or raw_name,
                confidence=0.7 if val is not None else 0.4,
            )
        )
    return tests


def _baseline_from_extracted(extracted, source_file: str) -> MedicalDocumentResult:
    return MedicalDocumentResult(
        document_type="medical_lab_report",
        lab_info=LabInfo(lab_name=extracted.laboratoire),
        patient_info=PatientInfo(patient_name=extracted.patient_nom),
        document_metadata=DocumentMetadata(
            dossier_number=extracted.reference_dossier,
            sample_date=extracted.date_prelevement,
            report_date=extracted.date_resultat,
            source_file=source_file,
        ),
        tests=_rows_to_tests(extracted.resultats_analyses),
        warnings=[],
        extraction_source="ocr",
    )


def _merge_gemini_with_baseline(
    gem: MedicalDocumentResult, base: MedicalDocumentResult, ocr_text: str
) -> MedicalDocumentResult:
    if not gem.lab_info.lab_name and base.lab_info.lab_name:
        gem.lab_info.lab_name = base.lab_info.lab_name
    if not gem.patient_info.patient_name and base.patient_info.patient_name:
        gem.patient_info.patient_name = base.patient_info.patient_name
    if not gem.document_metadata.dossier_number and base.document_metadata.dossier_number:
        gem.document_metadata.dossier_number = base.document_metadata.dossier_number
    if not gem.document_metadata.sample_date and base.document_metadata.sample_date:
        gem.document_metadata.sample_date = base.document_metadata.sample_date
    if not gem.document_metadata.report_date and base.document_metadata.report_date:
        gem.document_metadata.report_date = base.document_metadata.report_date
    gem.raw_text = ocr_text[:80_000] if ocr_text else gem.raw_text
    gem.warnings.extend([w for w in base.warnings if w not in gem.warnings])
    return gem


def process_medical_file(
    file_path: Path,
    *,
    use_gemini: bool = False,
    gemini_api_key: Optional[str] = None,
    gemini_model: Optional[str] = None,
) -> MedicalDocumentResult:
    warnings: List[ProcessingWarning] = []
    suffix = file_path.suffix.lower()
    api_key = gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    model = gemini_model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def _try_gemini(ocr_text: str, image_for_model: Optional[Path]) -> tuple[Optional[MedicalDocumentResult], List[ProcessingWarning]]:
        if not use_gemini or not api_key:
            return None, []
        try:
            gem = analyze_medical_document_gemini(
                api_key=api_key,
                model_name=model,
                ocr_text=ocr_text,
                image_path=image_for_model,
                source_file=str(file_path),
            )
            return gem, []
        except Exception as exc:
            return None, [
                ProcessingWarning(code="GEMINI_FAILED", message=str(exc), context=str(file_path))
            ]

    if suffix in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
        ocr_text = extract_combined_ocr_text(file_path)
        extracted = extract_fields_from_medical(file_path)
        baseline = _baseline_from_extracted(extracted, str(file_path))
        baseline.raw_text = ocr_text[:80_000]

        gem, gem_err = _try_gemini(ocr_text, file_path)
        baseline.warnings.extend(warnings)
        baseline.warnings.extend(gem_err)
        if gem and len(gem.tests) > 0:
            return _merge_gemini_with_baseline(gem, baseline, ocr_text)
        if gem and len(gem.tests) == 0 and len(baseline.tests) > 0:
            baseline.warnings.append(
                ProcessingWarning(
                    code="GEMINI_EMPTY_TESTS",
                    message="Gemini n'a retourne aucun test ; affichage OCR.",
                )
            )
            return baseline
        if gem:
            return _merge_gemini_with_baseline(gem, baseline, ocr_text)
        return baseline

    if suffix == ".pdf":
        raw_text = ""
        try:
            reader = PdfReader(str(file_path))
            raw_text = "\n".join([(p.extract_text() or "") for p in reader.pages]).strip()
        except Exception as exc:
            warnings.append(
                ProcessingWarning(code="PDF_TEXT_READ_FAILED", message=str(exc), context=str(file_path))
            )

        fd, tmp_png = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        png_path = Path(tmp_png)
        try:
            pages = convert_from_path(str(file_path), dpi=200, first_page=1, last_page=1)
            if not pages:
                return MedicalDocumentResult(
                    document_metadata=DocumentMetadata(source_file=str(file_path)),
                    raw_text=raw_text or None,
                    warnings=warnings
                    + [ProcessingWarning(code="PDF_NO_PAGE", message="Aucune page convertie")],
                    extraction_source="ocr",
                )
            pages[0].save(png_path)

            ocr_text = extract_combined_ocr_text(png_path)
            if raw_text:
                ocr_text = f"--- TEXTE PDF (copie) ---\n{raw_text[:40_000]}\n\n{ocr_text}"

            extracted = extract_fields_from_medical(png_path)
            baseline = _baseline_from_extracted(extracted, str(file_path))
            baseline.raw_text = ocr_text[:80_000]

            gem, gem_err = _try_gemini(ocr_text, png_path)
            baseline.warnings.extend(warnings)
            baseline.warnings.extend(gem_err)
            if gem and len(gem.tests) > 0:
                return _merge_gemini_with_baseline(gem, baseline, ocr_text)
            if gem and len(gem.tests) == 0 and len(baseline.tests) > 0:
                baseline.warnings.append(
                    ProcessingWarning(
                        code="GEMINI_EMPTY_TESTS",
                        message="Gemini n'a retourne aucun test ; affichage OCR.",
                    )
                )
                return baseline
            if gem:
                return _merge_gemini_with_baseline(gem, baseline, ocr_text)
            return baseline
        finally:
            png_path.unlink(missing_ok=True)

    return MedicalDocumentResult(
        document_metadata=DocumentMetadata(source_file=str(file_path)),
        warnings=[ProcessingWarning(code="UNSUPPORTED_FILE_TYPE", message=f"Type non supporte: {suffix}")],
        extraction_source="ocr",
    )
