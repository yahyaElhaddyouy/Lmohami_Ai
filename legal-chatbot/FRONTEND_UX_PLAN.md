# Frontend UX Plan

## Goals

- Make the chat feel calm, fast, and trustworthy.
- Keep Darija and Arabic readable with RTL support.
- Show sources clearly.
- Give useful recovery when the server, ngrok, or Ollama fails.

## Current Improvements

- Loading/typing state.
- Retry button on failed messages.
- Source chips on assistant messages.
- Example question chips.
- Clear chat action.
- API environment label in the header.
- Base URL normalization to avoid `//chat`.

## Next UI Work

- Add a settings sheet for API environment switching.
- Add dark mode toggle.
- Add source preview cards with page context.
- Add connection preflight to `/health`.
- Add copy/share actions for answers and sources.
- Add better empty states for offline backend and missing model.

## Example Questions

- واش المشغل يقدر يطردني بلا سبب؟
- شنو ندير إلا ما خلصنيش؟
- واش الحامل عندها حماية من الطرد؟
- واش الساعات الإضافية خاصها تخلص؟
- أنا وقع ليا حادث داخل الخدمة، شنو الحقوق ديالي؟
