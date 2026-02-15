"""Premium subscription handlers."""
import logging
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.db import get_session
from app.database.models import User, Subscription, CoinTransaction
from decimal import Decimal

logger = logging.getLogger(__name__)
router = Router()

# Subscription tiers
PREMIUM_TIERS = {
    "free": {
        "name": "🆓 Free",
        "price": 0,
        "benefits": [
            "✅ Базовые медведи",
            "✅ Стандартный доход",
            "✅ Комиссия обмена 5%",
            "✅ Реферальная система"
        ],
        "income_bonus": 0,
        "fee_discount": 0,
    },
    "premium": {
        "name": "⭐ Premium",
        "price": 0.1,  # 0.1 TON per month
        "benefits": [
            "✅ Все медведи Free",
            "🎁 +50% к доходу медведей",
            "💎 0% комиссии обмена",
            "🎯 Эксклюзивные кейсы",
            "👥 +10% реферальные бонусы",
            "🎨 Premium бейдж в профиле"
        ],
        "income_bonus": 0.5,
        "fee_discount": 1.0,
    },
    "vip": {
        "name": "👑 VIP",
        "price": 0.5,  # 0.5 TON per month
        "benefits": [
            "✅ Все медведи Premium",
            "🎁 +100% к доходу медведей",
            "💎 0% комиссии обмена",
            "🎯 VIP эксклюзивные кейсы",
            "👥 +20% реферальные бонусы",
            "🎨 VIP бейдж в профиле",
            "🚀 Приоритетная поддержка",
            "🎰 3 спина колеса/день",
            "🏆 Доступ к VIP турнирам"
        ],
        "income_bonus": 1.0,
        "fee_discount": 1.0,
    }
}


def get_user_tier(user: User) -> str:
    """Get user subscription tier."""
    if not user.is_premium:
        return "free"
    
    # Check if premium is still valid
    if user.premium_until and user.premium_until < datetime.utcnow():
        return "free"
    
    # Get subscription to check tier
    # Default to premium for now
    return "premium"


@router.callback_query(F.data == "premium")
async def premium_menu(query: CallbackQuery):
    """Show premium subscription menu."""
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            current_tier = get_user_tier(user)
            
            text = (
                f"⭐ **Premium подписка**\n\n"
                f"💼 **Текущий статус:** {PREMIUM_TIERS[current_tier]['name']}\n"
            )
            
            if user.is_premium and user.premium_until:
                time_left = user.premium_until - datetime.utcnow()
                if time_left.total_seconds() > 0:
                    days = time_left.days
                    hours = (time_left.total_seconds() % 86400) // 3600
                    text += f"⏰ Действует: {days}д {int(hours)}ч\n"
            
            text += (
                f"\n🎁 **Преимущества Premium:**\n"
                f"• +50% к доходу медведей\n"
                f"• 0% комиссии обмена\n"
                f"• Эксклюзивные кейсы\n"
                f"• Premium бейдж\n"
                f"• Больше реферальных бонусов\n\n"
                f"👑 **Преимущества VIP:**\n"
                f"• +100% к доходу медведей\n"
                f"• 0% комиссии обмена\n"
                f"• VIP эксклюзивные кейсы\n"
                f"• VIP бейдж\n"
                f"• 3 спина колеса/день\n"
                f"• Приоритетная поддержка\n"
                f"• VIP турниры\n\n"
                f"💡 Выберите подписку:"
            )
            
            keyboard = []
            
            if current_tier == "free":
                keyboard.append([
                    InlineKeyboardButton(text="⭐ Premium (0.1 TON/мес)", callback_data="buy_premium"),
                ])
                keyboard.append([
                    InlineKeyboardButton(text="👑 VIP (0.5 TON/мес)", callback_data="buy_vip"),
                ])
            elif current_tier == "premium":
                keyboard.append([
                    InlineKeyboardButton(text="👑 Апгрейд до VIP (0.5 TON/мес)", callback_data="buy_vip"),
                ])
                keyboard.append([
                    InlineKeyboardButton(text="🔄 Продлить Premium", callback_data="buy_premium"),
                ])
            else:  # vip
                keyboard.append([
                    InlineKeyboardButton(text="🔄 Продлить VIP", callback_data="buy_vip"),
                ])
            
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


