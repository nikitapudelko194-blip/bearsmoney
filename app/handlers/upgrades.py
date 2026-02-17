"""Upgrades handler - comprehensive upgrade system."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import StateFilter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_session
from app.database.models import User, UserUpgrade, CoinTransaction
from datetime import datetime

logger = logging.getLogger(__name__)
router = Router()

# Конфигурация улучшений
UPGRADES_CONFIG = {
    # 👤 ПРОФИЛЬ
    'bear_slots': {
        'name': '📦 Слоты для медведей',
        'category': 'profile',
        'emoji': '📦',
        'description': 'Увеличивает количество мест для медведей',
        'max_level': 10,
        'base_cost': 5000,
        'cost_multiplier': 1.8,
        'effect_per_level': 2,  # +2 слота за уровень
        'effect_type': 'flat',
        'base_value': 10,  # Начальное значение без улучшений
    },
    'income_multiplier': {
        'name': '💰 Множитель дохода',
        'category': 'profile',
        'emoji': '💰',
        'description': 'Увеличивает весь доход от медведей',
        'max_level': 15,
        'base_cost': 10000,
        'cost_multiplier': 2.0,
        'effect_per_level': 5,  # +5% за уровень
        'effect_type': 'percent',
        'base_value': 0,
    },
    'auto_collect': {
        'name': '⚡ Автосбор монет',
        'category': 'profile',
        'emoji': '⚡',
        'description': 'Автоматически собирает монеты каждые N часов',
        'max_level': 5,
        'base_cost': 50000,
        'cost_multiplier': 2.5,
        'effect_per_level': -2,  # -2 часа за уровень (с 24 до 14 часов)
        'effect_type': 'time',
        'base_value': 24,  # 24 часа изначально
    },
    'case_bonus': {
        'name': '🎁 Бонус к кейсам',
        'category': 'profile',
        'emoji': '🎁',
        'description': 'Увеличивает награды из кейсов',
        'max_level': 10,
        'base_cost': 20000,
        'cost_multiplier': 2.0,
        'effect_per_level': 10,  # +10% за уровень
        'effect_type': 'percent',
        'base_value': 0,
    },
    'referral_bonus': {
        'name': '👥 Реферальный бонус',
        'category': 'profile',
        'emoji': '👥',
        'description': 'Увеличивает доход с рефералов',
        'max_level': 10,
        'base_cost': 15000,
        'cost_multiplier': 2.2,
        'effect_per_level': 5,  # +5% за уровень
        'effect_type': 'percent',
        'base_value': 0,
    },
    'rare_chance': {
        'name': '🍀 Шанс редкости',
        'category': 'profile',
        'emoji': '🍀',
        'description': 'Увеличивает шанс редких медведей',
        'max_level': 8,
        'base_cost': 30000,
        'cost_multiplier': 2.5,
        'effect_per_level': 5,  # +5% за уровень
        'effect_type': 'percent',
        'base_value': 0,
    },
    
    # 🏭 ПРОИЗВОДСТВО
    'production_speed': {
        'name': '⏰ Скорость производства',
        'category': 'production',
        'emoji': '⏰',
        'description': 'Медведи производят монеты быстрее',
        'max_level': 12,
        'base_cost': 8000,
        'cost_multiplier': 1.9,
        'effect_per_level': 10,  # +10% за уровень
        'effect_type': 'percent',
        'base_value': 0,
    },
    'coin_quality': {
        'name': '💎 Качество монет',
        'category': 'production',
        'emoji': '💎',
        'description': 'Больше монет за каждый сбор',
        'max_level': 10,
        'base_cost': 12000,
        'cost_multiplier': 2.1,
        'effect_per_level': 15,  # +15% за уровень
        'effect_type': 'percent',
        'base_value': 0,
    },
    'auto_reinvest': {
        'name': '🔄 Авто-реинвест',
        'category': 'production',
        'emoji': '🔄',
        'description': 'Автоматически покупает новых медведей',
        'max_level': 3,
        'base_cost': 100000,
        'cost_multiplier': 3.0,
        'effect_per_level': 1,  # Уровни: выкл, обычные, редкие, эпические
        'effect_type': 'tier',
        'base_value': 0,
    },
    
    # 💼 БИЗНЕС
    'shop_discount': {
        'name': '🏪 Скидка в магазине',
        'category': 'business',
        'emoji': '🏪',
        'description': 'Скидка на покупки в магазине',
        'max_level': 10,
        'base_cost': 15000,
        'cost_multiplier': 2.0,
        'effect_per_level': 3,  # +3% за уровень
        'effect_type': 'percent',
        'base_value': 0,
    },
    'exchange_rate': {
        'name': '💱 Курс обмена',
        'category': 'business',
        'emoji': '💱',
        'description': 'Лучший курс обмена монет на TON',
        'max_level': 8,
        'base_cost': 25000,
        'cost_multiplier': 2.3,
        'effect_per_level': 5,  # +5% за уровень
        'effect_type': 'percent',
        'base_value': 0,
    },
    'commission_reduce': {
        'name': '📉 Снижение комиссий',
        'category': 'business',
        'emoji': '📉',
        'description': 'Уменьшает комиссии за все операции',
        'max_level': 10,
        'base_cost': 20000,
        'cost_multiplier': 2.2,
        'effect_per_level': 5,  # -5% за уровень
        'effect_type': 'percent',
        'base_value': 0,
    },
}


def calculate_upgrade_cost(upgrade_type: str, current_level: int) -> int:
    """Рассчитать стоимость следующего уровня улучшения."""
    config = UPGRADES_CONFIG[upgrade_type]
    cost = config['base_cost'] * (config['cost_multiplier'] ** current_level)
    return int(cost)


def calculate_upgrade_effect(upgrade_type: str, level: int) -> float:
    """Рассчитать эффект улучшения на определенном уровне."""
    config = UPGRADES_CONFIG[upgrade_type]
    if config['effect_type'] == 'percent':
        return config['effect_per_level'] * level
    elif config['effect_type'] == 'flat':
        return config['base_value'] + (config['effect_per_level'] * level)
    elif config['effect_type'] == 'time':
        return max(2, config['base_value'] + (config['effect_per_level'] * level))  # Минимум 2 часа
    elif config['effect_type'] == 'tier':
        return level
    return 0


async def get_user_upgrade(session: AsyncSession, user_id: int, upgrade_type: str) -> UserUpgrade:
    """Получить или создать улучшение пользователя."""
    result = await session.execute(
        select(UserUpgrade).where(
            UserUpgrade.user_id == user_id,
            UserUpgrade.upgrade_type == upgrade_type
        )
    )
    upgrade = result.scalar_one_or_none()
    
    if not upgrade:
        config = UPGRADES_CONFIG[upgrade_type]
        upgrade = UserUpgrade(
            user_id=user_id,
            upgrade_type=upgrade_type,
            current_level=0,
            max_level=config['max_level']
        )
        session.add(upgrade)
        await session.commit()
        await session.refresh(upgrade)
    
    return upgrade


@router.callback_query(F.data == "upgrades")
async def show_upgrades_menu(callback: CallbackQuery):
    """Показать главное меню улучшений."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="upgrades_category:profile")],
        [InlineKeyboardButton(text="🏭 Производство", callback_data="upgrades_category:production")],
        [InlineKeyboardButton(text="💼 Бизнес", callback_data="upgrades_category:business")],
        [InlineKeyboardButton(text="📊 Все улучшения", callback_data="upgrades_all")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="start")],
    ])
    
    text = (
        "<b>🚀 СИСТЕМА УЛУЧШЕНИЙ</b>\n\n"
        "Выберите категорию улучшений:\n\n"
        "👤 <b>Профиль</b> - увеличение слотов, дохода, бонусов\n"
        "🏭 <b>Производство</b> - скорость и качество производства\n"
        "💼 <b>Бизнес</b> - скидки, курсы, снижение комиссий\n\n"
        "💡 Улучшения постоянны и действуют всегда!"
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("upgrades_category:"))
async def show_category_upgrades(callback: CallbackQuery):
    """Показать улучшения определенной категории."""
    category = callback.data.split(":")[1]
    
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        # Фильтруем улучшения по категории
        category_upgrades = {k: v for k, v in UPGRADES_CONFIG.items() if v['category'] == category}
        
        # Категории на русском
        category_names = {
            'profile': '👤 Профиль',
            'production': '🏭 Производство',
            'business': '💼 Бизнес'
        }
        
        text = f"<b>{category_names[category]}</b>\n\n"
        text += f"💰 Ваши монеты: <b>{user.coins:,.0f}</b>\n\n"
        
        keyboard_buttons = []
        
        for upgrade_type, config in category_upgrades.items():
            upgrade = await get_user_upgrade(session, user.id, upgrade_type)
            
            current_effect = calculate_upgrade_effect(upgrade_type, upgrade.current_level)
            next_cost = calculate_upgrade_cost(upgrade_type, upgrade.current_level)
            
            # Форматирование эффекта
            if config['effect_type'] == 'percent':
                effect_str = f"+{current_effect}%"
            elif config['effect_type'] == 'flat':
                effect_str = f"{int(current_effect)}"
            elif config['effect_type'] == 'time':
                effect_str = f"{int(current_effect)}ч"
            elif config['effect_type'] == 'tier':
                tiers = ['Выкл', 'Обычные', 'Редкие', 'Эпические']
                effect_str = tiers[int(current_effect)] if current_effect < len(tiers) else 'Макс'
            
            status = "🔒 МАКС" if upgrade.current_level >= config['max_level'] else f"💵 {next_cost:,.0f}"
            
            text += (
                f"{config['emoji']} <b>{config['name']}</b>\n"
                f"📈 Уровень: {upgrade.current_level}/{config['max_level']}\n"
                f"⚡ Эффект: {effect_str}\n"
                f"💰 Цена: {status}\n\n"
            )
            
            if upgrade.current_level < config['max_level']:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"{config['emoji']} {config['name']} (ур.{upgrade.current_level})",
                        callback_data=f"upgrade_buy:{upgrade_type}"
                    )
                ])
        
        keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="upgrades")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("upgrade_buy:"))
