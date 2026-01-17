"""Payment handlers for TON and Coins purchases."""
import logging
from decimal import Decimal
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, CoinTransaction
from config import settings
import hashlib

logger = logging.getLogger(__name__)
router = Router()

# ADMIN ID - замените на ваш Telegram ID
ADMIN_ID = 810540896  # TODO: Замените на свой ID!

# TON packages with prices
TON_PACKAGES = {
    'package_0.5': {
        'ton_amount': 0.5,
        'stars': 200,
        'rub': 250,
        'ton_crypto': 0.5,
        'name': '0.5 TON',
        'emoji': '🪙'
    },
    'package_1.0': {
        'ton_amount': 1.0,
        'stars': 400,
        'rub': 500,
        'ton_crypto': 1.0,
        'name': '1.0 TON',
        'emoji': '💎'
    },
    'package_2.5': {
        'ton_amount': 2.5,
        'stars': 1000,
        'rub': 1250,
        'ton_crypto': 2.5,
        'name': '2.5 TON',
        'emoji': '💎💎'
    },
    'package_5.0': {
        'ton_amount': 5.0,
        'stars': 2000,
        'rub': 2500,
        'ton_crypto': 5.0,
        'name': '5.0 TON',
        'emoji': '💠'
    },
    'package_10.0': {
        'ton_amount': 10.0,
        'stars': 4000,
        'rub': 5000,
        'ton_crypto': 10.0,
        'name': '10.0 TON',
        'emoji': '💰'
    },
}

# Coins packages with prices (1 Star = 5 Coins)
COINS_PACKAGES = {
    'coins_1k': {
        'coins_amount': 500,
        'stars': 100,
        'name': '500 Coins',
        'emoji': '🪙'
    },
    'coins_5k': {
        'coins_amount': 2500,
        'stars': 500,
        'name': '2,500 Coins',
        'emoji': '💰'
    },
    'coins_10k': {
        'coins_amount': 5000,
        'stars': 1000,
        'name': '5,000 Coins',
        'emoji': '💵'
    },
    'coins_25k': {
        'coins_amount': 10000,
        'stars': 2500,
        'name': '10,000 Coins',
        'emoji': '💸'
    },
    'coins_50k': {
        'coins_amount': 25000,
        'stars': 5000,
        'name': '25,000 Coins',
        'emoji': '🤑'
    },
}

# Coins packages for TON - SYNCHRONIZED WITH STARS RATE (1 TON = 1,000 Coins)
COINS_TON_PACKAGES = {
    'coins_ton_100k': {
        'coins_amount': 200,
        'ton_amount': 0.2,
        'name': '200 Coins',
        'emoji': '💰'
    },
    'coins_ton_250k': {
        'coins_amount': 500,
        'ton_amount': 0.5,
        'name': '500 Coins',
        'emoji': '💵'
    },
    'coins_ton_500k': {
        'coins_amount': 1000,
        'ton_amount': 1.0,
        'name': '1,000 Coins',
        'emoji': '💸'
    },
    'coins_ton_1250k': {
        'coins_amount': 2500,
        'ton_amount': 2.5,
        'name': '2,500 Coins',
        'emoji': '🤑'
    },
    'coins_ton_2500k': {
        'coins_amount': 5000,
        'ton_amount': 5.0,
        'name': '5,000 Coins',
        'emoji': '💎'
    },
}

# Temporary storage for pending TON payments
# В продакшене лучше использовать Redis или базу данных
pending_ton_payments = {}


class PaymentStates(StatesGroup):
    """States for payment flow."""
    waiting_for_ton_address = State()


# ============ MAIN PAYMENT MENU ============

