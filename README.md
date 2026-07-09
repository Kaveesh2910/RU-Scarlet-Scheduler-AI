# RU Scarlet Scheduler AI 🎓

**A Discord bot that helps Rutgers University New Brunswick students plan their upcoming semester using AI.**

Built by **Kaveesh Kapoor**

---

## What It Does

RU Scarlet Scheduler AI is a Discord bot powered by the **Anthropic Claude API** and **live Rutgers University course data**. Students input their major, core elective requirement, credits wanted, credits completed, and course history. The AI then recommends a personalized course schedule for their upcoming semester — pulling only from real, currently available Rutgers New Brunswick courses.

---

## How To Use It

All you need is a Discord account and a Discord server. No coding knowledge required.

1. Add the bot to your Discord server using the invite link *(coming soon)*
2. Type `/plansemester` or `!planSemester` in any channel
3. Select your current semester from the dropdown (Freshman Fall, Sophomore Spring, Senior Fall, etc.)
4. A form will appear — fill in your:
   - Major(s) and/or Minor(s) (using Rutgers subject codes, e.g. 198 for Computer Science)
   - Core elective requirement needed (e.g. CCD, HST, NS — leave blank if none)
   - Credits wanted this semester
   - Total credits completed so far
   - All courses completed so far (using Rutgers course codes, e.g. 01:198:111)
5. Hit submit and wait a moment — the bot will respond with a recommended schedule

---

## Example Output

![Example Output](screenshots/example_output.png)

---

## Tech Stack

- **Python** — core programming language
- **discord.py** — Discord bot framework
- **Anthropic Claude API** — AI model powering course recommendations
- **Rutgers SIS API** — live course data pulled directly from Rutgers University
- **python-dotenv** — secure environment variable management

---

## How It Was Built

This project goes beyond just building a bot. It follows a proper **AI engineering workflow**:

### 1. Prompt Engineering
The AI's behavior is controlled through a carefully designed system prompt using XML tags, strict rules, and output format specifications to ensure responses are accurate, concise, and useful for students.

### 2. Live Data Integration
Instead of relying on the AI's training data (which could be outdated or inaccurate), the bot fetches **live course data** from the Rutgers SIS API on every request. This ensures the AI only recommends courses that actually exist and are relevant to the student's major.

### 3. Evaluation Pipeline
A full **eval pipeline** was built to measure and improve the AI's performance:
- **Stage 1** — Generated 10 realistic student test cases using Claude
- **Stage 2** — Ran each test case through the bot and collected outputs
- **Stage 3** — Used a separate Claude instance to grade each output on a 0-10 rubric
- **Stage 4** — Results displayed in a custom HTML dashboard for analysis

### 4. Iterative Improvement
Based on eval results, the system prompt was refined multiple times and **multi-shot examples** were added to guide the AI toward ideal responses. The final average score across 10 test cases was **8.4/10**.

---

## Grading Rubric

Responses were evaluated on four criteria:

| Category | Points | Description |
|---|---|---|
| Accuracy | 0-3 | Are course codes valid? Are prerequisites respected? |
| Constraint Adherence | 0-3 | Does it meet the credit goal? One schedule only? Core satisfied? |
| Completeness & Conciseness | 0-2 | No cutoff? No relisting? Reasoning in summary only? |
| Professionalism & Tone | 0-2 | Clean, readable, and actionable for a student? |

---

## Planned Features

If this project gains traction among Rutgers students, the following features are planned:

- **Premium tier** — enhanced AI model with persistent memory and personalized recommendations over time
- **Export your input** — automatically save your course history as a file so you can reuse it next semester without retyping everything
- **Full degree planner** — `!planDegree` command that maps out all 8 semesters from start to graduation

---

## Project Status

✅ Completed — actively seeking student feedback from Rutgers New Brunswick students to improve future versions.

---

## Contact

**Kaveesh Kapoor**
GitHub: [Kaveesh2910](https://github.com/Kaveesh2910)
Email: [kaveeshdkap@gmail.com]

*For inquiries about this project, feel free to reach out via GitHub.*
