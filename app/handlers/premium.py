"""Premium subscription handlers."""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, Subscription, CoinTransaction

logger = logging.getLogger(__name__)
router = Router()

# Premium tiers
PREMIUM_TIERS = {
    "basic": {
        "name": "Basic",
        "price_ton": 0,
        "price_coins": 0,
        "emoji": "⚪",
        "income_bonus": 0,
        "commission_discount": 0,
        "features": [
            "Стандартный функционал",
            "Обычные медведи",
            "Комиссия 2%",
        ]
    },
    "premium": {
        "name": "Premium",
        "price_ton": 0.1,
        "price_coins": 50000,
        "emoji": "⭐",
        "income_bonus": 0.25,  # +25% к доходу
        "commission_discount": 0.5,  # -50% комиссии (1% вместо 2%)
        "features": [
            "✅ +25% к доходу медведей",
            "✅ Комиссия 1% вместо 2%",
            "✅ Эксклюзивный бейдж ⭐",
            "✅ Приоритетная поддержка",
            "✅ Доступ к редким кейсам",
        ]
    },
    "vip": {
        "name": "VIP",
        "price_ton": 0.5,
        "price_coins": 250000,
        "emoji": "👑",
        "income_bonus": 0.5,  # +50% к доходу
        "commission_discount": 1.0,  # 0% комиссии!
        "features": [
            "✅ +50% к доходу медведей",
            "✅ БЕЗ КОМИССИЙ (0%)!",
            "✅ Эксклюзивный бейдж 👑",
            "✅ VIP поддержка 24/7",
            "✅ Легендарные кейсы",
            "✅ Эксклюзивные медведи",
            "✅ Ранний доступ к новинкам",
        ]
    }
}


async def get_user_tier(user: User) -> str:
    """Get user's current premium tier."""
    if not user.is_premium or not user.premium_until:
        return "basic"
    
    if user.premium_until < datetime.utcnow():
        return "basic"
    
    # Check subscription level
    # For now, premium tier is determined by premium_until existence
    # TODO: Add tier field to User model
    return "premium"  # Default to premium if has active subscription


