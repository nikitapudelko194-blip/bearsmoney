"""Handlers for coins <-> TON exchange."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, CoinTransaction
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from config import settings

logger = logging.getLogger(__name__)
router = Router()

# Exchange rates
COIN_TO_TON_RATE = settings.COIN_TO_TON_RATE  # 0.001 (1000 coins = 1 TON)
MIN_EXCHANGE_COINS = 1000  # Минимальная сумма обмена
MIN_EXCHANGE_TON = 1  # Минимальная сумма TON


class ExchangeStates(StatesGroup):
    """States for exchange process."""
    waiting_for_coins_amount = State()
    waiting_for_ton_amount = State()


@router.callback_query(F.data == "exchange")
async def exchange_menu(query: CallbackQuery):
    """
    Show exchange menu.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Calculate exchange rates
            coins_to_ton = 1000 * COIN_TO_TON_RATE  # 1000 coins = ? TON
            ton_to_coins = 1 / COIN_TO_TON_RATE  # 1 TON = ? coins
            
            text = (
                f"💱 **Обмен валюты**\n\n"
                f"💼 **Ваш баланс**\n"
                f"🪙 Коины: {user.coins:.0f}\n"
                f"💎 TON: {user.ton_balance:.4f}\n\n"
                f"📈 **Курс обмена**\n"
                f"• 1,000 коинов = {coins_to_ton:.3f} TON\n"
                f"• 1 TON = {ton_to_coins:.0f} коинов\n\n"
                f"⚠️ **Минимальные суммы**\n"
                f"• Коины → TON: {MIN_EXCHANGE_COINS} коинов\n"
                f"• TON → Коины: {MIN_EXCHANGE_TON} TON\n\n"
                f"👉 Выберите направление обмена:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🪙 Коины → 💎 TON", callback_data="exchange_coins_to_ton")],
                [InlineKeyboardButton(text="💎 TON → 🪙 Коины", callback_data="exchange_ton_to_coins")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in exchange_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "exchange_coins_to_ton")
