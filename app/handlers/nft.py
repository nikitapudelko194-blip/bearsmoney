"""NFT marketplace and bear conversion handlers."""
import logging
import hashlib
from datetime import datetime
from decimal import Decimal
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database.db import get_session
from app.database.models import User, Bear, P2PListing, CoinTransaction
from app.services.bears import BEAR_CLASSES

logger = logging.getLogger(__name__)
router = Router()

# NFT conversion costs
NFT_CONVERSION_COST = {
    'rare': 10000,  # 10k coins
    'epic': 50000,  # 50k coins
    'legendary': 100000,  # 100k coins
}

# NFT royalty percentage
NFT_ROYALTY_PERCENT = 0.05  # 5%

# Minimum rarity for NFT conversion
NFT_MIN_RARITY = ['rare', 'epic', 'legendary']


class NFTStates(StatesGroup):
    """NFT states."""
    waiting_for_price = State()
    waiting_for_bear_id = State()


def generate_nft_id(bear_id: int, user_id: int) -> str:
    """
    Generate unique NFT ID.
    """
    data = f"{bear_id}_{user_id}_{datetime.utcnow().timestamp()}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]


@router.callback_query(F.data == "nft_marketplace")
async def nft_marketplace_menu(query: CallbackQuery):
    """
    Show NFT marketplace main menu.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Count user's NFT bears
            bears_query = select(Bear).where(
                Bear.owner_id == user.id,
                Bear.bear_type.in_(NFT_MIN_RARITY)
            )
            bears_result = await session.execute(bears_query)
            nft_bears = bears_result.scalars().all()
            
            # Count active listings
            listings_query = select(P2PListing).where(
                P2PListing.seller_id == user.id,
                P2PListing.status == 'active'
            )
            listings_result = await session.execute(listings_query)
            active_listings = listings_result.scalars().all()
            
            # Count marketplace listings
            market_query = select(P2PListing).where(
                P2PListing.status == 'active',
                P2PListing.seller_id != user.id
            )
            market_result = await session.execute(market_query)
            market_listings = market_result.scalars().all()
            
            text = (
                f"🖼️ **NFT Marketplace**\n\n"
                f"🐻 **Ваши NFT медведи:** {len(nft_bears)}\n"
                f"🏷️ **Активные лоты:** {len(active_listings)}\n"
                f"📊 **На рынке:** {len(market_listings)} медведей\n\n"
                f"✨ **NFT функции:**\n"
                f"• Конвертация редких медведей\n"
                f"• P2P торговля\n"
                f"• 5% royalty с перепродаж\n"
                f"• Уникальные коллекции\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🖼️ Мои NFT", callback_data="nft_my_collection")],
                [InlineKeyboardButton(text="🛈️ Выставить на продажу", callback_data="nft_list_for_sale")],
                [InlineKeyboardButton(text="🛒 Покупка NFT", callback_data="nft_browse_marketplace")],
                [InlineKeyboardButton(text="✨ Конвертировать в NFT", callback_data="nft_convert")],
                [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in nft_marketplace_menu: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "nft_my_collection")
async def nft_my_collection(query: CallbackQuery):
    """
    Show user's NFT collection.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get NFT bears (rare+)
            bears_query = select(Bear).where(
                Bear.owner_id == user.id,
                Bear.bear_type.in_(NFT_MIN_RARITY)
            ).order_by(Bear.level.desc())
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            if not bears:
                text = (
                    f"🖼️ **Моя NFT коллекция**\n\n"
                    f"📦 У вас пока нет NFT медведей!\n\n"
                    f"💡 Чтобы создать NFT:\n"
                    f"1. Получите редкого/эпического/легендарного медведя\n"
                    f"2. Конвертируйте его в NFT\n"
                    f"3. Торгуйте на маркетплейсе!\n"
                )
            else:
                text = (
                    f"🖼️ **Моя NFT коллекция** ({len(bears)})\n\n"
                )
                
                for idx, bear in enumerate(bears[:10], 1):
                    class_info = BEAR_CLASSES[bear.bear_type]
                    on_sale = " 🏷️" if bear.is_on_sale else ""
                    text += (
                        f"{idx}. {class_info['color']} **{bear.name}** (ID: {bear.id})\n"
                        f"   ├ ⭐ Lv{bear.level} | 💰 {bear.coins_per_hour:.1f}k/h{on_sale}\n"
                        f"   └ 📅 {bear.purchased_at.strftime('%d.%m.%Y')}\n\n"
                    )
                
                if len(bears) > 10:
                    text += f"... и ещё {len(bears) - 10}\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛈️ Выставить на продажу", callback_data="nft_list_for_sale")],
                [InlineKeyboardButton(text="⬅️ К NFT", callback_data="nft_marketplace")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in nft_my_collection: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "nft_convert")