async def buy_upgrade(callback: CallbackQuery):
    """Купить улучшение."""
    upgrade_type = callback.data.split(":")[1]
    config = UPGRADES_CONFIG[upgrade_type]
    
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        upgrade = await get_user_upgrade(session, user.id, upgrade_type)
        
        # Проверка на максимальный уровень
        if upgrade.current_level >= config['max_level']:
            await callback.answer("✅ Это улучшение уже на максимальном уровне!")
            return
        
        cost = calculate_upgrade_cost(upgrade_type, upgrade.current_level)
        
        # Проверка баланса
        if user.coins < cost:
            await callback.answer(
                f"❌ Недостаточно монет! Нужно: {cost:,.0f}, у вас: {user.coins:,.0f}",
                show_alert=True
            )
            return
        
        # Покупка улучшения
        user.coins -= cost
        upgrade.current_level += 1
        upgrade.updated_at = datetime.utcnow()
        
        # Транзакция
        transaction = CoinTransaction(
            user_id=user.id,
            amount=-cost,
            transaction_type='upgrade',
            description=f"Улучшение: {config['name']} до уровня {upgrade.current_level}"
        )
        session.add(transaction)
        
        await session.commit()
        
        new_effect = calculate_upgrade_effect(upgrade_type, upgrade.current_level)
        
        await callback.answer(
            f"✅ Улучшено до уровня {upgrade.current_level}!\n"
            f"Новый эффект: {new_effect}",
            show_alert=True
        )
        
        # Обновляем экран категории
        await show_category_upgrades(callback)


