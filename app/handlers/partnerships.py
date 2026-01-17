"""Partnership and cross-promotion handlers."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
router = Router()

# Partner projects
PARTNERS = [
    {
        "name": "CryptoGame XYZ",
        "description": "Играй и зарабатывай криптовалюту!",
        "reward": "500 Coins",
        "url": "https://t.me/example_bot",
        "emoji": "🎮"
    },
    {
        "name": "TON Airdrop",
        "description": "Получи бесплатные TON токены!",
        "reward": "0.1 TON",
        "url": "https://t.me/example_airdrop",
        "emoji": "💎"
    },
]


@router.callback_query(F.data == "partnerships")
async def partnerships_menu(query: CallbackQuery):
    """Show partnerships menu."""
    try:
        text = (
            f"🤝 **Партнёры**\n\n"
            f"Проверенные проекты с бонусами для наших игроков!\n\n"
            f"✨ Выбери проект:"
        )
        
        keyboard = []
        for idx, partner in enumerate(PARTNERS):
            keyboard.append([InlineKeyboardButton(
                text=f"{partner['emoji']} {partner['name']} (+{partner['reward']})",
                callback_data=f"partner_{idx}"
            )])
        
        keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        try:
            await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"Error in partnerships_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("partner_"))
async def partner_details(query: CallbackQuery):
    """Show partner details."""
    try:
        partner_idx = int(query.data.split("_")[-1])
        partner = PARTNERS[partner_idx]
        
        text = (
            f"{partner['emoji']} **{partner['name']}**\n\n"
            f"{partner['description']}\n\n"
            f"🎁 **Бонус:** {partner['reward']}\n\n"
            f"👉 Перейди по ссылке, чтобы получить бонус!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Открыть проект", url=partner['url'])],
            [InlineKeyboardButton(text="⬅️ К партнёрам", callback_data="partnerships")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"Error in partner_details: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
