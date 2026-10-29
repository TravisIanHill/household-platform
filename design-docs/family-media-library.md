# Family Media Library: Design Direction

Status: **Design**, October 2026. Not yet built. This document defines the record, conventions and safeguards before any code is written.

## 1. The need

Our family has years of our own video: dance performances and rehearsals, sports games, workouts, school and family events. It lives in scattered folders, with names that made sense to whoever saved it that day. Finding "the regional competition, the second angle, from 2024" means scrubbing through files.

The goal is the same as every Jupiter app: **easy to save and easy to retrieve.** A family member should be able to find a specific performance or game in seconds, see who's in it, and know which copy is the good one.

## 2. Scope

- **In scope:** video and photos the family recorded or received of our own events.
- **Out of scope:** commercial movies and TV, and any download or acquisition tooling.
- Files stay where they are. The library is an information layer over them: it reads file details, stores the record, and links to the file. It never moves, renames or deletes originals on its own.

## 3. The record

| Group | Fields |
|---|---|
| Identity | Title, kind (performance, rehearsal, class, game, practice, workout, event), date |
| Event | Event or venue, season, opponent or competition (sports) |
| People | Performers or players (linked to household people), coach, choreographer or instructor; studio or team (text) |
| Content | Style or sport, routine or piece, music (text) |
| Workout | Program or series, focus, intensity, equipment |
| Relationships | Other angle of the same event, same routine at other dates, preferred version |
| Review | Status, reviewer, notes, shared or private |
| File (automatic) | Duration, resolution, codecs, frame rate, size, file date, checksum, path |

**Borrowed, not invented:** dance archives built on Dublin Core (Choreographer, Performer roles), linking only a few people roles rather than every credit, free-text style and genre, same-event multi-angle links, and a standard file-details field set. Field sizes are set when the schema is written.

## 4. Conventions

- **Dates are American month-day-year**, with dashes in file names (03-14-2026) and the same order on screen. Stored as real date values.
- Partial dates (month and year, or year only) are valid. A file's own date is a hint, never the truth.
- Safe characters only, one separator style, sensible name length.
- Renames are proposals a person approves; original names are always kept in the record.
- Example patterns: `Routine Name - Event or Class - 03-14-2026.ext`, `Team vs Opponent - 10-04-2025.ext`, `Program - Session Title.ext`.
- **People's names stay out of file names by default.** They live in the record, where access can be controlled.

## 5. Safeguards

- **Family video stays local.** Videos of family members, including children, are never sent to a hosted AI model. File details are read locally and need no model at all. See the [model data-handling policy](model-data-handling-policy.md).
- **Understand first, organize second.** The first pass only catalogs. Nothing is moved or renamed until a person reviews it.
- **Private by default.** Each record is shared or private, and assigning someone a review task never grants access to private material.
- **Originals are preserved.** Cleanup goes to a recoverable quarantine, never straight to deletion.

## 6. Open decisions

Sidecar files beside each video versus catalog-only storage; final field sizes; whether the family browse view lives in this app or the household portal; how multi-angle footage is grouped on screen.
