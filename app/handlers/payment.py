"""Payment handlers for TON purchases."""
import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, CoinTransaction
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)
router = Router()

# TON packages with prices
TON_PACKAGES = {
    'package_0.5': {
        'ton_amount': 0.5,
        'stars': 50,
        'rub': 250,
        'ton_crypto': 0.5,
        'name': '0.5 TON',
        'emoji': '🪙'
    },
    'package_1.0': {
        'ton_amount': 1.0,
        'stars': 100,
        'rub': 500,
        'ton_crypto': 1.0,
        'name': '1.0 TON',
        'emoji': '💎'
    },
    'package_2.5': {
        'ton_amount': 2.5,
        'stars': 250,
        'rub': 1250,
        'ton_crypto': 2.5,
        'name': '2.5 TON',
        'emoji': '💎💎'
    },
    'package_5.0': {
        'ton_amount': 5.0,
        'stars': 500,
        'rub': 2500,
        'ton_crypto': 5.0,
        'name': '5.0 TON',
        'emoji': '💠'
    },
    'package_10.0': {
        'ton_amount': 10.0,
        'stars': 1000,
        'rub': 5000,
        'ton_crypto': 10.0,
        'name': '10.0 TON',
        'emoji': '💰'
    },
}


class PaymentStates(StatesGroup):
    """States for payment flow."""
    waiting_for_ton_address = State()


