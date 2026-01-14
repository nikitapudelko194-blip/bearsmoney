"""Handlers for shop functionality."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_session
from app.database.models import User
from app.services.bears import BearsService, BEAR_CLASSES, BEAR_NAMES
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
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            text = (
                "🛍️ **Магазин Медведей**\n\n"
                "Выберите класс медведя:\n\n"
            )
            
            # Add class info
            for bear_type in ['common', 'rare', 'epic', 'legendary']:
                class_info = BEAR_CLASSES[bear_type]
                stats = BearsService.get_bear_stats(bear_type, 1)  # Variant 1
                premium_badge = ""
                if class_info['require_premium']:
                    premium_badge = " 💳 (Только донат)"
                text += (
                    f"{class_info['color']} **{class_info['rarity']}{premium_badge}**\n"
                    f"💰 Начиная с: {stats['cost']} коинов\n"
                    f"💰 Доход: +{stats['income']:.1f} коин/ч (Lv1)\n\n"
                )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🐻️ Обычные", callback_data="select_class:common")],
                [InlineKeyboardButton(text="🟢 Редкие", callback_data="select_class:rare")],
                [InlineKeyboardButton(text="🟣 Эпические", callback_data="select_class:epic")],
                [
                    InlineKeyboardButton(
                        text="🟡 Легендарные",
                        callback_data="select_class:legendary" if user.is_premium else "premium_only"
                    )
                ],
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


@router.callback_query(F.data == "premium_only")
async def premium_only(query: CallbackQuery):
    """
    Show premium required message.
    """
    await query.answer(
        "💳 Легендарные медведи автоматически распределяются в премиум пополнении средств!",
        show_alert=True
    )


@router.callback_query(F.data.startswith("select_class:"))
async def select_bear_class(query: CallbackQuery):
    """
    Show bear variants to choose from.
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
            bear_names = BEAR_NAMES[bear_type]
            
            text = (
                f"{class_info['color']} **Выберите медведя** ({class_info['rarity']})\n\n"
            )
            
            # Show first 5 variants
            for variant in range(1, 6):
                stats = BearsService.get_bear_stats(bear_type, variant)
                text += (
                    f"№{variant}. **{bear_names[variant-1]}**\n"
                    f"💰 Цена: {stats['cost']} коинов\n"
                    f"💰 Доход: +{stats['income']:.2f} коин/ч (Lv1)\n"
                    f"💵 Обмен: {stats['sell']} коинов\n\n"
                )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                # First 5 variants
                [InlineKeyboardButton(text=f"№{i+1}", callback_data=f"bear_confirm:{bear_type}:{i+1}") for i in range(5)],
                # Pagination: Next 5
                [InlineKeyboardButton(text="➡️ Надалее", callback_data=f"bear_page:{bear_type}:2")],
                # Back buttons
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="shop")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}, sending new message instead")
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in select_bear_class: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("bear_page:"))
async def bear_page(query: CallbackQuery):
    """
    Show next page of bear variants.
    """
    try:
        parts = query.data.split(":")
        bear_type = parts[1]
        page = int(parts[2])
        
        if bear_type not in BEAR_CLASSES:
            await query.answer("❌ Неизвестный тип")
            return
        
        class_info = BEAR_CLASSES[bear_type]
        bear_names = BEAR_NAMES[bear_type]
        
        # Calculate variant range for this page
        start_variant = (page - 1) * 5 + 1
        end_variant = min(start_variant + 5, 16)
        
        text = (
            f"{class_info['color']} **Выберите медведя** ({class_info['rarity']}) - стр. {page}\n\n"
        )
        
        for variant in range(start_variant, end_variant):
            stats = BearsService.get_bear_stats(bear_type, variant)
            text += (
                f"№{variant}. **{bear_names[variant-1]}**\n"
                f"💰 Цена: {stats['cost']} коинов\n"
                f"💰 Доход: +{stats['income']:.2f} коин/ч (Lv1)\n"
                f"💵 Обмен: {stats['sell']} коинов\n\n"
            )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        # Add variant buttons for this page
        variant_buttons = [
            InlineKeyboardButton(text=f"№{i}", callback_data=f"bear_confirm:{bear_type}:{i}")
            for i in range(start_variant, end_variant)
        ]
        keyboard.inline_keyboard.append(variant_buttons)
        
        # Navigation buttons
        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton(text="←️ Назад", callback_data=f"bear_page:{bear_type}:{page-1}"))
        if end_variant < 16:
            nav_buttons.append(InlineKeyboardButton(text="Далее ➡️", callback_data=f"bear_page:{bear_type}:{page+1}"))
        if nav_buttons:
            keyboard.inline_keyboard.append(nav_buttons)
        
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ К классам", callback_data="shop")])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception as e:
            logger.warning(f"Could not edit message: {e}, sending new message instead")
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in bear_page: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("bear_confirm:"))
async def bear_confirm(query: CallbackQuery):
    """
    Show confirmation for buying a specific bear.
    """
    try:
        parts = query.data.split(":")
        bear_type = parts[1]
        variant = int(parts[2])
        
        if bear_type not in BEAR_CLASSES:
            await query.answer("❌ Неизвестный тип")
            return
        
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            class_info = BEAR_CLASSES[bear_type]
            bear_names = BEAR_NAMES[bear_type]
            stats = BearsService.get_bear_stats(bear_type, variant)
            cost = stats['cost']
            
            # Check premium for legendary
            if class_info['require_premium'] and not user.is_premium:
                await query.answer(
                    "💳 Легендарные медведи доступны только для премиум пользователей!",
                    show_alert=True
                )
                return
            
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
                    f"{class_info['color']} **Купить этого медведя?**\n\n"
                    f"{class_info['emoji']} **{bear_names[variant-1]}** (Вариант {variant}/15)\n"
                    f"💰 Цена: {cost} коинов\n"
                    f"💵 Обмен: {stats['sell']} коинов\n"
                    f"💰 Доход: +{stats['income']:.2f} коин/ч (Lv1)\n"
                    f"\n💰 Останется: {user.coins - cost:.0f} коинов"
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Купить", callback_data=f"buy_confirm:{bear_type}:{variant}"),
                        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"select_class:{bear_type}"),
                    ],
                ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception as e:
                logger.warning(f"Could not edit message: {e}, sending new message instead")
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in bear_confirm: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("buy_confirm:"))
async def buy_confirm(query: CallbackQuery):
    """
    Purchase a specific bear variant.
    """
    try:
        parts = query.data.split(":")
        bear_type = parts[1]
        variant = int(parts[2])
        
        if bear_type not in BEAR_CLASSES:
            await query.answer("❌ Неизвестный тип")
            return
        
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            class_info = BEAR_CLASSES[bear_type]
            bear_names = BEAR_NAMES[bear_type]
            stats = BearsService.get_bear_stats(bear_type, variant)
            cost = stats['cost']
            
            # Check premium for legendary
            if class_info['require_premium'] and not user.is_premium:
                await query.answer("💳 Недостаточно прав для покупки", show_alert=True)
                return
            
            if user.coins < cost:
                await query.answer("❌ Недостаточно коинов", show_alert=True)
                return
            
            try:
                # Create bear with specific variant
                bear = await BearsService.create_bear(session, user.id, bear_type, variant=variant)
                user.coins -= cost
                await session.commit()
                
                text = (
                    f"✅ **Медведь куплен!**\n\n"
                    f"{class_info['color']} {class_info['emoji']} {bear.name}\n"
                    f"Класс: {class_info['rarity']}\n"
                    f"Вариант: {bear.variant}/15\n"
                    f"💰 Осталось: {user.coins:.0f} коинов"
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Купить ещё", callback_data=f"select_class:{bear_type}")],
                    [InlineKeyboardButton(text="🐻 Мои медведи", callback_data="bears")],
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
        logger.error(f"❌ Error in buy_confirm: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