@router.callback_query(F.data == "premium")
async def premium_menu(query: CallbackQuery):
    """Show premium subscription menu."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            current_tier = await get_user_tier(user)
            tier_info = PREMIUM_TIERS[current_tier]
            
            text = (
                f"⭐ **Premium подписка**\n\n"
                f"💼 **Текущий статус:** {tier_info['emoji']} {tier_info['name']}\n"
            )
            
            if user.is_premium and user.premium_until:
                time_left = user.premium_until - datetime.utcnow()
                if time_left.total_seconds() > 0:
                    days = time_left.days
                    hours = (time_left.total_seconds() % 86400) // 3600
                    text += f"⏰ **Активна до:** {user.premium_until.strftime('%d.%m.%Y')} ({days}д {hours:.0f}ч)\n\n"
                else:
                    text += "⚠️ **Подписка истекла**\n\n"
            else:
                text += "\n"
            
            text += (
                f"🎁 **Преимущества Premium:**\n"
                f"├ ⭐ Premium: +25% доход, комиссия 1%\n"
                f"└ 👑 VIP: +50% доход, БЕЗ КОМИССИЙ!\n\n"
                f"💡 Выбери свой тариф:"
            )
            
            keyboard = []
            
            # Show Premium option if not VIP
            if current_tier != "vip":
                keyboard.append([InlineKeyboardButton(
                    text="⭐ Premium (0.1 TON/месяц)",
                    callback_data="premium_tier_premium"
                )])
            
            # Show VIP option
            if current_tier != "vip":
                keyboard.append([InlineKeyboardButton(
                    text="👑 VIP (0.5 TON/месяц)",
                    callback_data="premium_tier_vip"
                )])
            
            # Show current subscription info
            keyboard.append([InlineKeyboardButton(
                text="ℹ️ Подробнее о тарифах",
                callback_data="premium_info"
            )])
            
            if user.is_premium:
                keyboard.append([InlineKeyboardButton(
                    text="❌ Отменить подписку",
                    callback_data="premium_cancel"
                )])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in premium_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "premium_info")
async def premium_info(query: CallbackQuery):
    """Show detailed premium info."""
    try:
        text = (
            "⭐ **Тарифы Premium**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "⚪ **BASIC (Бесплатно)**\n"
        )
        
        for feature in PREMIUM_TIERS["basic"]["features"]:
            text += f"├ {feature}\n"
        
        text += (
            "\n━━━━━━━━━━━━━━━━━━━━\n"
            "⭐ **PREMIUM (0.1 TON/месяц)**\n"
        )
        
        for feature in PREMIUM_TIERS["premium"]["features"]:
            text += f"├ {feature}\n"
        
        text += (
            "\n━━━━━━━━━━━━━━━━━━━━\n"
            "👑 **VIP (0.5 TON/месяц)**\n"
        )
        
        for feature in PREMIUM_TIERS["vip"]["features"]:
            text += f"├ {feature}\n"
        
        text += (
            "\n💡 **Примеры выгоды:**\n\n"
            "📊 С 10 медведями (1000 к/день):\n"
            "├ Basic: 1000 к/день\n"
            "├ ⭐ Premium: 1250 к/день (+250)\n"
            "└ 👑 VIP: 1500 к/день (+500)\n\n"
            "💸 Экономия на комиссиях:\n"
            "├ Basic: 2% (20к с 1M обмена)\n"
            "├ ⭐ Premium: 1% (10к с 1M)\n"
            "└ 👑 VIP: 0% (0к - БЕЗ КОМИССИЙ!)\n\n"
            "🎯 VIP окупается за ~15 дней!"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Купить Premium", callback_data="premium_tier_premium")],
            [InlineKeyboardButton(text="👑 Купить VIP", callback_data="premium_tier_vip")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="premium")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in premium_info: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("premium_tier_"))
async def premium_tier_select(query: CallbackQuery):
    """Select premium tier to purchase."""
    try:
        tier = query.data.split("_")[-1]  # "premium" or "vip"
        tier_info = PREMIUM_TIERS[tier]
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            text = (
                f"{tier_info['emoji']} **Подписка {tier_info['name']}**\n\n"
                f"💰 **Стоимость:** {tier_info['price_ton']} TON/месяц\n"
                f"💎 Или: {tier_info['price_coins']:,} Coins/месяц\n\n"
                f"🎁 **Преимущества:**\n"
            )
            
            for feature in tier_info["features"]:
                text += f"{feature}\n"
            
            text += (
                f"\n💼 **Ваши балансы:**\n"
                f"├ 💎 TON: {float(user.ton_balance):.4f}\n"
                f"└ 🪙 Coins: {user.coins:,.0f}\n\n"
                f"💡 Выберите способ оплаты:"
            )
            
            keyboard = []
            
            # TON payment
            if float(user.ton_balance) >= tier_info['price_ton']:
                keyboard.append([InlineKeyboardButton(
                    text=f"💎 Оплатить {tier_info['price_ton']} TON",
                    callback_data=f"premium_buy_ton_{tier}"
                )])
            else:
                keyboard.append([InlineKeyboardButton(
                    text=f"❌ Недостаточно TON (нужно {tier_info['price_ton']})",
                    callback_data="noop"
                )])
            
            # Coins payment
            if user.coins >= tier_info['price_coins']:
                keyboard.append([InlineKeyboardButton(
                    text=f"🪙 Оплатить {tier_info['price_coins']:,} Coins",
                    callback_data=f"premium_buy_coins_{tier}"
                )])
            else:
                keyboard.append([InlineKeyboardButton(
                    text=f"❌ Недостаточно Coins (нужно {tier_info['price_coins']:,})",
                    callback_data="noop"
                )])
            
            keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="premium")])
            
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            try:
                await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in premium_tier_select: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("premium_buy_"))
async def premium_buy(query: CallbackQuery):
    """Purchase premium subscription."""
    try:
        parts = query.data.split("_")
        payment_method = parts[2]  # "ton" or "coins"
        tier = parts[3]  # "premium" or "vip"
        
        tier_info = PREMIUM_TIERS[tier]
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Check balance
            if payment_method == "ton":
                cost = tier_info['price_ton']
                if float(user.ton_balance) < cost:
                    await query.answer("❌ Недостаточно TON!", show_alert=True)
                    return
                user.ton_balance -= Decimal(str(cost))
            else:  # coins
                cost = tier_info['price_coins']
                if user.coins < cost:
                    await query.answer("❌ Недостаточно Coins!", show_alert=True)
                    return
                user.coins -= cost
                
                # Log transaction
                transaction = CoinTransaction(
                    user_id=user.id,
                    amount=-cost,
                    transaction_type='premium_subscription',
                    description=f'Подписка {tier_info["name"]} (30 дней)'
                )
                session.add(transaction)
            
            # Activate premium
            now = datetime.utcnow()
            if user.is_premium and user.premium_until and user.premium_until > now:
                # Extend existing subscription
                user.premium_until += timedelta(days=30)
            else:
                # New subscription
                user.is_premium = True
                user.premium_until = now + timedelta(days=30)
            
            # Create subscription record
            subscription = Subscription(
                user_id=user.id,
                tier=tier,
                coins_bonus=tier_info['income_bonus'],
                commission_reduction=tier_info['commission_discount'],
                started_at=now,
                expires_at=user.premium_until,
                auto_renew=False,  # TODO: implement auto-renew
                status='active'
            )
            session.add(subscription)
            
            await session.commit()
            
            text = (
                f"✅ **Подписка активирована!**\n\n"
                f"{tier_info['emoji']} **{tier_info['name']}**\n"
                f"⏰ Действует до: {user.premium_until.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"🎁 **Ваши бонусы:**\n"
            )
            
            for feature in tier_info['features']:
                text += f"{feature}\n"
            
            text += (
                f"\n💼 **Новые балансы:**\n"
                f"├ 💎 TON: {float(user.ton_balance):.4f}\n"
                f"└ 🪙 Coins: {user.coins:,.0f}\n\n"
                f"🎉 Наслаждайтесь Premium возможностями!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🐻 К медведям", callback_data="bears")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("🎉 Подписка активирована!")
            
            logger.info(f"✅ User {user.telegram_id} purchased {tier} subscription")
    
    except Exception as e:
        logger.error(f"❌ Error in premium_buy: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "premium_cancel")
async def premium_cancel(query: CallbackQuery):
    """Cancel premium subscription."""
    try:
        text = (
            "❌ **Отмена подписки**\n\n"
            "⚠️ Вы уверены, что хотите отменить Premium?\n\n"
            "После отмены вы потеряете:\n"
            "├ 📉 Бонусы к доходу\n"
            "├ 💸 Скидки на комиссии\n"
            "├ 🎁 Доступ к эксклюзивному контенту\n"
            "└ ⭐ Premium бейдж\n\n"
            "💡 Подписка останется активной до конца оплаченного периода."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, отменить", callback_data="premium_cancel_confirm")],
            [InlineKeyboardButton(text="❌ Нет, оставить", callback_data="premium")],
        ])
        
        try:
            await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in premium_cancel: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "premium_cancel_confirm")
async def premium_cancel_confirm(query: CallbackQuery):
    """Confirm premium cancellation."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Cancel auto-renewal (subscription will expire naturally)
            subscription_query = select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status == 'active'
            ).order_by(Subscription.created_at.desc())
            subscription_result = await session.execute(subscription_query)
            subscription = subscription_result.scalar_one_or_none()
            
            if subscription:
                subscription.auto_renew = False
                subscription.status = 'cancelled'
                await session.commit()
            
            expires_date = user.premium_until.strftime('%d.%m.%Y') if user.premium_until else "неизвестно"
            
            text = (
                "✅ **Подписка отменена**\n\n"
                f"⏰ Premium будет активен до: {expires_date}\n\n"
                "💡 Вы всегда можете возобновить подписку в разделе Premium!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("Подписка отменена")
            
            logger.info(f"User {user.telegram_id} cancelled premium subscription")
    
    except Exception as e:
        logger.error(f"❌ Error in premium_cancel_confirm: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "noop")
async def noop_handler(query: CallbackQuery):
    """No-op handler for disabled buttons."""
    await query.answer()