@router.callback_query(F.data == "buy_ton")
async def buy_ton_menu(query: CallbackQuery):
    """
    Show TON purchase menu with packages.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            text = (
                f"💳 **Купить TON**\n\n"
                f"💼 **Ваш баланс**\n"
                f"└ 💎 TON: {user.ton_balance:.4f}\n\n"
                f"💎 **Выберите пакет:**\n\n"
                f"🪙 **0.5 TON** - 50 ⭐ / 250₽\n"
                f"💎 **1.0 TON** - 100 ⭐ / 500₽\n"
                f"💎💎 **2.5 TON** - 250 ⭐ / 1,250₽\n"
                f"💠 **5.0 TON** - 500 ⭐ / 2,500₽\n"
                f"💰 **10.0 TON** - 1,000 ⭐ / 5,000₽\n\n"
                f"💡 Выберите пакет для продолжения:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🪙 0.5 TON", callback_data="select_package:package_0.5")],
                [InlineKeyboardButton(text="💎 1.0 TON", callback_data="select_package:package_1.0")],
                [InlineKeyboardButton(text="💎💎 2.5 TON", callback_data="select_package:package_2.5")],
                [InlineKeyboardButton(text="💠 5.0 TON", callback_data="select_package:package_5.0")],
                [InlineKeyboardButton(text="💰 10.0 TON", callback_data="select_package:package_10.0")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in buy_ton_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("select_package:"))
async def select_package(query: CallbackQuery):
    """
    Show payment methods for selected package.
    """
    try:
        package_id = query.data.split(":")[1]
        
        if package_id not in TON_PACKAGES:
            await query.answer("❌ Неизвестный пакет", show_alert=True)
            return
        
        package = TON_PACKAGES[package_id]
        
        text = (
            f"{package['emoji']} **Пакет: {package['name']}**\n\n"
            f"💎 Получите: **{package['ton_amount']} TON**\n\n"
            f"💳 **Выберите способ оплаты:**\n\n"
            f"⭐ **Telegram Stars** - {package['stars']} Stars\n"
            f"• Оплата внутри Telegram\n"
            f"• Мгновенное зачисление\n\n"
            f"💎 **TON Wallet** - {package['ton_crypto']} TON\n"
            f"• Оплата криптовалютой\n"
            f"• Зачисление 1-5 мин\n\n"
            f"💳 **Банковская карта** - {package['rub']}₽\n"
            f"• Оплата российскими рублями\n"
            f"• Зачисление 1-2 мин"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ {package['stars']} Stars", callback_data=f"pay_stars:{package_id}")],
            [InlineKeyboardButton(text=f"💎 {package['ton_crypto']} TON", callback_data=f"pay_ton:{package_id}")],
            [InlineKeyboardButton(text=f"💳 {package['rub']}₽", callback_data=f"pay_rub:{package_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_ton")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in select_package: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============ TELEGRAM STARS PAYMENT ============

@router.callback_query(F.data.startswith("pay_stars:"))
async def pay_with_stars(query: CallbackQuery):
    """
    Create Telegram Stars invoice.
    """
    try:
        package_id = query.data.split(":")[1]
        
        if package_id not in TON_PACKAGES:
            await query.answer("❌ Неизвестный пакет", show_alert=True)
            return
        
        package = TON_PACKAGES[package_id]
        
        # Create invoice
        prices = [LabeledPrice(label=package['name'], amount=package['stars'])]
        
        await query.bot.send_invoice(
            chat_id=query.from_user.id,
            title=f"Покупка {package['name']}",
            description=f"Пополнение баланса на {package['ton_amount']} TON",
            payload=f"ton_stars_{package_id}_{query.from_user.id}",
            provider_token="",  # Empty for Telegram Stars
            currency="XTR",
            prices=prices,
            max_tip_amount=0,
            suggested_tip_amounts=[],
        )
        
        await query.answer("💳 Инвойс отправлен!")
        
    except Exception as e:
        logger.error(f"❌ Error in pay_with_stars: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """
    Handle pre-checkout query (approve payment).
    """
    try:
        await pre_checkout_query.answer(ok=True)
    except Exception as e:
        logger.error(f"❌ Error in process_pre_checkout: {e}", exc_info=True)
        await pre_checkout_query.answer(
            ok=False,
            error_message="Произошла ошибка. Попробуйте позже."
        )


@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """
    Handle successful payment.
    """
    try:
        payload = message.successful_payment.invoice_payload
        
        # Parse payload: ton_stars_package_0.5_123456789
        parts = payload.split("_")
        if len(parts) < 4 or parts[0] != "ton" or parts[1] != "stars":
            logger.error(f"Invalid payload: {payload}")
            return
        
        package_id = f"{parts[2]}_{parts[3]}"
        user_id = int(parts[4])
        
        if package_id not in TON_PACKAGES:
            logger.error(f"Unknown package: {package_id}")
            return
        
        package = TON_PACKAGES[package_id]
        ton_amount = package['ton_amount']
        
        # Credit TON to user
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == user_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User not found: {user_id}")
                return
            
            # Add TON
            user.ton_balance += ton_amount
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=ton_amount,
                transaction_type='purchase_stars',
                description=f'Покупка {package["name"]} за {package["stars"]} Stars (+{ton_amount} TON)'
            )
            session.add(transaction)
            
            await session.commit()
            
            # Success message
            text = (
                f"✅ **Платёж успешен!**\n\n"
                f"💎 **Начислено:** {ton_amount} TON\n"
                f"⭐ **Оплачено:** {package['stars']} Stars\n\n"
                f"💼 **Новый баланс:** {user.ton_balance:.4f} TON\n\n"
                f"🎉 Спасибо за покупку!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎰 Открыть кейсы", callback_data="cases")],
                [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            logger.info(f"✅ Payment successful: User {user_id} purchased {ton_amount} TON for {package['stars']} Stars")
            
    except Exception as e:
        logger.error(f"❌ Error in process_successful_payment: {e}", exc_info=True)


# ============ TON WALLET PAYMENT ============

@router.callback_query(F.data.startswith("pay_ton:"))
async def pay_with_ton_wallet(query: CallbackQuery):
    """
    Pay with TON cryptocurrency.
    """
    try:
        package_id = query.data.split(":")[1]
        
        if package_id not in TON_PACKAGES:
            await query.answer("❌ Неизвестный пакет", show_alert=True)
            return
        
        package = TON_PACKAGES[package_id]
        
        # TODO: Generate unique deposit address or use payment link
        # For now, using placeholder address
        deposit_address = "UQAabc123def456ghi789jkl012mno345pqr678stu901vwx234yz"
        
        # Generate payment memo (comment)
        payment_memo = f"USER_{query.from_user.id}_{package_id}"
        
        text = (
            f"💎 **Оплата TON**\n\n"
            f"💰 **Пакет:** {package['name']}\n"
            f"💵 **Сумма:** {package['ton_crypto']} TON\n\n"
            f"🔑 **Адрес для перевода:**\n"
            f"`{deposit_address}`\n\n"
            f"📝 **Комментарий (обязательно):**\n"
            f"`{payment_memo}`\n\n"
            f"⚠️ **Важно:**\n"
            f"• Обязательно укажите комментарий!\n"
            f"• Отправьте точную сумму: {package['ton_crypto']} TON\n"
            f"• Зачисление после 1-5 подтверждений\n\n"
            f"🔍 **Статус:** Ожидаем платёж...\n\n"
            f"💬 Помощь: @support (TODO: add support contact)"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Проверить платёж", callback_data=f"check_ton_payment:{package_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"select_package:{package_id}")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer(
            "💎 Отправьте TON на указанный адрес с комментарием!",
            show_alert=True
        )
        
    except Exception as e:
        logger.error(f"❌ Error in pay_with_ton_wallet: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("check_ton_payment:"))
async def check_ton_payment(query: CallbackQuery):
    """
    Check TON payment status (placeholder).
    """
    # TODO: Implement blockchain transaction checking
    await query.answer(
        "🔍 Проверка платежа...\n\n"
        "🚧 Функция в разработке.\n"
        "Платёж будет обработан автоматически в течение 5 минут.",
        show_alert=True
    )


# ============ BANK CARD PAYMENT (YOOKASSA) ============

@router.callback_query(F.data.startswith("pay_rub:"))
async def pay_with_card(query: CallbackQuery):
    """
    Pay with bank card (rubles via YooKassa).
    """
    try:
        package_id = query.data.split(":")[1]
        
        if package_id not in TON_PACKAGES:
            await query.answer("❌ Неизвестный пакет", show_alert=True)
            return
        
        package = TON_PACKAGES[package_id]
        
        # TODO: Create YooKassa payment
        # For now, showing placeholder
        payment_url = f"https://example.com/payment/{query.from_user.id}/{package_id}"
        
        text = (
            f"💳 **Оплата банковской картой**\n\n"
            f"💰 **Пакет:** {package['name']}\n"
            f"💵 **Сумма:** {package['rub']}₽\n"
            f"💎 **Получите:** {package['ton_amount']} TON\n\n"
            f"🔒 **Безопасная оплата через YooKassa**\n"
            f"• Принимаются все российские карты\n"
            f"• Зачисление в течение 1-2 минут\n"
            f"• Сертифицированный платёжный сервис\n\n"
            f"🚧 **Функция в разработке**\n"
            f"Скоро будет доступна оплата российскими рублями.\n\n"
            f"💡 **Пока можно использовать:**\n"
            f"• ⭐ Telegram Stars\n"
            f"• 💎 TON Wallet"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            # [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],  # TODO: uncomment when ready
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"select_package:{package_id}")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer(
            "🚧 Оплата рублями скоро будет доступна!",
            show_alert=True
        )
        
    except Exception as e:
        logger.error(f"❌ Error in pay_with_card: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
