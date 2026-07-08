# Imports
import discord
from discord import app_commands
from discord.ext import commands
import os
import aiohttp
import json
from dotenv import load_dotenv
from anthropic import Anthropic

# Client
load_dotenv()

anthropic_client = Anthropic()
model = "claude-sonnet-4-6"

# Intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

conversation_histories = {}

# ─── API FETCHING LOGIC ───────────────────────────────────

async def fetch_and_filter_rutgers_courses(subjects_string: str, core_string: str, history_string: str):
    url = "https://classes.rutgers.edu/soc/api/courses.json?year=2026&term=9&campus=NB&level=U"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return "Error: Could not fetch Rutgers API data."
                all_courses = await resp.json()
    except Exception as e:
        return f"Error fetching API: {e}"

    # Map user-friendly inputs to official API codes
    code_map = {
        "CC-O": "CCO", "CC-D": "CCD", "NS": "NS", "SCL": "SCL", 
        "HST": "HST", "AHo": "AHo", "AHp": "AHp", "AHq": "AHq", 
        "AHr": "AHr", "WC": "WC", "WCr": "WCr", "WCd": "WCd", 
        "QQ": "QQ", "QR": "QR"
    }

    target_subjects = [s.strip() for s in subjects_string.split(",")] if subjects_string else []
    
    # Normalize the core input using the map, default to uppercase input if not mapped
    user_input = core_string.strip()
    target_core = code_map.get(user_input, user_input.upper()) 
    
    history_check = history_string if history_string else ""

    filtered_courses = []
    core_elective_count = 0

    for course in all_courses:
        course_str = course.get("courseString", "")
        
        if course_str and course_str in history_check:
            continue
            
        subj = str(course.get("subject", ""))
        is_major_minor = subj in target_subjects
        
        # Check core codes against the normalized target_core
        has_core = False
        if target_core:
            core_codes = [c.get("code") for c in course.get("coreCodes", [])]
            if target_core in core_codes:
                has_core = True
                
        if is_major_minor:
            filtered_courses.append({
                "code": course_str,
                "title": course.get("title"),
                "credits": course.get("credits"),
                "prereqs": course.get("preReqNotes", ""),
                "coreCodes": [c.get("code") for c in course.get("coreCodes", [])]
            })
        elif has_core and core_elective_count < 10:
            filtered_courses.append({
                "code": course_str,
                "title": course.get("title"),
                "credits": course.get("credits"),
                "prereqs": course.get("preReqNotes", ""),
                "coreCodes": [c.get("code") for c in course.get("coreCodes", [])]
            })
            core_elective_count += 1

    return json.dumps(filtered_courses)


# ─── AI SETUP ─────────────────────────────────────────────

def add_user_message(messages, text):
    messages.append({"role": "user", "content": text})

def add_assistant_message(messages, text):
    messages.append({"role": "assistant", "content": text})

