## UI spec (Streamlit) — high level

Этот документ содержит детали UI, вынесенные из `specs/Tech_Req.md` (раздел 4).

### Боковая панель
- LLM Provider API-ключ (MVP: OpenRouter; в сессии)
- Выбор модели
- Путь к папке + «Загрузить»

Настройки (см. ссылки на разделы ТЗ):
- PII Masking Service (см. `F3`): URL/метод/опции (`model_id`, `timeout_seconds`), health/methods, чекбокс bypass.
- OCR (см. `F2`): включение OCR и его параметры.
- Limits & Tokens (одно место; source of truth = settings):
  - `prompt_budget_tokens`, `max_output_tokens`
  - `per_file_structure_tokens`, `per_file_evidence_tokens`
  - `pdf_evidence_pages_max`
  - `evidence_keep_first_n_files` (MVP compression, `F1.3.MVP`)
  - token estimate: `k`
  - quick actions: `reset_defaults`, `save_preset`, `load_preset`
  - always-visible summary: current values + `tokens_prompt_total_est` + status `fits/exceeds`

### Основная область
- Материалы: просмотр Full Corpus + список файлов с `tokens_total_full_est`
- OCR (опционально): запуск OCR, просмотр результатов
- Маскировка: «Скрыть личные данные», предпросмотр
- Анализ: поле “Задание”, «Анализировать», предпросмотр промпта с показом токен‑сводки
- Уточнения: ответы на вопросы + файлы, «Отправить уточнения» + предпросмотр

### MVP: UI “Прозрачность сжатия” (F1.3.1)
- **Token summary**: `tokens_full_corpus_est`, `tokens_prompt_corpus_est`, `tokens_prompt_total_est` (до/после + итог).
- **Таблица файлов** (1 строка = 1 файл):
  - `rel_path`
  - `tokens_full_est.total` → `tokens_prompt_est.total`
  - флаги: `evidence_removed` (bool), `evidence_trimmed` (bool = `evidence_after < evidence_before`)
  - для `.pdf`: `pdf_included_pages` (если применимо)
  - для `.csv/.xlsx`: `table_included_ranges` (если применимо)
- **Два read-only предпросмотра**: `Full Corpus` и `Prompt Corpus` (второй = “ровно то, что уйдёт в LLM Provider”).