@router.callback_query(F.data == "upgrades_all")
async def show_all_upgrades(callback: CallbackQuery):
    """Показать все улучшения пользователя."""
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.answer("❌ Пользователь не найден")
            return
        
        text = "<b>📊 ВСЕ ВАШИ УЛУЧШЕНИЯ</b>\n\n"
        text += f"💰 Баланс: <b>{user.coins:,.0f}</b>\n\n"
        
        categories = {
            'profile': '👤 ПРОФИЛЬ',
            'production': '🏭 ПРОИЗВОДСТВО',
            'business': '💼 БИЗНЕС'
        }
        
        for category, category_name in categories.items():
            text += f"<b>{category_name}</b>\n"
            
            category_upgrades = {k: v for k, v in UPGRADES_CONFIG.items() if v['category'] == category}
            
            for upgrade_type, config in category_upgrades.items():
                upgrade = await get_user_upgrade(session, user.id, upgrade_type)
                
                if upgrade.current_level > 0:
                    current_effect = calculate_upgrade_effect(upgrade_type, upgrade.current_level)
                    
                    if config['effect_type'] == 'percent':
                        effect_str = f"+{current_effect}%"
                    elif config['effect_type'] == 'flat':
                        effect_str = f"{int(current_effect)}"
                    elif config['effect_type'] == 'time':
                        effect_str = f"{int(current_effect)}ч"
                    elif config['effect_type'] == 'tier':
                        tiers = ['Выкл', 'Обычные', 'Редкие', 'Эпические']
                        effect_str = tiers[int(current_effect)]
                    
                    text += f"{config['emoji']} {config['name']}: <b>ур.{upgrade.current_level}</b> ({effect_str})\n"
            
            text += "\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="upgrades")],
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
