"""
Telegram Bot Keyboards
Inline keyboard builders for version selection and navigation.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_version_selection_keyboard(session_id: str) -> InlineKeyboardMarkup:
    """
    Keyboard with 3 version selection buttons.
    Callback data format: select_version:{session_id}:{version_type}
    """
    buttons = [
        [InlineKeyboardButton(
            "📄 ATS Optimized Version",
            callback_data=f"select:{session_id}:ats_optimized"
        )],
        [InlineKeyboardButton(
            "✨ Modern Professional Version",
            callback_data=f"select:{session_id}:modern_professional"
        )],
        [InlineKeyboardButton(
            "💻 Developer / Technical Version",
            callback_data=f"select:{session_id}:developer_focused"
        )],
    ]
    return InlineKeyboardMarkup(buttons)


def get_format_keyboard(session_id: str, version_type: str) -> InlineKeyboardMarkup:
    """
    Keyboard to choose output format (PDF or DOCX).
    """
    buttons = [
        [
            InlineKeyboardButton(
                "📕 Download PDF",
                callback_data=f"format:{session_id}:{version_type}:pdf"
            ),
            InlineKeyboardButton(
                "📘 Download DOCX",
                callback_data=f"format:{session_id}:{version_type}:docx"
            ),
        ],
        [InlineKeyboardButton(
            "◀️ Back to Versions",
            callback_data=f"back:{session_id}"
        )],
    ]
    return InlineKeyboardMarkup(buttons)


def get_restart_keyboard() -> InlineKeyboardMarkup:
    """
    Simple restart button.
    """
    buttons = [
        [InlineKeyboardButton("🔄 Analyze Another Resume", callback_data="restart")],
    ]
    return InlineKeyboardMarkup(buttons)


def get_regenerate_keyboard(session_id: str) -> InlineKeyboardMarkup:
    """
    Options after receiving a file: regenerate or start fresh.
    """
    buttons = [
        [InlineKeyboardButton(
            "📋 Choose Another Version",
            callback_data=f"back:{session_id}"
        )],
        [InlineKeyboardButton("🔄 Start Fresh", callback_data="restart")],
    ]
    return InlineKeyboardMarkup(buttons)
