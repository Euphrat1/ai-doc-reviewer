## Parsing rules (STRUCTURE + EVIDENCE)

Этот документ содержит детали парсинга материалов в корпус для LLM (Full Corpus), используемый в `specs/Tech_Req.md` (раздел `F1.2`).

### Общий формат блока файла (текстовый рендер для LLM)
Каждый файл рендерится блоком:
- `FILE: <rel_path> | TYPE: <ext> | SIZE: <bytes> | PARSE: ok|warn|fail`
- `STRUCTURE: ...`
- `EVIDENCE: ...` (может быть пустым, если удалён при сжатии Prompt Corpus)

### MVP: `PARSE` статус (ok|warn|fail) — как трактовать и что показывать
- `ok`: парсинг успешен; `STRUCTURE` и `EVIDENCE` заполнены по правилам типа (насколько возможно).
- `warn`: парсинг частично успешен (например: не все страницы PDF извлечены, часть таблицы не прочиталась).
  - `STRUCTURE` **должен** содержать короткое предупреждение/причину (1–2 строки).
  - `EVIDENCE` заполняется тем, что удалось извлечь.
- `fail`: парсинг не удался.
  - `STRUCTURE` **должен** содержать короткую причину ошибки (1–2 строки).
  - `EVIDENCE` должен быть пустым.

UI/экспорт: `parse` показывается рядом с файлом; `warn/fail` считаются “потерей данных на этапе парсинга” (отдельно от потерь из-за сжатия Prompt Corpus).

### MVP: контракт данных корпуса (Full Corpus → Prompt Corpus)
Минимальный контракт данных (в памяти/JSON) для UI/сжатия/экспорта. Источники правды по смыслу: `tech_req.md` (`F1.3`, `F1.3.1`, `F9`).

- **Token estimation**: `tokens_est ~= ceil(chars / k)`, default `k=3.0` (настраиваемо).

**Full Corpus** (без сжатия):
- верхний уровень: `token_estimation.k`, `files[]`, `tokens_full_corpus_est`
- `files[]`: `rel_path`, `ext`, `size_bytes`, `parse(ok|warn|fail)`, `structure_text`, `evidence_text`, `tokens_full_est{structure,evidence,total}`

**Prompt Corpus** (после сжатия):
- верхний уровень: `policy` (лимиты/настройки из UI, см. `specs/ui_spec.md` → `Limits & Tokens`), `files[]`, `tokens_prompt_corpus_est`, `tokens_prompt_total_est`
- `files[]`: `rel_path`, `structure_text`, `evidence_text`, `tokens_prompt_est{structure,evidence,total}`, `compression{evidence_before_tokens_est,evidence_after_tokens_est,evidence_removed,pdf_included_pages?,table_included_ranges?}`

MVP-политика сжатия (детерминированная, простая): источник правды — `tech_req.md`, `F1.3.MVP`.

### Минимальные правила по типам
- `.txt`, `.md`:
  - STRUCTURE: оглавление (если применимо)
  - EVIDENCE: текст (абзацы/списки сохранять)
- `.csv`, `.xlsx`:
  - STRUCTURE: листы (xlsx), размерность, колонки, типы, доля пустых
  - EVIDENCE: первые N строк + N примеров (крайние/нетипичные)
- `.xml`:
  - STRUCTURE: корень, частые элементы, важные атрибуты
  - EVIDENCE: текстовые узлы/атрибуты без “шума”
- `.bpmn`:
  - STRUCTURE: participants/lanes/tasks/events/gateways/flows
  - EVIDENCE: трасса процесса шагами
  - MVP: best-effort; при невозможности разбора → `parse=fail`, `STRUCTURE`=причина (1–2 строки), `EVIDENCE` пустой
- `.drawio`:
  - STRUCTURE: страницы, узлы, связи
  - EVIDENCE: labels + edge-list без координат/стилей
  - MVP: best-effort; при невозможности разбора → `parse=fail`, `STRUCTURE`=причина (1–2 строки), `EVIDENCE` пустой
- `.png`, `.jpg`:
  - без OCR: превью+метаданные в UI; в корпус — только метаданные в STRUCTURE
  - с OCR: EVIDENCE включает `OCR_TEXT` (если OCR включён)
- `.pdf`:
  - STRUCTURE: страницы/оглавление
  - EVIDENCE: `PDF_TEXT` по страницам; OCR fallback при недостатке текста (если OCR включён)

### Примечания
- Парсинг формирует **Full Corpus** (вариант B). Сжатие выполняется при сборке Prompt Corpus (см. `F1.3`).

