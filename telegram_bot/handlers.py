"""
Telegram Bot Handlers
Two-phase flow: 
  Phase 1: Upload resume + JD → instant score + suggestions
  Phase 2: Select version → generate on-demand → download

Uses HTML parse_mode throughout (much less strict than MarkdownV2).
"""
import os
import logging
import httpx
from telegram import Update, InputFile
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import settings
from telegram_bot.keyboards import (
    get_version_selection_keyboard,
    get_format_keyboard,
    get_restart_keyboard,
    get_regenerate_keyboard,
)

logger = logging.getLogger(__name__)

# ── User State Management ────────────────────────────────────────────────────
user_states: dict[int, dict] = {}


def get_user_state(user_id: int) -> dict:
    if user_id not in user_states:
        user_states[user_id] = {"state": "IDLE"}
    return user_states[user_id]


def reset_user_state(user_id: int):
    user_states[user_id] = {"state": "IDLE"}


# ── Command Handlers ─────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reset_user_state(user_id)

    welcome_text = (
        "🤖 <b>AI Resume Analyzer Bot</b>\n\n"
        "I help you optimize your resume for any job!\n\n"
        "<b>How it works:</b>\n"
        "1️⃣ Send your resume (PDF/DOCX)\n"
        "2️⃣ Paste the job description\n"
        "3️⃣ Get instant ATS score + suggestions\n"
        "4️⃣ Generate optimized versions\n"
        "5️⃣ Download your new resume\n\n"
        "📎 <b>Send your resume file to start!</b>"
    )
    await update.message.reply_text(welcome_text, parse_mode="HTML")
    get_user_state(user_id)["state"] = "AWAITING_RESUME"


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 <b>Help</b>\n\n"
        "/start - Start over\n"
        "/help - This help\n"
        "/cancel - Cancel\n\n"
        "<b>Versions:</b>\n"
        "📄 ATS Optimized\n"
        "✨ Modern Professional\n"
        "💻 Developer Focused"
    )
    await update.message.reply_text(help_text, parse_mode="HTML")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_user_state(update.effective_user.id)
    await update.message.reply_text("❌ Cancelled. Send /start to begin again.")