async def nft_convert_select(query: CallbackQuery, state: FSMContext):
    """
    Select bear to convert to NFT.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get eligible bears
            bears_query = select(Bear).where(
                Bear.owner_id == user.id,
                Bear.bear_type.in_(NFT_MIN_RARITY),
                Bear.is_on_sale == False
            )
            bears_result = await session.execute(bears_query)
            bears = bears_result.scalars().all()
            
            if not bears:
                await query.answer(
                    "❌ У вас нет подходящих медведей.\n"
                    "Нужен редкий/эпический/легендарный медведь.",
                    show_alert=True
                )
                return
            
            text = (
                f"✨ **Конвертация в NFT**\n\n"
                f"💡 Выберите медведя для конвертации:\n\n"
                f"💰 **Стоимость:**\n"
                f"├ Rare: {NFT_CONVERSION_COST['rare']:,} Coins\n"
                f"├ Epic: {NFT_CONVERSION_COST['epic']:,} Coins\n"
                f"└ Legendary: {NFT_CONVERSION_COST['legendary']:,} Coins\n\n"
                f"📝 Введите ID медведя:\n\n"
            )
            
            for bear in bears[:5]:
                class_info = BEAR_CLASSES[bear.bear_type]
                cost = NFT_CONVERSION_COST[bear.bear_type]
                text += (
                    f"{class_info['color']} **{bear.name}** (ID: {bear.id})\n"
                    f"   Lv{bear.level} | {bear.coins_per_hour:.1f}k/h | {cost:,} Coins\n\n"
                )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="nft_marketplace")],
            ])
            
            await state.set_state(NFTStates.waiting_for_bear_id)
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in nft_convert_select: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.message(NFTStates.waiting_for_bear_id)
async def nft_convert_confirm(message: Message, state: FSMContext):
    """
    Confirm NFT conversion.
    """
    try:
        bear_id = int(message.text)
        
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == message.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get bear
            bear_query = select(Bear).where(
                Bear.id == bear_id,
                Bear.owner_id == user.id,
                Bear.bear_type.in_(NFT_MIN_RARITY)
            )
            bear_result = await session.execute(bear_query)
            bear = bear_result.scalar_one_or_none()
            
            if not bear:
                await message.answer("❌ Медведь не найден или не подходит для NFT.")
                await state.clear()
                return
            
            cost = NFT_CONVERSION_COST[bear.bear_type]
            
            if user.coins < cost:
                await message.answer(
                    f"❌ Недостаточно Coins!\n"
                    f"Нужно: {cost:,} Coins\n"
                    f"Есть: {user.coins:,.0f} Coins"
                )
                await state.clear()
                return
            
            # Convert to NFT
            user.coins -= cost
            bear.is_locked = True  # Lock from accidental sale
            
            # Generate NFT ID (in real app, this would mint on TON blockchain)
            nft_id = generate_nft_id(bear.id, user.id)
            
            # Log transaction
            transaction = CoinTransaction(
                user_id=user.id,
                amount=-cost,
                transaction_type='nft_conversion',
                description=f'NFT конверсия {bear.name} (ID: {nft_id[:8]})'
            )
            session.add(transaction)
            
            await session.commit()
            
            class_info = BEAR_CLASSES[bear.bear_type]
            text = (
                f"✅ **NFT создан!**\n\n"
                f"✨ {class_info['color']} **{bear.name}** теперь NFT!\n\n"
                f"🆔 **NFT ID:** `{nft_id}`\n"
                f"📊 **Характеристики:**\n"
                f"├ ⭐ Уровень: {bear.level}\n"
                f"├ 💰 Доход: {bear.coins_per_hour:.1f}k/h\n"
                f"└ 💎 Тип: {class_info['rarity']}\n\n"
                f"💰 **Списано:** {cost:,} Coins\n"
                f"💼 **Новый баланс:** {user.coins:,.0f} Coins\n\n"
                f"💡 Теперь вы можете продать этого медведя на NFT маркетплейсе!\n"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛈️ Выставить на продажу", callback_data="nft_list_for_sale")],
                [InlineKeyboardButton(text="🖼️ Мои NFT", callback_data="nft_my_collection")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")],
            ])
            
            await message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            await state.clear()
            
            logger.info(f"✅ User {user.telegram_id} converted bear {bear.id} to NFT for {cost} coins")
    
    except ValueError:
        await message.answer("❌ Неверный ID. Введите число.")
    except Exception as e:
        logger.error(f"❌ Error in nft_convert_confirm: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")
        await state.clear()


@router.callback_query(F.data == "nft_browse_marketplace")
async def nft_browse_marketplace(query: CallbackQuery):
    """
    Browse NFT marketplace.
    """
    try:
        async with get_session() as session:
            user_query = select(User).where(User.telegram_id == query.from_user.id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one()
            
            # Get active listings
            listings_query = select(P2PListing).where(
                P2PListing.status == 'active'
            ).order_by(P2PListing.created_at.desc()).limit(10)
            listings_result = await session.execute(listings_query)
            listings = listings_result.scalars().all()
            
            if not listings:
                text = (
                    f"🛒 **NFT Marketplace**\n\n"
                    f"📦 На маркетплейсе пока нет предложений.\n\n"
                    f"💡 Станьте первым, кто выставит своего медведя!\n"
                )
            else:
                text = (
                    f"🛒 **NFT Marketplace** ({len(listings)})\n\n"
                )
                
                for listing in listings:
                    # Get bear and seller
                    bear_query = select(Bear).where(Bear.id == listing.bear_id)
                    bear_result = await session.execute(bear_query)
                    bear = bear_result.scalar_one()
                    
                    seller_query = select(User).where(User.id == listing.seller_id)
                    seller_result = await session.execute(seller_query)
                    seller = seller_result.scalar_one()
                    
                    class_info = BEAR_CLASSES[bear.bear_type]
                    
                    text += (
                        f"{class_info['color']} **{bear.name}** (ID: {bear.id})\n"
                        f"   ├ ⭐ Lv{bear.level} | 💰 {bear.coins_per_hour:.1f}k/h\n"
                        f"   ├ 💸 Цена: {listing.price_coins:,.0f} Coins\n"
                        f"   └ 👤 Продавец: @{seller.username or seller.first_name}\n\n"
                    )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛈️ Купить NFT", callback_data="nft_buy_select")],
                [InlineKeyboardButton(text="⬅️ К NFT", callback_data="nft_marketplace")],
            ])
            
            try:
                await query.message.edit_text(text, reply_markup=keyboard, parse_mode="markdown")
            except Exception:
                await query.message.answer(text, reply_markup=keyboard, parse_mode="markdown")
            
            await query.answer()
    
    except Exception as e:
        logger.error(f"❌ Error in nft_browse_marketplace: {e}", exc_info=True)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


# Note: Additional handlers for listing, buying, and managing NFTs would be added here
# This is a foundation for the NFT system. Full implementation would include:
# - nft_list_for_sale: List bear for sale
# - nft_buy_select: Select and buy NFT
# - nft_cancel_listing: Cancel listing
# - Integration with TON blockchain for actual NFT minting
# - Royalty distribution system