def chat(messages):
    system = """
    You are RU Scarlet Scheduler AI, a course scheduling assistant for Rutgers University New Brunswick students.

    <examples>
        <example>
            <user_input>
                Plan my semester: Freshman Spring. Major: 960, 198. Core: NS. Credits: 14. Completed: 01:198:111, 01:960:151.
            </user_input>
            <ideal_response>
                - 01:198:112 DATA STRUCTURES | 4 Credits | Prerequisites met: Yes
                - 01:198:205 INTR DISCRET STRCT I | 4 Credits | Prerequisites met: Yes
                - 01:119:103 PRINCIPLES OF BIOL | 3 Credits | Prerequisites met: Yes (NS)
                - 01:198:104 GREAT IDEAS IN CS | 1 Credit | Prerequisites met: Yes

                This schedule covers core CS and Statistics major requirements while fulfilling the NS Core Elective, landing at 12 credits as no additional eligible courses could fill the remaining gap without unmet prerequisites. The workload is appropriate for a Freshman Spring student, though the 2-credit shortfall from the 14-credit goal is worth discussing with your academic advisor.
            </ideal_response>
        </example>
        <example>
            <user_input>
                Plan my semester: Senior Fall. Major: 260, 920, 640. Core: CCO. Credits: 11. Completed: 01:260:201, 01:260:251, 01:920:201, 01:920:301, 01:640:150, 01:640:251, 01:198:111, 01:198:251.
            </user_input>
            <ideal_response>
                - 01:920:311 SOC RESEARCH | 4 Credits | Prerequisites met: Yes
                - 01:920:316 SOC THEORY | 4 Credits | Prerequisites met: Partial (College Writing assumed met as a Senior)
                - 01:920:225 INTRO IMMIGRATION | 3 Credits | Prerequisites met: Yes (CCO)

                This schedule meets the 11-credit goal exactly, covering core Sociology requirements and satisfying the CCO Core Elective. The workload is very manageable for a Senior Fall semester.
            </ideal_response>
        </example>
        <example>
            <user_input>
                Plan my semester: Junior Fall. Major: 440, 960, 198. Core: HST. Credits: 16. Completed: 01:440:101, 01:440:201, 01:960:151, 01:960:251, 01:198:111, 01:198:112.
            </user_input>
            <ideal_response>
                - 01:198:205 INTR DISCRET STRCT I | 4 Credits | Prerequisites met: Yes
                - 01:198:211 COMPUTER ARCHITECTUR | 4 Credits | Prerequisites met: Yes
                - 01:198:213 SOFTWARE METHODOLOGY | 4 Credits | Prerequisites met: Yes
                - 01:016:222 MODERN AFRICA | 3 Credits | Prerequisites met: Yes (HST)

                This schedule covers three core CS requirements and satisfies the HST Core Elective, aligning well with junior-level progression. It lands at 15 credits as no eligible course could fill the remaining 1-credit gap without exceeding the target.
            </ideal_response>
        </example>
    </examples>

    <rules>
    - Only recommend real Rutgers courses found in the LIVE API DATA provided.
    - Never recommend a course whose prerequisites the student has not yet met. Skip it silently.
    - Prioritize courses in this exact order: Major/Minor → Requested Core Elective → Free Electives.
    - Only suggest a Core Elective if explicitly requested by the student.
    - Never suggest free electives unless Major/Minor and Core courses cannot fill the requested credits.
    - DO NOT relist or mention courses the student has already taken. Ever.
    - DO NOT offer alternative schedules or multiple options. Provide exactly one recommended schedule.
    - DO NOT show your reasoning process, thinking, scratchpad, or eligibility analysis. Output the final schedule only.
    - Try to meet the exact credit count requested. If not possible, go under rather than over.
    - If you cannot reach the requested credit count, mention the shortfall in the summary only.
    - Your summary must be exactly 2-3 sentences. If it exceeds 3 sentences, delete sentences until it does.
    - Never offer alternative schedules or swaps in the summary.
    </rules>

    <output_format>
    For each recommended course:
    - Course code and name | Credits | Prerequisites met: Yes / No / Partial

    End with a summary of exactly 2-3 sentences that covers:
    1. Whether the schedule meets the student's major requirements and credit goal
    2. Whether the overall workload is reasonable for their level
    3. A brief credit warning only if you fell short, or if total is below 12 or above 18
    Do not explain individual course choices in the summary.

    - Use **bold** for course codes and the summary sentence only.
    </output_format>
    """

    # SLIDING WINDOW: Only send the most recent user prompt to save massive token costs
    truncated_messages = [messages[-1]]

    message = anthropic_client.messages.create(
        model=model,
        max_tokens=1000, 
        messages=truncated_messages,
        system=system,
        temperature=0.1, 
    )
    return message.content[0].text

async def send_long_discord_message(interaction: discord.Interaction, header: str, content: str):
    full_message = f"{header}\n\n{content}"
    max_length = 2000

    if len(full_message) <= max_length:
        await interaction.followup.send(full_message)
        return

    for i in range(0, len(full_message), max_length):
        chunk = full_message[i:i + max_length]
        await interaction.followup.send(chunk)


# ─── MODALS ───────────────────────────────────────────────

