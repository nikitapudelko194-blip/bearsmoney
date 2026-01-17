"""Premium subscription handlers."""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, Subscription, CoinTransaction

logger = logging.getLogger(__name__)
router = Router()

# Premium tiers configuration
PREMIUM_TIERS = {
    "basic": {
        "name": "Базовый",
        "emoji": "⚪",
        "price_ton": 0,
        "price_coins": 0,
        "income_bonus": 0,
        "commission_reduction": 0,
        "features": ["Базовые функции"],
    },
    "premium": {
        "name": "Premium",
        "emoji": "👑",
        "price_ton": 0.1,  # 100 TON -> 0.1 for testing
        "price_coins": 100000,
        "income_bonus": 0.5,  # +50% income
        "commission_reduction": 0.02,  # 0% commission (removes 2%)
        "features": [
            "✨ +50% к доходу от медведей",
            "💸 0% комиссии на обмен и вывод",
            "🎁 Эксклюзивные кейсы",
            "🎯 Приоритетная поддержка",
            "🏆 Специальный бейдж",
        ],
    },
    "vip": {
        "name": "VIP",
        "emoji": "💎",
        "price_ton": 0.5,  # 500 TON -> 0.5 for testing
        "price_coins": 500000,
        "income_bonus": 1.0,  # +100% income (2x)
        "commission_reduction": 0.02,  # 0% commission
        "features": [
            "🚀 +100% к доходу от медведей",
            "💸 0% комиссии на всё",
            "🎉 VIP кейсы с гарантией легенд",
            "⚡ Мгновенный вывод",
            "🎁 Еженедельные бонусы",
            "👑 Эксклюзивные медведи",
            "🏆 VIP бейдж и статус",
        ],
    },
}


async def get_active_subscription(user_id: int, session) -> Subscription | None:
    """
    Get active subscription for user.
    """
    query = (
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == "active",
            Subscription.expires_at > datetime.utcnow(),
        )
        .order_by(Subscription.expires_at.desc())
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


