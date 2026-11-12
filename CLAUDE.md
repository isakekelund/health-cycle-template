# Health Cycle – klientversion

## Vad det här är
- Kundversionen av Isaks vanetracker. `index.html` här är GENERERAD av `build_from_main.py` från `~/Code/health-cycle/index.html`. Redigera inte `index.html` för hand.
- Klientspecifikt (lagras på enheten i stället för Isaks Firebase, generiska startvanor, inställningssida för poäng, välkomsttur m.m.) läggs på i `build_from_main.py`.
- Live: Netlify-sajten `health-cycle-client-habit-tracker` (site id i `.netlify/state.json`), kopplad till GitHub-repot `isakekelund/health-cycle-template`.
- Förhandsvisning på port 8421 via `~/Code/health-cycle/.claude/launch.json`.

## Regler
- Ändringar görs i `build_from_main.py` (klientdelar) eller i `~/Code/health-cycle` (gemensamma delar), sedan körs `python3 build_from_main.py`.
- Klientversionen får aldrig skicka data till Isaks Firebase eller någon annan server.
- Publicera alltid till den befintliga Netlify-sajten. Skapa aldrig en ny.
- Gränssnitt på svenska, kod och kommentarer på engelska.

## Hur du pratar med Isak
- Isak är inte utvecklare. Svara på enkel svenska och förklara tekniska ord första gången.
- Avsluta varje svar med en mening om vad han ska göra härnäst.