class PreCollegeModal(discord.ui.Modal, title="Pre-College Credit Equivalents"):
    subjects = discord.ui.TextInput(label="Major/Minor Codes (comma separated)", placeholder="e.g. 198, 640", required=True)
    core_elective = discord.ui.TextInput(label="Core Requirement Needed (if any)", placeholder="e.g. AH, HST, SCL (leave blank if none)", required=False)
    credits_wanted = discord.ui.TextInput(label="Credits Wanted This Semester", placeholder="e.g. 15", required=True)
    academic_history = discord.ui.TextInput(label="Rutgers Credit Equivalents (AP/Dual)", placeholder="e.g. 01:640:151, 01:198:111 (codes only)", style=discord.TextStyle.paragraph, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        user_id = str(interaction.user.id)

        api_data = await fetch_and_filter_rutgers_courses(self.subjects.value, self.core_elective.value, self.academic_history.value)

        user_prompt = f"""
        LIVE API COURSE DATA: {api_data}
        
        Please plan my Freshman Fall semester with the following information:
        - Target Semester: Freshman Fall
        - Major(s)/Minor(s): {self.subjects.value}
        - Desired Core Elective Type: {self.core_elective.value or "None"}
        - Credits Wanted This Semester: {self.credits_wanted.value}
        - Total Credits Completed: 0
        - Rutgers Credit Equivalents from AP/DE: {self.academic_history.value or "None"}
        """

        if user_id not in conversation_histories:
            conversation_histories[user_id] = []

        user_messages = conversation_histories[user_id]
        add_user_message(user_messages, user_prompt)
        answer = chat(user_messages)
        add_assistant_message(user_messages, answer)

        await send_long_discord_message(interaction, f"📚 **Semester Plan for {interaction.user.display_name}:**", answer)


class CollegeSemesterModal(discord.ui.Modal):
    def __init__(self, semester_label: str):
        super().__init__(title=f"Plan My Semester — {semester_label}")
        self.semester_label = semester_label

    subjects = discord.ui.TextInput(label="Major/Minor Codes (comma separated)", placeholder="e.g. 198, 640", required=True)
    core_elective = discord.ui.TextInput(label="Core Requirement Needed (if any)", placeholder="e.g. AH, HST, SCL, WCr (leave blank if none)", required=False)
    credits_wanted = discord.ui.TextInput(label="Credits Wanted This Semester", placeholder="e.g. 15", required=True)
    credits_completed = discord.ui.TextInput(label="Total Credits Completed So Far", placeholder="e.g. 32", required=True)
    academic_history = discord.ui.TextInput(label="All Courses Completed (AP + Rutgers)", placeholder="e.g. 01:198:111, 01:640:151 (codes only)", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        user_id = str(interaction.user.id)

        api_data = await fetch_and_filter_rutgers_courses(self.subjects.value, self.core_elective.value, self.academic_history.value)

        user_prompt = f"""
        LIVE API COURSE DATA: {api_data}
        
        Please plan my semester with the following information:
        - Target Semester: {self.semester_label}
        - Major(s)/Minor(s): {self.subjects.value}
        - Desired Core Elective Type: {self.core_elective.value or "None"}
        - Credits Wanted This Semester: {self.credits_wanted.value}
        - Total Credits Completed So Far: {self.credits_completed.value}
        - All Completed Courses: {self.academic_history.value}
        """

        if user_id not in conversation_histories:
            conversation_histories[user_id] = []

        user_messages = conversation_histories[user_id]
        add_user_message(user_messages, user_prompt)
        answer = chat(user_messages)
        add_assistant_message(user_messages, answer)

        await send_long_discord_message(interaction, f"📚 **Semester Plan for {interaction.user.display_name}:**", answer)


class SummerWinterModal(discord.ui.Modal, title="Plan My Summer / Winter Session"):
    session = discord.ui.TextInput(label="Session Type", placeholder="Summer or Winter", required=True)
    subjects = discord.ui.TextInput(label="Major/Minor Codes (comma separated)", placeholder="e.g. 198, 640", required=True)
    core_elective = discord.ui.TextInput(label="Core Requirement Needed (if any)", placeholder="e.g. AH, SCL (leave blank if none)", required=False)
    credits_wanted = discord.ui.TextInput(label="Credits Wanted This Session", placeholder="e.g. 6", required=True)
    academic_history = discord.ui.TextInput(label="All Courses Completed (AP + Rutgers)", placeholder="e.g. 01:198:111, 01:640:151", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        user_id = str(interaction.user.id)

        api_data = await fetch_and_filter_rutgers_courses(self.subjects.value, self.core_elective.value, self.academic_history.value)

        user_prompt = f"""
        LIVE API COURSE DATA: {api_data}
        
        Please plan my intersession with the following information:
        - Session Type: {self.session.value}
        - Major(s)/Minor(s): {self.subjects.value}
        - Desired Core Elective Type: {self.core_elective.value or "None"}
        - Credits Wanted This Session: {self.credits_wanted.value}
        - All Completed Courses: {self.academic_history.value}
        """

        if user_id not in conversation_histories:
            conversation_histories[user_id] = []

        user_messages = conversation_histories[user_id]
        add_user_message(user_messages, user_prompt)
        answer = chat(user_messages)
        add_assistant_message(user_messages, answer)

        await send_long_discord_message(interaction, f"📚 **{self.session.value} Session Plan for {interaction.user.display_name}:**", answer)


# ─── SEMESTER SELECTOR ────────────────────────────────────

SEMESTER_CHOICES = [
    discord.SelectOption(label="Freshman Fall",    value="freshman_fall",    description="First semester, no prior Rutgers courses"),
    discord.SelectOption(label="Freshman Spring",  value="freshman_spring",  description="Second semester"),
    discord.SelectOption(label="Sophomore Fall",   value="sophomore_fall",   description="Third semester"),
    discord.SelectOption(label="Sophomore Spring", value="sophomore_spring", description="Fourth semester"),
    discord.SelectOption(label="Junior Fall",      value="junior_fall",      description="Fifth semester"),
    discord.SelectOption(label="Junior Spring",    value="junior_spring",    description="Sixth semester"),
    discord.SelectOption(label="Senior Fall",      value="senior_fall",      description="Seventh semester"),
    discord.SelectOption(label="Senior Spring",    value="senior_spring",    description="Eighth semester"),
    discord.SelectOption(label="Summer Session",   value="summer",           description="Summer intersession"),
    discord.SelectOption(label="Winter Session",   value="winter",           description="Winter intersession"),
]

class SemesterSelectView(discord.ui.View):
    @discord.ui.select(
        placeholder="Select your target semester...",
        options=SEMESTER_CHOICES
    )
    async def select_semester(self, interaction: discord.Interaction, select: discord.ui.Select):
        value = select.values[0]

        if value == "freshman_fall":
            await interaction.response.send_modal(PreCollegeModal())
        elif value == "summer":
            await interaction.response.send_modal(SummerWinterModal())
        elif value == "winter":
            await interaction.response.send_modal(SummerWinterModal())
        else:
            label_map = {
                "freshman_spring":  "Freshman Spring",
                "sophomore_fall":   "Sophomore Fall",
                "sophomore_spring": "Sophomore Spring",
                "junior_fall":      "Junior Fall",
                "junior_spring":    "Junior Spring",
                "senior_fall":      "Senior Fall",
                "senior_spring":    "Senior Spring",
            }
            await interaction.response.send_modal(CollegeSemesterModal(label_map[value]))


# ─── DISCORD COMMANDS ─────────────────────────────────────

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@bot.tree.command(name="plansemester", description="Get a personalized Rutgers semester course plan!")
async def plan_semester_slash(interaction: discord.Interaction):
    await interaction.response.send_message(
        "📅 **RU Scarlet Scheduler**\nSelect your target semester to get started:",
        view=SemesterSelectView(),
        ephemeral=True
    )

@bot.command(name="planSemester")
async def plan_semester_prefix(ctx):
    await ctx.send(
        "📅 **RU Scarlet Scheduler**\nSelect your target semester to get started:",
        view=SemesterSelectView()
    )

bot.run(os.getenv("DISCORD_TOKEN"))