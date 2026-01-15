"""Handlers for coin-TON exchange."""
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
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()


class ExchangeStates(StatesGroup):
    """States for exchange flow."""
    waiting_for_coin_amount = State()
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
            
            # Exchange rate from config
            rate = settings.COIN_TO_TON_RATE  # 0.001 TON per coin
            
            text = (
                f"💱 **Обмен валюты**\n\n"
                f"💼 **Ваши балансы**\n"
                f"├ 🪙 Coins: {user.coins:.2f}\n"
                f"└ 💎 TON: {user.ton_balance:.4f}\n\n"
                f"📈 **Курс обмена**\n"
                f"├ 1 TON = {1/rate:.0f} Coins\n"
                f"└ 1 Coin = {rate:.6f} TON\n\n"
                f"⚠️ **Лимиты**\n"
                f"├ 💰 Мин. обмен: 100 Coins\n"
                f"└ 💎 Мин. вывод: {settings.MIN_WITHDRAW} TON\n\n"
                f"💡 Выберите направление обмена:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="🪙 → 💎 Coins → TON", callback_data="exchange_coins_to_ton"),
                ],
                [
                    InlineKeyboardButton(text="💎 → 🪙 TON → Coins", callback_data="exchange_ton_to_coins"),
                ],
                [
                    InlineKeyboardButton(text="📊 История обменов", callback_data="exchange_history"),
                ],
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
async def start_exchange_coins_to_ton(query: CallbackQuery, state: FSMContext):
    """
    Start coins to TON exchange.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            if user.coins < 100:
                await query.answer("❌ Минимальная сумма обмена: 100 Coins", show_alert=True)
                return
            
            rate = settings.COIN_TO_TON_RATE
            
            text = (
                f"🪙 → 💎 **Обмен Coins на TON**\n\n"
                f"💼 Ваш баланс: {user.coins:.2f} Coins\n"
                f"📈 Курс: 1 Coin = {rate:.6f} TON\n\n"
                f"⚠️ Минимум: 100 Coins\n"
                f"📊 Максимум: {user.coins:.0f} Coins\n\n"
                f"📝 Введите количество Coins для обмена:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Отмена", callback_data="exchange")],
            ])
            
            await state.set_state(ExchangeStates.waiting_for_coin_amount)
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in start_exchange_coins_to_ton: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.message(ExchangeStates.waiting_for_coin_amount)
async def process_coin_amount(message: Message, state: FSMContext):
    """
    Process coin amount for exchange.
    """
    try:
        # Parse amount
        try:
            amount = float(message.text)
        except ValueError:
            await message.answer("❌ Неверный формат. Введите число.")
            return
        
        if amount < 100:
            await message.answer("❌ Минимальная сумма: 100 Coins")
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == message.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            if amount > user.coins:
                await message.answer(f"❌ Недостаточно Coins. Доступно: {user.coins:.2f}")
                return
            
            # Calculate TON amount
            rate = settings.COIN_TO_TON_RATE
            ton_amount = amount * rate
            
            text = (
                f"✅ **Подтвердите обмен**\n\n"
                f"🪙 Отдаёте: {amount:.2f} Coins\n"
                f"💎 Получите: {ton_amount:.4f} TON\n\n"
                f"📈 Курс: 1 Coin = {rate:.6f} TON\n\n"
                f"💼 Останется:\n"
                f"├ 🪙 Coins: {user.coins - amount:.2f}\n"
                f"└ 💎 TON: {user.ton_balance + ton_amount:.4f}\n"
            )
            
            # Store data in state
            await state.update_data(coin_amount=amount, ton_amount=ton_amount)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_coins_to_ton"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="exchange"),
                ],
            ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
    except Exception as e:
        logger.error(f"❌ Error in process_coin_amount: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


@router.callback_query(F.data == "confirm_coins_to_ton")
async def confirm_coins_to_ton(query: CallbackQuery, state: FSMContext):
    """
    Confirm and execute coins to TON exchange.
    """
    try:
        data = await state.get_data()
        coin_amount = data.get('coin_amount')
        ton_amount = data.get('ton_amount')
        
        if not coin_amount or not ton_amount:
            await query.answer("❌ Ошибка данных", show_alert=True)
            await state.clear()
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Double check balance
            if user.coins < coin_amount:
                await query.answer("❌ Недостаточно Coins", show_alert=True)
                await state.clear()
                return
            
            # Execute exchange
            user.coins -= coin_amount
            user.ton_balance += ton_amount
            
            # Log transaction (spend coins)
            transaction_spend = CoinTransaction(
                user_id=user.id,
                amount=-coin_amount,
                transaction_type='exchange_to_ton',
                description=f'Обмен {coin_amount:.2f} Coins на {ton_amount:.4f} TON'
            )
            session.add(transaction_spend)
            
            await session.commit()
            
            text = (
                f"✅ **Обмен выполнен!**\n\n"
                f"🪙 Отдано: {coin_amount:.2f} Coins\n"
                f"💎 Получено: {ton_amount:.4f} TON\n\n"
                f"💼 **Новые балансы**\n"
                f"├ 🪙 Coins: {user.coins:.2f}\n"
                f"└ 💎 TON: {user.ton_balance:.4f}\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💱 Ещё обмен", callback_data="exchange")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("✅ Обмен успешен!")
            await state.clear()
            
    except Exception as e:
        logger.error(f"❌ Error in confirm_coins_to_ton: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        await state.clear()


@router.callback_query(F.data == "exchange_ton_to_coins")
async def start_exchange_ton_to_coins(query: CallbackQuery, state: FSMContext):
    """
    Start TON to coins exchange.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            min_ton = 0.01
            
            if user.ton_balance < min_ton:
                await query.answer(f"❌ Минимальная сумма: {min_ton} TON", show_alert=True)
                return
            
            rate = settings.COIN_TO_TON_RATE
            
            text = (
                f"💎 → 🪙 **Обмен TON на Coins**\n\n"
                f"💼 Ваш баланс: {user.ton_balance:.4f} TON\n"
                f"📈 Курс: 1 TON = {1/rate:.0f} Coins\n\n"
                f"⚠️ Минимум: {min_ton} TON\n"
                f"📊 Максимум: {user.ton_balance:.4f} TON\n\n"
                f"📝 Введите количество TON для обмена:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Отмена", callback_data="exchange")],
            ])
            
            await state.set_state(ExchangeStates.waiting_for_ton_amount)
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in start_exchange_ton_to_coins: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.message(ExchangeStates.waiting_for_ton_amount)
async def process_ton_amount(message: Message, state: FSMContext):
    """
    Process TON amount for exchange.
    """
    try:
        # Parse amount
        try:
            amount = float(message.text)
        except ValueError:
            await message.answer("❌ Неверный формат. Введите число.")
            return
        
        min_ton = 0.01
        if amount < min_ton:
            await message.answer(f"❌ Минимальная сумма: {min_ton} TON")
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == message.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            if amount > user.ton_balance:
                await message.answer(f"❌ Недостаточно TON. Доступно: {user.ton_balance:.4f}")
                return
            
            # Calculate coins amount
            rate = settings.COIN_TO_TON_RATE
            coins_amount = amount / rate
            
            text = (
                f"✅ **Подтвердите обмен**\n\n"
                f"💎 Отдаёте: {amount:.4f} TON\n"
                f"🪙 Получите: {coins_amount:.2f} Coins\n\n"
                f"📈 Курс: 1 TON = {1/rate:.0f} Coins\n\n"
                f"💼 Останется:\n"
                f"├ 💎 TON: {user.ton_balance - amount:.4f}\n"
                f"└ 🪙 Coins: {user.coins + coins_amount:.2f}\n"
            )
            
            # Store data in state
            await state.update_data(ton_amount=amount, coins_amount=coins_amount)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_ton_to_coins"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="exchange"),
                ],
            ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
    except Exception as e:
        logger.error(f"❌ Error in process_ton_amount: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


@router.callback_query(F.data == "confirm_ton_to_coins")
async def confirm_ton_to_coins(query: CallbackQuery, state: FSMContext):
    """
    Confirm and execute TON to coins exchange.
    """
    try:
        data = await state.get_data()
        ton_amount = data.get('ton_amount')
        coins_amount = data.get('coins_amount')
        
        if not ton_amount or not coins_amount:
            await query.answer("❌ Ошибка данных", show_alert=True)
            await state.clear()
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Double check balance
            if user.ton_balance < ton_amount:
                await query.answer("❌ Недостаточно TON", show_alert=True)
                await state.clear()
                return
            
            # Execute exchange
            user.ton_balance -= ton_amount
            user.coins += coins_amount
            
            # Log transaction
            transaction_earn = CoinTransaction(
                user_id=user.id,
                amount=coins_amount,
                transaction_type='exchange_from_ton',
                description=f'Обмен {ton_amount:.4f} TON на {coins_amount:.2f} Coins'
            )
            session.add(transaction_earn)
            
            await session.commit()
            
            text = (
                f"✅ **Обмен выполнен!**\n\n"
                f"💎 Отдано: {ton_amount:.4f} TON\n"
                f"🪙 Получено: {coins_amount:.2f} Coins\n\n"
                f"💼 **Новые балансы**\n"
                f"├ 💎 TON: {user.ton_balance:.4f}\n"
                f"└ 🪙 Coins: {user.coins:.2f}\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💱 Ещё обмен", callback_data="exchange")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("✅ Обмен успешен!")
            await state.clear()
            
    except Exception as e:
        logger.error(f"❌ Error in confirm_ton_to_coins: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        await state.clear()


@router.callback_query(F.data == "exchange_history")
async def exchange_history(query: CallbackQuery):
    """
    Show exchange history.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get last 10 exchange transactions
            transactions_query = select(CoinTransaction).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type.in_(['exchange_to_ton', 'exchange_from_ton'])
            ).order_by(CoinTransaction.created_at.desc()).limit(10)
            transactions_result = await session.execute(transactions_query)
            transactions = transactions_result.scalars().all()
            
            text = f"📊 **История обменов**\n\n"
            
            if not transactions:
                text += "📄 История пуста"
            else:
                for tx in transactions:
                    emoji = "🪙 → 💎" if tx.transaction_type == 'exchange_to_ton' else "💎 → 🪙"
                    date_str = tx.created_at.strftime('%d.%m %H:%M')
                    text += f"{emoji} {tx.description}\n📅 {date_str}\n\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ К обмену", callback_data="exchange")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in exchange_history: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
