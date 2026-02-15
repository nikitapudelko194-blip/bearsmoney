"""Handlers for bears management."""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.db import get_session
from app.services.bears import BearsService
from app.services.features import FeaturesService
from app.database.models import User, Bear
from sqlalchemy import select
from app.keyboards.main_menu import get_main_menu
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logger = logging.getLogger(__name__)
router = Router()


class BearStates(StatesGroup):
    """States for bear management."""
    waiting_for_rename = State()
    waiting_for_p2p_price = State()
    selecting_fusion_bears = State()


@router.callback_query(F.data == "bears")
async def bears_list(query: CallbackQuery, state: FSMContext):
    """
    Show list of user's bears with classification.
    """
    try:
        await state.clear()  # Clear any previous states
        
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get bears (only NOT on sale)
            bears_query = select(Bear).where(
                Bear.owner_id == user.id,
                Bear.is_on_sale == False  # Only bears NOT on sale
            )
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            if not bears:
                text = (
                    "🐻 **Мои медведи**\n\n"
                    "У вас нет медведей! 😢\n"
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
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(
                            text=f"№{idx} - {bear.name}",
                            callback_data=f"bear_detail:{bear.id}"
                        )
                    ])
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text="📊 P2P Маркет", callback_data="p2p_market"),
                    InlineKeyboardButton(text="🔥 Переплавка", callback_data="fusion_menu"),
                ])
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
            
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
async def bear_detail(query: CallbackQuery, state: FSMContext):
    """
    Show bear detail and ALL actions.
    """
    try:
        await state.clear()
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
            
            # Get upgrade cost for button
            upgrade_cost = BearsService.get_upgrade_cost(bear.bear_type, bear.level)
            cost_text = f"{upgrade_cost // 1000}k" if upgrade_cost >= 1000 else str(upgrade_cost)
            
            # ALL BUTTONS
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=f"⬆️ Улучшить ({cost_text})", callback_data=f"upgrade_bear:{bear_id}"),
                    InlineKeyboardButton(text="🔥 Буст", callback_data=f"boost_bear:{bear_id}"),
                ],
                [
                    InlineKeyboardButton(text="📝 Переименовать", callback_data=f"rename_bear:{bear_id}"),
                    InlineKeyboardButton(text="💵 Продать", callback_data=f"sell_bear:{bear_id}"),
                ],
                [
                    InlineKeyboardButton(text="📤 Продать на P2P", callback_data=f"p2p_sell:{bear_id}"),
                    InlineKeyboardButton(text="🛡️ Страховка", callback_data=f"insure_bear:{bear_id}"),
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


# ============ UPGRADE BEAR ============

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
                await bear_detail(query, None)
            except ValueError as e:
                await query.answer(f"❌ {str(e)}", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in upgrade_bear: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============ BOOST BEAR ============

@router.callback_query(F.data.startswith("boost_bear:"))
async def boost_bear(query: CallbackQuery):
    """
    Boost bear (temporary power increase).
    """
    try:
        bear_id = int(query.data.split(":")[1])
        
        text = (
            "🔥 **Буст медведя**\n\n"
            "Временно увеличьте силу медведя!\n\n"
            "⏰ 1 час - 1,000 коинов (+50%)\n"
            "⏰ 6 часов - 5,000 коинов (+50%)\n"
            "⏰ 24 часа - 15,000 коинов (+50%)\n\n"
            "⚠️ Функция в разработке!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bear_detail:{bear_id}")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in boost_bear: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============ RENAME BEAR ============

@router.callback_query(F.data.startswith("rename_bear:"))
async def rename_bear_start(query: CallbackQuery, state: FSMContext):
    """
    Start renaming process.
    """
    try:
        bear_id = int(query.data.split(":")[1])
        
        async with get_session() as session:
            bear_query = select(Bear).where(Bear.id == bear_id)
            bear_result = await session.execute(bear_query)
            bear = bear_result.scalar_one_or_none()
            
            if not bear:
                await query.answer("❌ Медведь не найден")
                return
            
            text = (
                f"📝 **Переименовать медведя**\n\n"
                f"Текущее имя: {bear.name}\n\n"
                f"💬 Введите новое имя:\n"
                f"(от 2 до 20 символов)"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"bear_detail:{bear_id}")],
            ])
            
            await state.set_state(BearStates.waiting_for_rename)
            await state.update_data(bear_id=bear_id)
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in rename_bear_start: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.message(BearStates.waiting_for_rename)
async def process_rename(message: Message, state: FSMContext):
    """
    Process bear rename.
    """
    try:
        data = await state.get_data()
        bear_id = data['bear_id']
        new_name = message.text.strip()
        
        # Validate name
        if len(new_name) < 2 or len(new_name) > 20:
            await message.answer("❌ Имя должно быть от 2 до 20 символов!")
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == message.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            bear_query = select(Bear).where(Bear.id == bear_id, Bear.owner_id == user.id)
            bear_result = await session.execute(bear_query)
            bear = bear_result.scalar_one_or_none()
            
            if not bear:
                await message.answer("❌ Медведь не найден")
                await state.clear()
                return
            
            old_name = bear.name
            bear.name = new_name
            await session.commit()
            
            await message.answer(
                f"✅ Медведь переименован!\n"
                f"Было: {old_name}\n"
                f"Стало: {new_name}"
            )
            await state.clear()
    except Exception as e:
        logger.error(f"❌ Error in process_rename: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


# ============ SELL BEAR TO SYSTEM ============

@router.callback_query(F.data.startswith("sell_bear:"))
async def sell_bear(query: CallbackQuery):
    """
    Sell bear to system (confirm).
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
            
            # Get bear number and stats (WITH VARIANT!)
            bear_num = await BearsService.get_bear_number(session, bear_id, user.id)
            class_info = BearsService.get_bear_class_info(bear.bear_type)
            stats = BearsService.get_bear_stats(bear.bear_type, bear.variant)  # ✅ FIX!
            
            text = (
                f"📋 Вы уверены что хотите продать?\n\n"
                f"{class_info['color']} **№{bear_num}. {bear.name}** ({class_info['rarity']})\n"
                f"Получите: {stats['sell']} коинов"  # ✅ FIX!
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
    Confirm selling bear to system.
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
                await bears_list(query, None)
            except ValueError as e:
                await query.answer(f"❌ {str(e)}", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in confirm_sell: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============ P2P SELLING ============

@router.callback_query(F.data.startswith("p2p_sell:"))
async def p2p_sell_bear(query: CallbackQuery, state: FSMContext):
    """
    Start P2P selling process (ask for price).
    """
    try:
        bear_id = int(query.data.split(":")[1])
        
        async with get_session() as session:
            bear_query = select(Bear).where(Bear.id == bear_id)
            bear_result = await session.execute(bear_query)
            bear = bear_result.scalar_one_or_none()
            
            if not bear:
                await query.answer("❌ Медведь не найден")
                return
            
            class_info = BearsService.get_bear_class_info(bear.bear_type)
            stats = BearsService.get_bear_stats(bear.bear_type, bear.variant)  # ✅ FIX!
            
            text = (
                f"📤 **Выставить на P2P**\n\n"
                f"{class_info['color']} {bear.name} ({class_info['rarity']})\n"
                f"Уровень: {bear.level}\n\n"
                f"💬 Введите цену в коинах:\n"
                f"Мин. {stats['sell']} коинов"  # ✅ FIX!
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"bear_detail:{bear_id}")],
            ])
            
            await state.set_state(BearStates.waiting_for_p2p_price)
            await state.update_data(bear_id=bear_id)
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in p2p_sell_bear: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.message(BearStates.waiting_for_p2p_price)
async def process_p2p_price(message: Message, state: FSMContext):
    """
    Process P2P price input.
    """
    try:
        data = await state.get_data()
        bear_id = data['bear_id']
        
        try:
            price = float(message.text)
            if price <= 0:
                await message.answer("❌ Цена должна быть больше 0!")
                return
        except ValueError:
            await message.answer("❌ Введите число!")
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == message.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            try:
                listing = await FeaturesService.list_bear_for_sale(session, bear_id, user.id, price)
                await message.answer(
                    f"✅ Медведь выставлен на продажу!\n"
                    f"💰 Цена: {price:.0f} коинов\n\n"
                    f"Медведь скрыт из профиля до продажи."
                )
                await state.clear()
            except ValueError as e:
                await message.answer(f"❌ {str(e)}")
                await state.clear()
    except Exception as e:
        logger.error(f"❌ Error in process_p2p_price: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


# ============ P2P MARKET ============

@router.callback_query(F.data == "p2p_market")
async def p2p_market(query: CallbackQuery):
    """
    Show P2P marketplace.
    """
    try:
        async with get_session() as session:
            listings = await FeaturesService.get_available_listings(session, limit=10)
            
            if not listings:
                text = (
                    "📊 **P2P Маркетплейс**\n\n"
                    "На маркете пока нет медведей! 😢\n\n"
                    "Будьте первым кто выставит медведя на продажу!"
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="bears")],
                ])
            else:
                text = f"📊 **P2P Маркетплейс** ({len(listings)} лотов)\n\n"
                
                for listing in listings:
                    bear_type_info = BearsService.get_bear_class_info(listing['bear_type'])
                    text += (
                        f"{bear_type_info['color']} **{listing['bear_name']}**\n"
                        f"├ {bear_type_info['rarity']} (Lv{listing['bear_level']})\n"
                        f"├ 💰 {listing['price_coins']:.0f} коинов\n"
                        f"└ Продавец: {listing['seller_name']}\n\n"
                    )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                for listing in listings:
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(
                            text=f"💰 {listing['bear_name']} - {listing['price_coins']:.0f}к",
                            callback_data=f"p2p_buy:{listing['listing_id']}"
                        )
                    ])
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="bears")])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in p2p_market: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("p2p_buy:"))
async def p2p_buy_confirm(query: CallbackQuery):
    """
    Confirm P2P purchase.
    """
    try:
        listing_id = int(query.data.split(":")[1])
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            try:
                result = await FeaturesService.buy_bear_from_player(session, listing_id, user.id)
                await query.answer("✅ Медведь куплен!")
                await p2p_market(query)
            except ValueError as e:
                await query.answer(f"❌ {str(e)}", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in p2p_buy_confirm: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============ INSURANCE ============

@router.callback_query(F.data.startswith("insure_bear:"))
async def insure_bear_menu(query: CallbackQuery):
    """
    Show insurance options.
    """
    try:
        bear_id = int(query.data.split(":")[1])
        
        text = (
            "🛡️ **Страховка медведя**\n\n"
            "Выберите срок:\n\n"
            "⏰ 24 часа - 5,000 коинов\n"
            "⏰ 48 часов - 10,000 коинов\n"
            "♾️ Навсегда - 50,000 коинов"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⏰ 24ч (5K)", callback_data=f"insure_confirm:{bear_id}:24"),
                InlineKeyboardButton(text="⏰ 48ч (10K)", callback_data=f"insure_confirm:{bear_id}:48"),
            ],
            [
                InlineKeyboardButton(text="♾️ Навсегда (50K)", callback_data=f"insure_confirm:{bear_id}:-1"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=f"bear_detail:{bear_id}"),
            ],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in insure_bear_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("insure_confirm:"))
async def insure_bear_confirm(query: CallbackQuery):
    """
    Confirm insurance purchase.
    """
    try:
        parts = query.data.split(":")
        bear_id = int(parts[1])
        hours = int(parts[2])
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            try:
                insurance = await FeaturesService.insure_bear(session, bear_id, user.id, hours)
                hours_text = f"{hours} часов" if hours > 0 else "навсегда"
                await query.answer(f"✅ Страховка на {hours_text} оформлена!")
                await bear_detail(query, None)
            except ValueError as e:
                await query.answer(f"❌ {str(e)}", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in insure_bear_confirm: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============ FUSION ============

@router.callback_query(F.data == "fusion_menu")
async def fusion_menu(query: CallbackQuery):
    """
    Show fusion menu.
    """
    try:
        text = (
            "🔥 **Переплавка медведей**\n\n"
            "Объедините 10 медведей в одного более редкого!\n\n"
            "🟢 10 Обычных → 1 Редкий\n"
            "🟣 10 Редких → 1 Эпический\n"
            "🔥 10 Эпических → 1 Легендарный"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Обычные → Редкий", callback_data="fusion_start:common")],
            [InlineKeyboardButton(text="🟣 Редкие → Эпический", callback_data="fusion_start:rare")],
            [InlineKeyboardButton(text="🔥 Эпические → Легендарный", callback_data="fusion_start:epic")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="bears")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in fusion_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("fusion_start:"))
async def fusion_start(query: CallbackQuery, state: FSMContext):
    """
    Start fusion process.
    """
    try:
        bear_type = query.data.split(":")[1]
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get bears of this type
            bears_query = select(Bear).where(
                Bear.owner_id == user.id,
                Bear.bear_type == bear_type,
                Bear.is_on_sale == False
            )
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            if len(bears) < 10:
                await query.answer(
                    f"❌ Недостаточно медведей!\nНужно: 10\nЕсть: {len(bears)}",
                    show_alert=True
                )
                return
            
            # Take first 10
            selected_bears = bears[:10]
            bear_ids = [b.id for b in selected_bears]
            
            class_info = BearsService.get_bear_class_info(bear_type)
            output_type = 'rare' if bear_type == 'common' else 'epic' if bear_type == 'rare' else 'legendary'
            output_info = BearsService.get_bear_class_info(output_type)
            
            text = (
                f"🔥 **Подтверждение переплавки**\n\n"
                f"{class_info['color']} 10x {class_info['rarity']}\n"
                f"⬇️\n"
                f"{output_info['color']} 1x {output_info['rarity']}\n\n"
                f"⚠️ Все 10 медведей будут уничтожены!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"fusion_confirm:{bear_type}:{','.join(map(str, bear_ids))}"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="fusion_menu"),
                ],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in fusion_start: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("fusion_confirm:"))
async def fusion_confirm(query: CallbackQuery):
    """
    Confirm fusion.
    """
    try:
        parts = query.data.split(":")
        bear_type = parts[1]
        bear_ids = [int(x) for x in parts[2].split(",")]
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            try:
                result = await FeaturesService.fuse_bears(session, user.id, bear_ids, bear_type)
                new_bear = result['new_bear']
                class_info = BearsService.get_bear_class_info(new_bear.bear_type)
                
                await query.answer(f"✅ Переплавка завершена!")
                
                text = (
                    f"🎉 **Переплавка завершена!**\n\n"
                    f"{class_info['color']} {class_info['emoji']} {new_bear.name}\n"
                    f"{class_info['rarity']}\n\n"
                    f"✨ Поздравляем!"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🐻 Мои медведи", callback_data="bears")],
                ])
                
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except ValueError as e:
                await query.answer(f"❌ {str(e)}", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Error in fusion_confirm: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============ BACK TO MAIN MENU ============

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(query: CallbackQuery, state: FSMContext):
    """
    Return to main menu.
    """
    try:
        await state.clear()
        text = (
            "🐻 **БеарсМани**\n\n"
            "🎮 Лавы в нашем приложении!\n\n"
            "🕹️ Выберите экшн вацу"
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