@router.callback_query(F.data == "premium")
async def premium_menu(query: CallbackQuery):
    """
    Show premium subscription menu.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()

            # Get current subscription
            subscription = await get_active_subscription(user.id, session)
            current_tier = subscription.tier if subscription else "basic"

            tier_info = PREMIUM_TIERS[current_tier]

            text = (
                f"⭐ **Premium подписка**\n\n"
                f"💼 **Текущий статус:**\n"
                f"{tier_info['emoji']} **{tier_info['name']}**\n\n"
            )

            if subscription:
                time_left = subscription.expires_at - datetime.utcnow()
                days_left = time_left.days
                hours_left = time_left.seconds // 3600

                text += (
                    f"⏰ **Действует до:**\n"
                    f"{subscription.expires_at.strftime('%d.%m.%Y %H:%M')}\n"
                    f"(осталось: {days_left}д {hours_left}ч)\n\n"
                )

                if subscription.auto_renew:
                    text += "♻️ **Авто-продление:** Включено\n\n"

            text += "🎯 **Доступные тарифы:**\n\n"

            # Show all tiers
            for tier_key, tier in PREMIUM_TIERS.items():
                if tier_key == "basic":
                    continue

                is_current = tier_key == current_tier
                status = " (Текущий)" if is_current else ""

                text += (
                    f"{tier['emoji']} **{tier['name']}{status}**\n"
                    f"💰 Цена: {tier['price_ton']} TON или {tier['price_coins']:,} Coins\n"
                )

                for feature in tier["features"]:
                    text += f"  {feature}\n"

                text += "\n"

            text += (
                "💡 **Преимущества Premium:**\n"
                "• Увеличенный доход\n"
                "• Минимальные комиссии\n"
                "• Эксклюзивный контент\n"
                "• Приоритетная поддержка\n"
            )

            keyboard = []

            # Add upgrade buttons
            if current_tier == "basic":
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            text="👑 Купить Premium", callback_data="buy_premium_premium"
                        )
                    ]
                )
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            text="💎 Купить VIP", callback_data="buy_premium_vip"
                        )
                    ]
                )
            elif current_tier == "premium":
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            text="💎 Улучшить до VIP", callback_data="buy_premium_vip"
                        )
                    ]
                )

            # Add manage button if has subscription
            if subscription:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            text="⚙️ Управление", callback_data="manage_premium"
                        )
                    ]
                )

            keyboard.append(
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
            )

            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

            try:
                await query.message.edit_text(
                    text, reply_markup=reply_markup, parse_mode="markdown"
                )
            except Exception:
                await query.message.answer(
                    text, reply_markup=reply_markup, parse_mode="markdown"
                )

            await query.answer()

    except Exception as e:
        logger.error(f"❌ Error in premium_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("buy_premium_"))
async def buy_premium(query: CallbackQuery):
    """
    Buy premium subscription.
    """
    try:
        tier = query.data.split("_")[-1]  # premium or vip
        tier_info = PREMIUM_TIERS[tier]

        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()

            text = (
                f"💳 **Покупка {tier_info['name']}**\n\n"
                f"{tier_info['emoji']} **{tier_info['name']}**\n"
                f"💰 Цена: {tier_info['price_ton']} TON или {tier_info['price_coins']:,} Coins\n\n"
                f"🎁 **Что вы получите:**\n"
            )

            for feature in tier_info["features"]:
                text += f"{feature}\n"

            text += (
                f"\n💼 **Ваш баланс:**\n"
                f"├ 🪙 Coins: {user.coins:,.0f}\n"
                f"└ 💎 TON: {float(user.ton_balance):.4f}\n\n"
                f"⏰ **Срок:** 30 дней\n\n"
                f"💡 Выберите способ оплаты:"
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        text=f"💎 Оплатить {tier_info['price_ton']} TON",
                        callback_data=f"confirm_premium_ton_{tier}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"🪙 Оплатить {tier_info['price_coins']:,} Coins",
                        callback_data=f"confirm_premium_coins_{tier}",
                    )
                ],
                [InlineKeyboardButton(text="❌ Отмена", callback_data="premium")],
            ]

            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

            try:
                await query.message.edit_text(
                    text, reply_markup=reply_markup, parse_mode="markdown"
                )
            except Exception:
                await query.message.answer(
                    text, reply_markup=reply_markup, parse_mode="markdown"
                )

            await query.answer()

    except Exception as e:
        logger.error(f"❌ Error in buy_premium: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("confirm_premium_"))
async def confirm_premium_purchase(query: CallbackQuery):
    """
    Confirm premium purchase.
    """
    try:
        parts = query.data.split("_")
        payment_method = parts[2]  # ton or coins
        tier = parts[3]  # premium or vip

        tier_info = PREMIUM_TIERS[tier]

        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()

            # Check balance
            if payment_method == "ton":
                price = Decimal(str(tier_info["price_ton"]))
                if user.ton_balance < price:
                    await query.answer(
                        f"❌ Недостаточно TON! Нужно: {float(price):.4f}",
                        show_alert=True,
                    )
                    return
                user.ton_balance -= price
            else:  # coins
                price = tier_info["price_coins"]
                if user.coins < price:
                    await query.answer(
                        f"❌ Недостаточно Coins! Нужно: {price:,}", show_alert=True
                    )
                    return
                user.coins -= price

                # Log transaction
                transaction = CoinTransaction(
                    user_id=user.id,
                    amount=-price,
                    transaction_type="premium_purchase",
                    description=f"Покупка {tier_info['name']} подписки",
                )
                session.add(transaction)

            # Create or update subscription
            subscription = await get_active_subscription(user.id, session)

            if subscription:
                # Extend existing subscription
                subscription.tier = tier
                subscription.expires_at += timedelta(days=30)
            else:
                # Create new subscription
                subscription = Subscription(
                    user_id=user.id,
                    tier=tier,
                    coins_bonus=tier_info["income_bonus"],
                    commission_reduction=tier_info["commission_reduction"],
                    started_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=30),
                    status="active",
                    auto_renew=False,
                )
                session.add(subscription)

            # Update user premium status
            user.is_premium = True
            user.premium_until = subscription.expires_at

            await session.commit()

            # Success message
            text = (
                f"✅ **Поздравляем!**\n\n"
                f"{tier_info['emoji']} Вы приобрели **{tier_info['name']}**!\n\n"
                f"🎉 **Ваши преимущества:**\n"
            )

            for feature in tier_info["features"]:
                text += f"{feature}\n"

            text += (
                f"\n⏰ **Действует до:**\n"
                f"{subscription.expires_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"💡 Теперь вы получаете больше дохода от медведей!"
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🎉 Отлично!", callback_data="main_menu"
                        )
                    ],
                ]
            )

            try:
                await query.message.edit_text(
                    text, reply_markup=keyboard, parse_mode="markdown"
                )
            except Exception:
                await query.message.answer(
                    text, reply_markup=keyboard, parse_mode="markdown"
                )

            await query.answer("🎉 Поздравляем!")

            logger.info(
                f"✅ User {user.telegram_id} purchased {tier} subscription via {payment_method}"
            )

    except Exception as e:
        logger.error(f"❌ Error in confirm_premium_purchase: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "manage_premium")
async def manage_premium(query: CallbackQuery):
    """
    Manage premium subscription.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()

            subscription = await get_active_subscription(user.id, session)

            if not subscription:
                await query.answer("❌ У вас нет активной подписки", show_alert=True)
                return

            tier_info = PREMIUM_TIERS[subscription.tier]
            time_left = subscription.expires_at - datetime.utcnow()

            text = (
                f"⚙️ **Управление подпиской**\n\n"
                f"{tier_info['emoji']} **{tier_info['name']}**\n\n"
                f"⏰ **Действует до:**\n"
                f"{subscription.expires_at.strftime('%d.%m.%Y %H:%M')}\n"
                f"(осталось: {time_left.days}д {time_left.seconds // 3600}ч)\n\n"
            )

            if subscription.auto_renew:
                text += "♻️ **Авто-продление:** Включено\n"
                auto_renew_text = "❌ Выключить авто-продление"
                auto_renew_data = "toggle_auto_renew_off"
            else:
                text += "🚫 **Авто-продление:** Выключено\n"
                auto_renew_text = "✅ Включить авто-продление"
                auto_renew_data = "toggle_auto_renew_on"

            keyboard = [
                [InlineKeyboardButton(text=auto_renew_text, callback_data=auto_renew_data)],
                [
                    InlineKeyboardButton(
                        text="🔄 Продлить подписку", callback_data=f"renew_premium_{subscription.tier}"
                    )
                ],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="premium")],
            ]

            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

            try:
                await query.message.edit_text(
                    text, reply_markup=reply_markup, parse_mode="markdown"
                )
            except Exception:
                await query.message.answer(
                    text, reply_markup=reply_markup, parse_mode="markdown"
                )

            await query.answer()

    except Exception as e:
        logger.error(f"❌ Error in manage_premium: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("toggle_auto_renew_"))
async def toggle_auto_renew(query: CallbackQuery):
    """
    Toggle auto-renewal.
    """
    try:
        action = query.data.split("_")[-1]  # on or off

        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()

            subscription = await get_active_subscription(user.id, session)

            if not subscription:
                await query.answer("❌ У вас нет активной подписки", show_alert=True)
                return

            subscription.auto_renew = action == "on"
            await session.commit()

            status = "Включено" if subscription.auto_renew else "Выключено"
            await query.answer(f"✅ Авто-продление: {status}")

            # Refresh manage premium view
            await manage_premium(query)

    except Exception as e:
        logger.error(f"❌ Error in toggle_auto_renew: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
