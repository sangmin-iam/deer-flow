# Korean Translation Guide for DeerFlow

## Overview
This document lists all the Korean prompt template files that need to be created to complete Korean language support in DeerFlow.

## Infrastructure Changes (✅ Completed)
- ✅ Frontend locale mapping updated (`web/src/core/api/chat.ts`)
- ✅ Backend CLI updated to support Korean (`main.py`)
- ✅ Korean built-in questions added (`src/config/questions.py`)

## Korean Prompt Templates Required

You need to create 15 Korean prompt template files with the `.ko_KR.md` extension by translating from the corresponding English `.md` files.

### Core Agent Prompts (5 files)

1. **`src/prompts/coder.ko_KR.md`**
   - Translate from: `src/prompts/coder.md`
   - Purpose: Instructions for the code generation agent

2. **`src/prompts/coordinator.ko_KR.md`**
   - Translate from: `src/prompts/coordinator.md`
   - Purpose: Instructions for the coordinator agent that handles user clarification

3. **`src/prompts/planner.ko_KR.md`**
   - Translate from: `src/prompts/planner.md`
   - Purpose: Instructions for the planning agent that creates research plans

4. **`src/prompts/reporter.ko_KR.md`**
   - Translate from: `src/prompts/reporter.md`
   - Purpose: Instructions for the report writing agent

5. **`src/prompts/researcher.ko_KR.md`**
   - Translate from: `src/prompts/researcher.md`
   - Purpose: Instructions for the research agent

### Podcast Prompts (1 file)

6. **`src/prompts/podcast/podcast_script_writer.ko_KR.md`**
   - Translate from: `src/prompts/podcast/podcast_script_writer.md`
   - Purpose: Instructions for generating podcast scripts from reports

### PPT Prompts (1 file)

7. **`src/prompts/ppt/ppt_composer.ko_KR.md`**
   - Translate from: `src/prompts/ppt/ppt_composer.md`
   - Purpose: Instructions for generating PowerPoint presentations

### Prose Prompts (6 files)

8. **`src/prompts/prose/prose_continue.ko_KR.md`**
   - Translate from: `src/prompts/prose/prose_continue.md`
   - Purpose: Instructions for continuing prose writing

9. **`src/prompts/prose/prose_fix.ko_KR.md`**
   - Translate from: `src/prompts/prose/prose_fix.md`
   - Purpose: Instructions for fixing prose issues

10. **`src/prompts/prose/prose_improver.ko_KR.md`**
    - Translate from: `src/prompts/prose/prose_improver.md`
    - Purpose: Instructions for improving prose quality

11. **`src/prompts/prose/prose_longer.ko_KR.md`**
    - Translate from: `src/prompts/prose/prose_longer.md`
    - Purpose: Instructions for expanding prose

12. **`src/prompts/prose/prose_shorter.ko_KR.md`**
    - Translate from: `src/prompts/prose/prose_shorter.md`
    - Purpose: Instructions for condensing prose

13. **`src/prompts/prose/prose_zap.ko_KR.md`**
    - Translate from: `src/prompts/prose/prose_zap.md`
    - Purpose: Instructions for quick prose generation

### Prompt Enhancer (1 file)

14. **`src/prompts/prompt_enhancer/prompt_enhancer.ko_KR.md`**
    - Translate from: `src/prompts/prompt_enhancer/prompt_enhancer.md`
    - Purpose: Instructions for enhancing user prompts

## Translation Guidelines

1. **File naming**: Use `.ko_KR.md` extension (the system automatically converts `ko-KR` locale to `ko_KR` for file lookups)

2. **Jinja2 variables**: Keep all Jinja2 template variables unchanged (e.g., `{{ locale }}`, `{{ CURRENT_TIME }}`, etc.)

3. **Structure**: Maintain the same markdown structure and formatting as the English version

4. **Technical terms**: Translate appropriately for Korean technical audience while maintaining clarity

5. **Fallback behavior**: If a Korean prompt file is missing, the system will automatically fall back to the English version

## Testing

After creating the Korean prompt files:

1. **Test Web Interface**:
   ```bash
   cd web
   pnpm dev
   ```
   - Select Korean (한국어) from the language selector
   - Verify responses are in Korean

2. **Test CLI**:
   ```bash
   python main.py --interactive
   ```
   - Select "한국어" from the language menu
   - Choose a built-in question or ask your own
   - Verify the system uses Korean prompts and responds in Korean

## Notes

- The `{{ locale }}` variable in prompts will be set to `"ko-KR"` when Korean is selected
- Korean translations are already complete for the web frontend UI (`web/messages/ko.json`)
- The backend template system (`src/prompts/template.py`) already supports Korean with no changes needed
- You can translate the files incrementally - missing Korean prompts will fall back to English

## Quick Start Commands

To see which prompt files need translation:
```bash
# List all English prompt files
find src/prompts -name "*.md" -not -name "*zh_CN*" -not -name "*ko_KR*"

# Check if Korean version exists
find src/prompts -name "*.ko_KR.md"
```

