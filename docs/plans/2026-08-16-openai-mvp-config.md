# OpenAI MVP Configuration Simplification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace generic LLM deployment settings with a short OpenAI-first configuration contract.

**Architecture:** `Settings` reads an OpenAI key, an optional model with a default, and one exact browser origin. The factory selects OpenAI only when a key exists; otherwise it retains the deterministic local/test adapter. The OpenAI API base URL is a code constant.

**Tech Stack:** FastAPI, Python 3.12, dataclasses, pytest, python-dotenv.

---

### Task 1: Lock the simplified settings and adapter behavior with tests

**Files:**
- Modify: `backend/tests/services/llm/test_adapter_factory.py`
- Modify: `backend/tests/test_cors.py`
- Create: `backend/tests/test_openai_config.py`

**Step 1: Write failing tests**

Test that `OPENAI_API_KEY` produces an `OpenAICompatibleLLMAdapter` with base URL `https://api.openai.com/v1` and default model `gpt-5-mini`; test `OPENAI_MODEL` overrides it; test no API key keeps `RuleBasedLLMAdapter`; test `CORS_ORIGIN` permits the exact configured origin.

**Step 2: Verify RED**

Run: `cd backend && uv run pytest tests/services/llm/test_adapter_factory.py tests/test_cors.py tests/test_openai_config.py -v`

Expected: FAIL because the generic settings/provider contract is still present.

**Step 3: Implement the minimal settings/factory change**

Update `backend/app/core/config.py`, `backend/app/services/llm/factory.py`, and `backend/app/main.py` to use `OPENAI_API_KEY`, optional `OPENAI_MODEL`, fixed OpenAI base URL, `CORS_ORIGIN`, and rule-based fallback.

**Step 4: Verify GREEN**

Run the focused pytest command; expected PASS.

**Step 5: Commit**

```bash
git add backend/app/core/config.py backend/app/services/llm/factory.py backend/app/main.py backend/tests
git commit -m "feat: simplify OpenAI MVP configuration"
```

### Task 2: Document the minimal deployment contract

**Files:**
- Modify: `backend/.env.example`
- Modify: `README.md`

**Step 1: Write a documentation assertion/checklist**

Confirm documentation names only `OPENAI_API_KEY`, optional `OPENAI_MODEL`, `CORS_ORIGIN`, and frontend `NEXT_PUBLIC_API_BASE_URL` as cloud deployment variables. It must state that `OPENAI_API_KEY` belongs to backend deployment only.

**Step 2: Update docs minimally**

Provide copy-paste deployment examples and retain host/port only in a local-development subsection.

**Step 3: Verify full regression suite**

Run: `cd backend && uv run pytest -q`

Expected: PASS.

**Step 4: Commit**

```bash
git add backend/.env.example README.md
git commit -m "docs: simplify deployment environment setup"
```

### Task 3: Final verification

**Files:**
- Verify only

**Step 1: Run backend suite**

Run: `cd backend && uv run pytest -q`

Expected: PASS.

**Step 2: Check source formatting**

Run: `git diff --check`

Expected: no whitespace errors.

**Step 3: Review config exposure**

Verify no `OPENAI_API_KEY` appears in frontend source or any `NEXT_PUBLIC_` key.
