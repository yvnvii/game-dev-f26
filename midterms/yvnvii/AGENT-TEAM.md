# Agent team log


## Implementation agent
- Configuration: `CLAUDE.md`
- Allowed to see / do:
- Recommended:
- I decided:
- Evidence (session links, commits):


## 1. Claude (claude.ai chat) and Claude Code: design and build assistant, implementation agent
- **Could see / do:** 
Claude (chat): the brief and rubric I pasted, outputs I pasted from my terminal. It could not see or change my repository; it gave me zip files and patches that I applied and committed myself.
Claude Code: all files under my repository.
- **Recommended:** 
Claude (chat): it recommended the depth-3 baseline and comparing vs greedy,found gaps in rules and suggested adding rules on draw at turn 100 and setting the limit on how many times you can rotate in a game. It suggested the prompt v2 tuned only on T1–T3.
Claude Code: raised the output limit, recorded finish reasons, added a test, per-player clock.
- **What I decided:** I made the game design. I decided to do rubik's cube style twists on 3D connect four, then decided to allow unlimited twists. I decided to make the UI on web version drag-to-twist after the playtest. 

- **Evidence:** commits marked "Co-Authored-By: Claude"; CLAUDE.md; Claude Code sessions are recorded in yvnvii/agent-sessions/; chat link: https://claude.ai/share/d49d6a9d-8371-4fb4-be5a-199b5682709e

## Reusable skill: `add-rule-with-test`
- Configuration: `.claude/skills/add-rule-with-test/SKILL.md`
- Invoked in sessions: E1-clock-rule-skill and review-fixes-skill.
- What it produced:it restated the rule, then wrote 6 tests first and confirmed all 6 failed for the expected reasons before changing.
- I decided: I directed rule changes through the skill instead of asking for quick edits so that every rule change comes with a test. When it asked about late moves and call timeouts, I decided to discard late moves and to cap each call at the time left so the 15-minute limit is enforced during the call and not after.


## 4. Independent reviewer: rules-reviewer subagent (.claude/agents/rules-reviewer.md)
- **Could see / do:** read-only (Read, Grep, Glob); it could not run tests; not told to approve; did not write the code.
- **Recommended:** 0 critical/high, 8 medium, about 10 low findings (review.md).
- **What I decided:** I fixed findings 2, 4, 5 and 7 in review.md because they were small and obviously correct. For 3, I made running out of time a loss for that player, and switched to a clock per player, because one shared clock couldn’t say whose fault a timeout was. I left the low findings untouched: each call already has a time limit.