@router.callback_query(F.data == "payments")
async def payments_menu(query: CallbackQuery):
    """
    Main payments menu - choose what to buy.
    """
    try:
        text = (
            f"💳 **Магазин**\n\n"
            f"💎 **TON** - игровая валюта для премиум функций\n"
            f"• Открытие премиум кейсов\n"
            f"• Особые возможности\n\n"
            f"🪙 **Coins** - основная валюта\n"
            f"• Покупка медведей\n"
            f"• Улучшение уровней\n"
            f"• Ускорения\n\n"
            f"👇 **Выберите что купить:**"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Купить TON", callback_data="buy_ton")],
            [InlineKeyboardButton(text="🪙 Купить Coins", callback_data="buy_coins")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in payments_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============ TON PURCHASE ============

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
                f"💎 **Купить TON**\n\n"
                f"💼 **Ваш баланс**\n"
                f"└ 💎 TON: {float(user.ton_balance):.4f}\n\n"
                f"💎 **Выберите пакет:**\n\n"
                f"🪙 **0.5 TON** - 200 ⭐ / 250₽\n"
                f"💎 **1.0 TON** - 400 ⭐ / 500₽\n"
                f"💎💎 **2.5 TON** - 1,000 ⭐ / 1,250₽\n"
                f"💠 **5.0 TON** - 2,000 ⭐ / 2,500₽\n"
                f"💰 **10.0 TON** - 4,000 ⭐ / 5,000₽\n\n"
                f"💡 Выберите пакет для продолжения:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🪙 0.5 TON", callback_data="select_package:package_0.5")],
                [InlineKeyboardButton(text="💎 1.0 TON", callback_data="select_package:package_1.0")],
                [InlineKeyboardButton(text="💎💎 2.5 TON", callback_data="select_package:package_2.5")],
                [InlineKeyboardButton(text="💠 5.0 TON", callback_data="select_package:package_5.0")],
                [InlineKeyboardButton(text="💰 10.0 TON", callback_data="select_package:package_10.0")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="payments")],
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
            f"⭐ **Telegram Stars** - {package['stars']:,} Stars\n"
            f"• Оплата внутри Telegram\n"
            f"• Мгновенное зачисление\n\n"
            f"💎 **TON Wallet** - {package['ton_crypto']} TON\n"
            f"• Оплата криптовалютой\n"
            f"• Подтверждение администратором\n\n"
            f"💳 **Банковская карта** - {package['rub']}₽\n"
            f"• Оплата российскими рублями\n"
            f"• Зачисление 1-2 мин"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ {package['stars']:,} Stars", callback_data=f"pay_stars:{package_id}")],
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


# ============ TELEGRAM STARS PAYMENT (TON) ============

@router.callback_query(F.data.startswith("pay_stars:"))
async def pay_with_stars(query: CallbackQuery):
    """
    Create Telegram Stars invoice for TON.
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
    Handle successful payment (TON or Coins).
    """
    try:
        payload = message.successful_payment.invoice_payload
        parts = payload.split("_")
        
        if len(parts) < 4:
            logger.error(f"Invalid payload: {payload}")
            return
        
        payment_type = parts[0]  # 'ton' or 'coins'
        payment_method = parts[1]  # 'stars'
        
        if payment_type == "ton":
            await process_ton_stars_payment(message, payload)
        elif payment_type == "coins":
            await process_coins_stars_payment(message, payload)
        else:
            logger.error(f"Unknown payment type: {payment_type}")
            
    except Exception as e:
        logger.error(f"❌ Error in process_successful_payment: {e}", exc_info=True)