# ── File Upload Handler ─────────────────────────────────────────────────────

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_user_state(user_id)
    document = update.message.document
    filename = document.file_name.lower()

    if not (filename.endswith(".pdf") or filename.endswith(".docx") or filename.endswith(".doc")):
        await update.message.reply_text("❌ Please upload a PDF or DOCX file.")
        return

    await update.message.reply_text("📥 Downloading your resume...")

    try:
        file = await context.bot.get_file(document.file_id)
        upload_dir = os.path.join(settings.UPLOAD_DIR, f"tg_{user_id}")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, document.file_name)
        await file.download_to_drive(file_path)

        state["resume_path"] = file_path
        state["resume_filename"] = document.file_name
        state["state"] = "AWAITING_JD"

        await update.message.reply_text(
            f"✅ Resume received: <b>{document.file_name}</b>\n\n"
            "📝 Now paste the <b>job description</b> text.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.exception("Error downloading file")
        await update.message.reply_text(f"❌ Failed to download. Please try again with /start.")
        state["state"] = "AWAITING_RESUME"


# ── Text Handler (JD Input) ─────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_user_state(user_id)

    if state["state"] == "IDLE":
        await update.message.reply_text("👋 Send /start to begin!")
        return

    if state["state"] == "AWAITING_RESUME":
        await update.message.reply_text("📎 Please upload your resume file first (PDF or DOCX).")
        return

    if state["state"] != "AWAITING_JD":
        await update.message.reply_text("⏳ Please wait or send /cancel.")
        return

    jd_text = update.message.text.strip()
    if len(jd_text) < 20:
        await update.message.reply_text("⚠️ JD seems too short. Please paste a more complete description.")
        return

    state["state"] = "PROCESSING"
    state["jd_text"] = jd_text

    # PHASE 1: Quick scoring
    processing_msg = await update.message.reply_text(
        "🔄 <b>Analyzing your resume...</b>\n\n"
        "⏱ This takes about 15-20 seconds:\n"
        "• Parsing resume\n"
        "• Analyzing job description\n"
        "• Calculating ATS score",
        parse_mode="HTML"
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(state["resume_path"], "rb") as f:
                files = {"resume": (state["resume_filename"], f, "application/octet-stream")}
                data = {"jd_text": jd_text}
                response = await client.post(
                    f"{settings.API_BASE_URL}/api/score",
                    files=files,
                    data=data,
                )

        if response.status_code != 200:
            error_detail = response.json().get("detail", "Unknown error")
            await processing_msg.edit_text(f"❌ Error: {error_detail}")
            reset_user_state(user_id)
            return

        result = response.json()
        session_id = result["session_id"]
        state["session_id"] = session_id
        state["state"] = "SELECTING_VERSION"

        # Build score response
        score = result["original_score"]["final_score"]
        kw_score = result["original_score"]["keyword_score"]
        sem_score = result["original_score"]["semantic_score"]
        ats_score = result["original_ats_score"]

        score_emoji = "🟢" if score >= 80 else ("🟡" if score >= 60 else "🔴")
        ats_emoji = "🟢" if ats_score >= 80 else ("🟡" if ats_score >= 60 else "🔴")

        response_text = (
            f"📊 <b>Resume Analysis Complete!</b>\n\n"
            f"<b>Overall Score:</b> {score_emoji} {score}/100\n"
            f"├ Keyword Match: {kw_score}%\n"
            f"└ Semantic Match: {sem_score}%\n\n"
            f"<b>ATS Score:</b> {ats_emoji} {ats_score}/100\n"
            f"├ Keywords: {result['ats_breakdown']['keyword_match']:.0f}%\n"
            f"├ Formatting: {result['ats_breakdown']['formatting']:.0f}%\n"
            f"└ Sections: {result['ats_breakdown']['section_completeness']:.0f}%\n"
        )

        # Missing keywords
        missing = result.get("missing_keywords", [])
        if missing:
            top_missing = missing[:10]
            response_text += "\n⚠️ <b>Missing Keywords:</b>\n"
            for kw in top_missing:
                response_text += f"  • {kw}\n"
            if len(missing) > 10:
                response_text += f"  <i>...and {len(missing) - 10} more</i>\n"

        # Skills found
        skills = result.get("parsed_skills", [])
        if skills:
            response_text += f"\n✅ <b>Your Skills:</b> {', '.join(skills[:15])}"
            if len(skills) > 15:
                response_text += f" (+{len(skills) - 15} more)"
            response_text += "\n"

        response_text += "\n🚀 <b>Generate optimized versions:</b>"

        await processing_msg.edit_text(
            response_text,
            parse_mode="HTML",
            reply_markup=get_version_selection_keyboard(session_id),
        )

    except httpx.TimeoutException:
        await processing_msg.edit_text("⏰ Timed out. Please try again with /start.")
        reset_user_state(user_id)
    except Exception as e:
        logger.exception("Error during scoring")
        await processing_msg.edit_text(f"❌ Error: {str(e)}\n\nTry again with /start.")
        reset_user_state(user_id)


# ── Callback Query Handler ──────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    state = get_user_state(user_id)
    data = query.data

    # ── Restart ──
    if data == "restart":
        reset_user_state(user_id)
        get_user_state(user_id)["state"] = "AWAITING_RESUME"
        await query.edit_message_text(
            "🔄 <b>Starting fresh!</b>\n\n📎 Send your resume file.",
            parse_mode="HTML"
        )
        return

    # ── Version Selection → Generate on-demand ──
    if data.startswith("select:"):
        parts = data.split(":")
        session_id = parts[1]
        version_type = parts[2]

        version_labels = {
            "ats_optimized": "📄 ATS Optimized",
            "modern_professional": "✨ Modern Professional",
            "developer_focused": "💻 Developer / Technical",
        }
        label = version_labels.get(version_type, version_type)

        await query.edit_message_text(
            f"⏳ Generating <b>{label}</b> version...\n\nThis may take 20-30 seconds.",
            parse_mode="HTML"
        )

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{settings.API_BASE_URL}/api/rewrite/{session_id}/{version_type}"
                )

            if response.status_code != 200:
                error_detail = response.json().get("detail", "Unknown error")
                await query.edit_message_text(f"❌ Error: {error_detail}")
                return

            result = response.json()
            ats_score = result["ats_score"]
            preview = result.get("preview_text", "")

            ats_emoji = "🟢" if ats_score >= 85 else ("🟡" if ats_score >= 70 else "🔴")

            msg = f"✅ <b>{label}</b>\n\n{ats_emoji} ATS Score: {ats_score}/100"
            if preview:
                msg += f"\n\n<i>{preview[:150]}</i>"
            msg += "\n\nChoose download format:"

            await query.edit_message_text(
                msg,
                parse_mode="HTML",
                reply_markup=get_format_keyboard(session_id, version_type),
            )

        except httpx.TimeoutException:
            await query.edit_message_text("⏰ Generation timed out. Please try again.")
        except Exception as e:
            logger.exception("Error generating version")
            await query.edit_message_text(f"❌ Error: {str(e)}")
        return

    # ── Back to Version List ──
    if data.startswith("back:"):
        session_id = data.split(":")[1]
        await query.edit_message_text(
            "👇 <b>Select a version to generate:</b>",
            parse_mode="HTML",
            reply_markup=get_version_selection_keyboard(session_id),
        )
        return

    # ── Format Selection → Generate file & Send ──
    if data.startswith("format:"):
        parts = data.split(":")
        session_id = parts[1]
        version_type = parts[2]
        file_format = parts[3]

        await query.edit_message_text(f"📝 Creating {file_format.upper()} file...")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{settings.API_BASE_URL}/api/generate/{session_id}/{version_type}",
                    params={"format": file_format},
                )

            if response.status_code != 200:
                error_detail = response.json().get("detail", "Unknown error")
                await query.edit_message_text(f"❌ Error: {error_detail}")
                return

            result = response.json()
            download_url = result["download_url"]

            async with httpx.AsyncClient(timeout=30.0) as client:
                file_response = await client.get(download_url)

            if file_response.status_code != 200:
                await query.edit_message_text("❌ Failed to download generated file.")
                return

            from io import BytesIO
            file_obj = BytesIO(file_response.content)
            file_obj.name = result["filename"]

            version_labels = {
                "ats_optimized": "ATS Optimized",
                "modern_professional": "Modern Professional",
                "developer_focused": "Developer / Technical",
            }
            label = version_labels.get(version_type, version_type)

            await query.edit_message_text(
                f"✅ Your <b>{label}</b> resume is ready!",
                parse_mode="HTML"
            )

            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=InputFile(file_obj, filename=result["filename"]),
                caption=f"📎 {label} Resume ({file_format.upper()})",
                reply_markup=get_regenerate_keyboard(session_id),
            )

        except Exception as e:
            logger.exception("Error generating file")
            await query.edit_message_text(f"❌ Error: {str(e)}\n\nTry /start.")


# ── Register All Handlers ───────────────────────────────────────────────────

def register_handlers(application):
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(CallbackQueryHandler(handle_callback))
