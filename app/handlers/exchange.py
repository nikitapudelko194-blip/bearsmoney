"""Handlers for TON to Coins exchange (deposit only)."""
import logging
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

logger = logging.getLogger(__name__)
router = Router()


class ExchangeStates(StatesGroup):
    """States for exchange flow."""
    waiting_for_ton_amount = State()


@router.callback_query(F.data == "exchange")
async def exchange_menu(query: CallbackQuery):
    """
    Show exchange menu (TON → Coins only).
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Exchange rate from config
            rate = settings.COIN_TO_TON_RATE
            coins_per_ton = int(1 / rate)
            commission_pct = settings.WITHDRAW_COMMISSION * 100  # Комиссия в %
            
            text = (
                f"💱 **Пополнение баланса**\n\n"
                f"💼 **Ваши балансы**\n"
                f"├ 💎 TON: {float(user.ton_balance):.4f}\n"
                f"└ 🪙 Coins: {user.coins:,.0f}\n\n"
                f"📈 **Курс обмена**\n"
                f"├ 1 TON = {coins_per_ton:,} Coins\n"
                f"├ 0.5 TON = {coins_per_ton // 2:,} Coins\n"
                f"└ 0.1 TON = {coins_per_ton // 10:,} Coins\n\n"
                f"⚠️ **Условия**\n"
                f"├ 💰 Мин. пополнение: 0.01 TON\n"
                f"└ 📉 Комиссия: {commission_pct:.0f}%\n\n"
                f"💡 Обменяйте TON на игровые Coins для покупки медведей, кейсов и улучшений!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="💎 Пополнить (TON → Coins)", callback_data="exchange_ton_to_coins"),
                ],
                [
                    InlineKeyboardButton(text="📊 История пополнений", callback_data="exchange_history"),
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
            commission_pct = settings.WITHDRAW_COMMISSION * 100
            
            text = (
                f"💎 → 🪙 **Пополнение баланса**\n\n"
                f"💼 Ваш баланс: {float(user.ton_balance):.4f} TON\n"
                f"📈 Курс: 1 TON = {coins_per_ton:,} Coins\n"
                f"📉 Комиссия: {commission_pct:.0f}%\n\n"
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
            
            # Calculate coins amount WITH COMMISSION
            rate = settings.COIN_TO_TON_RATE
            coins_amount_before_commission = amount / rate
            commission_coins = coins_amount_before_commission * settings.WITHDRAW_COMMISSION
            coins_amount = coins_amount_before_commission - commission_coins  # Финальная сумма после комиссии
            
            coins_per_ton = int(1 / rate)
            commission_pct = settings.WITHDRAW_COMMISSION * 100
            
            text = (
                f"✅ **Подтвердите пополнение**\n\n"
                f"💎 **Отдаёте:** {amount:.4f} TON\n"
                f"🪙 **Получите:** {coins_amount:,.0f} Coins\n\n"
                f"🧠 **Расчёт:**\n"
                f"├ {amount:.4f} TON ÷ {rate:.8f} = {coins_amount_before_commission:,.0f} Coins\n"
                f"├ 📉 Комиссия ({commission_pct:.0f}%): {commission_coins:,.0f} Coins\n"
                f"└ 💰 К получению: {coins_amount:,.0f} Coins\n\n"
                f"📈 **Курс:** 1 TON = {coins_per_ton:,} Coins\n\n"
                f"💼 **Останется:**\n"
                f"├ 💎 TON: {float(user.ton_balance - amount_decimal):.4f}\n"
                f"└ 🪙 Coins: {user.coins + coins_amount:,.0f}\n"
            )
            
            # Store data in state
            await state.update_data(ton_amount=amount, coins_amount=coins_amount, commission_coins=commission_coins)
            
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
        commission_coins = data.get('commission_coins')
        
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
                description=f'Пополнение {ton_amount:.4f} TON → {coins_amount:,.0f} Coins (ком. {commission_coins:,.0f})'
            )
            session.add(transaction_earn)
            
            await session.commit()
            
            logger.info(f"✅ Exchange completed: {ton_amount:.4f} TON → {coins_amount:,.0f} coins (user {user.telegram_id})")
            
            text = (
                f"✅ **Пополнение выполнено!**\n\n"
                f"💎 Отдано: {ton_amount:.4f} TON\n"
                f"🪙 Получено: {coins_amount:,.0f} Coins\n"
                f"📉 Комиссия: {commission_coins:,.0f} Coins\n\n"
                f"💼 **Новые балансы**\n"
                f"├ 💎 TON: {float(user.ton_balance):.4f}\n"
                f"└ 🪙 Coins: {user.coins:,.0f}\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💱 Ещё пополнение", callback_data="exchange")],
                [InlineKeyboardButton(text="🛒 В магазин", callback_data="shop")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("✅ Пополнение успешно!")
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
                CoinTransaction.transaction_type == 'exchange_from_ton'
            ).order_by(CoinTransaction.created_at.desc()).limit(10)
            transactions_result = await session.execute(transactions_query)
            transactions = transactions_result.scalars().all()
            
            text = f"📊 **История пополнений**\n\n"
            
            if not transactions:
                text += "📄 История пуста\n\n💡 Пополните баланс, чтобы начать игру!"
            else:
                for tx in transactions:
                    date_str = tx.created_at.strftime('%d.%m %H:%M')
                    text += f"💎 {tx.description}\n📅 {date_str}\n\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Пополнить", callback_data="exchange_ton_to_coins")],
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
