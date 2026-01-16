"""Handlers for coin-TON exchange and withdrawals."""
import logging
import re
from decimal import Decimal
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


class WithdrawStates(StatesGroup):
    """States for withdrawal flow."""
    waiting_for_ton_address = State()
    waiting_for_withdraw_amount = State()


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
            rate = settings.COIN_TO_TON_RATE  # 0.000002 TON per coin
            coins_per_ton = int(1 / rate)  # 500,000 coins per TON
            
            text = (
                f"💱 **Обмен валюты**\n\n"
                f"💼 **Ваши балансы**\n"
                f"├ 🪙 Coins: {user.coins:,.0f}\n"
                f"└ 💎 TON: {float(user.ton_balance):.4f}\n\n"
                f"📈 **Курс обмена**\n"
                f"├ 1 TON = {coins_per_ton:,} Coins\n"
                f"├ 0.5 TON = {coins_per_ton // 2:,} Coins\n"
                f"└ 1 Coin = {rate:.8f} TON\n\n"
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
            coins_per_ton = int(1 / rate)
            
            text = (
                f"🪙 → 💎 **Обмен Coins на TON**\n\n"
                f"💼 Ваш баланс: {user.coins:,.0f} Coins\n"
                f"📈 Курс: 1 TON = {coins_per_ton:,} Coins\n\n"
                f"⚠️ Минимум: 100 Coins\n"
                f"📊 Максимум: {user.coins:,.0f} Coins\n\n"
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
            amount = float(message.text.replace(',', '').replace(' ', ''))
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
                await message.answer(f"❌ Недостаточно Coins. Доступно: {user.coins:,.0f}")
                return
            
            # Calculate TON amount - AUTOMATIC CALCULATION
            rate = settings.COIN_TO_TON_RATE
            ton_amount = amount * rate
            ton_amount_decimal = Decimal(str(ton_amount))  # Convert to Decimal for arithmetic
            coins_per_ton = int(1 / rate)
            
            text = (
                f"✅ **Подтвердите обмен**\n\n"
                f"🪙 **Отдаёте:** {amount:,.0f} Coins\n"
                f"💎 **Получите:** {ton_amount:.4f} TON\n\n"
                f"🧠 **Расчёт:**\n"
                f"{amount:,.0f} Coins × {rate:.8f} = {ton_amount:.4f} TON\n\n"
                f"📈 **Курс:** 1 TON = {coins_per_ton:,} Coins\n\n"
                f"💼 **Останется:**\n"
                f"├ 🪙 Coins: {user.coins - amount:,.0f}\n"
                f"└ 💎 TON: {float(user.ton_balance + ton_amount_decimal):.4f}\n"
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
            
            # Execute exchange - Convert to Decimal
            ton_amount_decimal = Decimal(str(ton_amount))
            user.coins -= coin_amount
            user.ton_balance += ton_amount_decimal
            
            # Log transaction
            transaction_spend = CoinTransaction(
                user_id=user.id,
                amount=-coin_amount,
                transaction_type='exchange_to_ton',
                description=f'Обмен {coin_amount:,.0f} Coins на {ton_amount:.4f} TON'
            )
            session.add(transaction_spend)
            
            await session.commit()
            
            text = (
                f"✅ **Обмен выполнен!**\n\n"
                f"🪙 Отдано: {coin_amount:,.0f} Coins\n"
                f"💎 Получено: {ton_amount:.4f} TON\n\n"
                f"💼 **Новые балансы**\n"
                f"├ 🪙 Coins: {user.coins:,.0f}\n"
                f"└ 💎 TON: {float(user.ton_balance):.4f}\n"
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
            
            if float(user.ton_balance) < min_ton:
                await query.answer(f"❌ Минимальная сумма: {min_ton} TON", show_alert=True)
                return
            
            rate = settings.COIN_TO_TON_RATE
            coins_per_ton = int(1 / rate)
            
            text = (
                f"💎 → 🪙 **Обмен TON на Coins**\n\n"
                f"💼 Ваш баланс: {float(user.ton_balance):.4f} TON\n"
                f"📈 Курс: 1 TON = {coins_per_ton:,} Coins\n\n"
                f"⚠️ Минимум: {min_ton} TON\n"
                f"📊 Максимум: {float(user.ton_balance):.4f} TON\n\n"
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
            amount = float(message.text.replace(',', '').replace(' ', ''))
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
            
            amount_decimal = Decimal(str(amount))
            
            if user.ton_balance < amount_decimal:
                await message.answer(f"❌ Недостаточно TON. Доступно: {float(user.ton_balance):.4f}")
                return
            
            # Calculate coins amount - AUTOMATIC CALCULATION
            rate = settings.COIN_TO_TON_RATE
            coins_amount = amount / rate
            coins_per_ton = int(1 / rate)
            
            text = (
                f"✅ **Подтвердите обмен**\n\n"
                f"💎 **Отдаёте:** {amount:.4f} TON\n"
                f"🪙 **Получите:** {coins_amount:,.0f} Coins\n\n"
                f"🧠 **Расчёт:**\n"
                f"{amount:.4f} TON ÷ {rate:.8f} = {coins_amount:,.0f} Coins\n\n"
                f"📈 **Курс:** 1 TON = {coins_per_ton:,} Coins\n\n"
                f"💼 **Останется:**\n"
                f"├ 💎 TON: {float(user.ton_balance - amount_decimal):.4f}\n"
                f"└ 🪙 Coins: {user.coins + coins_amount:,.0f}\n"
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
            
            ton_amount_decimal = Decimal(str(ton_amount))
            
            # Double check balance
            if user.ton_balance < ton_amount_decimal:
                await query.answer("❌ Недостаточно TON", show_alert=True)
                await state.clear()
                return
            
            # Execute exchange
            user.ton_balance -= ton_amount_decimal
            user.coins += coins_amount
            
            # Log transaction
            transaction_earn = CoinTransaction(
                user_id=user.id,
                amount=coins_amount,
                transaction_type='exchange_from_ton',
                description=f'Обмен {ton_amount:.4f} TON на {coins_amount:,.0f} Coins'
            )
            session.add(transaction_earn)
            
            await session.commit()
            
            text = (
                f"✅ **Обмен выполнен!**\n\n"
                f"💎 Отдано: {ton_amount:.4f} TON\n"
                f"🪙 Получено: {coins_amount:,.0f} Coins\n\n"
                f"💼 **Новые балансы**\n"
                f"├ 💎 TON: {float(user.ton_balance):.4f}\n"
                f"└ 🪙 Coins: {user.coins:,.0f}\n"
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


# ============ WITHDRAWAL ============


def validate_ton_address(address: str) -> bool:
    """
    Validate TON address format.
    """
    # TON address format: EQ... or UQ... (48 symbols)
    pattern = r'^[EU]Q[A-Za-z0-9_-]{46}$'
    return bool(re.match(pattern, address))


@router.callback_query(F.data == "withdraw")
async def withdraw_menu(query: CallbackQuery):
    """
    Show withdrawal menu.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            min_withdraw = settings.MIN_WITHDRAW
            commission = settings.WITHDRAW_COMMISSION * 100  # Convert to percentage
            
            # Check if user has enough balance
            can_withdraw = float(user.ton_balance) >= min_withdraw
            
            text = (
                f"💸 **Вывод средств**\n\n"
                f"💼 **Ваш баланс**\n"
                f"└ 💎 TON: {float(user.ton_balance):.4f}\n\n"
                f"⚠️ **Условия вывода**\n"
                f"├ 💵 Минимум: {min_withdraw} TON\n"
                f"├ 📊 Комиссия: {commission:.0f}%\n"
                f"└ ⏱️ Время: 1-24 часа\n\n"
            )
            
            if can_withdraw:
                # Calculate example
                example_amount = min_withdraw
                fee = example_amount * settings.WITHDRAW_COMMISSION
                receive_amount = example_amount - fee
                
                text += (
                    f"📊 **Пример расчёта:**\n"
                    f"Вывод: {example_amount} TON\n"
                    f"Комиссия: {fee:.4f} TON\n"
                    f"Получите: {receive_amount:.4f} TON\n\n"
                    f"✅ Вы можете вывести средства!"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💸 Вывести TON", callback_data="start_withdraw")],
                    [InlineKeyboardButton(text="📊 История выводов", callback_data="withdraw_history")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
                ])
            else:
                needed = min_withdraw - float(user.ton_balance)
                text += (
                    f"❌ **Недостаточно средств**\n\n"
                    f"Нужно ещё: {needed:.4f} TON\n\n"
                    f"💡 **Как получить TON:**\n"
                    f"1. Зарабатывайте Coins с помощью медведей\n"
                    f"2. Обменяйте Coins на TON в разделе '💱 Обмен'\n"
                    f"3. Приглашайте друзей и получайте бонусы"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💱 Обмен", callback_data="exchange")],
                    [InlineKeyboardButton(text="🐻 Мои медведи", callback_data="bears")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
                ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in withdraw_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "start_withdraw")
async def start_withdraw(query: CallbackQuery, state: FSMContext):
    """
    Start withdrawal process - ask for TON address.
    """
    try:
        text = (
            f"💸 **Вывод TON**\n\n"
            f"🔑 **Введите адрес TON кошелька**\n\n"
            f"💡 **Формат:**\n"
            f"• Начинается с EQ... или UQ...\n"
            f"• Пример: `EQAa1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2`\n\n"
            f"⚠️ **Важно:**\n"
            f"Проверьте адрес перед отправкой!\n"
            f"Средства, отправленные на неверный адрес, не могут быть возвращены!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="withdraw")],
        ])
        
        await state.set_state(WithdrawStates.waiting_for_ton_address)
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in start_withdraw: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.message(WithdrawStates.waiting_for_ton_address)
async def process_ton_address(message: Message, state: FSMContext):
    """
    Process TON address for withdrawal.
    """
    try:
        address = message.text.strip()
        
        # Validate address
        if not validate_ton_address(address):
            await message.answer(
                "❌ **Неверный формат адреса**\n\n"
                "Адрес TON должен:\n"
                "• Начинаться с EQ или UQ\n"
                "• Содержать 48 символов\n\n"
                "Попробуйте ещё раз.",
                parse_mode="markdown"
            )
            return
        
        # Save address and ask for amount
        await state.update_data(ton_address=address)
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == message.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            min_withdraw = settings.MIN_WITHDRAW
            max_withdraw = float(user.ton_balance)
            
            text = (
                f"✅ **Адрес принят**\n\n"
                f"🔑 Кошелёк: `{address}`\n\n"
                f"💼 **Ваш баланс:** {float(user.ton_balance):.4f} TON\n"
                f"💵 **Минимум:** {min_withdraw} TON\n"
                f"📊 **Максимум:** {max_withdraw:.4f} TON\n\n"
                f"💸 **Введите сумму для вывода:**"
            )
            
            await state.set_state(WithdrawStates.waiting_for_withdraw_amount)
            await message.answer(text, parse_mode="markdown")
            
    except Exception as e:
        logger.error(f"❌ Error in process_ton_address: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


@router.message(WithdrawStates.waiting_for_withdraw_amount)
async def process_withdraw_amount(message: Message, state: FSMContext):
    """
    Process withdrawal amount.
    """
    try:
        # Parse amount
        try:
            amount = float(message.text.replace(',', '').replace(' ', ''))
        except ValueError:
            await message.answer("❌ Неверный формат. Введите число.")
            return
        
        min_withdraw = settings.MIN_WITHDRAW
        
        if amount < min_withdraw:
            await message.answer(f"❌ Минимальная сумма: {min_withdraw} TON")
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == message.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            amount_decimal = Decimal(str(amount))
            
            if user.ton_balance < amount_decimal:
                await message.answer(
                    f"❌ **Недостаточно средств**\n\n"
                    f"Доступно: {float(user.ton_balance):.4f} TON",
                    parse_mode="markdown"
                )
                return
            
            # Calculate commission
            commission = amount * settings.WITHDRAW_COMMISSION
            receive_amount = amount - commission
            
            # Get address from state
            data = await state.get_data()
            ton_address = data.get('ton_address')
            
            text = (
                f"💸 **Подтвердите вывод**\n\n"
                f"🔑 **Адрес:**\n`{ton_address}`\n\n"
                f"📊 **Расчёт:**\n"
                f"├ 💵 Сумма: {amount:.4f} TON\n"
                f"├ 📉 Комиссия ({settings.WITHDRAW_COMMISSION * 100:.0f}%): {commission:.4f} TON\n"
                f"└ 💰 **Получите: {receive_amount:.4f} TON**\n\n"
                f"💼 **Останется на балансе:** {float(user.ton_balance - amount_decimal):.4f} TON\n\n"
                f"⏱️ **Время обработки:** 1-24 часа\n\n"
                f"⚠️ Проверьте все данные!"
            )
            
            # Store all data in state
            await state.update_data(
                withdraw_amount=amount,
                commission=commission,
                receive_amount=receive_amount
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_withdraw"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="withdraw"),
                ],
            ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
    except Exception as e:
        logger.error(f"❌ Error in process_withdraw_amount: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


@router.callback_query(F.data == "confirm_withdraw")
async def confirm_withdraw(query: CallbackQuery, state: FSMContext):
    """
    Confirm and execute withdrawal.
    """
    try:
        data = await state.get_data()
        ton_address = data.get('ton_address')
        withdraw_amount = data.get('withdraw_amount')
        commission = data.get('commission')
        receive_amount = data.get('receive_amount')
        
        if not all([ton_address, withdraw_amount, commission, receive_amount]):
            await query.answer("❌ Ошибка данных", show_alert=True)
            await state.clear()
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            withdraw_amount_decimal = Decimal(str(withdraw_amount))
            
            # Double check balance
            if user.ton_balance < withdraw_amount_decimal:
                await query.answer("❌ Недостаточно средств", show_alert=True)
                await state.clear()
                return
            
            # Execute withdrawal
            user.ton_balance -= withdraw_amount_decimal
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=-withdraw_amount,
                transaction_type='withdraw',
                description=f'Вывод {receive_amount:.4f} TON на {ton_address[:10]}...{ton_address[-6:]}'
            )
            session.add(transaction)
            
            await session.commit()
            
            # Notify admin about withdrawal (TODO: implement actual payment)
            admin_text = (
                f"🚨 **Заявка на вывод**\n\n"
                f"👤 User ID: {user.telegram_id}\n"
                f"👤 Username: @{query.from_user.username or 'none'}\n"
                f"🔑 Адрес: `{ton_address}`\n"
                f"💰 Сумма: {receive_amount:.4f} TON\n"
                f"📊 Комиссия: {commission:.4f} TON\n"
                f"💵 Всего списано: {withdraw_amount:.4f} TON"
            )
            
            try:
                from aiogram import Bot
                bot = query.bot
                if settings.ADMIN_ID:
                    await bot.send_message(
                        settings.ADMIN_ID,
                        admin_text,
                        parse_mode="markdown"
                    )
            except Exception as e:
                logger.error(f"Failed to notify admin: {e}")
            
            # Success message
            text = (
                f"✅ **Заявка принята!**\n\n"
                f"💸 **Детали вывода:**\n"
                f"├ 💰 Сумма: {receive_amount:.4f} TON\n"
                f"├ 🔑 Кошелёк: `{ton_address[:10]}...`\n"
                f"└ ⏱️ Статус: Обрабатывается\n\n"
                f"💼 **Новый баланс:** {float(user.ton_balance):.4f} TON\n\n"
                f"⏱️ Средства поступят на ваш кошелёк в течение 1-24 часов.\n\n"
                f"📊 Вы можете проверить статус в 'Истории выводов'."
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 История", callback_data="withdraw_history")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("✅ Заявка принята!")
            await state.clear()
            
    except Exception as e:
        logger.error(f"❌ Error in confirm_withdraw: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
        await state.clear()


@router.callback_query(F.data == "withdraw_history")
async def withdraw_history(query: CallbackQuery):
    """
    Show withdrawal history.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get last 10 withdrawal transactions
            transactions_query = select(CoinTransaction).where(
                CoinTransaction.user_id == user.id,
                CoinTransaction.transaction_type == 'withdraw'
            ).order_by(CoinTransaction.created_at.desc()).limit(10)
            transactions_result = await session.execute(transactions_query)
            transactions = transactions_result.scalars().all()
            
            text = f"📊 **История выводов**\n\n"
            
            if not transactions:
                text += "📄 История пуста"
            else:
                for tx in transactions:
                    date_str = tx.created_at.strftime('%d.%m.%Y %H:%M')
                    text += f"💸 {tx.description}\n📅 {date_str}\n\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ К выводу", callback_data="withdraw")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in withdraw_history: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
