"""Start command handler."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User
from datetime import datetime
from app.keyboards.main_menu import get_main_menu
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
router = Router()

# Экономические константы
STARTING_BONUS = 3000  # Стартовый бонус
REFERRAL_BONUS_REFERRER = 1000  # Бонус рефереру
REFERRAL_BONUS_REFERRED = 500   # Бонус новому игроку


@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Start command handler with improved economy.
    """
    try:
        # Check for referral code
        referrer_id = None
        if len(message.text.split()) > 1:
            try:
                referrer_id = int(message.text.split()[1])
            except ValueError:
                pass
        
        async with get_session() as session:
            # Check if user exists
            query = select(User).where(User.telegram_id == message.from_user.id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                # Calculate starting coins
                starting_coins = STARTING_BONUS
                referral_bonus = 0
                
                # Check if referrer exists
                referrer = None
                if referrer_id:
                    referrer_query = select(User).where(User.telegram_id == referrer_id)
                    referrer_result = await session.execute(referrer_query)
                    referrer = referrer_result.scalar_one_or_none()
                    
                    if referrer:
                        # Give bonus to both
                        referral_bonus = REFERRAL_BONUS_REFERRED
                        starting_coins += referral_bonus
                        referrer.coins += REFERRAL_BONUS_REFERRER
                        logger.info(f"✅ Referral bonus: {referrer_id} +{REFERRAL_BONUS_REFERRER}, new user +{referral_bonus}")
                
                # Create new user
                user = User(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    coins=float(starting_coins),
                    ton_balance=0.0,
                    created_at=datetime.utcnow(),
                    referred_by=referrer_id if referrer else None,
                )
                session.add(user)
                await session.commit()
                
                # Notify referrer
                if referrer:
                    try:
                        from aiogram import Bot
                        bot = message.bot
                        await bot.send_message(
                            referrer.telegram_id,
                            f"🎉 **По вашей ссылке зарегистрировался новый игрок!**\n\n"
                            f"💰 Получено: {REFERRAL_BONUS_REFERRER} коинов",
                            parse_mode="markdown"
                        )
                    except Exception as e:
                        logger.warning(f"Could not notify referrer: {e}")
                
                welcome_text = (
                    f"🐻 **Лавы в БеарсМани!**\n\n"
                    f"🎉 Привет, {message.from_user.first_name}!\n\n"
                    f"🐻 **Что ты можешь делать:**\n"
                    f"• 🐻 Покупать медведей (приносят пассивный доход)\n"
                    f"• ⬆️ Улучшать их для большего дохода\n"
                    f"• 💰 Выводить заработанные коины\n"
                    f"• 👥 Приглашать друзей и получать бонусы\n\n"
                )
                
                if referral_bonus > 0:
                    welcome_text += (
                        f"🎁 **Стартовый капитал:**\n"
                        f"├ 🎁 Базовый бонус: {STARTING_BONUS} коинов\n"
                        f"├ 👥 Реферальный бонус: {referral_bonus} коинов\n"
                        f"└ 💰 **Итого: {starting_coins} коинов!**\n\n"
                    )
                else:
                    welcome_text += f"🎁 **Стартовый бонус: {starting_coins} коинов!**\n\n"
                
                welcome_text += (
                    f"💡 **Совет:**\n"
                    f"Начни с покупки 5 обычных медведей (600 коинов каждый).\n"
                    f"Они будут приносить тебе пассивный доход!\n\n"
                    f"👉 Нажми '🛍️ Магазин' чтобы начать!"
                )
                
                logger.info(f"🐻 New user: {message.from_user.id} | Start: {starting_coins} coins | Ref: {referrer_id or 'None'}")
            else:
                # User already exists
                welcome_text = (
                    f"🐻 **С возвращением!**\n\n"
                    f"💰 **Основное меню**\n\n"
                    f"👤 @{message.from_user.username or 'User'}\n"
                    f"🪙 Баланс: {user.coins:.0f} коинов\n"
                    f"💎 TON: {user.ton_balance:.4f}\n"
                    f"⭐ Уровень: {user.level}"
                )
                logger.info(f"🐻 User returned: {message.from_user.id}")
            
            await message.answer(
                welcome_text,
                reply_markup=get_main_menu(),
                parse_mode="markdown"
            )
            
            # Remove any old reply keyboards
            await message.answer(
                "🐻 Меню загружено!",
                reply_markup=ReplyKeyboardRemove()
            )
            
    except Exception as e:
        logger.error(f"❌ Error in cmd_start: {e}", exc_info=True)
        await message.answer(
            f"❌ Ошибка при инициализации.\n\n"
            f"Технические детали: {str(e)}"
        )


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(query: CallbackQuery):
    """
    Return to main menu.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            text = (
                f"🐻 **Лавы в БеарсМани!**\n\n"
                f"💰 **Основное меню**\n\n"
                f"👤 @{query.from_user.username or 'User'}\n"
                f"🪙 Баланс: {user.coins:.0f} коинов\n"
                f"💎 TON: {user.ton_balance:.4f}\n"
                f"⭐ Уровень: {user.level}"
            )
            
            try:
                await query.message.edit_text(text, reply_markup=get_main_menu(), parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=get_main_menu(), parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in main_menu_callback: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============ QUESTS ============

@router.callback_query(F.data == "quests")
async def quests_menu(query: CallbackQuery):
    """
    Show quests menu (placeholder).
    """
    try:
        text = (
            "📋 **Квесты**\n\n"
            "🚧 Функция в разработке!\n\n"
            "🔜 Скоро здесь появятся:"
            "• ✅ Ежедневные квесты\n"
            "• ✅ Недельные задания\n"
            "• ✅ Специальные ачивки\n"
            "• ✅ Награды за выполнение\n\n"
            "👍 Следите за обновлениями!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in quests_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============ REFERRALS ============

@router.callback_query(F.data == "referrals")
async def referrals_menu(query: CallbackQuery):
    """
    Show referrals system.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get direct referrals
            referrals_query = select(User).where(User.referred_by == user.telegram_id)
            referrals_result = await session.execute(referrals_query)
            referrals = referrals_result.scalars().all()
            
            # Generate referral link
            bot_username = "bearsmoney_bot"  # TODO: Get from config
            referral_link = f"https://t.me/{bot_username}?start={user.telegram_id}"
            
            text = (
                f"👥 **Реферальная система**\n\n"
                f"🔗 **Ваша ссылка:**\n"
                f"`{referral_link}`\n\n"
                f"💰 **Ваши бонусы:**\n"
                f"• 🎁 За каждого друга: **{REFERRAL_BONUS_REFERRER} коинов**\n"
                f"• 🎁 Ваш друг получит: **{REFERRAL_BONUS_REFERRED} коинов**\n\n"
            )
            
            # Referrals list
            text += f"👥 **Ваши рефералы** ({len(referrals)} чел.)\n"
            if referrals:
                earned = len(referrals) * REFERRAL_BONUS_REFERRER
                text += f"💰 Заработано: {earned} коинов\n\n"
                for idx, ref in enumerate(referrals[:5], 1):
                    status = "✅" if ref.coins > 1000 else "🔵"
                    text += f"{idx}. {status} @{ref.username or ref.first_name}\n"
                if len(referrals) > 5:
                    text += f"и ещё {len(referrals) - 5}...\n"
            else:
                text += "Пусто. Пригласи друзей!\n"
            
            text += (
                f"\n👉 **Как это работает:**\n"
                f"1. Поделись ссылкой с друзьями\n"
                f"2. Когда они зарегистрируются - получишь бонус!\n"
                f"3. Чем больше друзей - тем больше коинов!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Поделиться", url=f"https://t.me/share/url?url={referral_link}&text=Присоединяйся к БеарсМани!")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in referrals_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