@router.callback_query(F.data.in_(["buy_premium", "buy_vip"]))
async def buy_premium(query: CallbackQuery):
    """Buy premium subscription."""
    try:
        tier = "premium" if query.data == "buy_premium" else "vip"
        tier_data = PREMIUM_TIERS[tier]
        
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Check balance
            if user.ton_balance < Decimal(str(tier_data["price"])):
                await query.answer(
                    f"❌ Недостаточно TON!\n"
                    f"Требуется: {tier_data['price']} TON\n"
                    f"У вас: {float(user.ton_balance):.4f} TON",
                    show_alert=True
                )
                return
            
            # Deduct TON
            user.ton_balance -= Decimal(str(tier_data["price"]))
            
            # Set premium
            user.is_premium = True
            
            # Set expiration (30 days)
            if user.premium_until and user.premium_until > datetime.utcnow():
                # Extend existing subscription
                user.premium_until += timedelta(days=30)
            else:
                user.premium_until = datetime.utcnow() + timedelta(days=30)
            
            # Create subscription record
            subscription = Subscription(
                user_id=user.id,
                tier=tier,
                start_date=datetime.utcnow(),
                end_date=user.premium_until,
                price=tier_data["price"],
                is_active=True
            )
            session.add(subscription)
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=0,  # TON transaction, not coins
                transaction_type='premium_purchase',
                description=f'Покупка {tier_data["name"]} подписки'
            )
            session.add(transaction)
            
            await session.commit()
            
            text = (
                f"✅ **Подписка активирована!**\n\n"
                f"🎉 {tier_data['name']}\n"
                f"💎 Списано: {tier_data['price']} TON\n"
                f"⏰ Действует до: {user.premium_until.strftime('%d.%m.%Y')}\n\n"
                f"🎁 **Ваши преимущества:**\n"
            )
            
            for benefit in tier_data["benefits"]:
                text += f"{benefit}\n"
            
            text += "\n💡 Наслаждайтесь Premium возможностями!"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🐻 Мои медведи", callback_data="bears")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("🎉 Подписка активирована!")
            
            logger.info(f"✅ User {user.telegram_id} purchased {tier} subscription")
    
    except Exception as e:
        logger.error(f"❌ Error in buy_premium: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "premium_status")
async def premium_status(query: CallbackQuery):
    """Show premium status and benefits."""
    try:
        async with get_session() as session:
            # Get user
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            current_tier = get_user_tier(user)
            tier_data = PREMIUM_TIERS[current_tier]
            
            text = (
                f"⭐ **Статус подписки**\n\n"
                f"📊 **Текущий уровень:** {tier_data['name']}\n"
            )
            
            if user.is_premium and user.premium_until:
                time_left = user.premium_until - datetime.utcnow()
                if time_left.total_seconds() > 0:
                    days = time_left.days
                    hours = (time_left.total_seconds() % 86400) // 3600
                    text += (
                        f"⏰ Действует до: {user.premium_until.strftime('%d.%m.%Y %H:%M')}\n"
                        f"⏳ Осталось: {days}д {int(hours)}ч\n\n"
                    )
                else:
                    text += "⚠️ Подписка истекла!\n\n"
            
            text += f"🎁 **Активные бонусы:**\n"
            
            if tier_data["income_bonus"] > 0:
                text += f"• +{int(tier_data['income_bonus']*100)}% к доходу медведей\n"
            if tier_data["fee_discount"] > 0:
                text += f"• {int(tier_data['fee_discount']*100)}% скидка на комиссии\n"
            
            if current_tier == "free":
                text += "\n💡 Купите Premium, чтобы получить больше преимуществ!"
            
            # Get subscription history
            subs_query = select(Subscription).where(
                Subscription.user_id == user.id
            ).order_by(Subscription.created_at.desc()).limit(5)
            subs_result = await session.execute(subs_query)
            subscriptions = subs_result.scalars().all()
            
            if subscriptions:
                text += "\n\n📜 **История подписок:**\n"
                for sub in subscriptions:
                    status = "✅" if sub.is_active else "❌"
                    text += (
                        f"{status} {PREMIUM_TIERS[sub.tier]['name']} - "
                        f"{sub.start_date.strftime('%d.%m.%Y')}\n"
                    )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Купить Premium", callback_data="premium")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in premium_status: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
