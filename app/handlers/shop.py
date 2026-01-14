"""Handlers for shop functionality."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_session
from app.database.models import User
from app.services.bears import BearsService, BEAR_CLASSES
from sqlalchemy import select
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "shop")
async def shop_menu(query: CallbackQuery):
    """
    Show shop menu with bear classes.
    """
    try:
        text = (
            "🛍️ **Магазин Медведей**\n\n"
            "Выберите класс медведя:\n\n"
        )
        
        # Add class info with prices
        for bear_type in ['common', 'rare', 'epic', 'legendary']:
            class_info = BEAR_CLASSES[bear_type]
            text += (
                f"{class_info['color']} **{class_info['rarity']}**\n"
                f"💰 {class_info['cost']} коинов\n"
                f"💵 Обмен: {class_info['sell_price']} коинов\n"
                f"💰 Доход: +{class_info['income_per_hour']:.1f} коин/ч\n\n"
            )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🐻️ Обычные", callback_data="buy_bear:common")],
            [InlineKeyboardButton(text="🟢 Редкие", callback_data="buy_bear:rare")],
            [InlineKeyboardButton(text="🟣 Эпические", callback_data="buy_bear:epic")],
            [InlineKeyboardButton(text="🟡 Легендарные", callback_data="buy_bear:legendary")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception as e:
            logger.warning(f"Could not edit message: {e}, sending new message instead")
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in shop_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("buy_bear:"))
async def buy_bear_confirm(query: CallbackQuery):
    """
    Show confirmation for buying a bear.
    """
    try:
        bear_type = query.data.split(":")[1]
        
        if bear_type not in BEAR_CLASSES:
            await query.answer("❌ Неизвестный тип медведя")
            return
        
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            class_info = BEAR_CLASSES[bear_type]
            cost = class_info['cost']
            
            if user.coins < cost:
                text = (
                    f"😢 **Недостаточно коинов**\n\n"
                    f"Необходимо: {cost} коинов\n"
                    f"У вас есть: {user.coins:.0f} коинов\n"
                    f"Но стоит: {cost - user.coins:.0f} коинов"
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Обратно", callback_data="shop")],
                ])
            else:
                text = (
                    f"{class_info['color']} **Купить {class_info['rarity']}?**\n\n"
                    f"{class_info['emoji']} {class_info['name']}\n"
                    f"💰 Объем: {cost} коинов\n"
                    f"💵 Обмен: {class_info['sell_price']} коинов\n"
                    f"💰 Доход: +{class_info['income_per_hour']:.1f} коин/ч\n"
                    f"💰 У вас останется: {user.coins - cost:.0f} коинов"
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Купить", callback_data=f"confirm_buy:{bear_type}"),
                        InlineKeyboardButton(text="❌ Отменить", callback_data="shop"),
                    ],
                ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}, sending new message instead")
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in buy_bear_confirm: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("confirm_buy:"))
async def confirm_buy_bear(query: CallbackQuery):
    """
    Purchase a bear.
    """
    try:
        bear_type = query.data.split(":")[1]
        
        if bear_type not in BEAR_CLASSES:
            await query.answer("❌ Неизвестный тип медведя")
            return
        
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            class_info = BEAR_CLASSES[bear_type]
            cost = class_info['cost']
            
            if user.coins < cost:
                await query.answer("❌ Недостаточно коинов", show_alert=True)
                return
            
            try:
                # Create bear
                bear = await BearsService.create_bear(session, user.id, bear_type)
                user.coins -= cost
                await session.commit()
                
                text = (
                    f"✅ **Медведь куплен!**\n\n"
                    f"{class_info['color']} {class_info['emoji']} {bear.name}\n"
                    f"Класс: {class_info['rarity']}\n"
                    f"💰 Осталось: {user.coins:.0f} коинов"
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🐻 Мои медведи", callback_data="bears")],
                    [InlineKeyboardButton(text="🛍️ Магазин", callback_data="shop")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
                ])
                
                try:
                    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
                except Exception as e:
                    logger.warning(f"Could not edit message: {e}, sending new message instead")
                    await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
                
                await query.answer(f"✅ {bear.name} куплен!")
            except ValueError as e:
                await query.answer(f"❌ {str(e)}", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in confirm_buy_bear: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
