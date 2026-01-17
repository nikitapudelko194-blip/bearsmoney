"""NFT integration handlers."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, Bear
from app.services.bears import BEAR_CLASSES

logger = logging.getLogger(__name__)
router = Router()

# NFT conversion costs
NFT_CONVERSION_COSTS = {
    "rare": 5000,
    "epic": 10000,
    "legendary": 20000
}


@router.callback_query(F.data == "nft_marketplace")
async def nft_marketplace(query: CallbackQuery):
    """Show NFT marketplace."""
    try:
        text = (
            "🖼️ **NFT Marketplace**\n\n"
            "🚧 **В разработке!**\n\n"
            "Скоро здесь появится:\n"
            "• Конвертация медведей в NFT (TON blockchain)\n"
            "• P2P торговля NFT медведями\n"
            "• Royalty 5% с перепродаж\n"
            "• Limited edition коллекции\n"
            "• Аукционы редких медведей\n\n"
            "💡 **Как это работает:**\n"
            "1. Выберите редкого медведя\n"
            "2. Оплатите конвертацию в NFT\n"
            "3. Получите уникальный NFT на TON\n"
            "4. Продавайте или обменивайте\n\n"
            "📈 **Стоимость конвертации:**\n"
            "🟦 Rare → NFT: 5,000 Coins\n"
            "🟪 Epic → NFT: 10,000 Coins\n"
            "🟧 Legendary → NFT: 20,000 Coins\n"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🐻 Мои медведи", callback_data="bears")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in nft_marketplace: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
