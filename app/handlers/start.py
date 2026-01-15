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


@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Start command handler.
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
                # Create new user
                user = User(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    coins=500.0,  # Starting coins
                    created_at=datetime.utcnow(),
                    referred_by=referrer_id,  # Set referrer
                )
                session.add(user)
                await session.commit()
                
                # Notify referrer
                if referrer_id:
                    referrer_query = select(User).where(User.telegram_id == referrer_id)
                    referrer_result = await session.execute(referrer_query)
                    referrer = referrer_result.scalar_one_or_none()
                    if referrer:
                        logger.info(f"✅ User {message.from_user.id} referred by {referrer_id}")
                
                welcome_text = (
                    f"🐻 **Лавы в БеарсМани!**\n\n"
                    f"🎉 Привет, {message.from_user.first_name}!\n\n"
                    f"🪣 В этом приложении вы можете:\n"
                    f"- 🐻 Собирать медведей\n"
                    f"- 💰 Зарабатывать коины\n"
                    f"- 🎁 Открывать ящики\n"
                    f"- 📋 Выполнять квесты\n"
                    f"- 👥 Приглашать друзей\n\n"
                    f"🌟 Вы получили 500 коинов для начала!\n\n"
                    f"💡 **Совет**: Начните с покупки обычного медведя (500 коинов). Он будет приносить доход!"
                )
                if referrer_id:
                    welcome_text += f"\n\n✅ Вы пришли по реферальной ссылке!"
                logger.info(f"🐻 New user registered: {message.from_user.id} ({message.from_user.first_name})")
            else:
                # User already exists
                welcome_text = (
                    f"🐻 **Лавы в БеарсМани!**\n\n"
                    f"💰 **Основное меню**\n\n"
                    f"👤 @{message.from_user.username or 'User'}\n"
                    f"💰 Ваш баланс: {user.coins:.0f} коинов\n"
                    f"🤝 Уровень: {user.level}"
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
            "🔜 Скоро здесь появятся:\n"
            "- ✅ Ежедневные квесты\n"
            "- ✅ Недельные задания\n"
            "- ✅ Специальные ачивки\n"
            "- ✅ Награды за выполнение\n\n"
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
    Show referrals system with 3 tiers.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get referrals by tier
            # Tier 1: direct referrals
            tier1_query = select(User).where(User.referred_by == user.telegram_id)
            tier1_result = await session.execute(tier1_query)
            tier1_users = tier1_result.scalars().all()
            
            # Tier 2: referrals of tier 1
            tier2_users = []
            for t1_user in tier1_users:
                tier2_query = select(User).where(User.referred_by == t1_user.telegram_id)
                tier2_result = await session.execute(tier2_query)
                tier2_users.extend(tier2_result.scalars().all())
            
            # Tier 3: referrals of tier 2
            tier3_users = []
            for t2_user in tier2_users:
                tier3_query = select(User).where(User.referred_by == t2_user.telegram_id)
                tier3_result = await session.execute(tier3_query)
                tier3_users.extend(tier3_result.scalars().all())
            
            # Generate referral link
            bot_username = "bearsmoney_bot"  # TODO: Get from config
            referral_link = f"https://t.me/{bot_username}?start={user.telegram_id}"
            
            text = (
                f"👥 **Реферальная система**\n\n"
                f"🔗 **Ваша ссылка:**\n"
                f"`{referral_link}`\n\n"
                f"💰 **Система дохода:**\n"
                f"🥇 1-й круг: **20%** от трат рефералов\n"
                f"🥈 2-й круг: **10%** от трат рефералов ваших рефералов\n"
                f"🥉 3-й круг: **5%** от трат рефералов 2-го круга\n\n"
            )
            
            # Tier 1
            text += f"\n🥇 **1-й круг** ({len(tier1_users)} чел.)\n"
            if tier1_users:
                tier1_earnings = sum(u.referral_earnings_tier1 or 0 for u in tier1_users)
                text += f"├ 💰 Заработано: {user.referral_earnings_tier1 or 0:.0f} коинов\n"
                for idx, ref in enumerate(tier1_users[:5], 1):
                    text += f"├ {idx}. @{ref.username or ref.first_name}\n"
                if len(tier1_users) > 5:
                    text += f"└ и ещё {len(tier1_users) - 5}...\n"
            else:
                text += "└ Пусто\n"
            
            # Tier 2
            text += f"\n🥈 **2-й круг** ({len(tier2_users)} чел.)\n"
            if tier2_users:
                text += f"├ 💰 Заработано: {user.referral_earnings_tier2 or 0:.0f} коинов\n"
                text += f"└ 👥 Рефералы ваших рефералов\n"
            else:
                text += "└ Пусто\n"
            
            # Tier 3
            text += f"\n🥉 **3-й круг** ({len(tier3_users)} чел.)\n"
            if tier3_users:
                text += f"├ 💰 Заработано: {user.referral_earnings_tier3 or 0:.0f} коинов\n"
                text += f"└ 👥 Рефералы 2-го круга\n"
            else:
                text += "└ Пусто\n"
            
            # Total
            total_earnings = (
                (user.referral_earnings_tier1 or 0) +
                (user.referral_earnings_tier2 or 0) +
                (user.referral_earnings_tier3 or 0)
            )
            text += f"\n💸 **Всего заработано:** {total_earnings:.0f} коинов"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Скопировать ссылку", url=referral_link)],
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
