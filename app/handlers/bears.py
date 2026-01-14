"""Handlers for bears management."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_session
from app.services.bears import BearsService
from app.database.models import User, Bear
from sqlalchemy import select
from app.keyboards.main_menu import get_main_menu, get_back_button, get_back_confirm_buttons
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()


@router.callback_query(F.data == "bears")
async def bears_list(query: CallbackQuery):
    """
    Show list of user's bears.
    """
    async with get_session() as session:
        # Get user
        user_query = select(User).where(User.telegram_id == query.from_user.id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one()
        
        # Get bears
        bears = await BearsService.get_user_bears(session, user.id)
        
        if not bears:
            text = "🐻 **Мои медведи**\n\n"
            text += "На вас нет медведей! 😢\n"
            text += "Перейдите в магазин чтобы купить первого медведя!"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ Магазин", callback_data="shop")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")],
            ])
        else:
            text = f"🐻 **Мои медведи** ({len(bears)})\n\n"
            
            for i, bear in enumerate(bears, 1):
                text += f"\n**{i}. {bear.name}**\n"
                text += f"Тип: `{bear.bear_type}`\n"
                text += f"Уровень: `{bear.level}`\n"
                text += f"Доход: `{bear.coins_per_hour:.1f}` коинов/час\n"
            
            # Create keyboard with bear buttons
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for i, bear in enumerate(bears):
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(
                        text=f"🐻 {bear.name[:15]}",
                        callback_data=f"bear_detail:{bear.id}"
                    )
                ])
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])
        
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        await query.answer()


@router.callback_query(F.data.startswith("bear_detail:"))
async def bear_detail(query: CallbackQuery):
    """
    Show bear detail and actions.
    """
    bear_id = int(query.data.split(":")[1])
    
    async with get_session() as session:
        # Get user and bear
        user_query = select(User).where(User.telegram_id == query.from_user.id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one()
        
        bear_query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user.id)
        bear_result = await session.execute(bear_query)
        bear = bear_result.scalar_one_or_none()
        
        if not bear:
            await query.answer("❌ Медведь не найден")
            return
        
        text = await BearsService.format_bear_info(bear, user)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⬆️ Улучшить (50 к)", callback_data=f"upgrade_bear:{bear_id}"),
                InlineKeyboardButton(text="🔥 Буст", callback_data=f"boost_bear:{bear_id}"),
            ],
            [
                InlineKeyboardButton(text="🗂️ Переименовать", callback_data=f"rename_bear:{bear_id}"),
                InlineKeyboardButton(text="💵 Продать", callback_data=f"sell_bear:{bear_id}"),
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="bears"),
            ],
        ])
        
        await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        await query.answer()


@router.callback_query(F.data.startswith("upgrade_bear:"))
async def upgrade_bear(query: CallbackQuery):
    """
    Upgrade bear.
    """
    bear_id = int(query.data.split(":")[1])
    
    async with get_session() as session:
        user_query = select(User).where(User.telegram_id == query.from_user.id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one()
        
        try:
            bear = await BearsService.upgrade_bear(session, bear_id, user.id)
            await query.answer("✅ Медведь улучшен! (Уровень {bear.level})")
            
            # Refresh bear detail
            await bear_detail(query)
        except ValueError as e:
            await query.answer(f"❌ {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("sell_bear:"))
async def sell_bear(query: CallbackQuery):
    """
    Sell bear.
    """
    bear_id = int(query.data.split(":")[1])
    
    async with get_session() as session:
        user_query = select(User).where(User.telegram_id == query.from_user.id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one()
        
        bear_query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user.id)
        bear_result = await session.execute(bear_query)
        bear = bear_result.scalar_one_or_none()
        
        if not bear:
            await query.answer("❌ Медведь не найден")
            return
        
        text = f"📄 Вы уверены что хотите продать {bear.name}?\n"
        text += f"Получите: 50 коинов"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_sell:{bear_id}"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"bear_detail:{bear_id}"),
            ],
        ])
        
        await query.message.edit_text(text, reply_markup=keyboard)
        await query.answer()


@router.callback_query(F.data.startswith("confirm_sell:"))
async def confirm_sell(query: CallbackQuery):
    """
    Confirm selling bear.
    """
    bear_id = int(query.data.split(":")[1])
    
    async with get_session() as session:
        user_query = select(User).where(User.telegram_id == query.from_user.id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one()
        
        try:
            refund = await BearsService.sell_bear(session, bear_id, user.id)
            await query.answer(f"✅ Медведь продан! +{refund:.0f} коинов")
            
            # Go back to bears list
            await bears_list(query)
        except ValueError as e:
            await query.answer(f"❌ {str(e)}", show_alert=True)


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(query: CallbackQuery):
    """
    Return to main menu.
    """
    text = (
        "🐻 **БеарсМани**\n\n"
        "🎉 Лавы о программе!\n\n"
        "💰 🐻 🎁 📋 👥 🛍️ 💸 📈\n"
    )
    
    await query.message.edit_text(text, reply_markup=get_main_menu(), parse_mode="markdown")
    await query.answer()