async def exchange_coins_to_ton_start(query: CallbackQuery, state: FSMContext):
    """
    Start coins to TON exchange.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            if user.coins < MIN_EXCHANGE_COINS:
                await query.answer(
                    f"❌ Недостаточно коинов! Минимум: {MIN_EXCHANGE_COINS}",
                    show_alert=True
                )
                return
            
            text = (
                f"💱 **Обмен коинов на TON**\n\n"
                f"🪙 Ваш баланс: {user.coins:.0f} коинов\n"
                f"📈 Курс: 1,000 коинов = {COIN_TO_TON_RATE * 1000:.3f} TON\n\n"
                f"📝 Введите количество коинов для обмена\n"
                f"⚠️ Минимум: {MIN_EXCHANGE_COINS} коинов\n\n"
                f"⌨️ Отправьте сумму сообщением:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="exchange")],
            ])
            
            await state.set_state(ExchangeStates.waiting_for_coins_amount)
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in exchange_coins_to_ton_start: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.message(ExchangeStates.waiting_for_coins_amount)
async def process_coins_amount(message: Message, state: FSMContext):
    """
    Process coins amount for exchange.
    """
    try:
        amount = float(message.text)
        
        if amount < MIN_EXCHANGE_COINS:
            await message.answer(
                f"❌ Минимальная сумма: {MIN_EXCHANGE_COINS} коинов\nПопробуйте ещё раз."
            )
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == message.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            if user.coins < amount:
                await message.answer(
                    f"❌ Недостаточно коинов!\nУ вас: {user.coins:.0f}\nТребуется: {amount:.0f}"
                )
                return
            
            ton_amount = amount * COIN_TO_TON_RATE
            
            text = (
                f"✅ **Подтвердите обмен**\n\n"
                f"💸 Отдаёте: {amount:.0f} коинов\n"
                f"💰 Получите: {ton_amount:.4f} TON\n\n"
                f"📊 Курс: 1,000 коинов = {COIN_TO_TON_RATE * 1000:.3f} TON\n\n"
                f"💼 **После обмена**\n"
                f"🪙 Коины: {user.coins - amount:.0f}\n"
                f"💎 TON: {user.ton_balance + ton_amount:.4f}"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_exchange_c2t:{amount}"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="exchange"),
                ],
            ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            await state.clear()
    except ValueError:
        await message.answer("❌ Неправильное значение! Введите число.")
    except Exception as e:
        logger.error(f"❌ Error in process_coins_amount: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


@router.callback_query(F.data.startswith("confirm_exchange_c2t:"))
async def confirm_coins_to_ton(query: CallbackQuery):
    """
    Confirm and execute coins to TON exchange.
    """
    try:
        amount = float(query.data.split(":")[1])
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            if user.coins < amount:
                await query.answer("❌ Недостаточно коинов!", show_alert=True)
                return
            
            ton_amount = amount * COIN_TO_TON_RATE
            
            # Update balances
            user.coins -= amount
            user.ton_balance += ton_amount
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=-amount,
                transaction_type='exchange_to_ton',
                description=f"Обмен {amount:.0f} коинов на {ton_amount:.4f} TON"
            )
            session.add(transaction)
            
            await session.commit()
            
            text = (
                f"✅ **Обмен выполнен!**\n\n"
                f"💸 Обменяли: {amount:.0f} коинов\n"
                f"💰 Получили: {ton_amount:.4f} TON\n\n"
                f"💼 **Новый баланс**\n"
                f"🪙 Коины: {user.coins:.0f}\n"
                f"💎 TON: {user.ton_balance:.4f}"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё обмен", callback_data="exchange")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("✅ Обмен успешен!")
    except Exception as e:
        logger.error(f"❌ Error in confirm_coins_to_ton: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "exchange_ton_to_coins")
async def exchange_ton_to_coins_start(query: CallbackQuery, state: FSMContext):
    """
    Start TON to coins exchange.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            if user.ton_balance < MIN_EXCHANGE_TON:
                await query.answer(
                    f"❌ Недостаточно TON! Минимум: {MIN_EXCHANGE_TON} TON",
                    show_alert=True
                )
                return
            
            text = (
                f"💱 **Обмен TON на коины**\n\n"
                f"💎 Ваш баланс: {user.ton_balance:.4f} TON\n"
                f"📈 Курс: 1 TON = {1 / COIN_TO_TON_RATE:.0f} коинов\n\n"
                f"📝 Введите количество TON для обмена\n"
                f"⚠️ Минимум: {MIN_EXCHANGE_TON} TON\n\n"
                f"⌨️ Отправьте сумму сообщением:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="exchange")],
            ])
            
            await state.set_state(ExchangeStates.waiting_for_ton_amount)
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in exchange_ton_to_coins_start: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.message(ExchangeStates.waiting_for_ton_amount)
async def process_ton_amount(message: Message, state: FSMContext):
    """
    Process TON amount for exchange.
    """
    try:
        amount = float(message.text)
        
        if amount < MIN_EXCHANGE_TON:
            await message.answer(
                f"❌ Минимальная сумма: {MIN_EXCHANGE_TON} TON\nПопробуйте ещё раз."
            )
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == message.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            if user.ton_balance < amount:
                await message.answer(
                    f"❌ Недостаточно TON!\nУ вас: {user.ton_balance:.4f}\nТребуется: {amount:.4f}"
                )
                return
            
            coins_amount = amount / COIN_TO_TON_RATE
            
            text = (
                f"✅ **Подтвердите обмен**\n\n"
                f"💸 Отдаёте: {amount:.4f} TON\n"
                f"💰 Получите: {coins_amount:.0f} коинов\n\n"
                f"📊 Курс: 1 TON = {1 / COIN_TO_TON_RATE:.0f} коинов\n\n"
                f"💼 **После обмена**\n"
                f"🪙 Коины: {user.coins + coins_amount:.0f}\n"
                f"💎 TON: {user.ton_balance - amount:.4f}"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_exchange_t2c:{amount}"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="exchange"),
                ],
            ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            await state.clear()
    except ValueError:
        await message.answer("❌ Неправильное значение! Введите число.")
    except Exception as e:
        logger.error(f"❌ Error in process_ton_amount: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


@router.callback_query(F.data.startswith("confirm_exchange_t2c:"))
async def confirm_ton_to_coins(query: CallbackQuery):
    """
    Confirm and execute TON to coins exchange.
    """
    try:
        amount = float(query.data.split(":")[1])
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            if user.ton_balance < amount:
                await query.answer("❌ Недостаточно TON!", show_alert=True)
                return
            
            coins_amount = amount / COIN_TO_TON_RATE
            
            # Update balances
            user.ton_balance -= amount
            user.coins += coins_amount
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=coins_amount,
                transaction_type='exchange_from_ton',
                description=f"Обмен {amount:.4f} TON на {coins_amount:.0f} коинов"
            )
            session.add(transaction)
            
            await session.commit()
            
            text = (
                f"✅ **Обмен выполнен!**\n\n"
                f"💸 Обменяли: {amount:.4f} TON\n"
                f"💰 Получили: {coins_amount:.0f} коинов\n\n"
                f"💼 **Новый баланс**\n"
                f"🪙 Коины: {user.coins:.0f}\n"
                f"💎 TON: {user.ton_balance:.4f}"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔁 Ещё обмен", callback_data="exchange")],
                [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("✅ Обмен успешен!")
    except Exception as e:
        logger.error(f"❌ Error in confirm_ton_to_coins: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
