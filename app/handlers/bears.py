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
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "bears")
async def bears_list(query: CallbackQuery):
    """
    Show list of user's bears with classification.
    """
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get bears
            bears = await BearsService.get_user_bears(session, user.id)
            
            if not bears:
                text = (
                    "🐻 **Мои медведи**\n\n"
                    "На вас нет медведей! 😢\n"
                    "Перейдите в магазин чтобы купить первого медведя!"
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🛍️ Магазин", callback_data="shop")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
                ])
            else:
                text = f"🐻 **Мои медведи** ({len(bears)})\n\n"
                
                # Group bears by type for display
                bears_by_type = {}
                for idx, bear in enumerate(bears, 1):
                    if bear.bear_type not in bears_by_type:
                        bears_by_type[bear.bear_type] = []
                    bears_by_type[bear.bear_type].append((idx, bear))
                
                # Display bears grouped by type
                type_order = ['common', 'rare', 'epic', 'legendary']
                for bear_type in type_order:
                    if bear_type in bears_by_type:
                        class_info = BearsService.get_bear_class_info(bear_type)
                        text += f"\n{class_info['color']} **{class_info['rarity']}**\n"
                        for bear_num, bear in bears_by_type[bear_type]:
                            text += f"№{bear_num}. {bear.name} (Lv{bear.level})\n"
                
                # Create keyboard with bear buttons
                keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                for idx, bear in enumerate(bears, 1):
                    bear_card = await BearsService.format_bear_card(bear, idx)
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(
                            text=f"№{idx}",
                            callback_data=f"bear_detail:{bear.id}"
                        )
                    ])
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
            
            # Try to edit message, if fails - send new message
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}, sending new message instead")
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in bears_list: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("bear_detail:"))
async def bear_detail(query: CallbackQuery):
    """
    Show bear detail and actions.
    """
    try:
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
            
            # Get bear number
            bear_num = await BearsService.get_bear_number(session, bear_id, user.id)
            
            # Format header with number
            class_info = BearsService.get_bear_class_info(bear.bear_type)
            text = f"{class_info['color']} **№{bear_num}. {bear.name}**\n"
            text += f"{class_info['emoji']} {class_info['rarity']}\n\n"
            text += await BearsService.format_bear_info(bear, user)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="⬆️ Улучшить (50 к)", callback_data=f"upgrade_bear:{bear_id}"),
                    InlineKeyboardButton(text="🔥 Буст", callback_data=f"boost_bear:{bear_id}"),
                ],
                [
                    InlineKeyboardButton(text="📝 Переименовать", callback_data=f"rename_bear:{bear_id}"),
                    InlineKeyboardButton(text="💵 Продать", callback_data=f"sell_bear:{bear_id}"),
                ],
                [
                    InlineKeyboardButton(text="⬅️ Назад", callback_data="bears"),
                ],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}, sending new message instead")
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in bear_detail: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("upgrade_bear:"))
async def upgrade_bear(query: CallbackQuery):
    """
    Upgrade bear.
    """
    try:
        bear_id = int(query.data.split(":")[1])
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            try:
                bear = await BearsService.upgrade_bear(session, bear_id, user.id)
                await query.answer(f"✅ Медведь улучшен! (Уровень {bear.level})")
                
                # Refresh bear detail
                await bear_detail(query)
            except ValueError as e:
                await query.answer(f"❌ {str(e)}", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in upgrade_bear: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("sell_bear:"))
async def sell_bear(query: CallbackQuery):
    """
    Sell bear.
    """
    try:
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
            
            # Get bear number
            bear_num = await BearsService.get_bear_number(session, bear_id, user.id)
            class_info = BearsService.get_bear_class_info(bear.bear_type)
            
            text = (
                f"📋 Вы уверены что хотите продать?\n\n"
                f"{class_info['color']} **№{bear_num}. {bear.name}** ({class_info['rarity']})\n"
                f"Получите: {class_info['sell_price']} коинов"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_sell:{bear_id}"),
                    InlineKeyboardButton(text="❌ Нет", callback_data=f"bear_detail:{bear_id}"),
                ],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}, sending new message instead")
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in sell_bear: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("confirm_sell:"))
async def confirm_sell(query: CallbackQuery):
    """
    Confirm selling bear.
    """
    try:
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
    except Exception as e:
        logger.error(f"❌ Error in confirm_sell: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "main_menu")
async def main_menu_callback(query: CallbackQuery):
    """
    Return to main menu.
    """
    try:
        text = (
            "🐻 **БеарсМани**\n\n"
            "🎮 Лавы в нашем приложении!\n\n"
            "🕹️ Выберите экшн вацу\n"
        )
        
        try:
            await query.message.edit_text(text, reply_markup=get_main_menu(), parse_mode="markdown")
        except Exception as e:
            logger.warning(f"Could not edit message: {e}, sending new message instead")
            await query.message.answer(text, reply_markup=get_main_menu(), parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in main_menu_callback: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