async def process_ton_stars_payment(message: Message, payload: str):
    """
    Process TON purchase via Stars.
    """
    try:
        # Parse payload: ton_stars_package_0.5_123456789
        parts = payload.split("_")
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
            user.ton_balance += Decimal(str(ton_amount))
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=ton_amount,
                transaction_type='purchase_stars',
                description=f'Покупка {package["name"]} за {package["stars"]:,} Stars (+{ton_amount} TON)'
            )
            session.add(transaction)
            await session.commit()
            
            # Success message
            text = (
                f"✅ **Платёж успешен!**\n\n"
                f"💎 **Начислено:** {ton_amount} TON\n"
                f"⭐ **Оплачено:** {package['stars']:,} Stars\n\n"
                f"💼 **Новый баланс:** {float(user.ton_balance):.4f} TON\n\n"
                f"🎉 Спасибо за покупку!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎰 Открыть кейсы", callback_data="cases")],
                [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            logger.info(f"✅ TON Payment: User {user_id} purchased {ton_amount} TON for {package['stars']:,} Stars")
            
    except Exception as e:
        logger.error(f"❌ Error in process_ton_stars_payment: {e}", exc_info=True)


# ============ TON WALLET PAYMENT WITH ADMIN CONFIRMATION ============

@router.callback_query(F.data.startswith("pay_ton:"))
async def pay_with_ton_wallet(query: CallbackQuery):
    """
    Pay with TON cryptocurrency - manual confirmation.
    """
    try:
        package_id = query.data.split(":")[1]
        
        if package_id not in TON_PACKAGES:
            await query.answer("❌ Неизвестный пакет", show_alert=True)
            return
        
        package = TON_PACKAGES[package_id]
        deposit_address = "UQBLaN9mzDOTceNlEGqo5JCjjWi8deYPYddGFzG_CqF4zXXg"
        payment_memo = f"USER_{query.from_user.id}_{package_id}"
        
        # Save to pending payments
        payment_id = f"{query.from_user.id}_{int(datetime.now().timestamp())}"
        pending_ton_payments[payment_id] = {
            'user_id': query.from_user.id,
            'package_id': package_id,
            'ton_amount': package['ton_crypto'],
            'status': 'pending',
            'created_at': datetime.now()
        }
        
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
            f"• После отправки нажмите кнопку ниже\n\n"
            f"🔍 **Статус:** Ожидаем платёж...\n\n"
            f"👇 После отправки TON нажмите кнопку:"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить платёж", callback_data=f"confirm_ton:{payment_id}")],
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


@router.callback_query(F.data.startswith("confirm_ton:"))
async def confirm_ton_payment(query: CallbackQuery):
    """
    User confirms they sent TON - notify admin.
    """
    try:
        payment_id = query.data.split(":")[1]
        
        if payment_id not in pending_ton_payments:
            await query.answer("❌ Платёж не найден", show_alert=True)
            return
        
        payment = pending_ton_payments[payment_id]
        
        if payment['status'] != 'pending':
            await query.answer("⚠️ Этот платёж уже обработан", show_alert=True)
            return
        
        # Update status
        payment['status'] = 'waiting_confirmation'
        
        # Get user info
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == payment['user_id'])
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            package = TON_PACKAGES[payment['package_id']]
            
            # Notify admin
            admin_text = (
                f"🔔 **Новый платёж TON**\n\n"
                f"👤 **Пользователь:** {user.first_name}\n"
                f"🆔 **ID:** `{user.telegram_id}`\n"
                f"📦 **Пакет:** {package['name']}\n"
                f"💎 **Сумма:** {package['ton_crypto']} TON\n\n"
                f"📝 **Комментарий:**\n"
                f"`USER_{user.telegram_id}_{payment['package_id']}`\n\n"
                f"⏰ **Время:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"💳 **Проверьте транзакцию и подтвердите:**"
            )
            
            admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_approve:{payment_id}")],
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject:{payment_id}")],
            ])
            
            # Try to send to admin with better error handling
            admin_notified = False
            error_message = ""
            
            try:
                logger.info(f"📤 Attempting to send admin notification to {ADMIN_ID}")
                await query.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=admin_text,
                    reply_markup=admin_keyboard,
                    parse_mode="markdown"
                )
                admin_notified = True
                logger.info(f"✅ Admin notification sent successfully to {ADMIN_ID}")
            except TelegramForbiddenError as e:
                error_message = f"Админ заблокировал бота (ID: {ADMIN_ID})"
                logger.error(f"❌ Admin blocked the bot: {e}")
            except TelegramBadRequest as e:
                error_message = f"Неверный ID админа или бот не может отправить сообщение (ID: {ADMIN_ID})"
                logger.error(f"❌ Bad request to admin: {e}")
            except Exception as e:
                error_message = f"Ошибка отправки админу: {str(e)}"
                logger.error(f"❌ Failed to notify admin: {e}", exc_info=True)
            
            # Notify user
            if admin_notified:
                user_text = (
                    f"✅ **Заявка отправлена!**\n\n"
                    f"💎 Ваша заявка на пополнение {package['name']} отправлена администратору.\n\n"
                    f"⏳ Платёж будет проверен в течение нескольких минут.\n"
                    f"🔔 Вы получите уведомление после проверки.\n\n"
                    f"Спасибо за ожидание!"
                )
                await query.message.edit_text(user_text, parse_mode="markdown")
                await query.answer("✅ Заявка отправлена администратору!")
            else:
                # Admin notification failed - inform user
                user_text = (
                    f"⚠️ **Заявка создана, но есть проблема**\n\n"
                    f"💎 Пакет: {package['name']}\n"
                    f"💵 Сумма: {package['ton_crypto']} TON\n\n"
                    f"❌ **Проблема:**\n"
                    f"{error_message}\n\n"
                    f"📝 **Ваш Payment ID:**\n"
                    f"`{payment_id}`\n\n"
                    f"💡 **Что делать:**\n"
                    f"1. Сохраните Payment ID\n"
                    f"2. Обратитесь в поддержку\n"
                    f"3. Укажите этот ID и скриншот перевода\n\n"
                    f"⚙️ Админ ID в настройках: `{ADMIN_ID}`"
                )
                await query.message.edit_text(user_text, parse_mode="markdown")
                await query.answer(
                    f"⚠️ Проблема с уведомлением админа! Обратитесь в поддержку. ID: {payment_id}",
                    show_alert=True
                )
                logger.error(
                    f"❌ ADMIN NOTIFICATION FAILED! "
                    f"Payment ID: {payment_id}, "
                    f"User: {user.telegram_id}, "
                    f"Admin ID: {ADMIN_ID}, "
                    f"Error: {error_message}"
                )
            
    except Exception as e:
        logger.error(f"❌ Error in confirm_ton_payment: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("admin_approve:"))
async def admin_approve_payment(query: CallbackQuery):
    """
    Admin approves TON payment.
    """
    try:
        payment_id = query.data.split(":")[1]
        
        if payment_id not in pending_ton_payments:
            await query.answer("❌ Платёж не найден", show_alert=True)
            return
        
        payment = pending_ton_payments[payment_id]
        
        if payment['status'] == 'approved':
            await query.answer("✅ Платёж уже одобрен", show_alert=True)
            return
        
        # Credit TON to user
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == payment['user_id'])
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                await query.answer("❌ Пользователь не найден", show_alert=True)
                return
            
            package = TON_PACKAGES[payment['package_id']]
            ton_amount = payment['ton_amount']
            
            # Add TON
            user.ton_balance += Decimal(str(ton_amount))
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=ton_amount,
                transaction_type='purchase_ton_wallet',
                description=f'Покупка {package["name"]} через TON Wallet (+{ton_amount} TON)'
            )
            session.add(transaction)
            await session.commit()
            
            # Update status
            payment['status'] = 'approved'
            
            # Notify user
            user_text = (
                f"✅ **Платёж подтверждён!**\n\n"
                f"💎 **Начислено:** {ton_amount} TON\n"
                f"💼 **Новый баланс:** {float(user.ton_balance):.4f} TON\n\n"
                f"🎉 Спасибо за покупку!"
            )
            
            user_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎰 Открыть кейсы", callback_data="cases")],
                [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
            ])
            
            try:
                await query.bot.send_message(
                    chat_id=payment['user_id'],
                    text=user_text,
                    reply_markup=user_keyboard,
                    parse_mode="markdown"
                )
            except Exception as e:
                logger.error(f"Failed to notify user: {e}")
            
            # Update admin message
            await query.message.edit_text(
                f"{query.message.text}\n\n✅ **ОДОБРЕНО** @{query.from_user.username or 'admin'}",
                parse_mode="markdown"
            )
            
            await query.answer("✅ Платёж одобрен! TON начислен пользователю.")
            logger.info(f"✅ Admin approved TON payment: {payment_id}")
            
    except Exception as e:
        logger.error(f"❌ Error in admin_approve_payment: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject_payment(query: CallbackQuery):
    """
    Admin rejects TON payment.
    """
    try:
        payment_id = query.data.split(":")[1]
        
        if payment_id not in pending_ton_payments:
            await query.answer("❌ Платёж не найден", show_alert=True)
            return
        
        payment = pending_ton_payments[payment_id]
        
        if payment['status'] == 'rejected':
            await query.answer("❌ Платёж уже отклонён", show_alert=True)
            return
        
        # Update status
        payment['status'] = 'rejected'
        
        # Notify user
        user_text = (
            f"❌ **Платёж отклонён**\n\n"
            f"К сожалению, ваш платёж не был подтверждён.\n\n"
            f"Возможные причины:\n"
            f"• Неверная сумма\n"
            f"• Отсутствие комментария\n"
            f"• Неверный адрес\n\n"
            f"Пожалуйста, попробуйте ещё раз или обратитесь в поддержку."
        )
        
        try:
            await query.bot.send_message(
                chat_id=payment['user_id'],
                text=user_text,
                parse_mode="markdown"
            )
        except Exception as e:
            logger.error(f"Failed to notify user: {e}")
        
        # Update admin message
        await query.message.edit_text(
            f"{query.message.text}\n\n❌ **ОТКЛОНЕНО** @{query.from_user.username or 'admin'}",
            parse_mode="markdown"
        )
        
        await query.answer("❌ Платёж отклонён. Пользователь уведомлён.")
        logger.info(f"❌ Admin rejected TON payment: {payment_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in admin_reject_payment: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# ============ COINS PURCHASE ============

@router.callback_query(F.data == "buy_coins")
async def buy_coins_menu(query: CallbackQuery):
    """
    Show Coins purchase menu with packages.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            text = (
                f"🪙 **Купить Coins**\n\n"
                f"💼 **Ваш баланс**\n"
                f"├ 🪙 Coins: {user.coins:,.0f}\n"
                f"└ 💎 TON: {float(user.ton_balance):.4f}\n\n"
                f"💡 **Выберите способ покупки:**"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Купить за Stars", callback_data="buy_coins_stars")],
                [InlineKeyboardButton(text="💎 Купить за TON", callback_data="buy_coins_ton")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="payments")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in buy_coins_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "buy_coins_stars")
async def buy_coins_stars_menu(query: CallbackQuery):
    """
    Show Coins packages for Stars.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            text = (
                f"⭐ **Купить Coins за Stars**\n\n"
                f"💼 **Ваш баланс**\n"
                f"└ 🪙 Coins: {user.coins:,.0f}\n\n"
                f"💰 **Выберите пакет:**\n\n"
                f"🪙 **500 Coins** - 100 ⭐\n"
                f"💰 **2,500 Coins** - 500 ⭐\n"
                f"💵 **5,000 Coins** - 1,000 ⭐\n"
                f"💸 **10,000 Coins** - 2,500 ⭐\n"
                f"🤑 **25,000 Coins** - 5,000 ⭐\n\n"
                f"💡 1 Star = 5 Coins\n\n"
                f"👇 Выберите пакет:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🪙 500 Coins", callback_data="select_coins:coins_1k")],
                [InlineKeyboardButton(text="💰 2,500 Coins", callback_data="select_coins:coins_5k")],
                [InlineKeyboardButton(text="💵 5,000 Coins", callback_data="select_coins:coins_10k")],
                [InlineKeyboardButton(text="💸 10,000 Coins", callback_data="select_coins:coins_25k")],
                [InlineKeyboardButton(text="🤑 25,000 Coins", callback_data="select_coins:coins_50k")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_coins")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in buy_coins_stars_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "buy_coins_ton")
async def buy_coins_ton_menu(query: CallbackQuery):
    """
    Show Coins packages for TON.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            text = (
                f"💎 **Купить Coins за TON**\n\n"
                f"💼 **Ваш баланс**\n"
                f"├ 🪙 Coins: {user.coins:,.0f}\n"
                f"└ 💎 TON: {float(user.ton_balance):.4f}\n\n"
                f"📈 **Курс:** 1 TON = 1,000 Coins\n\n"
                f"💰 **Выберите пакет:**\n\n"
                f"💰 **200 Coins** - 0.2 TON\n"
                f"💵 **500 Coins** - 0.5 TON\n"
                f"💸 **1,000 Coins** - 1.0 TON\n"
                f"🤑 **2,500 Coins** - 2.5 TON\n"
                f"💎 **5,000 Coins** - 5.0 TON\n\n"
                f"👇 Выберите пакет:"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💰 200 Coins", callback_data="select_coins_ton:coins_ton_100k")],
                [InlineKeyboardButton(text="💵 500 Coins", callback_data="select_coins_ton:coins_ton_250k")],
                [InlineKeyboardButton(text="💸 1,000 Coins", callback_data="select_coins_ton:coins_ton_500k")],
                [InlineKeyboardButton(text="🤑 2,500 Coins", callback_data="select_coins_ton:coins_ton_1250k")],
                [InlineKeyboardButton(text="💎 5,000 Coins", callback_data="select_coins_ton:coins_ton_2500k")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_coins")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in buy_coins_ton_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("select_coins:"))
async def select_coins_package(query: CallbackQuery):
    """
    Show confirmation for Coins package (Stars).
    """
    try:
        package_id = query.data.split(":")[1]
        
        if package_id not in COINS_PACKAGES:
            await query.answer("❌ Неизвестный пакет", show_alert=True)
            return
        
        package = COINS_PACKAGES[package_id]
        
        text = (
            f"{package['emoji']} **Пакет: {package['name']}**\n\n"
            f"🪙 Получите: **{package['coins_amount']:,} Coins**\n"
            f"⭐ Стоимость: **{package['stars']:,} Stars**\n\n"
            f"💳 **Способ оплаты:**\n"
            f"• Telegram Stars\n"
            f"• Мгновенное зачисление\n\n"
            f"👇 Нажмите для оплаты:"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ Оплатить {package['stars']:,} Stars", callback_data=f"pay_coins_stars:{package_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_coins_stars")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    except Exception as e:
        logger.error(f"❌ Error in select_coins_package: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("select_coins_ton:"))
async def select_coins_ton_package(query: CallbackQuery):
    """
    Show confirmation for Coins package (TON).
    """
    try:
        package_id = query.data.split(":")[1]
        
        if package_id not in COINS_TON_PACKAGES:
            await query.answer("❌ Неизвестный пакет", show_alert=True)
            return
        
        package = COINS_TON_PACKAGES[package_id]
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Check balance
            ton_amount_decimal = Decimal(str(package['ton_amount']))
            has_balance = user.ton_balance >= ton_amount_decimal
            
            text = (
                f"{package['emoji']} **Пакет: {package['name']}**\n\n"
                f"🪙 Получите: **{package['coins_amount']:,} Coins**\n"
                f"💎 Стоимость: **{package['ton_amount']} TON**\n\n"
                f"💼 **Ваш баланс:** {float(user.ton_balance):.4f} TON\n"
                f"💼 **Останется:** {float(user.ton_balance - ton_amount_decimal):.4f} TON\n\n"
            )
            
            if has_balance:
                text += (
                    f"✅ **У вас достаточно TON**\n\n"
                    f"💳 **Способ оплаты:**\n"
                    f"• С баланса TON\n"
                    f"• Мгновенное зачисление\n\n"
                    f"👇 Подтвердите покупку:"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"✅ Купить за {package['ton_amount']} TON", callback_data=f"confirm_coins_ton:{package_id}")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_coins_ton")],
                ])
            else:
                needed = float(ton_amount_decimal - user.ton_balance)
                text += (
                    f"❌ **Недостаточно TON**\n\n"
                    f"Нужно ещё: {needed:.4f} TON\n\n"
                    f"💡 Пополните баланс TON:"
                )
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💎 Купить TON", callback_data="buy_ton")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="buy_coins_ton")],
                ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            if not has_balance:
                await query.answer(f"❌ Недостаточно TON. Нужно ещё {needed:.4f} TON", show_alert=True)
            else:
                await query.answer()
            
    except Exception as e:
        logger.error(f"❌ Error in select_coins_ton_package: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("confirm_coins_ton:"))
async def confirm_coins_ton_purchase(query: CallbackQuery):
    """
    Confirm and execute Coins purchase with TON.
    """
    try:
        package_id = query.data.split(":")[1]
        
        if package_id not in COINS_TON_PACKAGES:
            await query.answer("❌ Неизвестный пакет", show_alert=True)
            return
        
        package = COINS_TON_PACKAGES[package_id]
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            ton_amount_decimal = Decimal(str(package['ton_amount']))
            
            # Double-check balance
            if user.ton_balance < ton_amount_decimal:
                await query.answer("❌ Недостаточно TON", show_alert=True)
                return
            
            # Execute purchase
            user.ton_balance -= ton_amount_decimal
            user.coins += package['coins_amount']
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=package['coins_amount'],
                transaction_type='purchase_ton_balance',
                description=f'Покупка {package["name"]} за {package["ton_amount"]} TON (+{package["coins_amount"]:,} Coins)'
            )
            session.add(transaction)
            await session.commit()
            
            # Success message
            text = (
                f"✅ **Покупка успешна!**\n\n"
                f"🪙 **Начислено:** {package['coins_amount']:,} Coins\n"
                f"💎 **Оплачено:** {package['ton_amount']} TON\n\n"
                f"💼 **Новые балансы**\n"
                f"├ 🪙 Coins: {user.coins:,.0f}\n"
                f"└ 💎 TON: {float(user.ton_balance):.4f}\n\n"
                f"🎉 Спасибо за покупку!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🐻 Купить медведей", callback_data="bears")],
                [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("✅ Coins начислены!")
            logger.info(f"✅ Coins Purchase: User {user.telegram_id} bought {package['coins_amount']:,} Coins for {package['ton_amount']} TON")
            
    except Exception as e:
        logger.error(f"❌ Error in confirm_coins_ton_purchase: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("pay_coins_stars:"))
async def pay_coins_with_stars(query: CallbackQuery):
    """
    Create Telegram Stars invoice for Coins.
    """
    try:
        package_id = query.data.split(":")[1]
        
        if package_id not in COINS_PACKAGES:
            await query.answer("❌ Неизвестный пакет", show_alert=True)
            return
        
        package = COINS_PACKAGES[package_id]
        
        # Create invoice
        prices = [LabeledPrice(label=package['name'], amount=package['stars'])]
        
        await query.bot.send_invoice(
            chat_id=query.from_user.id,
            title=f"Покупка {package['name']}",
            description=f"Пополнение баланса на {package['coins_amount']:,} Coins",
            payload=f"coins_stars_{package_id}_{query.from_user.id}",
            provider_token="",  # Empty for Telegram Stars
            currency="XTR",
            prices=prices,
            max_tip_amount=0,
            suggested_tip_amounts=[],
        )
        
        await query.answer("💳 Инвойс отправлен!")
        
    except Exception as e:
        logger.error(f"❌ Error in pay_coins_with_stars: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


async def process_coins_stars_payment(message: Message, payload: str):
    """
    Process Coins purchase via Stars.
    """
    try:
        # Parse payload: coins_stars_coins_1k_123456789
        parts = payload.split("_")
        package_id = f"{parts[2]}_{parts[3]}"
        user_id = int(parts[4])
        
        if package_id not in COINS_PACKAGES:
            logger.error(f"Unknown package: {package_id}")
            return
        
        package = COINS_PACKAGES[package_id]
        coins_amount = package['coins_amount']
        
        # Credit Coins to user
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == user_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User not found: {user_id}")
                return
            
            # Add Coins
            user.coins += coins_amount
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=coins_amount,
                transaction_type='purchase_stars',
                description=f'Покупка {package["name"]} за {package["stars"]:,} Stars (+{coins_amount:,} Coins)'
            )
            session.add(transaction)
            await session.commit()
            
            # Success message
            text = (
                f"✅ **Платёж успешен!**\n\n"
                f"🪙 **Начислено:** {coins_amount:,} Coins\n"
                f"⭐ **Оплачено:** {package['stars']:,} Stars\n\n"
                f"💼 **Новый баланс:** {user.coins:,.0f} Coins\n\n"
                f"🎉 Спасибо за покупку!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🐻 Купить медведей", callback_data="bears")],
                [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            logger.info(f"✅ Coins Payment: User {user_id} purchased {coins_amount:,} Coins for {package['stars']:,} Stars")
            
    except Exception as e:
        logger.error(f"❌ Error in process_coins_stars_payment: {e}", exc_info=True)


# ============ BANK CARD PAYMENT (YOOKASSA) - PLACEHOLDER ============

@router.callback_query(F.data.startswith("pay_rub:"))
async def pay_with_card(query: CallbackQuery):
    """
    Pay with bank card (rubles via YooKassa) - coming soon.
    """
    try:
        package_id = query.data.split(":")[1]
        
        if package_id not in TON_PACKAGES:
            await query.answer("❌ Неизвестный пакет", show_alert=True)
            return
        
        package = TON_PACKAGES[package_id]
        
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
