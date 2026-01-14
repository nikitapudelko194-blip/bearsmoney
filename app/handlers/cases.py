"""Handlers for loot cases."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User
from app.services.cases import CasesService, CASE_TYPES
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "cases")
async def cases_menu(query: CallbackQuery):
    """
    Show cases menu.
    """
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            text = (
                "📋 **Ящики**\n\n"
                "💰 Ваш баланс: {user.coins:.0f} коинов\n\n"
                "Выберите ящик:\n\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📋 Обычный", callback_data="case_info:common")],
                [InlineKeyboardButton(text="📦 Редкий", callback_data="case_info:rare")],
                [InlineKeyboardButton(text="🔥 Эпический", callback_data="case_info:epic")],
                [InlineKeyboardButton(text="🌟 Легендарный", callback_data="case_info:legendary")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text.format(user=user), reply_markup=keyboard, parse_mode="markdown")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}, sending new message instead")
                await query.message.answer(text.format(user=user), reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in cases_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("case_info:"))
async def case_info(query: CallbackQuery):
    """
    Show case information and ask for confirmation.
    """
    try:
        case_type = query.data.split(":")[1]
        
        if case_type not in CASE_TYPES:
            await query.answer("❌ Неизвестный тип ящика")
            return
        
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            case_info = CasesService.get_case_info(case_type)
            
            text = (
                f"{CasesService.format_case_info(case_type)}\n\n"
                f"💰 Ваш баланс: {user.coins:.0f} коинов\n\n"
            )
            
            # Check if user has enough coins
            if case_info['cost_coins'] > 0 and user.coins < case_info['cost_coins']:
                text += f"❌ Недостаточно коинов (нужно {case_info['cost_coins']})"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="cases")],
                ])
            else:
                text += f"😎 Открыть ящик?"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Открыть", callback_data=f"open_case:{case_type}"),
                        InlineKeyboardButton(text="⬅️ Назад", callback_data="cases"),
                    ],
                ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}, sending new message instead")
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in case_info: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("open_case:"))
async def open_case(query: CallbackQuery):
    """
    Open a case and show the reward.
    """
    try:
        case_type = query.data.split(":")[1]
        
        if case_type not in CASE_TYPES:
            await query.answer("❌ Неизвестный тип ящика")
            return
        
        async with get_session() as session:
            try:
                result = await CasesService.open_case(session, query.from_user.id, case_type)
                
                # Format result message
                text = CasesService.format_case_result(result)
                
                # Add bear info if it was a bear reward
                if result['bear_created']:
                    bear_info = await CasesService.format_case_info(case_type)  # Reuse for formatting
                    text += f"\n\n🐻 Новый медведь: {result['bear_created'].name}"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="📦 Открыть ещё", callback_data=f"case_info:{case_type}"),
                        InlineKeyboardButton(text="⬅️ Назад", callback_data="cases"),
                    ],
                ])
                
                try:
                    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
                except Exception as e:
                    logger.warning(f"Could not edit message: {e}, sending new message instead")
                    await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
                
                await query.answer("😮 Открыто!")
                
            except ValueError as e:
                await query.answer(f"❌ {str(e)}", show_alert=True)
                
    except Exception as e:
        logger.error(f"❌ Error in open_case: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
