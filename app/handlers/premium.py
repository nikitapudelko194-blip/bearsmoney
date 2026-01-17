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

# Premium tiers
PREMIUM_TIERS = {
    "basic": {
        "name": "Basic",
        "emoji": "🆓",
        "price_ton": 0,
        "coins_bonus": 0,
        "commission_reduction": 0,
        "features": ["Стандартные медведи", "Базовый доход", "2% комиссия"]
    },
    "premium": {
        "name": "Premium",
        "emoji": "⭐",
        "price_ton": 0.1,
        "coins_bonus": 0.5,  # +50%
        "commission_reduction": 0.02,  # 0% commission
        "features": [
            "+50% к доходу",
            "0% комиссия",
            "Эксклюзивные медведи",
            "Приоритетная поддержка",
            "Специальный бейдж"
        ]
    },
    "vip": {
        "name": "VIP",
        "emoji": "👑",
        "price_ton": 0.5,
        "coins_bonus": 1.0,  # +100%
        "commission_reduction": 0.02,  # 0% commission
        "features": [
            "+100% к доходу",
            "0% комиссия",
            "Все эксклюзивные медведи",
            "VIP поддержка 24/7",
            "Золотой бейдж",
            "Доступ к NFT раньше всех",
            "Эксклюзивные события"
        ]
    }
}


@router.callback_query(F.data == "premium")
async def premium_menu(query: CallbackQuery):
    """Show premium subscription menu."""
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Check current subscription
            sub_query = select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status == 'active',
                Subscription.expires_at > datetime.utcnow()
            ).order_by(Subscription.expires_at.desc())
            sub_result = await session.execute(sub_query)
            current_sub = sub_result.scalar_one_or_none()
            
            current_tier = current_sub.tier if current_sub else "basic"
            
            text = (
                f"⭐ **Premium подписка**\n\n"
                f"💎 **Текущий статус:** {PREMIUM_TIERS[current_tier]['emoji']} {PREMIUM_TIERS[current_tier]['name']}\n"
            )
            
            if current_sub and current_tier != "basic":
                time_left = current_sub.expires_at - datetime.utcnow()
                days_left = time_left.days
                text += f"⏰ **Осталось:** {days_left} дней\n"
                text += f"🔄 **Авто-продление:** {'Вкл' if current_sub.auto_renew else 'Выкл'}\n"
            
            text += "\n🌟 **Выберите план:**"
            
            keyboard = []
            
            for tier_key, tier in PREMIUM_TIERS.items():
                if tier_key == "basic":
                    continue
                    
                is_current = tier_key == current_tier
                button_text = f"{tier['emoji']} {tier['name']} - {tier['price_ton']} TON/мес"
                if is_current:
                    button_text += " ✅"
                
                keyboard.append([
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"premium_details_{tier_key}"
                    )
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


@router.callback_query(F.data.startswith("premium_details_"))
async def premium_details(query: CallbackQuery):
    """Show premium tier details."""
    try:
        tier_key = query.data.split("_")[-1]
        tier = PREMIUM_TIERS.get(tier_key)
        
        if not tier:
            await query.answer("❌ Неверный тариф", show_alert=True)
            return
        
        text = (
            f"{tier['emoji']} **{tier['name']} подписка**\n\n"
            f"💰 **Цена:** {tier['price_ton']} TON/месяц\n\n"
            f"🎁 **Преимущества:**\n"
        )
        
        for feature in tier['features']:
            text += f"✅ {feature}\n"
        
        text += (
            f"\n💡 **Бонусы:**\n"
            f"📈 Доход: +{int(tier['coins_bonus'] * 100)}%\n"
            f"📉 Комиссия: {int((1 - tier['commission_reduction']) * 100)}%\n"
        )
        
        keyboard = [
            [InlineKeyboardButton(
                text=f"💳 Купить за {tier['price_ton']} TON",
                callback_data=f"premium_buy_{tier_key}"
            )],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="premium")]
        ]
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        try:
            await query.message.edit_text(text, reply_markup=reply_markup, parse_mode="markdown")
        except Exception:
            await query.message.answer(text, reply_markup=reply_markup, parse_mode="markdown")
        
        await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in premium_details: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data.startswith("premium_buy_"))
async def premium_buy(query: CallbackQuery):
    """Buy premium subscription."""
    try:
        tier_key = query.data.split("_")[-1]
        tier = PREMIUM_TIERS.get(tier_key)
        
        if not tier:
            await query.answer("❌ Неверный тариф", show_alert=True)
            return
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            price = Decimal(str(tier['price_ton']))
            
            # Check balance
            if user.ton_balance < price:
                needed = float(price - user.ton_balance)
                await query.answer(
                    f"❌ Недостаточно TON\n\nНужно: {price} TON\nУ вас: {float(user.ton_balance):.4f} TON\nНехватает: {needed:.4f} TON",
                    show_alert=True
                )
                return
            
            # Deduct payment
            user.ton_balance -= price
            user.is_premium = True
            user.premium_until = datetime.utcnow() + timedelta(days=30)
            
            # Create subscription
            subscription = Subscription(
                user_id=user.id,
                tier=tier_key,
                coins_bonus=tier['coins_bonus'],
                commission_reduction=tier['commission_reduction'],
                status='active',
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=30),
                auto_renew=True
            )
            session.add(subscription)
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=0,
                transaction_type='premium_purchase',
                description=f'Покупка {tier["name"]} подписки за {price} TON'
            )
            session.add(transaction)
            
            await session.commit()
            
            text = (
                f"✅ **Подписка активирована!**\n\n"
                f"{tier['emoji']} **{tier['name']}**\n"
                f"⏰ Активна до: {subscription.expires_at.strftime('%d.%m.%Y')}\n\n"
                f"🎁 Теперь вы получаете:\n"
            )
            
            for feature in tier['features']:
                text += f"✅ {feature}\n"
            
            text += f"\n💎 Новый баланс: {float(user.ton_balance):.4f} TON"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎉 Отлично!", callback_data="premium")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")]
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer("🎉 Поздравляем с покупкой Premium!")
            
            logger.info(f"✅ User {user.telegram_id} purchased {tier_key} subscription")
    
    except Exception as e:
        logger.error(f"❌ Error in premium_buy: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)
