"""API endpoints for new game features."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.database import get_session
from app.services.features import FeaturesService
from app.services.utils import get_current_user
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/api/features", tags=["features"])


class DailyRewardResponse(BaseModel):
    """Daily reward response."""
    streak_day: int
    reward_type: str  # 'coins' or 'bear'
    reward_value: float
    bear_type: str | None
    emoji: str


class CaseStatisticsResponse(BaseModel):
    """Case statistics response."""
    total_opened: int
    total_spent: float
    total_earned: float
    rtp_percent: float
    profit: float


class BearInsuranceRequest(BaseModel):
    """Insurance request."""
    bear_id: int
    hours: int = 24  # 24, 48, or -1 for permanent


class P2PListingRequest(BaseModel):
    """P2P listing request."""
    bear_id: int
    price_coins: float


class P2PBuyRequest(BaseModel):
    """P2P buy request."""
    listing_id: int


class P2PCancelRequest(BaseModel):
    """P2P cancel listing request."""
    listing_id: int


class BearFusionRequest(BaseModel):
    """Bear fusion request."""
    bear_ids: list[int]
    input_type: str  # 'common', 'rare', 'epic'


# ============ ДОСТИЖЕНИЯ ============

@router.get("/achievements")
async def get_achievements(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
):
    """Get user achievements."""
    achievements = await FeaturesService.check_and_unlock_achievements(session, user_id)
    return {'achievements': achievements, 'count': len(achievements)}


# ============ ЕЖЕДНЕВНЫЕ ЛОГИНЫ ============

@router.get("/daily-reward")
async def claim_daily_reward(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
) -> DailyRewardResponse:
    """Claim daily reward."""
    try:
        reward = await FeaturesService.claim_daily_reward(session, user_id)
        return DailyRewardResponse(**reward)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ ИСТОРИЯ КЕЙСОВ ============

@router.get("/case-statistics")
async def get_case_statistics(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
) -> CaseStatisticsResponse:
    """Get case opening statistics with RTP."""
    stats = await FeaturesService.get_case_statistics(session, user_id)
    if 'error' in stats:
        raise HTTPException(status_code=404, detail=stats['error'])
    return CaseStatisticsResponse(
        total_opened=stats['total_opened'],
        total_spent=stats['total_spent'],
        total_earned=stats['total_earned'],
        rtp_percent=stats['rtp_percent'],
        profit=stats['profit'],
    )


# ============ СТРАХОВКА ============

@router.post("/bear-insurance")
async def insure_bear(
    request: BearInsuranceRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
):
    """Buy insurance for a bear."""
    try:
        insurance = await FeaturesService.insure_bear(session, request.bear_id, user_id, request.hours)
        expires_text = "Вечно" if insurance.expires_at is None else insurance.expires_at.strftime("%Y-%m-%d %H:%M")
        return {
            'success': True,
            'message': f'🐻 Медведь застрахован!',
            'expires_at': expires_text,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ P2P ТОРГОВЛЯ ============

@router.get("/p2p-marketplace")
async def get_marketplace(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """Get all available bears on P2P marketplace."""
    listings = await FeaturesService.get_available_listings(session, limit, offset)
    return {
        'listings': listings,
        'count': len(listings),
    }


@router.post("/p2p-list")
async def list_bear_for_sale(
    request: P2PListingRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
):
    """List bear for sale on P2P market (медведь исчезнет из профиля)."""
    try:
        listing = await FeaturesService.list_bear_for_sale(session, request.bear_id, user_id, request.price_coins)
        return {
            'success': True,
            'listing_id': listing.id,
            'message': f'🐻 Медведь выставлен на P2P маркетплейс! Он исчезнет из твоего профиля до продажи.',
            'price': request.price_coins,
            'status': 'on_sale',
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/p2p-cancel")
async def cancel_listing(
    request: P2PCancelRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
):
    """Cancel P2P listing and return bear to profile."""
    try:
        result = await FeaturesService.cancel_listing(session, request.listing_id, user_id)
        return {
            'success': True,
            'message': '✅ Медведь снят с продажи и вернулся в твой профиль!',
            'status': 'cancelled',
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/p2p-buy")
async def buy_bear_from_player(
    request: P2PBuyRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
):
    """Buy bear from another player."""
    try:
        result = await FeaturesService.buy_bear_from_player(session, request.listing_id, user_id)
        return {
            'success': True,
            'message': '✅ Медведь куплен! Он добавлен в твой профиль!',
            'status': 'completed',
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============ ПЕРЕПЛАВКА ============

@router.post("/fuse-bears")
async def fuse_bears(
    request: BearFusionRequest,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user),
):
    """Fuse bears (10 of one type = 1 of next tier)."""
    try:
        result = await FeaturesService.fuse_bears(session, user_id, request.bear_ids, request.input_type)
        return {
            'success': True,
            'message': result['message'],
            'new_bear': {
                'id': result['new_bear'].id,
                'type': result['new_bear'].bear_type,
                'level': result['new_bear'].level,
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
