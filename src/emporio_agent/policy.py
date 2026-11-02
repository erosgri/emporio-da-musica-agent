from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pypdf import PdfReader
from rank_bm25 import BM25Okapi

from emporio_agent.models import PolicyChunk, PolicyEvidence, PolicySearchResult
from emporio_agent.normalization import normalize_text

SECTION_HEADINGS = [
    ("1", "Sobre a Empório da Música"),
    ("1.1", "Missão"),
    ("1.2", "Dados da Empresa"),
    ("2", "Horário de Funcionamento"),
    ("3", "Formas de Pagamento"),
    ("3.1", "Regras de Parcelamento"),
    ("4", "Política de Trocas e Devoluções"),
    ("4.1", "Direito de Arrependimento (Compras Online)"),
    ("4.2", "Trocas por Defeito"),
    ("4.3", "Trocas por Preferência"),
    ("4.4", "Itens Não Elegíveis para Troca"),
    ("5", "Política de Frete e Entregas"),
    ("5.1", "Entregas na Região Metropolitana de Campo Grande"),
    ("5.2", "Entregas para Outras Cidades"),
    ("5.3", "Código de Rastreamento"),
    ("6", "Promoções e Descontos"),
    ("6.1", "Tipos de Promoção"),
    ("6.2", "Regras de Promoções"),
    ("7", "Atendimento via WhatsApp"),
    ("7.1", "Diretrizes de Atendimento"),
    ("7.2", "Fluxo de Atendimento Padrão"),
    ("7.3", "Situações Especiais"),
    ("8", "Garantia"),
    ("8.1", "Garantia Legal"),
    ("8.2", "Garantia do Fabricante"),
    ("8.3", "O que Não Cobre a Garantia"),
    ("9", "Privacidade e Proteção de Dados"),
    ("10", "Disposições Finais"),
]

SYNONYMS = {
    "devolucao": ["arrependimento", "reembolso"],
    "arrependimento": ["devolucao", "reembolso"],
    "troca": ["defeito", "preferencia"],
    "entrega": ["frete", "envio", "rastreamento"],
    "frete": ["entrega", "envio"],
    "pagamento": ["pix", "cartao", "boleto", "parcelamento"],
    "horario": ["funcionamento", "expediente"],
    "privacidade": ["dados", "lgpd"],
    "promocao": ["desconto"],
    "garantia": ["defeito", "fabricante"],
}


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean_page(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"Empório da Música Manual de Políticas e Procedimentos", " ", text)
    text = re.sub(r"Página \d+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _split_long_content(content: str, *, size: int = 500, overlap: int = 45) -> list[str]:
    words = content.split()
    if len(words) <= size:
        return [content]
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunks.append(" ".join(words[start : start + size]))
        if start + size >= len(words):
            break
        start += size - overlap
    return chunks


def _section_marker(section_number: str, section_title: str) -> str:
    separator = " " if "." in section_number else ". "
    return f"{section_number}{separator}{section_title}"


def build_policy_index(pdf_path: Path, output_path: Path) -> list[PolicyChunk]:
    reader = PdfReader(pdf_path)
    pages = [_clean_page(page.extract_text() or "") for page in reader.pages]

    page_offsets: list[tuple[int, int, int]] = []
    combined_parts: list[str] = []
    cursor = 0
    for page_number, page_text in enumerate(pages, start=1):
        combined_parts.append(page_text)
        page_offsets.append((cursor, cursor + len(page_text), page_number))
        cursor += len(page_text) + 1
    combined = " ".join(combined_parts)

    located: list[tuple[int, str, str]] = []
    search_start = 0
    for section_number, section_title in SECTION_HEADINGS:
        marker = _section_marker(section_number, section_title)
        position = combined.find(marker, search_start)
        if position < 0:
            raise ValueError(f"Seção não localizada no PDF: {marker}")
        located.append((position, section_number, section_title))
        search_start = position + len(marker)

    document_checksum = _checksum(pdf_path)
    chunks: list[PolicyChunk] = []
    for section_index, (position, section_number, section_title) in enumerate(located):
        marker = _section_marker(section_number, section_title)
        content_start = position + len(marker)
        content_end = (
            located[section_index + 1][0] if section_index + 1 < len(located) else len(combined)
        )
        content = combined[content_start:content_end].strip()
        page_start = next(page for start, end, page in page_offsets if start <= position <= end)
        page_end = next(
            (
                page
                for start, end, page in reversed(page_offsets)
                if start <= max(content_start, content_end - 1) <= end
            ),
            page_start,
        )

        for part_index, part in enumerate(_split_long_content(content), start=1):
            chunk_id = f"policy-{section_number.replace('.', '-')}-{part_index}"
            searchable = normalize_text(f"{section_title} {part}")
            chunks.append(
                PolicyChunk(
                    chunk_id=chunk_id,
                    document_id="politicas-loja",
                    source_file=pdf_path.name,
                    document_version="2.1",
                    section_number=section_number,
                    section_title=section_title,
                    page_start=page_start,
                    page_end=page_end,
                    content=part,
                    normalized_content=searchable,
                    checksum=document_checksum,
                )
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            [chunk.model_dump() for chunk in chunks],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return chunks


def load_or_build_policy_index(pdf_path: Path, output_path: Path) -> list[PolicyChunk]:
    current_checksum = _checksum(pdf_path)
    if output_path.exists():
        raw = json.loads(output_path.read_text(encoding="utf-8"))
        chunks = [PolicyChunk.model_validate(item) for item in raw]
        if chunks and all(chunk.checksum == current_checksum for chunk in chunks):
            return chunks
    return build_policy_index(pdf_path, output_path)


class PolicyRetriever:
    def __init__(self, chunks: list[PolicyChunk]) -> None:
        if not chunks:
            raise ValueError("O índice de políticas não pode estar vazio.")
        self.chunks = chunks
        self.corpus = [chunk.normalized_content.split() for chunk in chunks]
        self.index = BM25Okapi(self.corpus)

    def search(self, topic: str, *, limit: int = 3) -> PolicySearchResult:
        normalized = normalize_text(topic)
        tokens = normalized.split()
        expanded = list(tokens)
        for token in tokens:
            expanded.extend(SYNONYMS.get(token, []))
        scores = self.index.get_scores(expanded)
        ranked = sorted(enumerate(scores), key=lambda item: float(item[1]), reverse=True)

        evidences: list[PolicyEvidence] = []
        for index, score in ranked[:limit]:
            numeric_score = float(score)
            if numeric_score <= 0:
                continue
            chunk = self.chunks[index]
            evidences.append(
                PolicyEvidence(
                    chunk_id=chunk.chunk_id,
                    section_number=chunk.section_number,
                    section_title=chunk.section_title,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    excerpt=chunk.content[:1600],
                    score=round(numeric_score, 4),
                    source_file=chunk.source_file,
                    document_version=chunk.document_version,
                )
            )
        return PolicySearchResult(found=bool(evidences), query=topic, evidences=evidences)
